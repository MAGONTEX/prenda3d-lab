"""Nucleo del simulador de tela (Blender Cloth por codigo): escena, cuerpo, tela, Cloth, bucle de cuadros y salidas.

GENERADO por tools/partir_sim.py desde sim/origen/sim_e2s.py (sha256 340a0129c64238e427ad53428dc00bea4dbe053d7de9668c54b64455ca74a1de). No editar a mano mientras
dure la migracion: se cambia el generador y se regenera, y `tools/equivalencia_sim.py` tiene que seguir dando 0,000000 mm.

No tiene nombres de pieza. Lo propio de una prenda entra por dos lados:
  * datos    `ES.RD` (json de reglas de la prenda: piezas con canales inflados, prefijo de manga, costuras clave, indices del eje CF);
  * codigo   un modulo de reglas (`m133_reglas.py`) cuyas funciones el nucleo llama por nombre con `_regla(ES, "nombre")`.
             Sin modulo de reglas esas llamadas no hacen nada (una prenda sin capucha no tiene metrica de capucha).
Estado: todo lo que cruza de un bloque a otro vive en `ES` (SimpleNamespace). `preparar()` lo arma; `correr()` ejecuta las partes.

Reglas del Cloth que este archivo respeta (MANUAL-CLOTH-BLENDER-EXPERTO.md 1.7): toda F-curve se inserta ANTES de f1; escribir un grupo de
vertices o una propiedad a mitad de sim RECONSTRUYE el Cloth (cuadro muerto) -> solo lo hace el lazo de presion cuando nrb=0.
El estado interno del Cloth por offsets de memoria se lee en UN lugar: sim/offsets.py (control de version de Blender).
"""
import bpy, bmesh, json, math, sys, time, mathutils, collections, os, types
import numpy as np
import offsets

ORIGEN_SHA = "340a0129c64238e427ad53428dc00bea4dbe053d7de9668c54b64455ca74a1de"
PARTES = "escena_y_cuerpo, tela, cloth, bucle, cierre".split(", ")
DEFECTOS = dict(w_cost=0.0, pl_bh=-1.0, pl_hc=-1.0, abd_end=20.0, mass=0.02, tension=100, compression=15, shear=5, bending=5.0, quality=10, sew_max=80.0, air=1.0, fric=0.5,
         head=1, g0=1, g1=3, arm_top=-0.10, p0=16.0, w0=0.3, K=3, ramp=30, h_body=0.0105, h_sl=0.0093, off=0.0015, bend_max=50.0,
         w_cuff=0.6, renders=1, soft=1.0, S_body=0.04, S_sl=0.08, selfcol=1.0, self_d=0.003, sf=5.0, vtk=1.0, w_band=1.0,
         w_neck=0.0, w_sisa=0.0, hds=1.0, hd0=3, hd1=9, hd2=36, hd3=48,
         arm_end=-1.0, arm_f0=12, arm_f1=60, q_ramp=0, selfarm=0, arm_gap=0.012, hood_bend=-1.0, cd=0.004, th=0.008, uarm=-1.0, uarm_band=0.12, z_ax=1.33, vcol=0, hood_soft=0,
         hood_scope=0, sweep=0, sw_r=0.15, sw_f0=5, sw_f1=30, sw_f2=36, sw_th=0.004, hcol=0, stop_open=0.0, sw_path=1, arm_x1=-1.0,
         settle_min=0.0, settle_tol=2.0, settle_n=2, ent_c=0.0, nar=0.0, cinch=0.0, cz0=6, cz1=36, hfric=-1.0, settle_hood=1, tfric=-1.0, snaps=1, w_plk=1.0, msym=0, pres=1, notp=0, cuff_on=1,
         bgrow=18, bth=-1.0, deltoid=0, dl_x=0.215, dl_y=0.0, dl_z=1.405, dl_a=0.055, dl_b=0.06, dl_c=0.045, dl_s0=1.0, dl_f=1,
         sand=0, sand_ov=1, sand_txy=1.0, sand_zs=1.0, sand_rot=0, neck_hs=-1.0, neck_ht=-1.0, bmx=-1.0, rig_tap=0.0, noobj_neck=0, sand_d=5.5, sand_k=200.0, sand_kc=100.0, sand_len=10.0, sand_tap=12.0, sand_nc=1, stop_f6=30.0,
         cf_hold=0.0, cf_ramp=12.0, cf_ch=34.0, cf_lr=0.0, wsym=0.0, tp_nocol=0.0, sep_h=0.0, sep_eps=0.0, tfric_f=0.0, tfric2=-1.0, tfric_r=6.0, rk_f0=2, rk_df=3, fmp=2, nrb=0, sand_lvl=0.0,
         pfb=0.0, pfb_f0=30, pfb_clip=0.1, pfb_sm=1, mano=0.0, q_ini=0.0, q_ini_f=12, arm_x0=0.21, arm_z0=1.40, ath=-1.0, arm_xi=-1.0, arm_zi=-1.0)
# claves que la malla de la M133 trae y que una prenda mas simple puede no traer (sin forro, sin canales, sin avios rigidos)
MALLA_OPCIONALES = dict(lining={}, border=[], pinch=[], lx={}, pocket_area_m2={}, placket=[], zipper=[], cuff=[], band={}, inst={}, sew_seam=[])
MALLA_OBLIGATORIAS = ("v", "f", "uv", "groups", "sew")


def _mn(a): return a.min() if len(a) else float("nan")
def _mx(a): return a.max() if len(a) else float("nan")


def _regla(ES, nombre):
    """Llama la regla de la prenda si su modulo la define."""
    fn = getattr(ES.REGLAS, nombre, None) if ES.REGLAS is not None else None
    if fn is not None:
        fn(ES)


def preparar(P, nf, tag, malla, entradas, salida, nombre, cuerpo="", dumps=(), rk="", wini="", pramp="", pfit="", hrest="", reglas=None, datos_reglas=None):
    """Arma el estado. Reemplaza las lineas 51-119 del original (argv, P, log, carga de la malla). `P` ya viene resuelto (defectos + receta)."""
    ES = types.SimpleNamespace()
    ES.P = P; ES.NF = int(nf); ES.TAG = tag; ES.MESH = malla; ES.BODY = cuerpo or ""; ES.DUMPS = set(int(x) for x in dumps)
    ES.RK = rk or ""; ES.WINI = wini or ""; ES.PRAMP = pramp or ""; ES.PFIT = pfit or ""; ES.HREST = hrest or ""
    ES.ENT = entradas; ES.SAL = salida.rstrip("/\\") + "/"; ES.NOMBRE = nombre
    ES.RUTA = lambda x: x if os.path.isabs(x) else os.path.join(ES.ENT, x)
    ES.REGLAS = reglas; ES.RD = dict(piezas_inyectadas=[], prefijo_manga=[], costuras_clave=[], indices_cf=None); ES.RD.update(datos_reglas or {})
    ES.MANGA = tuple(ES.RD["prefijo_manga"])
    ES.LOG = open(ES.SAL + f"sim_{tag}.log", "w"); ES.AVISOS = {}

    def log(*a, sep=" "):
        ES.LOG.write(sep.join(str(x) for x in a) + "\n"); ES.LOG.flush()

    def avisar1(texto, e):
        """Un `except` que antes tragaba el error: queda en el log, una vez por texto, y contado en ES.AVISOS."""
        ES.AVISOS[texto] = ES.AVISOS.get(texto, 0) + 1
        if ES.AVISOS[texto] == 1:
            log("AVISO (except):", texto, "|", type(e).__name__, e)
    ES.log = log; ES.avisar1 = avisar1
    log("params", P, "frames", ES.NF)
    ES.D = json.load(open(ES.RUTA(malla))); log("malla", malla)
    faltan = [k for k in MALLA_OBLIGATORIAS if k not in ES.D]
    if faltan:
        raise KeyError(f"la malla {malla} no trae las claves obligatorias {faltan}")
    for k, v in MALLA_OPCIONALES.items():
        if k not in ES.D:
            ES.D[k] = v; log("malla: sin la clave", k, "-> vacia")
    if "pocket" not in ES.D: ES.D["pocket"] = [None] * len(ES.D["v"]); log("malla: sin la clave pocket -> sin bolsillos de presion")
    ES.TPV = set(); ES.HOODSET = set()   # los definen las reglas de la prenda; vacios si no hay
    return ES


def correr(ES):
    """Ejecuta las partes en el orden del original. Devuelve el estado final: FIN, STOP (guarda de costura) o ESTABLE (asentamiento)."""
    for nombre in PARTES:
        globals()[nombre](ES)
    ES.LOG.flush()
    return "STOP" if ES.STOP else ("ESTABLE" if ES.SETTLED else "FIN")


