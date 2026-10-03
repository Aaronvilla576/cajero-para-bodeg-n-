import tkinter as tk
import bcv


class BarraTasas(tk.Frame):
    """
    'Leyenda' fija tipo mapa: muestra de un vistazo las 3 tasas
    (BCV Dólar, BCV Euro, Manual) y cuál está activa para cobrar.
    Se coloca en la parte superior de cualquier ventana y se
    refresca sola cada cierto tiempo.
    """

    def __init__(self, parent, conn, refrescar_ms=60000):
        super().__init__(parent, bg="#10151c", padx=10, pady=6)
        self.conn = conn
        self.refrescar_ms = refrescar_ms

        self.lbl_usd = tk.Label(self, font=("Consolas", 11, "bold"), bg="#10151c", fg="#7ee787")
        self.lbl_eur = tk.Label(self, font=("Consolas", 11, "bold"), bg="#10151c", fg="#79c0ff")
        self.lbl_manual = tk.Label(self, font=("Consolas", 11, "bold"), bg="#10151c", fg="#ffd166")
        self.lbl_activa = tk.Label(self, font=("Segoe UI", 9, "italic"), bg="#10151c", fg="#9aa5b1")

        self.lbl_usd.pack(side="left", padx=(0, 18))
        self.lbl_eur.pack(side="left", padx=(0, 18))
        self.lbl_manual.pack(side="left", padx=(0, 18))
        self.lbl_activa.pack(side="left")

        self.actualizar_valores()
        self._programar_refresco()

    def actualizar_valores(self):
        usd, _ = bcv.get_tasa_bcv_usd(self.conn)
        eur, _ = bcv.get_tasa_bcv_eur(self.conn)
        manual, _ = bcv.get_tasa_manual(self.conn)
        _, etiqueta_activa = bcv.obtener_tasa_activa(self.conn)

        self.lbl_usd.config(text=f"💵 BCV USD: {usd:,.2f} Bs")
        self.lbl_eur.config(text=f"💶 BCV EUR: {eur:,.2f} Bs")
        self.lbl_manual.config(text=f"✍️ Manual: {manual:,.2f} Bs")
        self.lbl_activa.config(text=f"(cobrando con: {etiqueta_activa})")

    def _programar_refresco(self):
        try:
            self.after(self.refrescar_ms, self._tick)
        except tk.TclError:
            pass  # la ventana ya se cerró

    def _tick(self):
        self.actualizar_valores()
        self._programar_refresco()
