"""[ESC·f535] Triangulador 2D del laboratorio: copia LITERAL de las funciones de geometria y de `_triangular` del mallador de la prenda
(borde partido + reticula equilatera + Delaunay + aristas forzadas). Autocontenido: sin archivos de molderia, sin `bpy`, solo numpy y scipy."""
import collections
import math

import numpy as np


def _dc(a, b, per):
    d = abs(a - b) % per
    return min(d, per - d)


def _arco(s0, s1, sentido, per):
    d = ((s1 - s0) * (1 if sentido >= 0 else -1)) % per
    return 0.0 if per - d < 1e-6 else d


def _dentro(Q, poly):
    x, y = Q[:, 0][:, None], Q[:, 1][:, None]
    x1, y1 = poly[:, 0][None], poly[:, 1][None]
    x2, y2 = np.roll(poly[:, 0], -1)[None], np.roll(poly[:, 1], -1)[None]
    with np.errstate(divide="ignore", invalid="ignore"):
        c = ((y1 > y) != (y2 > y)) & (x < (x2 - x1) * (y - y1) / (y2 - y1) + x1)
    return c.sum(1) % 2 == 1


def _dist_segs(Q, A, B):
    """Distancia mínima de cada punto de Q a los segmentos A[i]-B[i]."""
    out = np.full(len(Q), np.inf)
    if len(A) == 0:
        return out
    ab = (B - A)[None]
    l2 = np.maximum((ab ** 2).sum(2), 1e-18)
    for i in range(0, len(Q), 2000):
        q = Q[i:i + 2000][:, None, :]
        t = np.clip(((q - A[None]) * ab).sum(2) / l2, 0.0, 1.0)
        out[i:i + 2000] = np.linalg.norm(q - (A[None] + t[..., None] * ab), axis=2).min(1)
    return out


