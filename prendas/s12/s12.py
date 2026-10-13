# [ESC·f535] BANCO S12 (2026-10-13): triangulacion IRREGULAR contra reticulas regulares, con bending 5 y 1 (Blender 5.1, -b --factory-startup).
# Base: banco S11 (s11.py, mismo disco, apoyos, semillas y parametros de la prenda de referencia). Pregunta: una malla irregular (sin direcciones
# de pliegue preferidas) cae mas natural que la reticula regular? bajar bending deja actuar al shear?
#   var=T  triangulos equilateros h 9,5 mm, filas horizontales (reticula de la prenda de referencia)
#   var=C  reticula CUADRADA alineada con el hilo, lado h sqrt(sqrt3/2) = 8,84 mm (misma densidad que T); diagonales = resortes de shear
#   var=R  triangulacion irregular isotropa: puntos Poisson-disk maximal + borde remuestreado (r_puntos.json, hecho con gen_r.py, misma
#          cantidad de vertices que T), triangulados aca con mathutils.geometry.delaunay_2d_cdt (Delaunay restringido de Blender)
#   bending=5 (defecto) o 1. Los demas parametros: mass 0.02, tension 100, compression 15, shear 5, quality 10, air 1; colision cd 4 mm,
#   th 8 mm, fric 0.5, damping 0.5, collision_quality 3; autocolision self_d 3 mm, self_friction 5; gravedad en rampa f1 -> f3; 24 fps.
#   apoyo=disco  Cusick: disco O 180 colisionador + tela PINZADA en r <= 90 | apoyo=esfera R 95: vertice central pinzado sobre el polo
#   semilla: traslacion <= 1,5 mm + giro en z al azar (movimiento rigido; misma perturbacion para T, C y R con la misma semilla)
# uso (lab, modo argv): blender -b --factory-startup -t 4 --python s12.py -- NF TAG [k=v ...]   (NF y TAG los antepone scripts/prendas.py)
#   k = var apoyo semilla nf bending mass tension compression shear quality air (una clave desconocida es error: no hay palancas mudas)
# Salida en $S12_OUT (defecto ./out): s12_<var>[_b<bending>]_<apoyo>_s<semilla>.npz y sim_<TAG>.log (termina en "fin ..." si corrio entera)
import bpy, sys, json, math, time, os
import numpy as np
from mathutils.geometry import delaunay_2d_cdt

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
P = dict(var="T", apoyo="disco", semilla=0, nf=150, h=9.5, rt=150.0, rd=90.0, rs=95.0, mass=0.02, tension=100.0, compression=15.0,
         shear=5.0, bending=5.0, quality=10, air=1.0, cd=0.004, th=0.008, fric=0.5, cdamp=0.5, cq=3, self_d=0.003, sf=5.0, g0=1, g1=3)
POS = []
for a in argv:
    if "=" not in a:
        POS.append(a); continue
    k, v = a.split("=", 1)
    if k not in P:
        raise SystemExit(f"S12 ERROR clave desconocida {k!r}")
    P[k] = type(P[k])(v)
if POS:
    P["nf"] = int(POS[0])
TAG = POS[1] if len(POS) > 1 else "local"
OUT = os.environ.get("S12_OUT", "out"); os.makedirs(OUT, exist_ok=True)
LOG = open(os.path.join(OUT, f"sim_{TAG}.log"), "w", encoding="utf-8", newline="\n")


def log(s):
    print(s, flush=True); LOG.write(s + "\n"); LOG.flush()


VAR = P["var"]; NF = int(P["nf"]); BEND = float(P["bending"])
if VAR not in ("T", "C", "R"):
    raise SystemExit(f"S12 ERROR var {VAR!r}")
LAB = VAR + ("" if BEND == 5.0 else f"_b{BEND:g}")
h = P["h"] / 1000.0; RT = P["rt"] / 1000.0; RD = P["rd"] / 1000.0; RS = P["rs"] / 1000.0
GAP = 8.0 / 9.0 * (P["cd"] + P["th"])
MALLA = {}

if VAR == "T":   # --- reticula equilatera con filas horizontales, recortada al disco (= s11.py)
    dy = h * math.sqrt(3) / 2
    nj = int(RT / dy) + 2; ni = int(RT / h) + 3
    idx = {}; V = []
    for j in range(-nj, nj + 1):
        off = 0.5 * h if j % 2 else 0.0
        for i in range(-ni, ni + 1):
            x, y = i * h + off, j * dy
            if x * x + y * y <= RT * RT + 1e-12:
                idx[(i, j)] = len(V); V.append((x, y))
    V = np.array(V); TRI, FQ = [], []
    for (i, j) in list(idx):
        if (i + 1, j) not in idx:
            continue
        L, R = idx[(i, j)], idx[(i + 1, j)]
        a, b = (i + j % 2, j + 1), (i + j % 2, j - 1)
        TRI += [t for t in ([L, R, idx[a]] if a in idx else None, [L, idx[b], R] if b in idx else None) if t]
    FACES = TRI
