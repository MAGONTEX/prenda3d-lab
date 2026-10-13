# [ESC f535] QUAD (2026-10-13): join pairs of triangles into quads so that Blender's Cloth builds SHEAR springs.
# cloth.cc (cloth_build_springs) adds shear springs only on faces with more than 3 sides ("Triangle faces already have
# shear springs due to structural geometry"): on an all-triangle mesh shear_stiffness does nothing and in-plane shear is
# held by the structural springs. On a quad (q0, q1, q2, q3) Blender adds the two diagonals as shear springs (and, with
# angular bending, as bending hinges) and tessellates it as (q0, q1, q2) + (q0, q2, q3): the same two triangles.
# Pure numpy: used by sim_e2s_R24.py (key quads=1|2) and by the local check (no Blender).
#
# Rule (deterministic, independent of the cyclic order of each triangle row):
#   1. both triangles are eligible (same listed piece, original faces, not excluded);
#   2. each triangle picks its most horizontal edge in the mold (uv; ties -> smaller vertex pair) and the two pick the
#      same edge, with consistent orientation ((a, b) in one, (b, a) in the other);
#   3. the shared edge is not a sew pair and does not have both ends among sewn vertices (seam and quilting lines stay
#      chains of edges);
#   4. the quad (a, d, b, c) from (a, b, c) + (b, a, d) is convex in the mold, with inner angles in [ang_min, ang_max]
#      and the orientation (sign of area) of its two triangles;
#   5. in the 3D start shape V the two triangles fold less than acos(fold_min) and Blender's tessellation keeps the
#      a-b diagonal (is_quad_flip_v3_first_third_fast and its normal variant are false).
import numpy as np

HOOD = ("hsR", "hsL", "hc", "hb", "hcl", "hlR", "hlL")          # quads=1: hood shell + hood lining (forro_HP)
TELA = ("back", "fcR", "fcL", "fsR", "fsL", "slR", "slL", "hsR", "hsL", "hc", "htR", "htL", "hb",
        "back_f", "fcR_f", "fcL_f", "fsR_f", "fsL_f", "slR_f", "slL_f", "tp", "bvR", "bvL", "faR", "faL",
        "hcl", "hlR", "hlL")                                       # quads=2: every fabric piece (not zp, cord, elR, elL)


def face_piece(F, groups, names):
    """index into names of the piece that holds the 3 vertices of each face; -1 if none (mixed or not listed)."""
    F = np.asarray(F, np.int64); out = np.full(len(F), -1, int)
    for k, n in enumerate(names):
        if n not in groups:
            continue
        a, b = groups[n]; out[((F >= a) & (F < b)).all(1)] = k
    return out


def near_mask(V, src, radius, chunk=4096):
    """bool per vertex: within radius (same units as V) of any vertex in src."""
    V = np.asarray(V, float); S = V[np.asarray(sorted(src), int)]; out = np.zeros(len(V), bool)
    if len(S) == 0:
        return out
    lo, hi = S.min(0) - radius, S.max(0) + radius
    cand = np.nonzero(((V >= lo) & (V <= hi)).all(1))[0]
    r2 = radius * radius
    for i in range(0, len(cand), chunk):
        c = cand[i:i + chunk]; d2 = ((V[c][:, None, :] - S[None, :, :]) ** 2).sum(2).min(1); out[c[d2 <= r2]] = True
    return out


def _cross2(a, b):
    return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]


