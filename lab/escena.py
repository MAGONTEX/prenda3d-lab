"""[ESC·f535] lab/escena.py - generador de ESCENAS MINIMAS del laboratorio (sin Blender). Escuela de Blender, frente B.

Malla con el MISMO mallador que la prenda (`prenda3d.malla_gen._triangular`: borde partido cada ~10 mm + reticula equilatera
+ Delaunay + suavizado; arista 10 mm = la de la M133 e2zzh1), en el formato de malla que lee el nucleo (`v` en m, `uv` en mm,
`f`, `groups`, `sew`, `sew_seam`, `autocol`, y para canelones `lining inst lx pocket pocket_area_m2 pinch border`).
Bloque `lab`: pines, piezas de cada probeta y colisionadores (lo lee `correr.py` y `metricas.py`; el nucleo lo ignora).

Reglas de armado (las mismas que la prenda): costura 1:1 por linea (mismo reparto en los dos lados); ninguna costura nace en
0 mm (0,5 mm de luz: un resorte de largo 0 no tiene direccion); autocolision a > 5 mm de los vertices cosidos (`sa_brd` 5 de
la M133); un vertice fijo (pin) arranca en su posicion del molde (el pin sigue a la clave de reposo).

    python lab/escena.py            -> escribe lab/escenas/*.json (b1_*, b2_*, b3_*, canelon)
"""
import json
import os
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__)); PAQ = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
from malla_lab import _triangular  # noqa: E402

H = 10.0          # arista de la malla de la M133 (m133_e2zzh1: p50 10,0 mm en todas las piezas)
LUZ = 0.5         # mm entre los dos lados de una costura al arrancar
SALIDA = os.path.join(AQUI, "escenas")


def pieza(x0, y0, w, h, lineas_x=(), paso=H):
    """Rectangulo del molde (mm) mallado como la prenda. lineas_x = lineas interiores forzadas (x constante) con el mismo reparto
    en y que el borde: ahi se cose otra pieza (margen, pespunte) o se mide (control)."""
    nx, ny = max(1, int(round(w / paso))), max(1, int(round(h / paso)))
    B = [(x0 + w * i / nx, y0) for i in range(nx)] + [(x0 + w, y0 + h * j / ny) for j in range(ny)]
    B += [(x0 + w - w * i / nx, y0 + h) for i in range(nx)] + [(x0, y0 + h - h * j / ny) for j in range(ny)]
    I, ar = [], []
    for xl in lineas_x:
        k0 = len(I); I += [(xl, y0 + h * j / ny) for j in range(1, ny)]; ar += [(k0 + j, k0 + j + 1) for j in range(ny - 2)]
    P, T, _ = _triangular(np.array(B, float), np.array(I, float).reshape(-1, 2), ar, paso, 6)
    return np.asarray(P, float), np.asarray(T, int)


