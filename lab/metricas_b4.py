"""[ESC·f535] lab/metricas_b4.py - metricas del banco 4 (canal con mascara de acortamiento en el pespunte). numpy, sin Blender.

    python lab/metricas_b4.py lab/out/b4_canal_mascara [--f 96] [--png 1]

Por variante (cuadro final): frunce junto al pespunte (perfil del ESPESOR cascara-pared a 8 mm del pespunte, a lo largo del
canal, y = 30..270 cada 2 mm, en las 4 lineas que tocan los 2 pespuntes; tendencia cuadratica afuera; amplitud = raiz2*rms;
lambda = pico de la FFT con ventana de Hann entre 30 y 120 mm (>= 3 aristas), en mm de MOLDE), lo mismo en la cresta (centro del canal),
loft (mediana del espesor en la cresta del canal central, y 60..240), deformacion de las aristas de la cascara contra el reposo
EFECTIVO (molde * sqrt(k_i k_j), k de encoge_<tag>.npy) en el canal central: p5 lejos (>= 15 mm del pespunte) a lo largo y a
traves, p5 cerca (<= 10 mm), acortamiento 3D del pespunte, ancho 3D del canal central, asentamiento (f84 -> final) y costuras.
Escribe lab/datos/b4_<tanda>.json con metricas + perfiles crudos (los usa tests/test_lab_b4.py) y banda |base - replica|.
"""
import json
import os
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__)); DATOS = os.path.join(AQUI, "datos")
Y = np.arange(30.0, 270.0 + 1e-9, 2.0)


def cargar(sal, tag, f):
    p = os.path.join(sal, f"X_{tag}_f{f}.npy")
    return np.load(p) if os.path.isfile(p) else None


def bary(UVt, pts):
    """indice de triangulo y pesos baricentricos de cada punto (uv del molde)."""
    A, B, C = UVt[:, 0], UVt[:, 1], UVt[:, 2]; v0, v1 = B - A, C - A; den = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]
    T, W = [], []
    for p in pts:
        d = p - A; l1 = (d[:, 0] * v1[:, 1] - v1[:, 0] * d[:, 1]) / den; l2 = (v0[:, 0] * d[:, 1] - d[:, 0] * v0[:, 1]) / den
        m = np.minimum(np.minimum(l1, l2), 1 - l1 - l2); t = int(np.argmax(m))
        T.append(t); W.append((1 - l1[t] - l2[t], l1[t], l2[t]))
    return np.array(T), np.array(W)


def espectro(s, dy=2.0, lmin=30.0, lmax=120.0):   # lmin 30 = 3 aristas de 10 mm: debajo, el pico es la faceta de la malla (visto en a2: 17-18 mm)
    """amplitud (raiz2*rms sin tendencia cuadratica) y lambda del pico de la FFT (ventana de Hann, relleno a 4096)."""
    t = np.arange(len(s)) * dy; r = s - np.polyval(np.polyfit(t, s, 2), t); amp = float(np.sqrt(2) * r.std())
    P = np.abs(np.fft.rfft(r * np.hanning(len(r)), 4096)) ** 2; fr = np.fft.rfftfreq(4096, dy)
    ok = (fr >= 1 / lmax) & (fr <= 1 / lmin); i = np.where(ok)[0][int(np.argmax(P[ok]))]
    return amp, float(1 / fr[i]), float(P[i] / max(np.median(P[ok]), 1e-30))


def valles(s, prof=1.0, dy=2.0, ven=30.0):
    """valles del perfil sin tendencia cuadratica con profundidad >= prof mm contra el maximo a +-ven mm de cada lado."""
    t = np.arange(len(s)) * dy; r = np.asarray(s) - np.polyval(np.polyfit(t, s, 2), t); m = int(ven / dy); n = 0
    for i in range(1, len(r) - 1):
        if r[i] < r[i - 1] and r[i] <= r[i + 1] and min(r[max(0, i - m):i].max(), r[i + 1:i + 1 + m].max()) - r[i] >= prof:
            n += 1
    return n


