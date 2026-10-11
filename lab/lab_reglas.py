"""[ESC·f535] lab/lab_reglas.py - modulo de reglas del laboratorio para sim/nucleo.py.

Expone el SANDWICH de la M133 tal cual (las mismas funciones de sim/m133_reglas.py, sin copiar ni editar): rotacion de
tri[0], reposo del ht superpuesto al hs y resortes internos. Con `sand=0` no hacen nada. Las demas reglas de la M133
(capucha, tapeta, axila, metricas por zona) no aplican a una escena minima y no se llaman.

[ESC·f535] b4t (2026-10-10): STRUTS del relleno inyectado portados de la prenda (RI/RJ). `relleno=<peso>` (> 0): el forro de cada
canal (D['lining']) va en la clave molde_plano a z = -sg x T(d) bajo su cascara (traslacion por vertice: isometrica por fila), con
T = max(relleno_min, relleno_h (1 - (1 - clip(d / relleno_r))^2)) y d = D['relleno_d'] (mm en el molde a pespuntes, bordes y
costuras; relleno_r = 0 -> T = relleno_h constante). Resortes internos del Cloth con peso `relleno` en el forro (grupo 'interno'),
largo max sand_len, desvio 0, chequeo de normal sand_nc, tension 0 -> sand_k, compresion 0 -> sand_kc. Guardia f1 = la de la
prenda: peso 0 en los vertices del forro a < relleno_g mm (V0) de otra pieza; se levanta en el primer paso del lazo de volumen.
Sin `relleno` (o 0) todo queda IDENTICO: los envoltorios solo llaman a la funcion de la M133.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sim"))
from m133_reglas import sandwich_rotar_caras, broches_con_altura  # noqa: E402,F401  [ESC·f535] broches: B8 (sin snap_sep no hace nada)
from m133_reglas import sandwich_reposo as _m133_sandwich_reposo, sandwich_resortes_internos as _m133_sandwich_resortes_internos  # noqa: E402

CAPAS = set()
DEFECTOS_RELLENO = dict(relleno=0.0, relleno_h=12.0, relleno_g=15.0, relleno_r=0.0, relleno_min=1.0)   # = defectos de la prenda


def _p(ES, k):
    return float(ES.P.get(k, DEFECTOS_RELLENO[k]))


def perfil(d, h, r, tmin):
    """Espesor de reposo del relleno (mm) a distancia d (mm) del pespunte: almohada, 0 -> h en r mm; piso tmin."""
    if r <= 0:
        return np.maximum(tmin, np.full_like(np.asarray(d, float), h))
    x = np.clip(np.asarray(d, float) / r, 0.0, 1.0)
    return np.maximum(tmin, h * (1.0 - (1.0 - x) ** 2))


def _signo_cascara(D, F, c):
    a, b = D["groups"][c]; UV = np.array(D["uv"], float); t = F[(F[:, 0] >= a) & (F[:, 0] < b)][:300]
    e1 = UV[t[:, 1]] - UV[t[:, 0]]; e2 = UV[t[:, 2]] - UV[t[:, 0]]
    return float(np.sign(np.sign(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]).sum()))


def sandwich_reposo(ES):
    _m133_sandwich_reposo(ES)
    if _p(ES, "relleno") <= 0:
        return
    h, r, tmin = _p(ES, "relleno_h"), _p(ES, "relleno_r"), _p(ES, "relleno_min")
    assert h < float(ES.P["sand_len"]), "relleno requiere relleno_h < sand_len (deteccion sobre el molde)"
    D = ES.D; F = np.asarray(ES.F); ES.RELLENO_F = []; tt = []
    if r > 0:
        assert "relleno_d" in D, "relleno_r > 0 requiere D['relleno_d'] en la escena (distancia al pespunte en el molde)"
    for c, fz in D["lining"].items():
        a, b = D["groups"][c]; a2, b2 = D["groups"][fz]; assert b - a == b2 - a2, (c, fz)
        sg = _signo_cascara(D, F, c)
        d = np.array([D["relleno_d"][a + k] for k in range(b - a)], float) if r > 0 else np.zeros(b - a)
        T = perfil(d, h, r, tmin)
        for k in range(b - a):
            u, w = D["uv"][a2 + k]
            ES.kc.data[a2 + k].co = (u / 1000.0, w / 1000.0, -sg * float(T[k]) / 1000.0)
        ES.RELLENO_F += list(range(a2, b2)); tt.append(T)
    tt = np.concatenate(tt)
    ES.log(f"[ESC·f535] RELLENO (lab, struts RI/RJ): forro {list(D['lining'].values())} a z = -normal x T(d) en el molde | h {h} r {r} piso {tmin} | "
           f"{len(ES.RELLENO_F)} v | T media {tt.mean():.2f} p50 {np.median(tt):.1f} max {tt.max():.1f}")


def sandwich_resortes_internos(ES):
    _m133_sandwich_resortes_internos(ES)
    if _p(ES, "relleno") <= 0:
        return
    import mathutils
    w = _p(ES, "relleno"); g = _p(ES, "relleno_g") / 1000.0; D = ES.D; nv0 = getattr(ES, "NV0", ES.NV)
    vint = ES.gar.vertex_groups.get("interno")
    if vint is None:
        vint = ES.gar.vertex_groups.new(name="interno"); vint.add(list(range(ES.NV)), 0.0, 'REPLACE')
    pc = np.empty(nv0, dtype=object)
    for p_, (a_, b_) in D["groups"].items():
        pc[a_:min(b_, nv0)] = p_
    own = {fz: {c, fz} for c, fz in D["lining"].items()}
    kd = mathutils.kdtree.KDTree(nv0)
    for i in range(nv0):
        kd.insert(ES.V0[i].tolist(), i)
    kd.balance(); ok, pend = [], []
    for i in ES.RELLENO_F:
        vec = [j for (_co, j, _d) in kd.find_range(ES.V0[i].tolist(), g) if pc[j] not in own[pc[i]]]
        (pend if vec else ok).append(i)
    if ok:
        vint.add(ok, w, 'REPLACE')
    ES.RELLENO_PEND = pend
    s = ES.s; s.use_internal_springs = True; s.internal_spring_max_length = ES.P["sand_len"] / 1000.0; s.internal_spring_max_diversion = 0.0
    s.internal_spring_normal_check = ES.P["sand_nc"] > 0; s.vertex_group_intern = "interno"
    s.internal_tension_stiffness = 0.0; s.internal_compression_stiffness = 0.0
    s.internal_tension_stiffness_max = ES.P["sand_k"]; s.internal_compression_stiffness_max = ES.P["sand_kc"]
    ES.log(f"[ESC·f535] RELLENO (lab): peso {w} en {len(ok)} v del forro desde f1 | guardia {len(pend)} a < {g * 1000:.0f} mm de otra pieza | "
           f"resortes internos: largo {s.internal_spring_max_length:.3f} m, normal_check {s.internal_spring_normal_check}, k {s.internal_tension_stiffness_max} kc {s.internal_compression_stiffness_max}")


def simetria_presion(ES):
    """Paso del lazo de volumen (antes de set_weights): levanta la guardia del relleno una vez. Sin relleno: no hace nada."""
    pend = getattr(ES, "RELLENO_PEND", None)
    if pend:
        ES.gar.vertex_groups["interno"].add(pend, _p(ES, "relleno"), 'REPLACE')
        ES.log(f"[ESC·f535] RELLENO (lab): guardia levantada en f{ES.f}, {len(pend)} v del forro al peso {_p(ES, 'relleno')}")
        ES.RELLENO_PEND = []
