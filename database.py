"""
database.py
Maneja la conexión a SQLite y todas las operaciones sobre las tablas:
usuarios, productos, clientes, ventas, detalle_ventas, config.
"""

import sqlite3
import os
import hashlib
import secrets
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "bodegon.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password: str, salt: str = None):
    if salt is None:
        salt = secrets.token_hex(8)
    h = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return h, salt


def verificar_password(password: str, hash_guardado: str, salt: str) -> bool:
    h, _ = hash_password(password, salt)
    return h == hash_guardado


def init_db():
    """Crea las tablas si no existen y siembra datos por defecto."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            apellido TEXT,
            email TEXT,
            usuario TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            rol TEXT NOT NULL CHECK(rol IN ('admin', 'cajero')),
            activo INTEGER NOT NULL DEFAULT 1,
            intentos_fallidos INTEGER NOT NULL DEFAULT 0,
            bloqueado_hasta TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            categoria TEXT,
            precio_usd REAL NOT NULL DEFAULT 0,
            stock INTEGER NOT NULL DEFAULT 0,
            stock_minimo INTEGER NOT NULL DEFAULT 5,
            activo INTEGER NOT NULL DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            telefono TEXT,
            cedula TEXT UNIQUE,
            frecuente INTEGER NOT NULL DEFAULT 0,
            fecha_registro TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_hora TEXT NOT NULL,
            cliente_id INTEGER,
            usuario_id INTEGER NOT NULL,
            total_usd REAL NOT NULL,
            total_bs REAL NOT NULL,
            tasa_bcv REAL NOT NULL,
            forma_pago TEXT NOT NULL,
            anulada INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS detalle_ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id INTEGER NOT NULL,
            producto_id INTEGER NOT NULL,
            nombre_producto TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            precio_unitario_usd REAL NOT NULL,
            FOREIGN KEY (venta_id) REFERENCES ventas(id),
            FOREIGN KEY (producto_id) REFERENCES productos(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS config (
            clave TEXT PRIMARY KEY,
            valor TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_hora TEXT NOT NULL,
            tipo TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            usuario_id INTEGER
        )
    """)

    conn.commit()

    # Semilla: usuario admin por defecto si no hay ningún usuario
    cur.execute("SELECT COUNT(*) AS c FROM usuarios")
    if cur.fetchone()["c"] == 0:
        crear_usuario(conn, "Administrador", "General", "admin@bodegon.local",
                      "admin", "admin123", "admin")
        crear_usuario(conn, "Cajero", "Uno", "cajero@bodegon.local",
                      "cajero", "cajero123", "cajero")

    # Semilla: config por defecto (tasas: BCV dólar auto, BCV euro auto, y manual)
    cur.execute("SELECT COUNT(*) AS c FROM config")
    if cur.fetchone()["c"] == 0:
        valores_iniciales = [
            ("tasa_bcv_usd", "0"),
            ("tasa_bcv_usd_actualizada", ""),
            ("tasa_bcv_eur", "0"),
            ("tasa_bcv_eur_actualizada", ""),
            ("tasa_manual", "0"),
            ("tasa_manual_actualizada", ""),
            ("tasa_para_ventas", "bcv_usd"),  # 'bcv_usd' o 'manual'
        ]
        cur.executemany("INSERT INTO config (clave, valor) VALUES (?, ?)", valores_iniciales)
        conn.commit()

    # Semilla: un par de productos de ejemplo si la tabla está vacía
    cur.execute("SELECT COUNT(*) AS c FROM productos")
    if cur.fetchone()["c"] == 0:
        ejemplo = [
            ("Harina PAN 1kg", "Alimentos", 1.20, 30, 10),
            ("Coca Cola 2L", "Bebidas", 1.80, 24, 6),
            ("Papel Higiénico x4", "Aseo", 2.50, 15, 5),
            ("Aceite Vatel 1L", "Alimentos", 3.00, 12, 4),
        ]
        cur.executemany(
            "INSERT INTO productos (nombre, categoria, precio_usd, stock, stock_minimo) "
            "VALUES (?, ?, ?, ?, ?)", ejemplo
        )
        conn.commit()

    conn.close()


# ---------------------------------------------------------------- USUARIOS

def crear_usuario(conn, nombre, apellido, email, usuario, password, rol):
    h, salt = hash_password(password)
    conn.execute(
        "INSERT INTO usuarios (nombre, apellido, email, usuario, password_hash, salt, rol) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (nombre, apellido, email, usuario, h, salt, rol)
    )
    conn.commit()


def obtener_usuario_por_login(conn, usuario):
    cur = conn.execute("SELECT * FROM usuarios WHERE usuario = ?", (usuario,))
    return cur.fetchone()


