"""
ticket.py
Genera el texto del ticket/factura de una venta y lo guarda como .txt
en la carpeta 'tickets/' (simula la impresión de la factura).
"""

import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TICKETS_DIR = os.path.join(BASE_DIR, "tickets")


def generar_texto_ticket(venta_row, detalle_rows, cliente_nombre, cajero_nombre):
    fecha = datetime.fromisoformat(venta_row["fecha_hora"]).strftime("%d/%m/%Y %I:%M %p")
    ancho = 40
    lineas = []
    lineas.append("BODEGÓN".center(ancho))
    lineas.append("Factura de venta".center(ancho))
    lineas.append("=" * ancho)
    lineas.append(f"Ticket #: {venta_row['id']}")
    lineas.append(f"Fecha:    {fecha}")
    lineas.append(f"Cliente:  {cliente_nombre or 'Consumidor final'}")
    lineas.append(f"Cajero:   {cajero_nombre}")
    lineas.append("-" * ancho)
    lineas.append(f"{'Producto':<20}{'Cant':>4}{'P/U $':>7}{'Subt $':>9}")
    lineas.append("-" * ancho)

    for d in detalle_rows:
        subtotal = d["cantidad"] * d["precio_unitario_usd"]
        nombre = d["nombre_producto"][:20]
        lineas.append(
            f"{nombre:<20}{d['cantidad']:>4}{d['precio_unitario_usd']:>7.2f}{subtotal:>9.2f}"
        )

    lineas.append("-" * ancho)
    lineas.append(f"{'TOTAL USD':<28}{'$':>3}{venta_row['total_usd']:>9.2f}")
    lineas.append(f"{'Tasa BCV':<28}{venta_row['tasa_bcv']:>12.2f}")
    lineas.append(f"{'TOTAL BS':<28}{'Bs':>3}{venta_row['total_bs']:>9.2f}")
    lineas.append(f"Forma de pago: {venta_row['forma_pago']}")
    lineas.append("=" * ancho)
    lineas.append("¡Gracias por su compra!".center(ancho))

    return "\n".join(lineas)


def guardar_ticket(texto, venta_id):
    os.makedirs(TICKETS_DIR, exist_ok=True)
    ruta = os.path.join(TICKETS_DIR, f"ticket_{venta_id}.txt")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(texto)
    return ruta
