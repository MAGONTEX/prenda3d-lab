"""Reglas de la W2057 ONYX (campera corta de ecocuero de MUJER, cuello alto de pie, cierre metalico entre dos tiras de 15 mm, canesues,
2 pliegues cosidos en la espalda, corte-pinza en el frente; forro acolchado 60 g SUMADO a la cascara). Copia adaptada de m1195_reglas.py.

El nucleo (`nucleo.py`, generado) llama hooks por los NOMBRES de la M133 con `_regla(ES, "nombre")` y saltea los que este modulo no define:
  filtrar_costuras_diagnostico  antes de armar la escena      -> exige que la malla traiga zipper / zonas / autocol / marcadores (sim/arma_malla_sim.py)
  sandwich_rotar_caras          con el cuerpo ya cargado      -> quita la colision de los tubos de brazo y la cabeza del MANIQUI (la piel completa colisiona)
  cuello_flexion_por_capa       con la rigidez ya cargada     -> flexion por zona (cuello / tira x3, vista / ruedo / puno / bolsillo x2, pliegue x3) de w2057_reglas.json
  metricas_definir              antes del bucle               -> indices (ruedo, punos, CB, hombro, HPS, canto, escote, costados, pecho, filas del cierre, pliegues) y cuerpo
  metrica_cf_y_asentamiento     cada 6 cuadros                -> asentamiento (ruedo CB / CF, canto, puno) con settle_min / settle_tol / settle_n
  metricas_por_cuadro           cada 6 cuadros                -> caida del ruedo y costados (compuerta f2: <= 15 mm), torsion del cierre, R-L, hombro apoyado,
                                                                 cuello (canto sobre el escote; distancia al menton: compuerta), pliegues (abertura), ficha (G, A, D, L, F, K, C)
Sin presion, sin sandwich, sin broches, sin cordon ni capucha. Datos: w2057_reglas.json (ES.RD). CAPAS = capas de prenda.json que estas reglas tratan.
"""
import bpy, json, math, os
import numpy as np

CAPAS = {"forro", "vista"}     # forro acolchado y vistas entran como masa + flexion de la cascara (PLAN-SIM-W2057 1): sin capa propia en la sim


def _pesos(ES, nombre):
    W = np.zeros(ES.NV); vg = ES.gar.vertex_groups[nombre]
    for v in ES.gar.data.vertices:
        for g in v.groups:
            if g.group == vg.index:
                W[v.index] = g.weight
    return W


def filtrar_costuras_diagnostico(ES):
    """La malla de sim de la W2057 trae la construccion hecha (sim/arma_malla_sim.py): no se inventa nada aca."""
    falt = [k for k in ("zipper", "zonas", "autocol", "marcadores", "border") if not ES.D.get(k)]
    assert not falt, f"malla sin la construccion de la W2057 {falt}: correr 50-w2057/sim/arma_malla_sim.py"
    z = ES.D["zonas"]
    ES.log(f"W2057 construccion: cierre {len(ES.D['zipper'])} v | zonas " + " ".join(f"{k} {len(v)}" for k, v in z.items())
           + f" | autocol {len(ES.D['autocol'])} v | costuras {len(ES.D['sew'])} pares | generador {ES.D.get('generador_sim', {})}")


def sandwich_rotar_caras(ES):
    """Cuerpo = piel completa de mujer M con brazos (npz). Los tubos de brazo y la cabeza del maniqui parametrico no colisionan."""
    quitados = []
    for o in list(ES.MANIQUI):
        if o.name.startswith("CD_maniqui_"):
            for m in [m for m in o.modifiers if m.type == "COLLISION"]:
                o.modifiers.remove(m); quitados.append(o.name)
            o.hide_viewport = True; o.hide_render = True
    ES.TFOBJ = [o for o in ES.TFOBJ if not o.name.startswith("CD_maniqui_")]
    vivos = [(o.name, round(o.collision.cloth_friction, 1), round(o.collision.thickness_outer, 4)) for o in ES.MANIQUI if any(m.type == "COLLISION" for m in o.modifiers)]
    assert vivos and all(n.startswith("CD_cuerpo") for n, _, _ in vivos), f"colisionadores inesperados: {vivos}"
    ES.log(f"W2057 cuerpo: solo colisiona la piel completa {vivos} (friccion, espesor) | maniqui sin colision: {quitados}")


