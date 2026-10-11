"""REGISTRO DE CORRIDAS (paso 1 de ARQUITECTURA.md): un MANIFEST por corrida, reconstruido de lo que ya hay en disco, y
`comparables`, que dice SI/NO a "¿puedo comparar la corrida A contra la B?" con el motivo.

Fuentes (todas en etapa2/ o en la carpeta _qc_* de la corrida): sim_<tag>.log (linea 1 = `params`), estado_<tag>.txt (la linea de
tokens y la hora), corre_<tag>.out (compuertas), run_<tag>.txt (version de Blender), compuerta_humo_<tag>.out (base de comparacion),
_qc_*/cadena_<tag>.out (exentas y control). Lo que NO esta escrito en ningun lado se dice "desconocido": no se inventa.

Identidad del codigo del simulador (la parte dificil): sim_e2s.py no tiene historia git (91 archivos sin commit). Se usa lo unico que
hay: el archivo actual + las copias `_papelera/sim_e2s_pre_<x>.py` que se sacan A MANO justo antes de cada edicion. Cada copia dice
"este contenido estaba vivo hasta la hora en que se copio"; si conserva la fecha de modificacion original, tambien desde cuando.
Una corrida cuya ventana cae dentro de una de esas ventanas queda `verificado` (ventana exacta) o `inferido` (ventana entre copias
consecutivas); si ninguna copia la cubre queda `desconocido`, y se dice cuales ediciones conocidas ocurrieron despues.

Uso: python -m prenda3d.registro reconstruir <tag>... | listar | comparables <tagA> <tagB> [--distinto-cuerpo MOTIVO] [--distinto-codigo MOTIVO]
"""
from __future__ import annotations

import ast
import glob
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from . import receta as RC

AQUI = os.path.dirname(os.path.abspath(__file__))
PAQUETE = os.path.dirname(AQUI)
DATOS = os.path.join(PAQUETE, "datos_m133")
CORRIDAS = os.path.join(DATOS, "corridas")
HUELLAS = os.path.join(DATOS, "huellas.json")
IDENT_CUERPO_CARPETAS = ("",)                    # el cuerpo (body=) y la malla (mesh=) son relativos a etapa2/


# ------------------------------------------------------------------ utilidades
def sha256(ruta: str) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts).isoformat(timespec="seconds")


def _ts(iso: str) -> float:
    return datetime.fromisoformat(iso).timestamp()


