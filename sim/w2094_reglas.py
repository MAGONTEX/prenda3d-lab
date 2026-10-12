"""Reglas de la W2094 QUARTZ (bomber de ecocuero de MUJER talle M, [x]; cuello alto de dos caras, cintura doblada con elastico, puno doble
con broche, cierre central; forro acolchado SUMADO a la cascara). Humo 1 (2026-10-10, tecnico-3d).

El nucleo (`nucleo.py`) llama hooks por los NOMBRES de la M133 con `_regla(ES, "nombre")` y saltea los que este modulo no define. Plantilla:
`m1195_reglas.py` (mismo proveedor, misma capa unica). Lo que hace cada hook EN ESE PUNTO del nucleo:
  filtrar_costuras_diagnostico  antes de armar la escena   -> exige la construccion de `49-w2094/molderia/arma_malla_v0.py` (strip `zipper`, `cuff`, grupos)
  sandwich_rotar_caras          con el cuerpo cargado      -> solo colisiona la piel completa del npz (sin tubos de brazo ni cabeza del maniqui)
  broches_con_altura            al armar la tela           -> [ESC·f535] T2e10: broche del puno con altura (sep_h > 0; defecto 0 = identico)
  cuello_flexion_por_capa       con la rigidez cargada     -> flexion por zona (w2094_reglas.json): cuello x3, cintura doblada x2, franja de la vista x2;
                                                              el strip del cierre queda en bend_max (nucleo) y el puno en w_cuff (nucleo, cuff_on=1)
  metricas_definir              antes del bucle            -> indices: ruedo (eje de la cintura), punos, hombro, cuello, strip, tabla; cuerpo y cabeza
  metricas_por_cuadro           cada 6 cuadros             -> caida desde f1 (ruedo R/L/CB/CF, costados vs V0), hombro apoyado, cuello-menton, ancho y
                                                              torsion del strip, tabla cerrada, mitades de la cintura, medidas A/G/K/L/F de la ficha
Sin presion, sin sandwich del M133, sin broches, sin capucha. El elastico de la cintura (factor 0,706 en u) NO entra en el humo 1: es la palanca 2
(reposo por shape key). Datos: w2094_reglas.json (ES.RD). CAPAS = capas de prenda.json que estas reglas saben tratar (lanzar.py las suma a las del nucleo).
"""
import json
import math
import os

import bpy
import numpy as np

CAPAS = {"forro"}     # el forro acolchado entra como masa + espesor de la cascara (PLAN-SIM-W2094 1): sin capa propia en la sim


def _pesos(ES, nombre):
    W = np.zeros(ES.NV); vg = ES.gar.vertex_groups[nombre]
    for v in ES.gar.data.vertices:
        for g in v.groups:
            if g.group == vg.index:
                W[v.index] = g.weight
    return W


def _ids(ES, *grupos):
    return np.array([i for g in grupos for i in range(*ES.D["groups"][g])], int)


def filtrar_costuras_diagnostico(ES):
    """La malla trae la construccion hecha (molderia/arma_malla_v0.py): strip del cierre (`zipper`), punos (`cuff`), cintura ya doblada."""
    falt = [k for k in ("zipper", "cuff", "inst", "sew_seam") if not ES.D.get(k)]
    assert not falt, f"malla sin la construccion de la W2094 {falt}: correr 49-w2094/molderia/arma_malla_v0.py"
    assert "cierre" in ES.D["groups"], "malla sin el grupo `cierre` (strip del cierre)"
    ES.log(f"W2094 construccion: strip del cierre {len(ES.D['zipper'])} v | punos {len(ES.D['cuff'])} v | costuras {len(ES.D['sew'])} pares | "
           f"grupos {len(ES.D['groups'])} | generador {ES.D.get('generador', {})}")


