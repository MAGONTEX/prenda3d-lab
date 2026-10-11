"""[ESC·f535] prenda3d/lab/zozo/zz_corre.py - corre un spec de zz_escena.py en el ZOZO (python de la distribucion, sin -I:
el frontend ES el codigo bajo prueba) y guarda cuadros + cruces por cuadro. Las metricas van en la laptop (zz_metricas.py).

    ./ppf-contact-solver python zz_corre.py <spec.npz> <salida_dir> <tag> <cuadros> [clave=valor ...]

claves: p (presion; 0 = sin presion), pull (w; 0 = borde clavado), y las del objeto con su nombre ZOZO (bend, density, strain-limit, young-mod, ...);
dt=<s> va a la sesion. Si el spec trae `mesa`, pared invisible en y = mesa. Salida: <salida>/<tag>.npz (Q cada `paso`
cuadros + el ultimo, en el ORDEN DEL SPEC; cruces por cuadro con el verificador del frontend) y <tag>.json.
"""
import json
import os
import sys
import time

import numpy as np
from frontend import App
from frontend._intersection_ import check_self_intersection

SPEC, OUT, TAG, NF = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
KV = dict(a.split("=", 1) for a in sys.argv[5:])
S = np.load(SPEC); V, F, pin, mesa = S["V"], S["F"].astype(np.int64), S["pin"].astype(int).tolist(), float(S["mesa"][0])
BASE = {"strain-limit": 0.02, "density": 0.07, "contact-gap": 5e-4, "contact-offset": 1.5e-4, "friction": 0.4,
        "bend-rest-from-geometry": 1.0}
P = float(KV.pop("p", 0)); DT = float(KV.pop("dt", 0.01)); PASO = int(KV.pop("paso", 5))
PULL = float(KV.pop("pull", 0))   # [ESC·f535] Z19: >0 = el borde es un resorte pin.pull(w) a su lugar inicial, no un pin duro
par = dict(BASE, **{k: (v if v.isalpha() else float(v)) for k, v in KV.items()})
if P:
    par["pressure"] = P
app = App.create(f"zz_{TAG}")
app.asset.add.tri("m", V, F)
scene = app.scene.create(); obj = scene.add("m")
if pin:
    h = obj.pin(pin)
    if PULL > 0:
        h.pull(PULL)
defs = {}
for k in ("bend", "density", "young-mod", "poiss-rat", "model", "shrink", "strain-limit", "pressure"):
    try:
        defs[k] = obj.param.get(k)
    except Exception as e:  # noqa: BLE001
        defs[k] = f"? {e}"
for k, v in par.items():
    obj.param.set(k, v)
if not np.isnan(mesa):
    scene.add.invisible.wall([0, mesa, 0], [0, 1, 0])
scene = scene.build(); session = app.session.create(scene)
session.param.set("frames", NF).set("dt", DT); session = session.build()
t0 = time.time(); session.start(blocking=True); tw = time.time() - t0
Q0 = np.asarray(session.get.vertex(0)[0], float); c0, cv = Q0.mean(0), V.mean(0); A, B = V - cv, Q0 - c0
perm = np.empty(len(V), int); dmin = np.empty(len(V))
for i in range(0, len(V), 400):                       # vecino mas cercano por tramos (el buffer viene en otro orden)
    D = np.linalg.norm(A[i:i + 400, None, :] - B[None, :, :], axis=2); perm[i:i + 400] = D.argmin(1); dmin[i:i + 400] = D.min(1)
diag = dict(nn_max_mm=float(dmin.max()) * 1000, unicos=int(len(set(perm.tolist()))), nv=len(V), nt=len(F))
cruces, Qs, fs, t1 = [], [], [], time.time()
for n in range(NF + 1):
    r = session.get.vertex(n)
    if r is None:
        cruces.append(-1); continue
    Q = np.asarray(r[0], float)[perm] - (c0 - cv); cruces.append(len(check_self_intersection(Q, F)))
    if n % PASO == 0 or n == NF:
        Qs.append(Q); fs.append(n)
tc = time.time() - t1
res = dict(firma="[ESC·f535]", tag=TAG, spec=os.path.basename(SPEC), nf=NF, dt=DT, p=P, par=par, defectos=defs, diag=diag,
           t_wall_s=tw, s_cuadro=tw / max(NF, 1), t_cruces_s=tc, cruces_max=max(cruces), cuadros_con_cruce=int(sum(c > 0 for c in cruces)),
           cuadros_leidos=int(sum(c >= 0 for c in cruces)))
os.makedirs(OUT, exist_ok=True)
np.savez(os.path.join(OUT, TAG + ".npz"), Q=np.array(Qs), f=np.array(fs), cruces=np.array(cruces))
json.dump(res, open(os.path.join(OUT, TAG + ".json"), "w"), indent=1, default=str)
print("[ESC·f535]", json.dumps({k: res[k] for k in ("tag", "s_cuadro", "cruces_max", "cuadros_leidos", "diag")}, default=str))
