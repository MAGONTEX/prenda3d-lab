"""[ESC·f535] M133: indicadores de _qc_R16/medir_R16.py (R16) DENTRO del trabajo de GitHub Actions (prenda.yml, tanda con `medir`).
Las funciones de medida son copia literal de medir_R16.py; cambian solo las entradas: la malla por ruta, los extremos de la costura
de la espalda en m133_medir.json (3 numeros sacados del molde; la moldería no se publica) y cruce_np al lado de este archivo.
uso: python medir_m133.py malla=<malla.json> dir=<carpeta con X_<tag>_f<N>.npy y sim_<tag>.log> tag=<tag> cuadros=20,60 json=<salida.json>
Mide los cuadros pedidos que existan y, si la corrida se corto antes, tambien su ultimo dump. Ademas: COSTURAS = hueco maximo por costura
(pares cosidos de la malla, mm) y las que pasan 5 mm; HUELLAS = sha256 (16) de cada X_<tag>_f*.npy (replicas no nulas: f2 distinto);
PARAMS = los de la linea `params` del log que deciden la tanda (bi_k, relleno...).
Indicadores (definiciones de medir_R16.py):
 REL  relieve de canales de la espalda: relieve3d de analisis_e2e.py (flecha de la cascara a la cuerda entre pespuntes vecinos,
      'afuera' = lejos del eje Z) en 5 rectas del molde de la espalda (y = yc + -200..200 mm), solo canales interiores (sin el de
      arriba ni el del ruedo): mediana de la flecha (mm) y de amp = flecha/cuerda.
 CART cartera (tp) en 3 sectores por s del cierre (uv0 del zp mas cercano en el V0; s=0 arriba): cuello s<150, cierre 150-612,
      ruedo s>612. cruces = pares de triangulos que se cortan con una cara de tp del sector (cruce_np, sin caras que comparten
      vertice); pen = penetracion tp x delanteros: tp por DEBAJO de la cara externa de fc/fs, o fc/fs por ENCIMA de la tp, a
      lateral <= 4 mm de la normal (tp a > 15 mm de la costura 'tapeta' en el V0): n vertices a > 1 mm, p95 y max (mm).
 SISA sisa de atras L/R: zona = vertices de back y sl a <= 40 mm de la costura 'sisa espalda' en el cuadro. cruces de cascaras
      en la zona; forro que asoma = vertice de forro (back_f/sl_f, mismo indice local) por FUERA de su cascara > 1 mm (n, max);
      hueco max de la costura (mm, pares cosidos).
 HB   costura banda-capucha: hueco p95/max (mm, pares cosidos) y cruces hb x capucha (hc/hs/ht).
"""
import sys, os, json, collections, numpy as np
from scipy.spatial import cKDTree
import matplotlib.tri as mtri
sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__)) + os.sep
sys.path.insert(0, AQUI); import cruce_np
MB = json.load(open(AQUI + "m133_medir.json", encoding="utf-8"))   # extremos de la linea de costura de la espalda (molde, mm)
_M = {}
def malla(nm):
    if nm in _M: return _M[nm]
    D = json.load(open(nm, encoding="utf-8")); G = D["groups"]; F = np.array(D["f"]); V0 = np.array(D["v"], float); UV = np.array(D["uv"], float); NV = len(V0)
    SW = np.array(D["sew"]); SN = np.array(D["sew_seam"]); g = np.full(NV, "", object)
    for k, (a, b) in G.items(): g[a:b] = k
    FF, FG = cruce_np.prep(D)
    zp0, zp1 = G["zp"]; tp0, tp1 = G["tp"]; _, iz = cKDTree(V0[zp0:zp1]).query(V0[tp0:tp1]); s = np.full(NV, np.nan); s[tp0:tp1] = UV[zp0 + iz, 0]
    tap = np.unique(SW[SN == "tapeta"].ravel()); tap = tap[(tap >= tp0) & (tap < tp1)]
    tpok = np.zeros(NV, bool); tpok[tp0:tp1] = cKDTree(V0[tap]).query(V0[tp0:tp1])[0] > 0.015
    sh = ["back", "fcR", "fcL", "fsR", "fsL", "slR", "slL", "hsR", "hsL", "hc", "htR", "htL", "tp", "zp", "hb"]
    cxy = V0[np.concatenate([np.arange(*G[k]) for k in ("back", "fcR", "fcL", "fsR", "fsL")])][:, :2].mean(0)
    n0 = vnorm(V0, F, NV); sgn = np.ones(NV)
    for k in sh:                                        # normal hacia afuera por pieza (voto en el V0, radial desde el eje del torso)
        a, b = G[k]; r = V0[a:b, :2] - cxy; dots = (n0[a:b, :2] * r).sum(1); sgn[a:b] = 1.0 if dots.sum() >= 0 else -1.0
    M = dict(D=D, G=G, F=F, V0=V0, UV=UV, NV=NV, SW=SW, SN=SN, g=g, FF=FF, FG=FG, s=s, tpok=tpok, sgn=sgn); _M[nm] = M; return M
