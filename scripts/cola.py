"""[ESC·f535] scripts/cola.py - cola autonoma de bancos del laboratorio (solo stdlib; las metricas usan numpy).

Carpetas del repo:  cola/ (pendientes) -> tomadas/ (alguien la corre; <t>.quien dice quien y cuando)
                    -> hecho/ (corrio bien) | fallo/ (algo fallo)      resultados/<t>.json = resumen chico
Subcomandos:
    validar  <tanda.json> [--raiz R]                 formato + escenas/receta existentes en el repo
    tomar    --quien Q [--max 20] [--donde actions|vps] [--viejas-h 6]   mueve cola->tomadas (git mv), imprime lista json
    metricas <tanda.json> <salida>                   corre el script de metricas declarado en la tanda
    resumir  <tanda.json> <salida> --estado-correr X --estado-metricas Y [--quien Q] [--t-blender S]
    cerrar   --resumenes DIR --tandas '["a","b"]' [--url U]   resultados/<t>.json + mueve a hecho/ o fallo/
Las operaciones git (commit/push con reintento) las hace quien llama: el workflow cola.yml o worker_vps.sh.
"""
import argparse
import datetime as dt
import glob
import json
import os
import re
import subprocess
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOMBRE_OK = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,60}$")
CLAVES_TANDA = {"nombre", "firma", "nota", "receta", "receta_lab", "nf", "dumps", "variantes", "metricas", "donde", "hilos"}
CLAVES_VAR = {"tag", "escena", "params", "nf", "dumps", "escala", "ruido_z_mm", "replica", "nota", "encoge", "reescala"}
SCRIPTS_METRICAS = {"lab/metricas.py", "lab/metricas_b4.py", "lab/metricas_b78.py"}
# metricas por defecto de las tandas que ya tienen resultados de laptop (base/replica de progreso.txt)
METRICAS_CONOCIDAS = {
    "b1_bisagra": ["lab/metricas.py", "b1", "{sal}", "--base", "b240", "--replica", "b240r"],
    "b2_salto": ["lab/metricas.py", "b2", "{sal}", "--base", "s0877", "--replica", "s0877r"],
    "b3_sandwich": ["lab/metricas.py", "b3", "{sal}", "--base", "base", "--replica", "base_r"],
    "b7_cuello": ["lab/metricas_b78.py", "b7", "{sal}"],
    "b8_cartera": ["lab/metricas_b78.py", "b8", "{sal}"],
}
LIMITE_RESUMEN = 60_000   # bytes: el resumen tiene que poder leerlo un agente sin bajar artifacts


def ahora():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def git(*a, check=True):
    return subprocess.run(["git", *a], cwd=RAIZ, check=check, capture_output=True, text=True).stdout.strip()


