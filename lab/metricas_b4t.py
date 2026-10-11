"""[ESC·f535] lab/metricas_b4t.py - metrica del banco de transferencia b4t (tubo de canales con struts), sin Blender.

Las mismas magnitudes que se midieron en la prenda (LEYES, "Banco de transferencia (b4t)"), sobre X_<tag>_fin.npy:
  * loft = |cascara_i - forro_i| (mm, pares vertice a vertice). CRESTA = vertices de la cascara con d >= relleno_r (ahi el
    reposo del strut es relleno_h). loft cresta y loft/t (loft / T(d)) = medianas por canal; t = perfil lente de lab_reglas.
  * estiramiento (%) por arista = largo 3D / reposo efectivo - 1. Cascara: reposo = molde x (1 + encoge cascara). Forro (_f):
    reposo = sqrt(molde^2 + (T_i - T_j)^2) x (1 + encoge pared). LEJOS = las dos puntas con d >= relleno_r; CERCA = d <= 15 mm.
  * ruedo: perimetro 3D del borde de abajo de la cascara (% contra el molde C); largo: caida vertical media borde de arriba ->
    ruedo y recorrido 3D por la costura de cierre (% contra el alto del molde). Delta contra la primera variante de la tanda.

    python lab/metricas_b4t.py lab/tandas/b4t_humo.json lab/out/_cola/b4t_humo [--json lab/datos/b4t_humo.json]
"""
import argparse
import json
import os
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
DEF = dict(relleno=0.0, relleno_h=12.0, relleno_g=15.0, relleno_r=0.0, relleno_min=1.0)   # = lab_reglas.DEFECTOS_RELLENO


def perfil(d, h, r, tmin):
    if r <= 0:
        return np.maximum(tmin, np.full_like(d, h))
    return np.maximum(tmin, h * (1.0 - (1.0 - np.clip(d / r, 0.0, 1.0)) ** 2))


def aristas(F, a, b):
    t = F[(F[:, 0] >= a) & (F[:, 0] < b)]
    return np.unique(np.sort(np.vstack([t[:, [0, 1]], t[:, [1, 2]], t[:, [2, 0]]]), axis=1), axis=0)


def pc(x):
    return [round(float(np.percentile(x, q)), 2) for q in (5, 50, 95)] if len(x) else None


def medir(D, X, P, enc):
    X = X * 1000.0; UV = np.array(D["uv"], float); F = np.array(D["f"], int); L = D["lab"]
    a, b = D["groups"]["cn"]; af, bf = D["groups"]["cn_f"]; n = b - a
    d = np.array(D["relleno_d"][a:b], float); h, r, tmin = P["relleno_h"], P["relleno_r"], P["relleno_min"]
    T = perfil(d, h, r, tmin) if P["relleno"] > 0 else np.zeros(n)
    loft = np.linalg.norm(X[a:b] - X[af:bf], axis=1); ch = (np.array(L["lx"])[None, :] < UV[a:b, 0][:, None]).sum(1)
    rc = r if r > 0 else 45.0; cres = d >= rc; out = dict(canales={})
    for k in range(L["n_canales"]):
        m = cres & (ch == k)
        out["canales"][f"cn{k}"] = dict(loft_cresta=round(float(np.median(loft[m])), 2), loft_p10_p90=[round(float(np.percentile(loft[m], q)), 2) for q in (10, 90)],
                                        loft_t=round(float(np.median(loft[m] / T[m])), 3) if P["relleno"] > 0 else None, n=int(m.sum()))
    ec, ew = float(enc.get("cascara", 0.0)), float(enc.get("pared", 0.0))
    for nm, (g0, g1), e, tz in (("cascara", (a, b), ec, None), ("_f", (af, bf), ew, T)):
        E = aristas(F, g0, g1); i, j = E[:, 0] - g0, E[:, 1] - g0
        l0 = np.linalg.norm(UV[E[:, 0]] - UV[E[:, 1]], axis=1)
        if tz is not None:
            l0 = np.sqrt(l0 ** 2 + (tz[i] - tz[j]) ** 2)
        s = 100.0 * (np.linalg.norm(X[E[:, 0]] - X[E[:, 1]], axis=1) / (l0 * (1.0 + e)) - 1.0)
        lej = (d[i] >= rc) & (d[j] >= rc); cer = (d[i] <= 15.0) & (d[j] <= 15.0)
        out[f"estira_{nm}"] = dict(lejos_p5_p50_p95=pc(s[lej]), cerca_p5_p50_p95=pc(s[cer]), n_lejos=int(lej.sum()))
    Q = UV[a:b]; C, alto = float(L["C"]), float(L["alto"])
    ru = np.where(Q[:, 0] > alto - 1e-6)[0]; ru = ru[np.argsort(Q[ru, 1])]; ru = ru[Q[ru, 1] < C - 1e-6]
    per = float(np.linalg.norm(np.diff(X[a + np.r_[ru, ru[:1]]], axis=0), axis=1).sum())
    ar = np.where(Q[:, 0] < 1e-6)[0]; ci = np.where(Q[:, 1] < 1e-6)[0]; ci = ci[np.argsort(Q[ci, 0])]
    rec = float(np.linalg.norm(np.diff(X[a + ci], axis=0), axis=1).sum())
    out.update(ruedo_mm=round(per, 1), ruedo_pct=round(100 * (per / C - 1), 2), caida_mm=round(float(X[a + ar, 2].mean() - X[a + ru, 2].mean()), 1),
               recorrido_cierre_pct=round(100 * (rec / alto - 1), 2), forro_r_mm=round(float(np.median(np.linalg.norm(X[af:bf, :2] - np.array(L["centro"]), axis=1))), 1),
               finito=bool(np.isfinite(X).all()))
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("tanda"); ap.add_argument("dir"); ap.add_argument("--json"); ap.add_argument("--sufijo", default="fin")
    A = ap.parse_args(); T = json.load(open(A.tanda, encoding="utf-8")); filas = {}
    for var in T["variantes"]:
        ruta = os.path.join(A.dir, f"X_{var['tag']}_{A.sufijo}.npy")
        if not os.path.exists(ruta):
            print(f"{var['tag']}: falta {ruta}"); continue
        D = json.load(open(os.path.join(AQUI, "escenas", var["escena"] + ".json"), encoding="utf-8"))
        P = dict(DEF); P.update({k: float(v) for k, v in {**T.get("receta_lab", {}), **var.get("params", {})}.items() if k in DEF})
        filas[var["tag"]] = medir(D, np.load(ruta), P, var.get("encoge") or {})
    base = next(iter(filas.values()), None)
    for tag, m in filas.items():
        dl = {k: (round(100 * (m["canales"][k]["loft_cresta"] / base["canales"][k]["loft_cresta"] - 1), 2) if base["canales"][k]["loft_cresta"] > 0 else None) for k in m["canales"]}
        m["delta_vs_" + next(iter(filas))] = dict(loft_pct=dl, ruedo_pct=round(100 * (m["ruedo_mm"] / base["ruedo_mm"] - 1), 2))
        print(tag, json.dumps(m, ensure_ascii=False))
    if A.json:
        json.dump(filas, open(A.json, "w", encoding="utf-8"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    sys.exit(main())
