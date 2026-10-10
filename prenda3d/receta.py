"""RECETA COMO OBJETO (paso 2 de ARQUITECTURA.md): receta base + overrides -> dict plano de parametros `k=v` del simulador.

Hoy la receta es la suma de 4 strings (BASE de lanza_w.sh + QA de corre_e2zw.sh + A de la cadena + linea de la cola) y gana el
ultimo valor. Aca es un json con esquema (`receta.schema.json`), herencia de UN nivel (`base`) y claves VALIDADAS contra los
parametros reales de `sim_e2s.py` (se leen del codigo con `ast`, no de una lista copiada): una clave desconocida es ERROR.

Que sabe de `sim_e2s.py` (extraido del codigo, no escrito a mano):
  * defectos      el dict `P = dict(...)` del modulo (nombre -> valor por defecto);
  * ocultas       claves que el codigo lee con `P.get("k", d)` o `P["k"]` pero que NO estan en ese dict (`sa_brd`, `tilt`, `tiltf`);
  * especiales    las que el bucle de argv trata aparte (`mesh body rk wini pramp pfit dumps`): no entran en `P`;
  * muertas       en el dict y NUNCA leidas (hoy `arm_gap`); advertencia, no error: el simulador las acepta y no hacen nada;
  * una_vez       leidas en una sola linea (flags de un experimento).
Uso: python -m prenda3d.receta claves | validar R.json | resolver R.json [--tokens|--json] | probar R.json sim_<tag>.log
                               | importar --estado estado_<tag>.txt --base-lanzador lanza_w.sh --nombre T -o R.json
"""
from __future__ import annotations

import ast
import difflib
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field

AQUI = os.path.dirname(os.path.abspath(__file__))
PAQUETE = os.path.dirname(AQUI)                        # Diseño/prenda3d
ESQUEMA = os.path.join(PAQUETE, "receta.schema.json")
ETAPA2_DEFECTO = PAQUETE

# flags de diagnostico (ARQUITECTURA.md 3): no son construccion ni fisica; si una receta los usa se declaran en `diagnostico`
DIAGNOSTICO = ("notp", "snaps", "tp_nocol")


class RecetaError(ValueError):
    """Receta invalida: clave desconocida, token mal formado, herencia de mas de un nivel, forma que no cumple el esquema."""


def etapa2(ruta: str | None = None) -> str:
    return os.path.abspath(ruta or os.environ.get("PRENDA3D_ETAPA2") or ETAPA2_DEFECTO)


# ------------------------------------------------------------------ lo que acepta sim_e2s.py (leido del codigo)
@dataclass
class ParametrosSim:
    ruta: str
    defectos: dict                                      # clave -> defecto (las del dict P)
    ocultas: dict                                       # clave -> defecto de P.get (None si se lee con P["k"] sin defecto)
    especiales: tuple                                   # claves con tratamiento propio en el bucle de argv
    lecturas: dict = field(default_factory=dict)        # clave -> cantidad de LINEAS que la leen
    muertas: list = field(default_factory=list)
    una_vez: list = field(default_factory=list)

    @property
    def validas(self) -> set:
        return set(self.defectos) | set(self.ocultas)

    def defecto(self, k: str):
        return self.defectos[k] if k in self.defectos else self.ocultas.get(k)

    def clasificar(self, k: str) -> str:
        if k in self.especiales:
            return "especial"
        if k in self.muertas:
            return "muerta"
        if k in DIAGNOSTICO:
            return "diagnostico"
        if k in self.una_vez:
            return "una_vez"
        return "oculta" if k in self.ocultas else "normal"


_cache_sim: dict = {}


