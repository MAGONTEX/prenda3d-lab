"""[ESC·f535] lab/metricas.py - metricas del laboratorio por script (numpy, sin Blender) + banda de ruido por replica.

    python lab/metricas.py b1|b2|b3 <carpeta de salida de la tanda> [--base TAG --replica TAG]

Lee X_<tag>_f<f>.npy + res_<tag>.json + la escena; imprime una tabla corta y escribe lab/datos/<banco>_<tanda>.json con las
metricas y los DATOS REDUCIDOS (puntos de las franjas, series por cuadro, espesores por vertice) que usan los tests de
prenda3d/tests/test_lab_grupo1.py para reproducir cada ley sin Blender.
"""
import glob
import json
import math
import os
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__)); PAQ = os.path.dirname(AQUI)
sys.path.insert(0, os.path.join(PAQ, "sim"))
import m133_sandwich as SE   # noqa: E402  (sin bpy: transl, taper_w, bary_map, sand_stats)

DATOS = os.path.join(AQUI, "datos")


def escena(nombre):
    return json.load(open(os.path.join(AQUI, "escenas", nombre + ".json"), encoding="utf-8"))


def X(sal, tag, f):
    p = os.path.join(sal, f"X_{tag}_f{f}.npy")
    return np.load(p) if os.path.isfile(p) else None


def resultados(sal):
    return {json.load(open(p, encoding="utf-8"))["tag"]: json.load(open(p, encoding="utf-8")) for p in sorted(glob.glob(os.path.join(sal, "res_*.json")))}


def ids_molde(D, piezas):
    UV = np.array(D["uv"], float); out_i, out_p = [], []
    for g in piezas:
        a, b = D["groups"][g]; out_i.append(np.arange(a, b)); out_p.append(UV[a:b] - np.array(D["lab"]["uv_d"][g]))
    return np.concatenate(out_i), np.concatenate(out_p)


def normales(Xv, F):
    n = np.cross(Xv[F[:, 1]] - Xv[F[:, 0]], Xv[F[:, 2]] - Xv[F[:, 0]]); return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-15)


def diedros(Xv, F, sel=None):
    """angulo (grados) entre normales de triangulos que comparten arista (solo triangulos con todos sus vertices en sel)."""
    F = np.asarray(F)
    if sel is not None:
        F = F[np.isin(F, sel).all(1)]
    N = normales(Xv, F); e = {}
    for t, tri in enumerate(F):
        for k in range(3):
            key = tuple(sorted((int(tri[k]), int(tri[(k + 1) % 3]))))
            e.setdefault(key, []).append(t)
    pares = np.array([v for v in e.values() if len(v) == 2])
    if not len(pares):
        return np.zeros(0)
    return np.degrees(np.arccos(np.clip((N[pares[:, 0]] * N[pares[:, 1]]).sum(1), -1, 1)))


def pendiente(Xs, u):
    """direccion 3D de la tela a lo largo de u (minimos cuadrados X = X0 + u t), normalizada."""
    A = np.c_[np.ones(len(u)), u]; t = np.linalg.lstsq(A, Xs, rcond=None)[0][1]; return t / np.linalg.norm(t)


def angulo_xz(t):
    return math.degrees(math.atan2(t[2], t[0]))


def peirce(l, theta):
    return l * (math.cos(theta / 2) / (8 * math.tan(theta))) ** (1 / 3) if theta > 1e-6 else float("inf")


