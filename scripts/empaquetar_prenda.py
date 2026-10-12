"""[ESC·f535] Empaqueta UNA prenda para correrla entera en GitHub Actions (prendas/<codigo>/). Corre en la laptop, no en Actions.

    python scripts/empaquetar_prenda.py --carpeta <carpeta de la prenda> --paquete <carpeta del paquete prenda3d> --codigo w2057 \
        --malla w2057_s1.json --cuerpo cuerpo_W2057_piel20.npz --receta sim/receta_c1.json [--receta sim/receta_c4.json ...] \
        [--extra sim/ficha_m1195.py] --patrones <limpieza_patrones.txt privado>

Que hace:
  * prenda.json -> prendas/<codigo>/prenda_publica.json por LISTA BLANCA: solo los campos que leen lanzar.py y las reglas (piezas, costuras, avios,
    fuera_de_sim, solo_render, zonas_rigidez, tolerancias, pendiente, materiales, malla). Fuera: dxf, nombre, notas, razones, descripciones,
    bloques, contornos, auditoria, metricas, revision. Los materiales se renombran mat1, mat2... (los nombres originales vienen del DXF).
  * malla V0 (json), cuerpo (npz), recetas y extras: copia tal cual (las recetas pierden `descripcion`).
  * reglas de la prenda (sim/<codigo>_reglas.py/.json del paquete) -> sim/ de este repo, con los patrones privados reemplazados por [x].
  * escanea TODO lo que escribio (patrones privados + rutas personales + claves + DXF + texto en chino): si algo queda, borra nada pero
    sale con codigo 1 y lo lista. No commitea: eso lo hace quien lo corre, con rutas explicitas.
El archivo de patrones es PRIVADO (nombres de proveedores): nunca se copia a este repo.

[ESC·f535] --modo argv (M133, 2026-10-12): para una prenda que NO usa el nucleo generico sino su propio script de sim (k=v por argv).
    python scripts/empaquetar_prenda.py --modo argv --carpeta <etapa2> --codigo m133 --patrones <privado> \
        --script _qc_R16/vps/sim_e2s_R16.py=sim_e2s_R16.py --script sand_e2s.py ... --extra m133_e2zzh1.json ... \
        --receta-argv _qc_R16/vps/receta_HQ.txt=receta_hq.json
  * `orig=destino`: destino relativo a prendas/<codigo>/ (sin `=`, la misma ruta).
  * --script (.py): patrones privados -> [x], ruta local de ROOT/E2 -> ".", texto en chino -> [x]; despues el AST tiene que quedar
    IGUAL al original (salvo ese literal de ROOT/E2): si un reemplazo toca codigo, sale con 1.
  * --extra .json: se sanean solo los TEXTOS (patrones privados -> [x]); numeros, listas y claves tienen que quedar iguales.
    .npz: solo arreglos numericos (si hay texto, sale con 1). Otro tipo: copia tal cual.
  * --receta-argv: txt con tokens k=v (lineas '#' fuera) -> {"modo": "argv", "argv": [...]} (el orden importa: gana el ultimo).
  * no escribe prenda_publica.json ni copia reglas; escribe paquete.json (sha256 del original y del publicado, saneado si/no).
"""
import argparse
import ast
import hashlib
import json
import os
import py_compile
import re
import shutil
import sys

import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERICOS = [re.compile(r"C:.Users", re.I), re.compile(r"/home/[a-z]", re.I), re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"),
             re.compile(r"ghp_[A-Za-z0-9]{20}"), re.compile(r"github_pat_"), re.compile(r"AKIA[0-9A-Z]{16}"),
             re.compile(r"\.dxf\b", re.I), re.compile("[\\u3400-\\u9fff]")]
ARRIBA = ("version", "id", "talle", "piezas", "costuras", "avios", "fuera_de_sim", "solo_render", "zonas_rigidez", "tolerancias",
          "pendiente", "materiales", "malla")
FUERA = re.compile(r"^(nota.*|pendiente|razon|rol|descripcion|bloques?|contorno|origen|medida_foto.*|nombre|fuente.*|foto.*|dxf|comentario.*)$")