def leer_parametros_sim(ruta: str | None = None) -> ParametrosSim:
    """Extrae del codigo de sim_e2s.py: defectos, ocultas, especiales, lecturas. Sin importar bpy."""
    ruta = ruta or os.path.join(etapa2(), "sim_e2s.py")
    k = (ruta, os.path.getmtime(ruta))
    if k in _cache_sim:
        return _cache_sim[k]
    with open(ruta, encoding="utf-8") as fh:
        src = fh.read()
    arbol = ast.parse(src)
    defectos, especiales = None, []
    for n in arbol.body:
        if isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "P" for t in n.targets) \
                and isinstance(n.value, ast.Call) and getattr(n.value.func, "id", None) == "dict":
            defectos = {kw.arg: ast.literal_eval(kw.value) for kw in n.value.keywords}
        if isinstance(n, ast.For) and "argv" in ast.dump(n.iter):          # el bucle `for kv in argv[2:]`
            for m in ast.walk(n):
                if isinstance(m, ast.Compare) and isinstance(m.left, ast.Name) and m.left.id == "k" \
                        and isinstance(m.comparators[0], ast.Constant) and isinstance(m.comparators[0].value, str):
                    especiales.append(m.comparators[0].value)
    if defectos is None:
        raise RecetaError(f"{ruta}: no encontre `P = dict(...)` en el nivel del modulo")
    lineas = src.split("\n")
    leidas: dict = {}
    for k_, pat in (("get", re.compile(r"""P\.get\(\s*["'](\w+)["']\s*(?:,\s*([-+0-9.eE]+|None|True|False))?""")),
                    ("idx", re.compile(r"""P\[\s*["'](\w+)["']\s*\]"""))):
        for i, ln in enumerate(lineas, 1):
            for m in pat.finditer(ln):
                leidas.setdefault(m.group(1), {"lineas": set(), "defecto": ...})["lineas"].add(i)
                if k_ == "get" and m.lastindex and m.group(2) is not None:
                    leidas[m.group(1)]["defecto"] = ast.literal_eval(m.group(2))
    ocultas = {}
    for nombre, info in leidas.items():
        if nombre not in defectos:
            ocultas[nombre] = None if info["defecto"] is ... else info["defecto"]
    lect = {nombre: len(leidas[nombre]["lineas"]) if nombre in leidas else 0 for nombre in list(defectos) + list(ocultas)}
    sp = ParametrosSim(ruta, defectos, ocultas, tuple(especiales), lect,
                       muertas=sorted(k_ for k_ in defectos if lect[k_] == 0),
                       una_vez=sorted(k_ for k_ in defectos if lect[k_] == 1))
    _cache_sim.clear()
    _cache_sim[k] = sp
    return sp


# ------------------------------------------------------------------ tokens `k=v` (como los parte el bucle de argv del simulador)
def parsear_tokens(texto: str) -> list:
    """'a=1 b=2' -> [('a','1'), ('b','2')], en orden. El simulador hace `kv.split("=")`: un token sin '=' o con dos '=' lo rompe."""
    out = []
    for tok in str(texto).split():
        partes = tok.split("=")
        if len(partes) != 2 or not partes[0]:
            raise RecetaError(f"token mal formado '{tok}' (el simulador espera k=v con un solo '=')")
        out.append((partes[0], partes[1]))
    return out


def _numero(v):
    f = float(v)
    return int(f) if f == int(f) and "." not in str(v) and "e" not in str(v).lower() else f


@dataclass
class Resuelta:
    nombre: str
    params: dict                                        # solo lo que la receta fija (base + overrides), ultimo gana
    especiales: dict                                    # malla, cuerpo, dumps, rk... (no entran en P)
    frames: int | None = None
    repetidas: dict = field(default_factory=dict)       # clave -> [valores en orden] (solo al importar tokens)
    advertencias: list = field(default_factory=list)
    diagnostico: list = field(default_factory=list)
    base: str | None = None

    def completo(self, sp: ParametrosSim | None = None) -> dict:
        """Lo que imprime `params {...}` el simulador: defectos del codigo + lo que fija la receta (floats, como `float(v)`)."""
        sp = sp or leer_parametros_sim()
        d = dict(sp.defectos)
        d.update({k: float(v) for k, v in self.params.items()})
        return d

    def tokens(self) -> str:
        t = " ".join(f"{k}={_fmt(v)}" for k, v in self.params.items())
        e = self.especiales
        if e.get("dumps"):
            t += " dumps=" + ",".join(str(int(x)) for x in e["dumps"])
        for k in ("rk", "wini", "pramp", "pfit"):
            if e.get(k):
                t += f" {k}={e[k]}"
        if e.get("malla"):
            t += f" mesh={e['malla']}"
        if e.get("cuerpo"):
            t += f" body={e['cuerpo']}"
        return t.strip()

    def hash(self, sp: ParametrosSim | None = None) -> str:
        return hash_params(self.completo(sp))


def _fmt(v) -> str:
    return repr(float(v)) if not float(v).is_integer() else str(int(v))


def hash_params(d: dict) -> str:
    return hashlib.sha256(json.dumps({k: float(v) for k, v in sorted(d.items())}, separators=(",", ":")).encode()).hexdigest()