# ------------------------------------------------------------------------------------------------ B1
def b1_tira(Xv, D, tira, banda=(5.0, 25.0)):
    pz = tira["piezas"]; xs, xr, xp = tira["x_costura"], tira["x_raiz"], tira["x_punta"]
    ia, pa = ids_molde(D, [pz[0]]); ib, pb = ids_molde(D, [pz[-1]])
    ma = (pa[:, 0] >= xs - banda[1]) & (pa[:, 0] <= xs - banda[0]); mb = (pb[:, 0] >= xs + banda[0]) & (pb[:, 0] <= xs + banda[1])
    if len(pz) > 1:
        ma &= pa[:, 0] < xs - 1e-6
    ta, tb = pendiente(Xv[ia[ma]], pa[ma, 0]), pendiente(Xv[ib[mb]], pb[mb, 0])
    i_all, p_all = ids_molde(D, pz)
    raiz = Xv[i_all[np.abs(p_all[:, 0] - xr) < 1e-3]].mean(0); punta = Xv[i_all[np.abs(p_all[:, 0] - xp) < 1e-3]].mean(0)
    caida, alcance = 1000 * (raiz[2] - punta[2]), 1000 * (punta[0] - raiz[0]); th = math.atan2(caida, max(alcance, 1e-6))
    libres = i_all[p_all[:, 0] > xr + 1e-3]
    return dict(quiebre=round(angulo_xz(tb) - angulo_xz(ta), 2), ang_a=round(angulo_xz(ta), 2), ang_b=round(angulo_xz(tb), 2), caida=round(caida, 1),
                alcance=round(alcance, 1), theta=round(math.degrees(th), 2), c=round(peirce(xp - xr, th), 1), diedro_max=round(float(diedros(Xv, D["f"], libres).max()), 1),
                _franja=dict(xa=(Xv[ia[ma]] * 1000).round(3).tolist(), ua=pa[ma, 0].round(3).tolist(), xb=(Xv[ib[mb]] * 1000).round(3).tolist(), ub=pb[mb, 0].round(3).tolist(),
                             raiz=(raiz * 1000).round(3).tolist(), punta=(punta * 1000).round(3).tolist(), l=xp - xr)), libres


def b1(sal, R):
    out = {}
    for tag, r in R.items():
        D = escena(r["escena"]); M = D["lab"]; nf = r.get("cuadros", 72); fin = X(sal, tag, nf)
        if r["estado"] != "FIN" or fin is None:
            out[tag] = dict(estado=r["estado"], error=r.get("error", "")); continue
        o = dict(estado=r["estado"], s_cuadro=r.get("s_por_cuadro"), t_total=r.get("t_total"), params=r["params_var"], costuras=r["costuras_mm"], cuadro=nf)
        if "tiras" in M:
            for k, tira in M["tiras"].items():
                m, libres = b1_tira(fin, D, tira); o[k] = m
                x71, x66 = X(sal, tag, nf - 1), X(sal, tag, nf - 6)
                if x71 is not None:
                    o[k]["jitter_mm"] = round(float(np.sqrt((((fin[libres] - x71[libres]) * 1000) ** 2).sum(1).mean())), 4)
                    o[k]["deriva6_mm"] = round(float(np.abs((fin[libres] - x66[libres]) * 1000).max()), 3)
            o["quiebre_extra"] = round(o["S"]["quiebre"] - o["C"]["quiebre"], 2)
        else:                                       # cilindro: diedro en la costura y dentro de los paneles
            UV = np.array(D["uv"]); F = np.array(D["f"]); N = normales(fin, F); xs = M["x_costura"]; nn = []
            for g in M["paneles"]:
                i, p = ids_molde(D, [g]); en = set(i[np.abs(p[:, 0] - xs) < 1e-3].tolist()); a, b = D["groups"][g]
                ft = [t for t in range(len(F)) if F[t, 0] >= a and F[t, 0] < b and en & set(F[t].tolist())]
                v = N[ft].mean(0); nn.append(v / np.linalg.norm(v))
                o[f"diedro_{g}_p95"] = round(float(np.percentile(diedros(fin, F, np.arange(a, b)), 95)), 2)
                o[f"diedro_{g}_max"] = round(float(diedros(fin, F, np.arange(a, b)).max()), 2)
            o["diedro_costura"] = round(math.degrees(math.acos(np.clip(nn[0] @ nn[1], -1, 1))), 2)
            o["_normales"] = [list(map(float, v)) for v in nn]
        out[tag] = o
    return out


# ------------------------------------------------------------------------------------------------ B2
def plano_resid(P):
    c = P.mean(0); _, _, vt = np.linalg.svd(P - c, full_matrices=False); d = (P - c) @ vt[2]; return 1000 * (d.max() - d.min()), vt[2]


def lobulos(Xf, UVp, fijo):
    """lobulos a lo largo del eje largo (franja central del molde): tramos de signo constante con |d| > 1 mm; d = z (fijo: plano de los
    pines) o distancia al plano medio (libre)."""
    k = np.where(np.abs(UVp[:, 1] * 1000 - 72.5) < 8)[0]; k = k[np.argsort(UVp[k, 0])]
    if fijo:
        d = Xf[k, 2] * 1000
    else:
        c = Xf.mean(0); _, _, vt = np.linalg.svd(Xf - c, full_matrices=False); d = (Xf[k] - c) @ vt[2] * 1000
    n, run = 0, []
    for v in list(d) + [0.0]:
        if run and (np.sign(v) != np.sign(run[0]) or v == 0.0):
            n += int(max(abs(x) for x in run) > 1.0); run = []
        if v != 0.0:
            run.append(v)
    return n