def sandwich_rotar_caras(ES):
    """Cuerpo = piel completa con brazos (npz). Los tubos de brazo y la cabeza del maniqui parametrico no colisionan."""
    quitados = []
    for o in list(ES.MANIQUI):
        if o.name.startswith("CD_maniqui_"):
            for m in [m for m in o.modifiers if m.type == "COLLISION"]:
                o.modifiers.remove(m); quitados.append(o.name)
            o.hide_viewport = True; o.hide_render = True
    ES.TFOBJ = [o for o in ES.TFOBJ if not o.name.startswith("CD_maniqui_")]
    vivos = [(o.name, round(o.collision.cloth_friction, 1), round(o.collision.thickness_outer, 4)) for o in ES.MANIQUI if any(m.type == "COLLISION" for m in o.modifiers)]
    assert vivos and all(n.startswith("CD_cuerpo") for n, _, _ in vivos), f"colisionadores inesperados: {vivos}"
    ES.log(f"W2094 cuerpo: solo colisiona la piel completa {vivos} (friccion, espesor) | maniqui sin colision: {quitados}")


def _zonas(ES):
    """Zonas de rigidez por indices de vertice (se calculan de la malla, no vienen en el json)."""
    D = ES.D; UV = np.array(D["uv"], float)
    z = {"cuello": _ids(ES, "cue", "pie"), "cintura": _ids(ES, "cin", "citR", "citL")}
    # franja de la vista: vertices de delR/delL a <= ancho_mm (uv) de su borde delantero (los vertices cosidos al strip)
    ancho = float(ES.RD.get("vista_franja_mm", 128.4)); vis = []
    for g in ("delR", "delL"):
        a, b = D["groups"][g]
        borde = sorted({x for (x, y), nm in zip(D["sew"], D["sew_seam"]) if nm.startswith("borde delantero con el cierre") and a <= x < b})
        if not borde:
            continue
        B = UV[borde]; I = np.arange(a, b)
        d = np.empty(len(I))
        for k in range(0, len(I), 512):
            d[k:k + 512] = np.linalg.norm(UV[I[k:k + 512]][:, None, :] - B[None], axis=2).min(1)
        vis += [int(i) for i in I[d <= ancho]]
    z["vista"] = np.array(vis, int)
    return z


def cuello_flexion_por_capa(ES):
    """Flexion por zona: b_zona = mult x bending, como peso del grupo 'rigidez' (lineal entre bending y bend_max)."""
    mult = dict(ES.RD.get("flexion_zonas", {})); b0, bm = ES.P["bending"], ES.P["bend_max"]
    por_tag = (ES.RD.get("flexion_zonas_por_tag") or {}).get(str(ES.TAG).rstrip("b"))        # ronda 5: una corrida puede cambiar la flexion de una zona (palanca con nombre)
    if por_tag:
        mult.update(por_tag); ES.log(f"W2094 FLEXION por tag {ES.TAG}: {por_tag}")
    W = _pesos(ES, "rigidez"); W0 = W.copy(); zip_ = set(ES.D["zipper"]); res = []
    ES.ZONAS = _zonas(ES)
    for zn, m in mult.items():
        ids = np.array([i for i in ES.ZONAS.get(zn, []) if i not in zip_], int)
        if not len(ids):
            continue
        w = float(np.clip((m * b0 - b0) / max(bm - b0, 1e-9), 0.0, 1.0)); W[ids] = np.maximum(W[ids], w)
        res.append(f"{zn} x{m:g} -> {b0 + (bm - b0) * w:.0f} ({len(ids)} v, peso {w:.3f})")
    chg = np.where(np.abs(W - W0) > 1e-9)[0]
    for i in chg:
        ES.vrig.add([int(i)], float(W[i]), "REPLACE")
    ES.log(f"W2094 FLEXION por zona (base {b0:g}, tope {bm:g}, cierre {len(zip_)} v en {bm:g}, puno por w_cuff): " + " | ".join(res) + f" | {len(chg)} pesos escritos")


