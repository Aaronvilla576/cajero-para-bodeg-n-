import tkinter as tk
from tkinter import ttk, messagebox

import database as db
import auth


class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Bodegón - Iniciar sesión")
        self.geometry("380x320")
        self.resizable(False, False)
        self.usuario_autenticado = None  # se llena si el login es exitoso

        self.configure(bg="#1f2933")
        self._construir_ui()
        self.protocol("WM_DELETE_WINDOW", self._salir)

    def _construir_ui(self):
        marco = tk.Frame(self, bg="#1f2933")
        marco.pack(expand=True, fill="both", padx=30, pady=30)

        tk.Label(
            marco, text="🏪 Sistema de Ventas — Bodegón",
            font=("Segoe UI", 13, "bold"), bg="#1f2933", fg="white",
            wraplength=300, justify="center"
        ).pack(pady=(0, 20))

        tk.Label(marco, text="Usuario", bg="#1f2933", fg="white").pack(anchor="w")
        self.entry_usuario = ttk.Entry(marco, width=30)
        self.entry_usuario.pack(pady=(0, 10))
        self.entry_usuario.focus()

        tk.Label(marco, text="Contraseña", bg="#1f2933", fg="white").pack(anchor="w")
        self.entry_password = ttk.Entry(marco, width=30, show="*")
        self.entry_password.pack(pady=(0, 15))

        self.btn_login = ttk.Button(marco, text="Ingresar", command=self._on_login)
        self.btn_login.pack(pady=5, fill="x")

        self.lbl_mensaje = tk.Label(
            marco, text="", bg="#1f2933", fg="#ff6b6b", wraplength=300, justify="center"
        )
        self.lbl_mensaje.pack(pady=10)

        self.bind("<Return>", lambda e: self._on_login())

        tk.Label(
            marco, text="Usuarios de prueba:\nadmin / admin123   |   cajero / cajero123",
            bg="#1f2933", fg="#9aa5b1", font=("Segoe UI", 8), justify="center"
        ).pack(side="bottom", pady=(10, 0))

    def _on_login(self):
        usuario = self.entry_usuario.get().strip()
        password = self.entry_password.get()

        if not usuario or not password:
            self.lbl_mensaje.config(text="Ingresa usuario y contraseña.")
            return

        conn = db.get_connection()
        try:
            resultado = auth.intentar_login(conn, usuario, password)
        finally:
            conn.close()

        if resultado.ok:
            self.usuario_autenticado = resultado.usuario_row
            self.destroy()
        else:
            self.lbl_mensaje.config(text=resultado.mensaje)
            self.entry_password.delete(0, tk.END)

    def _salir(self):
        self.usuario_autenticado = None
        self.destroy()
