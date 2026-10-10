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
EXP_CLOTH = {"bending_damping": -2, "pin_stiffness": 3}


def factor(var):
    rz = var.get("reescala")
    return None if not rz else float(rz["h2"]) / float(rz["h"])


def params(P, var):
    """P reescalado (copia) y lista de cambios. Va DESPUES de receta + receta_lab + params de la variante."""
    r = factor(var)
    if r is None:
        return P, []
    Q = dict(P); cambios = []
    for k, e in EXP.items():
        if k in Q and Q[k] > 0:
            Q[k] = Q[k] * r ** e; cambios.append((k, P[k], Q[k]))
    return Q, cambios


def cloth(ES, var):
    """Lo que no es parametro de la receta: amortiguamiento de flexion y rigidez del pin, sobre el Cloth ya armado."""
    r = factor(var)
    if r is None:
        return []
    cambios = []
    for k, e in EXP_CLOTH.items():
        v0 = getattr(ES.s, k); setattr(ES.s, k, v0 * r ** e); cambios.append((k, v0, getattr(ES.s, k)))
    return cambios
