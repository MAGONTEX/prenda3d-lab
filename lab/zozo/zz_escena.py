"""[ESC·f535] prenda3d/lab/zozo/zz_escena.py - igual contra igual: una escena del laboratorio (formato Blender) -> spec ZOZO.

    python lab/zozo/zz_escena.py                  # (desde Diseño/prenda3d) escribe lab/escenas/zz_canal_h10.json y
                                                  # lab/zozo/specs/{canal1_h10,canal1_h5,canal3_h10,volad_h10}.npz

Misma malla que Blender (mismos v, f, pin y mesa). Lo unico que cambia es lo que el ZOZO exige:
- los pares cosidos `borde` y `canal` (pespunte) se FUNDEN en un vertice (superficie cerrada, el "Snap and Merge" del add-on);
  los `ancla` no (unen dos vertices clavados de la misma pieza);
- la capa interior (`*_f`) invierte sus caras (normal hacia afuera) y los pares de caras gemelas que quedan duplicadas
  (los 3 vertices fundidos, celdas de esquina, todos clavados) se sacan de a dos: la superficie sigue cerrada;
- separacion inicial +-1 mm en z para los vertices no fundidos (el ZOZO no arranca con capas en contacto). La escena de
  Blender `zz_canal_h10` lleva la MISMA separacion, para que las dos arranquen igual.
Ejes: Blender (x, y, z arriba) -> ZOZO (x, z, -y), gravedad -y. `mapa[k]` = vertice ZOZO del vertice Blender k.
"""
import json
import os

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__)); LAB = os.path.dirname(AQUI)
SEP = 0.001


def a_zozo(X):
    return np.c_[X[:, 0], X[:, 2], -X[:, 1]]


def de_zozo(Q):
    return np.c_[Q[:, 0], -Q[:, 2], Q[:, 1]]


def separar(D, sep=SEP):
    """Copia de la escena con +-sep en z para los vertices no cosidos de las piezas con forro (`*_f`)."""
    X = np.array(D["v"], float); cos = {i for p, s in zip(D["sew"], D["sew_seam"]) if s != "ancla" for i in p}
    for g, (a, b) in D["groups"].items():
        if g + "_f" in D["groups"] or g.endswith("_f"):
            s = -sep if g.endswith("_f") else sep
            for i in range(a, b):
                if i not in cos:
                    X[i, 2] += s
    E = dict(D); E["v"] = X.round(9).tolist(); return E


def spec(D, nombre, sep=SEP):
    X = np.array(separar(D, sep)["v"] if any(g.endswith("_f") for g in D["groups"]) else D["v"], float)
    n = len(X); par = np.arange(n)

    def raiz(i):
        while par[i] != i:
            par[i] = par[par[i]]; i = par[i]
        return i
    for (i, j), s in zip(D["sew"], D["sew_seam"]):
        if s != "ancla":
            ri, rj = raiz(i), raiz(j); par[max(ri, rj)] = min(ri, rj)
    rep = np.array([raiz(i) for i in range(n)]); uniq, mapa = np.unique(rep, return_inverse=True)
    F = np.array(D["f"], np.int64); lin = np.zeros(len(F), bool)
    for g, (a, b) in D["groups"].items():
        if g.endswith("_f"):
            lin |= (F >= a).all(1) & (F < b).all(1)
    UV = np.array(D["uv"], float); A2 = np.cross(UV[F[:, 1]] - UV[F[:, 0]], UV[F[:, 2]] - UV[F[:, 0]])
    flip = (A2 < 0) ^ lin                      # el mallador deja caras con giro mezclado: se orientan por el area del molde
    F = F.copy(); F[flip] = F[flip][:, ::-1]; G = mapa[F]
    k = np.sort(G, 1); _, inv, cnt = np.unique(k, axis=0, return_inverse=True, return_counts=True)
    dup = cnt[inv.ravel()] > 1; G = G[~dup]
    V = a_zozo(X[uniq]); vol = float(np.einsum("ij,ij->i", V[G[:, 0]], np.cross(V[G[:, 1]], V[G[:, 2]])).sum() / 6)
    if vol < 0:
        G = G[:, ::-1]; vol = -vol
    pin = np.unique(mapa[np.array(D["lab"].get("pin", []), int)])
    mesa = [c["z"] for c in D["lab"].get("colisionadores", []) if c.get("tipo") == "mesa"]
    os.makedirs(os.path.join(AQUI, "specs"), exist_ok=True)
    np.savez(os.path.join(AQUI, "specs", nombre + ".npz"), V=V, F=G, pin=pin, mapa=mapa, mesa=np.array(mesa[:1] or [np.nan]))
    print(f"[ESC·f535] {nombre}: Blender {n} v -> ZOZO {len(V)} v, {len(G)} tri (duplicadas fuera {int(dup.sum())}), "
          f"pin {len(pin)}, vol0 {vol * 1e6:.1f} ml, mesa {mesa[:1]}")


def escena(n):
    return json.load(open(os.path.join(LAB, "escenas", n + ".json"), encoding="utf-8"))


if __name__ == "__main__":
    D = escena("b5_almohadon_h10"); E = separar(D); E["lab"] = dict(E["lab"], escena="zz_canal_h10")
    json.dump(E, open(os.path.join(LAB, "escenas", "zz_canal_h10.json"), "w", encoding="utf-8"))
    spec(D, "canal1_h10"); spec(escena("b5_almohadon_h5"), "canal1_h5"); spec(escena("b4_canal_marco"), "canal3_h10")
    spec(escena("b5_voladizo_h10"), "volad_h10", sep=0.0)