def patrones(ruta):
    out = []
    for l in (x.strip() for x in open(ruta, encoding="utf-8")):
        if l and not l.startswith("#"):
            out.append((l.startswith("ruta:"), re.compile(l[5:] if l.startswith("ruta:") else l, re.I)))
    return out


def limpiar(x, mat):
    """Lista blanca recursiva: tira las claves de texto libre; renombra los materiales."""
    if isinstance(x, dict):
        o = {}
        for k, v in x.items():
            if FUERA.match(k):
                continue
            o[k] = mat.get(v, v) if k == "material" and isinstance(v, str) else limpiar(v, mat)
        return o
    if isinstance(x, list):
        return [limpiar(v, mat) for v in x]
    return x


def prenda_publica(P, malla, cuerpo):
    mat = {k: f"mat{i + 1}" for i, k in enumerate(sorted(P.get("materiales", {})))}
    o = {k: P[k] for k in ARRIBA if k in P}
    o["materiales"] = {mat[k]: {"rol": v.get("rol")} for k, v in P.get("materiales", {}).items()}
    o = {k: (v if k == "materiales" else limpiar(v, mat)) for k, v in o.items()}
    def campo(c):
        for k, v in mat.items():
            c = str(c).replace(k, v)
        return c
    o["pendiente"] = [{"campo": campo(x.get("campo"))} if isinstance(x, dict) else "pendiente" for x in P.get("pendiente", [])]
    o["malla"] = {"archivo": malla, "colisionador": cuerpo}
    o["publico"] = "[ESC·f535] version publica para simular (lista blanca de scripts/empaquetar_prenda.py): sin DXF, notas ni nombres"
    return o


def sanear_texto(txt, pats):
    for s, r in pats:
        if not s:
            txt = r.sub("[x]", txt)
    return txt


def escanear(rutas, pats):
    malos = []
    for f in rutas:
        nombre = os.path.basename(f)
        malos += [f"{f}: nombre de archivo prohibido" for s, r in pats if s and r.search(nombre)]
        if f.endswith(".npz"):
            continue
        try:
            txt = open(f, encoding="utf-8").read()
        except UnicodeDecodeError:
            continue
        for ln, l in enumerate(txt.splitlines(), 1):
            for s, r in pats + [(False, g) for g in GENERICOS]:
                m = None if s else r.search(l)
                if m:
                    a = max(0, m.start() - 30)
                    malos.append(f"{f}:{ln}: ...{l[a:m.end() + 30]}...")
    return malos


RX_RAIZ = re.compile(r'^(ROOT|E2)(\s*=\s*)r?(["\'])([^"\'\n]*)\3', re.M)
RX_LOCAL = re.compile(r"([A-Za-z]:[/\\]|/home/|/Users/)")
CJK = re.compile("[\\u3400-\\u9fff]+")


def sha(ruta):
    return hashlib.sha256(open(ruta, "rb").read()).hexdigest()


def par(s):
    o, _, d = s.partition("=")
    return o, (d or o)


def sanear_script(txt, pats):
    """argv: ruta local de ROOT/E2 -> "." (o "./"), patrones privados -> [x], chino -> [x]. El AST se controla aparte."""
    t = RX_RAIZ.sub(lambda m: (f'{m.group(1)}{m.group(2)}r"{"./" if m.group(4).endswith("/") else "."}"'
                               if RX_LOCAL.match(m.group(4)) else m.group(0)), txt)
    return CJK.sub("[x]", sanear_texto(t, pats))


def ast_igual(a, b):
    """mismo programa: AST identico salvo el literal de ROOT/E2 de nivel superior (comentarios y formato no cuentan)."""
    def norm(s):
        T = ast.parse(s)
        for n in T.body:
            if (isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
                    and n.targets[0].id in ("ROOT", "E2") and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)):
                n.value.value = "<raiz>"
        return ast.dump(T)
    return norm(a) == norm(b)


