"""Entrada unica de una simulacion: prenda.json + receta.json + cuerpo + malla -> corrida con MANIFEST.

    blender -b --factory-startup -t <hilos> --python sim/lanzar.py -- prenda=<json> receta=<json> cuerpo=<npz> malla=<json> tag=<t> nf=<n>
            [salida=<carpeta>] [entradas=<carpeta>] [rk= wini= pramp= pfit= hrest=] [base=<id o tag de la corrida contra la que se va a comparar>]
    python sim/lanzar.py --validar prenda=<json> receta=<json> [...]     # sin Blender: dice si se puede simular y que falta

Que hace, en orden: valida la receta (prenda3d.receta: clave desconocida = error) -> revisa que esten malla, cuerpo y reglas (lista lo que falta
en vez de romperse) -> escribe el manifest (estado EN_CURSO) -> corre el nucleo -> reescribe el manifest (FIN / STOP / ESTABLE / ERROR, salidas con sha).
`malla` y `cuerpo` salen del argumento, si no de la receta, si no de `prenda.malla`. Rutas relativas: contra `entradas` (defecto: carpeta de la malla).
"""
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import traceback

SIM = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(SIM)
for _p in (SIM, RAIZ):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from prenda3d import receta as RC      # noqa: E402  (solo stdlib: corre en el Python de Blender)
from prenda3d import registro as RG    # noqa: E402

ORIGEN = os.path.join(SIM, "origen", "sim_e2s.py")      # de aca lee prenda3d.receta los parametros validos y sus defectos
CODIGO = ("nucleo.py", "lanzar.py", "offsets.py")       # + reglas de la prenda: lo que identifica "el codigo" de una corrida
CUERPO_CLAVES = ("V20", "V8", "Vin", "T", "cabeza")
CAPAS_CON_REGLA = {"cascara", "pared", "avio", "plancha", "vista"}   # capas que el nucleo + reglas de la M133 saben tratar
ESPECIALES = ("rk", "wini", "pramp", "pfit", "hrest")


def leer_args(argv):
    a = {"validar": False}
    for t in argv:
        if t == "--validar":
            a["validar"] = True
        elif "=" in t:
            k, v = t.split("=", 1); a[k] = v
        else:
            raise SystemExit(f"argumento no entendido: {t!r} (se espera clave=valor o --validar)")
    for k in ("prenda", "receta"):
        if k not in a:
            raise SystemExit(f"falta {k}=<json>")
    return a


def _abs(ruta, carpeta):
    return ruta if os.path.isabs(ruta) else os.path.normpath(os.path.join(carpeta, ruta))


def capas_de_reglas(ruta_py):
    """`CAPAS = {...}` declarado en el modulo de reglas de la prenda, leido del texto (el modulo importa bpy: no se puede importar sin Blender)."""
    if not ruta_py:
        return set()
    import ast
    m = re.search(r"^CAPAS\s*=\s*(\{[^}]*\}|set\(\))", open(ruta_py, encoding="utf-8").read(), re.M)
    try:
        return set(ast.literal_eval(m.group(1))) if m and m.group(1) != "set()" else set()
    except (ValueError, SyntaxError) as e:
        raise SystemExit(f"reglas: CAPAS mal escrito en {ruta_py}: {e}")


