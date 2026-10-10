"""[ESC·f535] lab/metricas_b78.py - metricas de los bancos 7 y 8 sobre los dumps X_<tag>_f<f>.npy (sin Blender).

    python lab/metricas_b78.py b7 lab/out/b7_cuello      -> lab/datos/b7_b7_cuello.json
    python lab/metricas_b78.py b8 lab/out/b8_cartera     -> lab/datos/b8_b8_cartera.json
B7 (mm): alto_cf = Z max de la columna del CF (|arco| <= 15 mm) sobre la costura del escote (z 0,5); canto_cf = Z del canto en el CF;
  quiebre = alto_cf - canto_cf (canto volcado); abre_cf = radio del canto en el CF - R; flecha_cf = desvio max del perfil del CF a la recta
  base-canto (plano r-z); alto_medio / alto_espalda; desp16 = max |X6 - X1|; osc = max |X72 - X60| (asentada si < 1).
B8: ang_k = angulo (grados) entre el eje del broche k (base en fL -> vertice t de la cartera; el apice va cosido a t) y la normal de la
  cartera en t; hueco = separacion radial cartera - capa de abajo (p50 / p95, mm) entre broches 1 y 3, a > 5 mm de los cantos; agujero =
  area (mm2, 86,6 mm2 por vertice) de cartera entre broches 1 y 2 con la capa de abajo por ENCIMA (separacion < 0,5 mm); canto = canto
  superior (y 50): desvio max a su recta (mm) y labio = separacion en el canto - p50 del interior (mm).
"""
import glob
import json
import os
import re
import sys

import numpy as np
from scipy.interpolate import griddata

AQUI = os.path.dirname(os.path.abspath(__file__))


def cargar(sal):
    X = {}
    for r in glob.glob(os.path.join(sal, "X_*_f*.npy")):
        m = re.match(r"X_(.+)_f(\d+)\.npy$", os.path.basename(r))
        if m:
            X.setdefault(m.group(1), {})[int(m.group(2))] = np.load(r) * 1000.0
    return X


def esc(tag, sal):
    e = json.load(open(os.path.join(sal, f"res_{tag}.json"), encoding="utf-8"))["escena"]
    return json.load(open(os.path.join(AQUI, "escenas", e + ".json"), encoding="utf-8"))


def b7(tag, Xs, D):
    a, b = D["groups"]["cu"]; U = np.array(D["uv"])[a:b]; R = D["lab"]["R_mm"]; o = {}
    cf = (U[:, 1] <= 15) | (U[:, 1] >= 645); lin = np.abs(U[:, 1]) < 1e-6; top = np.abs(U[:, 0] - 120) < 1e-6
    for f in (30, 48, 72):
        X = Xs[f][a:b]; z = X[:, 2] - 0.5
        col = np.round(U[:, 1] / 10).astype(int); zmax = np.array([z[col == c].max() for c in np.unique(col)])
        k = np.where(lin)[0]; k = k[np.argsort(U[k, 0])]; P = np.c_[np.hypot(X[k, 0], X[k, 1]), z[k]]
        d = P[-1] - P[0]; fl = np.abs(np.cross(d, P - P[0])) / max(np.linalg.norm(d), 1e-9)
        o[f"f{f}"] = dict(alto_cf=float(z[cf].max()), canto_cf=float(z[cf & top].mean()), quiebre=float(z[cf].max() - z[cf & top].mean()),
                          abre_cf=float(P[-1, 0] - R), flecha_cf=float(fl.max()), alto_medio=float(np.median(zmax)),
                          alto_espalda=float(z[np.abs(U[:, 1] - 330) <= 15].max()))
    o["desp16"] = float(np.linalg.norm(Xs[6][a:b] - Xs[1][a:b], axis=1).max())
    o["osc"] = float(np.linalg.norm(Xs[72][a:b] - Xs[60][a:b], axis=1).max())
    return o


def normales(X, F):
    N = np.zeros_like(X); c = np.cross(X[F[:, 1]] - X[F[:, 0]], X[F[:, 2]] - X[F[:, 0]])
    for j in range(3):
        np.add.at(N, F[:, j], c)
    return N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)


def b8(tag, Xs, D):
    g = D["groups"]; F = np.array(D["f"]); U = np.array(D["uv"]); items = D["snap_sep"]["items"]; yb = D["lab"]["broches_y"]; o = {}
    ac, bc = g["cart"]; Uc = U[ac:bc] - np.array([0, 1000.0]); fr = np.r_[np.arange(*g["fR"]), np.arange(*g["fL"])]
    for f in (30, 48, 72):
        X = Xs[f]; N = normales(X, F); r = {}
        for k, it in enumerate(items):
            ax = X[it["t"]] - np.array(it["bary"]) @ X[it["face"]]
            r[f"ang{k + 1}"] = float(np.degrees(np.arccos(min(1.0, abs(ax @ N[it["t"]]) / np.linalg.norm(ax)))))
        pc = lambda Y: np.c_[np.arctan2(Y[:, 0], Y[:, 2]) * 155.0, Y[:, 1]]                  # (arco mm, eje mm)
        rad = lambda Y: np.hypot(Y[:, 0], Y[:, 2])
        Xc = X[ac:bc]; rf = griddata(pc(X[fr]), rad(X[fr]), pc(Xc), method="linear"); gap = rad(Xc) - rf
        inn = (Uc[:, 1] > yb[0]) & (Uc[:, 1] < yb[2]) & (Uc[:, 0] > -10) & (Uc[:, 0] < 40) & np.isfinite(gap)
        h12 = (Uc[:, 1] > yb[0]) & (Uc[:, 1] < yb[1]) & np.isfinite(gap)
        cs = np.abs(Uc[:, 1] - 50.0) < 1e-6; P = Xc[cs]; c0 = P.mean(0); w = np.linalg.svd(P - c0)[2][0]
        dev = np.linalg.norm((P - c0) - np.outer((P - c0) @ w, w), axis=1)
        r.update(hueco_p50=float(np.median(gap[inn])), hueco_p95=float(np.percentile(gap[inn], 95)),
                 agujero_mm2=float(86.6 * np.sum(gap[h12] < 0.5)), canto_dev=float(dev.max()),
                 labio=float(np.nanmax(gap[cs]) - np.median(gap[inn])))
        o[f"f{f}"] = r
    o["osc"] = float(np.linalg.norm(Xs[72][ac:bc] - Xs[60][ac:bc], axis=1).max())
    return o


def main():
    banco, sal = sys.argv[1], sys.argv[2]; Xs = cargar(sal); fn = dict(b7=b7, b8=b8)[banco]; out = {}
    for tag in sorted(Xs):
        out[tag] = fn(tag, Xs[tag], esc(tag, sal))
    os.makedirs(os.path.join(AQUI, "datos"), exist_ok=True)
    ruta = os.path.join(AQUI, "datos", f"{banco}_{os.path.basename(os.path.normpath(sal))}.json")
    json.dump(dict(firma="[ESC·f535]", banco=banco, salida=sal, variantes=out), open(ruta, "w", encoding="utf-8"), indent=1)
    for tag, o in out.items():
        print(tag, {k: (round(v, 1) if isinstance(v, float) else {kk: round(vv, 1) for kk, vv in v.items()}) for k, v in o.items() if k in ("f72", "desp16", "osc")})
    print("->", ruta)


if __name__ == "__main__":
    main()