# ---------- validar ----------
def validar(T, raiz=RAIZ, nombre_archivo=None):
    """Devuelve lista de errores (vacia = ok)."""
    e = []
    if not isinstance(T, dict):
        return ["la tanda no es un objeto json"]
    extra = set(T) - CLAVES_TANDA
    if extra:
        e.append(f"claves desconocidas en la tanda: {sorted(extra)}")
    for k in ("nombre", "receta", "receta_lab", "nf", "dumps", "variantes"):
        if k not in T:
            e.append(f"falta '{k}'")
    if e:
        return e
    if not NOMBRE_OK.match(T["nombre"]):
        e.append(f"nombre invalido '{T['nombre']}' (a-z 0-9 _ . -)")
    if nombre_archivo and nombre_archivo != T["nombre"]:
        e.append(f"el archivo se llama {nombre_archivo}.json pero nombre = {T['nombre']}")
    if not os.path.isfile(os.path.join(raiz, T["receta"])):
        e.append(f"receta inexistente en el repo: {T['receta']}")
    if not isinstance(T["receta_lab"], dict):
        e.append("receta_lab tiene que ser un objeto")
    if not (isinstance(T["nf"], int) and 1 <= T["nf"] <= 2000):
        e.append("nf fuera de rango (1..2000)")
    if not (isinstance(T["dumps"], list) and all(isinstance(d, int) for d in T["dumps"])):
        e.append("dumps tiene que ser lista de enteros")
    if T.get("donde", "cualquiera") not in ("cualquiera", "actions", "vps"):
        e.append("donde = cualquiera | actions | vps")
    V = T["variantes"]
    if not (isinstance(V, list) and 1 <= len(V) <= 200):
        return e + ["variantes: lista de 1..200"]
    tags = [v.get("tag") for v in V]
    if len(set(tags)) != len(tags):
        e.append("tags repetidos")
    for v in V:
        if not NOMBRE_OK.match(str(v.get("tag", ""))):
            e.append(f"tag invalido: {v.get('tag')}")
        x = set(v) - CLAVES_VAR
        if x:
            e.append(f"{v.get('tag')}: claves desconocidas {sorted(x)}")
        if not os.path.isfile(os.path.join(raiz, "lab", "escenas", f"{v.get('escena')}.json")):
            e.append(f"{v.get('tag')}: escena inexistente en el repo: lab/escenas/{v.get('escena')}.json")
        if not isinstance(v.get("params", {}), dict):
            e.append(f"{v.get('tag')}: params tiene que ser objeto")
    m = T.get("metricas")
    if m is not None:
        if not (isinstance(m, list) and m and m[0] in SCRIPTS_METRICAS and "{sal}" in m):
            e.append(f"metricas = [script de {sorted(SCRIPTS_METRICAS)}, args..., con '{{sal}}' donde va la salida]")
    return e


# ---------- tomar ----------
def leer_quien(p):
    try:
        q = open(p, encoding="utf-8").read().split("\t")
        return q[0], dt.datetime.fromisoformat(q[1].strip())
    except Exception:
        return "?", dt.datetime.fromtimestamp(0, dt.timezone.utc)


def tomar(quien, maximo, donde, viejas_h):
    # 1) soltar tomas viejas (el que la tomo murio): vuelven a la cola
    for q in sorted(glob.glob(os.path.join(RAIZ, "tomadas", "*.quien"))):
        _, cuando = leer_quien(q)
        if (dt.datetime.now(dt.timezone.utc) - cuando).total_seconds() > viejas_h * 3600:
            t = os.path.basename(q)[:-6]
            git("mv", "-f", f"tomadas/{t}.json", f"cola/{t}.json", check=False); git("rm", "-q", "-f", f"tomadas/{t}.quien", check=False)
            print(f"suelto toma vieja: {t}", file=sys.stderr)
    # 2) tomar pendientes, la mas vieja primero (fecha del commit que la encolo)
    pend = []
    for p in glob.glob(os.path.join(RAIZ, "cola", "*.json")):
        t = os.path.basename(p)[:-5]
        try:
            T = json.load(open(p, encoding="utf-8"))
        except Exception as ex:
            print(f"{t}: json roto ({ex}) -> fallo/", file=sys.stderr)
            os.makedirs(os.path.join(RAIZ, "fallo"), exist_ok=True); git("mv", "-f", f"cola/{t}.json", f"fallo/{t}.json"); continue
        if T.get("donde", "cualquiera") not in ("cualquiera", donde):
            continue
        err = validar(T, nombre_archivo=t)
        if err:
            print(f"{t}: invalida {err} -> fallo/", file=sys.stderr)
            os.makedirs(os.path.join(RAIZ, "fallo"), exist_ok=True); git("mv", "-f", f"cola/{t}.json", f"fallo/{t}.json"); continue
        pend.append((git("log", "-1", "--format=%cI", "--", f"cola/{t}.json", check=False) or ahora(), t))
    tomadas = []
    os.makedirs(os.path.join(RAIZ, "tomadas"), exist_ok=True)
    for enc, t in sorted(pend)[:maximo]:
        git("mv", "-f", f"cola/{t}.json", f"tomadas/{t}.json")
        with open(os.path.join(RAIZ, "tomadas", f"{t}.quien"), "w", encoding="utf-8") as fh:
            fh.write(f"{quien}\t{ahora()}\tencolada {enc}\n")
        git("add", f"tomadas/{t}.quien"); tomadas.append(t)
    print(json.dumps(tomadas))