ESPECIAL_A_CAMPO = {"mesh": "malla", "body": "cuerpo"}


def desde_tokens(texto: str, sp: ParametrosSim | None = None, nombre: str = "", estricto_muertas: bool = False) -> Resuelta:
    """Receta plana desde el string que arma hoy la cadena (BASE QA A mesh= body=): el ultimo valor de cada clave gana,
    las repetidas quedan anotadas. Clave desconocida -> RecetaError."""
    sp = sp or leer_parametros_sim()
    params, esp, rep, adv = {}, {}, {}, []
    for k, v in parsear_tokens(texto):
        if k in sp.especiales:
            if k == "dumps":
                esp["dumps"] = [int(x) for x in v.split(",") if x]
            else:
                esp[ESPECIAL_A_CAMPO.get(k, k)] = v
            continue
        _clave_valida(k, sp)
        try:
            float(v)
        except ValueError:
            raise RecetaError(f"{k}={v}: el simulador hace float(v) y esto no es un numero")
        if k in params:
            rep.setdefault(k, [params[k]]).append(_numero(v))
        params[k] = _numero(v)
    r = Resuelta(nombre, params, esp, repetidas=rep)
    _avisos(r, sp, adv, estricto_muertas)
    return r


def _clave_valida(k: str, sp: ParametrosSim):
    if k in sp.validas or k in sp.especiales:
        return
    cerca = difflib.get_close_matches(k, sorted(sp.validas | set(sp.especiales)), n=3, cutoff=0.6)
    raise RecetaError(f"clave desconocida '{k}': el simulador la aceptaria en silencio y no haria nada"
                      + (f" (¿{' o '.join(cerca)}?)" if cerca else ""))


def _avisos(r: Resuelta, sp: ParametrosSim, adv: list, estricto: bool):
    for k in r.params:
        if k in sp.muertas:
            msg = f"'{k}' esta muerta: sim_e2s.py la acepta y no la lee en ninguna linea"
            if estricto:
                raise RecetaError(msg)
            adv.append(msg)
        if k in DIAGNOSTICO and k not in r.diagnostico and float(r.params[k]) != float(sp.defecto(k)):
            adv.append(f"'{k}={r.params[k]}' es un flag de DIAGNOSTICO y la receta no lo declara en `diagnostico`")
    r.advertencias = adv


# ------------------------------------------------------------------ receta.json
def cargar(ruta: str) -> dict:
    with open(ruta, encoding="utf-8") as fh:
        return json.load(fh)


def validar_forma(d: dict) -> list:
    """Errores de forma contra receta.schema.json (jsonschema si esta; si no, el minimo equivalente)."""
    with open(ESQUEMA, encoding="utf-8") as fh:
        esq = json.load(fh)
    try:
        import jsonschema
        return [f"{'/'.join(map(str, e.absolute_path)) or '<raiz>'}: {e.message}" for e in
                sorted(jsonschema.Draft7Validator(esq).iter_errors(d), key=lambda e: list(map(str, e.absolute_path)))]
    except ImportError:
        errs = [f"falta '{k}'" for k in esq["required"] if k not in d]
        errs += [f"clave no permitida '{k}'" for k in d if k not in esq["properties"]]
        errs += [f"params.{k} no es numero" for k, v in (d.get("params") or {}).items() if isinstance(v, bool) or not isinstance(v, (int, float))]
        return errs


