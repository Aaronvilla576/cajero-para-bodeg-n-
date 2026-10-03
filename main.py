"""
main.py — Punto de entrada del Sistema de Ventas de Bodegón.

Ejecuta:  python main.py

Al primer arranque crea la base de datos (bodegon.db) con dos usuarios de
prueba:
    admin  / admin123   -> Panel de Administrador
    cajero / cajero123  -> Punto de venta (cajero)
"""

import database as db
from ui.login_window import LoginWindow
from ui.admin_window import AdminWindow
from ui.cashier_window import CashierWindow


def main():
    db.init_db()

    while True:
        login = LoginWindow()
        login.mainloop()

        usuario = login.usuario_autenticado
        if usuario is None:
            break  # el usuario cerró la ventana de login sin autenticarse

        if usuario["rol"] == "admin":
            app = AdminWindow(usuario)
        else:
            app = CashierWindow(usuario)

        app.mainloop()
        # al cerrar sesión (o la ventana), volvemos a mostrar el login


if __name__ == "__main__":
    main()
