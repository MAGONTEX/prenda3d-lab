"""Reglas de la W2094 QUARTZ (bomber de ecocuero de MUJER talle M, [x]; cuello alto de dos caras, cintura doblada con elastico, puno doble
con broche, cierre central; forro acolchado SUMADO a la cascara). Humo 1 (2026-10-10, tecnico-3d).

El nucleo (`nucleo.py`) llama hooks por los NOMBRES de la M133 con `_regla(ES, "nombre")` y saltea los que este modulo no define. Plantilla:
`m1195_reglas.py` (mismo proveedor, misma capa unica). Lo que hace cada hook EN ESE PUNTO del nucleo:
  filtrar_costuras_diagnostico  antes de armar la escena   -> exige la construccion de `49-w2094/molderia/arma_malla_v0.py` (strip `zipper`, `cuff`, grupos)
  sandwich_rotar_caras          con el cuerpo cargado      -> solo colisiona la piel completa del npz (sin tubos de brazo ni cabeza del maniqui)
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
