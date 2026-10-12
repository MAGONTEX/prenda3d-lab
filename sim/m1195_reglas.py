"""Reglas de la M1195 GRAVITY (campera corta de ecocuero, cuello camisero, cierre metalico central; forro acolchado SUMADO a la cascara).

El nucleo (`nucleo.py`, generado) llama hooks por los NOMBRES de la M133 con `_regla(ES, "nombre")` y saltea los que este modulo no define.
Aca cada hook hace lo que la M1195 necesita EN ESE PUNTO del nucleo (el nombre dice donde se llama, no que hace):
  filtrar_costuras_diagnostico  antes de armar la escena      -> exige que la malla traiga zipper / zonas / autocol / marcadores (arma_malla_sim.py)
  sandwich_rotar_caras          con el cuerpo ya cargado      -> quita la colision de los tubos de brazo y la cabeza del MANIQUI (la piel completa
                                                                 del npz ya colisiona; el nucleo solo apaga torso y cabeza del maniqui)
  cuello_flexion_por_capa       con la rigidez ya cargada     -> flexion por zona (cuello x3, vista / ruedo / puno x2) leida de m1195_reglas.json
  metricas_definir              antes del bucle               -> indices (ruedo, punos, CB, hombro, HPS, canto, filas del cierre) y cuerpo
  metrica_cf_y_asentamiento     cada 6 cuadros                -> asentamiento (ruedo CB / CF, canto, puno) con settle_min / settle_tol / settle_n
  metricas_por_cuadro           cada 6 cuadros                -> caida del ruedo y costados, torsion del cierre, R-L, hombro apoyado, cuello
                                                                 (canto bajo el quiebre, distancia al menton), medidas de la ficha (G, A, D, L, F)
Sin presion, sin sandwich, sin broches, sin cordon ni capucha: esos hooks no existen aca. Datos: m1195_reglas.json (ES.RD).
CAPAS = capas de prenda.json que estas reglas saben tratar (lanzar.py las suma a las del nucleo).
"""
import bpy, json, math, os
import numpy as np

CAPAS = {"forro"}     # el forro acolchado entra como masa + espesor de la cascara (PLAN-SIM-M1195 1): sin capa propia en la sim


def _pesos(ES, nombre):
    W = np.zeros(ES.NV); vg = ES.gar.vertex_groups[nombre]
    for v in ES.gar.data.vertices:
        for g in v.groups:
            if g.group == vg.index:
                W[v.index] = g.weight
    return W


def filtrar_costuras_diagnostico(ES):
    """La malla de sim de la M1195 trae la construccion hecha (sim/arma_malla_sim.py): no se inventa nada aca."""
    falt = [k for k in ("zipper", "zonas", "autocol", "marcadores", "border") if not ES.D.get(k)]
    assert not falt, f"malla sin la construccion de la M1195 {falt}: correr 47-m1195/sim/arma_malla_sim.py"
    z = ES.D["zonas"]
    ES.log(f"M1195 construccion: tira del cierre {len(ES.D['zipper'])} v | zonas " + " ".join(f"{k} {len(v)}" for k, v in z.items())
           + f" | autocol {len(ES.D['autocol'])} v | costuras {len(ES.D['sew'])} pares | generador {ES.D.get('generador_sim', {})}")


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
    ES.log(f"M1195 cuerpo: solo colisiona la piel completa {vivos} (friccion, espesor) | maniqui sin colision: {quitados}")


def sandwich_reposo(ES):
    """r6, cuello de 2 hojas (malla con D['sandwich'], 47-m1195/sim/arma_cuello2.py): la clave molde_plano de las gemelas cuB/pieB queda SUPERPUESTA
    a la hoja de abajo (uv de su gemela, z = -d; cuB con una rampa de 15 mm junto al quiebre = +4 mm de arco, la vuelta de la tela de la P19 real).
    Los resortes internos y las aristas toman su largo de reposo de esta clave (Dynamic Mesh). Sin D['sandwich'] no hace nada (mallas s1)."""
    sw = ES.D.get("sandwich")
    if not sw:
        return
    for i, co in zip(sw["ids"], sw["reposo_mm"]):
        ES.kc.data[int(i)].co = (co[0] / 1000.0, co[1] / 1000.0, co[2] / 1000.0)
    z = np.array([c[2] for c in sw["reposo_mm"]])
    ES.log(f"M1195 SANDWICH reposo: {len(sw['ids'])} v de {list(sw['piezas'])} sobre {list(sw['piezas'].values())} | z {z.min():.1f}..{z.max():.1f} mm (d {sw['d_mm']}, vuelta +{sw['delta_mm']} mm en {sw['zq_mm']} mm)")