def _elastico_blando(ES):
    """Ronda 4: el elastico de la cintura con su PROPIA rigidez a traccion (w2094_reglas.json elastico_cintura.tension; None = la de la tela).
    Con la traccion de la tela (200) la banda encogida a 0,706 es un aro rigido de 937 mm: no pasa la cadera (981 a z 867) y trepa a la cintura
    natural (z 988), sostiene la prenda y despega el hombro 34 mm. Se hace con el grupo `cascara` (peso 0 en `cin` -> traccion base; el resto
    en 1 -> traccion de la receta). Corre en metricas_definir: el modificador Cloth ya existe y el bucle todavia no arranco."""
    t = (ES.RD.get("elastico_cintura") or {}).get("tension")
    t = ((ES.RD.get("elastico_cintura") or {}).get("tension_por_tag") or {}).get(str(ES.TAG).rstrip("b"), t)      # ronda 5: palanca con nombre
    if not t or ES.P["soft"] <= 0:
        ES.log("W2094 elastico: traccion de la tela (sin elastico_cintura.tension)"); return
    W = _pesos(ES, "cascara"); bajo = int((W < 0.999).sum()); ids = _ids(ES, "cin")
    assert bajo == 0, f"elastico blando: {bajo} vertices con peso de cascara < 1 antes de tocar (quedarian con la traccion del elastico)"
    ES.s.tension_stiffness = float(t); ES.s.tension_stiffness_max = ES.P["tension"]
    ES.vcas.add([int(i) for i in ids], 0.0, "REPLACE")
    ES.log(f"W2094 ELASTICO BLANDO: traccion {float(t):g} en cin ({len(ids)} v, peso de cascara 0; compresion {ES.s.compression_stiffness:g}) | resto traccion "
           f"{ES.s.tension_stiffness_max:g}, compresion {ES.s.compression_stiffness_max:g}")


def metricas_definir(ES):
    _elastico_blando(ES)
    D = ES.D; UV = np.array(D["uv"], float); G = D["groups"]
    B = np.load(ES.RUTA(ES.BODY)); ES.BV20 = B["V20"]; ES.BV8 = B["V8"]; ES.BCAB = B["cabeza"].astype(bool); ES.BT = B["T"]
    ES.HEADV = np.unique(ES.BT[ES.BCAB]) if ES.BCAB.any() else np.array([], int)
    ES.MENTON = (B["menton_mm"] / 1000.0) if "menton_mm" in B.files else None
    mk = {}
    ejes = ES.RD.get("eje_cintura_v", {"cin": 1969.8, "citR": 1997.0, "citL": 1997.0})
    mk["ruedo"] = np.array([i for g, vf in ejes.items() for i in range(*G[g]) if abs(UV[i, 1] - vf) < 0.6], int)     # eje de la banda = ruedo real
    for s_ in "RL":
        a, b = G["pue" + s_]; I = np.arange(a, b); mk["puno_" + s_] = I[UV[I, 1] < UV[I, 1].min() + 0.6]              # canto libre del puno (abajo en el DXF)
        mk["hombro_costura_" + s_] = np.array(sorted({x for (x, y), nm in zip(D["sew"], D["sew_seam"]) if nm == "hombro " + s_ and G["del" + s_][0] <= x < G["del" + s_][1]}), int)
        mk["tabla_" + s_] = np.array([(x, y) for (x, y), nm in zip(D["sew"], D["sew_seam"]) if nm.startswith("tabla del puno") and nm.endswith(s_)], int)
    mk["hombro_R"] = int(mk["hombro_costura_R"][np.argmin(UV[mk["hombro_costura_R"], 0])]) if len(mk["hombro_costura_R"]) else 0   # extremo de la sisa
    mk["hombro_L"] = int(mk["hombro_costura_L"][np.argmax(UV[mk["hombro_costura_L"], 0])]) if len(mk["hombro_costura_L"]) else 0
    a, b = G["cue"]; I = np.arange(a, b); mk["canto_cuello"] = I[UV[I, 1] > UV[I, 1].max() - 0.6]
    a, b = G["cierre"]; n2 = (b - a) // 2; mk["zip_filas"] = np.c_[np.arange(a, a + n2), np.arange(b - 1, a + n2 - 1, -1)]   # (R_k, L_k)
    a, b = G["esp"]; I = np.arange(a, b); xc = 0.5 * (UV[I, 0].min() + UV[I, 0].max()); mk["cb"] = I[np.abs(UV[I, 0] - xc) < 4.6][np.argsort(-UV[I[np.abs(UV[I, 0] - xc) < 4.6], 1])]
    ES.MK = mk; ES.F1 = None
    ES.log(f"W2094 metricas: ruedo (eje de la cintura) {len(mk['ruedo'])} v, punos {len(mk['puno_R'])}/{len(mk['puno_L'])}, hombro costura {len(mk['hombro_costura_R'])}/{len(mk['hombro_costura_L'])} v, "
           f"canto del cuello {len(mk['canto_cuello'])} v, filas del strip {len(mk['zip_filas'])}, CB {len(mk['cb'])} v, tabla {len(mk['tabla_R'])}/{len(mk['tabla_L'])} pares | "
           f"cuerpo {len(ES.BV20)} v, cabeza {len(ES.HEADV)} v, menton {None if ES.MENTON is None else np.round(ES.MENTON * 1000)}")


