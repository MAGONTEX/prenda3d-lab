"""RJ (2026-10-10, CP84) palanca A: RELLENO EN LENTE. Espesor de reposo cascara-forro por vertice = h x perfil(d), con d = distancia en el molde (uv)
al pespunte o costura mas cercana de la pieza (pares de costura cascara<->forro 'pespunte' + 'borde forro', y el borde topologico de la pieza), medida
contra los SEGMENTOS de esas lineas (no contra sus vertices: la malla es de 10 mm). Perfil 'almohada' (foto q10: canal casi plano en el medio, caida
suave en 3-4 cm junto al pespunte): t = h (1 - (1 - min(d/r, 1))^2), piso tmin (un resorte interno de largo 0 = NaN).
Lo usa sim_e2s.py (relleno_r > 0) y, sin Blender, `python _qc_RJ/lente.py <malla.json> h=18 r=45 [tmin=1]` imprime espesor medio por bolsillo y el
estiramiento de las aristas de reposo del forro (no isometrico: el forro queda flojo en la franja del taper; medido, no supuesto)."""
import collections
import numpy as np


def lineas_cosidas(D, F, pieza, forro):
    """Vertices de la cascara `pieza` cosidos a su forro (pespuntes + borde forro) + borde topologico; devuelve (indices, segmentos (k,2) en indices)."""
    G = D["groups"]; a, b = G[pieza]; a2, b2 = G[forro]
    SEW = np.array(D["sew"], int)
    i0, i1 = SEW[:, 0], SEW[:, 1]
    k = ((i0 >= a) & (i0 < b) & (i1 >= a2) & (i1 < b2)) | ((i1 >= a) & (i1 < b) & (i0 >= a2) & (i0 < b2))
    cos = set(np.where((i0 >= a) & (i0 < b), i0, i1)[k].tolist())
    fm = F[(F >= a).all(1) & (F < b).all(1)]
    E = np.sort(np.vstack([fm[:, [0, 1]], fm[:, [1, 2]], fm[:, [2, 0]]]), axis=1)
    Eu, cnt = np.unique(E, axis=0, return_counts=True)
    borde = set(Eu[cnt == 1].ravel().tolist())
    S = cos | borde
    m = np.zeros(len(D["v"]), bool); m[list(S)] = True
    seg = Eu[m[Eu[:, 0]] & m[Eu[:, 1]]]
    return np.array(sorted(S), int), seg


def dist_segmentos(P, A, B, chunk=400):
    """Distancia minima de cada punto de P (n,2) a los segmentos A->B (k,2)."""
    out = np.empty(len(P))
    AB = B - A; L2 = np.maximum((AB * AB).sum(1), 1e-9)
    for s in range(0, len(P), chunk):
        Q = P[s:s + chunk]
        t = np.clip(((Q[:, None, :] - A[None]) * AB[None]).sum(2) / L2[None], 0.0, 1.0)
        C = A[None] + t[:, :, None] * AB[None]
        out[s:s + chunk] = np.sqrt(((Q[:, None, :] - C) ** 2).sum(2)).min(1)
    return out


def perfil(d, h, r, tmin):
    x = np.clip(d / max(r, 1e-6), 0.0, 1.0)
    return np.maximum(tmin, h * (1.0 - (1.0 - x) ** 2))


def espesores(D, F, h, r, tmin=1.0):
    """{indice del vertice del FORRO: espesor de reposo (mm)} para todos los canales de D['lining'] (forro con la misma uv y orden que su cascara)."""
    UV = np.array(D["uv"], float); G = D["groups"]; T = {}; DIST = {}
    for c, fz in D["lining"].items():
        a, b = G[c]; a2, b2 = G[fz]; assert b - a == b2 - a2, (c, fz)
        S, seg = lineas_cosidas(D, F, c, fz)
        d = dist_segmentos(UV[a:b], UV[seg[:, 0]], UV[seg[:, 1]])
        t = perfil(d, h, r, tmin)
        for k in range(b - a):
            T[a2 + k] = float(t[k]); DIST[a2 + k] = float(d[k])
    return T, DIST


def informe(D, F, T, DIST, h, r):
    UV = np.array(D["uv"], float); G = D["groups"]
    P = np.array([p if p is not None else "" for p in D["pocket"]])
    lines = []
    for c, fz in D["lining"].items():
        a, b = G[c]; a2, b2 = G[fz]
        t = np.array([T[a2 + k] for k in range(b - a)]); d = np.array([DIST[a2 + k] for k in range(b - a)])
        for pk in sorted(set(P[a:b].tolist())):
            if not pk: continue
            s = P[a:b] == pk
            lines.append("  %-6s n %4d | d p50 %5.1f max %5.1f | t media %5.1f p50 %5.1f | >= 0.9h %3.0f %%" % (pk, s.sum(), np.median(d[s]), d[s].max(), t[s].mean(), np.median(t[s]), 100 * (t[s] >= 0.9 * h).mean()))
        # estiramiento de las aristas de reposo del forro (uv con z = -t) contra el molde plano
        fm = F[(F >= a2).all(1) & (F < b2).all(1)]
        E = np.unique(np.sort(np.vstack([fm[:, [0, 1]], fm[:, [1, 2]], fm[:, [2, 0]]]), axis=1), axis=0)
        z = np.array([T[i] for i in range(a2, b2)]); l0 = np.linalg.norm(UV[E[:, 0]] - UV[E[:, 1]], axis=1)
        dz = z[E[:, 0] - a2] - z[E[:, 1] - a2]; l1 = np.sqrt(l0 ** 2 + dz ** 2); ok = l0 > 0.5; q = l1[ok] / l0[ok]
        lines.append("  %s: t media %5.1f (todo el forro) | aristas reposo/molde p50 %.3f p95 %.3f max %.3f | > 1.03: %.1f %% | > 1.10: %.1f %%" % (fz, z.mean(), np.median(q), np.percentile(q, 95), q.max(), 100 * (q > 1.03).mean(), 100 * (q > 1.10).mean()))
    return "\n".join(lines)


if __name__ == "__main__":
    import json, os, sys
    sys.stdout.reconfigure(encoding="utf-8")
    E2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    a_ = [q for q in sys.argv[1:] if "=" not in q]; KW = dict(q.split("=", 1) for q in sys.argv[1:] if "=" in q)
    h = float(KW.get("h", 18)); r = float(KW.get("r", 45)); tmin = float(KW.get("tmin", 1.0))
    D = json.load(open(os.path.join(E2, a_[0]), encoding="utf-8")); F = np.array(D["f"], int)
    T, DIST = espesores(D, F, h, r, tmin)
    tt = np.array(list(T.values()))
    print("lente h %.1f r %.1f tmin %.1f: %d vertices de forro | t media %.2f p50 %.1f | pendiente max 2h/r = %.2f" % (h, r, tmin, len(T), tt.mean(), np.median(tt), 2 * h / r))
    print(informe(D, F, T, DIST, h, r))
