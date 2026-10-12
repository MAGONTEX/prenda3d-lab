# [ESC·f535] PT-puente (2026-10-11): margen de costura del CUELLO (hsR/hsL/hc) que cruza la costura escote-cuello
# ("cuello-capucha") y se cose en su canto al cuerpo = banco 1 m10p (LEYES L1-2: margen 10 + pespunte en el canto = tela continua).
# El margen continua el plano del cuello en el molde (reposo plano, flexion heredada) y en el V0 va por DENTRO del cuerpo,
# a `off` mm de la cascara, hasta el vertice del cuerpo a ~w mm de la costura (pespunte = resorte de costura canto->cuerpo).
# Reposo del margen = espejo de la franja real del cuerpo (largos iguales) -> sin estiramiento al coserse.
# Uso: sim_e2s.py pt_w=10 [pt_off=4.5]  |  chequeo sin Blender: python _qc_PT/puente_PT.py m133_e2zzh1.json [w] [off]
import numpy as np
COLLAR = ("hsR", "hsL", "hc"); BODY = ("back", "fcR", "fcL", "fsR", "fsL")

def _u(x):
    n = np.linalg.norm(x); return x / n if n > 1e-12 else x

def margen(D, V0, w=10.0, off=4.5, seam="cuello-capucha", rows=0, hmax=12.0):
    if rows > 0: return margen_hueco(D, V0, w, off, seam, rows, hmax)   # [ESC·f535] PTH: rows=0 = PT/PT-R tal cual
    G = D["groups"]; nv0 = len(V0); UV = np.array(D["uv"], float)[:nv0]; F = np.array(D["f"], int); V0 = np.asarray(V0, float)
    names = list(G); pid = np.full(nv0, -1)
    for k, n in enumerate(names):
        a, b = G[n]; pid[a:min(b, nv0)] = k
    pn = lambda i: names[pid[i]] if pid[i] >= 0 else None
    par = {}
    for (a, b), s in zip(D["sew"], D["sew_seam"]):
        if s != seam: continue
        if pn(a) in BODY and pn(b) in COLLAR: a, b = b, a
        if pn(a) in COLLAR and pn(b) in BODY and a not in par: par[a] = b
    A = sorted(par); Aset = set(A); Bset = set(par.values())
    cm = np.isin(pid, [names.index(n) for n in COLLAR if n in names]); Fc = F[cm[F].all(1)]
    cnt = {}
    for f in Fc:
        for x, y in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])):
            k = (min(x, y), max(x, y)); cnt[k] = cnt.get(k, 0) + 1; cnt[(x, y, "d")] = 1
    bnd = [(x, y) for (x, y, *_) in [k for k in cnt if len(k) == 3] if cnt[(min(x, y), max(x, y))] == 1 and x in Aset and y in Aset]
    nb = {a: [] for a in A}
    for x, y in bnd: nb[x].append(y); nb[y].append(x)
    def inward(i, Fp, Tn):   # normal en el molde que entra a la pieza de i (lado de sus vecinos fuera de la costura)
        rows = Fp[(Fp == i).any(1)]; o = [j for j in set(rows.ravel()) if j != i and j not in Aset and j not in Bset]
        if not o: return Tn
        return Tn if np.dot(UV[o].mean(0) - UV[i], Tn) > 0 else -Tn
    mloc = {}; vout, uvout, sew, parl, taken, rw, dmd = [], [], [], [], set(), [], []
    C = V0[A].mean(0)
    for a in A:
        b = par[a]; pb = pn(b); ga, gb = G[pb]
        nbs = [x for x in nb[a] if pn(par[x]) == pb] or nb[a]
        if not nbs: continue
        Tc = _u(UV[nbs[0]] - UV[a]); Tb = _u(UV[par[nbs[0]]] - UV[b]) if pn(par[nbs[0]]) == pb else None
        Nout = -inward(a, Fc, np.array([-Tc[1], Tc[0]]))
        Fb = F[(F >= ga).all(1) & (F < gb).all(1)]
        Tb_ = Tb if Tb is not None else Tc
        Nin = inward(b, Fb, np.array([-Tb_[1], Tb_[0]]))
        q = UV[b] + w * Nin; ids = np.arange(ga, gb); dd = np.linalg.norm(UV[ga:gb] - q, axis=1)
        d = None
        for j in np.argsort(dd)[:6]:
            c = int(ids[j]); r = UV[c] - UV[b]
            if c in taken or c in Bset or dd[j] > 0.6 * w or np.dot(r, Nin) < 0.5 * w: continue
            d = c; break
        if d is None: r = w * Nin
        else: r = UV[d] - UV[b]; taken.add(d)
        t = float(np.dot(r, Tb)) if Tb is not None else 0.0; n = float(np.dot(r, Nin))
        uvm = UV[a] + t * Tc + n * Nout; L = np.linalg.norm(uvm - UV[a]) / 1000.0
        tgt = V0[d] if d is not None else V0[b]
        rows = Fb[(Fb == (d if d is not None else b)).any(1)]
        n3 = np.zeros(3)
        for f in rows: n3 += np.cross(V0[f[1]] - V0[f[0]], V0[f[2]] - V0[f[0]])
        n3 = _u(n3); n3 = n3 if np.dot(n3, C - tgt) > 0 else -n3
        p = tgt + off / 1000.0 * n3; p = V0[a] + (p - V0[a]) * L / max(np.linalg.norm(p - V0[a]), 1e-9)
        mloc[a] = len(vout); vout.append(p); uvout.append(uvm); parl.append(a); rw.append(L * 1000)
        if d is not None: sew.append((mloc[a], d)); dmd.append(np.linalg.norm(p - V0[d]) * 1000)
    fac = []
    for x, y in bnd:
        if x in mloc and y in mloc: fac += [[y, x, nv0 + mloc[x]], [y, nv0 + mloc[x], nv0 + mloc[y]]]
    U2 = np.array(uvout); oth = ~np.isin(pid, [names.index(n) for n in COLLAR if n in names]) & (pid >= 0)
    dmin = min(np.linalg.norm(UV[oth] - u, axis=1).min() for u in U2) if len(U2) else -1
    msg = (f"seam '{seam}' w {w} off {off} | margen {len(vout)} v (de {len(A)} v de costura del cuello), {len(fac)} caras, pespunte {len(sew)} | "
           f"ancho reposo p50 {np.median(rw):.1f} min {min(rw):.1f} max {max(rw):.1f} mm | canto-cuerpo en V0 p50 {np.median(dmd):.2f} max {max(dmd):.2f} mm | "
           f"molde: otra pieza a >= {dmin:.1f} mm del margen")
    return dict(v=[list(map(float, p)) for p in vout], uv=[list(map(float, u)) for u in uvout], f=fac,
                sew=[(nv0 + m, d) for m, d in sew], par=parl, msg=msg)

