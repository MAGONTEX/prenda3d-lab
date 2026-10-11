"""[ESC·f535] Cola de PRENDAS ENTERAS para GitHub Actions (workflow prenda.yml). Solo stdlib: corre con el python3 del runner.

Tanda = cola_prendas/<nombre>.json (ver prendas/README.md). Cada variante es UN trabajo de Actions (4 vCPU, hasta 20 a la vez, 6 h).
    python3 scripts/prendas.py validar cola_prendas/<t>.json            revisa una tanda sin tomarla (usar antes de encolar)
    python3 scripts/prendas.py tomar --max 20                           git mv cola_prendas -> tomadas_prendas; imprime la matriz ["t--tag", ...]
    python3 scripts/prendas.py preparar <item> <salida>                 receta combinada + args de lanzar.py (uno por linea) en <salida>/
    python3 scripts/prendas.py resumir <item> <salida> --rc N --t S     resumen chico (json) de una variante, leido del log del nucleo
    python3 scripts/prendas.py cerrar --resumenes <dir> --items '[...]' --url U   resultados_prendas/<t>.json + mueve a hecho_/fallo_prendas
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLA, TOMADAS, HECHO, FALLO, RES = "cola_prendas", "tomadas_prendas", "hecho_prendas", "fallo_prendas", "resultados_prendas"
NOMBRE = re.compile(r"^[a-z0-9][a-z0-9_]{0,40}$")
SEP = "--"


def _git(*a):
    subprocess.run(["git", "-C", REPO] + list(a), check=True)


def leer(ruta):
    return json.load(open(ruta, encoding="utf-8"))


ARCHIVOS = ("receta", "malla", "cuerpo", "rk", "wini", "pramp", "pfit", "hrest")   # rk..hrest: especiales de lanzar.py (van por argv)


def campo(T, v, k, d=None):
    """Valor de una variante: la variante manda, despues su grupo (`grupos[v.grupo]`), despues la tanda."""
    g = (T.get("grupos") or {}).get(v.get("grupo"), {}) if v.get("grupo") else {}
    for src in (v, g, T):
        if src.get(k) not in (None, "", []):
            return src[k]
    return d


def validar(T, ruta=""):
    """Lista de errores de una tanda (vacia = se puede correr)."""
    e = []
    nom = T.get("nombre") or os.path.splitext(os.path.basename(ruta))[0]
    if ruta and nom != os.path.splitext(os.path.basename(ruta))[0]:
        e.append(f"nombre {nom!r} distinto del archivo")
    if not NOMBRE.match(nom or ""):
        e.append(f"nombre {nom!r}: solo a-z 0-9 _ (max 41)")
    p = T.get("prenda", "")
    d = os.path.join(REPO, "prendas", p)
    if not p or not os.path.isdir(d):
        e.append(f"prenda {p!r}: no existe prendas/{p}/")
        return e
    if not os.path.isfile(os.path.join(d, "prenda_publica.json")):
        e.append(f"falta prendas/{p}/prenda_publica.json")
    if not os.path.isfile(os.path.join(REPO, T.get("script", "sim/lanzar.py"))):
        e.append(f"script {T.get('script')!r} no existe")
    V = T.get("variantes") or []
    if not V:
        e.append("sin variantes")
    tags = [v.get("tag", "") for v in V]
    if len(set(tags)) != len(tags):
        e.append("tags repetidos")
    for v in V:
        if not NOMBRE.match(v.get("tag", "")):
            e.append(f"tag {v.get('tag')!r}: solo a-z 0-9 _")
        if v.get("grupo") and v["grupo"] not in (T.get("grupos") or {}):
            e.append(f"{v.get('tag')}: grupo {v['grupo']!r} no esta en `grupos`")
        if not campo(T, v, "receta"):
            e.append(f"{v.get('tag')}: sin receta")
        nf = campo(T, v, "nf")
        if not isinstance(nf, int) or nf < 1 or nf > 2000:
            e.append(f"{v.get('tag')}: nf entero 1..2000")
        for k in ARCHIVOS:
            x = campo(T, v, k)
            if x and not os.path.isfile(os.path.join(d, x)):
                e.append(f"{v.get('tag')}: {k} {x!r} no esta en prendas/{p}/")
    h = T.get("hilos", 4)
    if not isinstance(h, int) or not 1 <= h <= 4:
        e.append("hilos: 1..4 (el runner tiene 4 vCPU)")
    return e


def cmd_validar(a):
    T = leer(a.tanda); e = validar(T, a.tanda)
    print("OK: " + ", ".join(f"{T['nombre']}{SEP}{v['tag']}" for v in T["variantes"]) if not e else "\n".join("ERROR " + x for x in e))
    return 1 if e else 0


def cmd_tomar(a):
    items = []
    for ruta in sorted(glob.glob(os.path.join(REPO, COLA, "*.json"))):
        t = os.path.splitext(os.path.basename(ruta))[0]
        try:
            T = leer(ruta); e = validar(T, ruta)
        except Exception as ex:
            T, e = {}, [f"json ilegible: {ex}"]
        if e:
            T["error"] = e
            os.makedirs(os.path.join(REPO, FALLO), exist_ok=True)
            _git("mv", "-f", ruta, os.path.join(REPO, FALLO, t + ".json"))
            json.dump(T, open(os.path.join(REPO, FALLO, t + ".json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
            _git("add", os.path.join(FALLO, t + ".json"))
            print(f"tanda {t} invalida: {e}", file=sys.stderr)
            continue
        n = len(T["variantes"])
        if items and len(items) + n > a.max:
            break   # queda para la proxima corrida (prenda.yml se relanza si queda algo en la cola)
        T["tomada"] = {"por": a.quien, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        os.makedirs(os.path.join(REPO, TOMADAS), exist_ok=True)
        dst = os.path.join(REPO, TOMADAS, t + ".json")
        _git("mv", "-f", ruta, dst)
        json.dump(T, open(dst, "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
        _git("add", os.path.join(TOMADAS, t + ".json"))
        items += [f"{t}{SEP}{v['tag']}" for v in T["variantes"]]
    print(json.dumps(items))
    return 0


def _tanda_de(item):
    t, tag = item.split(SEP, 1)
    T = leer(os.path.join(REPO, TOMADAS, t + ".json"))
    v = next(x for x in T["variantes"] if x["tag"] == tag)
    return T, v, tag


def cmd_preparar(a):
    T, v, tag = _tanda_de(a.item)
    d = os.path.join("prendas", T["prenda"])
    R = leer(os.path.join(REPO, d, campo(T, v, "receta")))
    R.setdefault("params", {})
    R["params"]["renders"] = 0   # sin GPU: el render Workbench queda apagado salvo que la tanda lo pida en params
    g = (T.get("grupos") or {}).get(v.get("grupo"), {}) if v.get("grupo") else {}
    for src in (T.get("params") or {}, g.get("params") or {}, v.get("params") or {}):
        R["params"].update(src)
    nf = int(campo(T, v, "nf"))
    dumps = campo(T, v, "dumps") or R.get("dumps") or []
    R["dumps"] = sorted({int(x) for x in dumps if int(x) <= nf} | {nf})
    R["frames"] = nf
    for k in ("malla", "cuerpo"):
        if campo(T, v, k):
            R[k] = campo(T, v, k)
    R["nombre"] = f"{R.get('nombre', 'receta')}__{T['nombre']}_{tag}"
    os.makedirs(a.salida, exist_ok=True)
    rr = os.path.join(a.salida, f"receta_{tag}.json")
    json.dump(R, open(rr, "w", encoding="utf-8", newline="\n"), indent=1)
    args = [f"prenda={d}/prenda_publica.json", f"receta={rr}", f"entradas={d}", f"salida={a.salida}", f"tag={tag}", f"nf={nf}"]
    args += [f"{k}={campo(T, v, k)}" for k in ("malla", "cuerpo", "rk", "wini", "pramp", "pfit", "hrest", "base") if campo(T, v, k)]
    open(os.path.join(a.salida, "args.txt"), "w", encoding="utf-8", newline="\n").write("\n".join(args) + "\n")
    print(T.get("script", "sim/lanzar.py"))
    print(T.get("hilos", 4))
    print(int(T.get("tmo_min", 330)))
    return 0


RX_F = re.compile(r"^f(\d+) t=(\d+)s .*costura media ([\d.]+) max ([\d.]+) mm")
RX_C = re.compile(r"^(.+?)\s+n\s+(\d+)\s+max\s+([\d.]+) mm\s+p95\s+([\d.]+)\s+media\s+([\d.]+)")
PRIV = re.compile(r"(/home/\S+|/tmp/\S+|C:[\\/]\S+)")


def _limpio(s):
    return PRIV.sub("<ruta>", s)[:300]


def cmd_resumir(a):
    T, v, tag = _tanda_de(a.item)
    log = os.path.join(a.salida, f"sim_{tag}.log")
    L = open(log, encoding="utf-8", errors="replace").read().splitlines() if os.path.isfile(log) else []
    f = [m for m in (RX_F.match(x) for x in L) if m]
    cost = sorted(((float(m.group(3)), m.group(1).strip(), int(m.group(2)), float(m.group(4)), float(m.group(5)))
                   for m in (RX_C.match(x) for x in L) if m), reverse=True)
    tsim = [x for x in L if x.startswith("t sim")]
    man = {}
    for p in sorted(glob.glob(os.path.join(a.salida, "corridas", "*.json")), key=os.path.getmtime):
        try:
            man = leer(p)
        except Exception:
            pass
    npy = sorted(os.path.basename(x) for x in glob.glob(os.path.join(a.salida, f"X_{tag}_*.npy")))
    R = {"item": a.item, "tag": tag, "prenda": T["prenda"], "rc": a.rc, "t_pared_s": a.t,
         "estado": man.get("estado") or ("SIN_MANIFEST" if a.rc == 0 else "ERROR"), "cuadros_pedidos": int(campo(T, v, "nf")), "grupo": v.get("grupo"),
         "cuadros_hechos": man.get("cuadros_hechos", int(f[-1].group(1)) if f else 0),
         "t_sim_s": int(tsim[-1].split()[-1]) if tsim else None,
         "stop": [_limpio(x) for x in L if x.startswith("STOP")],
         "costura_ultimo_cuadro": ({"f": int(f[-1].group(1)), "t_s": int(f[-1].group(2)), "media_mm": float(f[-1].group(3)), "max_mm": float(f[-1].group(4))} if f else None),
         "costuras_peores": [{"costura": c[1], "n": c[2], "max_mm": c[0], "p95_mm": c[3], "media_mm": c[4]} for c in cost[:8]],
         "asent": _limpio(next((x.strip() for x in reversed(L) if x.strip().startswith("ASENT")), "")),
         "avisos": [_limpio(x) for x in L if x.startswith("AVISO")][:6],
         "error": _limpio(man.get("error", "")) or (_limpio(next((x for x in reversed(L) if "Error" in x), "")) if a.rc else ""),
         "params": man.get("params_finales") or {}, "receta_hash": man.get("receta_hash"), "id_corrida": man.get("id"),
         "blender": (man.get("blender") or {}).get("version"), "hilos": (man.get("hilos") or {}).get("n"),
         "dumps": npy, "params_variante": v.get("params") or {}}
    print(json.dumps(R, indent=1, ensure_ascii=False))
    return 0


def cmd_cerrar(a):
    items = json.loads(a.items); por = {}
    for it in items:
        por.setdefault(it.split(SEP, 1)[0], []).append(it)
    os.makedirs(os.path.join(REPO, RES), exist_ok=True)
    for t, its in por.items():
        src = os.path.join(REPO, TOMADAS, t + ".json")
        if not os.path.isfile(src):
            print(f"{t}: ya no esta en {TOMADAS}/ (otro cierre?)"); continue
        T = leer(src); V = {}
        for it in its:
            p = os.path.join(a.resumenes, it + ".json")
            V[it.split(SEP, 1)[1]] = leer(p) if os.path.isfile(p) else {"estado": "SIN_RESUMEN"}
        ok = all(x.get("rc") == 0 and x.get("estado") in ("FIN", "STOP", "ESTABLE") for x in V.values())
        R = {"tanda": t, "prenda": T["prenda"], "url": a.url, "estado": "OK" if ok else "FALLO", "nota": T.get("nota", ""),
             "tomada": T.get("tomada"), "cerrada_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "variantes": V,
             "artifacts": [f"prenda-{it}-<run>" for it in its]}
        json.dump(R, open(os.path.join(REPO, RES, t + ".json"), "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
        _git("add", os.path.join(RES, t + ".json"))
        dst = HECHO if ok else FALLO
        os.makedirs(os.path.join(REPO, dst), exist_ok=True)
        _git("mv", "-f", src, os.path.join(REPO, dst, t + ".json"))
        print(f"| {t} | {R['estado']} | " + " ; ".join(f"{k}: {x.get('estado')} f{x.get('cuadros_hechos')} t {x.get('t_sim_s')} s STOP {len(x.get('stop') or [])}" for k, x in V.items()) + " |")
    return 0


def main():
    ap = argparse.ArgumentParser(); s = ap.add_subparsers(dest="c", required=True)
    x = s.add_parser("validar"); x.add_argument("tanda")
    x = s.add_parser("tomar"); x.add_argument("--max", type=int, default=20); x.add_argument("--quien", default="local")
    x = s.add_parser("preparar"); x.add_argument("item"); x.add_argument("salida")
    x = s.add_parser("resumir"); x.add_argument("item"); x.add_argument("salida"); x.add_argument("--rc", type=int, default=0); x.add_argument("--t", type=int, default=0)
    x = s.add_parser("cerrar"); x.add_argument("--resumenes", required=True); x.add_argument("--items", required=True); x.add_argument("--url", default="")
    a = ap.parse_args()
    return {"validar": cmd_validar, "tomar": cmd_tomar, "preparar": cmd_preparar, "resumir": cmd_resumir, "cerrar": cmd_cerrar}[a.c](a)


if __name__ == "__main__":
    sys.exit(main())