def _or(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _cruzan(p, q, a, b) -> bool:
    return _or(a, b, p) * _or(a, b, q) < 0 and _or(p, q, a) * _or(p, q, b) < 0


def _inter(p1, p2, q1, q2, eps=0.5):
    """Punto de corte de dos segmentos (con `eps` mm de gracia en las puntas: uniones en T), o None."""
    r, s = p2 - p1, q2 - q1
    den = r[0] * s[1] - r[1] * s[0]
    lr, ls = np.linalg.norm(r), np.linalg.norm(s)
    if abs(den) < 1e-9 * max(lr * ls, 1e-9) or lr < 1e-9 or ls < 1e-9:
        return None
    t = ((q1[0] - p1[0]) * s[1] - (q1[1] - p1[1]) * s[0]) / den
    u = ((q1[0] - p1[0]) * r[1] - (q1[1] - p1[1]) * r[0]) / den
    if -eps / lr <= t <= 1 + eps / lr and -eps / ls <= u <= 1 + eps / ls:
        return p1 + np.clip(t, 0, 1) * r
    return None


def calidad(UV, F) -> dict:
    """Ángulo mínimo por triángulo (grados), razón de aspecto (lado mayor / altura menor × √3/2: 1 = equilátero) y aristas."""
    A, B, C = UV[F[:, 0]], UV[F[:, 1]], UV[F[:, 2]]
    a, b, c = np.linalg.norm(B - C, axis=1), np.linalg.norm(C - A, axis=1), np.linalg.norm(A - B, axis=1)
    ar = 0.5 * np.abs((B[:, 0] - A[:, 0]) * (C[:, 1] - A[:, 1]) - (B[:, 1] - A[:, 1]) * (C[:, 0] - A[:, 0]))
    lmax, lmin = np.maximum(a, np.maximum(b, c)), np.minimum(a, np.minimum(b, c))
    amin = np.degrees(np.arcsin(np.clip(2 * ar / np.maximum(lmax * np.sort(np.c_[a, b, c], axis=1)[:, 1], 1e-12), 0, 1)))
    asp = lmax / np.maximum(2 * ar / lmax, 1e-9) * (math.sqrt(3) / 2)
    return dict(ang_min=float(amin.min()), ang_p1=float(np.percentile(amin, 1)), asp_max=float(asp.max()), asp_p99=float(np.percentile(asp, 99)),
                l_min=float(lmin.min()), l_p50=float(np.median(np.r_[a, b, c])), l_max=float(lmax.max()), area=float(ar.sum()),
                astillas=int(((amin < 15.0) | (asp > 4.0)).sum()), n_tri=int(len(F)))


# ---------------------------------------------------------------------------------------------------------------- Delaunay con aristas forzadas
def _forzar(P, T, aristas) -> tuple:
    """Fuerza las aristas por giros (Sloan 1993). T: (n,3). -> (T nuevo, recuperadas). Lanza si una arista forzada cruza a otra."""
    T = [list(map(int, t)) for t in T]
    e2t = collections.defaultdict(set)
    fijas = {(min(a, b), max(a, b)) for a, b in aristas}

    def k(u, v):
        return (u, v) if u < v else (v, u)

    def pon(i, s=True):
        t = T[i]
        for j in range(3):
            (e2t[k(t[j], t[(j + 1) % 3])].add if s else e2t[k(t[j], t[(j + 1) % 3])].discard)(i)
    for i in range(len(T)):
        pon(i)
    rec = 0
    for a, b in sorted(fijas):
        if e2t.get((a, b)):
            continue
        rec += 1
        cola = collections.deque(e for e, ts in e2t.items() if len(ts) == 2 and a not in e and b not in e and _cruzan(P[e[0]], P[e[1]], P[a], P[b]))
        guard = 0
        while cola:
            guard += 1
            if guard > 20000:
                raise RuntimeError(f"no se pudo forzar la arista {a}-{b}")
            u, v = cola.popleft()
            ts = list(e2t.get((u, v), ()))
            if len(ts) != 2:
                continue
            if (u, v) in fijas:
                raise RuntimeError(f"la arista forzada {a}-{b} cruza a la forzada {u}-{v}")
            c = next(x for x in T[ts[0]] if x not in (u, v))
            d = next(x for x in T[ts[1]] if x not in (u, v))
            if not _cruzan(P[c], P[d], P[u], P[v]):          # cuadrilátero no convexo: se deja para después
                cola.append((u, v))
                continue
            pon(ts[0], False)
            pon(ts[1], False)
            T[ts[0]], T[ts[1]] = [c, d, u], [d, c, v]
            pon(ts[0])
            pon(ts[1])
            if k(c, d) != (a, b) and _cruzan(P[c], P[d], P[a], P[b]):
                cola.append(k(c, d))
        if not e2t.get((a, b)):
            raise RuntimeError(f"arista forzada {a}-{b} sin recuperar")
    T = np.array(T, int)
    A, B, C = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    neg = ((B[:, 0] - A[:, 0]) * (C[:, 1] - A[:, 1]) - (B[:, 1] - A[:, 1]) * (C[:, 0] - A[:, 0])) < 0
    T[neg] = T[neg][:, [0, 2, 1]]
    return T, rec


def _triangular(B, I, aristas_int, h, pasos):
    """B: borde (nb,2) en orden; I: interiores fijos; -> (puntos, triángulos CCW, aristas recuperadas)."""
    from scipy.spatial import Delaunay
    nb, ni = len(B), len(I)
    A_, B_ = B, np.roll(B, -1, axis=0)
    segA = np.vstack([A_] + ([np.array([I[a] for a, _ in aristas_int])] if aristas_int else []))
    segB = np.vstack([B_] + ([np.array([I[b] for _, b in aristas_int])] if aristas_int else []))
    lo, hi = B.min(0), B.max(0)
    dy = h * math.sqrt(3) / 2
    ys = np.arange(lo[1] + 0.31 * h, hi[1], dy)
    L = np.vstack([np.c_[np.arange(lo[0] + 0.17 * h + (0.5 * h if j % 2 else 0.0), hi[0], h), np.full(len(np.arange(lo[0] + 0.17 * h + (0.5 * h if j % 2 else 0.0), hi[0], h)), y)]
                   for j, y in enumerate(ys)]) if len(ys) else np.zeros((0, 2))
    if len(L):
        ok = _dentro(L, B) & (_dist_segs(L, segA, segB) >= 0.6 * h)
        if ni:
            ok &= np.linalg.norm(L[:, None, :] - I[None], axis=2).min(1) >= 0.6 * h
        L = L[ok]
    span = float(np.linalg.norm(hi - lo)) * 20 + 1000
    cen = (lo + hi) / 2
    SUP = cen + span * np.array([[-1, -1], [1, -1], [1, 1], [-1, 1.0]])
    forz = [(i, (i + 1) % nb) for i in range(nb)] + [(nb + a, nb + b) for a, b in aristas_int]
    for it in range(pasos + 1):
        P = np.vstack([B, I, L, SUP]) if ni else np.vstack([B, L, SUP])
        T = Delaunay(P).simplices
        if it == pasos:
            break
        T = T[(T < len(P) - 4).all(1)]
        T = T[_dentro(P[T].mean(1), B)]
        n0 = nb + ni
        acc, cnt = np.zeros((len(P), 2)), np.zeros(len(P))
        for i, j in ((0, 1), (1, 2), (2, 0)):
            np.add.at(acc, T[:, i], P[T[:, j]])
            np.add.at(cnt, T[:, i], 1)
            np.add.at(acc, T[:, j], P[T[:, i]])
            np.add.at(cnt, T[:, j], 1)
        Ln = L + 0.6 * (acc[n0:n0 + len(L)] / np.maximum(cnt[n0:n0 + len(L)], 1)[:, None] - L)
        mv = (cnt[n0:n0 + len(L)] > 0) & _dentro(Ln, B) & (_dist_segs(Ln, segA, segB) >= 0.5 * h)
        L = np.where(mv[:, None], Ln, L)
    T, rec = _forzar(P, T, forz)
    T = T[(T < len(P) - 4).all(1)]
    T = T[_dentro(P[T].mean(1), B)]
    P = P[:-4]
    A, Bq, C = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    T = T[np.abs((Bq[:, 0] - A[:, 0]) * (C[:, 1] - A[:, 1]) - (Bq[:, 1] - A[:, 1]) * (C[:, 0] - A[:, 0])) > 1e-7 * h * h]
    return P, T, rec


# ---------------------------------------------------------------------------------------------------------------- líneas interiores
def _dist_seg(q, a, b):
    ab = b - a
    t = float(np.clip(((q - a) @ ab) / max(float(ab @ ab), 1e-12), 0.0, 1.0))
    p = a + t * ab
    return float(np.linalg.norm(q - p)), p