def join(F, UV, sew, piece, V=None, excl=None, ang_min=35.0, ang_max=145.0, fold_min=0.5):
    """F (nf, 3) triangles, UV (nv, 2) mold, sew pairs, piece (nf,) from face_piece, V (nv, 3) start shape or None,
    excl (nf,) bool faces that must stay triangles. Returns dict: faces (list, quads at the index of their first
    triangle, other rows untouched), pairs (np, 2) triangle indices, quads (np, 4), reasons (rejection counts)."""
    F = np.asarray(F, np.int64); UV = np.asarray(UV, float); nf = len(F); nv = len(UV)
    ok = np.asarray(piece) >= 0
    if excl is not None:
        ok &= ~np.asarray(excl, bool)
    S = np.asarray(sew, np.int64).reshape(-1, 2)
    sew_key = set((np.minimum(S[:, 0], S[:, 1]) * nv + np.maximum(S[:, 0], S[:, 1])).tolist())
    sewn = np.zeros(nv, bool); sewn[S.ravel()] = True
    E = np.stack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]], 1)                      # (nf, 3, 2) directed edges
    key = np.minimum(E[..., 0], E[..., 1]) * nv + np.maximum(E[..., 0], E[..., 1])   # (nf, 3) undirected edge id
    d = UV[E[..., 1]] - UV[E[..., 0]]
    h = np.abs(d[..., 1]) / (np.linalg.norm(d, axis=-1) + 1e-30)                     # sin(angle to the mold horizontal)
    row = np.repeat(np.arange(nf), 3)
    o = np.lexsort((key.ravel(), h.ravel(), row)).reshape(nf, 3)[:, 0] - np.arange(nf) * 3   # pick per face
    ck = key[np.arange(nf), o]                                                         # chosen edge id
    # faces per edge (all faces): an edge joins only if exactly 2 faces hold it
    uk, inv, cnt = np.unique(key.ravel(), return_inverse=True, return_counts=True)
    first = np.full(len(uk), -1, np.int64); second = np.full(len(uk), -1, np.int64)
    fidx = row
    for j in range(len(fidx)):   # fill the two holders of each edge (order of face index)
        e = inv[j]
        if first[e] < 0:
            first[e] = fidx[j]
        elif second[e] < 0:
            second[e] = fidx[j]
    rs = dict(no_elegible=0, borde_o_no_manifold=0, no_mutua=0, otra_pieza=0, orientacion=0, costura=0, dos_cosidos=0,
              no_convexo=0, angulo=0, area_signo=0, plegado_3d=0, blender_flip=0)
    pairs = []; quads = []
    eid = np.searchsorted(uk, ck)
    for t in range(nf):
        if not ok[t]:
            continue
        e = eid[t]
        if cnt[e] != 2:
            rs["borde_o_no_manifold"] += 1; continue
        u = second[e] if first[e] == t else first[e]
        if u < t:
            continue                       # handled (or rejected) from the smaller index
        if not ok[u]:
            rs["no_elegible"] += 1; continue
        if ck[u] != ck[t]:
            rs["no_mutua"] += 1; continue
        if piece[u] != piece[t]:
            rs["otra_pieza"] += 1; continue
        a, b = E[t, o[t]]; ua, ub = E[u, o[u]]
        if not (ua == b and ub == a):
            rs["orientacion"] += 1; continue
        c = int(F[t][(o[t] + 2) % 3]); dd = int(F[u][(o[u] + 2) % 3])
        if int(ck[t]) in sew_key:
            rs["costura"] += 1; continue
        if sewn[a] and sewn[b]:
            rs["dos_cosidos"] += 1; continue
        Q = np.array([a, dd, b, c], np.int64); P = UV[Q]
        e_in = P - np.roll(P, 1, 0); e_out = np.roll(P, -1, 0) - P
        cz = _cross2(e_in, e_out)
        area = 0.5 * _cross2(P, np.roll(P, -1, 0)).sum()
        a1 = _cross2(UV[b] - UV[a], UV[c] - UV[a]); a2 = _cross2(UV[a] - UV[b], UV[dd] - UV[b])
        if not (np.sign(a1) == np.sign(a2) == np.sign(area) != 0):
            rs["area_signo"] += 1; continue
        if not (np.all(np.sign(cz) == np.sign(area))):
            rs["no_convexo"] += 1; continue
        v1 = np.roll(P, 1, 0) - P; v2 = np.roll(P, -1, 0) - P
        cosang = (v1 * v2).sum(1) / (np.linalg.norm(v1, axis=1) * np.linalg.norm(v2, axis=1) + 1e-30)
        ang = np.degrees(np.arccos(np.clip(cosang, -1.0, 1.0)))
        if ang.min() < ang_min or ang.max() > ang_max:
            rs["angulo"] += 1; continue
        if V is not None:
            X = np.asarray(V[Q], float)
            n1 = np.cross(X[1] - X[0], X[2] - X[0]); n2 = np.cross(X[2] - X[0], X[3] - X[0])   # (a,d,b), (a,b,c)
            cf = float(n1 @ n2) / (np.linalg.norm(n1) * np.linalg.norm(n2) + 1e-30)
            if cf < fold_min:
                rs["plegado_3d"] += 1; continue
            # Blender: mesh_tessellate.cc flips to (q0,q1,q3)+(q1,q2,q3) if the 0-2 split is degenerate
            fast = float(np.cross(X[1] - X[0], X[2] - X[0]) @ np.cross(X[3] - X[0], X[2] - X[0])) > 0.0
            nrm = np.cross(X[2] - X[0], X[3] - X[1])                      # quad normal (diagonals)
            tg = np.cross(X[2] - X[0], nrm); d0 = X[0] @ tg
            withn = (X[3] @ tg >= d0) or (X[1] @ tg <= d0)
            if fast or withn:
                rs["blender_flip"] += 1; continue
        pairs.append((t, int(u))); quads.append(Q.tolist())
    pairs = np.array(pairs, np.int64).reshape(-1, 2); quads = np.array(quads, np.int64).reshape(-1, 4)
    rep = np.full(nf, -1, np.int64); rep[pairs[:, 0]] = np.arange(len(pairs)); drop = np.zeros(nf, bool); drop[pairs[:, 1]] = True
    faces = [quads[rep[t]].tolist() if rep[t] >= 0 else F[t].tolist() for t in range(nf) if not drop[t]]
    return dict(faces=faces, pairs=pairs, quads=quads, reasons=rs, eligible=ok, choice=o, h=h)


def summary(res, piece, names):
    """per piece: eligible triangles, quads, loose eligible triangles, % joined."""
    ok = res["eligible"]; joined = np.zeros(len(ok), bool); joined[res["pairs"].ravel()] = True; out = {}
    for k, n in enumerate(names):
        m = (np.asarray(piece) == k)
        if not m.any():
            continue
        ne = int((m & ok).sum()); nj = int((m & joined).sum())
        out[n] = dict(tri_total=int(m.sum()), elegibles=ne, quads=nj // 2, sueltos=ne - nj, pct=round(100.0 * nj / max(ne, 1), 1))
    return out