def b2(sal, R):
    out = {}
    for tag, r in R.items():
        D = escena(r["escena"]); a, b = D["groups"]["panel"]; F = np.array(D["f"]); Fp = F[(F >= a).all(1) & (F < b).all(1)]
        fs = sorted(int(p.rsplit("_f", 1)[1][:-4]) for p in glob.glob(os.path.join(sal, f"X_{tag}_f*.npy")) if p.rsplit("_f", 1)[1][:-4].isdigit())
        if r["estado"] != "FIN" or 1 not in fs:
            out[tag] = dict(estado=r["estado"], error=r.get("error", "")); continue
        X1 = X(sal, tag, 1)[a:b]; serie = {}
        UVp = np.array(D["uv"])[a:b] / 1000.0; area0 = 0.5 * np.linalg.norm(np.cross(np.c_[UVp[Fp[:, 1] - a] - UVp[Fp[:, 0] - a], np.zeros(len(Fp))], np.c_[UVp[Fp[:, 2] - a] - UVp[Fp[:, 0] - a], np.zeros(len(Fp))]), axis=1).sum()
        prev = X1
        for f in fs:
            Xf = X(sal, tag, f)[a:b]; dsp = np.linalg.norm(Xf - X1, axis=1) * 1000; rz, nrm = plano_resid(Xf)
            N = normales(Xf, Fp - a); fr = float(1 - np.abs(N @ nrm).mean())
            ar = 0.5 * np.linalg.norm(np.cross(Xf[Fp[:, 1] - a] - Xf[Fp[:, 0] - a], Xf[Fp[:, 2] - a] - Xf[Fp[:, 0] - a]), axis=1).sum() / area0
            serie[f] = dict(dmax=round(float(dsp.max()), 3), dmed=round(float(np.median(dsp)), 3), paso=round(float(np.median(np.linalg.norm(Xf - prev, axis=1)) * 1000), 3),
                            fuera_plano=round(rz, 3), fruncido=round(fr, 5), lobulos=lobulos(Xf, UVp, fijo=bool(D['lab'].get('fijo'))), area=round(float(ar), 4), diedro_max=round(float(diedros(Xf, Fp - a).max()), 1))
            prev = Xf
        fmax = 30 if 30 in serie else max(serie)
        out[tag] = dict(estado=r["estado"], s_cuadro=r.get("s_por_cuadro"), t_total=r.get("t_total"), escala=None, params=r["params_var"],
                        fraccion_f2=round(serie[2]["dmax"] / max(serie[fmax]["dmax"], 1e-9), 3), serie=serie)
    return out


# ------------------------------------------------------------------------------------------------ B3
def cambia_todos(Xa, Xb, bm, F):
    """vertices del ht (todos, sin filtro de peso) que estan del otro lado de su hs en Xa respecto de Xb (cruce de capa)."""
    n = 0; VA, VB = SE.vnormals_np(Xa, F), SE.vnormals_np(Xb, F)
    for i, (tri, w) in bm.items():
        s = []
        for Xv, VN in ((Xa, VA), (Xb, VB)):
            tri_ = np.array(tri); w_ = np.array(w); Pp = (Xv[tri_] * w_[:, None]).sum(0); nn = (VN[tri_] * w_[:, None]).sum(0); s.append(np.sign((Xv[i] - Pp) @ nn))
        n += int(s[0] != s[1])
    return n