def sanear_json(x, pats, cambios, ruta="$"):
    """argv: solo los textos pasan por los patrones privados; una CLAVE que cambiaria es error (el script la busca por nombre)."""
    if isinstance(x, dict):
        o = {}
        for k, v in x.items():
            if sanear_texto(k, pats) != k or CJK.search(k):
                raise ValueError(f"{ruta}: la clave {k!r} tiene texto privado (no se renombra sola)")
            o[k] = sanear_json(v, pats, cambios, f"{ruta}/{k}")
        return o
    if isinstance(x, list):
        return [sanear_json(v, pats, cambios, f"{ruta}[{i}]") for i, v in enumerate(x)]
    if isinstance(x, str):
        y = CJK.sub("[x]", sanear_texto(x, pats))
        if y != x:
            cambios.append(ruta)
        return y
    return x


def igual_salvo_textos(a, b, ruta="$"):
    if isinstance(a, dict):
        assert isinstance(b, dict) and list(a) == list(b), f"{ruta}: claves distintas"
        for k in a:
            igual_salvo_textos(a[k], b[k], f"{ruta}/{k}")
    elif isinstance(a, list):
        assert isinstance(b, list) and len(a) == len(b), f"{ruta}: largo distinto"
        for i, (u, v) in enumerate(zip(a, b)):
            igual_salvo_textos(u, v, f"{ruta}[{i}]")
    elif isinstance(a, str):
        assert isinstance(b, str), f"{ruta}: tipo distinto"
    else:
        assert type(a) is type(b) and (a == b or (a != a and b != b)), f"{ruta}: {a!r} != {b!r}"


def npz_numerico(ruta):
    with zipfile.ZipFile(ruta) as z:
        nombres = z.namelist()
    import numpy as np   # solo en la laptop (el empaquetador no corre en Actions)
    with np.load(ruta, allow_pickle=False) as Z:
        malos = [k for k in Z.files if Z[k].dtype.kind not in "biufc"]
    return malos, nombres