def cruces(s, dy=2.0):
    """[ESC·f535] lambda por cruces por cero del perfil sin tendencia cuadratica: 2 * tramo / cruces (mm)."""
    t = np.arange(len(s)) * dy; r = np.asarray(s) - np.polyval(np.polyfit(t, s, 2), t); c = int((np.diff(np.sign(r)) != 0).sum())
    return round(2 * t[-1] / max(c, 1), 1)


def variante(D, M, X, k, Xprev, lmin=30.0, dists=(8.0,)):
    a, b = D["groups"]["cn"]; af = D["groups"]["cn_f"][0]; uv = np.array(D["uv"]); F = np.array(D["f"])
    Fs = F[(F >= a).all(1) & (F < b).all(1)]; UVt = uv[Fs]; lx = M["lx"]; A = M["ancho"]; L = M["largo"]
    def espesor(x0, ys):
        T, W = bary(UVt, np.c_[np.full(len(ys), x0), ys]); ids = Fs[T]
        Xs = (X[ids] * W[..., None]).sum(1); Xw = (X[ids - a + af] * W[..., None]).sum(1)
        return 1000 * np.linalg.norm(Xs - Xw, axis=1), 1000 * Xs[:, 2]
    o = dict(perfiles={}, alturas={})
    lineas = [(f"p{int(x)}{s}", x + d) for x in lx for s, d in (("-", -8.0), ("+", 8.0))]
    am, la, pr = [], [], []
    for nm, x0 in lineas:
        e, z = espesor(x0, Y); o["perfiles"][nm] = np.round(e, 3).tolist(); o["alturas"][nm] = np.round(z, 3).tolist()
        q = espectro(e, lmin=lmin); am.append(q[0]); la.append(q[1]); pr.append(q[2])
    for dd in dists:                                   # [ESC·f535] h5: lineas a otras distancias del pespunte + lambda por cruces por cero
        a_, l_, z_ = [], [], []
        for x in lx:
            for sg in (-1.0, 1.0):
                e, _ = espesor(x + sg * dd, Y); q = espectro(e, lmin=lmin); a_.append(q[0]); l_.append(q[1]); z_.append(cruces(e))
        o[f"amp_d{dd:g}"] = round(float(np.mean(a_)), 3); o[f"lam_d{dd:g}"] = round(float(np.median(l_)), 1); o[f"lamzc_d{dd:g}"] = round(float(np.median(z_)), 1)
    o.update(amp_p=round(float(np.mean(am)), 3), lam_p=round(float(np.median(la)), 1), lam_p_lineas=np.round(la, 1).tolist(),
             prom_p=round(float(np.median(pr)), 1), amp_p_lineas=np.round(am, 3).tolist())
    xc = lx[0] + A / 2; e, z = espesor(xc, Y); o["perfiles"]["cresta"] = np.round(e, 3).tolist(); q = espectro(e, lmin=lmin)
    XS = np.arange(lx[0] + 2.5, lx[1] - 2.5 + 1e-9, 2.5); YS = np.arange(60.0, 240.0 + 1e-9, 10.0); zt, zw = [], []   # [ESC·f535] caida: perfil transversal
    for x0 in XS:
        T_, W_ = bary(UVt, np.c_[np.full(len(YS), x0), YS]); ids = Fs[T_]
        zt.append(float(np.median(1000 * (X[ids][..., 2] * W_).sum(1)))); zw.append(float(np.median(1000 * (X[ids - a + af][..., 2] * W_).sum(1))))
    o["caida_x"] = np.round(XS, 1).tolist(); o["caida_z"] = np.round(zt, 3).tolist(); o["caida_zw"] = np.round(zw, 3).tolist()
    o["z_cresta"] = round(float(np.max(zt)), 2); o["z_pared"] = round(float(np.min(zw)), 2)
    o.update(valles_c=valles(e), valles_p=[valles(np.array(o["perfiles"][nm])) for nm, _ in lineas], amp_c=round(q[0], 3), lam_c=round(q[1], 1), loft=round(float(np.median(e[(Y >= 60) & (Y <= 240)])), 2))
    # aristas de la cascara contra el reposo efectivo
    E = np.unique(np.sort(np.r_[Fs[:, [0, 1]], Fs[:, [1, 2]], Fs[:, [2, 0]]], 1), axis=0); U0, U1 = uv[E[:, 0]], uv[E[:, 1]]
    lr = np.linalg.norm(U0 - U1, axis=1) * np.sqrt(k[E[:, 0]] * k[E[:, 1]]); l3 = 1000 * np.linalg.norm(X[E[:, 0]] - X[E[:, 1]], axis=1)
    st = 100 * (l3 / lr - 1); st0 = 100 * (l3 / np.linalg.norm(U0 - U1, axis=1) - 1)
    xm = np.minimum(U0[:, 0], U1[:, 0]); xM = np.maximum(U0[:, 0], U1[:, 0]); ym = np.minimum(U0[:, 1], U1[:, 1]); yM = np.maximum(U0[:, 1], U1[:, 1])
    dp = np.minimum.reduce([np.abs(U0[:, 0] - x) for x in lx] + [np.abs(U1[:, 0] - x) for x in lx])
    cen = (xm >= lx[0] - 1e-6) & (xM <= lx[1] + 1e-6) & (ym >= 30) & (yM <= L - 30)
    lej = cen & (dp >= 15); cer = cen & (dp <= 10); lar = np.abs(U1[:, 1] - U0[:, 1]) > np.abs(U1[:, 0] - U0[:, 0])
    p5 = lambda s: round(float(np.percentile(s, 5)), 2) if len(s) else None
    o.update(p5_lejos=p5(st[lej]), p5_lejos_largo=p5(st[lej & lar]), p5_lejos_traves=p5(st[lej & ~lar]), p50_lejos=round(float(np.median(st[lej])), 2),
             p5_cerca=p5(st[cer]), p50_cerca=round(float(np.median(st[cer])), 2), p5_lejos_molde=p5(st0[lej]), n_lejos=int(lej.sum()), n_cerca=int(cer.sum()),
             deform_lejos=np.round(st[lej], 3).tolist())
    lp = []
    for x in lx:
        ids = sorted([i for i in range(a, b) if abs(uv[i, 0] - x) < 1e-4], key=lambda i: uv[i, 1]); lp.append(1000 * np.linalg.norm(np.diff(X[ids], axis=0), axis=1).sum())
    o["acort_pesp"] = round(100 * (float(np.mean(lp)) / L - 1), 2)
    ym_ = [i for i in range(a, b) if abs(uv[i, 1] - L / 2) < 5.01]
    pa = [min(ym_, key=lambda i: abs(uv[i, 0] - x) + abs(uv[i, 1] - L / 2)) for x in lx]
    o["ancho_c"] = round(100 * (1000 * float(np.linalg.norm(X[pa[0]] - X[pa[1]])) / A - 1), 2)
    if Xprev is not None:
        o["asentado_mm"] = round(float(1000 * np.percentile(np.linalg.norm(X[a:b] - Xprev[a:b], axis=1), 95)), 2)
    return o