def b3(sal, R):
    out = {}
    for tag, r in R.items():
        D = escena(r["escena"]); M = D["lab"]; nf = r.get("cuadros", 72); fin = X(sal, tag, nf); x1 = X(sal, tag, 1)
        if r["estado"] != "FIN" or fin is None:
            out[tag] = dict(estado=r["estado"], error=r.get("error", "")); continue
        P = r["P"]; T = SE.transl(D); BM = SE.bary_map(D, T); W = SE.taper_w(D, P["sand_tap"]); F = np.array(D["f"])
        o = dict(estado=r["estado"], s_cuadro=r.get("s_por_cuadro"), t_total=r.get("t_total"), params=r["params_var"], costuras=r["costuras_mm"])
        for s in "RL":
            a, b = D["groups"]["ht" + s]; bm = {i: v for i, v in BM.items() if a <= i < b}
            def esp(Xv):
                VN = SE.vnormals_np(Xv, F); dn, dt = [], []
                for i, (tri, w) in bm.items():
                    if W.get(i, 0) < 0.99:
                        continue
                    tri = np.array(tri); w = np.array(w); Pp = (Xv[tri] * w[:, None]).sum(0); n = (VN[tri] * w[:, None]).sum(0); n /= np.linalg.norm(n) + 1e-12
                    v = Xv[i] - Pp; q = float(v @ n); dn.append(-q * 1000); dt.append(float(np.linalg.norm(v - q * n)) * 1000)
                return np.array(dn), np.array(dt)
            dn, dt = esp(fin); dn1, _ = esp(x1)
            ih, ph = ids_molde(D, ["hs" + s]); punta = fin[ih[np.abs(ph[:, 0] - M["x_punta"]) < 1e-3]].mean(0); raiz = fin[ih[np.abs(ph[:, 0]) < 1e-3]].mean(0)
            o[s] = dict(esp_med=round(float(np.median(dn)), 2), esp_p5=round(float(np.percentile(dn, 5)), 2), esp_p95=round(float(np.percentile(dn, 95)), 2),
                        desl_med=round(float(np.median(dt)), 2), desl_p95=round(float(np.percentile(dt, 95)), 2), desl_max=round(float(dt.max()), 2),
                        cambian_lado=int((np.sign(dn) != np.sign(dn1)).sum()), n=int(len(dn)), cambian_lado_todos=cambia_todos(fin, x1, bm, F), caida_punta=round(1000 * float(raiz[2] - punta[2]), 1),
                        _dn=dn.round(3).tolist(), _dt=dt.round(3).tolist(), _dn1=dn1.round(3).tolist())
        ic, pc = ids_molde(D, ["ctl"]); o["C"] = dict(caida_punta=round(1000 * float(fin[ic[np.abs(pc[:, 0]) < 1e-3]].mean(0)[2] - fin[ic[np.abs(pc[:, 0] - M["x_punta"]) < 1e-3]].mean(0)[2]), 1))
        out[tag] = o
    return out


def banda(out, base, rep, claves):
    if base not in out or rep not in out or "error" in out[base] or "error" in out[rep]:
        return {}
    g = lambda o, k: o[k.split(".")[0]][k.split(".")[1]] if "." in k else o[k]
    return {k: round(abs(g(out[base], k) - g(out[rep], k)), 3) for k in claves}


def main():
    banco, sal = sys.argv[1], os.path.abspath(sys.argv[2]); kv = dict(zip(sys.argv[3::2], sys.argv[4::2])); R = resultados(sal)
    out = {"b1": b1, "b2": b2, "b3": b3}[banco](sal, R)
    claves = {"b1": ["S.quiebre", "C.quiebre", "quiebre_extra", "C.c", "S.caida"], "b2": ["fraccion_f2"], "b3": ["R.esp_med", "R.desl_med", "L.esp_med", "L.desl_med", "R.caida_punta"]}[banco]
    bd = banda(out, kv.get("--base"), kv.get("--replica"), claves) if kv.get("--base") else {}
    os.makedirs(DATOS, exist_ok=True); ruta = os.path.join(DATOS, f"{banco}_{os.path.basename(sal)}.json")
    json.dump(dict(firma="[ESC·f535]", banco=banco, salida=os.path.basename(sal), banda=bd, variantes=out), open(ruta, "w", encoding="utf-8"), indent=1)
    for tag, o in out.items():
        if "error" in o:
            print(tag, o["estado"], o["error"][:120]); continue
        lim = {k: v for k, v in o.items() if not k.startswith("_") and k not in ("serie", "costuras", "params")}
        txt = json.dumps(lim, ensure_ascii=False)
        txt = txt.replace('"_franja"', '"f"')
        print(tag, json.dumps({k: (({kk: vv for kk, vv in v.items() if not kk.startswith("_")}) if isinstance(v, dict) else v) for k, v in lim.items()}, ensure_ascii=False)[:600])
    if bd:
        print("BANDA (|base - replica|):", bd)
    print("->", ruta)


if __name__ == "__main__":
    main()
