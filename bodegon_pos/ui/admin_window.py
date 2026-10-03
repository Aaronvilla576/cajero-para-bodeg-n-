import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, timedelta

import database as db
import bcv
import backup
from ui.widgets import BarraTasas


class AdminWindow(tk.Tk):
    def __init__(self, usuario_row):
        super().__init__()
        self.usuario_row = usuario_row
        self.title(f"Panel de Administrador — {usuario_row['nombre']}")
        self.geometry("940x600")

        self.conn = db.get_connection()

        self._construir_menu()
        self.barra_tasas = BarraTasas(self, self.conn)
        self.barra_tasas.pack(fill="x")
        self._construir_tabs()
        self._alertar_stock_bajo_inicio()

        self.protocol("WM_DELETE_WINDOW", self._cerrar)

    # ------------------------------------------------------------ layout

    def _construir_menu(self):
        top = tk.Frame(self, bg="#2f3b4c")
        top.pack(fill="x")
        tk.Label(
            top, text=f"Sesión: {self.usuario_row['nombre']} {self.usuario_row['apellido'] or ''} (Administrador)",
            bg="#2f3b4c", fg="white", padx=10, pady=6
        ).pack(side="left")
        ttk.Button(top, text="Cerrar sesión", command=self._cerrar).pack(side="right", padx=10, pady=5)

    def _construir_tabs(self):
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(expand=True, fill="both", padx=8, pady=8)

        self.tab_productos = tk.Frame(self.tabs)
        self.tab_reportes = tk.Frame(self.tabs)
        self.tab_tasa = tk.Frame(self.tabs)
        self.tab_usuarios = tk.Frame(self.tabs)

        self.tabs.add(self.tab_productos, text="Productos / Inventario")
        self.tabs.add(self.tab_reportes, text="Reportes de ventas")
        self.tabs.add(self.tab_tasa, text="Tasa BCV")
        self.tabs.add(self.tab_usuarios, text="Usuarios")

        self._construir_tab_productos()
        self._construir_tab_reportes()
        self._construir_tab_tasa()
        self._construir_tab_usuarios()

    # ------------------------------------------------------- PRODUCTOS

    def _construir_tab_productos(self):
        frame = self.tab_productos

        barra = tk.Frame(frame)
        barra.pack(fill="x", pady=6, padx=6)
        ttk.Button(barra, text="➕ Agregar producto", command=self._agregar_producto).pack(side="left", padx=3)
        ttk.Button(barra, text="✏️ Editar seleccionado", command=self._editar_producto).pack(side="left", padx=3)
        ttk.Button(barra, text="📦 Ajustar stock", command=self._ajustar_stock).pack(side="left", padx=3)
        ttk.Button(barra, text="🗑️ Eliminar", command=self._eliminar_producto).pack(side="left", padx=3)
        ttk.Button(barra, text="🔄 Refrescar", command=self._refrescar_productos).pack(side="left", padx=3)

        columnas = ("id", "nombre", "categoria", "precio_usd", "stock", "stock_minimo")
        self.tree_productos = ttk.Treeview(frame, columns=columnas, show="headings", height=15)
        titulos = {
            "id": "ID", "nombre": "Nombre", "categoria": "Categoría",
            "precio_usd": "Precio $", "stock": "Stock", "stock_minimo": "Stock mín."
        }
        for c in columnas:
            self.tree_productos.heading(c, text=titulos[c])
            self.tree_productos.column(c, width=130 if c == "nombre" else 90, anchor="center")
        self.tree_productos.column("nombre", anchor="w")
        self.tree_productos.pack(expand=True, fill="both", padx=6, pady=6)
        self.tree_productos.tag_configure("bajo_stock", background="#ffe0e0")

        self._refrescar_productos()

    def _refrescar_productos(self):
        for row in self.tree_productos.get_children():
            self.tree_productos.delete(row)
        for p in db.listar_productos(self.conn):
            tag = "bajo_stock" if p["stock"] <= p["stock_minimo"] else ""
            self.tree_productos.insert(
                "", "end", iid=p["id"],
                values=(p["id"], p["nombre"], p["categoria"] or "-", f"{p['precio_usd']:.2f}",
                        p["stock"], p["stock_minimo"]),
                tags=(tag,)
            )

    def _obtener_producto_seleccionado(self):
        sel = self.tree_productos.selection()
        if not sel:
            messagebox.showinfo("Selecciona un producto", "Primero selecciona un producto de la lista.")
            return None
        return int(sel[0])

    def _agregar_producto(self):
        DialogoProducto(self, self.conn, usuario_id=self.usuario_row["id"], on_guardado=self._refrescar_productos)

    def _editar_producto(self):
        pid = self._obtener_producto_seleccionado()
        if pid is None:
            return
        producto = db.obtener_producto(self.conn, pid)
        DialogoProducto(self, self.conn, producto=producto, usuario_id=self.usuario_row["id"],
                         on_guardado=self._refrescar_productos)

    def _ajustar_stock(self):
        pid = self._obtener_producto_seleccionado()
        if pid is None:
            return
        producto = db.obtener_producto(self.conn, pid)
        delta = simpledialog.askinteger(
            "Ajustar stock",
            f"Stock actual de '{producto['nombre']}': {producto['stock']}\n"
            "Ingresa cuánto quieres sumar (positivo) o restar (negativo):",
            parent=self
        )
        if delta:
            db.ajustar_stock(self.conn, pid, delta, usuario_id=self.usuario_row["id"])
            self._refrescar_productos()

    def _eliminar_producto(self):
        pid = self._obtener_producto_seleccionado()
        if pid is None:
            return
        producto = db.obtener_producto(self.conn, pid)
        if messagebox.askyesno("Confirmar", f"¿Eliminar '{producto['nombre']}' del catálogo?"):
            db.eliminar_producto(self.conn, pid, usuario_id=self.usuario_row["id"])
            self._refrescar_productos()

    def _alertar_stock_bajo_inicio(self):
        bajos = db.productos_bajo_stock(self.conn)
        if bajos:
            nombres = "\n".join(f"• {p['nombre']} (quedan {p['stock']})" for p in bajos)
            messagebox.showwarning(
                "Alerta de inventario bajo",
                f"Los siguientes productos están por agotarse:\n\n{nombres}"
            )

    # ------------------------------------------------------- REPORTES

    def _construir_tab_reportes(self):
        frame = self.tab_reportes

        barra = tk.Frame(frame)
        barra.pack(fill="x", pady=8, padx=6)
        ttk.Button(barra, text="Ventas de HOY", command=lambda: self._generar_reporte("dia")).pack(side="left", padx=3)
        ttk.Button(barra, text="Ventas de la SEMANA", command=lambda: self._generar_reporte("semana")).pack(side="left", padx=3)
        ttk.Button(barra, text="Ventas del MES", command=lambda: self._generar_reporte("mes")).pack(side="left", padx=3)

        barra2 = tk.Frame(frame)
        barra2.pack(fill="x", pady=(0, 8), padx=6)
        ttk.Button(barra2, text="📝 Generar registro diario", command=self._generar_registro_diario).pack(side="left", padx=3)
        ttk.Button(barra2, text="🗄️ Respaldar base de datos", command=self._crear_backup).pack(side="left", padx=3)

        self.lbl_resumen = tk.Label(frame, text="Selecciona un rango para ver el resumen.", font=("Segoe UI", 10, "bold"))
        self.lbl_resumen.pack(pady=6)

        tk.Label(frame, text="Productos más vendidos en el rango:").pack(anchor="w", padx=8)
        columnas = ("producto", "unidades", "total_usd")
        self.tree_top = ttk.Treeview(frame, columns=columnas, show="headings", height=10)
        self.tree_top.heading("producto", text="Producto")
        self.tree_top.heading("unidades", text="Unidades vendidas")
        self.tree_top.heading("total_usd", text="Total $")
        self.tree_top.column("producto", width=250, anchor="w")
        self.tree_top.column("unidades", width=140, anchor="center")
        self.tree_top.column("total_usd", width=120, anchor="center")
        self.tree_top.pack(expand=True, fill="both", padx=8, pady=8)

    def _generar_reporte(self, rango):
        ahora = datetime.now()
        if rango == "dia":
            inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        elif rango == "semana":
            inicio = ahora - timedelta(days=ahora.weekday())
            inicio = inicio.replace(hour=0, minute=0, second=0, microsecond=0)
        else:  # mes
            inicio = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        ventas = db.ventas_entre_fechas(self.conn, inicio.isoformat(), ahora.isoformat())
        total_usd = sum(v["total_usd"] for v in ventas)
        total_bs = sum(v["total_bs"] for v in ventas)
        cantidad = len(ventas)

        self.lbl_resumen.config(
            text=f"Transacciones: {cantidad}   |   Total: ${total_usd:.2f}   |   Total: Bs {total_bs:.2f}"
        )

        for row in self.tree_top.get_children():
            self.tree_top.delete(row)
        for p in db.productos_mas_vendidos(self.conn, inicio.isoformat(), ahora.isoformat()):
            self.tree_top.insert(
                "", "end",
                values=(p["nombre_producto"], p["unidades"], f"{p['total_usd']:.2f}")
            )

    def _generar_registro_diario(self):
        ruta = backup.generar_registro_diario(self.conn)
        messagebox.showinfo("Registro generado", f"Registro diario guardado en:\n{ruta}")

    def _crear_backup(self):
        ruta = backup.crear_backup_db()
        messagebox.showinfo("Backup creado", f"Respaldo de la base de datos guardado en:\n{ruta}")

    # ------------------------------------------------------- TASA BCV

    def _construir_tab_tasa(self):
        frame = self.tab_tasa
        sub_tabs = ttk.Notebook(frame)
        sub_tabs.pack(expand=True, fill="both", padx=6, pady=6)

        self.sub_tab_usd = tk.Frame(sub_tabs)
        self.sub_tab_eur = tk.Frame(sub_tabs)
        self.sub_tab_manual = tk.Frame(sub_tabs)

        sub_tabs.add(self.sub_tab_usd, text="Dólar BCV")
        sub_tabs.add(self.sub_tab_eur, text="Euro BCV")
        sub_tabs.add(self.sub_tab_manual, text="Dólar Manual")

        # --- Sub-pestaña Dólar BCV ---
        c1 = tk.Frame(self.sub_tab_usd)
        c1.pack(pady=25)
        self.lbl_usd_valor = tk.Label(c1, text="-- Bs/$", font=("Segoe UI", 18, "bold"))
        self.lbl_usd_valor.pack(pady=8)
        self.lbl_usd_fecha = tk.Label(c1, text="")
        self.lbl_usd_fecha.pack(pady=4)
        ttk.Button(c1, text="🔄 Actualizar desde internet", command=self._actualizar_usd).pack(pady=8)
        self.btn_usar_usd = ttk.Button(c1, text="✅ Usar esta tasa para cobrar", command=self._usar_usd_para_ventas)
        self.btn_usar_usd.pack(pady=8)

        # --- Sub-pestaña Euro BCV ---
        c2 = tk.Frame(self.sub_tab_eur)
        c2.pack(pady=25)
        self.lbl_eur_valor = tk.Label(c2, text="-- Bs/€", font=("Segoe UI", 18, "bold"))
        self.lbl_eur_valor.pack(pady=8)
        self.lbl_eur_fecha = tk.Label(c2, text="")
        self.lbl_eur_fecha.pack(pady=4)
        ttk.Button(c2, text="🔄 Actualizar desde internet", command=self._actualizar_eur).pack(pady=8)
        tk.Label(c2, text="(Informativa: el euro no se usa para calcular las ventas)",
                 font=("Segoe UI", 8), fg="#666").pack(pady=4)

        # --- Sub-pestaña Manual ---
        c3 = tk.Frame(self.sub_tab_manual)
        c3.pack(pady=25)
        self.lbl_manual_valor = tk.Label(c3, text="-- Bs/$", font=("Segoe UI", 18, "bold"))
        self.lbl_manual_valor.pack(pady=8)
        self.lbl_manual_fecha = tk.Label(c3, text="")
        self.lbl_manual_fecha.pack(pady=4)

        manual_frame = tk.Frame(c3)
        manual_frame.pack(pady=10)
        tk.Label(manual_frame, text="Nueva tasa manual:").pack(side="left", padx=5)
        self.entry_tasa_manual = ttk.Entry(manual_frame, width=10)
        self.entry_tasa_manual.pack(side="left", padx=5)
        ttk.Button(manual_frame, text="Guardar", command=self._guardar_tasa_manual).pack(side="left", padx=5)

        self.btn_usar_manual = ttk.Button(c3, text="✅ Usar esta tasa para cobrar", command=self._usar_manual_para_ventas)
        self.btn_usar_manual.pack(pady=8)

        self._refrescar_tasas_tab()

    def _refrescar_tasas_tab(self):
        usd, usd_fecha = bcv.get_tasa_bcv_usd(self.conn)
        eur, eur_fecha = bcv.get_tasa_bcv_eur(self.conn)
        manual, manual_fecha = bcv.get_tasa_manual(self.conn)
        activa = bcv.get_tasa_para_ventas_nombre(self.conn)

        self.lbl_usd_valor.config(text=f"{usd:,.2f} Bs/$")
        self.lbl_usd_fecha.config(text=f"Última actualización: {usd_fecha or 'nunca'}")
        self.lbl_eur_valor.config(text=f"{eur:,.2f} Bs/€")
        self.lbl_eur_fecha.config(text=f"Última actualización: {eur_fecha or 'nunca'}")
        self.lbl_manual_valor.config(text=f"{manual:,.2f} Bs/$")
        self.lbl_manual_fecha.config(text=f"Última actualización: {manual_fecha or 'nunca'}")

        self.btn_usar_usd.config(text="✅ Usando esta para cobrar" if activa == "bcv_usd" else "Usar esta tasa para cobrar")
        self.btn_usar_manual.config(text="✅ Usando esta para cobrar" if activa == "manual" else "Usar esta tasa para cobrar")

        self.barra_tasas.actualizar_valores()

    def _actualizar_usd(self):
        valor, error = bcv.actualizar_bcv_usd(self.conn)
        if error:
            messagebox.showerror("Error al actualizar", error)
        else:
            messagebox.showinfo("Tasa actualizada", f"Nueva tasa BCV Dólar: {valor:.2f} Bs")
        self._refrescar_tasas_tab()

    def _actualizar_eur(self):
        valor, error = bcv.actualizar_bcv_eur(self.conn)
        if error:
            messagebox.showerror("Error al actualizar", error)
        else:
            messagebox.showinfo("Tasa actualizada", f"Nueva tasa BCV Euro: {valor:.2f} Bs")
        self._refrescar_tasas_tab()

    def _guardar_tasa_manual(self):
        texto = self.entry_tasa_manual.get().strip().replace(",", ".")
        try:
            valor = float(texto)
            if valor <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Valor inválido", "Ingresa un número mayor a 0.")
            return
        bcv.fijar_tasa_manual(self.conn, valor)
        self.entry_tasa_manual.delete(0, tk.END)
        self._refrescar_tasas_tab()

    def _usar_usd_para_ventas(self):
        bcv.set_tasa_para_ventas(self.conn, "bcv_usd")
        self._refrescar_tasas_tab()

    def _usar_manual_para_ventas(self):
        bcv.set_tasa_para_ventas(self.conn, "manual")
        self._refrescar_tasas_tab()

    # ------------------------------------------------------- USUARIOS

    def _construir_tab_usuarios(self):
        frame = self.tab_usuarios
        barra = tk.Frame(frame)
        barra.pack(fill="x", pady=8, padx=6)
        ttk.Button(barra, text="➕ Crear usuario", command=self._crear_usuario).pack(side="left", padx=3)
        ttk.Button(barra, text="🔑 Cambiar contraseña", command=self._cambiar_password_usuario).pack(side="left", padx=3)
        ttk.Button(barra, text="🗑️ Desactivar", command=self._desactivar_usuario).pack(side="left", padx=3)
        ttk.Button(barra, text="🔄 Refrescar", command=self._refrescar_usuarios).pack(side="left", padx=3)

        columnas = ("id", "nombre", "usuario", "rol", "activo")
        self.tree_usuarios = ttk.Treeview(frame, columns=columnas, show="headings", height=15)
        for c, t in zip(columnas, ("ID", "Nombre", "Usuario", "Rol", "Activo")):
            self.tree_usuarios.heading(c, text=t)
            self.tree_usuarios.column(c, width=130, anchor="center")
        self.tree_usuarios.pack(expand=True, fill="both", padx=6, pady=6)

        self._refrescar_usuarios()

    def _refrescar_usuarios(self):
        for row in self.tree_usuarios.get_children():
            self.tree_usuarios.delete(row)
        for u in db.listar_usuarios(self.conn):
            self.tree_usuarios.insert(
                "", "end", iid=u["id"],
                values=(u["id"], f"{u['nombre']} {u['apellido'] or ''}", u["usuario"],
                        u["rol"], "Sí" if u["activo"] else "No")
            )

    def _crear_usuario(self):
        DialogoUsuario(self, self.conn, on_guardado=self._refrescar_usuarios)

    def _cambiar_password_usuario(self):
        sel = self.tree_usuarios.selection()
        if not sel:
            messagebox.showinfo("Selecciona un usuario", "Primero selecciona un usuario.")
            return
        nueva = simpledialog.askstring("Cambiar contraseña", "Nueva contraseña:", show="*", parent=self)
        if nueva:
            db.cambiar_password(self.conn, int(sel[0]), nueva)
            messagebox.showinfo("Listo", "Contraseña actualizada.")

    def _desactivar_usuario(self):
        sel = self.tree_usuarios.selection()
        if not sel:
            messagebox.showinfo("Selecciona un usuario", "Primero selecciona un usuario.")
            return
        uid = int(sel[0])
        if uid == self.usuario_row["id"]:
            messagebox.showerror("No permitido", "No puedes desactivar tu propio usuario.")
            return
        if messagebox.askyesno("Confirmar", "¿Desactivar este usuario?"):
            db.eliminar_usuario(self.conn, uid, realizado_por=self.usuario_row["id"])
            self._refrescar_usuarios()

    # ------------------------------------------------------------ salir

    def _cerrar(self):
        if messagebox.askyesno("Cerrar sesión", "¿Confirmas cerrar la sesión de administrador?"):
            self.conn.close()
            self.destroy()


