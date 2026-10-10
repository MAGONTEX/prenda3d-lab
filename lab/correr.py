"""[ESC·f535] lab/correr.py - corre VARIAS variantes de un banco en UN Blender (5.1, -b) con el NUCLEO de la prenda (sim/nucleo.py).

Una variante = escena (lab/escenas/*.json) + receta. La receta es la de la M133 resuelta por prenda3d.receta (la misma que usa
sim/lanzar.py) + `receta_lab` de la tanda + `params` de la variante (clave desconocida = error, nada se ignora en silencio).
Del nucleo corren tal cual: preparar, tela (reposo molde plano / hrest, grupos, cascara), cloth (Cloth, autocolision, gravedad en
rampa) y bucle (cuadros, dumps, guardas). Cambian solo:
  * escena_lab (en vez de escena_y_cuerpo): colisionadores del banco en vez del maniqui; arranque con escala / ruido / replica;
    pines del banco (ES.TPV, el mismo grupo `pin` del nucleo); el desplazamiento de la capa interior (forro) es el del nucleo;
  * cierre_lab (en vez de cierre): sin renders ni .blend; final + aberturas por costura + tiempos en res_<tag>.json.

    blender -b --factory-startup -t 4 --python lab/correr.py -- tanda=<json> salida=<dir> [solo=a,b]

tanda.json = {nombre, receta (relativa a prenda3d/), receta_lab {k: v}, nf, dumps [..], variantes [{tag, escena, params {},
nf, dumps, escala (B2), ruido_z_mm, replica (semilla: ruido <= 0,3 mm en 3D, solo vertices libres), nota}]}
"""
import importlib.util
import json
import os
import sys
import time
import traceback

import bpy
import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__)); PAQ = os.path.dirname(AQUI); SIM = os.path.join(PAQ, "sim")
for _p in (SIM, PAQ, AQUI):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import nucleo                              # noqa: E402
from prenda3d import receta as RC          # noqa: E402

OCULTAS = ("sa_brd", "tilt", "tiltf")


def args():
    return dict(t.split("=", 1) for t in sys.argv[sys.argv.index("--") + 1:] if "=" in t)


def parametros(T, var, sp):
    res = RC.resolver(os.path.join(PAQ, T["receta"]), sp); P = dict(sp.defectos)
    for k, v in res.params.items():
        P[k] = float(v)
    for fuente in (T.get("receta_lab", {}), var.get("params", {})):
        for k, v in fuente.items():
            if k not in sp.defectos and k not in OCULTAS:
                raise KeyError(f"parametro desconocido {k!r} (no esta en sim_e2s.py)")
            P[k] = float(v)
    return P, res.nombre


