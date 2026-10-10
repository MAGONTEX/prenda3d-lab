"""[ESC·f535] lab/metricas_reescala.py - metricas de los controles de la regla de reescala (numpy, sin Blender).

    python lab/metricas_reescala.py <salida_tanda> [<salida_tanda> ...]   -> lab/datos/esc_<tanda>.json

almohadon (escena con cn/cn_f): loft = mediana del espesor cascara-pared en x = ancho/2, y 60..240; caida = z de la cascara
(mediana y 60..240) cada 2,5 mm a traves; seccion = integral de la caida; asentado = max |X(f) - X(f-12)| en mm.
voladizo (escena banco b5 con `tiras`): c de Peirce, theta, caida de la punta y jitter (metricas.b1_tira).
"""
import json
import os
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
from metricas import b1_tira  # noqa: E402
from metricas_b4 import bary  # noqa: E402


def cargar(sal, tag, f):
    p = os.path.join(sal, f"X_{tag}_f{f}.npy")
    return np.load(p) if os.path.isfile(p) else None


def almohadon(D, X):
    M = D["lab"]; A = M["ancho"]; a, b = D["groups"]["cn"]; af = D["groups"]["cn_f"][0]; uv = np.array(D["uv"]); F = np.array(D["f"])
    Fs = F[(F >= a).all(1) & (F < b).all(1)]; UVt = uv[Fs]; Y = np.arange(60.0, 240.0 + 1e-9, 2.0)
    T, W = bary(UVt, np.c_[np.full(len(Y), A / 2), Y]); ids = Fs[T]
    e = 1000 * np.linalg.norm((X[ids] * W[..., None]).sum(1) - (X[ids - a + af] * W[..., None]).sum(1), axis=1)
    XS = np.arange(2.5, A - 2.5 + 1e-9, 2.5); YS = np.arange(60.0, 240.0 + 1e-9, 10.0); zt, zw = [], []
    for x0 in XS:
        T_, W_ = bary(UVt, np.c_[np.full(len(YS), x0), YS]); i_ = Fs[T_]
        zt.append(float(np.median(1000 * (X[i_][..., 2] * W_).sum(1)))); zw.append(float(np.median(1000 * (X[i_ - a + af][..., 2] * W_).sum(1))))
    zt, zw = np.array(zt), np.array(zw)
    return dict(loft=round(float(np.median(e)), 3), z_cresta=round(float(zt.max()), 3), z_pared=round(float(zw.min()), 3),
                seccion_mm2=round(float(np.trapezoid(zt - zw, XS)), 1), caida_x=XS.round(1).tolist(), caida_z=zt.round(3).tolist(), caida_zw=zw.round(3).tolist())


def main():
    for sal in map(os.path.abspath, sys.argv[1:]):
        nombre = os.path.basename(sal); T = json.load(open(os.path.join(AQUI, "tandas", nombre + ".json"), encoding="utf-8")); out = {}
        for var in T["variantes"]:
            tag = var["tag"]; rp = os.path.join(sal, f"res_{tag}.json")
            if not os.path.isfile(rp):
                out[tag] = dict(estado="SIN res"); continue
            res = json.load(open(rp, encoding="utf-8")); nf = int(var.get("nf", T["nf"])); X = cargar(sal, tag, nf)
            D = json.load(open(os.path.join(AQUI, "escenas", var["escena"] + ".json"), encoding="utf-8"))
            if res["estado"] != "FIN" or X is None:
                out[tag] = dict(estado=res["estado"], error=str(res.get("error", "sin X"))[:200]); continue
            o = dict(estado="FIN", t_sim=res.get("t_sim"), s_cuadro=res.get("s_por_cuadro"), nv=len(X),
                     costura_max=max([v["max"] for v in res.get("costuras_mm", {}).values()] or [0.0]))
            if "tiras" in D["lab"]:
                m, libres = b1_tira(X, D, D["lab"]["tiras"]["C"]); o.update({k: v for k, v in m.items() if not k.startswith("_")})
                for df, k in ((1, "jitter_mm"), (6, "deriva6_mm"), (30, "deriva30_mm")):
                    Xp = cargar(sal, tag, nf - df)
                    if Xp is not None:
                        o[k] = round(float(np.abs((X[libres] - Xp[libres]) * 1000).max()), 4)
            else:
                o.update(almohadon(D, X)); Xp = cargar(sal, tag, nf - 12)
                if Xp is not None:
                    o["asentado_mm"] = round(float(np.abs((X - Xp) * 1000).max()), 3)
            out[tag] = o
            print(tag, {k: v for k, v in o.items() if not k.startswith("caida")})
        ruta = os.path.join(AQUI, "datos", f"esc_{nombre}.json")
        json.dump(dict(firma="[ESC·f535]", tanda=nombre, variantes=out), open(ruta, "w", encoding="utf-8"), indent=1); print("->", ruta)


if __name__ == "__main__":
    main()
