# e2s (2026-09-29, tecnico 3D): CUELLO SANDWICH = la vista del cuello (htR/htL) atada al hs en TODA el area del cuello, a distancia fija
# (espesor de la plancha, 5-6 mm medido en las fotos p01), con los RESORTES INTERNOS del Cloth de Blender (cloth.cc: rayo desde cada vertice
# por -normal, primer impacto a <= max_length, con normal_check solo pares de normales opuestas; el objetivo es tri[0] del triangulo tocado).
# El largo de reposo sale de xrest = molde plano (Dynamic Mesh): el ht se superpone en el molde plano al hs (traslacion T del molde, medida en
# las costuras ht-hs, residuo < 0,2 mm) a z = -d, asi cada resorte ht-hs tiene de reposo sqrt(dplano^2 + d^2). Una traslacion rigida del ht
# en el molde plano no cambia su forma (estructurales, flexion) ni las costuras (reposo 0): solo los resortes internos.
# Rigidez por vertice (vertex_group_intern): solo el ht pesa (hs y el resto 0) -> resorte ht-hs = 0,5 x w_ht x sand_k; los resortes internos
# entre otras capas (cascara-forro, etc.) quedan con rigidez 0 (y sin amortiguacion: cloth_calc_spring_force, rama INTERNAL, k == 0).
# Un vertice del ht con algun resorte a otra pieza (no hs) queda con peso 0 (su reposo en el molde plano no tiene sentido).
# Modulo sin bpy (numpy + mathutils opcional): lo usan sim_e2s.py (dentro de Blender) y pred_sand_e2s.py.
import numpy as np

FLT_EPS = 1.1920929e-07


def piece_of(D):
    NV = len(D["v"]); g = np.full(NV, "", object)
    for n, (a, b) in D["groups"].items(): g[a:b] = n
    return g


def transl(D):
    """T por lado (mm de molde) de hs -> ht, desde las costuras capucha-ht base/lado + vista-escote; y el residuo."""
    UV = np.array(D["uv"], float); S = np.array(D["sew"]); N = np.array(D["sew_seam"]); out = {}
    for s in "RL":
        c, d = D["groups"]["ht" + s]; P = []
        for nm in (f"capucha-ht base {s}", f"capucha-ht lado {s}", f"vista-escote {s}"):
            for i, j in S[N == nm]:
                if c <= i < d: i, j = j, i
                P.append((i, j))
        P = np.array(P); dd = UV[P[:, 1]] - UV[P[:, 0]]; T = dd.mean(0)
        out[s] = (T, float(np.median(np.linalg.norm(dd - T, axis=1))), float(np.linalg.norm(dd - T, axis=1).max()), len(P))
    return out


def seamed_ht(D):
    """vertices del ht que estan en alguna costura (con hs o con el cuerpo)."""
    S = np.array(D["sew"]); pc = piece_of(D); out = set()
    for i, j in S:
        for a in (i, j):
            if pc[a].startswith("ht"): out.add(int(a))
    return out


def taper_w(D, tap_mm):
    """peso del ht por distancia en el molde al vertice cosido mas cercano del mismo lado: 0 en la costura -> 1 a tap_mm."""
    UV = np.array(D["uv"], float); sm = seamed_ht(D); W = {}
    for s in "RL":
        c, d = D["groups"]["ht" + s]; I = np.arange(c, d); B = np.array(sorted(i for i in sm if c <= i < d))
        dm = np.min(np.linalg.norm(UV[I][:, None, :] - UV[B][None, :, :], axis=2), axis=1)
        for i, v in zip(I, dm): W[int(i)] = float(np.clip(v / tap_mm, 0.0, 1.0)) if tap_mm > 0 else 1.0
    return W