def sandwich_resortes_internos(ES):
    """r6: resortes INTERNOS del Cloth entre las dos hojas del cuello. Blender los detecta al crear el Cloth (f1, reposo = V0): rayo por -normal,
    resorte al tri[0] del triangulo tocado (cloth.cc); rigidez = peso del grupo `interno` x k (base 0: fuera del cuello no hay fuerza)."""
    sw = ES.D.get("sandwich")
    if not sw:
        return
    cfg = ES.RD.get("cuello_sandwich", {}); k = float(cfg.get("k", 200.0)); kc = float(cfg.get("kc", 100.0)); mx = float(sw["len_mm"]) / 1000.0
    vint = ES.gar.vertex_groups.new(name="interno"); vint.add(list(range(ES.NV)), 0.0, "REPLACE"); W = np.zeros(ES.NV)
    for i, w in zip(sw["w_ids"], sw["w"]):
        W[int(i)] = float(w)
        if w > 0:
            vint.add([int(i)], float(w), "REPLACE")
    s = ES.s; s.use_internal_springs = True; s.internal_spring_max_length = mx; s.internal_spring_max_diversion = 0.0; s.internal_spring_normal_check = True
    s.vertex_group_intern = "interno"; s.internal_tension_stiffness = 0.0; s.internal_compression_stiffness = 0.0
    s.internal_tension_stiffness_max = k; s.internal_compression_stiffness_max = kc
    import collections
    import m133_sandwich as SE                                             # solo su replica de find_internal_spring_target_vertex (no se edita)
    ES.me.update(); vn = np.empty(ES.NV * 3); ES.me.vertices.foreach_get("normal", vn); vn = vn.reshape(-1, 3)
    pares = SE.predict(np.array(ES.V0, float), ES.F, vn, mx, check_normal=True)
    pc = np.empty(ES.NV, object)
    for g, (a, b) in ES.D["groups"].items():
        pc[a:b] = g
    R = np.array([ES.kc.data[i].co[:] for i in range(ES.NV)]); V0 = np.array(ES.V0, float)
    P = np.array(pares, int).reshape(-1, 2)
    l3 = np.linalg.norm(V0[P[:, 0]] - V0[P[:, 1]], axis=1) * 1000; lr = np.linalg.norm(R[P[:, 0]] - R[P[:, 1]], axis=1) * 1000
    cnt = collections.Counter(tuple(sorted((pc[i], pc[j]))) for i, j in P)
    # c1 (r6) EXPLOTO en f6 (escote 1247 mm): 125 pares cuA-pieA / cuB-pieB (la hoja doblada queda a < 4 mm del pie) con largo de reposo = distancia
    # entre piezas en el molde (p95 141 mm) y rigidez > 0. Un par solo vale si une una hoja con SU gemela y su reposo se parece a su largo 3D;
    # si no, los DOS extremos pasan a peso 0 (la rigidez del resorte es el promedio de los dos pesos).
    gem = {frozenset(kv) for kv in sw["piezas"].items()}; d_mm = float(sw["d_mm"])
    malo = np.array([frozenset((pc[i], pc[j])) not in gem for i, j in P]) | (lr > 1.6 * np.maximum(l3, d_mm) + 1.0) | (lr < 0.3)
    anul = sorted(set(int(x) for x in P[malo].ravel() if W[int(x)] > 0))
    for i in anul:
        W[i] = 0.0; vint.add([i], 0.0, "REPLACE")
    wp = 0.5 * (W[P[:, 0]] + W[P[:, 1]]); act = wp > 0
    assert not (act & malo).any(), "sandwich: queda un par malo con rigidez"
    ES.log(f"M1195 SANDWICH pares anulados: {int(malo.sum())} malos (otra pieza o reposo incoherente) -> {len(anul)} v a peso 0")
    assert act.any() and lr[act].min() > 0.2, f"sandwich: sin resortes activos o con largo de reposo ~0 (min {lr[act].min() if act.any() else None})"
    ES.log(f"M1195 SANDWICH resortes internos (prediccion): {len(P)} pares {cnt.most_common(6)} | con rigidez {int(act.sum())} (peso medio {wp[act].mean():.2f}) | largo 3D arranque p5/med/p95 "
           f"{np.percentile(l3[act], [5, 50, 95]).round(1).tolist()} mm | reposo {np.percentile(lr[act], [5, 50, 95]).round(1).tolist()} mm (min {lr.min():.2f}) | k {k:g} / {kc:g}, rayo {mx * 1000:g} mm")