def resolver_entradas(a):
    """Junta todo lo que la corrida necesita. No abre Blender. Devuelve (ctx, faltan, avisos): `faltan` = lo que impide simular."""
    faltan, avisos = [], []
    ctx = {"args": a}
    prenda = json.load(open(a["prenda"], encoding="utf-8")); pdir = os.path.dirname(os.path.abspath(a["prenda"]))
    ctx["prenda"] = prenda; ctx["nombre"] = str(prenda.get("id", "prenda")).lower()
    sp = RC.leer_parametros_sim(ORIGEN)
    try:
        res = RC.resolver(a["receta"], sp)
    except RC.RecetaError as e:
        faltan.append(f"receta: {e}"); res = None
    ctx["sp"] = sp; ctx["res"] = res
    esp = res.especiales if res else {}
    pm = prenda.get("malla") or {}
    malla = a.get("malla") or esp.get("malla") or (pm.get("archivo") and _abs(pm["archivo"], pdir))
    cuerpo = a.get("cuerpo") or esp.get("cuerpo") or (pm.get("colisionador") and _abs(pm["colisionador"], pdir))
    # sin entradas=: la carpeta de la malla si vino absoluta; si no, la del prenda.json (donde vive su bloque `malla`), no el cwd
    ent = a.get("entradas") or (os.path.dirname(os.path.abspath(malla)) if malla and os.path.isabs(malla) else pdir)
    ctx["entradas"] = ent; ctx["malla"] = malla; ctx["cuerpo"] = cuerpo
    ctx["salida"] = os.path.abspath(a.get("salida") or os.getcwd())
    ctx["tag"] = a.get("tag") or (res.nombre if res else "sin_tag")
    ctx["nf"] = int(a.get("nf") or (res.frames if res and res.frames else 0) or 0)
    if ctx["nf"] <= 0:
        faltan.append("cuadros: ni nf=<n> ni `frames` en la receta")
    piezas = [p for p in prenda.get("piezas", [])]; ids = {p.get("id") for p in piezas}
    # --- malla 3D y V0
    D = None
    if not malla:
        faltan.append("malla 3D / V0: la prenda no tiene `malla` (ni malla= ni la receta la nombran). Falta construirla desde el DXF y las costuras "
                      "(ARQUITECTURA.md paso 8: `construir`) y colocarla sobre el cuerpo (arranque V0)")
    elif not os.path.isfile(_abs(malla, ent)):
        faltan.append(f"malla 3D / V0: no existe {_abs(malla, ent)}")
    else:
        D = json.load(open(_abs(malla, ent)))
        no = [k for k in ("v", "f", "uv", "groups", "sew") if k not in D]
        if no:
            faltan.append(f"malla: faltan las claves obligatorias {no}")
        else:
            sin_grupo = sorted(i for i in ids if i and i not in D["groups"])
            fuera = {x if isinstance(x, str) else x.get("id") for x in prenda.get("fuera_de_sim", [])} | {x if isinstance(x, str) else x.get("id") for x in prenda.get("solo_render", [])}
            sin_grupo = [i for i in sin_grupo if i not in fuera]
            if sin_grupo:
                avisos.append(f"malla: {len(sin_grupo)} piezas de la prenda sin grupo de vertices: {sin_grupo[:12]}")
            op = [k for k in ("lining", "pinch", "pocket", "pocket_area_m2", "placket", "zipper", "cuff", "band") if k not in D]
            if op:
                avisos.append(f"malla: sin las claves opcionales {op} (el nucleo las toma vacias: sin forro separado / sin presion / sin avios rigidos)")
    ctx["D"] = D
    # --- cuerpo
    if not cuerpo:
        avisos.append("cuerpo: sin npz -> colisiona contra el maniqui parametrico del nucleo (torso + cabeza + brazos)")
    elif not os.path.isfile(_abs(cuerpo, ent)):
        faltan.append(f"cuerpo: no existe {_abs(cuerpo, ent)}")
    else:
        try:
            import numpy as np
            no = [k for k in CUERPO_CLAVES if k not in np.load(_abs(cuerpo, ent)).files]
            if no:
                faltan.append(f"cuerpo: al npz le faltan las claves {no}")
        except ImportError:
            avisos.append("cuerpo: numpy no disponible, no se revisaron las claves del npz")
    # --- reglas de la prenda (codigo + datos)
    rpy = a.get("reglas") or os.path.join(SIM, ctx["nombre"] + "_reglas.py"); rjs = os.path.splitext(rpy)[0] + ".json"
    ctx["reglas_py"] = rpy if os.path.isfile(rpy) else None; ctx["reglas_json"] = rjs if os.path.isfile(rjs) else None
    ctx["datos_reglas"] = json.load(open(rjs, encoding="utf-8")) if ctx["reglas_json"] else {}
    if not ctx["reglas_py"]:
        avisos.append(f"reglas: no hay sim/{ctx['nombre']}_reglas.py -> corre solo el nucleo (sin metricas por zona ni construcciones propias)")
    for k in ("piezas_inyectadas",):
        mal = [x for x in ctx["datos_reglas"].get(k, []) if x not in ids]
        if mal:
            faltan.append(f"reglas: {k} nombra piezas que no estan en prenda.json: {mal}")
    # --- reglas de material y de construccion
    mats = sorted({str(p.get("material")) for p in piezas if p.get("material")})
    if len(mats) > 1 and ctx["reglas_py"]:
        avisos.append(f"material: {len(mats)} materiales con UNA fisica en la receta; las diferencias las ponen las reglas de la prenda (grupos de rigidez y cascara)")
    elif len(mats) > 1:
        faltan.append(f"reglas de material: la prenda tiene {len(mats)} materiales ({', '.join(mats)}) y la receta lleva UNA fisica para toda la tela "
                      "(tension/compression/bending/mass). Falta `receta.fisica` por material + medir cada tela en banco chico (PROXIMA-PRENDA.md 1.2)")
    # capas que entran en la sim: solo las de piezas en la malla (una pieza con en_malla=false no se construye: su capa no necesita regla);
    # un modulo de reglas puede declarar `CAPAS = {...}` (las que trata a su manera, p. ej. el forro sumado a la cascara en la M1195)
    capas = sorted({str(p.get("capa")) for p in piezas if p.get("capa") and p.get("en_malla", True)})
    con_regla = set(CAPAS_CON_REGLA) | capas_de_reglas(ctx["reglas_py"])
    sin_regla = [c for c in capas if c not in con_regla]
    if sin_regla:
        faltan.append(f"reglas de construccion: capas sin regla en el nucleo: {sin_regla} (el forro acolchado en rombos necesita su capa: pespuntes forro-guata, sin presion; ARQUITECTURA.md paso 7)")
    if prenda.get("pendiente"):
        avisos.append(f"prenda.json: {len(prenda['pendiente'])} datos pendientes de medir en la prenda fisica (campo `pendiente`)")
    return ctx, faltan, avisos