def listar_usuarios(conn):
    return conn.execute("SELECT * FROM usuarios ORDER BY id").fetchall()


def eliminar_usuario(conn, usuario_id, realizado_por=None):
    conn.execute("UPDATE usuarios SET activo = 0 WHERE id = ?", (usuario_id,))
    conn.commit()
    registrar_movimiento(conn, "usuario", f"Usuario id {usuario_id} desactivado", realizado_por)


def registrar_intento_fallido(conn, usuario_id, intentos, bloqueado_hasta):
    conn.execute(
        "UPDATE usuarios SET intentos_fallidos = ?, bloqueado_hasta = ? WHERE id = ?",
        (intentos, bloqueado_hasta, usuario_id)
    )
    conn.commit()


def resetear_intentos(conn, usuario_id):
    conn.execute(
        "UPDATE usuarios SET intentos_fallidos = 0, bloqueado_hasta = NULL WHERE id = ?",
        (usuario_id,)
    )
    conn.commit()


def cambiar_password(conn, usuario_id, nueva_password):
    h, salt = hash_password(nueva_password)
    conn.execute(
        "UPDATE usuarios SET password_hash = ?, salt = ? WHERE id = ?",
        (h, salt, usuario_id)
    )
    conn.commit()


# --------------------------------------------------------------- PRODUCTOS

def listar_productos(conn, solo_activos=True):
    if solo_activos:
        return conn.execute(
            "SELECT * FROM productos WHERE activo = 1 ORDER BY nombre"
        ).fetchall()
    return conn.execute("SELECT * FROM productos ORDER BY nombre").fetchall()


def productos_bajo_stock(conn):
    return conn.execute(
        "SELECT * FROM productos WHERE activo = 1 AND stock <= stock_minimo ORDER BY stock"
    ).fetchall()


def agregar_producto(conn, nombre, categoria, precio_usd, stock, stock_minimo, usuario_id=None):
    conn.execute(
        "INSERT INTO productos (nombre, categoria, precio_usd, stock, stock_minimo) "
        "VALUES (?, ?, ?, ?, ?)",
        (nombre, categoria, precio_usd, stock, stock_minimo)
    )
    conn.commit()
    registrar_movimiento(conn, "producto", f"Producto agregado: {nombre} (stock inicial {stock})", usuario_id)


def editar_producto(conn, producto_id, nombre, categoria, precio_usd, stock_minimo, usuario_id=None):
    conn.execute(
        "UPDATE productos SET nombre=?, categoria=?, precio_usd=?, stock_minimo=? WHERE id=?",
        (nombre, categoria, precio_usd, stock_minimo, producto_id)
    )
    conn.commit()
    registrar_movimiento(conn, "producto", f"Producto editado: {nombre} (precio ${precio_usd:.2f})", usuario_id)


def ajustar_stock(conn, producto_id, cantidad_delta, usuario_id=None):
    conn.execute(
        "UPDATE productos SET stock = stock + ? WHERE id = ?",
        (cantidad_delta, producto_id)
    )
    conn.commit()
    producto = obtener_producto(conn, producto_id)
    signo = "+" if cantidad_delta >= 0 else ""
    registrar_movimiento(
        conn, "stock",
        f"Ajuste de stock en '{producto['nombre']}': {signo}{cantidad_delta} (nuevo stock: {producto['stock']})",
        usuario_id
    )


def eliminar_producto(conn, producto_id, usuario_id=None):
    producto = obtener_producto(conn, producto_id)
    conn.execute("UPDATE productos SET activo = 0 WHERE id = ?", (producto_id,))
    conn.commit()
    registrar_movimiento(conn, "producto", f"Producto eliminado: {producto['nombre']}", usuario_id)


def obtener_producto(conn, producto_id):
    return conn.execute("SELECT * FROM productos WHERE id = ?", (producto_id,)).fetchone()


# --------------------------------------------------------------- CLIENTES

def buscar_cliente_por_cedula(conn, cedula):
    return conn.execute("SELECT * FROM clientes WHERE cedula = ?", (cedula,)).fetchone()


def buscar_clientes_por_nombre(conn, texto):
    return conn.execute(
        "SELECT * FROM clientes WHERE nombre LIKE ? ORDER BY nombre",
        (f"%{texto}%",)
    ).fetchall()


def registrar_cliente(conn, nombre, telefono, cedula, frecuente=False):
    conn.execute(
        "INSERT INTO clientes (nombre, telefono, cedula, frecuente, fecha_registro) "
        "VALUES (?, ?, ?, ?, ?)",
        (nombre, telefono, cedula, 1 if frecuente else 0, datetime.now().isoformat())
    )
    conn.commit()


