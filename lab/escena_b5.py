"""[ESC·f535] lab/escena_b5.py - controles de la REGLA DE REESCALA (sin Blender).

    python lab/escena_b5.py   -> lab/escenas/b5_almohadon_h{10,5,3}.json, b5_voladizo_h{10,5,3}.json, b4_canal_marco_h3.json

almohadon: b4_canal con 1 canal (145 x 300), borde de la cascara FIJO en su molde, sin pespuntes (solo presion + membrana).
voladizo: tira 30 x 183 mm (30 empotrados + 153 libres), sin colision (banco 5 de VERDADES-OLA2). h3 = paso 10/3.
"""
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from escena import Escena, pieza  # noqa: E402
from escena_b4 import b4_canal  # noqa: E402

PASOS = {"h10": 10.0, "h5": 5.0, "h3": 10.0 / 3.0}


def voladizo(nombre, paso, W=30.0, XR=30.0, L=183.0):   # 30 de ancho: con 25 a 10 mm quedan 2 filas de 12,5 (arista p50 13,2)
    E = Escena(nombre); P, T = pieza(0, 0, L, W, lineas_x=[XR], paso=paso); E.agregar("C", P, T)
    E.fijar("C", lambda Q: Q[:, 0] <= XR + 1e-6)
    return E.guardar(dict(banco="b5", colisionadores=[], paso=paso, tiras={"C": dict(piezas=["C"], x_costura=(XR + L) / 2, x_raiz=XR, x_punta=L)}))


if __name__ == "__main__":
    for k, p in PASOS.items():
        b4_canal(n_canales=1, nombre=f"b5_almohadon_{k}", marco=True, paso=p)
        voladizo(f"b5_voladizo_{k}", p)
    b4_canal(nombre="b4_canal_marco_h3", marco=True, paso=PASOS["h3"])