def main():
    sal = os.path.abspath(sys.argv[1]); kv = dict(zip(sys.argv[2::2], sys.argv[3::2])); f = int(kv.get("--f", 96))
    lmin = float(kv.get("--lmin", 30.0)); dists = tuple(float(x) for x in kv["--dist"].split(",")) if kv.get("--dist") else ()
    T = json.load(open(os.path.join(AQUI, "tandas", os.path.basename(sal).split("_t")[0] + ".json"), encoding="utf-8"))
    out = {}
    for var in T["variantes"]:
        tag = var["tag"]; rp = os.path.join(sal, f"res_{tag}.json")
        if not os.path.isfile(rp):
            continue
        res = json.load(open(rp, encoding="utf-8")); D = json.load(open(os.path.join(AQUI, "escenas", var["escena"] + ".json"), encoding="utf-8"))
        X = cargar(sal, tag, f)
        if res["estado"] != "FIN" or X is None:
            out[tag] = dict(estado=res["estado"], error=res.get("error", "sin X")); continue
        kp = os.path.join(sal, f"encoge_{tag}.npy"); k = np.load(kp) if os.path.isfile(kp) else np.ones(len(X))
        o = variante(D, D["lab"], X, k, cargar(sal, tag, f - 12), lmin=lmin, dists=dists); o.update(estado=res["estado"], encoge=var.get("encoge"), replica=var.get("replica", 0),
                                                                  costura_max=max(v["max"] for v in res["costuras_mm"].values()), s_cuadro=res.get("s_por_cuadro"))
        bp = os.path.join(sal, f"bolsillos_{tag}.json")
        if os.path.isfile(bp):
            B = json.load(open(bp, encoding="utf-8")); o["vol_vt"] = np.round(np.array(B["vol_m3"]) / np.array(B["vt_m3"]), 3).tolist(); o["W"] = np.round(B["w"], 3).tolist()
        out[tag] = o
    claves = ["amp_p", "lam_p", "amp_c", "valles_c", "loft", "p5_lejos", "p5_lejos_largo", "p5_cerca", "acort_pesp", "ancho_c"]
    bd = {}
    pares = [("a0", "a0r"), ("b20", "b20r")] + [(v["tag"][:-1], v["tag"]) for v in T["variantes"] if v.get("replica") and v["tag"].endswith("r") and v["tag"][:-1] not in ("a0", "b20")]
    claves = claves + sorted({c for o in out.values() if "error" not in o for c in o if c.startswith(("amp_d", "lam_d", "lamzc_d"))} | {"z_cresta", "z_pared"})
    for base, rep in pares:
        if base in out and rep in out and "error" not in out[base] and "error" not in out[rep]:
            bd[base] = {c: round(abs(out[base][c] - out[rep][c]), 3) for c in claves}
    os.makedirs(DATOS, exist_ok=True); ruta = os.path.join(DATOS, f"b4_{os.path.basename(sal)}.json")
    json.dump(dict(firma="[ESC·f535]", banco="b4", salida=os.path.basename(sal), cuadro=f, y_mm=Y.tolist(), banda=bd, variantes=out), open(ruta, "w", encoding="utf-8"), indent=1)
    print("tag    " + " ".join(f"{c:>13s}" for c in claves + ["costura_max", "asentado_mm"]))
    for tag, o in out.items():
        if "error" in o:
            print(tag, o["estado"], o["error"][:120]); continue
        print(f"{tag:6s} " + " ".join(f"{str(o.get(c)):>13s}" for c in claves + ["costura_max", "asentado_mm"]), "| lam lineas", o["lam_p_lineas"], "| vol/vt", o.get("vol_vt"), "W", o.get("W"))
    print("BANDA |base - replica|:", bd); print("->", ruta)
    if kv.get("--png"):
        png(sal, T, f, out)