def vnorm(X, F, NV):
    n = np.cross(X[F[:, 1]] - X[F[:, 0]], X[F[:, 2]] - X[F[:, 0]]); N = np.zeros((NV, 3))
    for i in range(3): np.add.at(N, F[:, i], n)
    return N / (np.linalg.norm(N, axis=1)[:, None] + 1e-15)
def cruces_idx(Xm, FF, sel):
    C = Xm[FF].mean(1); idx = np.where(sel)[0]
    pr = cKDTree(C[idx]).query_pairs(20.0, output_type="ndarray"); a, b = idx[pr[:, 0]], idx[pr[:, 1]]
    share = np.zeros(len(a), bool)
    for i in range(3):
        for j in range(3): share |= FF[a, i] == FF[b, j]
    a, b = a[~share], b[~share]; hit = np.zeros(len(a), bool); TA = Xm[FF[a]]; TB = Xm[FF[b]]
    for (i, j) in ((0, 1), (1, 2), (2, 0)):
        hit |= cruce_np.seg_tri(TA[:, i], TA[:, j], TB[:, 0], TB[:, 1], TB[:, 2]); hit |= cruce_np.seg_tri(TB[:, i], TB[:, j], TA[:, 0], TA[:, 1], TA[:, 2])
    return a[hit], b[hit]
def profund(Xm, FF, a, b):
    """profundidad de cada par que se corta (mm): lo minimo que habria que mover un triangulo por la normal del otro para separarlos."""
    TA, TB = Xm[FF[a]], Xm[FF[b]]
    def lado(P, Q):
        n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]); n /= np.linalg.norm(n, axis=1)[:, None] + 1e-15
        d = ((Q - P[:, :1]) * n[:, None]).sum(2); return np.minimum(np.clip(d, 0, None).max(1), np.clip(-d, 0, None).max(1))
    return np.minimum(lado(TA, TB), lado(TB, TA))
def relieve3d(D, X, n, p0, p1, lx):                    # = analisis_e2e.relieve3d (copia literal salvo los argumentos)
    I = D["inst"][n]; o = I["off"]; Fl = np.array(D["faces_local"][I["key"]]); nv = int(Fl.max()) + 1; uv = np.array(D["uv"])[o:o + nv]; xyz = X[o:o + nv]
    tf = mtri.Triangulation(uv[:, 0], uv[:, 1], Fl).get_trifinder()
    def at(q):
        j = tf(q[0], q[1])
        if j < 0: return None
        a, b, c = Fl[j]; Mm = np.array([[uv[a, 0] - uv[c, 0], uv[b, 0] - uv[c, 0]], [uv[a, 1] - uv[c, 1], uv[b, 1] - uv[c, 1]]]); l1, l2 = np.linalg.solve(Mm, q - uv[c])
        return l1 * xyz[a] + l2 * xyz[b] + (1 - l1 - l2) * xyz[c]
    out = []; lx = sorted(lx)
    for xa, xb in zip(lx, lx[1:]):
        qs = [np.array(p0) + (np.array(p1) - np.array(p0)) * t for t in np.linspace(0, 1, 800)]
        seg = [at(q) for q in qs if xa <= q[0] <= xb]; seg = [q for q in seg if q is not None]
        if len(seg) < 10: out.append(None); continue
        seg = np.array(seg); A0, B0 = seg[0], seg[-1]; c = B0 - A0; L = np.linalg.norm(c); u = c / L; mid = seg.mean(0)
        r0 = mid - np.array([0, 0, mid[2]]); r0 = r0 - (r0 @ u) * u; r0 /= max(np.linalg.norm(r0), 1e-12)
        d = (seg - A0) @ r0; out.append(dict(amp=float(d.max() / L), flecha=1000 * float(d.max())))
    return out