def cuello_flexion_por_capa(ES):
    """Flexion por zona: b_zona = mult x bending, como peso del grupo 'rigidez' (lineal entre bending y bend_max). El cierre queda en 1 (bend_max)."""
    mult = ES.RD.get("flexion_zonas", {}); b0, bm = ES.P["bending"], ES.P["bend_max"]
    W = _pesos(ES, "rigidez"); W0 = W.copy(); zip_ = set(ES.D["zipper"]); res = []
    for z, m in mult.items():
        ids = np.array([i for i in ES.D["zonas"].get(z, []) if i not in zip_], int)
        if not len(ids):
            continue
        w = float(np.clip((m * b0 - b0) / max(bm - b0, 1e-9), 0.0, 1.0)); W[ids] = np.maximum(W[ids], w)
        res.append(f"{z} x{m:g} -> {b0 + (bm - b0) * w:.0f} ({len(ids)} v, peso {w:.3f})")
    chg = np.where(np.abs(W - W0) > 1e-9)[0]
    for i in chg:
        ES.vrig.add([int(i)], float(W[i]), "REPLACE")
    ES.log(f"W2057 FLEXION por zona (base {b0:g}, tope {bm:g}, cierre {len(zip_)} v en {bm:g}): " + " | ".join(res) + f" | {len(chg)} pesos escritos")


def metricas_definir(ES):
    mk = ES.D["marcadores"]; ES.MK = {k: (np.array(v, int) if isinstance(v, list) else int(v)) for k, v in mk.items()}
    B = np.load(ES.RUTA(ES.BODY)); ES.BV20 = B["V20"]; ES.BV8 = B["V8"]; ES.BCAB = B["cabeza"].astype(bool); ES.BT = B["T"]
    ES.HEADV = np.unique(ES.BT[ES.BCAB]) if ES.BCAB.any() else np.array([], int)
    kz = (ES.BV20[:, 2] > 1.440) & (ES.BV20[:, 2] < 1.470)                       # menton: punto mas adelantado de la cara entre z 1440 y 1470
    ES.MENTON = ES.BV20[kz][np.argmin(ES.BV20[kz][:, 1])] if kz.any() else None
    ES.F1 = None; ES.SH1 = []; ES.UVm = np.array(ES.D["uv"], float); ES.PRENDA = _prenda_json(ES)
    ES.log(f"W2057 metricas: ruedo {len(ES.MK['ruedo'])} v, punos {len(ES.MK['puno_R'])}/{len(ES.MK['puno_L'])}, CB {len(ES.MK['cb'])} v, canto {len(ES.MK['canto_cuello'])} v, "
           f"escote {len(ES.MK['escote_R'])}/{len(ES.MK['escote_L'])}, filas del cierre {len(ES.MK['zip_filas'])}, hombro R/L {ES.MK['hombro_R']}/{ES.MK['hombro_L']}, "
           f"pliegues {len(ES.MK['pliegue_R'])}/{len(ES.MK['pliegue_L'])} pares | cuerpo {len(ES.BV20)} v, cabeza {len(ES.HEADV)} v, menton {None if ES.MENTON is None else (ES.MENTON * 1000).round(0).tolist()}")


def _cuerpo(ES):
    """Piel en este cuadro: mezcla V20 -> V8 con la misma rampa que el shape key brazos_8 (lineal; la clave es BEZIER: aproximado)."""
    if ES.P["arm_end"] >= 0 and ES.P["arm_end"] != ES.P["abd_end"]:
        t = float(np.clip((ES.f - ES.P["arm_f0"]) / max(ES.P["arm_f1"] - ES.P["arm_f0"], 1), 0, 1))
    else:
        t = 0.0
    return ES.BV20 * (1 - t) + ES.BV8 * t


def _dmin(P, Q):
    """distancia minima de cada punto de P al conjunto Q (fuerza bruta por bloques; sin scipy en Blender)."""
    out = np.empty(len(P))
    for a in range(0, len(P), 256):
        d = np.linalg.norm(P[a:a + 256, None, :] - Q[None, :, :], axis=2); out[a:a + 256] = d.min(1)
    return out