def bary_map(D, T):
    """para cada ht: triangulo del hs (mismo lado) que contiene uv - T y baricentricas; None si cae afuera."""
    UV = np.array(D["uv"], float); F = np.array(D["f"]); out = {}
    for s in "RL":
        a, b = D["groups"]["hs" + s]; fm = np.all((F >= a) & (F < b), 1); Fh = F[fm]
        A = UV[Fh[:, 0]]; B = UV[Fh[:, 1]]; C = UV[Fh[:, 2]]; det = (B[:, 0] - A[:, 0]) * (C[:, 1] - A[:, 1]) - (C[:, 0] - A[:, 0]) * (B[:, 1] - A[:, 1])
        c, d = D["groups"]["ht" + s]
        for i in range(c, d):
            p = UV[i] - T[s][0]
            l1 = ((p[0] - A[:, 0]) * (C[:, 1] - A[:, 1]) - (C[:, 0] - A[:, 0]) * (p[1] - A[:, 1])) / det
            l2 = ((B[:, 0] - A[:, 0]) * (p[1] - A[:, 1]) - (p[0] - A[:, 0]) * (B[:, 1] - A[:, 1])) / det
            l0 = 1 - l1 - l2; ok = np.where((l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6))[0]
            if len(ok): k = ok[0]; out[i] = (Fh[k].tolist(), [float(l0[k]), float(l1[k]), float(l2[k])])
    return out


def vnormals_np(V, F):
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]); VN = np.zeros_like(V)
    for j in range(3): np.add.at(VN, F[:, j], fn)
    return VN / np.maximum(np.linalg.norm(VN, axis=1, keepdims=True), 1e-12)


def sand_stats(X, F, BM, W=None, wmin=0.5):
    """espesor (distancia normal, mm; + = el ht por dentro) y deslizamiento tangencial (mm) del ht contra su punto del hs."""
    VN = vnormals_np(X, F); dn = []; dt = []
    for i, (tri, w) in BM.items():
        if W is not None and W.get(i, 0.0) < wmin: continue
        tri = np.array(tri); w = np.array(w); P = (X[tri] * w[:, None]).sum(0); n = (VN[tri] * w[:, None]).sum(0); n /= np.linalg.norm(n) + 1e-12
        v = X[i] - P; a = float(v @ n); dn.append(-a * 1000); dt.append(float(np.linalg.norm(v - a * n)) * 1000)
    dn = np.array(dn); dt = np.array(dt)
    return dict(n=len(dn), esp_med=float(np.median(dn)), esp_p5=float(np.percentile(dn, 5)), esp_p95=float(np.percentile(dn, 95)),
                desl_med=float(np.median(dt)), desl_p95=float(np.percentile(dt, 95)), desl_max=float(dt.max()))


def flat_levels(D, F, d, lvl):
    """e2zs: z (mm) en el molde plano de hs y ht por lado para que la RE-DETECCION de Blender (cada reconstruccion del Cloth) encuentre el sandwich.
    En el molde R y L estan SUPERPUESTAS (mismo uv, normales opuestas): el ht va DETRAS de su hs (lado opuesto a la normal del hs en el molde)
    y el sandwich R sube a su propio nivel (lvl mm > sand_len) para que ningun rayo toque la copia del otro lado. Traslaciones rigidas por pieza."""
    UV = np.array(D["uv"], float); out = {}
    for s in "RL":
        a, b = D["groups"]["hs" + s]; Fh = F[np.all((F >= a) & (F < b), 1)]; A = UV[Fh]
        sg = float(np.sign(((A[:, 1, 0] - A[:, 0, 0]) * (A[:, 2, 1] - A[:, 0, 1]) - (A[:, 2, 0] - A[:, 0, 0]) * (A[:, 1, 1] - A[:, 0, 1])).sum()))
        zh = float(lvl) if s == "R" else 0.0; out["hs" + s] = zh; out["ht" + s] = zh - sg * d; out["n" + s] = sg
    return out