def escena_y_cuerpo(ES):
    """Escena, maniqui (torso, cabeza, brazos, deltoides), cuerpo npz y capa interior separada. (sim_e2s.py L120-L305)"""
    _regla(ES, "filtrar_costuras_diagnostico")
    ES.sc = bpy.data.scenes.new('CAMPDIB_E2M')
    try:
        bpy.context.window.scene = ES.sc
    except Exception as _e_av:
        ES.avisar1('escena: no se pudo fijar en la ventana (normal con -b)', _e_av)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    ES.col = bpy.data.collections.new('CampDib_E2M')
    ES.sc.collection.children.link(ES.col)
    ES.sc.frame_start = 1
    ES.sc.frame_end = ES.NF
    ES.sc.render.fps = 24
    ES.INST = ES.D['inst']
    ES.NV = len(ES.D['v'])
    # e2l: triangulos explicitos con la diagonal espejada entre mitades (k < n/2: r0[k]-r1[k+1]; resto: r0[k+1]-r1[k])
    # e2l: tapas en abanico desde un vertice central (simetricas); poles = (z abajo, z arriba) si el polo no esta en el plano del anillo
    def loft(name, secs, cap=True, mirror=False, poles=None):
        n = 48
        bm = bmesh.new()
        rings = []
        sg = -1.0 if mirror else 1.0
        for z, a, b, yc in secs:
            rings.append([bm.verts.new((sg * a * math.sin(2 * math.pi * k / n), yc - b * math.cos(2 * math.pi * k / n), z)) for k in range(n)])
    
        def _f(vs):
            bm.faces.new(vs[::-1] if mirror else vs)
        for r0, r1 in zip(rings, rings[1:]):
            for k in range(n):
                q = (r0[k], r0[(k + 1) % n], r1[(k + 1) % n], r1[k])
                if ES.P['msym'] > 0:
                    if k < n // 2:
                        _f((q[0], q[1], q[2]))
                        _f((q[0], q[2], q[3]))
                    else:
                        _f((q[0], q[1], q[3]))
                        _f((q[1], q[2], q[3]))
                else:
                    _f(q)
        if cap:
            if ES.P['msym'] > 0:
                zb, zt = poles if poles else (secs[0][0], secs[-1][0])
                cb = bm.verts.new((0.0, secs[0][3], zb))
                ct = bm.verts.new((0.0, secs[-1][3], zt))
                for k in range(n):
                    _f((cb, rings[0][(k + 1) % n], rings[0][k]))
                    _f((ct, rings[-1][k], rings[-1][(k + 1) % n]))
            else:
                _f(rings[0][::-1])
                _f(rings[-1])
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(name, me)
        ES.col.objects.link(ob)
        return ob
    def collider(ob, th=None):
        th = ES.P['th'] if th is None else th
        ob.modifiers.new('col', 'COLLISION')
        ob.collision.thickness_outer = th
        ob.collision.cloth_friction = ES.P['fric']
        ob.collision.damping = 0.5
        ob.hide_render = True
        return ob
    ES.collider = collider
    # maniqui = el de v4h
    # e2e5, MANIQUI v2 (construccion del set): el de v4h tenia el frente plano (pecho -120 / cintura -110 / cadera -115 mm) y el cuello
    # horizontal y centrado (el escote de 589 mm se apoyaba horizontal en z 1,50: caida CB->CF 10 mm, real 60-90). Se HUNDEN el vientre
    # (hasta 22 mm) y el frente de la base del cuello (22-23 mm) dejando pecho, espalda y anchos: pecho 32 mm delante del vientre y
    # ningun punto avanza sobre la pose de arranque (no hay interpenetracion en f1). Contorno de pecho sigue en 97 cm (L ~104).
    def _rec(z, a, b, y, d):
        return (z, a, b - d / 2.0, y + d / 2.0)
    TS = [(0.66, 0.19, 0.12, 0), _rec(0.8, 0.185, 0.115, 0, 0.01), _rec(0.95, 0.17, 0.11, 0, 0.022), _rec(1.1, 0.175, 0.115, 0, 0.015), (1.25, 0.185, 0.12, 0), (1.36, 0.195, 0.115, 0), _rec(1.42, 0.2, 0.105, 0, 0.005), _rec(1.46, 0.185, 0.09, 0, 0.022), _rec(1.49, 0.12, 0.075, 0.0, 0.023), _rec(1.51, 0.07, 0.062, 0.005, 0.012), (1.58, 0.062, 0.06, 0.01)]
    # e2j: torso mas angosto bajo la axila (maniqui = construccion): -nar mm de semiancho entre z 1,20 y 1,36, a 0 en z 1,05 y 1,42; solo saca volumen
    if ES.P['nar'] > 0:
    
        def _tp(z):
            return float(np.clip(min((z - 1.05) / 0.15, (1.42 - z) / 0.06), 0.0, 1.0))
        TS = [(q[0], q[1] - ES.P['nar'] / 1000.0 * _tp(q[0]), q[2], q[3]) for q in TS]
        ES.log('maniqui: torso -', ES.P['nar'], 'mm de semiancho bajo la axila:', [(round(q[0], 2), round(q[1], 3)) for q in TS])
    # e2zu2: colisionadores que llevan tfric
    torso = ES.collider(loft('CD_maniqui_torso', TS))
    ES.TFOBJ = [torso] if ES.P['tfric'] >= 0 else []
    if ES.P['tfric'] >= 0:
        torso.collision.cloth_friction = ES.P['tfric']
        ES.log('torso: friccion', ES.P['tfric'], '(mu ~', round(0.01 * ES.P['tfric'], 2), '; camisa + cardigan contra forro 210T ~0,3-0,5)')
    # e2l: cabeza = elipsoide 0,085 x 0,105 x 0,12 centrado en (0, 0,01, 1,67) como loft de 15 anillos con polos en abanico (triangulacion espejada)
    if ES.P['msym'] > 0:
        _hs = [(1.67 - 0.12 * math.cos(math.pi * j / 16), 0.085 * math.sin(math.pi * j / 16), 0.105 * math.sin(math.pi * j / 16), 0.01) for j in range(1, 16)]
        head = loft('CD_maniqui_cabeza', _hs, poles=(1.67 - 0.12, 1.67 + 0.12))
        ES.log('maniqui SIMETRICO (msym): torso, brazos y cabeza con la triangulacion espejada; brazo L = espejo del R; tapas y polos en abanico')
    else:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1, location=(0, 0.01, 1.67))
        head = bpy.context.active_object
        head.name = 'CD_maniqui_cabeza'
        head.scale = (0.085, 0.105, 0.12)
        for c in head.users_collection:
            c.objects.unlink(head)
        ES.col.objects.link(head)
    if ES.P['head'] > 0:
        ES.collider(head)
        if ES.P['hfric'] >= 0:
            head.collision.cloth_friction = ES.P['hfric']
            ES.log('cabeza: friccion', ES.P['hfric'], '(torso/brazos', ES.P['fric'], ')')
    else:
        head.hide_render = True
        ES.log('cabeza: SIN colision (head=0)')
    # e2g T1-C: la cabeza se retira (escala) mientras la capucha cae y vuelve cuando ya cayo; la tela no se toca
    if ES.P['hds'] < 1.0:
        _s0 = (0.085, 0.105, 0.12)
        _ss = tuple((v * ES.P['hds'] for v in _s0))
        for _f, _v in ((1, _s0), (int(ES.P['hd0']), _s0), (int(ES.P['hd1']), _ss), (int(ES.P['hd2']), _ss), (int(ES.P['hd3']), _s0)):
            head.scale = _v
            head.keyframe_insert('scale', frame=_f)
        ES.log('cabeza: escala', ES.P['hds'], 'de f', int(ES.P['hd0']), 'a f', int(ES.P['hd1']), '; vuelve de f', int(ES.P['hd2']), 'a f', int(ES.P['hd3']))
    arms = []
    # e2zw (2026-10-05): MANO. El brazo terminaba a 0,62 m del pivote (seccion 40 x 36 mm) y se cerraba en 20 mm: sin mano. El anillo del puno
    # trabaja a 7-14 mm de ese borde y en e2zv1b lo paso (manga L, f48-f60: radio minimo 47 -> 24, la manga entera cae 30-46 mm y arrastra cuello y ruedo).
    # mano=<m> prolonga el tubo <m> metros con la MISMA seccion (perimetro 239 mm = el de una mano real) y recien ahi lo cierra. mano=0 = identico.
    for sgn in (1, -1):
        secs = [(-0.64, 0.02, 0.02, 0), (-0.62, 0.04, 0.036, 0), (-0.4, 0.046, 0.044, 0), (-0.2, 0.055, 0.052, 0), (-0.05, 0.06, 0.058, 0), (0.0, 0.058, 0.056, 0)]
        if ES.P['mano'] > 0:
            secs = [(-0.64 - ES.P['mano'], 0.02, 0.02, 0), (-0.62 - ES.P['mano'], 0.04, 0.036, 0)] + secs[1:]
        secs = [q for q in secs if q[0] <= ES.P['arm_top']] + [(ES.P['arm_top'] + 0.02, 0.03, 0.03, 0)]
        ar = loft(f"CD_maniqui_brazo_{('R' if sgn > 0 else 'L')}", secs, mirror=ES.P['msym'] > 0 and sgn < 0)
        ar.location = (ES.P['arm_x0'] * sgn, 0, ES.P['arm_z0'])
        ar.rotation_euler = (0, -sgn * math.radians(ES.P['abd_end']), 0)
        ES.collider(ar, th=ES.P['ath'] if ES.P['ath'] >= 0 else None)
        arms.append(ar)
    ES.MANIQUI = [torso, head, *arms]
    if ES.P['mano'] > 0:
        ES.log('brazos: MANO de', ES.P['mano'], 'm (misma seccion 40 x 36 mm que la muneca); el tubo termina a', round(0.64 + ES.P['mano'], 3), 'm del pivote')
    # e2g T2-A: brazo animado abd_end -> arm_end (pre-roll hasta arm_f0, rampa hasta arm_f1)
    # CP11: el hombro del maniqui se abre mientras baja el brazo (hueco de axila constante: en e2i2 cedio la axila a 14 grados)
    # RE: pivote de f1 (donde se armo el V0) -> arm_x0/arm_z0 en arm_f0
    if ES.P['arm_end'] >= 0 and ES.P['arm_end'] != ES.P['abd_end']:
        for ar, sgn in zip(arms, (1, -1)):
            for _f, _a in ((1, ES.P['abd_end']), (int(ES.P['arm_f0']), ES.P['abd_end']), (int(ES.P['arm_f1']), ES.P['arm_end'])):
                ar.rotation_euler = (0, -sgn * math.radians(_a), 0)
                ar.keyframe_insert('rotation_euler', frame=_f)
        ES.log('brazos:', ES.P['abd_end'], '->', ES.P['arm_end'], 'grados entre f', int(ES.P['arm_f0']), 'y f', int(ES.P['arm_f1']))
        if ES.P['arm_x1'] > 0:
            for ar, sgn in zip(arms, (1, -1)):
                _xi = ES.P['arm_xi'] if ES.P['arm_xi'] > 0 else ES.P['arm_x0']
                _zi = ES.P['arm_zi'] if ES.P['arm_zi'] > 0 else ES.P['arm_z0']
                for _f, _x, _z in ((1, _xi, _zi), (int(ES.P['arm_f0']), ES.P['arm_x0'], ES.P['arm_z0']), (int(ES.P['arm_f1']), ES.P['arm_x1'], ES.P['arm_z0'])):
                    ar.location = (_x * sgn, 0, _z)
                    ar.keyframe_insert('location', frame=_f)
            ES.log('brazos: pivote f1 x', ES.P['arm_xi'], 'z', ES.P['arm_zi'], '(-1 = el de arm_f0) | x', ES.P['arm_x0'], 'z', ES.P['arm_z0'], '->', ES.P['arm_x1'], '| espesor', ES.P['ath'] if ES.P['ath'] >= 0 else ES.P['th'], 'entre f', int(ES.P['arm_f0']), 'y f', int(ES.P['arm_f1']))
    # ---- malla: capa interior separada off mm hacia adentro (normal de la cascara) salvo borde y pespuntes -> volumen inicial > 0
    ES.V0 = np.array(ES.D['v'], float)
    ES.F = np.array(ES.D['f'])
    LIN = ES.D['lining']
    VN = np.zeros_like(ES.V0)
    tri = ES.V0[ES.F]
    fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    for j in range(3):
        np.add.at(VN, ES.F[:, j], fn)
    VN /= np.maximum(np.linalg.norm(VN, axis=1, keepdims=True), 1e-12)
    fixed = set(ES.D['border']) | set(ES.D['pinch'])
    for n, nf in LIN.items():
        o = ES.INST[n]['off']
        of = ES.INST[nf]['off']
        cnt = ES.D['groups'][nf][1] - ES.D['groups'][nf][0]
        for k in range(cnt):
            if of + k not in fixed:
                ES.V0[of + k] = ES.V0[o + k] - ES.P['off'] * VN[o + k]
    # e2n: deltoides (ver cabecera). Malla centrada en su origen (la escala crece alrededor del centro); L = espejo del R (msym)
    # Blender 5: acciones por capas/slots
    if ES.P['deltoid'] > 0:
        _dc = np.array([ES.P['dl_x'], ES.P['dl_y'], ES.P['dl_z']])
        _da = np.array([ES.P['dl_a'], ES.P['dl_b'], ES.P['dl_c']])
        _s0 = ES.P['dl_s0']
        _mg = ES.P['th'] + ES.P['cd']
        _es = [(-_da[2] * math.cos(math.pi * j / 16), _da[0] * math.sin(math.pi * j / 16), _da[1] * math.sin(math.pi * j / 16), 0.0) for j in range(1, 16)]
        for sgn in (1, -1):
            dl = loft(f"CD_maniqui_deltoides_{('R' if sgn > 0 else 'L')}", _es, mirror=ES.P['msym'] > 0 and sgn < 0, poles=(-_da[2], _da[2]))
            dl.location = (sgn * _dc[0], _dc[1], _dc[2])
            ES.collider(dl, th=ES.P['ath'] if ES.P['ath'] >= 0 else None)
            ES.MANIQUI.append(dl)
            if _s0 < 1.0:
                for _f, _v in ((1, _s0), (int(ES.P['dl_f']), 1.0)):
                    dl.scale = (_v, _v, _v)
                    dl.keyframe_insert('scale', frame=_f)
                try:
                    for fc in dl.animation_data.action.fcurves:
                        for k in fc.keyframe_points:
                            k.interpolation = 'LINEAR'
                except Exception as e:
                    try:
                        for lay in dl.animation_data.action.layers:
                            for stp in lay.strips:
                                for cb in stp.channelbags:
                                    for fc in cb.fcurves:
                                        for k in fc.keyframe_points:
                                            k.interpolation = 'LINEAR'
                    except Exception as e2:
                        ES.log('deltoides: interpolacion no lineal', e, e2)
            ES._c = _dc * np.array([sgn, 1.0, 1.0])
    
            def _nin(s_):
                return (int(((((ES.V0 - ES._c) / (_da * s_ + _mg)) ** 2).sum(1) < 1.0).sum()), int(((((ES.V0 - ES._c) / (_da * s_)) ** 2).sum(1) < 1.0).sum()))
            ES.log(f"deltoides {('R' if sgn > 0 else 'L')}: centro {np.round(ES._c, 3).tolist()} semiejes {np.round(_da, 3).tolist()} | escala {_s0} en f1 -> 1 en f{int(ES.P['dl_f'])} | arranque: vertices a < th+cd ({_mg * 1000:.0f} mm) / adentro: en f1 {_nin(_s0)} | a escala 1 {_nin(1.0)} | tope z {ES._c[2] + _da[2]:.3f}, afuera x {abs(ES._c[0]) + _da[0]:.3f}")
    # e2o: cuerpo MPFB2 (torso + cabeza) como colisionador; el torso y la cabeza del maniqui quedan sin colision
    # sin caras de cabeza en el npz (ztop) la cabeza sigue siendo la del maniqui
    # distancia al vertice mas cercano (mathutils.kdtree: Blender no trae scipy)
    if ES.BODY:
        _B = np.load(ES.RUTA(ES.BODY))
        _V20 = _B['V20']
        _V8 = _B['V8']
        _Vn = _B['Vin']
        _T = _B['T']
        _cab = _B['cabeza'].astype(bool)
        for _o in (torso, head) if _cab.any() else (torso,):
            for _m in [m for m in _o.modifiers if m.type == 'COLLISION']:
                _o.modifiers.remove(_m)
            _o.hide_viewport = True
            _o.hide_render = True
        BODYOBJ = []
        for _nm, _mk in (('CD_cuerpo_L', ~_cab), ('CD_cuerpo_L_cabeza', _cab)):
            _t = _T[_mk]
            if len(_t) == 0:
                continue
            _u = np.unique(_t)
            _rm = -np.ones(len(_V20), int)
            _rm[_u] = np.arange(len(_u))
            _me = bpy.data.meshes.new(_nm)
            _me.from_pydata(_V20[_u].tolist(), [], _rm[_t].tolist())
            _me.update()
            _ob = bpy.data.objects.new(_nm, _me)
            ES.col.objects.link(_ob)
            _ob.shape_key_add(name='Basis')
            _ka = _ob.shape_key_add(name='angosto', from_mix=False)
            _kb = _ob.shape_key_add(name='brazos_8', from_mix=False)
            for _i, _j in enumerate(_u):
                _ka.data[_i].co = tuple(_Vn[_j])
                _kb.data[_i].co = tuple(_V8[_j])
            for _f, _v in ((1, 1.0), (int(ES.P['bgrow']), 0.0)):
                _ka.value = _v
                _ka.keyframe_insert('value', frame=_f)
            if ES.P['arm_end'] >= 0 and ES.P['arm_end'] != ES.P['abd_end']:
                for _f, _v in ((1, 0.0), (int(ES.P['arm_f0']), 0.0), (int(ES.P['arm_f1']), 1.0)):
                    _kb.value = _v
                    _kb.keyframe_insert('value', frame=_f)
            else:
                _kb.value = 0.0
            try:
                _ad = _me.shape_keys.animation_data
                _fcs = []
                try:
                    _fcs = list(_ad.action.fcurves)
                except Exception as _e_av:
                    ES.avisar1('cuerpo: Action.fcurves no disponible, se leen las capas de la accion', _e_av)
                    for _lay in _ad.action.layers:
                        for _st in _lay.strips:
                            for _cb in _st.channelbags:
                                _fcs += list(_cb.fcurves)
                for _fc in _fcs:
                    if 'angosto' in _fc.data_path:
                        for _k in _fc.keyframe_points:
                            _k.interpolation = 'LINEAR'
            except Exception as _e:
                ES.log('cuerpo: interpolacion del angosto no lineal', _e)
            ES.collider(_ob, th=ES.P['bth'] if ES.P['bth'] >= 0 else None)
            if _nm.endswith('cabeza') and ES.P['hfric'] >= 0:
                _ob.collision.cloth_friction = ES.P['hfric']
            elif ES.P['tfric'] >= 0:
                _ob.collision.cloth_friction = ES.P['tfric']
                ES.TFOBJ.append(_ob)
            ES.MANIQUI.append(_ob)
            BODYOBJ.append(_ob)
        import mathutils.kdtree
    
        def _nearest(_A, _Q):
            _t = mathutils.kdtree.KDTree(len(_A))
            for _i, _p in enumerate(_A):
                _t.insert(tuple(_p), _i)
            _t.balance()
            return np.array([_t.find(tuple(_q))[2] for _q in _Q])
        _dmin = _nearest(_Vn, ES.V0)
        _d1 = _nearest(_V20, ES.V0)
        ES.log(f"cuerpo {ES.BODY}: {len(_V20)} vertices, {len(_T)} triangulos ({int(_cab.sum())} de cabeza, friccion {ES.P['hfric']}) | th {(ES.P['bth'] if ES.P['bth'] >= 0 else ES.P['th'])} | angosto 1 en f1 -> 0 en f{int(ES.P['bgrow'])} | brazos_8 f{int(ES.P['arm_f0'])}->f{int(ES.P['arm_f1'])} | campera -> vertice del cuerpo mas cercano: angosto min {_dmin.min() * 1000:.1f} mm, completo min {_d1.min() * 1000:.1f} mm (vertices a < 12 mm del completo: {int((_d1 < 0.012).sum())}) | torso del maniqui SIN colision; cabeza del maniqui {('SIN colision' if _cab.any() else 'CON colision (npz sin cabeza)')}")
    _regla(ES, "sandwich_rotar_caras")