def cuello_flexion_por_capa(ES):
    """Flexion por zona: b_zona = mult x bending, como peso del grupo 'rigidez' (lineal entre bending y bend_max). El cierre queda en 1 (bend_max)."""
    mult = ES.RD.get("flexion_zonas", {}); b0, bm = ES.P["bending"], ES.P["bend_max"]
    # r7: flexion_zonas_abs = flexion ABSOLUTA de una zona (no sigue a la base). El cuello lleva entretela y 4 capas pespunteadas: al bajar la
    # flexion del ecocuero (120 -> 20) no baja con el. Con base 120, cuello 360 = x3: las recetas viejas (h1..c2) dan los mismos pesos.
    absz = ES.RD.get("flexion_zonas_abs", {})
    W = _pesos(ES, "rigidez"); W0 = W.copy(); zip_ = set(ES.D["zipper"]); res = []
    for z, m in mult.items():
        ids = np.array([i for i in ES.D["zonas"].get(z, []) if i not in zip_], int)
        if not len(ids):
            continue
        bz = float(absz[z]) if z in absz else m * b0
        w = float(np.clip((bz - b0) / max(bm - b0, 1e-9), 0.0, 1.0)); W[ids] = np.maximum(W[ids], w)
        res.append(f"{z} {'abs' if z in absz else f'x{m:g}'} -> {b0 + (bm - b0) * w:.0f} ({len(ids)} v, peso {w:.3f})")
    chg = np.where(np.abs(W - W0) > 1e-9)[0]
    for i in chg:
        ES.vrig.add([int(i)], float(W[i]), "REPLACE")
    ES.log(f"M1195 FLEXION por zona (base {b0:g}, tope {bm:g}, cierre {len(zip_)} v en {bm:g}): " + " | ".join(res) + f" | {len(chg)} pesos escritos")


def metricas_definir(ES):
    mk = ES.D["marcadores"]; ES.MK = {k: (np.array(v, int) if isinstance(v, list) else int(v)) for k, v in mk.items()}
    import sys
    sys.path.insert(0, os.path.join(ES.ENT, "sim"))
    import ficha_m1195
    ES.FM = ficha_m1195; ES.HOMN = ficha_m1195.hombro_natural(ES.D)          # r5: cotas por recorrido (lineas de capa 8) y hombro natural
    ES.log(f"M1195 metricas r5: ficha por recorrido ({ficha_m1195.__file__}); molde: " + ficha_m1195.texto(ficha_m1195.medir(ES.D, np.array(ES.D['uv'])), ("A", "C", "D", "K", "L")))
    B = np.load(ES.RUTA(ES.BODY)); ES.BV20 = B["V20"]; ES.BV8 = B["V8"]; ES.BCAB = B["cabeza"].astype(bool); ES.BT = B["T"]
    ES.HEADV = np.unique(ES.BT[ES.BCAB]) if ES.BCAB.any() else np.array([], int)
    ES.F1 = None; ES.SH1 = []
    ES.log(f"M1195 metricas: ruedo {len(ES.MK['ruedo'])} v, punos {len(ES.MK['puno_R'])}/{len(ES.MK['puno_L'])}, CB {len(ES.MK['cb'])} v, canto {len(ES.MK['canto_cuello'])} v, "
           f"filas del cierre {len(ES.MK['zip_filas'])}, hombro R/L {ES.MK['hombro_R']}/{ES.MK['hombro_L']} | cuerpo {len(ES.BV20)} v, cabeza {len(ES.HEADV)} v")


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
    """largo de un anillo cerrado ordenado por azimut alrededor de su centroide (mm)."""
    P = X[ids]; c = P.mean(0); az = np.arctan2(P[:, 1] - c[1], P[:, 0] - c[0]); o = np.argsort(az); Q = P[o]
    return float((np.linalg.norm(np.diff(Q, axis=0), axis=1).sum() + np.linalg.norm(Q[0] - Q[-1])) * 1000)