def resolver(receta, sp: ParametrosSim | None = None, estricto_muertas: bool = False) -> Resuelta:
    """receta (ruta o dict) -> Resuelta. `base` es una ruta relativa a la receta; la base NO puede tener base (un nivel)."""
    sp = sp or leer_parametros_sim()
    carpeta = os.path.dirname(os.path.abspath(receta)) if isinstance(receta, str) else os.getcwd()
    d = cargar(receta) if isinstance(receta, str) else receta
    errs = validar_forma(d)
    if errs:
        raise RecetaError("la receta no cumple receta.schema.json: " + "; ".join(errs[:6]))
    params, esp, frames = {}, {}, None
    base = d.get("base")
    if base:
        rb = base if os.path.isabs(base) else os.path.join(carpeta, base)
        if not os.path.exists(rb):
            raise RecetaError(f"base '{base}' no existe (se busca junto a la receta)")
        b = cargar(rb)
        if b.get("base"):
            raise RecetaError(f"la base '{base}' tiene a su vez base '{b['base']}': la herencia es de UN nivel")
        errs = validar_forma(b)
        if errs:
            raise RecetaError(f"la base '{base}' no cumple el esquema: " + "; ".join(errs[:6]))
        params.update(b.get("params", {}))
        esp.update(_especiales_de(b))
        frames = b.get("frames", frames)
    params.update(d.get("params", {}))
    esp.update(_especiales_de(d))
    frames = d.get("frames", frames)
    for k in params:
        _clave_valida(k, sp)
        if k in sp.especiales:
            raise RecetaError(f"'{k}' es un parametro especial del simulador: va en su campo propio, no en params")
    r = Resuelta(d["nombre"], {k: v for k, v in params.items()}, esp, frames=frames, base=base,
                 diagnostico=list(d.get("diagnostico", [])))
    for k in r.diagnostico:
        if k not in DIAGNOSTICO:
            raise RecetaError(f"diagnostico: '{k}' no es un flag de diagnostico conocido {DIAGNOSTICO}")
    _avisos(r, sp, [], estricto_muertas)
    return r


def _especiales_de(d: dict) -> dict:
    return {k: d[k] for k in ("malla", "cuerpo", "dumps", "rk", "wini", "pramp", "pfit") if k in d}


def a_receta(r: Resuelta, base: str | None = None, descripcion: str = "", origen: dict | None = None) -> dict:
    d = {"version": 1, "nombre": r.nombre}
    if descripcion:
        d["descripcion"] = descripcion
    if base:
        d["base"] = base
    d["params"] = dict(r.params)
    d.update({k: v for k, v in r.especiales.items()})
    if r.frames:
        d["frames"] = r.frames
    if origen:
        d["origen"] = origen
    return d


def importar(tokens: str, nombre: str, base_tokens: str | None = None, base_ruta: str | None = None, frames: int | None = None,
             origen: dict | None = None, sp: ParametrosSim | None = None) -> dict:
    """tokens completos (BASE + resto, como los arma la cadena) -> receta con `base`: lo que ya trae la base se quita del prefijo."""
    sp = sp or leer_parametros_sim()
    resto = tokens
    if base_tokens:
        if not tokens.startswith(base_tokens):
            raise RecetaError("los tokens no empiezan con los de la base: no puedo separarlos")
        resto = tokens[len(base_tokens):]
    r = desde_tokens(resto, sp, nombre)
    r.frames = frames
    return a_receta(r, base_ruta, origen=dict(origen or {}, cadena_cruda=resto.strip(), repetidas=r.repetidas))


# ------------------------------------------------------------------ la prueba: resuelto == params logueado
def params_de_log(ruta_log: str) -> tuple:
    """Linea 1 de sim_<tag>.log: `params {...} frames N` -> (dict, N)."""
    with open(ruta_log, encoding="utf-8", errors="replace") as fh:
        ln = fh.readline().rstrip("\n")
    if not ln.startswith("params "):
        raise RecetaError(f"{ruta_log}: la linea 1 no es `params {{...}} frames N`")
    cuerpo, _, n = ln[len("params "):].rpartition(" frames ")
    return ast.literal_eval(cuerpo), int(n)


def comparar_con_log(r: Resuelta, ruta_log: str, sp: ParametrosSim | None = None) -> dict:
    """Compara el dict resuelto con el `params` del log. `solo_log`: claves del log que el codigo actual ya no tiene (errores);
    `solo_resuelto`: claves del codigo actual que el log no tenia (parametros agregados DESPUES de esa corrida; con su defecto
    valen lo mismo por contrato). `difieren`: valores distintos. `igual` = sin `solo_log` ni `difieren`; `exacto` = ademas sin `solo_resuelto`."""
    pl, nf = params_de_log(ruta_log)
    pr = r.completo(sp)
    solo_log = sorted(set(pl) - set(pr))
    solo_res = {k: pr[k] for k in sorted(set(pr) - set(pl))}
    difieren = {k: (pl[k], pr[k]) for k in sorted(set(pl) & set(pr)) if float(pl[k]) != float(pr[k])}
    return {"igual": not solo_log and not difieren, "exacto": not solo_log and not difieren and not solo_res,
            "solo_log": solo_log, "solo_resuelto": solo_res, "difieren": difieren, "n_log": len(pl), "n_resuelto": len(pr),
            "frames_log": nf, "frames_receta": r.frames}


