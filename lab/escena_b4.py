"""[ESC·f535] lab/escena_b4.py - banco 4: CANAL con mascara de acortamiento en el pespunte (sin Blender).

Placa de n canelones de `ancho` (a traves, entre pespuntes) x `largo` (a lo largo del pespunte) mm, como `escena.canelon`
(misma construccion y formato M133: cascara `cn` + pared `cn_f` copia vertice a vertice con normal opuesta, cosidas en el
borde y en los pespuntes; un bolsillo de presion por canal; apoyada en una mesa). Archivo aparte para no pisar escena.py,
que usan otros bancos a la vez.

    python lab/escena_b4.py        -> lab/escenas/b4_canal_mascara.json, b4_canal_marco.json, b4_canal_marco_h5.json (paso 5 mm)
"""
import json
import os
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from escena import H, Escena, SALIDA  # noqa: E402
from malla_lab import _triangular  # noqa: E402


def pieza_canales(ancho, largo, n, paso=H):
    """Como escena.pieza, pero el borde de arriba y de abajo se parte POR CANAL (ceil(ancho/paso) tramos): asi cada pespunte
    llega al borde en un vertice (con 435 mm de ancho y un solo reparto, x = 145 no cae en la grilla y la costura no cierra)."""
    nc = int(np.ceil(ancho / paso - 1e-9)); w, h = ancho * n, largo; ny = max(1, int(round(h / paso)))
    xs = [k * ancho + ancho * i / nc for k in range(n) for i in range(nc)] + [w]
    B = [(x, 0.0) for x in xs[:-1]] + [(w, h * j / ny) for j in range(ny)] + [(x, h) for x in xs[::-1][:-1]] + [(0.0, h - h * j / ny) for j in range(ny)]
    I, ar = [], []
    for xl in [ancho * k for k in range(1, n)]:
        k0 = len(I); I += [(xl, h * j / ny) for j in range(1, ny)]; ar += [(k0 + j, k0 + j + 1) for j in range(ny - 2)]
    P, T, _ = _triangular(np.array(B, float), np.array(I, float).reshape(-1, 2), ar, paso, 6)
    return np.asarray(P, float), np.asarray(T, int)


def b4_canal(n_canales=3, ancho=145.0, largo=300.0, nombre="b4_canal_mascara", marco=False, mesa_z=-6.0, paso=H):
    """marco=True: borde de la cascara FIJO en su molde (z 0) y mesa `mesa_z` mm abajo (almohadon con borde fijo, como Victor).
    Sin marco (b4_canal_mascara, 10-10 18:21) el acolchado libre se infla redondo y sale volando: corrida ROTA, no se usa."""
    E = Escena(nombre); w, h = ancho * n_canales, largo; lx = [ancho * k for k in range(1, n_canales)]
    P, T = pieza_canales(ancho, largo, n_canales, paso=paso); z0 = 0.0 if marco else 1.0 + 4.0 + 6.0
    a = E.agregar("cn", P, T, d=(0, 0, z0)); af = E.agregar("cn_f", P, T, d=(0, 0, z0), inv=True, uv_d=(0, h + 100.0))
    n = len(P); borde = [i for i in range(n) if P[i, 0] < 1e-6 or P[i, 0] > w - 1e-6 or P[i, 1] < 1e-6 or P[i, 1] > h - 1e-6]
    linea = [i for i in range(n) if any(abs(P[i, 0] - x) < 1e-4 for x in lx)]
    for i in sorted(set(borde) | set(linea)):
        E.sew.append([a + i, af + i]); E.seam.append("canal" if i in linea else "borde")
    ch = (np.array(lx)[None, :] < P[:, 0][:, None]).sum(1)
    if marco:
        E.fijar("cn", lambda Q: (Q[:, 0] < 1e-6) | (Q[:, 0] > w - 1e-6) | (Q[:, 1] < 1e-6) | (Q[:, 1] > h - 1e-6))
    meta = dict(banco="b4", colisionadores=[dict(tipo="mesa", z=(mesa_z if marco else 0.0) / 1000.0, lado=0.6)], marco=marco, datos_reglas=dict(piezas_inyectadas=["cn"]),
                ancho=ancho, largo=largo, n_canales=n_canales, lx=lx, w=w, **({"paso": paso} if paso != H else {}))
    D = E.datos(meta)
    nf = len(T); D["inst"] = {"cn": dict(off=a, foff=0, nf=nf, key="cn"), "cn_f": dict(off=af, foff=nf, nf=nf, key="cn")}
    D["lx"] = {"cn": lx}; D["lining"] = {"cn": "cn_f"}; D["border"] = [a + i for i in borde] + [af + i for i in borde]
    D["pinch"] = [a + i for i in linea] + [af + i for i in linea]
    D["pocket"] = [None] * (2 * n)
    for i in range(n):
        if i not in borde and i not in linea:
            D["pocket"][a + i] = D["pocket"][af + i] = f"cn{int(ch[i])}"
    D["pocket_area_m2"] = {f"cn{k}": ancho * h / 1e6 for k in range(n_canales)}
    os.makedirs(SALIDA, exist_ok=True); json.dump(D, open(os.path.join(SALIDA, nombre + ".json"), "w", encoding="utf-8"))
    print(f"{nombre}: {len(D['v'])} v {len(D['f'])} tri {len(D['sew'])} pares, {n_canales} bolsillos, pinch {len(D['pinch'])}, borde {len(D['border'])}")
    return D


if __name__ == "__main__":
    b4_canal(); b4_canal(nombre="b4_canal_marco", marco=True)
    b4_canal(nombre="b4_canal_marco_h5", marco=True, paso=5.0)   # [ESC·f535] banco 4 a 5 mm (reescala: lab/correr.py `reescala`)