def tela(ES):
    """Objeto de tela, reposo (molde plano / rampa rk), presion por bolsillo, grupos de rigidez, cascara y embebido. (sim_e2s.py L306-L536)"""
    ES.NV0 = ES.NV
    ES.SEPV = []
    ES.SEP_REST = {}
    _regla(ES, "broches_con_altura")
    ES.me = bpy.data.meshes.new('CD_campera')
    ES.me.from_pydata(ES.V0.tolist(), ES.D['sew'], ES.D['f'])
    ES.gar = bpy.data.objects.new('CD_campera', ES.me)
    ES.col.objects.link(ES.gar)
    for name, (a, b) in ES.D['groups'].items():
        vg = ES.gar.vertex_groups.new(name=name)
        vg.add(list(range(a, b)), 1.0, 'REPLACE')
    # reposo = molde plano desde f2 (Dynamic Mesh)
    ES.gar.shape_key_add(name='Basis')
    ES.kc = ES.gar.shape_key_add(name='molde_plano', from_mix=False)
    for i, (u, w) in enumerate(ES.D['uv']):
        ES.kc.data[i].co = (u / 1000.0, w / 1000.0, 0.0)
    # e2zd: reposo del separador = el mismo tetraedro (no es plano)
    for i, co_ in ES.SEP_REST.items():
        ES.kc.data[i].co = co_
    _regla(ES, "sandwich_reposo")
    # RG (2026-10-09, CP78): hrest=<npz> (ids, co en m; _qc_RG/mk_hrest.py) -> REPOSO EN FORMA: esos vertices de la clave molde_plano pasan a una forma 3D ISOMETRICA al molde
    #   (doblado desarrollable: mismos largos de reposo, cambian solo los angulos de reposo). Sin hrest = identico (copia previa: _papelera/sim_e2s_pre_RG.py).
    if ES.HREST:
        assert ES.P['cinch'] <= 0, 'hrest con cinch > 0: la clave cordon reescribe el molde plano de todos los vertices (reaplicar hrest ahi)'
        _hz = np.load(ES.RUTA(ES.HREST))
        _hi = _hz['ids'].astype(int)
        _hco = _hz['co'].astype(float)
        assert len(_hi) == len(_hco) and int(_hi.max()) < ES.NV0, ('hrest: la malla no coincide', len(_hi), ES.NV0)
        _mp = np.array([ES.kc.data[int(_i)].co[:] for _i in _hi])
        for _i, ES._c in zip(_hi, _hco):
            ES.kc.data[int(_i)].co = (float(ES._c[0]), float(ES._c[1]), float(ES._c[2]))
        _gn = sorted(set((_n for _n, (_a, _b) in ES.D['groups'].items() for _i in (int(_hi.min()), int(_hi.max())) if _a <= _i < _b)))
        ES.log(f'REPOSO EN FORMA (RG): {ES.HREST} | {len(_hi)} vertices de {_gn} | z del reposo {1000 * _hco[:, 2].min():.0f}..{1000 * _hco[:, 2].max():.0f} mm (molde plano: {1000 * _mp[:, 2].min():.0f}..{1000 * _mp[:, 2].max():.0f})')
    # e2zf: fmp=N -> el reposo queda FIJO en V0 (Basis) hasta fN (control: separar arranque fuera de equilibrio de cambio de reposo); 2 = identico
    FMP = int(ES.P['fmp'])
    # e2ze: reposo en rampa ARAP (ver cabecera)
    if ES.RK:
        _KZ = np.load(ES.RUTA(ES.RK))['keys']
        _nk = len(_KZ)
        _f0 = int(ES.P['rk_f0'])
        _df = int(ES.P['rk_df'])
        FMP = _f0 + _nk * _df
        assert _KZ.shape[1] == ES.NV0, ('rk: la malla no coincide', _KZ.shape, ES.NV0)
        for _k in range(_nk):
            _kk = ES.gar.shape_key_add(name=f'rk{_k + 1}', from_mix=False)
            _co = np.array(ES.V0, float).copy()
            _co[:ES.NV0] = _KZ[_k]
            for i, co_ in ES.SEP_REST.items():
                _co[i] = co_
            _kk.data.foreach_set('co', _co.ravel())
            for ES.f, v in ((1, 0.0), (_f0 + _k * _df, 1.0), (_f0 + (_k + 1) * _df, 0.0)):
                _kk.value = v
                _kk.keyframe_insert('value', frame=ES.f)
        ES.log(f'RAMPA DE REPOSO (e2ze): {ES.RK} | {_nk} claves ARAP desde f{_f0}, una cada {_df} cuadros | molde_plano = 1 en f{FMP}')
    for ES.f, v in ((1, 0.0), (FMP, 1.0)):
        ES.kc.value = v
        ES.kc.keyframe_insert('value', frame=ES.f)
    ES.log(f"molde_plano = 1 en f{FMP} (fmp {int(ES.P['fmp'])}, rk {bool(ES.RK)})")
    if ES.P['nrb'] > 0:
        ES.log(f"NRB (e2zi): el lazo de volumen no reescribe 'presion' -> sin reconstrucciones del Cloth ni cuadros muertos" + (' | OJO: pres > 0 con pesos congelados' if ES.P['pres'] > 0 else ''))
    ad = ES.gar.data.shape_keys.animation_data
    # e2zi (2026-10-01) BUG de Blender 5.x: Action.fcurves ya no existe (acciones por capas) -> el try viejo fallaba ('interp ... no attribute fcurves', 190 de 200
    #   logs) y las claves de reposo quedaban en BEZIER. Con 2 claves (molde_plano 1->2) no cambia nada en cuadros enteros, pero con la rampa rk los pesos se
    #   SUMAN (f12: molde 0,5 + 4 claves rk ~0,6-0,9 = 3,6) -> reposo basura -> presim e2zh invalida (230 mm, 137 k cruces). Ahora: capas/canales, CONSTANT solo
    #   en molde_plano y rk* (el cordon, si cinch > 0, sigue con su rampa), y log de los pesos por cuadro (suma 1 desde f2). Copia previa: _papelera/sim_e2s_pre_e2zi.py
    try:
        _fcs = []
        try:
            _fcs = list(ad.action.fcurves)
        except Exception as _e_av:
            ES.avisar1('reposo: Action.fcurves no disponible, se leen las capas de la accion', _e_av)
            for _lay in ad.action.layers:
                for _st in _lay.strips:
                    for _cb in _st.channelbags:
                        _fcs += list(_cb.fcurves)
        _rfc = [fc for fc in _fcs if 'key_blocks["molde_plano"]' in fc.data_path or 'key_blocks["rk' in fc.data_path]
        for fc in _rfc:
            for k in fc.keyframe_points:
                k.interpolation = 'CONSTANT'
        _wl = []
        for _f in range(1, min(FMP + 2, 61)):
            _w = {fc.data_path.split('"')[1]: fc.evaluate(_f) for fc in _rfc}
            _nz = {k_: round(v_, 4) for k_, v_ in _w.items() if abs(v_) > 1e-09}
            _wl.append(f'f{_f} {_nz} suma {sum(_w.values()):.4f}')
        ES.log(f'interp CONSTANT en {len(_rfc)} curvas de reposo de {len(_fcs)} | pesos por cuadro: ' + ' ; '.join(_wl))
    except Exception as e:
        ES.log('interp', e)
    _regla(ES, "cordon")
    # ---- bolsillos: caras por bolsillo (centroide en el molde -> canal), area y volumen objetivo
    UV = np.array(ES.D['uv'])
    PK = ES.D['pocket']
    LX = ES.D['lx']
    ES.face_pk = np.full(len(ES.F), -1)
    ES.names = sorted(ES.D['pocket_area_m2'])
    ES.idx = {n: i for i, n in enumerate(ES.names)}
    for n in ES.RD['piezas_inyectadas']:
        for nm in (n, n + '_f'):
            I = ES.INST[nm]
            a, b = (I['foff'], I['foff'] + I['nf'])
            cx = UV[ES.F[a:b]].mean(1)[:, 0]
            ch = (np.array(LX[I['key']])[None, :] < cx[:, None]).sum(1)
            ES.face_pk[a:b] = [ES.idx[f'{n}{c}'] for c in ch]
    ES.AREA = np.array([ES.D['pocket_area_m2'][n] for n in ES.names])
    HK = np.array([ES.P['h_sl'] if n.startswith(ES.MANGA) else ES.P['h_body'] for n in ES.names])
    ES.VT = ES.AREA * (4.0 / 3.0) * HK * ES.P['vtk']
    ES.vpk = collections.defaultdict(list)
    for i, pk in enumerate(PK):
        if pk is not None and pk in ES.idx:
            ES.vpk[ES.idx[pk]].append(i)
    PLACK = set(ES.D['placket'])
    for k in ES.vpk:
        ES.vpk[k] = [i for i in ES.vpk[k] if i not in PLACK]
    ES.W = np.full(len(ES.names), ES.P['w0'])
    # e2zj: pesos de presion por bolsillo FIJOS desde f1 (los finales de un humo de control: bolsillos_<tag>.json); con nrb=1 no se reescriben
    if ES.WINI:
        _wj = json.load(open(ES.RUTA(ES.WINI)))
        assert list(_wj['names']) == list(ES.names), 'wini: otros bolsillos'
        ES.W = np.array(_wj['w'], float)
        ES.log('WINI (e2zj): pesos de presion fijos desde', ES.WINI, '| min/med/max', round(float(ES.W.min()), 3), round(float(np.median(ES.W)), 3), round(float(ES.W.max()), 3))
    vpres = ES.gar.vertex_groups.new(name='presion')
    # e2h (consulta B): franja bajo la axila (cuerpo: z_ax - banda .. z_ax, costado |x| > 0,12; manga: mitad interna, z > z_ax - 0,25): el objetivo de
    # volumen de su parte del bolsillo y su peso de presion bajan en rampa 1 -> uarm, sincronizados con el brazo (arm_f0 -> arm_f1). El plumon real se comprime.
    ES.UA_IDS = set()
    ES.FR = np.zeros(len(ES.names))
    ES.MF = [1.0]
    _regla(ES, "franja_axila")
    # e2zb cf_hold: factor por bolsillo (1 = sin retener)
    ES.HOLD = np.ones(len(ES.names))
    ES.HK_ = []
    _regla(ES, "retener_bolsillos_cf")
    def set_weights():
        for k, ids in ES.vpk.items():
            wk = float(ES.W[k]) if ES.HOLD[k] >= 1.0 else max(float(ES.W[k] * ES.HOLD[k]), 0.0001)
            if ES.FR[k] > 0 and ES.MF[0] < 1.0:
                a_ = [i for i in ids if i not in ES.UA_IDS]
                b_ = [i for i in ids if i in ES.UA_IDS]
                if a_:
                    vpres.add(a_, wk, 'REPLACE')
                if b_:
                    vpres.add(b_, wk * ES.MF[0], 'REPLACE')
            else:
                vpres.add(ids, wk, 'REPLACE')
    ES.set_weights = set_weights
    ES.set_weights()
    if PLACK:
        vpres.add(sorted(PLACK), 0.0, 'REPLACE')
    ES.vrig = ES.gar.vertex_groups.new(name='rigidez')
    ES.vrig.add(ES.D['zipper'], 1.0, 'REPLACE')
    ES.vrig.add(ES.D['placket'], ES.P['w_plk'], 'REPLACE')
    if ES.P['w_plk'] != 1.0:
        ES.log('tapeta: peso de rigidez', ES.P['w_plk'], '(1 = flexion max, como el cierre)')
    # e2m: bug de e2k arreglado (el puno quedaba dentro del if de w_plk); cuff_on=0 reproduce e2k..e2m3
    if ES.P['cuff_on'] > 0:
        ES.vrig.add(ES.D['cuff'], ES.P['w_cuff'], 'REPLACE')
    ES.log('RIGIDEZ tapeta w_plk', ES.P['w_plk'], '-> flexion', round(ES.P['bending'] + (ES.P['bend_max'] - ES.P['bending']) * ES.P['w_plk'], 1), '| puno:', 'w_cuff %s' % ES.P['w_cuff'] if ES.P['cuff_on'] > 0 else 'SIN peso (flexion base, como e2k-e2m3)')
    BAND = [i for n in ES.D['band'].values() for i in range(*ES.D['groups'][n])]
    ES.vrig.add(BAND, ES.P['w_band'], 'REPLACE')
    # e2g: rigidez por franja REAL (rig_e2g.py): columna del cuello chimenea (hs bajo la vista + ht) y franja de margenes de la costura de sisa
    if ES.D.get('rig_cuello') and ES.P['w_neck'] > 0:
        ES.vrig.add(ES.D['rig_cuello'], ES.P['w_neck'], 'REPLACE')
        ES.log('rigidez cuello', len(ES.D['rig_cuello']), 'peso', ES.P['w_neck'])
    if ES.D.get('rig_sisa') and ES.P['w_sisa'] > 0:
        ES.vrig.add(ES.D['rig_sisa'], ES.P['w_sisa'], 'REPLACE')
        ES.log('rigidez sisa', len(ES.D['rig_sisa']), 'peso', ES.P['w_sisa'])
    if ES.D.get('rig_costado') and ES.P.get('w_cost', 0.0) > 0:
        ES.vrig.add(ES.D['rig_costado'], ES.P['w_cost'], 'REPLACE')
        ES.log('rigidez costado (e2x: margenes de la costura del costado)', len(ES.D['rig_costado']), 'peso', ES.P['w_cost'])
    # e2i: que es "capucha" para hood_bend/hood_soft. hood_scope=1: hs fuera de la huella del ht + hc (el cuello chimenea = hs bajo el ht + ht,
    # que en la real lleva cascara + guata + vista, queda con la rigidez del cuerpo); hood_scope=0: hs + hc + ht (como e2h4/e2h6)
    _regla(ES, "zona_capucha")
    # e2h: flexion propia de la capucha (hs, hc, ht); el resto conserva su flexion efectiva b = bending + (max - bending) w
    if ES.P['hood_bend'] >= 0:
        _b0, _bm = (ES.P['bending'], ES.P['bend_max'])
        _hb = ES.P['hood_bend']
        _W = np.zeros(ES.NV)
        for _gn in ('rigidez',):
            _vg = ES.gar.vertex_groups[_gn]
            for _v in ES.gar.data.vertices:
                for _g in _v.groups:
                    if _g.group == _vg.index:
                        _W[_v.index] = _g.weight
        _Wn = (_b0 + (_bm - _b0) * _W - _hb) / (_bm - _hb)
        _HOOD = ES.HOODSET
        _Wn[list(_HOOD)] = 0.0
        for _i in range(ES.NV):
            ES.vrig.add([_i], float(_Wn[_i]), 'REPLACE')
        ES.P['bending'] = _hb
        ES.log('flexion: capucha', _hb, '| resto igual (peso remapeado; base', _b0, '->', _hb, ')')
    # e2q PLANCHA: capucha mas rigida a la flexion que la base (panel de 3 capas: cascara + guata + forro)
    if ES.P.get('pl_bh', -1.0) > 0:
        assert ES.P['hood_bend'] < 0, 'pl_bh requiere hood_bend < 0 (hood_bend remapea la base hacia abajo)'
        _wh = (ES.P['pl_bh'] - ES.P['bending']) / (ES.P['bend_max'] - ES.P['bending'])
        ES.vrig.add(sorted(ES.HOODSET), float(_wh), 'REPLACE')
        ES.log('PLANCHA capucha: flexion', ES.P['pl_bh'], '(peso', round(_wh, 5), ') en', len(ES.HOODSET), 'vertices | cuello w_neck', ES.P['w_neck'], '-> flexion', round(ES.P['bending'] + (ES.P['bend_max'] - ES.P['bending']) * ES.P['w_neck'], 1), '| tapeta w_plk', ES.P['w_plk'], '| compresion capucha', 'blanda' if ES.P['hood_soft'] > 0 else ES.P['compression'])
    _regla(ES, "cuello_flexion_por_capa")
    _regla(ES, "cuello_rampa_costuras")
    if ES.SEPV:
        ES.vrig.add(ES.SEPV, 1.0, 'REPLACE')
        ES.log(f"broches con altura: flexion del separador {ES.P['bend_max']} (peso 1) en {len(ES.SEPV)} vertices")
    ES.log('bolsillos', len(ES.names), 'VT litros', np.round(ES.VT * 1000, 2).tolist())
    ES.log('rigidez: cierre', len(ES.D['zipper']), 'tapeta', len(ES.D['placket']), 'puno', len(ES.D['cuff']), 'cinta puno', len(BAND))
    # e2b: capa interior ([material]) blanda a la compresion y embebido del pespunte (encoge la linea de acolchado: el valle entra)
    ES.vcas = ES.gar.vertex_groups.new(name='cascara')
    ES.shell_ids = [i for n, (a, b) in ES.D['groups'].items() if not n.endswith('_f') for i in range(a, b)]
    ES.vcas.add(ES.shell_ids, 1.0, 'REPLACE')
    # e2h: capucha sin rigidez a la compresion en el plano (como la capa interior): la tela real pandea sin resistencia
    if ES.P['hood_soft'] > 0:
        _hood = sorted(ES.HOODSET)
        ES.vcas.add(_hood, 0.0, 'REPLACE')
        ES.log('capucha: compresion blanda', ES.P['soft'], 'en', len(_hood), 'vertices')
    venc = ES.gar.vertex_groups.new(name='encoge')
    ES.SMAX = max(ES.P['S_body'], ES.P['S_sl'], 1e-06)
    pin_sl = [i for i in ES.D['pinch'] if PK[i] is not None and PK[i].startswith(ES.MANGA)]
    pin_bd = [i for i in ES.D['pinch'] if PK[i] is not None and (not PK[i].startswith(ES.MANGA))]
    venc.add(pin_bd, ES.P['S_body'] / ES.SMAX, 'REPLACE')
    venc.add(pin_sl, ES.P['S_sl'] / ES.SMAX, 'REPLACE')
    ES.log('capa interior blanda', ES.P['soft'], 'embebido pespunte cuerpo/manga', ES.P['S_body'], ES.P['S_sl'], 'vertices', len(pin_bd), len(pin_sl))


