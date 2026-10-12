"""Medidas de la ficha sobre la prenda 3D por RECORRIDO sobre la tela (M1195, r5). Sin scipy (corre tambien dentro de Blender).

Las cotas de la ficha estan dibujadas en el molde como lineas de capa 8 y la malla las trae como vertices forzados
(D["lineas"][pieza][k]["v"]): una cota en 3D = largo de esa polilinea en el cuadro. Los anillos (ruedo D, puno L) se recorren por el
ORDEN DEL CONTORNO de cada pieza (inst[p]: los vertices off..off+nb son el borde en orden), no por azimut (r4: saltaba entre piezas).
Cotas (ficha talle L, mm). El molde ya difiere de la ficha: se informa 3D, molde (uv) y % contra los dos.
  A    hombro a hombro       espR l1 + espL l1 (linea de hombro de la espalda)                         ficha 530   molde 522,6
  C    pecho, media vuelta   delR l1 + cosR l0 + cosR l2 + espR l3 + 4 (media tira del cierre)         ficha 620   molde ~608
  D    ruedo, media vuelta   contorno del ruedo de las 6 piezas del torso + 8 de la tira, / 2          ficha 590
  F    largo delantero       delR l3 + l2 (borde delantero, ruedo -> escote) + alto del cuello al frente (molde)  ficha 685
  G    largo centro espalda  costura CB (marcador cb)                                                  ficha 660 + 25 de origen = 685
  H    ancho de hombro       espR l4 (hombro natural)                                                  ficha 185   molde 181,8
  J    sisa recta            (msaR l0 + bmR l0) / 2                                                    ficha 230   molde 228
  K    largo de manga        msaR l1 + msbR l0 (linea central por el corte del codo), R y L            ficha 655   molde 649
  K1A K2A K3A anchos de manga (msaR l2 + bmR l1) / 2, (msbR l2 + bmR l3) / 2, (msbR l1 + bmR l2) / 2  ficha 215 / 195 / 175
  L    puno, media vuelta    contorno del puno (msb + bm) / 2, promedio R y L                           ficha 135
Hombro apoyado: distancia con signo de espR/espL l4 (hombro natural) a la piel; la costura del canesu pasa 55-61 mm al frente y no sirve.
"""
import numpy as np

FICHA = dict(A=530.0, C=620.0, D=590.0, F=685.0, G=685.0, H=185.0, J=230.0, K=655.0, K1A=215.0, K2A=195.0, K3A=175.0, L=135.0)
ZIP_W = 8.0


def _poli(X, ids):
    ids = np.asarray(ids, int)
    return float(np.linalg.norm(np.diff(X[ids], axis=0), axis=1).sum()) if len(ids) > 1 else 0.0


def _linea(D, p, k):
    return np.array(D["lineas"][p][k]["v"], int)


def runs_contorno(D, p, ids_set):
    """tramos contiguos (orden de contorno, ciclico) del borde de la pieza p que caen en ids_set."""
    i = D["inst"][p]; b = np.arange(i["off"], i["off"] + i["nb"]); m = np.array([j in ids_set for j in b])
    if not m.any():
        return []
    if m.all():
        return [np.r_[b, b[0]]]
    k0 = int(np.argmin(m)); b = np.roll(b, -k0); m = np.roll(m, -k0); runs, cur = [], []
    for j, ok in zip(b, m):
        if ok:
            cur.append(int(j))
        elif cur:
            runs.append(np.array(cur)); cur = []
    if cur:
        runs.append(np.array(cur))
    return runs


def anillo_contorno(D, X, piezas, ids_set):
    return float(sum(_poli(X, r) for p in piezas for r in runs_contorno(D, p, ids_set)))


def aristas_contorno(D, p):
    """aristas del contorno de la pieza p entre esquinas consecutivas (inst.cs): lista de arrays de indices, con las dos esquinas."""
    i = D["inst"][p]; b = np.arange(i["off"], i["off"] + i["nb"]); s = np.array(i["s"]); cs = list(i["cs"]); per = i["per"]
    if not cs:
        return [np.r_[b, b[0]]]
    out = []
    for a, c in zip(cs, cs[1:] + [cs[0] + per]):
        m = (s >= a - 0.5) & (s <= c + 0.5)
        if c > per:
            m |= (s <= c - per + 0.5)
        sel = b[m]; o = np.argsort(np.where(s[m] < a - 0.5, s[m] + per, s[m])); out.append(sel[o])
    return out