def _cuerpo(ES):
    if ES.P["arm_end"] >= 0 and ES.P["arm_end"] != ES.P["abd_end"]:
        t = float(np.clip((ES.f - ES.P["arm_f0"]) / max(ES.P["arm_f1"] - ES.P["arm_f0"], 1), 0, 1))
    else:
        t = 0.0
    return ES.BV20 * (1 - t) + ES.BV8 * t


def _dmin(P, Q):
    out = np.empty(len(P))
    for a in range(0, len(P), 256):
        d = np.linalg.norm(P[a:a + 256, None, :] - Q[None, :, :], axis=2); out[a:a + 256] = d.min(1)
    return out


def _numeros(ES, X):
    mk = ES.MK; H = X[mk["ruedo"]]
    Z = X[mk["zip_filas"]]
    return dict(ruedo_R=float(np.median(H[H[:, 0] < 0, 2]) * 1000), ruedo_L=float(np.median(H[H[:, 0] > 0, 2]) * 1000),
                ruedo_CB=float(H[H[:, 1] > np.percentile(H[:, 1], 90), 2].mean() * 1000), ruedo_CF=float(Z[0].mean(0)[2] * 1000),
                puno_R=float(X[mk["puno_R"], 2].mean() * 1000), puno_L=float(X[mk["puno_L"], 2].mean() * 1000),
                zip_ancho=float(np.linalg.norm(Z[:, 0] - Z[:, 1], axis=1).mean() * 1000), zip_ancho_max=float(np.linalg.norm(Z[:, 0] - Z[:, 1], axis=1).max() * 1000),
                zip_x=float(Z.mean(1)[:, 0].mean() * 1000), zip_x_ruedo=float(Z.mean(1)[:3, 0].mean() * 1000), zip_x_top=float(Z.mean(1)[-3:, 0].mean() * 1000))


def metricas_por_cuadro(ES):
    X = ES.X; mk = ES.MK; n = _numeros(ES, X)
    if ES.F1 is None:
        ES.F1 = dict(n)
    f1 = ES.F1; BV = _cuerpo(ES)
    hom = np.r_[mk["hombro_costura_R"], mk["hombro_costura_L"]]; dh = _dmin(X[hom], BV) * 1000 if len(hom) else np.array([float("nan")])
    cue = _ids(ES, "cue", "pie"); dcab = _dmin(X[cue], BV[ES.HEADV]) * 1000 if len(ES.HEADV) else np.array([float("nan")])
    dmen = float(np.linalg.norm(X[cue] - ES.MENTON, axis=1).min() * 1000) if ES.MENTON is not None else float("nan")
    tab = {s_: float(np.linalg.norm(X[mk["tabla_" + s_][:, 0]] - X[mk["tabla_" + s_][:, 1]], axis=1).max() * 1000) if len(mk["tabla_" + s_]) else float("nan") for s_ in "RL"}
    dz_cos = {s_: float((X[_ids(ES, "del" + s_), 2].mean() - ES.V0[_ids(ES, "del" + s_), 2].mean()) * 1000) for s_ in "RL"}
    A = float(np.linalg.norm(X[mk["hombro_R"]] - X[mk["hombro_L"]]) * 1000)
    G = float(np.linalg.norm(np.diff(X[mk["cb"]], axis=0), axis=1).sum() * 1000) if len(mk["cb"]) > 1 else float("nan")
    K = {s_: float(np.linalg.norm(X[mk["hombro_" + s_]] - X[mk["puno_" + s_]].mean(0)) * 1000) for s_ in "RL"}
    ES.log(f"   W2094 CAIDA desde f1: ruedo R {n['ruedo_R'] - f1['ruedo_R']:+.0f} L {n['ruedo_L'] - f1['ruedo_L']:+.0f} CB {n['ruedo_CB'] - f1['ruedo_CB']:+.0f} CF {n['ruedo_CF'] - f1['ruedo_CF']:+.0f} mm | "
           f"delanteros z vs V0 R {dz_cos['R']:+.0f} L {dz_cos['L']:+.0f} | R-L ruedo {n['ruedo_R'] - n['ruedo_L']:+.0f} puno {n['puno_R'] - n['puno_L']:+.0f} mm")
    ES.log(f"   W2094 HOMBRO costura-piel med {np.median(dh):.1f} p95 {np.percentile(dh, 95):.1f} max {dh.max():.1f} mm | CUELLO-cabeza min {dcab.min():.1f} mm, cuello-menton {dmen:.1f} mm | "
           f"STRIP ancho med {n['zip_ancho']:.1f} max {n['zip_ancho_max']:.1f} mm (objetivo 18), x ruedo {n['zip_x_ruedo']:+.0f} top {n['zip_x_top']:+.0f} (torsion {n['zip_x_top'] - n['zip_x_ruedo']:+.0f}) | "
           f"TABLA abierta R {tab['R']:.1f} L {tab['L']:.1f} mm")
    ES.log(f"   W2094 FICHA A hombro-hombro (510) {A:.0f} | G CB canesu->eje cintura (molde ~606) {G:.0f} | K hombro->puno R/L (560) {K['R']:.0f}/{K['L']:.0f} mm")