class Escena:
    def __init__(self, nombre):
        self.nombre = nombre; self.UV, self.V, self.F = [], [], []; self.groups, self.P0, self.uvd = {}, {}, {}
        self.sew, self.seam = [], []; self.pin = set(); self.noauto = set()

    def agregar(self, g, P, T, d=(0.0, 0.0, 0.0), inv=False, uv_d=(0.0, 0.0)):
        """P (mm, molde) -> V0 = (P + d_xy)/1000 a z = d_z mm; uv = P + uv_d (isla corrida en el molde); inv = normal -z."""
        a = len(self.UV); T = T[:, [0, 2, 1]] if inv else T
        self.UV += (P + np.array(uv_d, float)).tolist()
        self.V += np.c_[(P + np.array(d[:2], float)) / 1000.0, np.full(len(P), d[2] / 1000.0)].tolist()
        self.F += (T + a).tolist(); self.groups[g] = [a, len(self.UV)]; self.P0[g] = P; self.uvd[g] = list(uv_d)
        return a

    def linea(self, g, x, rango=None, tol=1e-4):
        a = self.groups[g][0]; P = self.P0[g]; k = np.where(np.abs(P[:, 0] - x) < tol)[0]
        if rango is not None:
            k = k[(P[k, 1] >= rango[0] - tol) & (P[k, 1] <= rango[1] + tol)]
        k = k[np.argsort(P[k, 1])]
        return a + k, P[k]

    def coser(self, ga, gb, nombre, x, xb=None, rango=None):
        ia, pa = self.linea(ga, x, rango); ib, pb = self.linea(gb, x if xb is None else xb, rango)
        assert len(ia) == len(ib) > 0, f"{nombre}: {len(ia)} contra {len(ib)} vertices"
        assert np.abs(pa[:, 1] - pb[:, 1]).max() < 1e-3, f"{nombre}: reparto distinto en los dos lados (no es 1:1)"
        self.sew += [[int(i), int(j)] for i, j in zip(ia, ib)]; self.seam += [nombre] * len(ia)
        return len(ia)

    def fijar(self, g, cond):
        a = self.groups[g][0]; k = np.where(cond(self.P0[g]))[0]; ids = a + k
        V = np.array(self.V)[ids] * 1000.0; U = np.array(self.UV)[ids]
        assert np.abs(V[:, :2] - U).max() < 1e-6 and np.abs(V[:, 2]).max() < 1e-9, f"{g}: un pin tiene que arrancar en su molde"
        self.pin |= set(int(i) for i in ids)

    def datos(self, meta, sa_brd=5.0):
        S = np.array(self.sew, int).reshape(-1, 2); cos = set(S.ravel().tolist()); auto = []
        for g, (a, b) in self.groups.items():
            if g in self.noauto:
                continue
            P = self.P0[g]; c = [i - a for i in cos if a <= i < b]
            dm = np.linalg.norm(P[:, None, :] - P[c][None], axis=2).min(1) if c else np.full(len(P), 1e9)
            auto += [a + int(k) for k in np.where(dm > sa_brd)[0] if a + int(k) not in self.pin]
        D = dict(v=self.V, f=self.F, uv=self.UV, groups=self.groups, sew=self.sew, sew_seam=self.seam, autocol=sorted(auto))
        D["lab"] = dict(meta, escena=self.nombre, pin=sorted(self.pin), uv_d=self.uvd, n_v=len(self.V), sa_brd=sa_brd)
        return D

    def guardar(self, meta, **kw):
        D = self.datos(meta, **kw); os.makedirs(SALIDA, exist_ok=True); ruta = os.path.join(SALIDA, self.nombre + ".json")
        json.dump(D, open(ruta, "w", encoding="utf-8"))
        print(f"{self.nombre}: {len(self.V)} v {len(self.F)} tri {len(self.sew)} pares {len(D['autocol'])} autocol {len(self.pin)} pin -> {ruta}")
        return D


# ------------------------------------------------------------------------------------------------ B1 costura-bisagra
def b1(margen=0.0, pespunte=False, nombre="b1_tiras"):
    """Voladizo de 40 mm de ancho: tira S = A (30 mm empotrados + 80 libres [+ margen bajo B]) cosida a B (80 mm) en x = 110;
    tira C = control continuo de 190 mm con una linea en x = 110 (mismo reparto que la costura). Voladizo l = 160 mm.
    margen > 0: A sigue `margen` mm por debajo de B (margen planchado hacia B; B arranca 4 mm arriba = 2 x self_d).
    pespunte: segunda fila de pares en el canto del margen (x = 110 + margen) = costura cargada."""
    E = Escena(nombre); W, XS, L, YC, XR = 40.0, 110.0, 190.0, 100.0, 30.0
    la = [XR] + ([XS] if margen > 0 else [])
    PA, TA = pieza(0, 0, XS + margen, W, lineas_x=la); E.agregar("A", PA, TA)
    PB, TB = pieza(XS, 0, L - XS, W, lineas_x=[XS + margen] if pespunte else [])
    E.agregar("B", PB, TB, d=(LUZ, 0, 0) if margen <= 0 else (0, 0, 4.0))
    PC, TC = pieza(0, YC, L, W, lineas_x=[XR, XS]); E.agregar("C", PC, TC)
    E.coser("A", "B", "costura", XS)
    if pespunte:
        E.coser("A", "B", "pespunte", XS + margen)
    for g in ("A", "C"):
        E.fijar(g, lambda P: P[:, 0] <= XR + 1e-6)
    meta = dict(banco="b1", margen=margen, pespunte=bool(pespunte), colisionadores=[],
                tiras={"S": dict(piezas=["A", "B"], x_costura=XS, x_raiz=XR, x_punta=L), "C": dict(piezas=["C"], x_costura=XS, x_raiz=XR, x_punta=L)})
    return E.guardar(meta)