if __name__ == "__main__":
    import json, sys
    D = json.load(open(sys.argv[1], encoding="utf-8")); w = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0
    off = float(sys.argv[3]) if len(sys.argv) > 3 else 4.5
    r = margen(D, np.array(D["v"], float), w, off); print(r["msg"])
    V = np.vstack([np.array(D["v"]), np.array(r["v"])]); UVx = np.vstack([np.array(D["uv"]), np.array(r["uv"])])
    e = [(f[i], f[(i + 1) % 3]) for f in r["f"] for i in range(3)]
    s = np.array([np.linalg.norm(V[x] - V[y]) * 1000 / max(np.linalg.norm(UVx[x] - UVx[y]), 1e-9) - 1 for x, y in e])
    ar = np.array([np.cross(UVx[f[1]] - UVx[f[0]], UVx[f[2]] - UVx[f[0]]) for f in r["f"]])
    print(f"aristas del margen V0/reposo - 1: p5 {np.percentile(s, 5):+.3f} p50 {np.median(s):+.3f} p95 {np.percentile(s, 95):+.3f} | "
          f"caras de area de molde ~0: {(np.abs(ar) < 5).sum()} | signo de area +/-: {(ar > 0).sum()}/{(ar < 0).sum()}")

def reposo(kc, nv0, par, uv):
    """[ESC·f535] PT-R (2026-10-11): reposo del margen = reposo de SU vertice del cuello + el desplazamiento en el plano del molde (uv_m - uv_a).
    Causa del lado R roto (F535pe1s): sand_lvl pone hsR a z=+50 mm en la clave molde_plano y el margen quedaba en (u, w, 0) -> peldano R de reposo
    ~51 mm (x4,8 sobre 10,7) y en f2 (cuando el reposo pasa al molde) el margen R cae 14 mm y abre la costura. hsL y hc estan en z=0: L y C no cambian.
    Vale para traslaciones del reposo del cuello (niveles z, traslaciones xy); no para un reposo 3D (hrest) ni rampas rk."""
    rr = []
    for k, a in enumerate(par):
        m = nv0 + k; ca = kc.data[a].co
        kc.data[m].co = (ca[0] + (uv[m][0] - uv[a][0]) / 1000.0, ca[1] + (uv[m][1] - uv[a][1]) / 1000.0, ca[2])
        lr = np.hypot(uv[m][0] - uv[a][0], uv[m][1] - uv[a][1]); d = np.linalg.norm(np.array(kc.data[m].co[:]) - np.array(ca[:])) * 1000.0
        rr.append((d / max(lr, 1e-9), ca[2] * 1000.0))
    rr = np.array(rr)
    return f"peldano reposo/molde p50 {np.median(rr[:, 0]):.3f} max {rr[:, 0].max():.3f} | z del reposo del cuello (mm) {sorted(set(np.round(rr[:, 1], 1).tolist()))}"