def informe(ctx, faltan, avisos):
    o = [("LISTA PARA SIMULAR" if not faltan else f"NO SE PUEDE SIMULAR TODAVIA: faltan {len(faltan)}") + f" | prenda {ctx['prenda'].get('id')} | receta {ctx['res'].nombre if ctx['res'] else '?'} | "
         f"malla {ctx['malla']} | cuerpo {ctx['cuerpo']} | reglas {os.path.basename(ctx['reglas_py']) if ctx['reglas_py'] else 'ninguna'} | cuadros {ctx['nf']}"]
    o += [f"  FALTA  {x}" for x in faltan] + [f"  aviso  {x}" for x in avisos]
    return "\n".join(o)


def parametros(ctx):
    """P como lo armaba el original: defectos del codigo + lo que fija la receta, con float(v)."""
    P = dict(ctx["sp"].defectos)
    for k, v in ctx["res"].params.items():
        P[k] = float(v)
    return P


def _sha_codigo(ctx):
    arch = {n: RG.sha256(os.path.join(SIM, n)) for n in CODIGO}
    for k in ("reglas_py", "reglas_json"):
        if ctx[k]:
            arch[os.path.basename(ctx[k])] = RG.sha256(ctx[k])
    sand = os.path.join(SIM, ctx["nombre"] + "_sandwich.py")
    if os.path.isfile(sand):
        arch[os.path.basename(sand)] = RG.sha256(sand)
    comb = hashlib.sha256(json.dumps(sorted(arch.items())).encode()).hexdigest()
    git = {"commit": None, "dirty": None}
    try:
        git["commit"] = subprocess.run(["git", "-C", RAIZ, "rev-parse", "HEAD"], capture_output=True, text=True, timeout=20).stdout.strip() or None
        git["dirty"] = bool(subprocess.run(["git", "-C", RAIZ, "status", "--porcelain", "--", "."], capture_output=True, text=True, timeout=60).stdout.strip())
    except Exception as e:   # sin git en el PATH de Blender: queda dicho, no inventado
        git["error"] = repr(e)
    return {"sha256": comb, "archivos": arch, "origen_sim_e2s_sha256": RG.sha256(ORIGEN), "git": git, "identificacion": "sha256 de los archivos de sim/ (verificado)"}


def _hilos(bpy):
    for i, t in enumerate(sys.argv):
        if t in ("-t", "--threads") and i + 1 < len(sys.argv):
            return {"n": int(sys.argv[i + 1]), "fuente": "argv"}
    return {"n": int(bpy.context.scene.render.threads), "fuente": "render.threads (sin -t)"}


def _archivo(ruta):
    return {"nombre": os.path.basename(ruta), "ruta": ruta, "sha256": RG.sha256(ruta), "bytes": os.path.getsize(ruta)}