class DialogoProducto(tk.Toplevel):
    def __init__(self, parent, conn, producto=None, usuario_id=None, on_guardado=None):
        super().__init__(parent)
        self.conn = conn
        self.producto = producto
        self.usuario_id = usuario_id
        self.on_guardado = on_guardado
        self.title("Editar producto" if producto else "Agregar producto")
        self.geometry("340x380")
        self.resizable(True, True)
        self.minsize(320, 340)
        self.grab_set()

        campos = [("Nombre", "nombre"), ("Categoría", "categoria"),
                  ("Precio USD", "precio_usd"), ("Stock mínimo", "stock_minimo")]
        if not producto:
            campos.insert(3, ("Stock inicial", "stock"))

        self.entradas = {}
        for etiqueta, clave in campos:
            tk.Label(self, text=etiqueta).pack(anchor="w", padx=15, pady=(8, 0))
            e = ttk.Entry(self, width=30)
            e.pack(padx=15)
            self.entradas[clave] = e

        if producto:
            self.entradas["nombre"].insert(0, producto["nombre"])
            self.entradas["categoria"].insert(0, producto["categoria"] or "")
            self.entradas["precio_usd"].insert(0, str(producto["precio_usd"]))
            self.entradas["stock_minimo"].insert(0, str(producto["stock_minimo"]))

        ttk.Button(self, text="Guardar", command=self._guardar).pack(pady=15)

    def _guardar(self):
        try:
            nombre = self.entradas["nombre"].get().strip()
            categoria = self.entradas["categoria"].get().strip()
            precio = float(self.entradas["precio_usd"].get().replace(",", "."))
            stock_minimo = int(self.entradas["stock_minimo"].get())
            if not nombre or precio < 0 or stock_minimo < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Datos inválidos", "Revisa los campos: nombre, precio y stock mínimo.")
            return

        if self.producto:
            db.editar_producto(self.conn, self.producto["id"], nombre, categoria, precio, stock_minimo,
                                usuario_id=self.usuario_id)
        else:
            try:
                stock_inicial = int(self.entradas["stock"].get())
            except ValueError:
                stock_inicial = 0
            db.agregar_producto(self.conn, nombre, categoria, precio, stock_inicial, stock_minimo,
                                 usuario_id=self.usuario_id)

        if self.on_guardado:
            self.on_guardado()
        self.destroy()


