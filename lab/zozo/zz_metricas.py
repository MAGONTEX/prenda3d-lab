"""[ESC·f535] prenda3d/lab/zozo/zz_metricas.py - MISMAS medidas para ZOZO y Blender (numpy, sin Blender ni ZOZO).

    python lab/zozo/zz_metricas.py canal <lote_zozo> [tags...]      # almohadon: ZOZO (lab/zozo/out/<lote>/<tag>.npz)
    python lab/zozo/zz_metricas.py blender <tanda> <tag> ...          # almohadon: Blender (X_<tag>_f*.npy bajados con --npy)
    python lab/zozo/zz_metricas.py volad <lote_zozo> [tags...]       # voladizo: c de Peirce con metricas.b1_tira

Todo se mide en coordenadas y orden de Blender (de_zozo + mapa del spec): loft = `metricas_reescala.almohadon` (espesor
cascara-pared en x = A/2, y 60..240), esp10 = el mismo espesor en x = 10 y x = A-10 (mediana de los dos lados), gemelo_min =
min(z cascara - z pared) en el interior (< 0 = las capas se cruzaron), estiramiento contra el molde (uv), asentado = max |X(f)
- X(f-10)|. Los cruces del ZOZO vienen del verificador del frontend (por cuadro); los de Blender, de zz_cruces.py en el VPS.
"""
import glob
import json
import os
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__)); LAB = os.path.dirname(AQUI); sys.path.insert(0, LAB); sys.path.insert(0, AQUI)
from metricas import b1_tira  # noqa: E402
from metricas_b4 import bary  # noqa: E402
from metricas_reescala import almohadon  # noqa: E402
from zz_escena import de_zozo, escena  # noqa: E402


def medidas_canal(D, X, Xprev=None):
    M = D["lab"]; A = M["ancho"]; a, b = D["groups"]["cn"]; af = D["groups"]["cn_f"][0]; uv = np.array(D["uv"]); F = np.array(D["f"])
    o = {k: v for k, v in almohadon(D, X).items() if not k.startswith("caida")}
    Fs = F[(F >= a).all(1) & (F < b).all(1)]; Y = np.arange(60.0, 240.0 + 1e-9, 2.0); e10 = []
    for x0 in (10.0, A - 10.0):
        T, W = bary(uv[Fs], np.c_[np.full(len(Y), x0), Y]); ids = Fs[T]
        e10.append(1000 * np.linalg.norm((X[ids] * W[..., None]).sum(1) - (X[ids - a + af] * W[..., None]).sum(1), axis=1))
    cos = {i for p in D["sew"] for i in p}; inn = np.array([i for i in range(a, b) if i not in cos])
    E = np.unique(np.sort(np.r_[F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]], 1), axis=0)
    st = np.linalg.norm(X[E[:, 0]] - X[E[:, 1]], axis=1) * 1000 / np.linalg.norm(uv[E[:, 0]] - uv[E[:, 1]], axis=1) - 1
    o.update(esp10=round(float(np.median(np.concatenate(e10))), 3), esp10_lados=[round(float(np.median(x)), 2) for x in e10],
             gemelo_min=round(float(1000 * (X[inn, 2] - X[inn - a + af, 2]).min()), 3),
             st_p95=round(float(np.percentile(st, 95)) * 100, 2), st_max=round(float(st.max()) * 100, 2), st_p5=round(float(np.percentile(st, 5)) * 100, 2))
    if Xprev is not None:
        o["asentado_mm"] = round(float(1000 * np.linalg.norm(X - Xprev, axis=1).max()), 3)
    return o


def zozo(lote, tag):
    Z = np.load(os.path.join(AQUI, "out", lote, tag + ".npz")); R = json.load(open(os.path.join(AQUI, "out", lote, tag + ".json")))
    S = np.load(os.path.join(AQUI, "specs", R["spec"])); m = S["mapa"]
    return [de_zozo(q)[m] for q in Z["Q"]], Z["f"], Z["cruces"], R


def canal(lote, tags):
    D = escena("zz_canal_h10"); out = {}
    for t in tags:
        Xs, fs, cr, R = zozo(lote, t)
        o = medidas_canal(D, Xs[-1], Xs[-3] if len(Xs) > 2 else None)
        o.update(cruces_cuadros=int((cr > 0).sum()), cuadros=int((cr >= 0).sum()), s_cuadro=round(R["s_cuadro"], 3), p=R["p"],
                 loft_f=[round(medidas_canal(D, x)["loft"], 2) for x in Xs[::4]], f=fs[::4].tolist())
        out[t] = o; print(t, json.dumps({k: v for k, v in o.items() if k not in ("loft_f", "f")}))
    return out


def blender(tanda, tags):
    D = escena("zz_canal_h10"); out = {}
    for t in tags:
        fp = sorted([p for p in glob.glob(os.path.join(LAB, "out", "_cola", tanda, "**", f"X_{t}_f*.npy"), recursive=True)
                     if p.rsplit("_f", 1)[1][:-4].isdigit()], key=lambda p: int(p.rsplit("_f", 1)[1][:-4]))
        if not fp:
            print(t, "sin npy"); continue
        Xs = [np.load(p) for p in fp]; fs = [int(p.rsplit("_f", 1)[1][:-4]) for p in fp]
        o = medidas_canal(D, Xs[-1], Xs[-2]); o.update(loft_f=[round(medidas_canal(D, x)["loft"], 2) for x in Xs], f=fs)
        out[t] = o; print(t, json.dumps({k: v for k, v in o.items() if k not in ("loft_f", "f")}))
    return out


def volad(lote, tags):
    D = escena("b5_voladizo_h10"); tira = D["lab"]["tiras"]["C"]; out = {}
    for t in tags:
        Xs, fs, cr, R = zozo(lote, t)
        r, _ = b1_tira(Xs[-1], D, tira); r = {k: v for k, v in r.items() if not k.startswith("_")}
        r.update(deriva30_mm=round(float(1000 * np.linalg.norm(Xs[-1] - Xs[-7], axis=1).max()), 3), cruces_cuadros=int((cr > 0).sum()),
                 bend=R["par"].get("bend"), density=R["par"].get("density"), s_cuadro=round(R["s_cuadro"], 3))
        out[t] = r; print(t, json.dumps(r))
    return out


if __name__ == "__main__":
    modo, lote, tags = sys.argv[1], sys.argv[2], sys.argv[3:]
    if modo != "blender" and not tags:
        tags = sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(AQUI, "out", lote, "*.npz")))
    res = dict(canal=canal, blender=blender, volad=volad)[modo](lote, [t for t in tags if modo != "volad" or t.startswith("v")]
                                                                 if modo == "volad" else [t for t in tags if modo != "canal" or not t.startswith("v")])
    os.makedirs(os.path.join(AQUI, "datos"), exist_ok=True)
    json.dump(dict(firma="[ESC·f535]", modo=modo, lote=lote, res=res), open(os.path.join(AQUI, "datos", f"zz_{modo}_{lote}.json"), "w"), indent=1)