def _poli(X, ids):
    return float(np.linalg.norm(np.diff(X[ids], axis=0), axis=1).sum() * 1000)


def _anillo(X, ids):
    """largo de un anillo cerrado ordenado por azimut alrededor de su centroide (mm). NO usar para anillos que cruzan costuras (salta entre
    piezas: L dio 230 contra 132 en h1). Queda para diagnostico."""
    P = X[ids]; c = P.mean(0); az = np.arctan2(P[:, 1] - c[1], P[:, 0] - c[0]); o = np.argsort(az); Q = P[o]
    return float((np.linalg.norm(np.diff(Q, axis=0), axis=1).sum() + np.linalg.norm(Q[0] - Q[-1])) * 1000)


def _pieza_de(ES, i):
    for p, (a, b) in ES.D["groups"].items():
        if a <= i < b:
            return p
    return None


def _cadena(ES, X, ids):
    """Largo de un tramo de BORDE (ruedo, puno) como CADENA de aristas del contorno: por pieza, en el orden del arco `inst[p].s` del
    generador (r2: reemplaza al anillo por azimut, que saltaba entre piezas en cada costura). Devuelve (mm 3D, mm en el molde) sumando
    solo tramos contiguos (corte donde el arco salta mas de 3 lados de malla); el cruce de costura entre piezas no suma (gap ~ 0)."""
    D = ES.D; UV = ES.UVm; h = float(D.get("h_mm", 9.0)); l3 = luv = 0.0
    por = {}
    for i in ids:
        por.setdefault(_pieza_de(ES, int(i)), []).append(int(i))
    for p, ii in por.items():
        ins = D["inst"].get(p)
        if ins is None:
            continue
        ii = np.array(ii, int); k = ii - int(ins["off"]); s = np.array(ins["s"], float); per = float(ins["per"])
        ok = (k >= 0) & (k < len(s)); ii, k = ii[ok], k[ok]
        if len(ii) < 2:
            continue
        o = np.argsort(s[k]); kk = ii[o]; sk = s[k][o]
        br = np.where(np.diff(sk) > 3 * h)[0]; runs = np.split(kk, br + 1)
        if len(runs) > 1 and (sk[0] + per - sk[-1]) <= 3 * h:
            runs = [np.r_[runs[-1], runs[0]]] + runs[1:-1]
        for r in runs:
            l3 += float(np.linalg.norm(np.diff(X[r], axis=0), axis=1).sum()) * 1000; luv += float(np.linalg.norm(np.diff(UV[r], axis=0), axis=1).sum())
    return l3, luv


def _prenda_json(ES):
    """prenda.json de la corrida (el nucleo no lo expone a los hooks): el argumento prenda= de lanzar.py, si no el del carril."""
    import sys
    for t in sys.argv:
        if t.startswith("prenda="):
            return json.load(open(t[7:], encoding="utf-8"))
    return json.load(open(ES.RUTA("prenda.json"), encoding="utf-8"))


def _tramo_borde(ES, X, pieza, de, a, sentido):
    """Largo de un tramo del borde de una pieza (arco `de` -> `a` del molde, la misma convencion que prenda.json) como cadena de aristas:
    (mm 3D, mm molde). Misma logica que prenda3d.v0.contorno_cadena, sin importar el paquete (malla_gen no corre en Blender)."""
    ins = ES.D["inst"][pieza]; s = np.array(ins["s"], float); per = float(ins["per"]); off = int(ins["off"])
    L = ((a - de) * (1 if sentido >= 0 else -1)) % per
    d = ((s - de) * (1 if sentido >= 0 else -1)) % per
    k = np.where((d <= L + 0.3) | (d >= per - 0.3))[0]; d = np.where(d >= per - 0.3, 0.0, d); k = off + k[np.argsort(d[k])]
    if len(k) < 2:
        return 0.0, 0.0
    return float(np.linalg.norm(np.diff(X[k], axis=0), axis=1).sum()) * 1000, float(np.linalg.norm(np.diff(ES.UVm[k], axis=0), axis=1).sum())