def manifest_inicial(ctx, P, bpy):
    ent = ctx["entradas"]; a = ctx["args"]; res = ctx["res"]
    esp = {k: (a.get(k) or res.especiales.get(k) or None) for k in ESPECIALES}
    dumps = sorted(int(x) for x in (a["dumps"].split(",") if a.get("dumps") else res.especiales.get("dumps", [])))
    m = {"tag": ctx["tag"], "estado": "EN_CURSO", "inicio": datetime.datetime.now().isoformat(timespec="seconds"), "fin": None, "frames": ctx["nf"],
         "prenda": dict(_archivo(os.path.abspath(a["prenda"])), id=ctx["prenda"].get("id")),
         "malla": _archivo(_abs(ctx["malla"], ent)), "cuerpo": _archivo(_abs(ctx["cuerpo"], ent)) if ctx["cuerpo"] else None,
         "receta": {"ruta": os.path.abspath(a["receta"]), "nombre": res.nombre, "base": res.base, "sha256": RG.sha256(a["receta"]), "diagnostico": res.diagnostico},
         "params": P, "receta_hash": RC.hash_params(P),
         "especiales": dict(dumps=dumps, **{k: (_archivo(_abs(v, ent)) if v else None) for k, v in esp.items()}),
         "hilos": _hilos(bpy), "blender": {"version": bpy.app.version_string, "hash": getattr(bpy.app, "build_hash", b"").decode(errors="replace")},
         "codigo": _sha_codigo(ctx), "base_comparacion": a.get("base"), "salida": ctx["salida"], "salidas": {}, "linea": " ".join(sys.argv)}
    m["id"] = RG.id_corrida(m)
    ctx["esp"] = esp; ctx["dumps"] = dumps
    return m


def main(argv=None):
    argv = sys.argv[sys.argv.index("--") + 1:] if (argv is None and "--" in sys.argv) else (sys.argv[1:] if argv is None else argv)
    a = leer_args(argv)
    ctx, faltan, avisos = resolver_entradas(a)
    print(informe(ctx, faltan, avisos))
    if a["validar"]:
        return 0 if not faltan else 2
    if faltan:
        return 2
    import bpy
    import importlib.util
    import nucleo
    assert nucleo.DEFECTOS == ctx["sp"].defectos, "los DEFECTOS del nucleo no son los del origen: regenerar con tools/partir_sim.py"
    reglas = None
    if ctx["reglas_py"]:
        spec = importlib.util.spec_from_file_location(os.path.splitext(os.path.basename(ctx["reglas_py"]))[0], ctx["reglas_py"])
        reglas = importlib.util.module_from_spec(spec); spec.loader.exec_module(reglas)
    P = parametros(ctx)
    os.makedirs(ctx["salida"], exist_ok=True); carpeta = os.path.join(ctx["salida"], "corridas")
    m = manifest_inicial(ctx, dict(P), bpy)
    print("manifest:", RG.escribir(m, carpeta), "| id", m["id"])
    t0 = time.time(); c0 = time.process_time(); ES = None
    try:
        ES = nucleo.preparar(P, ctx["nf"], ctx["tag"], ctx["malla"], ctx["entradas"], ctx["salida"], ctx["nombre"], cuerpo=ctx["cuerpo"] or "", dumps=ctx["dumps"],
                             reglas=reglas, datos_reglas=ctx["datos_reglas"], **{k: (v or "") for k, v in ctx["esp"].items()})
        m["estado"] = nucleo.correr(ES)
    except BaseException as e:
        m["estado"] = "ERROR"; m["error"] = "".join(traceback.format_exception_only(type(e), e)).strip(); m["traza"] = traceback.format_exc()
        raise
    finally:
        m["fin"] = datetime.datetime.now().isoformat(timespec="seconds"); m["pared_s"] = round(time.time() - t0, 1); m["cpu_s"] = round(time.process_time() - c0, 1)
        if ES is not None:
            m["cuadros_hechos"] = int(getattr(ES, "f", 0)); m["avisos_except"] = dict(ES.AVISOS)
            m["params_finales"] = {k: v for k, v in ES.P.items() if m["params"].get(k) != v}   # el nucleo pisa bending / bend_max / sw_f0 al remapear
        for n in sorted(os.listdir(ctx["salida"])):
            p = os.path.join(ctx["salida"], n)
            if os.path.isfile(p) and re.search(r"(^|_)" + re.escape(ctx["tag"]) + r"(_|\.)", n):
                m["salidas"][n] = RG.sha256(p)
        RG.escribir(m, carpeta)
    return 0


if __name__ == "__main__":
    _r = main()
    if _r:
        sys.exit(_r)