def broches_con_altura(ES):
    """[ESC·f535] W2094 r7 T2e paso 10: broche del puno CON ALTURA en lugar de los 3 resortes de largo 0 'broche puno R/L' por lado.
    El resorte de largo 0 clava la punta B sobre la A (el V0 v8r las junta en una carpa: A sube ~3 mm, B baja ~2,7) y en la caida (f4-f16) la luz
    del solape se cierra a 1,3-2,6 mm en los 6 lados (T2e9). Aca el broche cerrado separa las capas sep_h mm durante TODA la sim.
    Requiere un V0 con el broche ya abierto (`49-w2094/sim/qc_r7/t2e10_v0.py`: a en la superficie de A, b a sep_h mm sobre a): si |b - a| no es
    sep_h (+-0,5 mm), falla. Por par (b = el mas lejos del centro del puno, punta B; a = punta A): tetraedro rigido con base = copia de una cara de B
    que contiene b, a sep_eps mm hacia a, y apice EN a (cosido a a; la base cosida a la cara). Reposo (SEP_REST): base = la cara en el molde (uv) y
    apice en las mismas coordenadas locales que en el V0 (sin pretension). Flexion maxima, fuera de la autocol (ver nucleo.tela).
    Variante de m133_reglas.broches_con_altura (base del molde + apice perpendicular). sep_h = 0 (defecto) -> identico."""
    if ES.P['sep_h'] <= 0 or ES.P['snaps'] <= 0:
        return
    nom = ES.D['sew_seam']
    pares = [ES.D['sew'][i] for i, nm in enumerate(nom) if nm.startswith('broche puno')]
    if not pares:
        return
    _kb = [i for i, nm in enumerate(nom) if not nm.startswith('broche puno')]
    ES.D['sew'] = [ES.D['sew'][i] for i in _kb]
    ES.D['sew_seam'] = [ES.D['sew_seam'][i] for i in _kb]
    _h = ES.P['sep_h'] / 1000.0
    _UVa = np.array(ES.D['uv'], float)
    F = np.array(ES.D['f'])
    _nv, _nuv, _nf, _msg = [], [], [], []
    for p in pares:
        lado = 'R' if ES.D['groups']['pueR'][0] <= p[0] < ES.D['groups']['pueR'][1] else 'L'
        g0, g1 = ES.D['groups']['pue' + lado]
        cen = ES.V0[g0:g1].mean(0)
        b, a = sorted((int(p[0]), int(p[1])), key=lambda i: -np.linalg.norm(ES.V0[i] - cen))   # b = capa de afuera (punta B)
        _gap = np.linalg.norm(ES.V0[b] - ES.V0[a])
        assert abs(_gap - _h) < 0.0005, f'broches_con_altura: |b - a| = {_gap * 1000:.2f} mm en el V0 y sep_h = {ES.P["sep_h"]} (usar el V0 de t2e10_v0.py)'
        _d = (ES.V0[a] - ES.V0[b]) / _gap                                     # eje del separador: de b hacia a
        cand = np.where((F == b).any(1))[0]
        cen_f = ES.V0[F[cand]].mean(1)
        fi = cand[np.argmin(np.linalg.norm(cen_f - ES.V0[b], axis=1))]
        _fv = [int(b)] + [int(x) for x in F[fi] if x != b]
        _B = ES.V0[_fv]
        _n = np.cross(_B[1] - _B[0], _B[2] - _B[0])
        _n /= np.linalg.norm(_n)
        _sg = 1.0 if np.dot(_n, _d) > 0 else -1.0                              # lado de la cara donde esta a
        _Bs = _B + _sg * (ES.P['sep_eps'] / 1000.0) * _n
        _ap = ES.V0[a].copy()
        _abc = np.linalg.solve(np.c_[_Bs[1] - _Bs[0], _Bs[2] - _Bs[0], _n], _ap - _Bs[0])   # apice en coordenadas locales de la base
        _R = np.c_[_UVa[_fv] / 1000.0, np.zeros(3)]
        _zr = np.sign(np.cross(_R[1] - _R[0], _R[2] - _R[0])[2])
        _apr = _R[0] + _abc[0] * (_R[1] - _R[0]) + _abc[1] * (_R[2] - _R[0]) + np.array([0.0, 0.0, _zr * _abc[2]])
        _i0 = ES.NV0 + len(_nv)
        b0, b1, b2, ap = (_i0, _i0 + 1, _i0 + 2, _i0 + 3)
        _nv += [*_Bs.tolist(), _ap.tolist()]
        _nuv += [(_R[k][:2] * 1000.0).tolist() for k in range(3)] + [(_apr[:2] * 1000.0).tolist()]
        for k in range(3):
            ES.SEP_REST[_i0 + k] = tuple(_R[k])
        ES.SEP_REST[ap] = tuple(_apr)
        _nf += [[b0, b2, b1], [b0, b1, ap], [b1, b2, ap], [b2, b0, ap]] if _sg > 0 else [[b0, b1, b2], [b1, b0, ap], [b2, b1, ap], [b0, b2, ap]]
        ES.D['sew'] += [[b0, _fv[0]], [b1, _fv[1]], [b2, _fv[2]], [ap, int(a)]]
        ES.D['sew_seam'] += ['broche base'] * 3 + ['broche puno ' + lado + ' (apice)']
        _msg.append(f'{lado} b{b}-a{a}: |b-a| {_gap * 1000:.2f} mm, alto {_sg * _abc[2] * 1000:.2f}, eje vs normal {np.degrees(np.arccos(min(1.0, abs(float(np.dot(_n, _d)))))):.0f} gr')
    ES.SEPV = list(range(ES.NV0, ES.NV0 + len(_nv)))
    ES.V0 = np.vstack([ES.V0, np.array(_nv)])
    ES.D['v'] = list(ES.D['v']) + _nv
    ES.D['uv'] = list(ES.D['uv']) + _nuv
    if 'pocket' in ES.D:
        ES.D['pocket'] = list(ES.D['pocket']) + [None] * len(_nv)
    ES.F = np.vstack([ES.F, np.array(_nf, int)])
    ES.D['f'] = ES.F.tolist()
    ES.D['groups']['snap_sep'] = [ES.NV0, ES.NV0 + len(_nv)]
    ES.NV = len(ES.V0)
    ES.log(f"BROCHES CON ALTURA (W2094 T2e10): {len(pares)} separadores de {ES.P['sep_h']} mm | base a {ES.P['sep_eps']} mm | {len(pares)} resortes "
           f"'broche puno' de largo 0 fuera | +{len(_nv)} vertices, +{len(_nf)} caras | " + ' | '.join(_msg))
