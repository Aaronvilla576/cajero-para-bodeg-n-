"""
auth.py
Lógica de inicio de sesión: verifica usuario/contraseña y aplica el bloqueo
de 3 minutos tras 3 intentos fallidos, tal como especifica el proyecto original.
"""

from datetime import datetime, timedelta
import database as db

MAX_INTENTOS = 3
MINUTOS_BLOQUEO = 3


class ResultadoLogin:
    def __init__(self, ok, mensaje, usuario_row=None, segundos_restantes=0):
        self.ok = ok
        self.mensaje = mensaje
        self.usuario_row = usuario_row
        self.segundos_restantes = segundos_restantes


def intentar_login(conn, usuario, password) -> ResultadoLogin:
    row = db.obtener_usuario_por_login(conn, usuario)

    if row is None or row["activo"] == 0:
        return ResultadoLogin(False, "Usuario o contraseña incorrectos.")

    # ¿Está bloqueado todavía?
    if row["bloqueado_hasta"]:
        bloqueado_hasta = datetime.fromisoformat(row["bloqueado_hasta"])
        if datetime.now() < bloqueado_hasta:
            restante = int((bloqueado_hasta - datetime.now()).total_seconds())
            minutos = restante // 60
            segundos = restante % 60
            return ResultadoLogin(
                False,
                f"Demasiados intentos fallidos. Intenta de nuevo en "
                f"{minutos} min {segundos} s.",
                segundos_restantes=restante
            )
        else:
            # Ya pasó el tiempo de bloqueo, se resetea
            db.resetear_intentos(conn, row["id"])
            row = db.obtener_usuario_por_login(conn, usuario)

    if db.verificar_password(password, row["password_hash"], row["salt"]):
        db.resetear_intentos(conn, row["id"])
        return ResultadoLogin(True, "Bienvenido.", usuario_row=row)

    # Contraseña incorrecta: sumar intento fallido
    intentos = row["intentos_fallidos"] + 1
    bloqueado_hasta = None
    mensaje = "Usuario o contraseña incorrectos."

    if intentos >= MAX_INTENTOS:
        bloqueado_hasta_dt = datetime.now() + timedelta(minutes=MINUTOS_BLOQUEO)
        bloqueado_hasta = bloqueado_hasta_dt.isoformat()
        mensaje = (
            f"Usuario o contraseña incorrectos. Alcanzaste el máximo de intentos, "
            f"espera {MINUTOS_BLOQUEO} minutos para volver a intentarlo."
        )

    db.registrar_intento_fallido(conn, row["id"], intentos, bloqueado_hasta)
    return ResultadoLogin(False, mensaje)