def _leer(ruta: str) -> str:
    with open(ruta, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _creado(ruta: str) -> float:
    s = os.stat(ruta)
    return getattr(s, "st_birthtime", None) or s.st_ctime          # en Windows st_ctime (py < 3.12) es la fecha de creacion


def ubicar(tag: str, raiz: str) -> dict:
    """Donde estan los archivos de la corrida: etapa2/ o la primera _qc_*/ que tenga sim_/estado_/corre_ de ese tag."""
    carpetas = [raiz] + sorted(glob.glob(os.path.join(raiz, "_qc_*")))
    for ancla in (f"sim_{tag}.log", f"estado_{tag}.txt", f"corre_{tag}.out"):
        for c in carpetas:
            if os.path.isfile(os.path.join(c, ancla)):
                f = {}
                for clave, nombre in (("sim_log", f"sim_{tag}.log"), ("estado", f"estado_{tag}.txt"), ("corre", f"corre_{tag}.out"),
                                      ("run", f"run_{tag}.txt"), ("compuerta_humo", f"compuerta_humo_{tag}.out"),
                                      ("final", f"final_{tag}.json")):
                    for d in (c, raiz):
                        if os.path.isfile(os.path.join(d, nombre)):
                            f[clave] = os.path.join(d, nombre)
                            break
                for d in carpetas:
                    p = os.path.join(d, f"cadena_{tag}.out")
                    if os.path.isfile(p):
                        f["cadena"] = p
                f["carpeta"] = c
                return f
    return {}


# ------------------------------------------------------------------ parseo de lo que dejan las corridas
def leer_estado(ruta: str) -> dict:
    """estado_<tag>.txt: 'sim T lanzada HH:MM:SS :: [SONDA ... ::] <tokens>' / 'winpid N' / 'sim T FIN HH:MM:SS' o 'SIN FIN'."""
    txt = _leer(ruta).splitlines()
    partes = txt[0].split(" :: ")
    m = re.match(r"sim (\S+) lanzada (\d\d:\d\d:\d\d)", partes[0])
    out = {"tag": m.group(1) if m else None, "lanzada": m.group(2) if m else None, "tokens": partes[-1].strip(),
           "sonda": partes[1] if len(partes) > 2 else None, "winpid": None, "resultado": None, "hora_fin": None,
           "mtime": os.path.getmtime(ruta)}
    for ln in txt[1:]:
        if ln.startswith("winpid"):
            out["winpid"] = int(ln.split()[1])
        mm = re.match(r"sim \S+ (FIN|SIN FIN) (\d\d:\d\d:\d\d)", ln)
        if mm:
            out["resultado"], out["hora_fin"] = mm.group(1).replace(" ", "_"), mm.group(2)
    return out


def base_de_lanzador(ruta: str) -> str:
    """El BASE="..." de un lanza_*.sh / lanzar_*.sh (los tokens que se anteponen a toda corrida)."""
    m = re.search(r'^BASE="([^"]*)"', _leer(ruta), re.M)
    if not m:
        raise RC.RecetaError(f"{ruta}: no encontre BASE=\"...\"")
    return m.group(1)


def leer_sim_log(ruta: str) -> dict:
    params, frames = RC.params_de_log(ruta)
    out = {"params": params, "frames": frames, "malla": None, "cuerpo": None, "stop": None, "t_sim_s": None, "t_total_s": None, "fin": False}
    for ln in _leer(ruta).splitlines():
        if ln.startswith("malla ") and not out["malla"]:
            out["malla"] = ln.split(None, 1)[1].strip()
        m = re.match(r"cuerpo (\S+\.npz):", ln)
        if m and not out["cuerpo"]:
            out["cuerpo"] = m.group(1)
        if ln.startswith("STOP") and not out["stop"]:
            out["stop"] = ln[:200]
        m = re.match(r"(t sim|fin) (\d+(?:\.\d+)?)\s*$", ln)
        if m:
            if m.group(1) == "fin":
                out["fin"], out["t_total_s"] = True, float(m.group(2))
            else:
                out["t_sim_s"] = float(m.group(2))
    return out


def leer_corre(ruta: str) -> dict:
    out = {"arranque": None, "humo": None, "tokens_inicio": None, "motivo_corte": None}
    for ln in _leer(ruta).splitlines():
        m = re.match(r"\S+ INICIO \S+ :: (.*)$", ln)
        if m and out["tokens_inicio"] is None:
            out["tokens_inicio"] = m.group(1).strip()
        m = re.match(r"\S+ COMPUERTA (ARRANQUE|HUMO) (PASA|FALLA)\b(.*)$", ln)
        if m:
            out[m.group(1).lower()] = (m.group(2) + m.group(3)).strip()
            if m.group(2) == "FALLA":
                out["motivo_corte"] = ln.split(" ", 1)[1][:400]
        if "SIM CORTADA POR LA GUARDA" in ln:
            out["motivo_corte"] = ln.split(" ", 1)[1][:300]
    return out


def leer_blender(ruta: str | None) -> dict:
    if ruta and os.path.isfile(ruta):
        m = re.search(r"Blender (\d+\.\d+(?:\.\d+)?) \(hash (\w+)", _leer(ruta))
        if m:
            return {"version": m.group(1), "hash": m.group(2), "fuente": os.path.basename(ruta)}
    return {"version": None, "hash": None, "fuente": "desconocido (no hay run_<tag>.txt con la cabecera de Blender)"}


def leer_hilos(tag: str, raiz: str, carpeta: str, estado: dict | None) -> dict:
    """-t de Blender. Si la carpeta tiene humos.log lo dice por corrida; si no, se DEDUCE del lanzador que usaba esa familia."""
    hl = os.path.join(carpeta, "humos.log")
    if os.path.isfile(hl):
        m = re.search(rf"INICIO humo {re.escape(tag)} \(\d+ cuadros, -t (\d+)", _leer(hl))
        if m:
            return {"valor": int(m.group(1)), "fuente": "humos.log"}
    if estado and estado.get("sonda"):                     # familia lanza_w.sh: la cadena la llama con `... 240 6`
        cw = os.path.join(raiz, "_qc_e2zw", "corre_e2zw.sh")
        if os.path.isfile(cw):
            m = re.search(r'lanza_w\.sh\s+"?\$T"?\s+\d+\s+(\d+)', _leer(cw))
            if m:
                return {"valor": int(m.group(1)), "fuente": "deducido de _qc_e2zw/corre_e2zw.sh (hoy dice -t " + m.group(1) + "); la corrida no lo registro"}
    return {"valor": None, "fuente": "desconocido (la corrida no lo registro y no se sabe que lanzador la arranco)"}


def leer_base_comparacion(tag: str, f: dict) -> dict:
    out = {"humo_control": [], "humo_candidato": None, "autocomparacion": False, "control_cadena": None, "exentas": [], "fuente": []}
    if f.get("compuerta_humo"):
        ln = _leer(f["compuerta_humo"]).splitlines()[0]
        m = re.match(r"COMPUERTA HUMO (\S+) \((\S+)\) contra (.+?)( \||$)", ln)
        if m:
            out["humo_candidato"] = m.group(1)
            out["humo_control"] = [x.strip() for x in m.group(3).split(",")]
            out["autocomparacion"] = m.group(1) in out["humo_control"]
            out["fuente"].append(os.path.basename(f["compuerta_humo"]))
        m = re.search(r"exentas[^:]*: \[(.*?)\]", ln)
        if m:
            out["exentas"] = re.findall(r"'([^']+)'", m.group(1))
    if f.get("cadena"):
        ln = _leer(f["cadena"]).splitlines()[0]
        m = re.search(r"control del humo (\S+)", ln)
        out["control_cadena"] = m.group(1) if m else None
        m = re.search(r"exentas \[(.*?)\]", ln)
        if m and not out["exentas"]:
            out["exentas"] = [x for x in m.group(1).split(",") if x]
        out["fuente"].append(os.path.basename(f["cadena"]))
    if not out["fuente"]:
        out["nota"] = "ningun archivo de la corrida dice contra que base se comparo"
    return out


# ------------------------------------------------------------------ identidad del codigo del simulador
def versiones_simulador(raiz: str) -> list:
    """Archivo actual + copias _papelera/**/sim_e2s_pre_*.py, cada una con su ventana de vida (ver docstring del modulo)."""
    actual = os.path.join(raiz, "sim_e2s.py")
    copias = sorted(glob.glob(os.path.join(raiz, "_papelera", "sim_e2s_pre_*.py")) + glob.glob(os.path.join(raiz, "_papelera", "*", "sim_e2s_pre_*.py")),
                    key=_creado)
    vs, previo = [], None
    for c in copias:
        mt, cr = os.path.getmtime(c), _creado(c)
        exacto = mt < cr - 2                              # conserva la fecha de modificacion original: se sabe desde cuando
        vs.append({"archivo": os.path.relpath(c, raiz).replace(os.sep, "/"), "ruta": c, "sha256": sha256(c), "mtime": mt, "creado": cr,
                   "lo": mt if exacto else (previo if previo is not None else float("-inf")), "hi": cr, "exacto": exacto, "actual": False})
        previo = cr
    if os.path.isfile(actual):
        vs.append({"archivo": "sim_e2s.py", "ruta": actual, "sha256": sha256(actual), "mtime": os.path.getmtime(actual), "creado": _creado(actual),
                   "lo": os.path.getmtime(actual), "hi": float("inf"), "exacto": True, "actual": True})
    return vs


def instantes_cambio(versiones: list) -> list:
    """Horas en que se sabe que el contenido del simulador cambio: cada copia (la edicion viene justo despues) y cada fecha
    de modificacion conservada."""
    s = set()
    for v in versiones:
        if not v["actual"]:
            s.add(v["creado"])
        if v["exacto"]:
            s.add(v["lo"])
    return sorted(s)


def identificar_codigo(versiones: list, ini: float, fin: float, claves_run: set | None = None) -> dict:
    cand = [v for v in versiones if v["lo"] <= ini and fin <= v["hi"]]
    cand.sort(key=lambda v: (not v["exacto"], v["hi"] - v["lo"]))
    firma = hashlib.sha256(",".join(sorted(claves_run)).encode()).hexdigest()[:12] if claves_run else None
    res = {"estado": "desconocido", "archivo": None, "sha256": None, "es_el_actual": False, "firma_claves": firma, "motivo": None}
    if not cand:
        despues = [t for t in instantes_cambio(versiones) if t > ini]
        res["motivo"] = ("ninguna copia de sim_e2s.py cubre la ventana de la corrida"
                         + (f"; primera edicion conocida despues: {_iso(despues[0])}" if despues else ""))
        return res
    v = cand[0]
    res.update(archivo=v["archivo"], sha256=v["sha256"], es_el_actual=v["actual"])
    if claves_run is not None:                            # control cruzado: las claves del log tienen que ser las de ESA version
        try:
            sp = RC.leer_parametros_sim(v["ruta"])
            if not set(sp.defectos) <= set(claves_run) or not (set(claves_run) - set(sp.defectos)) <= set(sp.ocultas):
                res.update(estado="desconocido", sha256=None, archivo=None, es_el_actual=False,
                           motivo=f"la ventana apunta a {v['archivo']} pero las claves del log no coinciden con las de esa version "
                                  f"(faltan {sorted(set(sp.defectos) - set(claves_run))[:5]}, sobran {sorted(set(claves_run) - set(sp.defectos) - set(sp.ocultas))[:5]})")
                return res
        except Exception as e:                            # noqa: BLE001 - una copia ilegible no tumba el manifest
            res["motivo"] = f"no pude leer las claves de {v['archivo']}: {e}"
    res["estado"] = "verificado" if v["exacto"] else "inferido"
    res["motivo"] = res["motivo"] or ("ventana exacta (fecha de modificacion conservada)" if v["exacto"] else "ventana entre copias consecutivas; "
                                      "no descarta una edicion sin copia en el medio")
    return res


# ------------------------------------------------------------------ reconstruir un manifest
def _archivo(raiz: str, nombre: str | None, inicio: float | None, que: str) -> dict:
    if not nombre:
        return {"archivo": None, "sha256": None, "motivo": f"desconocido: ni el log ni los tokens dicen que {que} uso"}
    p = os.path.join(raiz, nombre)
    if not os.path.isfile(p):
        return {"archivo": nombre, "sha256": None, "motivo": "el archivo ya no esta en etapa2/"}
    mt = os.path.getmtime(p)
    d = {"archivo": nombre, "bytes": os.path.getsize(p), "sha256": sha256(p), "mtime": _iso(mt), "verificable": True}
    if inicio is not None and mt > inicio:
        d["verificable"] = False
        d["motivo"] = f"el archivo se modifico ({_iso(mt)}) DESPUES del inicio de la corrida: su sha256 no identifica lo que se uso"
    return d


def _tokens_a_params(tokens: str, base: str | None, sp) -> tuple:
    r = RC.desde_tokens((base + " " if base else "") + tokens, sp)
    return r, r.completo(sp)


def reconstruir(tag: str, raiz: str | None = None, versiones: list | None = None) -> dict:
    raiz = RC.etapa2(raiz)
    f = ubicar(tag, raiz)
    if not f:
        raise FileNotFoundError(f"no hay sim_{tag}.log, estado_{tag}.txt ni corre_{tag}.out en {raiz} ni en sus _qc_*")
    carpeta = f["carpeta"]
    usados = [os.path.relpath(v, raiz).replace(os.sep, "/") for k, v in f.items() if k != "carpeta"]
    adv, sp = [], RC.leer_parametros_sim(os.path.join(raiz, "sim_e2s.py"))
    estado = leer_estado(f["estado"]) if "estado" in f else None
    corre = leer_corre(f["corre"]) if "corre" in f else None
    log = leer_sim_log(f["sim_log"]) if "sim_log" in f else None

    # --- cuando
    inicio = fin = None
    if estado and estado["lanzada"]:
        fin_ts = estado["mtime"]
        dfin = datetime.fromtimestamp(fin_ts)
        h = datetime.strptime(estado["lanzada"], "%H:%M:%S").time()
        ini = datetime.combine(dfin.date(), h)
        if ini > dfin:
            ini -= timedelta(days=1)
        inicio, fin = ini.timestamp(), fin_ts
    elif "corre" in f:
        fin = inicio = os.path.getmtime(f["corre"])
        adv.append("sin estado_<tag>.txt: la hora es la de modificacion de corre_<tag>.out")

    # --- parametros
    tokens = estado["tokens"] if estado else (corre or {}).get("tokens_inicio")
    base_lanz = None
    if (estado and estado.get("sonda") is not None) or (not estado and corre):
        cand = os.path.join(raiz, "_qc_e2zw", "lanza_w.sh")
        base_lanz = base_de_lanzador(cand) if os.path.isfile(cand) else None
        if base_lanz and not estado:
            adv.append("BASE tomada del _qc_e2zw/lanza_w.sh actual (la corrida no llego a escribir estado_<tag>.txt)")
    parametros, fuente_par, coincide = None, None, None
    if log:
        parametros, fuente_par = log["params"], f"{os.path.basename(f['sim_log'])} linea 1"
        if tokens:
            try:
                r = RC.desde_tokens(tokens, sp)               # la linea de estado ya trae BASE + resto; gana el ultimo valor
                dif = {k: (parametros.get(k), v) for k, v in r.params.items() if k in parametros and float(parametros[k]) != float(v)}
                ausentes = sorted(k for k in r.params if k not in parametros)
                coincide = {"igual": not dif and not ausentes, "difieren": dif, "tokens_ausentes_en_log": ausentes,
                            "claves_en_tokens": len(r.params), "claves_repetidas_en_tokens": len(r.repetidas)}
            except RC.RecetaError as e:
                coincide = {"igual": False, "error": str(e)}
    elif tokens:
        try:
            r, parametros = _tokens_a_params(tokens, base_lanz, sp)
            fuente_par = "RESUELTO de los tokens de corre_<tag>.out (no hubo sim_<tag>.log: la corrida no llego a lanzar Blender)"
            if not base_lanz:
                adv.append("sin BASE del lanzador: los parametros resueltos pueden estar incompletos")
            tokens = (base_lanz + " " if base_lanz else "") + tokens
        except RC.RecetaError as e:
            adv.append(f"no pude resolver los tokens: {e}")
    especiales = {}
    if tokens:
        try:
            rr = RC.desde_tokens(tokens, sp)
            especiales = {k: v for k, v in rr.especiales.items()}
        except RC.RecetaError:
            pass

    # --- malla / cuerpo
    nm = (log or {}).get("malla") or especiales.get("malla")
    nc = (log or {}).get("cuerpo") or especiales.get("cuerpo")
    malla = _archivo(raiz, nm, inicio, "malla")
    cuerpo = _archivo(raiz, nc, inicio, "cuerpo")
    if nc is None and log:
        cuerpo["motivo"] = "desconocido: la corrida no uso body= (cuerpo del maniqui por defecto, no un npz)"

    # --- estado
    if not log:
        est, motivo = "NO_LANZADA", (corre or {}).get("motivo_corte") or "no hay sim_<tag>.log"
    elif log["stop"]:
        est, motivo = "STOP", log["stop"]
    elif estado and estado["resultado"] == "FIN" and log["fin"]:
        est, motivo = "FIN", None
    elif estado and estado["resultado"] == "SIN_FIN":
        est, motivo = "SIN_FIN", "estado dice SIN FIN"
    else:
        est, motivo = "DESCONOCIDO", "el log no termina en `fin` y el estado no dice FIN"

    # --- codigo
    if versiones is None:
        versiones = versiones_simulador(raiz)
    if log and inicio:
        codigo = identificar_codigo(versiones, inicio, fin, set(log["params"]))
    else:
        codigo = {"estado": "no_aplica", "motivo": "la corrida no llego a correr el simulador", "sha256": None, "archivo": None,
                  "es_el_actual": False, "firma_claves": None}
    actual = next((v for v in versiones if v["actual"]), None)
    if actual:
        codigo["sim_actual_sha256"] = actual["sha256"]
        codigo["sim_actual_mtime"] = _iso(actual["mtime"])
        codigo["modificado_despues_de_la_corrida"] = bool(fin and actual["mtime"] > fin)
        if codigo["modificado_despues_de_la_corrida"]:
            adv.append(f"sim_e2s.py se modifico ({_iso(actual['mtime'])}) DESPUES de esta corrida: el sha actual no es el que corrio")
    huellas_sim = None
    if os.path.isfile(HUELLAS):
        for a in json.load(open(HUELLAS, encoding="utf-8")).get("archivos", []):
            if a["ruta"].endswith("sim_e2s.py") and "_papelera" not in a["ruta"]:
                huellas_sim = a["sha256"]
    codigo["huella_sim_sha256"] = huellas_sim
    codigo["coincide_con_huella"] = (codigo["sha256"] == huellas_sim) if codigo.get("sha256") and huellas_sim else None
    codigo["instantes_de_cambio_conocidos"] = [_iso(t) for t in instantes_cambio(versiones)]

    salidas = {}
    for k in ("sim_log", "final"):
        if k in f:
            salidas[os.path.basename(f[k])] = {"bytes": os.path.getsize(f[k]), "sha256": sha256(f[k])}
    m = {"version": 1, "tag": tag, "reconstruido": _iso(datetime.now().timestamp()), "reconstruido_de": sorted(usados),
         "raiz_etapa2": raiz, "carpeta": os.path.relpath(carpeta, raiz).replace(os.sep, "/") if carpeta != raiz else ".",
         "estado": est, "motivo_estado": motivo,
         "inicio": _iso(inicio) if inicio else None, "fin": _iso(fin) if fin else None,
         "duracion_s": round(fin - inicio) if inicio and fin else None, "frames": (log or {}).get("frames"),
         "t_sim_blender_s": (log or {}).get("t_sim_s"), "t_total_blender_s": (log or {}).get("t_total_s"),
         "parametros": parametros, "parametros_fuente": fuente_par,
         "parametros_vs_tokens": coincide, "tokens": tokens, "especiales": especiales,
         "receta_hash": RC.hash_params(parametros) if parametros else None,
         "malla": malla, "cuerpo": cuerpo, "hilos": leer_hilos(tag, raiz, carpeta, estado),
         "blender": leer_blender(f.get("run")), "codigo": codigo,
         "compuertas": {"arranque": (corre or {}).get("arranque"), "humo": (corre or {}).get("humo")},
         "base_comparacion": leer_base_comparacion(tag, f), "salidas": salidas, "advertencias": adv}
    m["id"] = id_corrida(m)
    return m


def id_corrida(m: dict) -> str:
    """Hash corto de (malla, cuerpo, receta resuelta, codigo): mismas entradas = mismo id."""
    c = m["codigo"]
    clave = [(m["malla"] or {}).get("sha256"), (m["cuerpo"] or {}).get("sha256"), m.get("receta_hash"),
             c.get("sha256") or ("firma:" + str(c.get("firma_claves"))), m.get("frames"), json.dumps(m.get("especiales", {}).get("dumps"))]
    return hashlib.sha256(json.dumps(clave).encode()).hexdigest()[:12]


def escribir(m: dict, carpeta: str | None = None) -> str:
    carpeta = carpeta or CORRIDAS
    os.makedirs(carpeta, exist_ok=True)
    p = os.path.join(carpeta, m["tag"] + ".json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(m, fh, ensure_ascii=False, indent=1)
    return p


def cargar_manifest(ref: str, carpeta: str | None = None) -> dict:
    """ref = ruta de un manifest o un tag guardado en corridas/."""
    p = ref if os.path.isfile(ref) else os.path.join(carpeta or CORRIDAS, ref + ".json")
    if not os.path.isfile(p):
        raise FileNotFoundError(f"no hay manifest para '{ref}' (busque {p}); reconstruirlo con `registro reconstruir {ref}`")
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


# ------------------------------------------------------------------ comparables
@dataclass
class Comparacion:
    a: str
    b: str
    comparable: bool
    motivos: list = field(default_factory=list)          # por que NO (o, si es SI, que se declaro)
    reservas: list = field(default_factory=list)
    dimensiones: dict = field(default_factory=dict)
    params_difieren: dict = field(default_factory=dict)
    claves_solo: dict = field(default_factory=dict)
    declarados: list = field(default_factory=list)

    def texto(self) -> str:
        L = [("SI" if self.comparable else "NO") + f" comparables {self.a} vs {self.b}"]
        for k in ("cuerpo", "codigo", "malla"):
            L.append(f"  {k:7s} {self.dimensiones.get(k, '?')}")
        pd = self.params_difieren
        L.append(f"  params  {len(pd)} difieren" + (": " + ", ".join(f"{k} {v[0]}->{v[1]}" for k, v in list(pd.items())[:12]) + (" ..." if len(pd) > 12 else "") if pd else ""))
        for s, ks in self.claves_solo.items():
            if ks:
                L.append(f"  claves solo en {s}: {ks[:8]}{' ...' if len(ks) > 8 else ''}")
        for x in self.motivos:
            L.append("  MOTIVO: " + x)
        for x in self.declarados:
            L.append("  DECLARADO: " + x)
        for x in self.reservas:
            L.append("  RESERVA: " + x)
        return "\n".join(L)


def _dim_archivo(ma: dict, mb: dict, k: str) -> tuple:
    a, b = ma[k] or {}, mb[k] or {}
    sa, sb = a.get("sha256"), b.get("sha256")
    if not sa or not sb:
        quien = [t for t, x in ((ma["tag"], a), (mb["tag"], b)) if not x.get("sha256")]
        return "DESCONOCIDO", f"no se conoce el {k} de {', '.join(quien)} ({(a if not sa else b).get('motivo', 'sin hash')})"
    if not a.get("verificable", True) or not b.get("verificable", True):
        quien = [t for t, x in ((ma["tag"], a), (mb["tag"], b)) if not x.get("verificable", True)]
        return "DESCONOCIDO", f"el {k} de {', '.join(quien)} se modifico despues de la corrida: el hash no prueba que sea el que se uso"
    if sa == sb:
        return "IGUAL", None
    return "DISTINTO", f"{a.get('archivo')} ({sa[:10]}) != {b.get('archivo')} ({sb[:10]})"


def _dim_codigo(ma: dict, mb: dict) -> tuple:
    ca, cb = ma["codigo"], mb["codigo"]
    if ca.get("estado") == "no_aplica" or cb.get("estado") == "no_aplica":
        return "DESCONOCIDO", "una de las corridas no llego a correr el simulador"
    if ca.get("sha256") and cb.get("sha256"):
        if ca["sha256"] == cb["sha256"]:
            return ("IGUAL" if "inferido" not in (ca["estado"], cb["estado"]) else "IGUAL_INFERIDO"), None
        return "DISTINTO", f"sim_e2s.py distinto: {ma['tag']} usa {ca['archivo']} ({ca['sha256'][:10]}), {mb['tag']} usa {cb['archivo']} ({cb['sha256'][:10]})"
    fa, fb = ca.get("firma_claves"), cb.get("firma_claves")
    if fa and fb and fa != fb:
        pa, pb = set(ma["parametros"] or ()), set(mb["parametros"] or ())
        return "DISTINTO", (f"el simulador de una corrida tenia otro conjunto de parametros (solo en {ma['tag']}: {sorted(pa - pb)[:6]}; "
                            f"solo en {mb['tag']}: {sorted(pb - pa)[:6]})")
    t0, t1 = sorted((_ts(ma["inicio"]), _ts(mb["inicio"])))
    entre = [t for t in (_ts(x) for x in ca.get("instantes_de_cambio_conocidos", [])) if t0 < t <= t1]
    if entre:
        return "DISTINTO", f"sim_e2s.py se edito el {_iso(entre[0])}, entre las dos corridas (no se puede probar que sea el mismo codigo)"
    quien = [m["tag"] for m in (ma, mb) if not m["codigo"].get("sha256")]
    return "IGUAL_INFERIDO", (f"el codigo de {', '.join(quien)} no se pudo identificar con una copia; se infiere igual porque "
                              f"las claves coinciden y no hay ediciones conocidas entre las dos corridas")


def comparables(ma: dict, mb: dict, distinto_cuerpo: str | None = None, distinto_codigo: str | None = None) -> Comparacion:
    """SI/NO. NO si alguna no corrio, si el cuerpo difiere o no se conoce, o si el codigo difiere (salvo que se DECLARE con motivo).
    La malla y los parametros pueden diferir (es lo que se prueba) pero se listan."""
    c = Comparacion(ma["tag"], mb["tag"], True)
    for m in (ma, mb):
        if m["estado"] == "NO_LANZADA":
            c.comparable = False
            c.motivos.append(f"{m['tag']} no corrio el simulador ({m['motivo_estado']})")
    if not c.comparable:
        c.dimensiones = {"cuerpo": "-", "codigo": "-", "malla": "-"}
        return c
    dc, mc = _dim_archivo(ma, mb, "cuerpo")
    dk, mk = _dim_codigo(ma, mb)
    dm, mm = _dim_archivo(ma, mb, "malla")
    c.dimensiones = {"cuerpo": dc + (f" ({mc})" if mc else ""), "codigo": dk + (f" ({mk})" if mk else ""), "malla": dm + (f" ({mm})" if mm else "")}
    if dc != "IGUAL":
        if distinto_cuerpo:
            c.declarados.append(f"cuerpo distinto/desconocido, declarado: {distinto_cuerpo}")
        else:
            c.comparable = False
            c.motivos.append(f"cuerpo {dc.lower()}: {mc}. Para compararlas igual hay que declararlo (--distinto-cuerpo MOTIVO)")
    if dk == "DISTINTO" or dk == "DESCONOCIDO":
        if distinto_codigo:
            c.declarados.append(f"codigo distinto/desconocido, declarado: {distinto_codigo}")
        else:
            c.comparable = False
            c.motivos.append(f"codigo {dk.lower()}: {mk}. Para compararlas igual hay que declararlo (--distinto-codigo MOTIVO)")
    elif dk == "IGUAL_INFERIDO":
        c.reservas.append(mk or "codigo igual solo por inferencia (alguna copia de sim_e2s.py no cubre la corrida)")
    if dm == "DESCONOCIDO":
        c.reservas.append(f"malla: {mm}")
    pa, pb = ma["parametros"] or {}, mb["parametros"] or {}
    c.params_difieren = {k: (pa[k], pb[k]) for k in sorted(set(pa) & set(pb)) if float(pa[k]) != float(pb[k])}
    if ma.get("frames") != mb.get("frames"):
        c.params_difieren["<frames>"] = (ma.get("frames"), mb.get("frames"))
    c.claves_solo = {ma["tag"]: sorted(set(pa) - set(pb)), mb["tag"]: sorted(set(pb) - set(pa))}
    if dm == "DISTINTO" and c.params_difieren:
        c.reservas.append("cambian la malla Y parametros a la vez: dos variables en una comparacion")
    return c


# ------------------------------------------------------------------ CLI
def listar(carpeta: str | None = None) -> str:
    carpeta = carpeta or CORRIDAS
    L = [f"{'tag':10s} {'inicio':19s} {'estado':10s} {'malla':22s} {'cuerpo':20s} {'codigo':11s} hilos  blender  base humo"]
    for p in sorted(glob.glob(os.path.join(carpeta, "*.json"))):
        m = json.load(open(p, encoding="utf-8"))
        bc = m["base_comparacion"]
        L.append(f"{m['tag']:10s} {str(m['inicio'] or '?'):19s} {m['estado']:10s} {str((m['malla'] or {}).get('archivo')):22s} "
                 f"{str((m['cuerpo'] or {}).get('archivo')):20s} {m['codigo']['estado']:11s} {str(m['hilos']['valor'] or '?'):5s}  "
                 f"{str(m['blender']['version'] or '?'):7s}  {','.join(bc['humo_control']) or '-'}{' (CONTRA SI MISMA)' if bc['autocomparacion'] else ''}")
    return "\n".join(L)


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="python -m prenda3d.registro")
    ap.add_argument("--etapa2", help="carpeta etapa2/ (defecto: la de la M133)")
    ap.add_argument("--corridas", help=f"carpeta de manifests (defecto: {CORRIDAS})")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("reconstruir"),
    s[0].add_argument("tags", nargs="+"), s[0].add_argument("--sin-escribir", action="store_true")
    sub.add_parser("listar")
    s = sub.add_parser("comparables")
    s.add_argument("a"), s.add_argument("b")
    s.add_argument("--distinto-cuerpo", metavar="MOTIVO"), s.add_argument("--distinto-codigo", metavar="MOTIVO")
    ns = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if ns.cmd == "reconstruir":
        rc = 0
        raiz = RC.etapa2(ns.etapa2)
        vs = versiones_simulador(raiz)
        for t in ns.tags:
            try:
                m = reconstruir(t, raiz, vs)
            except FileNotFoundError as e:
                print(f"FALLA {t}: {e}")
                rc = 1
                continue
            ruta = "(no escrito)" if ns.sin_escribir else escribir(m, ns.corridas)
            print(f"{t}: {m['estado']} | malla {(m['malla'] or {}).get('archivo')} | cuerpo {(m['cuerpo'] or {}).get('archivo')} | codigo {m['codigo']['estado']} "
                  f"| id {m['id']} -> {ruta}")
            for a in m["advertencias"]:
                print("   AVISO " + a)
        return rc
    if ns.cmd == "listar":
        print(listar(ns.corridas))
        return 0
    try:
        c = comparables(cargar_manifest(ns.a, ns.corridas), cargar_manifest(ns.b, ns.corridas), ns.distinto_cuerpo, ns.distinto_codigo)
    except FileNotFoundError as e:
        print(f"FALLA: {e}")
        return 2
    print(c.texto())
    return 0 if c.comparable else 1


if __name__ == "__main__":
    sys.exit(main())
