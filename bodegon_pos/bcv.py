"""
bcv.py
Maneja tres tasas independientes:
  - BCV Dólar (automática, vía API pública pyDolarVenezuela)
  - BCV Euro   (automática, misma API)
  - Manual     (la fija el administrador a mano)

Además define cuál de ellas ('bcv_usd' o 'manual') se usa para calcular
los totales en bolívares al momento de cobrar.
"""

from datetime import datetime
import database as db

API_URL_USD = "https://ve.dolarapi.com/v1/dolares/oficial"
API_URL_EUR = "https://ve.dolarapi.com/v1/euros/oficial"


def _pedir_api(url):
    try:
        import requests
    except ImportError:
        return None, "La librería 'requests' no está instalada (pip install requests)."

    try:
        headers = {"User-Agent": "Mozilla/5.0 (BodegonPOS/1.0)"}
        resp = requests.get(url, timeout=6, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        valor = None
        if isinstance(data, dict):
            # DolarApi.com devuelve compra/venta/promedio (BCV suele traer
            # solo "promedio" con valor, y compra/venta en null).
            for clave in ("promedio", "venta", "compra", "price"):
                v = data.get(clave)
                if v:
                    valor = v
                    break
            if valor is None and "monitors" in data and "bcv" in data["monitors"]:
                valor = data["monitors"]["bcv"].get("price")

        if valor is None:
            return None, "No se pudo interpretar la respuesta de la API."

        return float(valor), None
    except Exception as e:
        return None, f"No se pudo obtener la tasa: {e}"


def obtener_tasa_automatica_usd():
    return _pedir_api(API_URL_USD)


def obtener_tasa_automatica_eur():
    return _pedir_api(API_URL_EUR)


# --------------------------------------------------------- actualizar/leer

def actualizar_bcv_usd(conn):
    """Descarga y guarda la tasa BCV dólar. Devuelve (valor, error)."""
    valor, error = obtener_tasa_automatica_usd()
    if valor is not None:
        db.set_config(conn, "tasa_bcv_usd", valor)
        db.set_config(conn, "tasa_bcv_usd_actualizada", datetime.now().isoformat())
    return valor, error


def actualizar_bcv_eur(conn):
    """Descarga y guarda la tasa BCV euro. Devuelve (valor, error)."""
    valor, error = obtener_tasa_automatica_eur()
    if valor is not None:
        db.set_config(conn, "tasa_bcv_eur", valor)
        db.set_config(conn, "tasa_bcv_eur_actualizada", datetime.now().isoformat())
    return valor, error


def fijar_tasa_manual(conn, valor):
    db.set_config(conn, "tasa_manual", valor)
    db.set_config(conn, "tasa_manual_actualizada", datetime.now().isoformat())


def get_tasa_bcv_usd(conn):
    return float(db.get_config(conn, "tasa_bcv_usd", "0") or 0), \
        db.get_config(conn, "tasa_bcv_usd_actualizada", "")


def get_tasa_bcv_eur(conn):
    return float(db.get_config(conn, "tasa_bcv_eur", "0") or 0), \
        db.get_config(conn, "tasa_bcv_eur_actualizada", "")


def get_tasa_manual(conn):
    return float(db.get_config(conn, "tasa_manual", "0") or 0), \
        db.get_config(conn, "tasa_manual_actualizada", "")


# ------------------------------------------------- cuál tasa usar al cobrar

def set_tasa_para_ventas(conn, cual):
    """cual: 'bcv_usd' o 'manual'."""
    assert cual in ("bcv_usd", "manual")
    db.set_config(conn, "tasa_para_ventas", cual)


def get_tasa_para_ventas_nombre(conn):
    return db.get_config(conn, "tasa_para_ventas", "bcv_usd")


def obtener_tasa_activa(conn):
    """
    Devuelve (valor, etiqueta) de la tasa que se debe usar AHORA MISMO
    para calcular una venta, según lo que el administrador haya elegido.
    """
    cual = get_tasa_para_ventas_nombre(conn)
    if cual == "manual":
        valor, _ = get_tasa_manual(conn)
        return valor, "Manual"
    valor, _ = get_tasa_bcv_usd(conn)
    return valor, "BCV Dólar"