def reglas():
    spec = importlib.util.spec_from_file_location("lab_reglas", os.path.join(AQUI, "lab_reglas.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def encoge(ES, var):
    """[ESC·f535] B4: exceso de tela / mascara de acortamiento por clase (lab/encoge_lab.py). Sin `encoge` en la variante: nada."""
    if var.get("encoge") is not None:
        import encoge_lab
        encoge_lab.aplicar(ES, var["encoge"])


def reescala(ES, var, cambios_P):
    """[ESC·f535] banco 4 a 5 mm: regla de reescala (lab/reescala_lab.py). Sin `reescala` en la variante: nada."""
    if var.get("reescala"):
        import reescala_lab
        ES.log(f"[ESC·f535] REESCALA {var['reescala']}: " + " ".join(f"{k} {a:g}->{b:g}" for k, a, b in cambios_P + reescala_lab.cloth(ES, var)) + f" | quality {ES.s.quality}")


def limpiar():
    sc = bpy.data.scenes.new("LAB")
    try:
        bpy.context.window.scene = sc
    except Exception:
        pass
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for s in [s for s in bpy.data.scenes if s is not sc]:
        bpy.data.scenes.remove(s)
    for coll in (bpy.data.meshes, bpy.data.collections, bpy.data.actions):
        for x in list(coll):
            if x.users == 0:
                coll.remove(x)
    return sc


def escena_lab(ES, var, M):
    """Reemplaza nucleo.escena_y_cuerpo: mismo orden de reglas (filtrar_costuras antes, sandwich_rotar_caras al final)."""
    nucleo._regla(ES, "filtrar_costuras_diagnostico")
    ES.sc = limpiar(); ES.col = bpy.data.collections.new("Lab"); ES.sc.collection.children.link(ES.col)
    ES.sc.frame_start = 1; ES.sc.frame_end = ES.NF; ES.sc.render.fps = 24
    ES.INST = ES.D["inst"]; ES.NV = len(ES.D["v"])

    def collider(ob, th=None):                       # = nucleo.escena_y_cuerpo.collider
        th = ES.P["th"] if th is None else th
        ob.modifiers.new("col", "COLLISION"); ob.collision.thickness_outer = th; ob.collision.cloth_friction = ES.P["fric"]
        ob.collision.damping = 0.5; ob.hide_render = True
        return ob
    ES.collider = collider; ES.MANIQUI = []; ES.TFOBJ = []
    thc = ES.P["bth"] if ES.P["bth"] >= 0 else None
    for c in M.get("colisionadores", []):
        if c["tipo"] == "cilindro":
            bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=c["r"], depth=c["largo"], location=tuple(c["centro"]), rotation=tuple(c.get("rot", (1.5707963267948966, 0, 0))))  # [ESC·f535] rot opcional (B7: eje z)
        elif c["tipo"] == "mesa":
            bpy.ops.mesh.primitive_plane_add(size=c["lado"], location=(0.15, 0.07, c["z"]))
        ob = bpy.context.active_object; ob.name = "CD_lab_" + c["tipo"]
        for u in ob.users_collection:
            u.objects.unlink(ob)
        ES.col.objects.link(ob); ES.MANIQUI.append(ES.collider(ob, th=thc))
        ES.log(f"colisionador {c} | espesor {ob.collision.thickness_outer} friccion {ob.collision.cloth_friction}")
    ES.V0 = np.array(ES.D["v"], float); ES.F = np.array(ES.D["f"])
    LIN = ES.D["lining"]                              # = nucleo: capa interior separada `off` hacia adentro, salvo borde y pespuntes
    if LIN:
        VN = np.zeros_like(ES.V0); tri = ES.V0[ES.F]; fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        for j in range(3):
            np.add.at(VN, ES.F[:, j], fn)
        VN /= np.maximum(np.linalg.norm(VN, axis=1, keepdims=True), 1e-12); fixed = set(ES.D["border"]) | set(ES.D["pinch"])
        for n, nf in LIN.items():
            o, of = ES.INST[n]["off"], ES.INST[nf]["off"]
            for k in range(ES.D["groups"][nf][1] - ES.D["groups"][nf][0]):
                if of + k not in fixed:
                    ES.V0[of + k] = ES.V0[o + k] - ES.P["off"] * VN[o + k]
    pin = set(M.get("pin", [])) | (set(M.get("pin_panel", [])) if M.get("fijo") else set())
    libre = np.ones(ES.NV, bool); libre[sorted(pin)] = False
    if var.get("escala") is not None:                 # B2: arranque = molde escalado s alrededor del centro (z igual)
        s = float(var["escala"]); c = np.array(M["escala_centro"]) / 1000.0
        for g in M["escala_piezas"]:
            a, b = ES.D["groups"][g]; ES.V0[a:b, :2] = c + s * (ES.V0[a:b, :2] - c)
        ES.log(f"ARRANQUE escalado {s} (area {s * s:.3f} del molde) en {M['escala_piezas']}")
    if var.get("ruido_z_mm"):
        r = np.random.default_rng(7); amp = float(var["ruido_z_mm"]) / 1000.0
        ES.V0[libre, 2] += r.uniform(-amp, amp, int(libre.sum())); ES.log(f"ruido z +-{var['ruido_z_mm']} mm (semilla fija 7) en {int(libre.sum())} v libres")
    if int(var.get("replica", 0)):
        r = np.random.default_rng(int(var["replica"])); d = r.normal(size=(ES.NV, 3)); d /= np.linalg.norm(d, axis=1, keepdims=True)
        d *= r.uniform(0, 0.0003, size=(ES.NV, 1)); d[~libre] = 0; ES.V0 += d
        ES.log(f"REPLICA perturbada: <= 0,3 mm en {int(libre.sum())} v libres (semilla {var['replica']})")
    ES.TPV = pin
    if M.get("fijo") and M.get("pin_panel"):          # pines que no estan en su molde: su reposo = su arranque (hrest del nucleo)
        ids = np.array(sorted(M["pin_panel"]), int); ruta = os.path.join(ES.SAL, f"hrest_{ES.TAG}.npz")
        np.savez(ruta, ids=ids, co=ES.V0[ids]); ES.HREST = ruta
    ES.log(f"ESCENA LAB {M['escena']}: {ES.NV} v {len(ES.F)} tri {len(ES.D['sew'])} pares | pin {len(pin)} | autocol {len(ES.D.get('autocol', []))} | "
           f"escena del contexto {bpy.context.scene.name}")
    nucleo._regla(ES, "sandwich_rotar_caras")


def cierre_lab(ES, res):
    X = ES.coords(); np.save(ES.SAL + f"X_{ES.TAG}_fin.npy", X[:ES.NV0])
    S = np.array(ES.D["sew"]); g = {}
    for (a, b), nm in zip(S, ES.D["sew_seam"]):
        g.setdefault(nm, []).append(1000 * float(np.linalg.norm(X[a] - X[b])))
    res["costuras_mm"] = {k: dict(max=round(max(v), 2), p95=round(float(np.percentile(v, 95)), 2), n=len(v)) for k, v in g.items()}
    res["finito"] = bool(np.isfinite(X).all()); res["cuadros"] = int(ES.f)


def correr_variante(T, var, sp, salida, R):
    tag = var["tag"]; esc = json.load(open(os.path.join(AQUI, "escenas", var["escena"] + ".json"), encoding="utf-8")); M = esc["lab"]
    P, rnom = parametros(T, var, sp); import reescala_lab; P, cambios_P = reescala_lab.params(P, var); nf = int(var.get("nf", T.get("nf", 72))); dumps = var.get("dumps", T.get("dumps", [1, 2, 3, 4, 6, 12, 24, 36, 48, 60, 72]))
    tmp = os.path.join(salida, f"_malla_{tag}.json"); json.dump(esc, open(tmp, "w", encoding="utf-8"))
    res = dict(tag=tag, escena=var["escena"], receta=rnom, receta_hash=RC.hash_params(P), params_var=var.get("params", {}), estado="ERROR",
               nota=var.get("nota", ""), blender=bpy.app.version_string, hilos=[sys.argv[i + 1] for i, t in enumerate(sys.argv) if t == "-t"][:1])
    t0 = time.time()
    try:
        ES = nucleo.preparar(P, nf, tag, tmp, salida, salida, "lab", dumps=dumps, reglas=R, datos_reglas=M.get("datos_reglas"))
        escena_lab(ES, var, M); t1 = time.time()
        nucleo.tela(ES); nucleo.cloth(ES); encoge(ES, var); reescala(ES, var, cambios_P); t2 = time.time(); nucleo.bucle(ES); t3 = time.time()
        cierre_lab(ES, res); res["estado"] = "STOP" if ES.STOP else ("ROTA" if not res["finito"] else "FIN")
        res.update(t_escena=round(t1 - t0, 2), t_armado=round(t2 - t1, 2), t_sim=round(t3 - t2, 2), s_por_cuadro=round((t3 - t2) / max(ES.f, 1), 3),
                   avisos_except=dict(ES.AVISOS), params_finales={k: v for k, v in ES.P.items() if P.get(k) != v})
        ES.LOG.close()
    except Exception as e:
        res["error"] = repr(e); res["traza"] = traceback.format_exc(); print(res["traza"], flush=True)
    res["t_total"] = round(time.time() - t0, 2); res["P"] = P
    json.dump(res, open(os.path.join(salida, f"res_{tag}.json"), "w", encoding="utf-8"), indent=1)
    os.remove(tmp)
    print(f"LAB {tag}: {res['estado']} en {res['t_total']} s (sim {res.get('t_sim')} s, {res.get('s_por_cuadro')} s/cuadro)", flush=True)
    return res


def main():
    a = args(); T = json.load(open(a["tanda"], encoding="utf-8")); salida = os.path.abspath(a["salida"]); os.makedirs(salida, exist_ok=True)
    sp = RC.leer_parametros_sim(os.path.join(SIM, "origen", "sim_e2s.py"))
    assert nucleo.DEFECTOS == sp.defectos, "DEFECTOS del nucleo distintos del origen: regenerar con tools/partir_sim.py"
    R = reglas(); solo = set(a["solo"].split(",")) if a.get("solo") else None; filas = []
    for var in T["variantes"]:
        if solo and var["tag"] not in solo:
            continue
        r = correr_variante(T, var, sp, salida + os.sep, R)
        filas.append(f"{time.strftime('%m-%d %H:%M:%S')} {r['tag']} {r['estado']} {r['t_total']} s sim {r.get('t_sim')} s")
        with open(os.path.join(salida, "tiempos.txt"), "a", encoding="utf-8") as fh:
            fh.write(filas[-1] + "\n")
    print("LAB FIN", len(filas), "variantes", flush=True)


if __name__ == "__main__":
    main()