def _borde_por_costuras(ES, X, ids, lado="a"):
    """Suma de los tramos del lado `lado` (la cascara) de las costuras `ids` de prenda.json: (mm 3D, mm molde). Ruedo = las 4 costuras de la
    vista de ruedo; puno = 'ruedo de manga - vista de puno'. Es la cota de la ficha medida por RECORRIDO sobre la tela, no por cuerda."""
    l3 = luv = 0.0
    for c in ES.PRENDA.get("costuras", []):
        if c.get("id") not in ids:
            continue
        for t in c.get("tramos", []):
            if t.get("modo") != "borde" or lado not in t:
                continue
            b = t[lado]
            if b["pieza"] not in ES.D["groups"]:
                continue
            a3, auv = _tramo_borde(ES, X, b["pieza"], float(b["de"]), float(b["a"]), int(b.get("sentido", 1))); l3 += a3; luv += auv
    return l3, luv


RUEDO_COSTURAS = ("ruedo delantero (tira + delantero) - vista de ruedo R", "ruedo delantero (tira + delantero) - vista de ruedo L",
                  "ruedo de espalda - vista de ruedo R", "ruedo de espalda - vista de ruedo L")
PUNO_COSTURAS = {"R": ("ruedo de manga - vista de puno R",), "L": ("ruedo de manga - vista de puno L",)}


def _lineas_ficha(ES, X):
    """Lineas de medida de la capa 8 (dibujadas por el moldista) como cadena de aristas: 3D / molde. A = las 2 lineas horizontales del
    canesu (hombro a hombro, 2 x 233 = 466 de molde contra 478 de ficha); C = las lineas de pecho de delR/delL (marcador pecho_*)."""
    out = {}
    UV = ES.UVm; L = ES.D.get("lineas", {})
    A3 = Auv = 0.0
    for l in L.get("cane", []):
        ids = np.array(l["v"], int)
        if np.ptp(UV[ids, 1]) < 1.0 and 200 <= float(np.linalg.norm(np.diff(UV[ids], axis=0), axis=1).sum()) <= 260:
            A3 += float(np.linalg.norm(np.diff(X[ids], axis=0), axis=1).sum()) * 1000; Auv += float(np.linalg.norm(np.diff(UV[ids], axis=0), axis=1).sum())
    out["A"] = (A3, Auv)
    return out


def _hombro_cresta(ES, X, BV):
    """Hombro apoyado medido en la CRESTA de la prenda (el vertice mas alto del canesu por franja de |x| entre el HPS y el punto de hombro),
    no en la costura del canesu, que va 50-60 mm al frente del hombro (h1: 15,5 mm de 'hueco' que era la costura mirando al pecho)."""
    cane = np.arange(*ES.D["groups"]["cane"]); d = {}
    for s_ in "RL":
        x0 = float(X[ES.MK[f"hps_{s_}"], 0]); x1 = float(X[ES.MK[f"hombro_{s_}"], 0]); lo, hi = min(x0, x1), max(x0, x1)
        bins = np.linspace(lo, hi, 9); tops = []
        for a, b in zip(bins[:-1], bins[1:]):
            k = cane[(X[cane, 0] >= a) & (X[cane, 0] < b)]
            if len(k):
                tops.append(int(k[np.argmax(X[k, 2])]))
        d[s_] = _dmin(X[tops], BV) * 1000 if tops else np.array([float("nan")])
    return d


def _numeros(ES, X):
    mk = ES.MK; H = X[mk["ruedo"]]
    zR = float(np.median(H[H[:, 0] < 0, 2]) * 1000); zL = float(np.median(H[H[:, 0] > 0, 2]) * 1000)
    zf = np.array(mk["zip_filas"]); Z = X[zf].mean(1)
    cb = X[mk["cb"]]; zcb = float(cb[-1, 2] * 1000)                         # ultimo = el mas bajo (ruedo CB)
    canto = X[mk["canto_cuello"]]; esc = X[np.r_[mk["escote_R"], mk["escote_L"]]]
    return dict(ruedo_R=zR, ruedo_L=zL, ruedo_CB=zcb, ruedo_CF=float(Z[0, 2] * 1000), canto_z=float(canto[:, 2].mean() * 1000), escote_z=float(esc[:, 2].mean() * 1000),
                puno_R=float(X[mk["puno_R"], 2].mean() * 1000), puno_L=float(X[mk["puno_L"], 2].mean() * 1000),
                zip_x_pecho=float(Z[Z[:, 2] > 1.15, 0].mean() * 1000) if (Z[:, 2] > 1.15).any() else float("nan"), zip_x_ruedo=float(Z[Z[:, 2] < 1.0, 0].mean() * 1000) if (Z[:, 2] < 1.0).any() else float("nan"))


