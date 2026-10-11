"""[ESC·f535] lab/escena_b4t.py - banco de TRANSFERENCIA b4t: TUBO de canales horizontales colgado de un canesu (sin Blender).

Lo que el banco tiene que tener para representar a una campera de canelones (LEYES, "Banco de transferencia (b4t)"): canales
alrededor del cuerpo, ruedo LIBRE, peso colgando de los hombros, forro contra el torso y struts del relleno (lab_reglas).

  * cn + cn_f: el molde de escena_b4.pieza_canales (n canales de `ancho` entre pespuntes x C de largo), ENROLLADO: x del molde
    = alto (x 0 = canesu, x n*ancho = ruedo), y del molde = vuelta (theta = 2 pi y / C, radio C / 2 pi). Cascara y forro con la
    MISMA uv (el reposo del strut va bajo la cascara, como en la prenda); cosidas en pespuntes y bordes; costura de cierre
    y 0 <-> y C en cada capa. Normales de la cascara hacia afuera (se verifica).
  * cd: disco-canesu de una capa (radio = el del tubo), cosido 1:1 al borde de arriba de la cascara, en SU MOLDE a z 0
    (los pines siguen la clave molde_plano) con el centro (r < r_pin) fijo. Apoya en un plato colisionador (hombros).
  * colisionadores: plato (cilindro corto r_plato) y torso (cilindro r_torso, eje z). Sin marco ni pines en los canales.
  * D['relleno_d']: distancia en el molde (mm) de cada vertice de la cascara a pespuntes, bordes y costura de cierre (perfil
    lente de los struts); None en el resto.

    python lab/escena_b4t.py      -> lab/escenas/b4t_tubo.json
"""
import json
import math
import os
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from escena import H, Escena, SALIDA  # noqa: E402
from escena_b4 import pieza_canales  # noqa: E402
from prenda3d.malla_gen import _triangular  # noqa: E402


