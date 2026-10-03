import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

import database as db
import bcv
import ticket
from ui.widgets import BarraTasas


class CashierWindow(tk.Tk):
    FORMAS_PAGO = ["Efectivo $", "Efectivo Bs", "Pago Móvil", "Transferencia",
                   "Punto de venta", "Zelle", "Binance/USDT"]

    def __init__(self, usuario_row):
        super().__init__()
        self.usuario_row = usuario_row
        self.title(f"Punto de venta — Cajero: {usuario_row['nombre']}")
        self.geometry("1000x600")

        self.conn = db.get_connection()
        self.carrito = []  # lista de dicts: producto_id, nombre, cantidad, precio_unitario_usd
        self.cliente_seleccionado = None  # row de clientes o None (consumidor final)

        self._construir_menu()
        self.barra_tasas = BarraTasas(self, self.conn)
        self.barra_tasas.pack(fill="x")
        self._construir_layout()
        self._alertar_stock_bajo_inicio()

        self.protocol("WM_DELETE_WINDOW", self._cerrar)

    # ------------------------------------------------------------ layout

    def _construir_menu(self):
        top = tk.Frame(self, bg="#2f3b4c")
        top.pack(fill="x")
        tk.Label(
            top, text=f"Sesión: {self.usuario_row['nombre']} {self.usuario_row['apellido'] or ''} (Cajero)",
            bg="#2f3b4c", fg="white", padx=10, pady=6
        ).pack(side="left")
        ttk.Button(top, text="Cerrar sesión", command=self._cerrar).pack(side="right", padx=10, pady=5)

    def _construir_layout(self):
        contenedor = tk.Frame(self)
        contenedor.pack(expand=True, fill="both", padx=8, pady=8)

        # ---------- panel izquierdo: catálogo ----------
        panel_izq = tk.Frame(contenedor)
        panel_izq.pack(side="left", expand=True, fill="both", padx=(0, 6))

        buscar_frame = tk.Frame(panel_izq)
        buscar_frame.pack(fill="x")
        tk.Label(buscar_frame, text="Buscar producto:").pack(side="left")
        self.entry_buscar = ttk.Entry(buscar_frame)
        self.entry_buscar.pack(side="left", expand=True, fill="x", padx=5)
        self.entry_buscar.bind("<KeyRelease>", lambda e: self._filtrar_productos())

        columnas = ("id", "nombre", "precio_usd", "stock")
        self.tree_catalogo = ttk.Treeview(panel_izq, columns=columnas, show="headings", height=18)
        for c, t, w in zip(columnas, ("ID", "Producto", "Precio $", "Stock"), (40, 220, 90, 70)):
            self.tree_catalogo.heading(c, text=t)
            self.tree_catalogo.column(c, width=w, anchor="center")
        self.tree_catalogo.column("nombre", anchor="w")
        self.tree_catalogo.pack(expand=True, fill="both", pady=6)
        self.tree_catalogo.bind("<Double-1>", lambda e: self._agregar_al_carrito())

        ttk.Button(panel_izq, text="➕ Agregar al carrito", command=self._agregar_al_carrito).pack(fill="x")

        # ---------- panel derecho: carrito y cobro ----------
        panel_der = tk.Frame(contenedor, width=380)
        panel_der.pack(side="right", fill="both")

        cliente_frame = tk.LabelFrame(panel_der, text="Cliente")
        cliente_frame.pack(fill="x", pady=(0, 8))
        self.lbl_cliente = tk.Label(cliente_frame, text="Consumidor final", font=("Segoe UI", 10, "bold"))
        self.lbl_cliente.pack(side="left", padx=8, pady=6)
        ttk.Button(cliente_frame, text="Buscar / Registrar", command=self._abrir_cliente).pack(side="right", padx=6)
        ttk.Button(cliente_frame, text="Quitar", command=self._quitar_cliente).pack(side="right")

        tk.Label(panel_der, text="Carrito de venta", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        columnas_carrito = ("nombre", "cantidad", "precio", "subtotal")
        self.tree_carrito = ttk.Treeview(panel_der, columns=columnas_carrito, show="headings", height=10)
        for c, t, w in zip(columnas_carrito, ("Producto", "Cant.", "P/U $", "Subt. $"), (150, 50, 70, 80)):
            self.tree_carrito.heading(c, text=t)
            self.tree_carrito.column(c, width=w, anchor="center")
        self.tree_carrito.column("nombre", anchor="w")
        self.tree_carrito.pack(fill="both", pady=6)

        botones_carrito = tk.Frame(panel_der)
        botones_carrito.pack(fill="x")
        ttk.Button(botones_carrito, text="➖ Quitar seleccionado", command=self._quitar_del_carrito).pack(side="left")
        ttk.Button(botones_carrito, text="🗑️ Vaciar carrito", command=self._vaciar_carrito).pack(side="right")

        totales_frame = tk.Frame(panel_der)
        totales_frame.pack(fill="x", pady=10)
        self.lbl_total_usd = tk.Label(totales_frame, text="Total: $0.00", font=("Segoe UI", 14, "bold"))
        self.lbl_total_usd.pack(anchor="e")
        self.lbl_total_bs = tk.Label(totales_frame, text="Total: Bs 0.00", font=("Segoe UI", 12))
        self.lbl_total_bs.pack(anchor="e")

        tk.Label(panel_der, text="Forma de pago:").pack(anchor="w")
        self.combo_pago = ttk.Combobox(panel_der, values=self.FORMAS_PAGO, state="readonly")
        self.combo_pago.current(0)
        self.combo_pago.pack(fill="x", pady=(0, 10))

        ttk.Button(panel_der, text="💰 COBRAR", command=self._cobrar).pack(fill="x", ipady=8)

        self._refrescar_catalogo()

    # --------------------------------------------------------- catálogo

    def _refrescar_catalogo(self, filtro=""):
        for row in self.tree_catalogo.get_children():
            self.tree_catalogo.delete(row)
        for p in db.listar_productos(self.conn):
            if filtro and filtro.lower() not in p["nombre"].lower():
                continue
            self.tree_catalogo.insert(
                "", "end", iid=p["id"],
                values=(p["id"], p["nombre"], f"{p['precio_usd']:.2f}", p["stock"])
            )

    def _filtrar_productos(self):
        self._refrescar_catalogo(self.entry_buscar.get().strip())

    def _alertar_stock_bajo_inicio(self):
        bajos = db.productos_bajo_stock(self.conn)
        if bajos:
            nombres = "\n".join(f"• {p['nombre']} (quedan {p['stock']})" for p in bajos)
            messagebox.showwarning(
                "Alerta de inventario bajo",
                f"Los siguientes productos están por agotarse:\n\n{nombres}"
            )

    # ----------------------------------------------------------- carrito

    def _agregar_al_carrito(self):
        sel = self.tree_catalogo.selection()
        if not sel:
            messagebox.showinfo("Selecciona un producto", "Haz doble clic o selecciona un producto de la lista.")
            return
        pid = int(sel[0])
        producto = db.obtener_producto(self.conn, pid)

        cantidad = simpledialog.askinteger(
            "Cantidad", f"¿Cuántas unidades de '{producto['nombre']}'?",
            minvalue=1, initialvalue=1, parent=self
        )
        if not cantidad:
            return

        ya_en_carrito = sum(i["cantidad"] for i in self.carrito if i["producto_id"] == pid)
        if cantidad + ya_en_carrito > producto["stock"]:
            messagebox.showerror(
                "Stock insuficiente",
                f"Solo hay {producto['stock']} unidades disponibles de '{producto['nombre']}'."
            )
            return

        for item in self.carrito:
            if item["producto_id"] == pid:
                item["cantidad"] += cantidad
                break
        else:
            self.carrito.append({
                "producto_id": pid,
                "nombre": producto["nombre"],
                "cantidad": cantidad,
                "precio_unitario_usd": producto["precio_usd"],
            })

        self._refrescar_carrito()

    def _quitar_del_carrito(self):
        sel = self.tree_carrito.selection()
        if not sel:
            return
        idx = int(sel[0])
        del self.carrito[idx]
        self._refrescar_carrito()

    def _vaciar_carrito(self):
        self.carrito = []
        self._refrescar_carrito()

    def _refrescar_carrito(self):
        for row in self.tree_carrito.get_children():
            self.tree_carrito.delete(row)
        total_usd = 0
        for idx, item in enumerate(self.carrito):
            subtotal = item["cantidad"] * item["precio_unitario_usd"]
            total_usd += subtotal
            self.tree_carrito.insert(
                "", "end", iid=str(idx),
                values=(item["nombre"], item["cantidad"], f"{item['precio_unitario_usd']:.2f}", f"{subtotal:.2f}")
            )

        tasa, etiqueta = bcv.obtener_tasa_activa(self.conn)
        total_bs = total_usd * tasa
        self.lbl_total_usd.config(text=f"Total: ${total_usd:.2f}")
        self.lbl_total_bs.config(text=f"Total: Bs {total_bs:,.2f}  (tasa {etiqueta}: {tasa:.2f})")

    # ----------------------------------------------------------- cliente

    def _abrir_cliente(self):
        DialogoCliente(self, self.conn, on_seleccionado=self._set_cliente)

    def _set_cliente(self, cliente_row):
        self.cliente_seleccionado = cliente_row
        etiqueta = "Frecuente" if cliente_row["frecuente"] else "Nuevo"
        self.lbl_cliente.config(text=f"{cliente_row['nombre']} ({etiqueta})")

    def _quitar_cliente(self):
        self.cliente_seleccionado = None
        self.lbl_cliente.config(text="Consumidor final")

    # ------------------------------------------------------------ cobro

    def _cobrar(self):
        if not self.carrito:
            messagebox.showinfo("Carrito vacío", "Agrega al menos un producto antes de cobrar.")
            return

        tasa, etiqueta = bcv.obtener_tasa_activa(self.conn)
        if tasa <= 0:
            messagebox.showerror(
                "Falta la tasa",
                "La tasa activa para cobrar es 0. Pide al administrador que la actualice o la fije."
            )
            return

        forma_pago = self.combo_pago.get()
        cliente_id = self.cliente_seleccionado["id"] if self.cliente_seleccionado else None
        cliente_nombre = self.cliente_seleccionado["nombre"] if self.cliente_seleccionado else "Consumidor final"

        total_usd = sum(i["cantidad"] * i["precio_unitario_usd"] for i in self.carrito)
        if not messagebox.askyesno(
            "Confirmar cobro",
            f"Cliente: {cliente_nombre}\nTotal: ${total_usd:.2f}  (Bs {total_usd * tasa:,.2f})\n"
            f"Forma de pago: {forma_pago}\n\n¿Confirmar la venta?"
        ):
            return

        venta_id = db.registrar_venta(
            self.conn, cliente_id, self.usuario_row["id"], self.carrito, tasa, forma_pago
        )

        venta_row = db.obtener_venta(self.conn, venta_id)
        detalle_rows = db.obtener_detalle_venta(self.conn, venta_id)
        texto_ticket = ticket.generar_texto_ticket(
            venta_row, detalle_rows, cliente_nombre, self.usuario_row["nombre"]
        )
        ruta = ticket.guardar_ticket(texto_ticket, venta_id)

        self._mostrar_ticket(texto_ticket, ruta)

        self.carrito = []
        self.cliente_seleccionado = None
        self.lbl_cliente.config(text="Consumidor final")
        self._refrescar_carrito()
        self._refrescar_catalogo(self.entry_buscar.get().strip())

    def _mostrar_ticket(self, texto, ruta):
        ventana = tk.Toplevel(self)
        ventana.title("Ticket de venta")
        ventana.geometry("340x480")
        texto_widget = tk.Text(ventana, font=("Consolas", 10))
        texto_widget.insert("1.0", texto)
        texto_widget.config(state="disabled")
        texto_widget.pack(expand=True, fill="both", padx=8, pady=8)
        tk.Label(ventana, text=f"Guardado en: {ruta}", font=("Segoe UI", 8), fg="#666").pack(pady=(0, 6))
        ttk.Button(ventana, text="Cerrar", command=ventana.destroy).pack(pady=(0, 8))

    # ------------------------------------------------------------ salir

    def _cerrar(self):
        if messagebox.askyesno("Cerrar sesión", "¿Confirmas cerrar la sesión de cajero?"):
            self.conn.close()
            self.destroy()


class DialogoCliente(tk.Toplevel):
    def __init__(self, parent, conn, on_seleccionado=None):
        super().__init__(parent)
        self.conn = conn
        self.on_seleccionado = on_seleccionado
        self.title("Buscar / Registrar cliente")
        self.geometry("380x560")
        self.resizable(True, True)
        self.minsize(360, 480)
        self.grab_set()

        tk.Label(self, text="Buscar por nombre o cédula:").pack(anchor="w", padx=15, pady=(10, 0))
        buscar_frame = tk.Frame(self)
        buscar_frame.pack(fill="x", padx=15)
        self.entry_buscar = ttk.Entry(buscar_frame)
        self.entry_buscar.pack(side="left", expand=True, fill="x")
        ttk.Button(buscar_frame, text="Buscar", command=self._buscar).pack(side="left", padx=5)

        self.lista = tk.Listbox(self, height=6)
        self.lista.pack(fill="x", padx=15, pady=8)
        self.lista.bind("<Double-1>", lambda e: self._seleccionar_de_lista())
        self._resultados = []

        ttk.Button(self, text="Seleccionar", command=self._seleccionar_de_lista).pack(pady=(0, 10))

        tk.Label(self, text="— o registrar cliente nuevo —", fg="#666").pack(pady=(5, 5))

        tk.Label(self, text="Nombre").pack(anchor="w", padx=15)
        self.entry_nombre = ttk.Entry(self, width=35)
        self.entry_nombre.pack(padx=15)

        tk.Label(self, text="Teléfono").pack(anchor="w", padx=15, pady=(6, 0))
        self.entry_telefono = ttk.Entry(self, width=35)
        self.entry_telefono.pack(padx=15)

        tk.Label(self, text="Cédula").pack(anchor="w", padx=15, pady=(6, 0))
        self.entry_cedula = ttk.Entry(self, width=35)
        self.entry_cedula.pack(padx=15)

        self.var_frecuente = tk.BooleanVar(value=False)
        tk.Checkbutton(
            self, text="Cliente frecuente (solo requiere nombre)", variable=self.var_frecuente
        ).pack(anchor="w", padx=15, pady=6)

        ttk.Button(self, text="Registrar y usar", command=self._registrar).pack(pady=8)

    def _buscar(self):
        texto = self.entry_buscar.get().strip()
        self.lista.delete(0, tk.END)
        self._resultados = list(db.buscar_clientes_por_nombre(self.conn, texto)) if texto else []
        cliente_cedula = db.buscar_cliente_por_cedula(self.conn, texto)
        if cliente_cedula and cliente_cedula not in self._resultados:
            self._resultados.append(cliente_cedula)
        for c in self._resultados:
            etiqueta = "Frecuente" if c["frecuente"] else "Nuevo"
            self.lista.insert(tk.END, f"{c['nombre']} — {c['cedula'] or 's/cédula'} ({etiqueta})")

    def _seleccionar_de_lista(self):
        sel = self.lista.curselection()
        if not sel:
            return
        cliente = self._resultados[sel[0]]
        if self.on_seleccionado:
            self.on_seleccionado(cliente)
        self.destroy()

    def _registrar(self):
        nombre = self.entry_nombre.get().strip()
        frecuente = self.var_frecuente.get()

        if not nombre:
            messagebox.showerror("Falta el nombre", "El nombre del cliente es obligatorio.")
            return

        telefono = self.entry_telefono.get().strip()
        cedula = self.entry_cedula.get().strip()

        if not frecuente and (not telefono or not cedula):
            messagebox.showerror(
                "Datos incompletos",
                "Un cliente nuevo requiere teléfono y cédula.\n"
                "Si no los tienes a mano, marca la casilla de 'Cliente frecuente'."
            )
            return

        cedula = cedula or None
        if cedula and db.buscar_cliente_por_cedula(self.conn, cedula):
            messagebox.showerror("Cédula repetida", "Ya existe un cliente registrado con esa cédula.")
            return

        db.registrar_cliente(self.conn, nombre, telefono or None, cedula, frecuente)
        nuevo = db.buscar_cliente_por_cedula(self.conn, cedula) if cedula else \
            db.buscar_clientes_por_nombre(self.conn, nombre)[-1]

        if self.on_seleccionado:
            self.on_seleccionado(nuevo)
        self.destroy()