def metrica_cf_y_asentamiento(ES):
    n = _numeros(ES, ES.X)
    if ES.F1 is None:
        ES.F1 = dict(n)
    if ES.f >= ES.SET_F0:
        cn = np.array([n["ruedo_CB"], n["ruedo_CF"], n["canto_z"], n["puno_R"], n["puno_L"]])
        ES.SH1.append((ES.f, cn))
        if len(ES.SH1) > 1:
            dd = cn - ES.SH1[-2][1]; dm = float(np.abs(dd).max())
            ES.log(f"   ASENT f{ES.f} (+{ES.f - ES.SET_F0}) d/6f ruedo CB {dd[0]:+.1f} CF {dd[1]:+.1f} canto {dd[2]:+.1f} puno {dd[3]:+.1f}/{dd[4]:+.1f} mm | max {dm:.1f}")
            ES.SH1[-1] = (ES.f, cn, dm)
            if ES.P["settle_min"] > 0 and ES.f - ES.SET_F0 >= ES.P["settle_min"] and len(ES.SH1) > int(ES.P["settle_n"]) and all(len(h) > 2 and h[2] < ES.P["settle_tol"] for h in ES.SH1[-int(ES.P["settle_n"]):]):
                ES.log(f"ESTABLE en f{ES.f}: ruedo/canto/puno < {ES.P['settle_tol']} mm cada 6 cuadros en {int(ES.P['settle_n'])} chequeos seguidos"); ES.SETTLED = True