# ------------------------------------------------------------------ CLI
def _tabla_claves(sp: ParametrosSim) -> str:
    L = [f"sim: {sp.ruta}", f"{len(sp.defectos)} en el dict de defectos + {len(sp.ocultas)} ocultas ({', '.join(sorted(sp.ocultas))}) "
         f"+ {len(sp.especiales)} especiales ({', '.join(sp.especiales)})",
         f"muertas ({len(sp.muertas)}): {', '.join(sp.muertas) or '-'} | leidas en UNA linea ({len(sp.una_vez)}): {', '.join(sp.una_vez)}",
         f"{'clave':14s} {'defecto':>10s} {'lineas':>6s}  clase"]
    for k in list(sp.defectos) + [k for k in sp.ocultas]:
        L.append(f"{k:14s} {str(sp.defecto(k)):>10s} {sp.lecturas.get(k, 0):6d}  {sp.clasificar(k)}")
    return "\n".join(L)


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="python -m prenda3d.receta")
    ap.add_argument("--sim", help="ruta de sim_e2s.py (defecto: etapa2/sim_e2s.py)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("claves", help="tabla de parametros que acepta sim_e2s.py")
    for c in ("validar", "resolver"):
        s = sub.add_parser(c)
        s.add_argument("receta")
        if c == "resolver":
            g = s.add_mutually_exclusive_group()
            g.add_argument("--tokens", action="store_true", help="imprime 'k=v k=v ...'")
            g.add_argument("--json", action="store_true", help="imprime el dict completo (defectos + receta)")
        else:
            s.add_argument("--estricto", action="store_true", help="una clave muerta tambien es error")
    s = sub.add_parser("probar", help="resuelto == params de la linea 1 del log")
    s.add_argument("receta"), s.add_argument("log")
    s = sub.add_parser("importar", help="receta desde la linea de un estado_<tag>.txt")
    s.add_argument("--estado", required=True), s.add_argument("--base-lanzador", help="script con BASE=\"...\" (lanza_w.sh)")
    s.add_argument("--base", help="receta base (ruta relativa a la salida)"), s.add_argument("--nombre", required=True)
    s.add_argument("--frames", type=int), s.add_argument("-o", "--salida", required=True)
    ns = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sp = leer_parametros_sim(ns.sim)
    try:
        if ns.cmd == "claves":
            print(_tabla_claves(sp))
        elif ns.cmd == "validar":
            r = resolver(ns.receta, sp, ns.estricto)
            print(f"PASA receta {r.nombre}: {len(r.params)} parametros propios, base {r.base or '-'}")
            for a in r.advertencias:
                print("  AVISO " + a)
        elif ns.cmd == "resolver":
            r = resolver(ns.receta, sp)
            print(r.tokens() if ns.tokens else json.dumps(r.completo(sp), indent=1) if ns.json else
                  f"{r.nombre}: {len(r.params)} parametros fijados, hash {r.hash(sp)[:12]}\n{r.tokens()}")
        elif ns.cmd == "probar":
            c = comparar_con_log(resolver(ns.receta, sp), ns.log, sp)
            print(("PASA" if c["igual"] else "FALLA") + f" resuelto == params de {os.path.basename(ns.log)}: "
                  f"{c['n_resuelto']} claves resueltas, {c['n_log']} en el log" + (" (exacto)" if c["exacto"] else ""))
            for k, v in c["difieren"].items():
                print(f"  DIFIERE {k}: log {v[0]} resuelto {v[1]}")
            if c["solo_log"]:
                print(f"  solo en el log (el codigo actual ya no las tiene): {c['solo_log']}")
            if c["solo_resuelto"]:
                print(f"  solo en lo resuelto (agregadas al codigo despues de esa corrida, valen su defecto): {c['solo_resuelto']}")
            return 0 if c["igual"] else 1
        elif ns.cmd == "importar":
            from .registro import leer_estado, base_de_lanzador
            est = leer_estado(ns.estado)
            bt = base_de_lanzador(ns.base_lanzador) if ns.base_lanzador else None
            d = importar(est["tokens"], ns.nombre, bt, ns.base, ns.frames, {"estado": os.path.basename(ns.estado)}, sp)
            with open(ns.salida, "w", encoding="utf-8") as fh:
                json.dump(d, fh, ensure_ascii=False, indent=1)
            print(f"receta {ns.nombre} escrita en {ns.salida}")
    except RecetaError as e:
        print(f"FALLA receta: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