def cloth(ES):
    """Esfera de barrido, modificador Cloth, presion animada, colision y autocolision, calidad, friccion por tiempo, gravedad. (sim_e2s.py L537-L774)"""
    # e2i (consulta A, paso 2): esfera colisionadora invisible que barre de delante de la coronilla a la espalda (sw_f0 -> sw_f1) y sale (-> sw_f2)
    ES.SWEEP = None
    # CP11: por la linea media, de delante de la frente sobre la coronilla, atras y abajo por la nuca hasta la espalda alta,
    # y sale HACIA ATRAS en horizontal y despacio (la 1 salia hacia arriba a 7 cm/cuadro). Cuadros fijos 6-12-20-28-34-44.
    # Blender 5: acciones por capas/slots
    if ES.P['sweep'] > 0:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=ES.P['sw_r'], location=(0, -0.21, 1.92))
        ES.SWEEP = bpy.context.active_object
        ES.SWEEP.name = 'CD_barrido_esfera'
        for c in ES.SWEEP.users_collection:
            c.objects.unlink(ES.SWEEP)
        ES.col.objects.link(ES.SWEEP)
        ES.collider(ES.SWEEP, th=ES.P['sw_th'])
        f0, f1, f2 = (int(ES.P['sw_f0']), int(ES.P['sw_f1']), int(ES.P['sw_f2']))
        fa = f0 + round(0.28 * (f1 - f0))
        fb = f0 + round(0.6 * (f1 - f0))
        KEYS = ((1, (0, -0.21, 1.92)), (f0, (0, -0.21, 1.92)), (fa, (0, -0.02, 1.9)), (fb, (0, 0.18, 1.74)), (f1, (0, 0.36, 1.5)), (f2, (0, 0.8, 1.75)))
        if ES.P['sw_path'] == 2:
            KEYS = ((1, (0, -0.25, 1.95)), (6, (0, -0.25, 1.95)), (12, (0, -0.05, 1.93)), (20, (0, 0.14, 1.84)), (28, (0, 0.3, 1.62)), (34, (0, 0.34, 1.5)), (44, (0, 0.75, 1.5)))
            ES.P['sw_f0'], ES.P['sw_f2'] = (6, 44)
        for _f, _p in KEYS:
            ES.SWEEP.location = _p
            ES.SWEEP.keyframe_insert('location', frame=_f)
        try:
            for fc in ES.SWEEP.animation_data.action.fcurves:
                for k in fc.keyframe_points:
                    k.interpolation = 'LINEAR'
        except Exception as e:
            try:
                for lay in ES.SWEEP.animation_data.action.layers:
                    for stp in lay.strips:
                        for cb in stp.channelbags:
                            for fc in cb.fcurves:
                                for k in fc.keyframe_points:
                                    k.interpolation = 'LINEAR'
            except Exception as e2:
                ES.log('barrido: interpolacion no lineal', e, e2)
        ES.MANIQUI.append(ES.SWEEP)
        _d0 = np.linalg.norm(ES.V0 - np.array(KEYS[0][1]), axis=1)
        ES.log('barrido: esfera r', ES.P['sw_r'], 'espesor', ES.P['sw_th'], 'keys', KEYS, '| arranque: vertices a < r+th+cd del centro:', int((_d0 < ES.P['sw_r'] + ES.P['sw_th'] + ES.P['cd']).sum()), 'min', round(float(_d0.min() - ES.P['sw_r']) * 1000, 1), 'mm de la superficie')
    ES.cm = ES.gar.modifiers.new('cloth', 'CLOTH')
    ES.s = ES.cm.settings
    ES.s.quality = int(ES.P['quality'])
    ES.s.mass = ES.P['mass']
    ES.s.air_damping = ES.P['air']
    ES.s.tension_stiffness = ES.P['tension']
    ES.s.compression_stiffness = ES.P['compression']
    ES.s.shear_stiffness = ES.P['shear']
    ES.s.bending_stiffness = ES.P['bending']
    ES.s.use_sewing_springs = True
    ES.s.sewing_force_max = ES.P['sew_max']
    ES.s.use_dynamic_mesh = True
    ES.s.vertex_group_bending = 'rigidez'
    ES.s.bending_stiffness_max = ES.P['bend_max']
    # e2j: entretela = compresion ent_c en la franja del cuello; cascara sigue en compression
    if ES.P['soft'] > 0:
        ES.s.vertex_group_structural_stiffness = 'cascara'
        ES.s.tension_stiffness_max = ES.P['tension']
        ES.s.compression_stiffness_max = ES.P['compression']
        ES.s.compression_stiffness = ES.P['soft']
        if ES.P['ent_c'] > ES.P['compression'] and ES.D.get('rig_cuello'):
            _cue = sorted(set(ES.D['rig_cuello']))
            _ws = (ES.P['compression'] - ES.P['soft']) / (ES.P['ent_c'] - ES.P['soft'])
            ES.vcas.add(ES.shell_ids, _ws, 'REPLACE')
            if ES.P['hood_soft'] > 0:
                ES.vcas.add(sorted(ES.HOODSET), 0.0, 'REPLACE')
            ES.vcas.add(_cue, 1.0, 'REPLACE')
            ES.s.compression_stiffness_max = ES.P['ent_c']
            ES.log('entretela cuello: compresion', ES.P['ent_c'], 'en', len(_cue), 'vertices (rig_cuello) | cascara peso', round(_ws, 4), '->', ES.P['compression'], '| traccion', ES.P['tension'], 'igual | flexion sin tocar')
    # e2q PLANCHA: compresion de panel de la capucha
    if ES.P['soft'] > 0 and ES.P.get('pl_hc', -1.0) > ES.P['compression'] and (ES.P['ent_c'] <= ES.P['compression']):
        assert ES.P['hood_soft'] <= 0, 'pl_hc requiere hood_soft=0'
        _ws = (ES.P['compression'] - ES.P['soft']) / (ES.P['pl_hc'] - ES.P['soft'])
        ES.vcas.add(ES.shell_ids, _ws, 'REPLACE')
        ES.vcas.add(sorted(ES.HOODSET), 1.0, 'REPLACE')
        ES.s.compression_stiffness_max = ES.P['pl_hc']
        ES.log('PLANCHA capucha: compresion', ES.P['pl_hc'], 'en', len(ES.HOODSET), 'vertices | cascaras peso', round(_ws, 4), '->', ES.P['compression'], '| capa interior', ES.P['soft'], '| traccion', ES.P['tension'], 'igual')
    if ES.SEPV and ES.P['soft'] > 0:
        ES.vcas.add(ES.SEPV, 1.0, 'REPLACE')
        ES.log(f'broches con altura: compresion del separador {ES.s.compression_stiffness_max} (peso 1), traccion {ES.s.tension_stiffness_max}')
    ES.s.shrink_min = 0.0
    ES.s.shrink_max = ES.SMAX
    ES.s.vertex_group_shrink = 'encoge'
    ES.s.use_pressure = ES.P['pres'] > 0
    ES.s.uniform_pressure_force = ES.P['p0']
    ES.s.pressure_factor = 1.0
    ES.s.vertex_group_pressure = 'presion'
    # e2zj: presion por OTRA VIA (sin tocar grupos): uniform_pressure_force animada = p0 x mediana(W control en f) / mediana(W control final)
    if ES.PRAMP and ES.s.use_pressure:
        _cj = json.load(open(ES.RUTA(ES.PRAMP)))['ctrl']
        _mf = float(np.median(_cj[-1][2]))
        _ks = [(1, ES.P['w0'] / _mf)] + [(int(c_[0]) + 1, float(np.median(c_[2])) / _mf) for c_ in _cj]
        for _f, _r in _ks:
            ES.s.uniform_pressure_force = ES.P['p0'] * _r
            ES.s.keyframe_insert('uniform_pressure_force', frame=_f)
        ES.log('PRAMP (e2zj): uniform_pressure_force animada (cuadro, factor):', [(f_, round(r_, 3)) for f_, r_ in _ks])
    ES.PF = None
    # e2zl: presion global = trayectoria de la COMPLETA de referencia (rank-1 con w = WINI) + lazo opcional (ver cabecera)
    # con pramp: sus claves (BEZIER, = e2zk1) hasta pfb_f0
    if ES.PFIT and ES.s.use_pressure:
        assert ES.P['nrb'] > 0 and ES.WINI and (ES.P['pfb'] > 0 or not ES.PRAMP), 'pfit requiere nrb=1, wini= (y pfb > 0 si va con pramp)'
        _rj = json.load(open(ES.RUTA(ES.PFIT)))
        assert list(_rj['names']) == list(ES.names), 'pfit: otros bolsillos'
        _rf = np.array([c_[0] for c_ in _rj['ctrl']], int)
        _rW = np.array([c_[2] for c_ in _rj['ctrl']], float)
        _rR = np.array([float(np.median(c_[1])) for c_ in _rj['ctrl']])
        _den = float((ES.AREA * ES.W * ES.W).sum())
        _g = (_rW * (ES.AREA * ES.W)[None, :]).sum(1) / _den
        _g1 = float((ES.AREA * ES.P['w0'] * ES.W).sum()) / _den
        _sm = int(ES.P['pfb_sm'])
        _rRs = np.array([_rR[max(0, i_ - _sm):i_ + _sm + 1].mean() for i_ in range(len(_rR))])
        _kk = [] if ES.PRAMP else [(1, _g1)] + [(int(f_) + 1, float(g_)) for f_, g_ in zip(_rf, _g) if ES.P['pfb'] <= 0 or f_ + 1 <= ES.P['pfb_f0']]
        for _f, _r in _kk:
            ES.s.uniform_pressure_force = ES.P['p0'] * _r
            ES.s.keyframe_insert('uniform_pressure_force', frame=_f)
        _afc = []
        for _lay in ES.gar.animation_data.action.layers:
            for _st in _lay.strips:
                for _cb in _st.channelbags:
                    _afc += [fc for fc in _cb.fcurves if fc.data_path.endswith('uniform_pressure_force')]
        assert len(_afc) == 1, f'pfit: {len(_afc)} F-curves de uniform_pressure_force'
        if not ES.PRAMP:
            for _kp in _afc[0].keyframe_points:
                _kp.interpolation = 'CONSTANT'
        ES.PF = dict(f=_rf, g=_g, rr=_rR, rrs=_rRs, c=1.0, fc=_afc[0], log=[])
        ES.log(f'PFIT (e2zl): referencia {ES.PFIT} ({len(_rf)} controles f{_rf[0]}-f{_rf[-1]}) | w = WINI | g(f) rank-1 por area: f1 {_g1:.3f} ' + ' '.join((f'f{f_} {g_:.3f}' for f_, g_ in zip(_rf, _g) if f_ % 12 == 0 or f_ in (3, 6))) + (f' | claves previas {len(_kk)} (hasta f{_kk[-1][0]}) CONSTANT' if _kk else f' | claves previas = PRAMP {ES.PRAMP} ({len(_afc[0].keyframe_points)}, sin tocar)') + (f" | LAZO pfb {ES.P['pfb']} desde f{int(ES.P['pfb_f0'])} clip {ES.P['pfb_clip']} media movil {2 * _sm + 1} controles" if ES.P['pfb'] > 0 else ' | sin lazo'))
        ES.log('PFIT evaluado en la F-curve (cuadro: factor):', ' '.join((f"f{f_}:{_afc[0].evaluate(f_) / ES.P['p0']:.3f}" for f_ in (1, 2, 3, 4, 5, 7, 10, 19, 28, 31, 40, 61, 100, 193))))
    ES.log('presion:', 'PRENDIDA' if ES.s.use_pressure else 'APAGADA (use_pressure False)', '| p0', ES.s.uniform_pressure_force, '| grupo', repr(ES.s.vertex_group_pressure), '| factor', ES.s.pressure_factor)
    _regla(ES, "sandwich_resortes_internos")
    cs = ES.cm.collision_settings
    cs.collision_quality = 3
    cs.distance_min = ES.P['cd']
    cs.use_self_collision = False
    # e2d: tapeta sobre el fcL sin atravesarlo (solo esas zonas; sin forro, sin bordes cosidos)
    # OJO: en Blender este grupo EXCLUYE (triangulos con todos sus vertices en el grupo no autocolisionan) -> se carga el complemento
    # e2g T2-A: colision manga-cuerpo (solo cascaras, a > 12 mm de los bordes): manga entera y costados del cuerpo bajo la axila
    # e2q: sa_brd = franja sin autocolision junto a los bordes (mm de molde; 12 = como e2g-e2p)
    # e2h: la vista choca con la CASCARA (no con la capa interior: con la franja del fc en el grupo, chocarian cascara e interior)
    # sin scipy en el Python de Blender: KDTree de mathutils (puntos 2D o 3D)
    # bordes cosidos: CF, hombro, escote
    # e2i: la capucha se apoya en la espalda y los hombros sin atravesarlos (solo cascaras, a > 12 mm de los bordes)
    # contorno de la pieza en la malla (aristas con una sola cara): D["border"] no trae la capucha (no tiene capa interior)
    # e2zc DIAGNOSTICO: la tapeta sin autocolision (sigue cosida y con broches) -> si la deriva del CF a L se va, la empuja el choque de la tp
    if ES.P['selfcol'] > 0 and ES.D.get('autocol'):
        ES.keep = set(ES.D['autocol'])
        _regla(ES, "autocol_manga_cuerpo")
        _regla(ES, "autocol_vista")
        _regla(ES, "autocol_capucha")
        ES.keep -= ES.TPV
        _regla(ES, "autocol_tapeta_diagnostico")
        vac = ES.gar.vertex_groups.new(name='sin_autocol')
        vac.add([i for i in range(ES.NV) if i not in ES.keep], 1.0, 'REPLACE')
        cs.use_self_collision = True
        cs.self_distance_min = ES.P['self_d']
        cs.self_friction = ES.P['sf']
        cs.vertex_group_self_collisions = 'sin_autocol'
        ES.log('autocolision', len(ES.D['autocol']), 'vertices, distancia', ES.P['self_d'])
    elif ES.P['selfcol'] > 0:   # [ESC·f535] 10-11: M1194 y W2094 corrieron 22 rondas sin autocolision y sin aviso
        ES.log('AVISO: selfcol', ES.P['selfcol'], 'pero la malla no trae autocol -> SIN autocolision (falta construccion)')
    # e2s DIAGNOSTICO (no es construccion): el cuello (hs bajo la vista + ht) sin colision con el cuerpo
    if ES.P['noobj_neck'] > 0 and ES.D.get('rig_cuello'):
        vno = ES.gar.vertex_groups.new(name='sin_colobj')
        vno.add(sorted(set(ES.D['rig_cuello'])), 1.0, 'REPLACE')
        cs.vertex_group_object_collisions = 'sin_colobj'
        ES.log('DIAGNOSTICO: cuello sin colision con el cuerpo:', len(set(ES.D['rig_cuello'])), 'vertices | grupo', repr(cs.vertex_group_object_collisions))
    if ES.TPV:
        vpin = ES.gar.vertex_groups.new(name='pin')
        vpin.add(sorted(ES.TPV), 1.0, 'REPLACE')
        ES.s.vertex_group_mass = 'pin'
        ES.log('tapeta: pin en', len(ES.TPV), 'vertices')
    ES.cm.point_cache.frame_start = 1
    ES.cm.point_cache.frame_end = ES.NF
    # e2i: colision mas fina solo mientras la esfera se mueve (27-37 mm/cuadro)
    if ES.SWEEP is not None:
        try:
            for _f, ES._c in ((1, 3), (int(ES.P['sw_f0']), 5), (int(ES.P['sw_f2']) + 3, 5), (int(ES.P['sw_f2']) + 4, 3)):
                cs.collision_quality = ES._c
                cs.keyframe_insert('collision_quality', frame=_f)
            ES.log('barrido: calidad de colision 5 entre f', int(ES.P['sw_f0']), 'y f', int(ES.P['sw_f2']) + 3)
        except Exception as e:
            ES.log('barrido: calidad de colision no animada', e)
    # e2g T2-A: calidad y colision mas finas solo en la ventana del movimiento
    if ES.P['q_ramp'] > 0 and ES.P['arm_end'] >= 0:
        try:
            for _f, _q, ES._c in ((1, int(ES.P['quality']), 3), (int(ES.P['arm_f0']), int(ES.P['q_ramp']), 5), (int(ES.P['arm_f1']) + 6, int(ES.P['q_ramp']), 5), (int(ES.P['arm_f1']) + 12, int(ES.P['quality']), 3)):
                ES.s.quality = _q
                ES.s.keyframe_insert('quality', frame=_f)
                cs.collision_quality = ES._c
                cs.keyframe_insert('collision_quality', frame=_f)
            ES.log('calidad animada', int(ES.P['quality']), '->', int(ES.P['q_ramp']), 'en la rampa')
        except Exception as e:
            ES.log('calidad animada: no se pudo', e)
    # e2zz (2026-10-08, CP67): q_ini=<n> [q_ini_f=<F>, 12] -> MAS PASOS DEL SOLVER SOLO EN f1..F (golpe del reposo f1 -> f2: la axila pasa de area 0,58 a 1,0 del molde
    #   en un cuadro y el pliegue queda dado vuelta). Medido (_qc_e2zz/t_quality.py, Blender 5.1): el Cloth fija dt = 1/quality al CREARSE; una clave de 'quality' sola
    #   no cambia nada (bit a bit) y recien entra en la siguiente RECONSTRUCCION (aca el lazo de presion reescribe 'presion' cada K cuadros: f4, f7, f10, f13...).
    #   Claves cuadro a cuadro, CONSTANT: n hasta F y el calendario que ya habia (evaluado ANTES de tocarlo, en float) desde F + 1. El log 'QINI' lee el dt REAL del
    #   Cloth evaluado (ClothSimSettings + 32; layout validado con Cvi, gravedad y masa). q_ini=0 = identico (copia: _papelera/e2zz/sim_e2s_pre_e2zz.py).
    ES.QINI = None
    if ES.P['q_ini'] > 0:
        import ctypes as _ct
    
        def _qcurves():
            _o = []
            for _lay in ES.gar.animation_data.action.layers:
                for _st in _lay.strips:
                    for _cb in _st.channelbags:
                        _o += [fc for fc in _cb.fcurves if fc.data_path.endswith('.settings.quality')]
            return _o
        if ES.gar.animation_data is None or ES.gar.animation_data.action is None or (not _qcurves()):
            ES.s.quality = int(ES.P['quality'])
            ES.s.keyframe_insert('quality', frame=1)
        _qfc = _qcurves()
        assert len(_qfc) == 1, f'q_ini: {len(_qfc)} F-curves de quality'
        _qf = int(ES.P['q_ini_f'])
        _qb = {f_: float(_qfc[0].evaluate(f_)) for f_ in range(1, ES.NF + 2)}
        for f_ in range(1, ES.NF + 2):
            _qfc[0].keyframe_points.insert(f_, float(ES.P['q_ini']) if f_ <= _qf else _qb[f_])
        for _kp in _qfc[0].keyframe_points:
            _kp.interpolation = 'CONSTANT'
        _bad = [f_ for f_ in range(_qf + 1, ES.NF + 2) if abs(_qfc[0].evaluate(f_) - _qb[f_]) > 1e-06]
        assert not _bad, f'q_ini: el calendario viejo cambio en {_bad[:5]}'
        ES.QINI = _qf
        ES.s.quality = int(ES.P['q_ini'])
        ES.log(f"q_ini: {int(ES.P['q_ini'])} pasos del solver hasta f{_qf} | calendario viejo (float) f1 {_qb[1]:.2f} f4 {_qb[min(4, ES.NF)]:.2f} f7 {_qb[min(7, ES.NF)]:.2f} f10 {_qb[min(10, ES.NF)]:.2f} f{_qf + 1} {_qb[min(_qf + 1, ES.NF)]:.2f} | nuevo f1 {_qfc[0].evaluate(1):.2f} f{_qf} {_qfc[0].evaluate(_qf):.2f} f{_qf + 1} {_qfc[0].evaluate(_qf + 1):.2f} | claves {len(_qfc[0].keyframe_points)}")
    # e2zu2 (2026-10-05, CP58): FRICCION DEL CUERPO POR TIEMPO (ayuda de vestido). tfric_f=<F> tfric2=<v> [tfric_r=<R>, 6] -> los colisionadores que llevan tfric (el cuerpo sin la
    #   cabeza) tienen tfric hasta el cuadro F, rampa lineal de R cuadros y tfric2 desde F+R (R <= 1 = escalon en F+1). Clave en CADA cuadro: el valor en cuadros enteros no depende de
    #   la interpolacion (Blender 5.1: acciones por capas). La F-curve se evalua sobre la copia evaluada del colisionador (collision.cc lee collob->pd->pdef_cfrict): no hay edicion de
    #   usuario a mitad de sim -> no reconstruye el Cloth (medido con la sonda: _qc_e2zu/prueba_tfric.out). El asentamiento cuenta desde el fin de la rampa.
    #   tfric_f=0 = identico a antes (copia previa: _papelera/sim_e2s_pre_e2zu2.py).
    ES.TFK = None
    if ES.P['tfric_f'] > 0:
        ES.TFOBJ = [_o for _o in ES.TFOBJ if any((_m.type == 'COLLISION' for _m in _o.modifiers))]
        assert ES.P['tfric'] >= 0 and ES.P['tfric2'] >= 0 and ES.TFOBJ, 'tfric_f requiere tfric >= 0, tfric2 >= 0 y un colisionador con tfric'
        _tfF = int(ES.P['tfric_f'])
        _tfR = max(int(ES.P['tfric_r']), 1)
        ES.TFK = [float(ES.P['tfric'] + (ES.P['tfric2'] - ES.P['tfric']) * min(max((_f - _tfF) / _tfR, 0.0), 1.0)) for _f in range(1, ES.NF + 1)]
        for _o in ES.TFOBJ:
            for _f in range(1, ES.NF + 1):
                _o.collision.cloth_friction = ES.TFK[_f - 1]
                _o.collision.keyframe_insert('cloth_friction', frame=_f)
            _o.collision.cloth_friction = ES.TFK[0]
        ES.log(f"FRICCION POR TIEMPO (e2zu2): {[_o.name for _o in ES.TFOBJ]} tfric {ES.P['tfric']} hasta f{_tfF}, rampa de {_tfR} cuadros, {ES.P['tfric2']} desde f{_tfF + _tfR} (mu {0.01 * ES.P['tfric']:.2f} -> {0.01 * ES.P['tfric2']:.2f}) | claves f{_tfF}-f{_tfF + _tfR}: {[round(_v, 2) for _v in ES.TFK[_tfF - 1:_tfF + _tfR]]}")
    ew = ES.s.effector_weights
    for ES.f, g in ((1, 0.0), (int(ES.P['g0']), 0.0), (int(ES.P['g1']), 1.0)):
        ew.gravity = g
        ew.keyframe_insert('gravity', frame=ES.f)
    # e2f capucha baja: gravedad inclinada hacia atras (+Y) al arranque = sacarse la capucha; vuelve a vertical
    if ES.P.get('tilt', 0) > 0:
        th = math.radians(ES.P['tilt'])
        T1 = int(ES.P.get('tiltf', 18))
        gs = ES.sc.gravity.length
        for ES.f, v in ((1, (0, gs * math.sin(th), -gs * math.cos(th))), (T1, (0, gs * math.sin(th), -gs * math.cos(th))), (T1 + 12, (0, 0, -gs))):
            ES.sc.gravity = v
            ES.sc.keyframe_insert('gravity', frame=ES.f)
        ES.log('gravedad inclinada', ES.P['tilt'], 'grados hacia atras hasta f', T1, 'y vertical en f', T1 + 12)