def listar_clientes(conn):
    return conn.execute("SELECT * FROM clientes ORDER BY nombre").fetchall()


# ----------------------------------------------------------------- VENTAS

def registrar_venta(conn, cliente_id, usuario_id, carrito, tasa_bcv, forma_pago):
    """
    carrito: lista de dicts {producto_id, nombre, cantidad, precio_unitario_usd}
    Descuenta stock y guarda venta + detalle. Devuelve el id de la venta.
    """
    total_usd = sum(item["cantidad"] * item["precio_unitario_usd"] for item in carrito)
    total_bs = total_usd * tasa_bcv

    cur = conn.cursor()
    cur.execute(
        "INSERT INTO ventas (fecha_hora, cliente_id, usuario_id, total_usd, total_bs, tasa_bcv, forma_pago) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (datetime.now().isoformat(), cliente_id, usuario_id, total_usd, total_bs, tasa_bcv, forma_pago)
    )
    venta_id = cur.lastrowid

    for item in carrito:
        cur.execute(
            "INSERT INTO detalle_ventas (venta_id, producto_id, nombre_producto, cantidad, precio_unitario_usd) "
            "VALUES (?, ?, ?, ?, ?)",
            (venta_id, item["producto_id"], item["nombre"], item["cantidad"], item["precio_unitario_usd"])
        )
        cur.execute(
            "UPDATE productos SET stock = stock - ? WHERE id = ?",
            (item["cantidad"], item["producto_id"])
        )

    conn.commit()
    registrar_movimiento(
        conn, "venta",
        f"Venta #{venta_id} por ${total_usd:.2f} (Bs {total_bs:.2f}) - {forma_pago}",
        usuario_id
    )
    return venta_id


def obtener_venta(conn, venta_id):
    return conn.execute("SELECT * FROM ventas WHERE id = ?", (venta_id,)).fetchone()


def obtener_detalle_venta(conn, venta_id):
    return conn.execute(
        "SELECT * FROM detalle_ventas WHERE venta_id = ?", (venta_id,)
    ).fetchall()


def ventas_entre_fechas(conn, fecha_ini_iso, fecha_fin_iso):
    return conn.execute(
        "SELECT * FROM ventas WHERE fecha_hora BETWEEN ? AND ? AND anulada = 0 ORDER BY fecha_hora DESC",
        (fecha_ini_iso, fecha_fin_iso)
    ).fetchall()


def productos_mas_vendidos(conn, fecha_ini_iso, fecha_fin_iso, limite=10):
    return conn.execute("""
        SELECT dv.nombre_producto, SUM(dv.cantidad) AS unidades,
               SUM(dv.cantidad * dv.precio_unitario_usd) AS total_usd
        FROM detalle_ventas dv
        JOIN ventas v ON v.id = dv.venta_id
        WHERE v.fecha_hora BETWEEN ? AND ? AND v.anulada = 0
        GROUP BY dv.producto_id
        ORDER BY unidades DESC
        LIMIT ?
    """, (fecha_ini_iso, fecha_fin_iso, limite)).fetchall()


# ------------------------------------------------------------------ CONFIG

def get_config(conn, clave, default=None):
    row = conn.execute("SELECT valor FROM config WHERE clave = ?", (clave,)).fetchone()
    return row["valor"] if row else default


def set_config(conn, clave, valor):
    conn.execute(
        "INSERT INTO config (clave, valor) VALUES (?, ?) "
        "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
        (clave, str(valor))
    )
    conn.commit()


# -------------------------------------------------------------- MOVIMIENTOS

def registrar_movimiento(conn, tipo, descripcion, usuario_id=None):
    """
    Guarda un renglón en la bitácora de movimientos (para el registro diario).
    tipo típico: 'venta', 'producto', 'stock', 'usuario', 'tasa'.
    """
    conn.execute(
        "INSERT INTO movimientos (fecha_hora, tipo, descripcion, usuario_id) VALUES (?, ?, ?, ?)",
        (datetime.now().isoformat(), tipo, descripcion, usuario_id)
    )
    conn.commit()


def movimientos_entre_fechas(conn, fecha_ini_iso, fecha_fin_iso):
    return conn.execute(
        "SELECT m.*, u.nombre AS usuario_nombre FROM movimientos m "
        "LEFT JOIN usuarios u ON u.id = m.usuario_id "
        "WHERE m.fecha_hora BETWEEN ? AND ? ORDER BY m.fecha_hora",
        (fecha_ini_iso, fecha_fin_iso)
    ).fetchall()
