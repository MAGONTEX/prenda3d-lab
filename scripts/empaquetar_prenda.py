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
"""
import argparse
import json
import os
import py_compile
import re
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERICOS = [re.compile(r"C:.Users", re.I), re.compile(r"/home/[a-z]", re.I), re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"),
             re.compile(r"ghp_[A-Za-z0-9]{20}"), re.compile(r"github_pat_"), re.compile(r"AKIA[0-9A-Z]{16}"),
             re.compile(r"\.dxf\b", re.I), re.compile("[\\u3400-\\u9fff]")]
ARRIBA = ("version", "id", "talle", "piezas", "costuras", "avios", "fuera_de_sim", "solo_render", "zonas_rigidez", "tolerancias",
          "pendiente", "materiales", "malla")
FUERA = re.compile(r"^(nota.*|pendiente|razon|rol|descripcion|bloques|contorno|origen|medida_foto.*|nombre|fuente.*|foto.*|dxf|comentario.*)$")


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--carpeta", required=True); ap.add_argument("--paquete", required=True); ap.add_argument("--codigo", required=True)
    ap.add_argument("--malla", required=True, action="append"); ap.add_argument("--cuerpo", required=True)
    ap.add_argument("--receta", action="append", default=[]); ap.add_argument("--extra", action="append", default=[])
    ap.add_argument("--patrones", required=True)
    a = ap.parse_args()
    pats = patrones(a.patrones); cod = a.codigo.lower()
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