def b1_cilindro(nombre="b1_cil150"):
    """Dos paneles de 150 x 100 mm cosidos por una costura paralela al eje, apoyados planos sobre un cilindro R 150 (eje y), costura arriba."""
    E = Escena(nombre); R, z0 = 150.0, 150.0 + 1.0 + 4.0 + 3.0
    P1, T1 = pieza(0, 0, 150, 100); P2, T2 = pieza(150, 0, 150, 100)
    E.agregar("P1", P1, T1, d=(-150, -50, z0)); E.agregar("P2", P2, T2, d=(-150 + LUZ, -50, z0))
    E.coser("P1", "P2", "costura", 150.0)
    meta = dict(banco="b1", colisionadores=[dict(tipo="cilindro", r=R / 1000, largo=0.30, eje="y", centro=[0, 0, 0])],
                paneles=["P1", "P2"], x_costura=150.0)
    return E.guardar(meta)


# ------------------------------------------------------------------------------------------------ B2 salto de reposo
def b2(fijo=False, nombre="b2_panel"):
    """Panel de 145 x 300 mm (molde del plan). El arranque lo escala `correr.py` (escala s alrededor del centro). Sin colisionadores.
    fijo: los dos lados cortos fijos EN SU ARRANQUE (cosidos a vecinos que no se mueven). Testigo: dos triangulos fijos cosidos
    lejos (el nucleo necesita al menos una costura para sus guardas)."""
    E = Escena(nombre); P, T = pieza(0, 0, 300, 145); E.agregar("panel", P, T)
    for g, x0 in (("tg1", 1000.0), ("tg2", 1010.0 + 2.0)):
        Pt = np.array([[x0, 0], [x0 + 10, 0], [x0, 10]], float); E.agregar(g, Pt, np.array([[0, 1, 2]])); E.fijar(g, lambda P: P[:, 0] > -1)
        E.noauto.add(g)
    E.sew.append([E.groups["tg1"][0] + 1, E.groups["tg2"][0]]); E.seam.append("testigo")
    meta = dict(banco="b2", fijo=bool(fijo), colisionadores=[], escala_piezas=["panel"], escala_centro=[150.0, 72.5],
                pin_en_v0=["panel"] if fijo else [])
    if fijo:
        a = E.groups["panel"][0]; k = np.where((P[:, 0] < 1e-6) | (P[:, 0] > 300 - 1e-6))[0]; meta["pin_panel"] = (a + k).tolist()
    return E.guardar(meta)


# ------------------------------------------------------------------------------------------------ B3 sandwich hs-ht
def b3(gap=5.5, nombre="b3_sandwich"):
    """Mini-cuello en voladizo, con los nombres de la M133 para que corran SIN CAMBIOS sandwich_rotar_caras / sandwich_reposo /
    sandwich_resortes_internos de m133_reglas y transl / taper_w / bary_map / sand_stats de m133_sandwich.
    back = escote fijo (30 x 200). R: hsR (cascara, 100 x 40) con htR (vista) DEBAJO a `gap` mm; L: hsL con htL ARRIBA (sand_zs=-1);
    ctl = una sola capa (control). Costuras como el cuello real: hs-back 'cuello-capucha', ht-back 'vista-escote', punta ht-hs
    'capucha-ht base' (el canto)."""
    E = Escena(nombre); T = (0.0, 300.0)
    Pb, Tb = pieza(-30, 0, 30, 200); E.agregar("back", Pb, Tb); E.fijar("back", lambda P: P[:, 0] > -1e9)
    for s, y0, inv_hs, zt in (("R", 0.0, False, -gap), ("L", 80.0, True, +gap)):
        P, Tr = pieza(0, y0, 100, 40)
        E.agregar("hs" + s, P, Tr, d=(LUZ, 0, 0), inv=inv_hs)
        E.agregar("ht" + s, P, Tr, d=(LUZ, 0, zt), inv=not inv_hs, uv_d=T)
        E.coser("hs" + s, "back", "cuello-capucha", 0.0, rango=(y0, y0 + 40))
        E.coser("ht" + s, "back", "vista-escote " + s, 0.0, rango=(y0, y0 + 40))
        E.coser("ht" + s, "hs" + s, "capucha-ht base " + s, 100.0)
    P, Tc = pieza(0, 160, 100, 40); E.agregar("ctl", P, Tc, d=(LUZ, 0, 0)); E.coser("ctl", "back", "ctl-base", 0.0, rango=(160, 200))
    meta = dict(banco="b3", gap=gap, colisionadores=[], probetas={"R": ["hsR", "htR"], "L": ["hsL", "htL"], "C": ["ctl"]}, x_punta=100.0)
    return E.guardar(meta)