def _numeros(ES, X):
    mk = ES.MK; H = X[mk["ruedo"]]
    zR = float(np.median(H[H[:, 0] < 0, 2]) * 1000); zL = float(np.median(H[H[:, 0] > 0, 2]) * 1000)
    zf = np.array(mk["zip_filas"]); Z = X[zf].mean(1)
    cb = X[mk["cb"]]; zcb = float(cb[-1, 2] * 1000)                         # ultimo = el mas bajo (ruedo CB)
    canto = X[mk["canto_cuello"]]; pie = X[mk["pie_hoja"]]
    return dict(ruedo_R=zR, ruedo_L=zL, ruedo_CB=zcb, ruedo_CF=float(Z[0, 2] * 1000), canto_z=float(canto[:, 2].mean() * 1000), pie_z=float(pie[:, 2].mean() * 1000),
                puno_R=float(X[mk["puno_R"], 2].mean() * 1000), puno_L=float(X[mk["puno_L"], 2].mean() * 1000),
                zip_x_pecho=float(Z[Z[:, 2] > 1.2, 0].mean() * 1000) if (Z[:, 2] > 1.2).any() else float("nan"), zip_x_ruedo=float(Z[Z[:, 2] < 1.0, 0].mean() * 1000) if (Z[:, 2] < 1.0).any() else float("nan"))


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
    hom = ES.HOMN; dh = _dmin(X[hom], BV) * 1000                                   # r5: linea de hombro natural (espR/espL l4), no la costura del canesu
    cue = np.r_[np.arange(*ES.D["groups"]["cuA"]), np.arange(*ES.D["groups"]["pieA"])]
    dcab = _dmin(X[cue], BV[ES.HEADV]) * 1000 if len(ES.HEADV) else np.array([float("nan")])
    dz_cos = {s_: float((X[np.arange(*ES.D["groups"]["cos" + s_]), 2].mean() - ES.V0[np.arange(*ES.D["groups"]["cos" + s_]), 2].mean()) * 1000) for s_ in "RL"}
    med = ES.FM.medir(ES.D, X * 1000)
    ES.log(f"   M1195 CAIDA ruedo R {n['ruedo_R'] - f1['ruedo_R']:+.0f} L {n['ruedo_L'] - f1['ruedo_L']:+.0f} CB {n['ruedo_CB'] - f1['ruedo_CB']:+.0f} CF {n['ruedo_CF'] - f1['ruedo_CF']:+.0f} mm desde f1 | costado z R {dz_cos['R']:+.0f} L {dz_cos['L']:+.0f} vs V0 | "
           f"R-L ruedo {n['ruedo_R'] - n['ruedo_L']:+.0f} puno {n['puno_R'] - n['puno_L']:+.0f} mm | TORSION cierre x pecho {n['zip_x_pecho']:+.0f} ruedo {n['zip_x_ruedo']:+.0f} mm")
    ES.log(f"   M1195 HOMBRO costura-piel med {np.median(dh):.1f} p95 {np.percentile(dh, 95):.1f} max {dh.max():.1f} mm (apoyado ~ th+cd {1000 * (ES.P['bth'] if ES.P['bth'] >= 0 else ES.P['th']) + 1000 * ES.P['cd']:.0f}) | "
           f"CUELLO canto z med {n['canto_z']:.0f} vs quiebre pie-hoja {n['pie_z']:.0f} ({'doblado' if n['canto_z'] < n['pie_z'] else 'LEVANTADO'}) | cuello-cabeza min {dcab.min():.1f} mm")
    ES.log("   M1195 FICHA (recorridos) " + ES.FM.texto(med, ("G", "A", "C", "D", "F", "K", "L")) + f" | K R/L {med['K_R'][0]:.0f}/{med['K_L'][0]:.0f} | L R/L {med['L_R'][0]:.0f}/{med['L_L'][0]:.0f}")