def flat_rest(D, F, T, d, lvl):
    """e2zs: posiciones (m) del molde plano con el sandwich en sus niveles (flat_levels) y el ht superpuesto a su hs (T)."""
    UV = np.array(D["uv"], float); M = np.c_[UV, np.zeros(len(UV))]; Z = flat_levels(D, F, d, lvl)
    for s in "RL":
        a, b = D["groups"]["ht" + s]; M[a:b, :2] -= T[s][0]; M[a:b, 2] = Z["ht" + s]; a, b = D["groups"]["hs" + s]; M[a:b, 2] = Z["hs" + s]
    return M / 1000.0, Z


def predict(V0, F, VN, maxlen, check_normal=True, bvh=None):
    """replica find_internal_spring_target_vertex (cloth.cc) con max_diversion 0: pares unicos (i, j) en orden de creacion."""
    import mathutils
    from mathutils.bvhtree import BVHTree
    if bvh is None: bvh = BVHTree.FromPolygons([tuple(p) for p in V0], [tuple(f) for f in F], all_triangles=True, epsilon=0.0)
    pairs = []; seen = set()
    for i in range(len(V0)):
        no = -VN[i]; nl = np.linalg.norm(no)
        if nl < 1e-12: continue
        no = no / nl; co = V0[i] + no * FLT_EPS
        loc, nrm, idx, dist = bvh.ray_cast(mathutils.Vector(co), mathutils.Vector(no), maxlen if maxlen > 0 else 1e30)
        if loc is None or dist > maxlen: continue
        if check_normal:
            nn = np.array(nrm); nn = nn / (np.linalg.norm(nn) + 1e-30)
            if nn @ no < 0.0: continue
        tri = F[idx]
        if i in tri: continue
        j = int(tri[0]); key = (min(i, j), max(i, j))
        if key in seen: continue
        seen.add(key); pairs.append((i, j))
    return pairs


def predict_hits(V0, F, VN, maxlen, check_normal=True):
    """como predict, pero devuelve cada rayo aceptado: (vertice, indice del triangulo tocado, punto de impacto) sin elegir tri[0]."""
    import mathutils
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromPolygons([tuple(p) for p in V0], [tuple(f) for f in F], all_triangles=True, epsilon=0.0); out = []
    for i in range(len(V0)):
        no = -VN[i]; nl = np.linalg.norm(no)
        if nl < 1e-12: continue
        no = no / nl; co = V0[i] + no * FLT_EPS
        loc, nrm, idx, dist = bvh.ray_cast(mathutils.Vector(co), mathutils.Vector(no), maxlen if maxlen > 0 else 1e30)
        if loc is None or dist > maxlen: continue
        if check_normal:
            nn = np.array(nrm); nn = nn / (np.linalg.norm(nn) + 1e-30)
            if nn @ no < 0.0: continue
        if i in F[idx]: continue
        out.append((i, int(idx), np.array(loc)))
    return out


def rotate_for_ties(D, F, hits, V=None):
    """rota (ciclico: la normal no cambia) cada triangulo tocado por un rayo ht->hs o hs->ht para que su tri[0] sea el vertice mas cercano al
    impacto medio: Blender ata el rayo a tri[0] (cloth.cc), asi el resorte queda casi normal y cada vertice del ht recibe el suyo."""
    pc = piece_of(D); acc = {}
    for i, t, loc in hits:
        a = pc[i]; b = pc[F[t][0]]
        if (a.startswith("ht") and b.startswith("hs") and a[-1] == b[-1]) or (a.startswith("hs") and b.startswith("ht") and a[-1] == b[-1]):
            acc.setdefault(t, []).append(loc)
    V = np.array(D["v"], float) if V is None else V; F2 = F.copy(); nrot = 0   # e2zs: V = posicion donde se midieron los impactos (defecto: la malla 3D)
    for t, locs in acc.items():
        m = np.mean(locs, axis=0); k = int(np.argmin(np.linalg.norm(V[F[t]] - m, axis=1)))
        if k: F2[t] = np.roll(F[t], -k); nrot += 1
    return F2, len(acc), nrot