elif VAR == "C":   # --- cuadrada al hilo (= s11.py var C): cuads enteros; celdas de borde con 3 vertices = triangulo
    s_ = h * math.sqrt(math.sqrt(3) / 2); n_ = int(RT / s_) + 2
    idx = {}; V = []
    for j in range(-n_, n_ + 1):
        for i in range(-n_, n_ + 1):
            x, y = i * s_, j * s_
            if x * x + y * y <= RT * RT + 1e-12:
                idx[(i, j)] = len(V); V.append((x, y))
    V = np.array(V); TRI, FQ = [], []
    for (i, j) in list(idx):
        k4 = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]; ok = [q in idx for q in k4]
        if all(ok):
            a_, b_, c_, d_ = [idx[q] for q in k4]; FQ.append([a_, b_, c_, d_]); TRI += [[a_, b_, c_], [a_, c_, d_]]
        elif sum(ok) == 3:
            t_ = [idx[q] for q, o in zip(k4, ok) if o]; FQ.append(t_); TRI.append(t_)
    FACES = FQ
else:   # --- R: puntos fijos (gen_r.py) + Delaunay restringido de Blender con el borde como restriccion
    here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "."
    src = next(p for p in (os.path.join(here, "r_puntos.json"), os.path.join(OUT, "r_puntos.json"), "r_puntos.json") if os.path.isfile(p))
    J = json.load(open(src, encoding="utf-8")); nb = int(J["nb"])
    V = np.array(J["puntos_mm"], dtype=float) / 1000.0 * (RT / 0.150)
    vc, ed, fa, ov, oe, of = delaunay_2d_cdt([tuple(p) for p in V], [(i, (i + 1) % nb) for i in range(nb)], [], 0, 1e-9, True)
    if len(vc) != len(V) or any(list(ov[i]) != [i] for i in range(len(V))):
        raise SystemExit(f"S12 ERROR el CDT cambio los vertices ({len(vc)} vs {len(V)})")
    TRI = []
    for f in fa:
        f = list(f)
        if len(f) != 3:
            raise SystemExit(f"S12 ERROR cara de {len(f)} lados en el CDT")
        a_, b_, c_ = V[f[0]], V[f[1]], V[f[2]]
        TRI.append(f if (b_[0] - a_[0]) * (c_[1] - a_[1]) - (b_[1] - a_[1]) * (c_[0] - a_[0]) > 0 else [f[0], f[2], f[1]])
    FACES = TRI; FQ = []
    T_ = np.array(TRI); E_ = np.unique(np.sort(np.r_[T_[:, [0, 1]], T_[:, [1, 2]], T_[:, [2, 0]]], axis=1), axis=0)
    Le = np.linalg.norm(V[E_[:, 1]] - V[E_[:, 0]], axis=1) * 1000
    def _ang(p, q, s):
        u, v = q - p, s - p
        return np.degrees(np.arccos(np.clip((u * v).sum(1) / np.linalg.norm(u, axis=1) / np.linalg.norm(v, axis=1), -1, 1)))
    a_, b_, c_ = V[T_[:, 0]], V[T_[:, 1]], V[T_[:, 2]]
    Am = np.minimum(np.minimum(_ang(a_, b_, c_), _ang(b_, c_, a_)), _ang(c_, a_, b_))
    MALLA = dict(src=os.path.basename(src), nb=nb, ntri=len(TRI), nedges=len(E_), arista_media_mm=float(Le.mean()), arista_sd_mm=float(Le.std()),
                 arista_min_mm=float(Le.min()), arista_max_mm=float(Le.max()), angulo_min=float(Am.min()), n_menor_25=int((Am < 25).sum()))
    log(f"S12 R malla: {json.dumps(MALLA)}")

# --- semilla: movimiento rigido chico (= s11.py)
rng = np.random.default_rng(1000 + int(P["semilla"]))
ang = rng.uniform(0.0, math.pi / 3); d = rng.uniform(-1.0, 1.0, 2)
d = d / max(np.linalg.norm(d), 1e-12) * 0.0015 * rng.uniform(0.3, 1.0)
c_, s_ = math.cos(ang), math.sin(ang)
Vw = V @ np.array([[c_, s_], [-s_, c_]]) + d
if P["apoyo"] == "disco":
    z0 = 0.0; ztop = -GAP
    PINS = [int(k) for k in np.nonzero(np.linalg.norm(Vw, axis=1) <= RD + 1e-9)[0]]
