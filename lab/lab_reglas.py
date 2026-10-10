"""[ESC·f535] lab/lab_reglas.py - modulo de reglas del laboratorio para sim/nucleo.py.

Solo expone el SANDWICH de la M133 tal cual (las mismas funciones de sim/m133_reglas.py, sin copiar ni editar): rotacion de
tri[0], reposo del ht superpuesto al hs y resortes internos. Con `sand=0` las tres no hacen nada. Las demas reglas de la M133
(capucha, tapeta, axila, metricas por zona) no aplican a una escena minima y no se llaman.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sim"))
from m133_reglas import sandwich_rotar_caras, sandwich_reposo, sandwich_resortes_internos, broches_con_altura  # noqa: E402,F401  [ESC·f535] broches: B8 (sin snap_sep no hace nada)

CAPAS = set()