def bucle(ES):
    """Bucle de cuadros: dumps, lazo de volumen por bolsillo, guardas de costura y log. (sim_e2s.py L775-L907)"""
    SEW = np.array(ES.D['sew'])
    ES.SEWN = ES.D['sew_seam']
    FP = [np.where(ES.face_pk == k)[0] for k in range(len(ES.names))]
    def coords():
        dg = bpy.context.evaluated_depsgraph_get()
        ev = ES.gar.evaluated_get(dg)
        m2 = ev.to_mesh()
        X = np.empty(len(m2.vertices) * 3)
        m2.vertices.foreach_get('co', X)
        ev.to_mesh_clear()
        return X.reshape(-1, 3)
    ES.coords = coords
    def volumes(X):
        out = np.zeros(len(ES.names))
        for k, fi in enumerate(FP):
            T = X[ES.F[fi]]
            c = T.reshape(-1, 3).mean(0)
            T = T - c
            out[k] = np.einsum('ij,ij->i', T[:, 0], np.cross(T[:, 1], T[:, 2])).sum() / 6.0
        return out
    ES.volumes = volumes
    # e2e2+: camino de carga del CF por cuadro (cfidx_e2e.py): pandeo del eje del cierre y la tapeta (largo / largo suavizado SG 101 mm, tramo
    # interior), z de la esquina CF y del cuello CF, y R-L del ruedo por azimut (0 = CF, 90 = costado, 180 = CB).
    _regla(ES, "metricas_definir")
    # desde aca cuenta el asentamiento
    ES.SET_F0 = int(ES.P['arm_f1']) if ES.P['arm_end'] >= 0 and ES.P['arm_end'] != ES.P['abd_end'] else int(ES.P['g1'])
    if ES.P['tfric_f'] > 0:
        ES.SET_F0 = max(ES.SET_F0, int(ES.P['tfric_f']) + max(int(ES.P['tfric_r']), 1))
        ES.log('asentamiento: cuenta desde f', ES.SET_F0, '(fin de la rampa de friccion, e2zu2)')
    ES.SHIST = []
    ES.SETTLED = False
    ES.t0 = time.time()
    ES.CT = []
    GHIST = {}
    ES.STOP = False
    _regla(ES, "capucha_sin_cuello")
    ARMS = ES.P['arm_end'] >= 0 and ES.P['arm_end'] != ES.P['abd_end']
    KEYSEAMS = tuple(ES.RD['costuras_clave'])
    def seam_max(X):
        L = np.linalg.norm(X[SEW[:, 0]] - X[SEW[:, 1]], axis=1) * 1000
        GG = collections.defaultdict(float)
        for nm_, l_ in zip(ES.SEWN, L):
            GG[nm_] = max(GG[nm_], l_)
        return GG
    # e2zz: pasos REALES del solver en este cuadro (solo lectura)
    # e2zu2: friccion evaluada = clave
    # e2zb cf_hold: reloj del objetivo corrido N para los retenidos; W congelado mientras la rampa no llega a 1
    # e2zb: mismo peso de presion en el canal R y su espejo L (mismo relleno inyectado por canal); 0 = identico
    # e2zi: nrb=1 -> sin reescribir 'presion' (ver cabecera)
    # e2zl: lazo sobre la presion GLOBAL (clave directa en la F-curve: no reconstruye el Cloth)
    # ANTES de insertar (orden del banco)
    # e2i: un paso de 3 grados del brazo (0,2 grados/cuadro)
    # e2w5: guarda de arranque (e2w3/e2w4: cierre R 303/315 mm en f6 y 2 h perdidas)
    # e2j: asentamiento (mm cada 6 cuadros)
    # e2i: capucha (sin cuello) apoyada: centroide y fraccion detras de la nuca (y > 0,10) y bajo z 1,62
    for ES.f in range(1, ES.NF + 1):
        ES.sc.frame_set(ES.f)
        if ES.f in ES.DUMPS:
            np.save(ES.SAL + f'X_{ES.TAG}_f{ES.f}.npy', ES.coords()[:ES.NV0])
            ES.log('dump X cuadro', ES.f)
        if ES.QINI is not None and (ES.f <= ES.QINI + 5 or ES.f % 30 == 0 or ES.f == ES.NF):
            _es = ES.gar.evaluated_get(bpy.context.evaluated_depsgraph_get()).modifiers[ES.cm.name].settings
            _fl = offsets.floats_sim_settings(_es, bpy)
            ES.log(f'   QINI f{ES.f} quality evaluada {_es.quality} | dt real {_fl[6]:.5f} = {1.0 / max(_fl[6], 1e-09):.1f} pasos | layout: Cvi {_fl[2]:.3f} g_z {_fl[5]:.3f} masa {_fl[7]:.4f}')
        if ES.TFK is not None and (ES.f <= 2 or ES.f % 6 == 0 or ES.f == ES.NF or (ES.TFK[ES.f - 1] != ES.TFK[max(ES.f - 2, 0)]) or (ES.f < ES.NF and ES.TFK[ES.f] != ES.TFK[ES.f - 1])):
            _dg = bpy.context.evaluated_depsgraph_get()
            _ev = [float(_o.evaluated_get(_dg).collision.cloth_friction) for _o in ES.TFOBJ]
            ES.log(f'   TFRIC f{ES.f} clave {ES.TFK[ES.f - 1]:.3f} | evaluado {[round(_e, 3) for _e in _ev]}')
            assert max((abs(_e - ES.TFK[ES.f - 1]) for _e in _ev)) < 0.001, f'tfric evaluado {_ev} != clave {ES.TFK[ES.f - 1]} en f{ES.f}'
        if ES.f >= 2 and ES.f % int(ES.P['K']) == 0:
            if ES.P['uarm'] >= 0:
                ES.MF[0] = 1.0 - (1.0 - ES.P['uarm']) * float(np.clip((ES.f - ES.P['arm_f0']) / max(ES.P['arm_f1'] - ES.P['arm_f0'], 1), 0, 1))
            ES.X = ES.coords()
            vol = ES.volumes(ES.X)
            tgt = ES.VT * min(1.0, 0.15 + 0.85 * ES.f / ES.P['ramp']) * (1.0 - ES.FR * (1.0 - ES.MF[0]))
            if len(ES.HK_):
                fh = max(ES.f - ES.P['cf_hold'], 0.0)
                tgt[ES.HK_] = ES.VT[ES.HK_] * min(1.0, 0.15 + 0.85 * fh / ES.P['ramp'])
                W0h = ES.W[ES.HK_].copy()
            ES.W = np.clip(ES.W * np.clip((tgt / np.maximum(vol, 1e-07)) ** 0.5, 0.8, 1.25), 0.01, 1.0)
            _regla(ES, "simetria_presion")
            if len(ES.HK_):
                hf = float(np.clip((ES.f - ES.P['cf_hold']) / max(ES.P['cf_ramp'], 1.0), 0.0, 1.0))
                if hf < 1.0:
                    ES.W[ES.HK_] = W0h
                ES.HOLD[ES.HK_] = hf
                if ES.f % 6 == 0 or (hf in (0.0, 1.0) and ES.f - ES.P['cf_hold'] in (0.0, ES.P['cf_ramp'])):
                    ES.log(f'   CF_HOLD f{ES.f} factor {hf:.2f} | W {np.round(ES.W[ES.HK_], 3).tolist()} | vol/obj {np.round(vol[ES.HK_] / np.maximum(tgt[ES.HK_], 1e-09), 2).tolist()}')
            if ES.P['nrb'] <= 0:
                ES.set_weights()
            r = vol / tgt
            ES.CT.append((ES.f, np.round(r, 3).tolist(), np.round(ES.W, 3).tolist()))
            if ES.PF is not None:
                i_ = min(int(np.searchsorted(ES.PF['f'], ES.f)), len(ES.PF['f']) - 1)
                rm_ = float(np.median(r))
                pe_ = ES.gar.evaluated_get(bpy.context.evaluated_depsgraph_get()).modifiers[ES.cm.name].settings.uniform_pressure_force / ES.P['p0']
                if ES.P['pfb'] > 0 and ES.f + 1 > ES.P['pfb_f0']:
                    ES.PF['c'] = float(np.clip(ES.PF['c'] * np.clip((ES.PF['rrs'][i_] / max(rm_, 0.001)) ** ES.P['pfb'], 1.0 - ES.P['pfb_clip'], 1.0 + ES.P['pfb_clip']), 0.5, 2.0))
                    kp_ = ES.PF['fc'].keyframe_points.insert(ES.f + 1, ES.P['p0'] * float(ES.PF['g'][i_]) * ES.PF['c'])
                    kp_.interpolation = 'CONSTANT'
                ES.PF['log'].append((ES.f, round(rm_, 4), round(float(ES.PF['rr'][i_]), 4), round(float(ES.PF['g'][i_]), 4), round(ES.PF['c'], 4), round(ES.PF['fc'].evaluate(ES.f + 1) / ES.P['p0'], 4), round(pe_, 4)))
                if ES.f % 6 == 0:
                    ES.log(f"   PFIT f{ES.f} vol/obj med {rm_:.3f} ref {ES.PF['rr'][i_]:.3f} (suav {ES.PF['rrs'][i_]:.3f}) | g {ES.PF['g'][i_]:.3f} c {ES.PF['c']:.3f} -> factor f{ES.f + 1} {ES.PF['fc'].evaluate(ES.f + 1) / ES.P['p0']:.3f} | evaluado en f{ES.f} {pe_:.3f}")
            if ARMS and ES.f >= ES.P['arm_f0'] and ((ES.f - int(ES.P['arm_f0'])) % 15 == 0):
                GHIST[ES.f] = seam_max(ES.X)
                ang = ES.P['abd_end'] + (ES.P['arm_end'] - ES.P['abd_end']) * float(np.clip((ES.f - ES.P['arm_f0']) / max(ES.P['arm_f1'] - ES.P['arm_f0'], 1), 0, 1))
                prev = GHIST.get(ES.f - 15)
                dl = {k: round(GHIST[ES.f][k] - prev[k], 1) for k in GHIST[ES.f]} if prev else {}
                ES.log(f'PASO f{ES.f} brazo {ang:.1f} grados | ' + ' '.join((f'{k}:{GHIST[ES.f][k]:.1f}' + (f'({dl[k]:+.1f})' if dl else '') for k in KEYSEAMS if k in GHIST[ES.f])))
                if dl:
                    worst = max(dl.items(), key=lambda kv: kv[1])
                    ES.log(f'   peor apertura en 3 grados: {worst[0]} {worst[1]:+.1f} mm')
                    if ES.P['stop_open'] > 0 and worst[1] > ES.P['stop_open']:
                        ES.log(f"STOP: {worst[0]} abrio {worst[1]:+.1f} mm en 3 grados (> {ES.P['stop_open']})")
                        ES.STOP = True
            if ES.f % 6 == 0:
                L = np.linalg.norm(ES.X[SEW[:, 0]] - ES.X[SEW[:, 1]], axis=1) * 1000
                ES.log(f'f{ES.f} t={time.time() - ES.t0:.0f}s vol/obj min {_mn(r):.2f} med {np.median(r):.2f} max {_mx(r):.2f} | peso min {_mn(ES.W):.2f} med {np.median(ES.W):.2f} max {_mx(ES.W):.2f} n_sat {int((ES.W >= 0.999).sum())} | costura media {L.mean():.1f} max {L.max():.0f} mm z {ES.X[:, 2].min():.3f}-{ES.X[:, 2].max():.3f} finito {bool(np.isfinite(ES.X).all())}')
                GG = collections.defaultdict(float)
                for (ia, ib), nm_, l_ in zip(SEW, ES.SEWN, L):
                    GG[nm_] = max(GG[nm_], l_)
                ES.log('   por costura (max mm):', sorted(((round(v, 1), k) for k, v in GG.items()), reverse=True)[:6])
                if ES.P['stop_f6'] > 0 and ES.f <= 6 and (L.max() > ES.P['stop_f6']):
                    wk = max(GG.items(), key=lambda kv: kv[1])
                    ES.log(f"STOP: f{ES.f} costura {wk[0]} abierta {wk[1]:.0f} mm (> stop_f6 {ES.P['stop_f6']:.0f}): arranque roto")
                    ES.STOP = True
                _regla(ES, "metrica_cf_y_asentamiento")
                _regla(ES, "metricas_por_cuadro")
                if ES.SWEEP is not None:
                    ES.log(f'   esfera en {tuple((round(v, 3) for v in ES.SWEEP.matrix_world.translation))}')
        if ES.STOP:
            ES.log('corrida cortada en f', ES.f)
            break
        if ES.SETTLED:
            ES.log('asentamiento cumplido: fin en f', ES.f)
            break