def medir(X, M):
    D, G, F, NV, SW, SN, g, FF, FG, s = M["D"], M["G"], M["F"], M["NV"], M["SW"], M["SN"], M["g"], M["FF"], M["FG"], M["s"]
    X = X[:NV]; Xm = X * 1000; N = vnorm(X, F, NV) * M["sgn"][:, None]; R = {}
    xs = np.array([MB["back_x_min"], MB["back_x_max"]]); yc = MB["back_yc"]; lxb = [xs.min() + 1] + sorted(D["lx"]["back"]) + [xs.max() - 1]
    fl, am = [], []
    for dy in (-200, -100, 0, 100, 200):
        ch = relieve3d(D, X, "back", (xs.min(), yc + dy), (xs.max(), yc + dy), lxb)[1:-1]
        fl += [c["flecha"] for c in ch if c]; am += [c["amp"] for c in ch if c]
    R["rel_flecha"] = float(np.median(fl)); R["rel_amp"] = float(np.median(am)); R["rel_n"] = len(fl)
    # zonas
    tp0, tp1 = G["tp"]; T = np.arange(tp0, tp1); sec = {"cuello": T[s[T] < 150], "cierre": T[(s[T] >= 150) & (s[T] <= 612)], "ruedo": T[s[T] > 612]}
    sis = {sd: np.unique(SW[SN == "sisa espalda " + sd].ravel()) for sd in "RL"}
    zs = {}
    for sd in "RL":
        cand = np.concatenate([np.arange(*G["back"]), np.arange(*G["sl" + sd])]); dd = cKDTree(X[sis[sd]]).query(X[cand])[0]; zs[sd] = cand[dd <= 0.040]
    hbv = np.arange(*G["hb"])
    zona = np.zeros(NV, bool); zona[T] = True; zona[hbv] = True
    for sd in "RL": zona[zs[sd]] = True
    near = np.zeros(NV, bool); near[np.where(zona)[0]] = True
    kz = cKDTree(Xm[zona]); dz = kz.query(Xm)[0]; near = dz <= 30.0                     # caras a <= 30 mm de alguna zona
    sel = near[FF].any(1); a, b = cruces_idx(Xm, FF, sel); ga, gb = FG[a], FG[b]
    C0 = M["V0"][FF].mean(1); sv = np.zeros(NV, bool); sv[SW.ravel()] = True; sfc = sv[FF].any(1)
    cosida = sfc[a] & sfc[b] & (np.linalg.norm(C0[a] - C0[b], axis=1) < 0.015)      # contacto de costura (las dos caras tocan vertices cosidos y estaban a < 15 mm en el V0)
    R["cruces_cosidos"] = int(cosida.sum()); a, b = a[~cosida], b[~cosida]; ga, gb = FG[a], FG[b]; prof = profund(Xm, FF, a, b); R["cruces_zonas"] = int(len(a))
    def st(m, pre):
        p = prof[m]; R[pre + "_n"] = int(m.sum()); R[pre + "_p95"] = float(np.percentile(p, 95)) if len(p) else 0.0; R[pre + "_max"] = float(p.max()) if len(p) else 0.0
    for k, v in sec.items():
        vs = np.zeros(NV, bool); vs[v] = True; ta = (ga == "tp") & vs[FF[a]].any(1); tb = (gb == "tp") & vs[FF[b]].any(1); st(ta | tb, "cart_" + k)
    # sisas
    for sd in "RL":
        vz = np.zeros(NV, bool); vz[zs[sd]] = True; st(vz[FF[a]].any(1) | vz[FF[b]].any(1), "sisa" + sd)
        asom = []
        for k in ("back", "sl" + sd):
            a0, b0 = G[k]; f0 = G[k + "_f"][0]; vv = zs[sd][(zs[sd] >= a0) & (zs[sd] < b0)]; fv = vv - a0 + f0
            asom.append(((X[fv] - X[vv]) * N[vv]).sum(1) * 1000)
        asom = np.concatenate(asom); R[f"sisa{sd}_asoma_n"] = int((asom > 1.0).sum()); R[f"sisa{sd}_asoma_max"] = float(max(asom.max(), 0))
        P = SW[SN == "sisa espalda " + sd]; R[f"sisa{sd}_gap_max"] = float((np.linalg.norm(X[P[:, 0]] - X[P[:, 1]], axis=1) * 1000).max())
    P = SW[SN == "banda-capucha"]; gp = np.linalg.norm(X[P[:, 0]] - X[P[:, 1]], axis=1) * 1000
    R["hb_gap_p95"] = float(np.percentile(gp, 95)); R["hb_gap_max"] = float(gp.max())
    hood = np.isin(ga, ["hc", "hsR", "hsL", "htR", "htL"]) & (gb == "hb") | np.isin(gb, ["hc", "hsR", "hsL", "htR", "htL"]) & (ga == "hb"); st(hood, "hbx")
    R["hb_cruces_todo"] = int(((ga == "hb") | (gb == "hb")).sum())
    return R