def arista_baja(D, p):
    """la arista del contorno con menor v media en el molde (ruedo de un panel, puno de una manga)."""
    UV = np.array(D["uv"]); ar = aristas_contorno(D, p)
    return ar[int(np.argmin([UV[r, 1].mean() for r in ar]))]


def anillo_bajo(D, X, piezas):
    return float(sum(_poli(X, arista_baja(D, p)) for p in piezas))


def alto_cuello_frente(D):
    """alto del cuello en su extremo delantero, en el molde (uv): arista de la punta de la hoja (|du| < 30, |dv| > 50: N1 85) + alto del pie en su extremo."""
    UV = np.array(D["uv"]); tot = 0.0
    for r in aristas_contorno(D, "cuA"):
        du, dv = np.ptp(UV[r, 0]), np.ptp(UV[r, 1])
        if du < 30 and dv > 50:
            tot += _poli(UV, r); break
    i = D["inst"]["pieA"]; b = np.arange(i["off"], i["off"] + i["nb"]); u = UV[b, 0]; sel = b[u < u.min() + 10.0]
    tot += float(np.ptp(UV[sel, 1]))
    return tot


def medir(D, X, XM=None):
    """X: posiciones (mm, N x 3). XM: molde (uv, N x 2) para la columna 'molde'. Devuelve dict cota -> (3d, molde)."""
    if XM is None:
        XM = np.array(D["uv"])
    mk = D["marcadores"]; L = lambda p, k, P: _poli(P, _linea(D, p, k))
    out = {}
    for P, key in ((X, 0), (XM, 1)):
        m = {}
        m["A"] = L("espR", 1, P) + L("espL", 1, P)
        m["C"] = L("delR", 1, P) + L("cosR", 0, P) + L("cosR", 2, P) + L("espR", 3, P) + ZIP_W / 2
        m["D"] = (anillo_bajo(D, P, ("delR", "delL", "cosR", "cosL", "espR", "espL")) + ZIP_W) / 2
        m["F"] = L("delR", 3, P) + L("delR", 2, P) + alto_cuello_frente(D)
        m["G"] = _poli(P, mk["cb"])
        m["H"] = L("espR", 4, P)
        m["J"] = (L("msaR", 0, P) + L("bmR", 0, P)) / 2
        m["K"] = (L("msaR", 1, P) + L("msbR", 0, P) + L("msaL", 1, P) + L("msbL", 0, P)) / 2
        m["K_R"] = L("msaR", 1, P) + L("msbR", 0, P); m["K_L"] = L("msaL", 1, P) + L("msbL", 0, P)
        m["K1A"] = (L("msaR", 2, P) + L("bmR", 1, P)) / 2; m["K2A"] = (L("msbR", 2, P) + L("bmR", 3, P)) / 2; m["K3A"] = (L("msbR", 1, P) + L("bmR", 2, P)) / 2
        m["L_R"] = anillo_bajo(D, P, ("msbR", "bmR")) / 2; m["L_L"] = anillo_bajo(D, P, ("msbL", "bmL")) / 2
        m["L"] = (m["L_R"] + m["L_L"]) / 2
        for k, v in m.items():
            out.setdefault(k, [0.0, 0.0])[key] = v
    return out


def texto(med, cotas=("G", "A", "C", "D", "F", "H", "J", "K", "K1A", "K2A", "K3A", "L")):
    """una linea: cota 3d (ficha: %ficha | molde: %molde)"""
    return " | ".join(f"{k} {med[k][0]:.0f} (ficha {FICHA[k]:.0f} {100 * (med[k][0] / FICHA[k] - 1):+.1f} % | molde {med[k][1]:.0f} {100 * (med[k][0] / med[k][1] - 1):+.1f} %)" for k in cotas)


def fuera(med, tol=0.03, cotas=("G", "A", "C", "D", "F", "H", "J", "K", "K1A", "K2A", "K3A", "L")):
    """cotas fuera de +-tol contra la FICHA (la compuerta) y, aparte, contra el molde (la tela se estiro o se encogio)."""
    f_ficha = [k for k in cotas if abs(med[k][0] / FICHA[k] - 1) > tol]
    f_molde = [k for k in cotas if abs(med[k][0] / med[k][1] - 1) > tol]
    return f_ficha, f_molde


def hombro_natural(D):
    return np.r_[_linea(D, "espR", 4), _linea(D, "espL", 4)]
