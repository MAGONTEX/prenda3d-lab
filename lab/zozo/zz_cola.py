"""[ESC·f535] prenda3d/lab/zozo/zz_cola.py - corre una tanda ZOZO de la cola (GitHub Actions) y la mide en el mismo trabajo.

    python3 lab/zozo/zz_cola.py <tanda.json> <salida_dir> <carpeta_del_zozo>

Tanda: mismo formato que las de Blender, con receta_lab = {"motor": "zozo"} (cola.yml elige el motor por eso).
Por variante: escena (lab/escenas/<escena>.json, se pasa a spec con zz_escena.spec) y params:
  ps = p* = p/(rho g) (Z5: la presion del ZOZO va por unidad de masa; se convierte con la density de la variante),
  bend, strain-limit, density, pull (w del resorte del borde; 0 = clavado), dt, paso y cualquier parametro del objeto ZOZO.
Escribe res_<tag>.json (estado FIN | ERROR) y datos/<tag>.json (zz_metricas.medidas_canal + espesor entre gemelos p50/p95
del interior del canal + cruces) como los espera scripts/cola.py resumir; npz y logs del solver en <salida>/zz/.
"""
import json
import os
import subprocess
import sys
import time

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(AQUI)); sys.path.insert(0, AQUI)
from zz_escena import de_zozo, escena, spec  # noqa: E402
from zz_metricas import medidas_canal  # noqa: E402

G0 = 9.8
TANDA, SAL, ZZ = sys.argv[1:4]
T = json.load(open(TANDA, encoding="utf-8")); Z = os.path.join(SAL, "zz")
os.makedirs(os.path.join(SAL, "datos"), exist_ok=True); os.makedirs(Z, exist_ok=True)
EXE = os.path.join(ZZ, "ppf-contact-solver"); hechas = set()


def gemelos(D, X):
    a, b = D["groups"]["cn"]; af = D["groups"]["cn_f"][0]; cos = {i for p in D["sew"] for i in p}
    inn = np.array([i for i in range(a, b) if i not in cos]); d = 1000 * np.linalg.norm(X[inn] - X[inn - a + af], axis=1)
    return dict(esp_p50=round(float(np.percentile(d, 50)), 3), esp_p95=round(float(np.percentile(d, 95)), 3), n_int=len(inn))


for v in T["variantes"]:
    tag, esc = v["tag"], v["escena"]; P = dict(v.get("params", {})); nf = int(v.get("nf", T["nf"])); t0 = time.time()
    res = dict(firma="[ESC·f535]", tag=tag, estado="ERROR")
    try:
        D = escena(esc)
        if esc not in hechas:
            spec(D, esc); hechas.add(esc)
        ps = float(P.pop("ps", 0)); rho = float(P.get("density", 0.07))
        kv = [f"p={ps * rho * G0:.6g}"] + [f"{k}={x}" for k, x in P.items()]
        cmd = [EXE, "python", os.path.join(AQUI, "zz_corre.py"), os.path.join(AQUI, "specs", esc + ".npz"), Z, tag, str(nf)] + kv
        with open(os.path.join(Z, tag + ".log"), "w") as log:
            try:
                rc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=1500).returncode
            except subprocess.TimeoutExpired:
                rc = "timeout"
        subprocess.run(["pkill", "-f", f"ppf-contact-solver --path .*/zz_{tag}/"], check=False)   # Z: el timeout no mata al solver
        R = json.load(open(os.path.join(Z, tag + ".json"))); Q = np.load(os.path.join(Z, tag + ".npz"))
        S = np.load(os.path.join(AQUI, "specs", esc + ".npz")); m = S["mapa"]
        Xs = [de_zozo(q)[m] for q in Q["Q"]]; cr = Q["cruces"]
        o = medidas_canal(D, Xs[-1], Xs[-3] if len(Xs) > 2 else None); o.update(gemelos(D, Xs[-1]))
        o.update(tag=tag, escena=esc, ps=ps, params=v.get("params", {}), rc=rc, cruces_max=int(cr.max()),
                 cuadros_con_cruce=int((cr > 0).sum()), cuadros=int((cr >= 0).sum()), s_cuadro=round(R["s_cuadro"], 4),
                 loft_f=[round(medidas_canal(D, x)["loft"], 2) for x in Xs[::4]], f=Q["f"][::4].tolist())
        json.dump(o, open(os.path.join(SAL, "datos", tag + ".json"), "w"), indent=1, default=str)
        res.update(estado="FIN" if rc == 0 and o["cuadros"] == nf + 1 else "ERROR", s_por_cuadro=round(R["s_cuadro"], 4),
                   t_sim=round(R["t_wall_s"], 1))
        print("[ESC·f535]", tag, json.dumps({k: o[k] for k in ("loft", "esp_p50", "esp_p95", "st_p95", "cruces_max", "s_cuadro")}))
    except Exception as e:  # noqa: BLE001  (una variante rota no frena la tanda)
        res["error"] = f"{type(e).__name__}: {e}"[:300]; print("[ESC·f535]", tag, "ERROR", res["error"])
    res["t_total"] = round(time.time() - t0, 1)
    json.dump(res, open(os.path.join(SAL, f"res_{tag}.json"), "w"), indent=1)