def costuras(X, M):
    """hueco maximo por costura (mm) con los pares cosidos de la malla (= costuras_gap del simulador, en este cuadro)."""
    SW, SN = M["SW"], M["SN"]; X = X[:M["NV"]]
    gp = np.linalg.norm(X[SW[:, 0]] - X[SW[:, 1]], axis=1) * 1000
    mx = {str(nm): float(gp[SN == nm].max()) for nm in np.unique(SN)}
    ap = {n: mx.pop(n) for n in NO_COSTURA if n in mx}
    k = max(mx, key=mx.get); g5 = {n: round(v, 1) for n, v in sorted(mx.items(), key=lambda kv: -kv[1]) if v > 5.0}
    return {"costura_max_mm": mx[k], "costura_max": k, "costuras_gt5_n": len(g5), "costuras_gt5": g5, "aparte_mm": ap}
NO_COSTURA = ("broche",)   # pares viejos del broche: la sim los saca y pone el separador de 4,5 mm (e2zd); su distancia es la altura del broche
def leer_log(ruta):
    import ast
    R = {"params": {}, "stop": [], "cortada_f": None, "asentada_f": None, "fin": False}
    if not os.path.isfile(ruta): return R
    L = open(ruta, encoding="utf-8", errors="replace").read().splitlines()
    for l in L:
        if l.startswith("params ") and " frames " in l and not R["params"]:
            try:
                P = ast.literal_eval(l[len("params "):l.rindex(" frames ")])
                R["params"] = {k: P[k] for k in CLAVES if k in P}
            except Exception as ex:
                R["params"] = {"error": str(ex)[:120]}
        elif l.startswith("malla "): R["malla_log"] = l.split(" ", 1)[1].strip()
        elif l.startswith("STOP"): R["stop"].append(l[:200])
        elif l.startswith("corrida cortada en f"): R["cortada_f"] = int(l.split()[-1])
        elif l.startswith("asentamiento cumplido"): R["asentada_f"] = int(l.split()[-1])
        elif l.startswith("fin "): R["fin"] = True
    return R
CLAVES = ("bi_k", "bi_w", "relleno", "relleno_h", "relleno_r", "relleno_g", "sand_kc", "sand_len", "pl_bh", "pc_w", "hf", "hf_w", "fric", "muneca", "bth", "ath", "stop_open")
def main():
    import hashlib, re
    A = dict(x.split("=", 1) for x in sys.argv[1:] if "=" in x)
    tag, d = A["tag"], A["dir"]; cu = [int(c) for c in A.get("cuadros", "").split(",") if c]
    rx = re.compile(r"^X_" + re.escape(tag) + r"_f(\d+)\.npy$")
    hechos = sorted(int(m.group(1)) for m in (rx.match(f) for f in os.listdir(d)) if m)
    out = {"tag": tag, "malla": os.path.basename(A["malla"]), "cuadros_pedidos": cu, "dumps": hechos,
           "huellas": {f"f{n}": hashlib.sha256(open(os.path.join(d, f"X_{tag}_f{n}.npy"), "rb").read()).hexdigest()[:16] for n in hechos},
           "log": leer_log(os.path.join(d, f"sim_{tag}.log")), "medidor": "medir_m133.py (= _qc_R16/medir_R16.py + costuras)"}
    pedir = [c for c in cu if c in hechos]
    if hechos and hechos[-1] not in pedir: pedir.append(hechos[-1])   # corrida cortada: tambien su ultimo dump
    out["ultimo"] = hechos[-1] if hechos else None
    if pedir: M = malla(A["malla"])
    for n in pedir:
        X = np.load(os.path.join(d, f"X_{tag}_f{n}.npy")); R = medir(X, M); R.update(costuras(X, M)); out[f"f{n}"] = R
        f = lambda p: "%3d/%4.1f/%4.1f" % (R[p + "_n"], R[p + "_p95"], R[p + "_max"])
        print("%-14s f%-3d REL %4.1f mm | CART cu %s ci %s ru %s | SISA R %s L %s | HB gap %3.1f/%3.1f x %s | costuras>5 %d (max %.1f %s)" % (
            tag, n, R["rel_flecha"], f("cart_cuello"), f("cart_cierre"), f("cart_ruedo"), f("sisaR"), f("sisaL"), R["hb_gap_p95"], R["hb_gap_max"], f("hbx"),
            R["costuras_gt5_n"], R["costura_max_mm"], R["costura_max"]), flush=True)
    json.dump(out, open(A["json"], "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
    return 0
if __name__ == "__main__":
    sys.exit(main())