# ------------------------------------------------------------------------------------------------ canelones (grupo 2)
def canelon(n_canales=3, nombre="canelon"):
    """Placa de 300 x 145 mm con `n_canales` canelones (pespuntes cada 300/n en u): cascara `cn` + pared interior `cn_f` (copia
    vertice a vertice, normal opuesta), cosidas en el borde y en los pespuntes; bolsillos cn0.. por canal (presion del nucleo:
    piezas_inyectadas = [cn]). Apoyada en una mesa. Formato de la M133 (inst, lx, lining, pocket, pinch, border)."""
    E = Escena(nombre); w, h = 300.0, 145.0; lx = [w * k / n_canales for k in range(1, n_canales)]
    P, T = pieza(0, 0, w, h, lineas_x=lx); z0 = 1.0 + 4.0 + 6.0
    a = E.agregar("cn", P, T, d=(0, 0, z0)); af = E.agregar("cn_f", P, T, d=(0, 0, z0), inv=True, uv_d=(0, 200))
    n = len(P); borde = [i for i in range(n) if P[i, 0] < 1e-6 or P[i, 0] > w - 1e-6 or P[i, 1] < 1e-6 or P[i, 1] > h - 1e-6]
    linea = [i for i in range(n) if any(abs(P[i, 0] - x) < 1e-4 for x in lx)]
    for i in sorted(set(borde) | set(linea)):
        E.sew.append([a + i, af + i]); E.seam.append("canal" if i in linea else "borde")
    ch = (np.array(lx)[None, :] < P[:, 0][:, None]).sum(1)
    D = E.datos(dict(banco="canelon", colisionadores=[dict(tipo="mesa", z=0.0, lado=0.6)], datos_reglas=dict(piezas_inyectadas=["cn"])))
    nf = len(T); D["inst"] = {"cn": dict(off=a, foff=0, nf=nf, key="cn"), "cn_f": dict(off=af, foff=nf, nf=nf, key="cn")}
    D["lx"] = {"cn": lx}; D["lining"] = {"cn": "cn_f"}; D["border"] = [a + i for i in borde] + [af + i for i in borde]
    D["pinch"] = [a + i for i in linea] + [af + i for i in linea]
    D["pocket"] = [None] * (2 * n)
    for i in range(n):
        if i not in borde and i not in linea:
            D["pocket"][a + i] = D["pocket"][af + i] = f"cn{int(ch[i])}"
    D["pocket_area_m2"] = {f"cn{k}": (w / n_canales) * h / 1e6 for k in range(n_canales)}
    os.makedirs(SALIDA, exist_ok=True); json.dump(D, open(os.path.join(SALIDA, nombre + ".json"), "w", encoding="utf-8"))
    print(f"{nombre}: {len(D['v'])} v {len(D['f'])} tri {len(D['sew'])} pares, {n_canales} bolsillos, pinch {len(D['pinch'])}")
    return D


if __name__ == "__main__":
    b1(); b1(margen=10.0, nombre="b1_tiras_m10"); b1(margen=20.0, nombre="b1_tiras_m20"); b1(margen=10.0, pespunte=True, nombre="b1_tiras_m10p")
    b1_cilindro(); b2(); b2(fijo=True, nombre="b2_panel_fijo"); b3(); b3(gap=2.0, nombre="b3_sandwich_g2"); canelon()