# ---------- metricas ----------
def correr_metricas(tanda, sal):
    T = json.load(open(tanda, encoding="utf-8"))
    m = T.get("metricas") or METRICAS_CONOCIDAS.get(T["nombre"])
    if not m:
        print("sin metricas declaradas: solo tiempos y estados"); return 0
    datos = os.path.join(RAIZ, "lab", "datos"); antes = set(os.listdir(datos)) if os.path.isdir(datos) else set()
    cmd = [sys.executable, os.path.join(RAIZ, m[0])] + [a.replace("{sal}", os.path.abspath(sal)) for a in m[1:]]
    r = subprocess.run(cmd, cwd=RAIZ)
    nuevos = sorted(set(os.listdir(datos)) - antes) if os.path.isdir(datos) else []
    os.makedirs(os.path.join(sal, "datos"), exist_ok=True)
    for n in nuevos:   # el json completo de metricas viaja con los npy (artifact); el resumen lo reduce
        os.replace(os.path.join(datos, n), os.path.join(sal, "datos", n))
    return r.returncode


# ---------- resumir ----------
def reducir(o, prof=0):
    """Saca lo pesado del json de metricas: claves '_*', series, listas largas."""
    if isinstance(o, dict):
        return {k: reducir(v, prof + 1) for k, v in o.items() if not str(k).startswith("_") and k not in ("serie", "y_mm")}
    if isinstance(o, list):
        return [reducir(v, prof + 1) for v in o] if len(o) <= 12 else f"<lista de {len(o)}>"
    if isinstance(o, float):
        return round(o, 4)
    return o


def resumir(tanda, sal, est_correr, est_metricas, quien, t_blender):
    T = json.load(open(tanda, encoding="utf-8")); n = T["nombre"]
    var = {}
    for p in sorted(glob.glob(os.path.join(sal, "res_*.json"))):
        r = json.load(open(p, encoding="utf-8"))
        var[r["tag"]] = {k: r.get(k) for k in ("estado", "t_total", "t_sim", "s_por_cuadro", "error") if r.get(k) is not None}
    faltan = [v["tag"] for v in T["variantes"] if v["tag"] not in var]
    met = {}
    for p in sorted(glob.glob(os.path.join(sal, "datos", "*.json"))):
        d = reducir(json.load(open(p, encoding="utf-8")))
        d["salida"] = n   # sin rutas de la maquina
        met[os.path.basename(p)] = d
    ok = est_correr == "success" and not faltan and all(v.get("estado") == "FIN" for v in var.values()) and est_metricas in ("success", "skipped")
    R = dict(firma="[ESC·f535]", tanda=n, estado="ok" if ok else "fallo", quien=quien, fin_trabajo=ahora(),
             estado_correr=est_correr, estado_metricas=est_metricas, t_blender_s=t_blender, n_variantes=len(T["variantes"]),
             faltan=faltan, variantes=var, metricas=met, maquina=maquina())
    if not ok:
        log = os.path.join(os.path.dirname(os.path.abspath(sal)), f"{n}.log")
        if os.path.isfile(log):
            R["log_cola"] = open(log, encoding="utf-8", errors="replace").read().splitlines()[-25:]
    txt = json.dumps(R, ensure_ascii=False, indent=1)
    if len(txt.encode()) > LIMITE_RESUMEN:
        R["metricas"] = {k: {"banda": v.get("banda"), "nota": "recortado: ver artifact"} for k, v in met.items()}
        txt = json.dumps(R, ensure_ascii=False, indent=1)
    print(sanear(txt))