elif P["apoyo"] == "esfera":
    z0 = RS + GAP
    PINS = [int(np.argmin(np.linalg.norm(Vw, axis=1)))]
else:
    raise SystemExit(f"S12 ERROR apoyo {P['apoyo']!r}")

# --- escena (= s11.py)
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
sc = bpy.context.scene
sc.frame_start = 1; sc.frame_end = NF; sc.render.fps = 24
if P["apoyo"] == "disco":
    bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=RD, depth=0.01, location=(0, 0, ztop - 0.005))
else:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=48, radius=RS, location=(0, 0, 0))
col = bpy.context.active_object; col.name = "apoyo"
col.modifiers.new("col", 'COLLISION'); col.collision.thickness_outer = P["th"]; col.collision.cloth_friction = P["fric"]; col.collision.damping = P["cdamp"]

me = bpy.data.meshes.new("tela"); me.from_pydata([(float(x), float(y), z0) for x, y in Vw], [], FACES); me.update()
ob = bpy.data.objects.new("tela", me); sc.collection.objects.link(ob)
vg = ob.vertex_groups.new(name="pin"); vg.add(PINS, 1.0, 'REPLACE')
cm = ob.modifiers.new("cloth", 'CLOTH'); s = cm.settings
s.quality = P["quality"]; s.mass = P["mass"]; s.air_damping = P["air"]
s.tension_stiffness = P["tension"]; s.compression_stiffness = P["compression"]; s.shear_stiffness = P["shear"]; s.bending_stiffness = BEND
s.vertex_group_mass = "pin"
cs = cm.collision_settings; cs.collision_quality = P["cq"]; cs.distance_min = P["cd"]
cs.use_self_collision = True; cs.self_distance_min = P["self_d"]; cs.self_friction = P["sf"]
ew = s.effector_weights
for f, g in ((1, 0.0), (P["g0"], 0.0), (P["g1"], 1.0)):
    ew.gravity = g; ew.keyframe_insert("gravity", frame=f)
cm.point_cache.frame_start = 1; cm.point_cache.frame_end = NF
nf4 = sum(1 for p in me.polygons if len(p.vertices) == 4)
log(f"S12 {LAB} {P['apoyo']} s{P['semilla']} tag {TAG}: NV {len(V)} tri {len(TRI)} caras {len(FACES)} (cuads {nf4}) pines {len(PINS)} "
    f"| bending_model {s.bending_model} bending {s.bending_stiffness} shear {s.shear_stiffness} | giro {math.degrees(ang):.1f} desplaz {d * 1000} mm")

REC = sorted({f for f in (1, 2, 3, 5, 10, 25, 50, 75, 100, 125, NF - 10, NF - 1, NF) if 1 <= f <= NF})
X = {}
t0 = time.time()
for f in range(1, NF + 1):
    sc.frame_set(f)
    if f in REC:
        dg = bpy.context.evaluated_depsgraph_get(); oe = ob.evaluated_get(dg); m = oe.to_mesh()
        co = np.empty(len(m.vertices) * 3); m.vertices.foreach_get("co", co); oe.to_mesh_clear()
        X[f] = co.reshape(-1, 3).copy()
        if f % 50 == 0 or f == NF:
            log(f"S12 f{f} {time.time() - t0:.1f}s zmin {X[f][:, 2].min() * 1000:.1f} mm nan {int(np.isnan(X[f]).sum())}")
fn = os.path.join(OUT, f"s12_{LAB}_{P['apoyo']}_s{P['semilla']}.npz")
info = dict(A=dict(P, var=LAB, var_malla=VAR), P=P, NV=len(V), ntri=len(TRI), nfaces=len(FACES), nquads=nf4, pins=len(PINS), giro=math.degrees(ang),
            desplaz=(d * 1000).tolist(), z0=z0, gap=GAP, t=time.time() - t0, bending_model=s.bending_model, blender=bpy.app.version_string, malla=MALLA, tag=TAG)
np.savez_compressed(fn, V0=Vw, rho0=np.linalg.norm(V, axis=1), tri=np.array(TRI), quads=np.array([q for q in FQ if len(q) == 4]),
                    pins=np.array(PINS), frames=np.array(REC), X=np.stack([X[f] for f in REC]), info=json.dumps(info))
log(f"t sim {int(round(time.time() - t0))}")
log(f"fin {TAG} {os.path.basename(fn)} nan {int(np.isnan(X[NF]).sum())}")
LOG.close()