def cierre(ES):
    """Salidas: bolsillos, costuras, final, objeto aplicado, siluetas y .blend. (sim_e2s.py L908-L945)"""
    ES.X = ES.coords()
    vol = ES.volumes(ES.X)
    json.dump(dict(names=ES.names, area_m2=ES.AREA.tolist(), vt_m3=ES.VT.tolist(), vol_m3=vol.tolist(), w=ES.W.tolist(), ctrl=ES.CT, **{'pfit': ES.PF['log'], 'pfit_cols': 'f, vol/obj med, ref, g, c, factor f+1, factor evaluado en f'} if ES.PF is not None else {}), open(ES.SAL + f'bolsillos_{ES.TAG}.json', 'w'))
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ES.gar.evaluated_get(dg)
    fin = bpy.data.meshes.new_from_object(ev)
    fo = bpy.data.objects.new('CD_campera_final', fin)
    ES.col.objects.link(fo)
    fin.shade_smooth()
    # e2zd: el separador del broche no va al objeto final (fuera del render)
    if ES.SEPV:
        _bm = bmesh.new()
        _bm.from_mesh(fin)
        _bm.verts.ensure_lookup_table()
        bmesh.ops.delete(_bm, geom=[_bm.verts[i] for i in ES.SEPV], context='VERTS')
        _bm.to_mesh(fin)
        _bm.free()
        ES.log('broches con altura: separadores fuera del objeto final:', len(fin.vertices), 'vertices (malla', ES.NV0, ')')
    G = collections.defaultdict(list)
    for (a, b), nm in zip(ES.D['sew'], ES.SEWN):
        G[nm].append(1000 * float(np.linalg.norm(ES.X[a] - ES.X[b])))
    rows = []
    for nm, l in G.items():
        l = sorted(l)
        rows.append(f'{nm:34s} n {len(l):4d}  max {l[-1]:6.1f} mm  p95 {l[int(0.95 * (len(l) - 1))]:6.1f}  media {sum(l) / len(l):5.1f}')
    open(ES.SAL + f'costuras_gap_{ES.TAG}.txt', 'w', encoding='utf-8').write(chr(10).join(rows) + chr(10))
    ES.log(*rows, sep=chr(10))
    # e2zd: altura final de cada separador (apice a su base) y costuras del broche
    if ES.SEPV:
        _hs = [float(np.dot(ES.X[i0 + 3] - ES.X[i0:i0 + 3].mean(0), np.cross(ES.X[i0 + 1] - ES.X[i0], ES.X[i0 + 2] - ES.X[i0]) / np.linalg.norm(np.cross(ES.X[i0 + 1] - ES.X[i0], ES.X[i0 + 2] - ES.X[i0])))) * 1000 for i0 in ES.SEPV[::4]]
        ES.log('broches con altura: altura final de los separadores (mm):', [round(abs(v), 1) for v in _hs])
    json.dump(ES.X[:ES.NV0].tolist(), open(ES.SAL + f'final_{ES.TAG}.json', 'w'))
    ES.log('t sim', round(time.time() - ES.t0))
    # ---- objeto final aplicado: sin cloth ni cache, sin shape keys; se borra la malla simulada
    bpy.data.objects.remove(ES.gar, do_unlink=True)
    for o in ES.MANIQUI:
        o.hide_render = True
        o.hide_viewport = True
    if ES.P['renders'] > 0:
        ES.sc.render.engine = 'BLENDER_WORKBENCH'
        sh = ES.sc.display.shading
        sh.light = 'FLAT'
        sh.color_type = 'SINGLE'
        sh.single_color = (1, 1, 1)
        ES.sc.render.film_transparent = True
        ES.sc.render.resolution_x = 1200
        ES.sc.render.resolution_y = 1200
        ES.sc.render.image_settings.file_format = 'PNG'
        ES.sc.render.image_settings.color_mode = 'RGBA'
        cam = bpy.data.cameras.new('CD_cam_orto')
        cam.type = 'ORTHO'
        co = bpy.data.objects.new('CD_cam_orto', cam)
        ES.col.objects.link(co)
        ES.sc.camera = co
        bb = np.array([fo.matrix_world @ mathutils.Vector(c) for c in fo.bound_box])
        cx, cy, cz = (bb.min(0) + bb.max(0)) / 2
        cam.ortho_scale = float((bb.max(0) - bb.min(0)).max()) * 1.25
        for nm, loc, rot in (('frente', (cx, -3, cz), (90, 0, 0)), ('perfil', (3, cy, cz), (90, 0, 90)), ('espalda', (cx, 3, cz), (90, 0, 180))):
            co.location = loc
            co.rotation_euler = tuple((math.radians(a) for a in rot))
            ES.sc.render.filepath = ES.SAL + f'sil_{nm}_{ES.TAG}.png'
            bpy.ops.render.render(write_still=True)
        ES.log('ortho_scale', cam.ortho_scale, 'bbox', np.round(bb.min(0), 3).tolist(), np.round(bb.max(0), 3).tolist())
        sh.light = 'STUDIO'
        sh.single_color = (0.18, 0.36, 0.45)
        ES.sc.render.film_transparent = False
        ES.sc.render.resolution_x = 900
        ES.sc.render.resolution_y = 900
        co.location = (cx + 2.1, cy - 2.1, cz + 0.2)
        co.rotation_euler = (math.radians(88), 0, math.radians(45))
        ES.sc.render.filepath = ES.SAL + f'vista_{ES.TAG}.png'
        bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=ES.SAL + f'{ES.NOMBRE}_{ES.TAG}.blend')
    ES.log('fin', round(time.time() - ES.t0))