def sanear(txt):
    """El resumen va a un repo publico: sin rutas de la maquina (repo -> <repo>, home -> ~, otros /home/x -> ~)."""
    for a, b in ((RAIZ, "<repo>"), (RAIZ.replace("\\", "\\\\"), "<repo>"), (os.path.expanduser("~"), "~")):
        txt = txt.replace(a, b)
    return re.sub(r"/home/[A-Za-z0-9_.-]+", "~", txt)


def maquina():
    m = {"nproc": os.cpu_count()}
    try:
        m["cpu"] = next(l.split(":", 1)[1].strip() for l in open("/proc/cpuinfo") if l.startswith("model name"))
    except Exception:
        pass
    return m


# ---------- cerrar ----------
def cerrar(resumenes, tandas, url):
    os.makedirs(os.path.join(RAIZ, "resultados"), exist_ok=True)
    for d in ("hecho", "fallo"):
        os.makedirs(os.path.join(RAIZ, d), exist_ok=True)
    for t in tandas:
        p = os.path.join(resumenes, f"{t}.json")
        R = json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else dict(firma="[ESC·f535]", tanda=t, estado="fallo", nota="el trabajo no dejo resumen (cancelado o se cayo el runner)")
        quien, tomada = leer_quien(os.path.join(RAIZ, "tomadas", f"{t}.quien"))
        enc = ""
        try:
            enc = open(os.path.join(RAIZ, "tomadas", f"{t}.quien"), encoding="utf-8").read().split("encolada ")[1].strip()
        except Exception:
            pass
        R.update(tomada=tomada.isoformat(), encolada=enc, cerrada=ahora(), corrida=url)
        if enc:
            R["t_cola_a_resultado_s"] = int((dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(enc)).total_seconds())
        json.dump(R, open(os.path.join(RAIZ, "resultados", f"{t}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        destino = "hecho" if R.get("estado") == "ok" else "fallo"
        if os.path.isfile(os.path.join(RAIZ, "tomadas", f"{t}.json")):
            git("mv", "-f", f"tomadas/{t}.json", f"{destino}/{t}.json")
        git("rm", "-q", "-f", "--ignore-unmatch", f"tomadas/{t}.quien")
        git("add", f"resultados/{t}.json")
        print(f"{t}: {R.get('estado')} -> {destino}/")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="c", required=True)
    a = sp.add_parser("validar"); a.add_argument("tanda"); a.add_argument("--raiz", default=RAIZ)
    a = sp.add_parser("tomar"); a.add_argument("--quien", required=True); a.add_argument("--max", type=int, default=20)
    a.add_argument("--donde", default="actions"); a.add_argument("--viejas-h", type=float, default=6)
    a = sp.add_parser("metricas"); a.add_argument("tanda"); a.add_argument("sal")
    a = sp.add_parser("resumir"); a.add_argument("tanda"); a.add_argument("sal"); a.add_argument("--estado-correr", default="success")
    a.add_argument("--estado-metricas", default="success"); a.add_argument("--quien", default="?"); a.add_argument("--t-blender", type=float, default=None)
    a = sp.add_parser("cerrar"); a.add_argument("--resumenes", required=True); a.add_argument("--tandas", required=True); a.add_argument("--url", default="")
    A = ap.parse_args()
    if A.c == "validar":
        T = json.load(open(A.tanda, encoding="utf-8")); err = validar(T, A.raiz)
        print("\n".join(err) if err else "ok"); sys.exit(1 if err else 0)
    if A.c == "tomar":
        tomar(A.quien, A.max, A.donde, A.viejas_h)
    if A.c == "metricas":
        sys.exit(correr_metricas(A.tanda, A.sal))
    if A.c == "resumir":
        resumir(A.tanda, A.sal, A.estado_correr, A.estado_metricas, A.quien, A.t_blender)
    if A.c == "cerrar":
        cerrar(A.resumenes, json.loads(A.tandas), A.url)


if __name__ == "__main__":
    main()