def _ray(o, d, T, tmin=5e-5):   # [ESC·f535] PTH: primer impacto t > tmin (m) del rayo o + t*d (d unitario) contra los triangulos T (m x 3 x 3); inf si no hay
    if not len(T): return np.inf
    a = T[:, 0]; e1 = T[:, 1] - a; e2 = T[:, 2] - a; h = np.cross(d, e2); det = np.einsum("ij,ij->i", e1, h); ok = np.abs(det) > 1e-18
    inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0); s = o - a; u = np.einsum("ij,ij->i", s, h) * inv; q = np.cross(s, e1)
    v = (q @ d) * inv; t = np.einsum("ij,ij->i", e2, q) * inv; hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > tmin)
    return float(t[hit].min()) if hit.any() else np.inf

def margen_hueco(D, V0, w=10.0, off=4.5, seam="cuello-capucha", rows=2, hmax=12.0):
    """[ESC·f535] PTH (2026-10-11): el margen como TIRA de `rows` filas que sigue la cara interna de la cascara, a la MITAD del hueco entre la cascara
    y la primera capa de adentro (vista fa, forro *_f, ht, tapeta...), medido POR FILA en el V0 de la sim (forro ya a P["off"]). Fila j: punto de la
    cascara en el molde uv_b + (j/rows)(uv_d - uv_b) (baricentricas), normal hacia adentro = -normal de vertice (la que usa el forro), rayo a la capa
    siguiente -> prof = hueco/2 (si no hay capa a <= hmax mm: off). Reposo de la fila j = uv_a + (j/rows)(uv_canto - uv_a) (mismo canto que PT).
    Pespunte solo en el canto (ultima fila) -> d. Misma pareja a/b/d, mismo uv del canto y misma cara de molde que margen(rows=0)."""
    G = D["groups"]; nv0 = len(V0); UV = np.array(D["uv"], float)[:nv0]; F = np.array(D["f"], int); V0 = np.asarray(V0, float)
    names = list(G); pid = np.full(nv0, -1)
    for k, n in enumerate(names):
        a, b = G[n]; pid[a:min(b, nv0)] = k
    pn = lambda i: names[pid[i]] if pid[i] >= 0 else None
    par = {}
    for (a, b), s in zip(D["sew"], D["sew_seam"]):
        if s != seam: continue
        if pn(a) in BODY and pn(b) in COLLAR: a, b = b, a
        if pn(a) in COLLAR and pn(b) in BODY and a not in par: par[a] = b
    A = sorted(par); Aset = set(A); Bset = set(par.values())
    cm = np.isin(pid, [names.index(n) for n in COLLAR if n in names]); Fc = F[cm[F].all(1)]
    cnt = {}
    for f in Fc:
        for x, y in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])):
            k = (min(x, y), max(x, y)); cnt[k] = cnt.get(k, 0) + 1; cnt[(x, y, "d")] = 1
    bnd = [(x, y) for (x, y, *_) in [k for k in cnt if len(k) == 3] if cnt[(min(x, y), max(x, y))] == 1 and x in Aset and y in Aset]
    nb = {a: [] for a in A}
    for x, y in bnd: nb[x].append(y); nb[y].append(x)
    def inward(i, Fp, Tn):
        rows_ = Fp[(Fp == i).any(1)]; o = [j for j in set(rows_.ravel()) if j != i and j not in Aset and j not in Bset]
        if not o: return Tn
        return Tn if np.dot(UV[o].mean(0) - UV[i], Tn) > 0 else -Tn
    bm = np.isin(pid, [names.index(n) for n in BODY if n in names]); FB = F[bm[F].all(1)]
    VN = np.zeros_like(V0); fn = np.cross(V0[FB[:, 1]] - V0[FB[:, 0]], V0[FB[:, 2]] - V0[FB[:, 0]])
    for j in range(3): np.add.at(VN, FB[:, j], fn)
    VN /= np.maximum(np.linalg.norm(VN, axis=1, keepdims=True), 1e-12)   # hacia AFUERA (el forro va a -off*VN en sim_e2s.py l.268)
    im = (pid >= 0) & ~cm & ~bm; TI = V0[F[im[F].all(1)]]; cen = TI.mean(1); SR = V0[A]
    keep = np.zeros(len(TI), bool)
    for i0 in range(0, len(TI), 20000):
        keep[i0:i0 + 20000] = np.min(np.linalg.norm(cen[i0:i0 + 20000, None, :] - SR[None], axis=2), axis=1) < 0.045
    TI = TI[keep]
    def sup(q, Fb):   # punto, normal hacia adentro (interpolada) de la pieza en la coordenada de molde q (mm)
        A_ = UV[Fb[:, 0]]; v0 = UV[Fb[:, 1]] - A_; v1 = UV[Fb[:, 2]] - A_; v2 = q - A_
        den = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]; ok = np.abs(den) > 1e-12; dd_ = np.where(ok, den, 1.0)
        l1 = np.where(ok, (v2[:, 0] * v1[:, 1] - v1[:, 0] * v2[:, 1]) / dd_, -1); l2 = np.where(ok, (v0[:, 0] * v2[:, 1] - v2[:, 0] * v0[:, 1]) / dd_, -1)
        l0 = 1 - l1 - l2; ins = ok & (l0 >= -1e-9) & (l1 >= -1e-9) & (l2 >= -1e-9)
        fu = not ins.any()   # fuera de la pieza en el molde: el triangulo mas cercano, baricentricas recortadas a [0, 1]
        j = int(np.argmax(np.minimum(np.minimum(l0, l1), l2))) if fu else int(np.where(ins)[0][0]); f = Fb[j]
        L_ = np.clip([l0[j], l1[j], l2[j]], 0, None); L_ = L_ / max(L_.sum(), 1e-12)
        return sum(L_[i] * V0[f[i]] for i in range(3)), -_u(sum(L_[i] * VN[f[i]] for i in range(3))), fu
    idx = {}; vout, uvout, sew, parl, taken, hue, prof, nfu, rlen = [], [], [], [], set(), [], [], 0, []
    for a in A:
        b = par[a]; pb = pn(b); ga, gb = G[pb]
        nbs = [x for x in nb[a] if pn(par[x]) == pb] or nb[a]
        if not nbs: continue
        Tc = _u(UV[nbs[0]] - UV[a]); Tb = _u(UV[par[nbs[0]]] - UV[b]) if pn(par[nbs[0]]) == pb else None
        Nout = -inward(a, Fc, np.array([-Tc[1], Tc[0]]))
        Fb = F[(F >= ga).all(1) & (F < gb).all(1)]
        Tb_ = Tb if Tb is not None else Tc
        Nin = inward(b, Fb, np.array([-Tb_[1], Tb_[0]]))
        q = UV[b] + w * Nin; ids = np.arange(ga, gb); dd = np.linalg.norm(UV[ga:gb] - q, axis=1)
        d = None
        for j in np.argsort(dd)[:6]:
            c = int(ids[j]); r = UV[c] - UV[b]
            if c in taken or c in Bset or dd[j] > 0.6 * w or np.dot(r, Nin) < 0.5 * w: continue
            d = c; break
        if d is None: r = w * Nin
        else: r = UV[d] - UV[b]; taken.add(d)
        t = float(np.dot(r, Tb)) if Tb is not None else 0.0; n = float(np.dot(r, Nin))
        uvm = UV[a] + t * Tc + n * Nout; rlen.append(np.linalg.norm(uvm - UV[a]))
        for j in range(1, rows + 1):
            s_ = j / rows; P, Ni, fu = sup(UV[b] + s_ * r, Fb); nfu += int(fu)
            if j == rows and d is not None: P = V0[d].copy(); Ni = -VN[d]
            h = _ray(P, Ni, TI) * 1000.0; pr = 0.5 * h if h <= hmax else off
            idx[(a, j)] = len(vout); vout.append(P + pr / 1000.0 * Ni); uvout.append(UV[a] + s_ * (uvm - UV[a])); parl.append(a); hue.append(h); prof.append(pr)
        if d is not None: sew.append((idx[(a, rows)], d))
    fac = []
    for x, y in bnd:
        if (x, 1) in idx and (y, 1) in idx:
            for j in range(1, rows + 1):
                X0 = x if j == 1 else nv0 + idx[(x, j - 1)]; Y0 = y if j == 1 else nv0 + idx[(y, j - 1)]
                fac += [[Y0, X0, nv0 + idx[(x, j)]], [Y0, nv0 + idx[(x, j)], nv0 + idx[(y, j)]]]
    hv = np.array(hue); pv = np.array(prof); cv = hv <= hmax
    msg = (f"PTH seam '{seam}' w {w} filas {rows} hmax {hmax} | margen {len(vout)} v ({len(vout) // rows} x {rows}), {len(fac)} caras, pespunte {len(sew)} | "
           f"ancho reposo p50 {np.median(rlen):.1f} min {min(rlen):.1f} max {max(rlen):.1f} mm | hueco a la capa de adentro p50 {np.median(hv[cv]) if cv.any() else -1:.2f} "
           f"min {hv[cv].min() if cv.any() else -1:.2f} max {hv[cv].max() if cv.any() else -1:.2f} mm ({int(cv.sum())}/{len(hv)} con capa a <= {hmax:.0f}) | "
           f"prof p50 {np.median(pv):.2f} max {pv.max():.2f} mm | filas fuera de la pieza {nfu}")
    return dict(v=[list(map(float, p)) for p in vout], uv=[list(map(float, u)) for u in uvout], f=fac,
                sew=[(nv0 + m, d) for m, d in sew], par=parl, msg=msg, hueco=hue, prof=prof, rows=rows)