class DialogoUsuario(tk.Toplevel):
    def __init__(self, parent, conn, on_guardado=None):
        super().__init__(parent)
        self.conn = conn
        self.on_guardado = on_guardado
        self.title("Crear usuario")
        self.geometry("340x440")
        self.resizable(True, True)
        self.minsize(320, 400)
        self.grab_set()

        campos = [("Nombre", "nombre"), ("Apellido", "apellido"), ("Email", "email"),
                  ("Usuario (login)", "usuario"), ("Contraseña", "password")]
        self.entradas = {}
        for etiqueta, clave in campos:
            tk.Label(self, text=etiqueta).pack(anchor="w", padx=15, pady=(6, 0))
            show = "*" if clave == "password" else ""
            e = ttk.Entry(self, width=30, show=show)
            e.pack(padx=15)
            self.entradas[clave] = e

        tk.Label(self, text="Rol").pack(anchor="w", padx=15, pady=(6, 0))
        self.combo_rol = ttk.Combobox(self, values=["cajero", "admin"], state="readonly", width=27)
        self.combo_rol.current(0)
        self.combo_rol.pack(padx=15)

        ttk.Button(self, text="Crear", command=self._guardar).pack(pady=15)

    def _guardar(self):
        nombre = self.entradas["nombre"].get().strip()
        usuario = self.entradas["usuario"].get().strip()
        password = self.entradas["password"].get()

        if not nombre or not usuario or not password:
            messagebox.showerror("Datos incompletos", "Nombre, usuario y contraseña son obligatorios.")
            return

        if db.obtener_usuario_por_login(self.conn, usuario):
            messagebox.showerror("Usuario repetido", "Ese nombre de usuario ya existe.")
            return

        db.crear_usuario(
            self.conn,
            nombre,
            self.entradas["apellido"].get().strip(),
            self.entradas["email"].get().strip(),
            usuario,
            password,
            self.combo_rol.get()
        )
        if self.on_guardado:
            self.on_guardado()
        self.destroy()