def metricas_por_cuadro(ES):
    X = ES.X; mk = ES.MK; n = _numeros(ES, X); f1 = ES.F1 or n; BV = _cuerpo(ES)
    hom = np.r_[mk["hombro_costura_R"], mk["hombro_costura_L"]]; dh = _dmin(X[hom], BV) * 1000
    cue = np.arange(*ES.D["groups"]["cuE"]); canto = mk["canto_cuello"]
    dcab = _dmin(X[cue], BV[ES.HEADV]) * 1000 if len(ES.HEADV) else np.array([float("nan")])
    dmen = float(np.linalg.norm(X[canto] - ES.MENTON, axis=1).min() * 1000) if ES.MENTON is not None else float("nan")
    dz_cos = {s_: float((X[mk["costado_" + s_], 2].mean() - ES.V0[mk["costado_" + s_], 2].mean()) * 1000) for s_ in "RL"}
    plg = {s_: float(np.linalg.norm(X[mk["pliegue_" + s_][:, 0]] - X[mk["pliegue_" + s_][:, 1]], axis=1).max() * 1000) for s_ in "RL" if len(mk["pliegue_" + s_])}
    Acu = float(np.linalg.norm(X[mk["hombro_R"]] - X[mk["hombro_L"]]) * 1000)          # cuerda 3D (diagnostico; la ficha mide a plano)
    A3, Auv = _lineas_ficha(ES, X)["A"]
    # r2b: G = los EJES dibujados (canesu 104 + espalda 429 en la malla; 115 + 440 en el DXF), 3D y molde sumados POR PIEZA: el uv salta
    # entre piezas (daba 616) y el 3D de corrido suma los ~20 mm de hueco entre los dos ejes (daba 540 contra 533)
    _pz = np.array([_pieza_de(ES, int(i)) for i in mk["cb"]]); G = Guv = 0.0
    for _p in dict.fromkeys(_pz.tolist()):
        _ids = mk["cb"][_pz == _p]
        if len(_ids) > 1:
            G += _poli(X, _ids); Guv += float(np.linalg.norm(np.diff(ES.UVm[_ids], axis=0), axis=1).sum())
    cinta = float(ES.RD.get("cinta_cierre_mm", 12.0))
    # ruedo = los 4 tramos de la cascara cosidos a las vistas de ruedo (del 2 x 242 + tira 2 x 15 + esp 534 SIN los tucks, que van a C06): 1048 de molde
    D3, Duv = _borde_por_costuras(ES, X, RUEDO_COSTURAS); Dm, Dmol = (D3 + cinta) / 2, (Duv + cinta) / 2
    sol = float(ES.RD.get("solapado_puno_mm", 30.0))                                          # la ficha mide el puno CERRADO: la abertura monta ~15 mm (2 x 15 por puno)
    LR3, LRuv = _borde_por_costuras(ES, X, PUNO_COSTURAS["R"]); LL3, LLuv = _borde_por_costuras(ES, X, PUNO_COSTURAS["L"]); Lm, Lmol = (LR3 + LL3 - 2 * sol) / 4, (LRuv + LLuv - 2 * sol) / 4
    Fm = float((X[mk["hps_R"], 2] - X[mk["zip_filas"][0][0], 2]) * 1000)
    K = {s_: float(np.linalg.norm(X[mk["hombro_" + s_]] - X[mk["puno_" + s_]].mean(0)) * 1000) for s_ in "RL"}
    C = sum(_poli(X, mk["pecho_" + s_]) for s_ in "RL" if len(mk["pecho_" + s_])) + cinta
    Cuv = sum(float(np.linalg.norm(np.diff(ES.UVm[mk["pecho_" + s_]], axis=0), axis=1).sum()) for s_ in "RL" if len(mk["pecho_" + s_])) + cinta
    hc = _hombro_cresta(ES, X, BV); hcc = np.r_[hc["R"], hc["L"]]
    ES.log(f"   W2057 CAIDA ruedo R {n['ruedo_R'] - f1['ruedo_R']:+.0f} L {n['ruedo_L'] - f1['ruedo_L']:+.0f} CB {n['ruedo_CB'] - f1['ruedo_CB']:+.0f} CF {n['ruedo_CF'] - f1['ruedo_CF']:+.0f} mm desde f1 | costado z R {dz_cos['R']:+.0f} L {dz_cos['L']:+.0f} vs V0 | "
           f"R-L ruedo {n['ruedo_R'] - n['ruedo_L']:+.0f} puno {n['puno_R'] - n['puno_L']:+.0f} mm | TORSION cierre x pecho {n['zip_x_pecho']:+.0f} ruedo {n['zip_x_ruedo']:+.0f} mm | PLIEGUES abiertos max R {plg.get('R', float('nan')):.1f} L {plg.get('L', float('nan')):.1f} mm")
    ES.log(f"   W2057 HOMBRO cresta-piel med {np.nanmedian(hcc):.1f} p95 {np.nanpercentile(hcc, 95):.1f} max {np.nanmax(hcc):.1f} mm R/L med {np.nanmedian(hc['R']):.1f}/{np.nanmedian(hc['L']):.1f} (apoyado ~ th+cd {1000 * (ES.P['bth'] if ES.P['bth'] >= 0 else ES.P['th']) + 1000 * ES.P['cd']:.0f}; costura del canesu-piel med {np.median(dh):.1f}, va al frente) | "
           f"CUELLO canto z med {n['canto_z']:.0f} sobre el escote {n['escote_z']:.0f} (+{n['canto_z'] - n['escote_z']:.0f} de 73 de molde: {'LEVANTADO' if n['canto_z'] - n['escote_z'] > 45 else 'caido'}) | cuello-cabeza min {dcab.min():.1f} mm | canto-menton min {dmen:.1f} mm")
    ES.log(f"   W2057 FICHA (3D | molde | 3D/molde; ficha M) G CB canesu->ruedo {G:.0f} | {Guv:.0f} | {G / Guv:.3f} (545) · A hombro-hombro lineas del canesu {A3:.0f} | {Auv:.0f} | {(A3 / Auv if Auv else float('nan')):.3f} (480; cuerda 3D {Acu:.0f}) · "
           f"C pecho {C:.0f} | {Cuv:.0f} | {C / Cuv:.3f} (570) · D ruedo/2 {Dm:.0f} | {Dmol:.0f} | {Dm / Dmol:.3f} (520) · L puno/2 {Lm:.0f} | {Lmol:.0f} | {(Lm / Lmol if Lmol else float('nan')):.3f} (120) · "
           f"F HPS->ruedo CF vertical {Fm:.0f} (555) · K hombro->puno cuerda R/L {K['R']:.0f}/{K['L']:.0f} (590) mm")