def png(sal, T, f, out):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    tags = [v["tag"] for v in T["variantes"] if v["tag"] in out and "error" not in out[v["tag"]] and not v.get("replica")]
    fig, ax = plt.subplots(2, (len(tags) + 1) // 2, figsize=(3.2 * ((len(tags) + 1) // 2), 7.5))
    for axx, tag in zip(ax.ravel(), tags):
        esc = next(v["escena"] for v in T["variantes"] if v["tag"] == tag)   # [ESC·f535] cada variante con SU escena (h10 y h5 en la misma tanda)
        D = json.load(open(os.path.join(AQUI, "escenas", esc + ".json"), encoding="utf-8")); a, b = D["groups"]["cn"]
        X = cargar(sal, tag, f); uv = np.array(D["uv"])[a:b]; F = np.array(D["f"]); Fs = F[(F >= a).all(1) & (F < b).all(1)] - a
        axx.tripcolor(uv[:, 0], uv[:, 1], Fs, 1000 * X[a:b, 2], shading="gouraud", cmap="gray", vmin=0, vmax=32)
        axx.set_title(f"{tag} amp {out[tag]['amp_p']} lam {out[tag]['lam_p']}", fontsize=8); axx.set_aspect("equal"); axx.axis("off")
    fig.tight_layout(); ruta = os.path.join(sal, f"altura_f{f}.png"); fig.savefig(ruta, dpi=70); print("png ->", ruta)


if __name__ == "__main__":
    main()
