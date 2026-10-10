"""[ESC·f535] lab/encoge_lab.py - exceso de tela y mascara de acortamiento por CLASE de vertice (banco 4), sobre el Cloth del nucleo.

Blender 5.1 (cloth.cc:cloth_shrink_factor): k_i = (1 - shrink_min) + (shrink_min - shrink_max) * w_i ; restlen = |xrest| * sqrt(k_i k_j).
Un solo grupo (`encoge`, el del nucleo) alcanza para tres niveles si se ordenan: el k MAYOR va en peso 0 y el MENOR en peso 1.
  cfg = {"cascara": e_s, "pared": e_w, "pespunte": m}  ->  k = 1 + valor  (positivo = exceso, negativo = acortamiento)
  sin "pespunte": los vertices del pespunte siguen a su capa.
Lo llama correr.py despues de nucleo.cloth (que deja shrink_min 0, shrink_max S, grupo `encoge`) y antes del bucle. Guarda
encoge_<tag>.npy (k por vertice) para medir la deformacion contra el reposo EFECTIVO.
"""
import numpy as np


def clases(D):
    """ids por clase: cascara (piezas sin _f), pared (_f), pespunte (D['pinch'], las dos capas)."""
    cas, par = [], []
    for g, (a, b) in D["groups"].items():
        (par if g.endswith("_f") else cas).extend(range(a, b))
    return dict(cascara=np.array(cas, int), pared=np.array(par, int), pespunte=np.array(sorted(set(D["pinch"])), int))


def niveles(cfg, nv, C):
    """k por vertice y (shrink_min, shrink_max, pesos) que lo reproducen en Blender."""
    k = np.ones(nv)
    k[C["cascara"]] = 1.0 + float(cfg.get("cascara", 0.0)); k[C["pared"]] = 1.0 + float(cfg.get("pared", 0.0))
    if "pespunte" in cfg:
        k[C["pespunte"]] = 1.0 + float(cfg["pespunte"])
    kmax, kmin = float(k.max()), float(k.min())
    if kmax - kmin < 1e-12:
        return k, 1.0 - kmax, 1.0 - kmax, np.zeros(nv)
    return k, 1.0 - kmax, 1.0 - kmin, (kmax - k) / (kmax - kmin)


def aplicar(ES, cfg):
    C = clases(ES.D); k, smin, smax, w = niveles(cfg, ES.NV, C)
    vg = ES.gar.vertex_groups.get("encoge") or ES.gar.vertex_groups.new(name="encoge")
    for wv in sorted(set(np.round(w, 9).tolist())):
        ids = [int(i) for i in np.where(np.abs(w - wv) < 1e-9)[0]]
        vg.add(ids, float(wv), "REPLACE")
    ES.s.shrink_min = smin; ES.s.shrink_max = smax; ES.s.vertex_group_shrink = vg.name
    kk = (1.0 - smin) + (smin - smax) * w                        # = cloth_shrink_factor por vertice
    assert np.abs(kk - k).max() < 1e-9, "encoge: los pesos no reproducen los k pedidos"
    np.save(ES.SAL + f"encoge_{ES.TAG}.npy", k)
    ES.log(f"[ESC·f535] ENCOGE {cfg}: shrink_min {smin:.4f} shrink_max {smax:.4f} grupo {vg.name!r} | k cascara "
           f"{sorted(set(np.round(k[C['cascara']], 4).tolist()))} pared {sorted(set(np.round(k[C['pared']], 4).tolist()))} "
           f"pespunte {sorted(set(np.round(k[C['pespunte']], 4).tolist()))} | pesos {sorted(set(np.round(w, 4).tolist()))}")
    return k
