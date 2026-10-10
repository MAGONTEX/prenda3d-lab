"""[ESC·f535] lab/reescala_lab.py - REGLA DE REESCALA de h a h' (mismo material), de lab/VERDADES-OLA2.md (banco 5), sobre la receta.

    variante: "reescala": {"h": 10, "h2": 5}      (r = h'/h; sin la clave no hace nada)

Exponente de r por parametro (factor = r ** e). Solo se escalan valores > 0 (los -1 = apagado quedan igual):
  masa, aire (por vertice, ∝ area)                               r^2
  flexion (bending, bend_max, pl_bh) y bending_damping         r^-2   (fuerza, no torque: D_ef ∝ bending h^2)
  traccion / compresion / corte (tension, compression, soft,    r^1   (k = valor / avg_spring_len; el corte usa la
    shear, ent_c, pl_hc)                                                 misma cuenta: VERDADES no lo lista, se agrega aca)
  resortes internos del sandwich (sand_k, sand_kc)              r^3
  pin_stiffness                                                 r^3   (con peso 1 el vertice queda clavado: no cambia nada)
  presion, shrink, distancias (cd, th, self_d, off), sew_max, amortiguamientos de traccion/compresion/corte, quality: igual.
`quality` NO se toca aca: la regla la sube x (h/h')^2 solo si la flexion esta cerca del tope; se pide aparte en `params`.
"""
EXP = {"mass": 2, "air": 2, "bending": -2, "bend_max": -2, "pl_bh": -2, "tension": 1, "compression": 1, "soft": 1, "shear": 1,
       "ent_c": 1, "pl_hc": 1, "sand_k": 3, "sand_kc": 3}
# [ESC·f535] 10-10 CORREGIDA (LEYES "Laboratorio — reescala" R-1..R-3): bending_damping NO se reescala (en Blender la flexion
# angular es EXPLICITA: con x(h/h')^2 el voladizo de 5 mm no asienta, deriva30 30 mm -> 2 mm sin reescalarlo); quality x(h/h')^2
# SIEMPRE (en params; a 5 mm q10 inventa un frunce de lambda 32); masa y aire por la cuenta de vertices si la variante trae
# "nv": [nv_h, nv_h2] (masa TOTAL igual: la tira de 30 mm tiene 16 % menos masa con r^2). Verificada a 5 mm; a 3,3 mm NO.
EXP_CLOTH = {"pin_stiffness": 3}
# [ESC·f535] diagnostico por termino: "reescala": {"h": 10, "h2": 5, "sin": ["traccion"]} deja ese grupo SIN reescalar.
TERMINO = {"masa": ("mass", "air"), "flexion": ("bending", "bend_max", "pl_bh", "bending_damping"),
           "traccion": ("tension", "compression", "soft", "shear", "ent_c", "pl_hc"), "internos": ("sand_k", "sand_kc"), "pin": ("pin_stiffness",),
           "amort_flexion": ("bending_damping",)}   # [ESC·f535] 10-10 22:50: separado para el diagnostico (explicito en Blender)


def _fuera(var):
    sin = (var.get("reescala") or {}).get("sin", [])
    assert all(t in TERMINO for t in sin), f"termino desconocido en sin: {sin}"
    return {k for t in sin for k in TERMINO[t]}


def factor(var):
    rz = var.get("reescala")
    return None if not rz else float(rz["h2"]) / float(rz["h"])


def params(P, var):
    """P reescalado (copia) y lista de cambios. Va DESPUES de receta + receta_lab + params de la variante."""
    r = factor(var)
    if r is None:
        return P, []
    Q = dict(P); cambios = []
    fuera = _fuera(var)
    nv = (var.get("reescala") or {}).get("nv")
    for k, e in EXP.items():
        if k in Q and Q[k] > 0 and k not in fuera:
            f = float(nv[0]) / float(nv[1]) if (nv and k in ("mass", "air")) else r ** e
            Q[k] = Q[k] * f; cambios.append((k, P[k], Q[k]))
    return Q, cambios


def cloth(ES, var):
    """Lo que no es parametro de la receta: amortiguamiento de flexion y rigidez del pin, sobre el Cloth ya armado."""
    r = factor(var)
    if r is None:
        return []
    cambios = []
    fuera = _fuera(var)
    for k, e in EXP_CLOTH.items():
        if k in fuera:
            continue
        v0 = getattr(ES.s, k); setattr(ES.s, k, v0 * r ** e); cambios.append((k, v0, getattr(ES.s, k)))
    return cambios