def main_argv(a, pats, cod):
    """--modo argv: script propio + entradas, sin prenda_publica.json (ver cabecera)."""
    dst = os.path.join(REPO, "prendas", cod); os.makedirs(dst, exist_ok=True); escritos = []; man = {}
    def destino(d):
        p = os.path.join(dst, d.replace("\\", "/")); os.makedirs(os.path.dirname(p), exist_ok=True); return p
    for s in a.script:
        o, d = par(s); src = os.path.join(a.carpeta, o); p = destino(d)
        txt = open(src, encoding="utf-8").read(); t = sanear_script(txt, pats)
        if not ast_igual(txt, t):
            print(f"LIMPIEZA: {o}: el saneado cambia el programa (AST distinto): revisar a mano el original"); return 1
        open(p, "w", encoding="utf-8", newline="\n").write(t); py_compile.compile(p, doraise=True)
        escritos.append(p); man[d] = {"origen": o, "sha256_origen": sha(src), "sha256": sha(p), "saneado": t != txt, "ast_igual": True}
    for e in a.extra:
        o, d = par(e); src = os.path.join(a.carpeta, o); p = destino(d)
        if o.endswith(".json"):
            X = json.load(open(src, encoding="utf-8")); cambios = []
            try:
                Y = sanear_json(X, pats, cambios)
            except ValueError as ex:
                print(f"LIMPIEZA: {o}: {ex}"); return 1
            if cambios:
                json.dump(Y, open(p, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, separators=(",", ":"))
                igual_salvo_textos(X, json.load(open(p, encoding="utf-8")))
            else:
                shutil.copyfile(src, p)
            man[d] = {"origen": o, "sha256_origen": sha(src), "sha256": sha(p), "saneado": bool(cambios), "textos_saneados": cambios[:20]}
        else:
            if o.endswith(".npz"):
                malos, _ = npz_numerico(src)
                if malos:
                    print(f"LIMPIEZA: {o}: arreglos no numericos {malos} (pueden traer texto)"); return 1
            shutil.copyfile(src, p); man[d] = {"origen": o, "sha256_origen": sha(src), "sha256": sha(p), "saneado": False}
        escritos.append(p)
    for r in a.receta_argv:
        o, d = par(r); src = os.path.join(a.carpeta, o); p = destino(d)
        tok = [t for l in open(src, encoding="utf-8") if not l.lstrip().startswith("#") for t in l.split()]
        malos = [t for t in tok if "=" not in t or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*=\S+$", t)]
        if malos:
            print(f"{o}: tokens que no son k=v: {malos[:5]}"); return 1
        json.dump({"modo": "argv", "argv": tok}, open(p, "w", encoding="utf-8", newline="\n"), indent=1)
        escritos.append(p); man[d] = {"origen": o, "sha256_origen": sha(src), "sha256": sha(p), "tokens": len(tok)}
    pm = os.path.join(dst, "paquete.json")
    json.dump({"modo": "argv", "codigo": cod, "archivos": man,
               "publico": "[ESC·f535] paquete --modo argv de scripts/empaquetar_prenda.py: sin DXF, notas privadas ni rutas"},
              open(pm, "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
    escritos.append(pm)
    malos = escanear(escritos, pats)
    for e in escritos:
        print(f"{os.path.getsize(e) / 1e6:7.2f} MB  {os.path.relpath(e, REPO)}" + ("  (saneado)" if man.get(os.path.relpath(e, dst).replace(os.sep, "/"), {}).get("saneado") else ""))
    if malos:
        print("LIMPIEZA: quedan cosas prohibidas (no commitear):"); print("\n".join(malos[:30])); return 1
    print("limpieza OK"); return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modo", choices=("nucleo", "argv"), default="nucleo")
    ap.add_argument("--carpeta", required=True); ap.add_argument("--paquete"); ap.add_argument("--codigo", required=True)
    ap.add_argument("--malla", action="append", default=[]); ap.add_argument("--cuerpo")
    ap.add_argument("--receta", action="append", default=[]); ap.add_argument("--extra", action="append", default=[])
    ap.add_argument("--script", action="append", default=[]); ap.add_argument("--receta-argv", action="append", default=[])
    ap.add_argument("--patrones", required=True)
    a = ap.parse_args()
    pats = patrones(a.patrones); cod = a.codigo.lower()
    if a.modo == "argv":
        return main_argv(a, pats, cod)
    if not (a.malla and a.cuerpo and a.paquete):
        ap.error("--modo nucleo necesita --malla, --cuerpo y --paquete")
    dst = os.path.join(REPO, "prendas", cod); os.makedirs(dst, exist_ok=True); escritos = []
    P = json.load(open(os.path.join(a.carpeta, "prenda.json"), encoding="utf-8"))
    pp = os.path.join(dst, "prenda_publica.json")   # otro nombre a proposito: `prenda.json` (el original) sigue prohibido por la limpieza privada
    json.dump(prenda_publica(P, a.malla[0], a.cuerpo), open(pp, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    escritos.append(pp)
    for f in a.malla + [a.cuerpo] + a.extra:
        d = os.path.join(dst, f.replace("\\", "/")); os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copyfile(os.path.join(a.carpeta, f), d); escritos.append(d)
    for f in a.receta:
        R = json.load(open(os.path.join(a.carpeta, f), encoding="utf-8")); R.pop("descripcion", None)
        d = os.path.join(dst, os.path.basename(f)); json.dump(R, open(d, "w", encoding="utf-8", newline="\n"), indent=1); escritos.append(d)
    for ext in (".py", ".json"):
        o = os.path.join(a.paquete, "sim", f"{cod}_reglas{ext}")
        if os.path.isfile(o):
            d = os.path.join(REPO, "sim", os.path.basename(o))
            open(d, "w", encoding="utf-8", newline="\n").write(sanear_texto(open(o, encoding="utf-8").read(), pats))
            if ext == ".py":
                py_compile.compile(d, doraise=True)
            escritos.append(d)
    malos = escanear(escritos, pats)
    for e in escritos:
        print(f"{os.path.getsize(e) / 1e6:7.2f} MB  {os.path.relpath(e, REPO)}")
    if malos:
        print("LIMPIEZA: quedan cosas prohibidas (no commitear):"); print("\n".join(malos[:30])); return 1
    print("limpieza OK"); return 0


if __name__ == "__main__":
    sys.exit(main())
