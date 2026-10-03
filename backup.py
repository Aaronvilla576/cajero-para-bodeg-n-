"""
backup.py
- crear_backup_db(): copia segura del archivo bodegon.db (usa la API de backup
  de sqlite3, así que funciona aunque el programa esté usando la base en ese momento).
- generar_registro_diario(): junta las ventas y movimientos del día en un
  archivo de texto legible, como una bitácora diaria.
"""

import os
import sqlite3
from datetime import datetime

import database as db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUPS_DIR = os.path.join(BASE_DIR, "backups")
REGISTROS_DIR = os.path.join(BASE_DIR, "registros")


def crear_backup_db():
    os.makedirs(BACKUPS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = os.path.join(BACKUPS_DIR, f"bodegon_backup_{timestamp}.db")

    origen_conn = sqlite3.connect(db.DB_PATH)
    destino_conn = sqlite3.connect(destino)
    with destino_conn:
        origen_conn.backup(destino_conn)
    origen_conn.close()
    destino_conn.close()
    return destino


def generar_registro_diario(conn, fecha=None):
    """
    Genera un .txt con el resumen del día: ventas realizadas y todos los
    movimientos registrados (productos, stock, tasas, usuarios).
    """
    fecha = fecha or datetime.now()
    inicio = fecha.replace(hour=0, minute=0, second=0, microsecond=0)
    fin = fecha.replace(hour=23, minute=59, second=59, microsecond=999999)

    ventas = db.ventas_entre_fechas(conn, inicio.isoformat(), fin.isoformat())
    movimientos = db.movimientos_entre_fechas(conn, inicio.isoformat(), fin.isoformat())

    total_usd = sum(v["total_usd"] for v in ventas)
    total_bs = sum(v["total_bs"] for v in ventas)

    lineas = []
    lineas.append("=" * 60)
    lineas.append(f"REGISTRO DIARIO — {fecha.strftime('%d/%m/%Y')}".center(60))
    lineas.append("=" * 60)
    lineas.append("")
    lineas.append(f"Total de ventas: {len(ventas)}")
    lineas.append(f"Total facturado: ${total_usd:.2f}  (Bs {total_bs:.2f})")
    lineas.append("")
    lineas.append("-" * 60)
    lineas.append("VENTAS DEL DÍA")
    lineas.append("-" * 60)
    if ventas:
        for v in ventas:
            hora = datetime.fromisoformat(v["fecha_hora"]).strftime("%I:%M %p")
            lineas.append(
                f"  #{v['id']:<5} {hora:<10} ${v['total_usd']:>8.2f}  "
                f"(Bs {v['total_bs']:>10.2f})  Pago: {v['forma_pago']}"
            )
    else:
        lineas.append("  (sin ventas registradas)")

    lineas.append("")
    lineas.append("-" * 60)
    lineas.append("BITÁCORA DE MOVIMIENTOS")
    lineas.append("-" * 60)
    if movimientos:
        for m in movimientos:
            hora = datetime.fromisoformat(m["fecha_hora"]).strftime("%I:%M %p")
            usuario = m["usuario_nombre"] or "sistema"
            lineas.append(f"  [{hora}] ({m['tipo']}) {m['descripcion']} — {usuario}")
    else:
        lineas.append("  (sin movimientos registrados)")

    lineas.append("")
    lineas.append("=" * 60)

    os.makedirs(REGISTROS_DIR, exist_ok=True)
    nombre_archivo = f"registro_{fecha.strftime('%Y%m%d')}.txt"
    ruta = os.path.join(REGISTROS_DIR, nombre_archivo)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))

    return ruta