def b4t_tubo(n_canales=3, ancho=160.0, C=1194.0, nombre="b4t_tubo", r_torso=172.0, r_plato=186.0, r_pin=80.0, paso=H):
    R = C / (2 * math.pi); alto = ancho * n_canales; cx, cy = alto + 300.0 + R, C / 2.0   # disco lejos del molde del tubo
    P, T = pieza_canales(ancho, C, n_canales, paso=paso); lx = [ancho * k for k in range(1, n_canales)]

    def enrollar(Q):
        th = 2 * math.pi * Q[:, 1] / C
        return np.c_[cx + R * np.cos(th), cy + R * np.sin(th), -Q[:, 0]]
    X = enrollar(P); t0 = T[len(T) // 2]; nrm = np.cross(X[t0[1]] - X[t0[0]], X[t0[2]] - X[t0[0]]); c_ = X[t0].mean(0)
    if np.dot(nrm[:2], c_[:2] - (cx, cy)) < 0:
        T = T[:, [0, 2, 1]]                          # cascara con la normal hacia afuera del tubo
    E = Escena(nombre); a = E.agregar("cn", P, T); af = E.agregar("cn_f", P, T, inv=True); n = len(P)
    E.V[a:a + n] = (X / 1000.0).tolist(); E.V[af:af + n] = (X / 1000.0).tolist()
    # disco-canesu: borde = los vertices del borde x 0 del tubo (mismo reparto en y), en su molde a z 0
    ys = np.sort(P[np.abs(P[:, 0]) < 1e-6, 1]); ny = len(ys) - 1
    assert abs(ys[0]) < 1e-6 and abs(ys[-1] - C) < 1e-6, "el borde de arriba tiene que ir de y 0 a y C"
    th = 2 * math.pi * ys[:-1] / C; B = np.c_[cx + R * np.cos(th), cy + R * np.sin(th)]
    Pd, Td, _ = _triangular(B, np.zeros((0, 2)), [], paso, 6); Pd = np.asarray(Pd, float); Td = np.asarray(Td, int)
    ad = E.agregar("cd", Pd, Td); jb = [int(np.argmin(np.linalg.norm(Pd - b, axis=1))) for b in B]
    assert max(np.linalg.norm(Pd[jb] - B, axis=1)) < 1e-6, "el disco no conserva el borde del tubo (costura no 1:1)"
    E.fijar("cd", lambda Q: np.linalg.norm(Q - (cx, cy), axis=1) < r_pin)
    # costuras: cascara <-> forro (bordes y pespuntes), cierre en cada capa, canesu
    borde = [i for i in range(n) if P[i, 0] < 1e-6 or P[i, 0] > alto - 1e-6 or P[i, 1] < 1e-6 or P[i, 1] > C - 1e-6]
    linea = [i for i in range(n) if any(abs(P[i, 0] - x) < 1e-4 for x in lx)]
    for i in sorted(set(borde) | set(linea)):
        E.sew.append([a + i, af + i]); E.seam.append("canal" if i in linea else "borde")
    i0 = sorted(np.where(np.abs(P[:, 1]) < 1e-6)[0], key=lambda i: P[i, 0]); i1 = sorted(np.where(np.abs(P[:, 1] - C) < 1e-6)[0], key=lambda i: P[i, 0])
    assert len(i0) == len(i1) and np.abs(P[i0, 0] - P[i1, 0]).max() < 1e-6, "cierre no 1:1"
    for off, nm in ((a, "cierre"), (af, "cierre_f")):
        E.sew += [[off + int(i), off + int(j)] for i, j in zip(i0, i1)]; E.seam += [nm] * len(i0)
    top = {round(float(P[i, 1]), 6): i for i in range(n) if P[i, 0] < 1e-6}
    for k, y in enumerate(ys[:-1]):
        E.sew.append([ad + jb[k], a + top[round(float(y), 6)]]); E.seam.append("canesu")
    E.sew.append([ad + jb[0], a + top[round(float(ys[-1]), 6)]]); E.seam.append("canesu")
    # distancia al pespunte / borde / cierre en el molde (perfil lente) y bolsillos por canal
    dx = np.min(np.abs(P[:, 0][:, None] - np.array([0.0] + lx + [alto])[None, :]), axis=1); dy = np.minimum(P[:, 1], C - P[:, 1])
    ch = (np.array(lx)[None, :] < P[:, 0][:, None]).sum(1)
    meta = dict(banco="b4t", colisionadores=[
        dict(tipo="cilindro", r=r_plato / 1000.0, largo=0.02, centro=[cx / 1000.0, cy / 1000.0, -0.012], rot=[0, 0, 0]),
        dict(tipo="cilindro", r=r_torso / 1000.0, largo=0.62, centro=[cx / 1000.0, cy / 1000.0, -0.012 - 0.01 - 0.31], rot=[0, 0, 0])],
        datos_reglas=dict(piezas_inyectadas=["cn"]), ancho=ancho, C=C, R=R, alto=alto, n_canales=n_canales, lx=lx, centro=[cx, cy],
        r_torso=r_torso, r_plato=r_plato, r_pin=r_pin, **({"paso": paso} if paso != H else {}))
    D = E.datos(meta); NV = len(D["v"]); nf = len(T)
    D["inst"] = {"cn": dict(off=a, foff=0, nf=nf, key="cn"), "cn_f": dict(off=af, foff=nf, nf=nf, key="cn")}
    D["lx"] = {"cn": lx}; D["lining"] = {"cn": "cn_f"}
    D["border"] = [a + i for i in borde] + [af + i for i in borde]; D["pinch"] = [a + i for i in linea] + [af + i for i in linea]
    D["pocket"] = [None] * NV
    for i in range(n):
        if i not in borde and i not in linea:
            D["pocket"][a + i] = D["pocket"][af + i] = f"cn{int(ch[i])}"
    D["pocket_area_m2"] = {f"cn{k}": ancho * C / 1e6 for k in range(n_canales)}
    D["relleno_d"] = [None] * NV
    for i in range(n):
        D["relleno_d"][a + i] = round(float(min(dx[i], dy[i])), 3)
    os.makedirs(SALIDA, exist_ok=True); json.dump(D, open(os.path.join(SALIDA, nombre + ".json"), "w", encoding="utf-8"))
    print(f"{nombre}: {NV} v {len(D['f'])} tri {len(D['sew'])} pares ({len(i0)} cierre x2, {ny + 1} canesu) | {n_canales} bolsillos | "
          f"pin {len(D['lab']['pin'])} | R {R:.1f} mm, alto {alto:.0f} | disco {len(Pd)} v")
    return D


if __name__ == "__main__":
    b4t_tubo()
