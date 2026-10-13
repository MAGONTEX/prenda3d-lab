# [ESC·f535] HEM2 (2026-10-13): hem facing band ("vivo del ruedo") of the M133, pure numpy (no bpy).
# Real garment (inside photos p08/p09 + owner's tape measure): the hem carries a 35-40 mm facing of SHELL fabric on the inside,
# with a topstitch visible from outside ~30 mm above the edge. Not in the DXF as a piece (no facing block; shell and inner wall
# blocks have the same outline), so it is modeled as a BAND of the existing pieces that reach the hem (back, fcR, fcL; the side
# fronts end at the lower curve seam): topstitch line = shell-inner sewing pairs at mold height W above the hem; inner ply of the
# band = shell fabric (takes its shell twin's stiffness weights, done in the sim). Used by sim_e2s_R24.py (key ruedo_vivo=W mm).
import numpy as np

PIEZAS = ("back", "fcR", "fcL", "fsR", "fsL")


def banda(D, F, W, piezas=PIEZAS, tol_hem=12.0, bin_mm=3.0):
    """W in mm of mold (height above the hem along uv-x, the piece's vertical: quilting lines are at constant uv-x).
    Returns sew pairs (shell, inner twin) of the topstitch line, band ids (h < W, below the line), their inner twins,
    shell area (m2) of the faces that touch the band per bottom pocket name, and a log."""
    G = D["groups"]; INST = D["inst"]; UV = np.asarray(D["uv"], float); V0 = np.asarray(D["v"], float)
    S = np.asarray(D["sew"]); N = np.asarray(D["sew_seam"]); F = np.asarray(F)
    BD = set(int(i) for i in D["border"]); PIN = set(int(i) for i in D["pinch"])
    otra = set(S[N != "borde forro"].ravel().tolist())          # sewn to another piece = not the free hem edge
    out = dict(sew=[], line=[], band=[], band_f=[], band_all=[], band_all_f=[], area_m2={}, h={}, log=[])
    for p in piezas:
        a, b = G[p]; o = INST[p]["off"]; of = INST[p + "_f"]["off"]
        libre = np.array([i for i in range(a, b) if i in BD and i not in otra], int)
        if len(libre) == 0 or V0[libre, 2].min() > V0[a:b, 2].min() + 0.005:
            out["log"].append(f"{p}: no free edge at the bottom (does not reach the hem) -> no band"); continue
        cand = libre[UV[libre, 0] <= UV[libre, 0].min() + tol_hem]
        keys = np.floor(UV[cand, 1] / bin_mm).astype(int); hem = []
        for k in np.unique(keys):                                  # per uv-y bin the lowest free vertex: drops the CF stub under the zipper
            c = cand[keys == k]; hem.append(int(c[np.argmin(UV[c, 0])]))
        hem = np.array(sorted(hem, key=lambda i: UV[i, 1]))
        ids = np.arange(a, b)
        h = UV[ids, 0] - np.interp(UV[ids, 1], UV[hem, 1], UV[hem, 0])
        out["h"][p] = h
        fa = F[(F >= a).all(1) & (F < b).all(1)]
        E = np.unique(np.sort(np.r_[fa[:, [0, 1]], fa[:, [1, 2]], fa[:, [2, 0]]], 1), axis=0)
        hu = h[E[:, 0] - a] - W; hv = h[E[:, 1] - a] - W
        cr = E[(hu * hv <= 0) & ~((hu == 0) & (hv == 0))]
        pick = np.where(np.abs(h[cr[:, 0] - a] - W) <= np.abs(h[cr[:, 1] - a] - W), cr[:, 0], cr[:, 1])
        line = sorted(set(int(i) for i in pick))
        band = [int(i) for i in ids[h < W] if int(i) not in set(line)]
        sew = [[i, of + (i - o)] for i in line if i not in BD and i not in PIN]   # border/pinch twins are already sewn
        lb = set(band); fb = fa[np.isin(fa, list(lb)).any(1)]
        t = UV[fb]; ar = 0.5 * np.abs((t[:, 1, 0] - t[:, 0, 0]) * (t[:, 2, 1] - t[:, 0, 1]) - (t[:, 2, 0] - t[:, 0, 0]) * (t[:, 1, 1] - t[:, 0, 1]))
        ch = (np.array(D["lx"][INST[p]["key"]])[None, :] < t[:, :, 0].mean(1)[:, None]).sum(1)
        for c in np.unique(ch): out["area_m2"][f"{p}{c}"] = out["area_m2"].get(f"{p}{c}", 0.0) + float(ar[ch == c].sum()) / 1e6
        out["sew"] += sew; out["line"] += line; out["band"] += band; out["band_f"] += [of + (i - o) for i in band]
        out["band_all"] += band + line; out["band_all_f"] += [of + (i - o) for i in band + line]
        hl = h[np.array(line) - a]
        out["log"].append(f"{p}: hem {len(hem)} v (uv-x {UV[hem, 0].min():.1f}..{UV[hem, 0].max():.1f}) | line {len(line)} v h {hl.min():.1f}/{np.median(hl):.1f}/{hl.max():.1f}"
                          f" | sew {len(sew)} | band {len(band)} v | band faces {len(fb)}, shell area {ar.sum() / 100:.1f} cm2 in pockets {sorted(set(f'{p}{c}' for c in ch))}")
    return out
