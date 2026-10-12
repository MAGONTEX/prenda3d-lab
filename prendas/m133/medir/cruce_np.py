# e2y: numpy port of autocruce_e2q.py (triangle pairs of the shell pieces that cut each other, faces sharing a vertex excluded), per pair of pieces.
# Same piece list as autocruce_e2q (SH). Used inside construction scripts; the gate still runs autocruce_e2q.py in Blender.
#   python _qc_e2y/cruce_np.py <malla.json> [pos=v|final.json|X.npy] [pares=fsLxfsL,...]
import json, sys, collections, numpy as np
from scipy.spatial import cKDTree
E2 = r"./"
SH = ["back", "fcR", "fcL", "fsR", "fsL", "slR", "slL", "hsR", "hsL", "hc", "htR", "htL", "tp", "hb", "zp", "faR", "faL", "bvR", "bvL", "elR", "elL"]
def prep(D):
    F = np.array(D["f"]); NV = len(D["v"]); g = np.full(NV, "", object)
    for n in SH:
        if n in D["groups"]: a, b = D["groups"][n]; g[a:b] = n
    m = (g[F[:, 0]] != "") & (g[F[:, 0]] == g[F[:, 1]]) & (g[F[:, 1]] == g[F[:, 2]]); FF = F[m]; return FF, g[FF[:, 0]]
def seg_tri(p0, p1, a, b, c, eps=1e-12):
    d = p1 - p0; e1 = b - a; e2 = c - a; h = np.cross(d, e2); det = (e1 * h).sum(1); ok = np.abs(det) > eps; inv = 1.0 / np.where(ok, det, 1.0)
    s = p0 - a; u = (s * h).sum(1) * inv; q = np.cross(s, e1); v = (d * q).sum(1) * inv; t = (e2 * q).sum(1) * inv
    return ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t >= 0) & (t <= 1)
def cruces(X_mm, FF, FG, sel=None):
    """X in mm. sel: optional bool mask of faces to consider (both faces of a pair must be in sel). Returns Counter of 'AxB' and z of each pair."""
    C = X_mm[FF].mean(1); idx = np.arange(len(FF)) if sel is None else np.where(sel)[0]
    kd = cKDTree(C[idx]); pr = kd.query_pairs(20.0, output_type="ndarray"); a, b = idx[pr[:, 0]], idx[pr[:, 1]]
    share = np.zeros(len(a), bool)
    for i in range(3):
        for j in range(3): share |= FF[a, i] == FF[b, j]
    a, b = a[~share], b[~share]; hit = np.zeros(len(a), bool); TA = X_mm[FF[a]]; TB = X_mm[FF[b]]
    for (i, j) in ((0, 1), (1, 2), (2, 0)):
        hit |= seg_tri(TA[:, i], TA[:, j], TB[:, 0], TB[:, 1], TB[:, 2]); hit |= seg_tri(TB[:, i], TB[:, j], TA[:, 0], TA[:, 1], TA[:, 2])
    a, b = a[hit], b[hit]; ga, gb = FG[a], FG[b]; keys = np.where(ga <= gb, ga + "x" + gb, gb + "x" + ga)
    return collections.Counter(keys.tolist()), keys, C[a, 2]
if __name__ == "__main__":
    D = json.load(open(E2 + sys.argv[1])); A = dict(x.split("=", 1) for x in sys.argv[2:] if "=" in x); P = A.get("pos", "v")
    X = (np.array(D["v"], float) if P == "v" else (np.load(E2 + P) if P.endswith(".npy") else np.array(json.load(open(E2 + P)), float))) * 1000
    FF, FG = prep(D); c, k, z = cruces(X, FF, FG); print("total", sum(c.values()), dict(c.most_common(60)))
