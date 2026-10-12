# e2s (2026-09-29): copia de sim_e2q.py + CUELLO SANDWICH (sand=1; sand_e2s.py): la vista del cuello (ht) atada al hs en toda el area con los
#      RESORTES INTERNOS del Cloth (rayo por -normal, pares de normales opuestas, <= sand_len mm); reposo = molde plano con el ht SUPERPUESTO al hs
#      (traslacion T del molde, z = -sand_d mm; sand_ov=0 = sin superponer, solo para el control). Rigidez: vertex_group_intern = 'interno' (solo el ht,
#      rampa sand_tap mm desde las costuras; 0 en los ht con algun resorte a otra pieza) x internal_*_stiffness_max = sand_k / sand_kc (min 0: los
#      resortes internos entre otras capas quedan en 0). Log PRED (resortes predichos por pieza) y SAND cada 6 cuadros (espesor, deslizamiento, anillo).
#      Sin sand el script es identico a sim_e2q.py.
# e2q (2026-09-28): copia de sim_e2m.py + PLANCHA (ficha/DXF: capucha, cuello y tapeta llevan plancha de guata 1200[x] / 16[x][x][x][x], no relleno inyectado;
#      [x] 09-28 lo confirma): pl_bh > 0 = flexion propia de la capucha (HOODSET: hs fuera del cuello + hc + hb + cordon) POR ENCIMA de la base,
#      como peso en 'rigidez' (w = (pl_bh - bending) / (bend_max - bending)); el cuello sigue con w_neck y la tapeta con w_plk. Requiere hood_bend < 0.
#      + dumps=36,72,... (posiciones X_<tag>_f<cuadro>.npy para ver CUANDO aparece un pliegue). Sin pl_bh ni dumps el script es identico a sim_e2m.py.
#      + pl_hc (e2q, 00:31): compresion de panel de la capucha > la de la cascara (compression_stiffness_max = pl_hc; cascaras remapeadas a su 15).
#      + sa_brd (e2q, 00:05): franja sin autocolision manga-cuerpo junto a los bordes, en mm de molde (12 por defecto = identico). Los rulos del fs que
#      reaparecen en la sim estan TODOS a < 12 mm del costado (autocruce_e2q2: 49/49 y 55/56 pares).
# RE (2026-10-09, CP76): + arm_x0 / arm_z0 (pivote del tubo del brazo; defecto 0.21 / 1.40 = identico) y ath (espesor de colision de brazos y deltoides, m; -1 = th).
#      Cuerpo RE2 (cintura escapular baja + casquete del hombro de piel real): body=cuerpo_L_RE2.npz deltoid=0 arm_x0=0.2022 arm_x1=0.2222 arm_z0=1.3709 bth=0.001 ath=0.001
# e2o (2026-09-28): + body=<npz> (cuerpo MPFB2 talle L, prep_cuerpo_e2o.py): TORSO + CABEZA del cuerpo real (hibrido: sin brazos; los brazos siguen siendo los del
#      maniqui + deltoides), CRECE desde el angosto (shape key 'angosto' 1 en f1 -> 0 en bgrow, lineal) y acompana la bajada de brazos (shape key 'brazos_8'
#      entre arm_f0 y arm_f1). Torso y cabeza del maniqui quedan SIN colision. Sin body= el script es identico al anterior.
# e2n (2026-09-28): + deltoid (M133-X-ESPALDA.md, sesion par): elipsoide colisionador por lado, FIJO al torso (no sigue al brazo), mismo collider()
#      y espesor; centro (+-dl_x, dl_y, dl_z), semiejes (dl_a, dl_b, dl_c); dl_s0 < 1 = arranca a esa escala en f1 y crece lineal hasta 1 en dl_f
#      (el elipsoide entero pisa la manga del arranque de m133_e2m3.json: 186 vertices por lado adentro). deltoid=0 = identico a antes.
# e2m (2026-09-26): copia de sim_e2l.py (escena CAMPDIB_E2M) + cuff_on (arregla el bug de e2k: la rigidez del puno estaba dentro del if de w_plk).
# e2l (2026-09-26): copia de sim_e2k.py (escena CAMPDIB_E2L) + msym (maniqui con triangulacion ESPEJADA: Blender parte cada cuadrilatero por la misma
#      diagonal, asi que el torso, la cabeza UV y los brazos eran quirales -rosca de 0,7 mm de mediana, 4,2 max en hombros y cuello-, diag_maniqui_e2l.py) + pres (0 = presion
#      APAGADA de verdad: use_pressure False; con p0=0 queda el termino de volumen de Blender) + log GIRO y PRES R/L por 6 cuadros (biseccion de la torsion).
# e2k (2026-09-26): copia de sim_e2j.py (escena CAMPDIB_E2K) + boca de la capucha (post_e2k.py: banda hb + cordon en el tunel): la banda y el cordon
#      entran en la capucha blanda (HOODSET), cinch = tirado del cordon (shape key 'cordon' relativa a molde_plano: reposo ojal-ojal x (1 - cinch),
#      rampa cz0 -> cz1), tfric = friccion propia del torso, hfric = friccion propia de la cabeza (Blender: mu = 0,01 x friccion), settle_hood = el asentamiento mira tambien la boca.
# e2j (2026-09-26): copia de sim_e2i.py (escena CAMPDIB_E2J) + settle_min/settle_tol/settle_n (asentamiento: log ASENT por 6 cuadros y corte cuando la
#      esquina CF se mueve < settle_tol mm en settle_n chequeos seguidos, desde arm_f1 + settle_min) + ent_c (entretela del cuello chimenea: compresion
#      en el plano de la franja rig_cuello = hs bajo el ht + ht; la malla es de TRIANGULOS, asi que Blender no arma resortes de corte y el corte en el
#      plano lo dan los estructurales: shear_stiffness no actua). La flexion del cuello no se toca.
# CP11 (2026-09-26): + sw_path=2 (barrido por la linea media que sale hacia atras en horizontal) y arm_x1 (pivote del brazo que se abre al bajar).
# e2i: copia de sim_e2h.py (escena CAMPDIB_E2I) + hood_scope (capucha blanda SIN el cuello chimenea: hs fuera de la huella del ht + hc;
#      el cuello = rig_cuello de rig_e2g.py queda como el cuerpo), sweep (esfera colisionadora invisible que pliega la capucha hacia la
#      espalda, consulta A paso 2), hcol (autocolision capucha-espalda/hombros, solo cascaras, a > 12 mm de bordes), stop_open (corta la
#      corrida de brazos si una costura abre > stop_open mm en 3 grados = 15 cuadros) y metricas de capucha apoyada.
# e2h: copia de sim_e2g.py (escena CAMPDIB_E2H) + hood_bend (flexion propia de la capucha, el resto igual), head=0 (sin cabeza),
#      cd/th (distancia de colision del Cloth / espesor del maniqui), uarm (objetivo de volumen bajo la axila en rampa, pose).
# e2g: copia de sim_e2f.py (escena CAMPDIB_E2G, rigidez por franja w_neck/w_sisa, cabeza que se retira hds/hd0-hd3).
# e2f: copia de sim_e2e5.py (maniqui v2) con la malla por argumento mesh=<json> y escena CAMPDIB_E2F.
# Etapa 2 (acolchado). Cascara + capa interior ([x][x][x][x], mismo molde) cosidas en pespuntes y borde, arranque en la pose v4h.
# Relleno (prueba chica P4-P5, blender/etapa2/prueba/): presion uniforme p0 con vertex_group_pressure y un peso por BOLSILLO
# (instancia x canal: 33) que se ajusta cada K cuadros hacia el volumen objetivo del bolsillo = area plana x 4/3 x h (lente de
# flecha h). Es el volumen por canal de A, dentro de un solo objeto (Blender no cose objetos entre si). Cloth relee los grupos
# de vertices en cada paso (verificado en P5). Avios sin pin: cinta del cierre del bolsillo (boca fc/fs e5), tapeta 7,5 cm
# (sin presion) y punio: rigidez por vertex_group_bending. Reposo = molde plano (Dynamic Mesh, como v4).
#   blender.exe -b --factory-startup --python sim_e2.py -- <frames> <tag> [k=v ...]
# Entrada: etapa2/m133_e2.json (prep_e2.py). Salida: etapa2/m133_<tag>.blend, final_<tag>.json, costuras_gap_<tag>.txt,
#   bolsillos_<tag>.json, sil_{frente,perfil,espalda}_<tag>.png, vista_<tag>.png, sim_<tag>.log
import bpy, bmesh, json, math, sys, time, mathutils, collections
import numpy as np
ROOT = r"."
E2 = __import__("os").environ.get("M133_E2") or (ROOT + "/blender/etapa2/")   # [ESC·f535] R16: E2 de entorno (VPS)
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
NF = int(argv[0]) if argv else 70; TAG = argv[1] if len(argv) > 1 else "e2"
P = dict(w_cost=0.0, pl_bh=-1.0, pl_hc=-1.0, abd_end=20.0, mass=0.02, tension=100, compression=15, shear=5, bending=5.0, quality=10, sew_max=80.0, air=1.0, fric=0.5,
         head=1, g0=1, g1=3, arm_top=-0.10, p0=16.0, w0=0.3, K=3, ramp=30, h_body=0.0105, h_sl=0.0093, off=0.0015, bend_max=50.0,
         w_cuff=0.6, renders=1, soft=1.0, S_body=0.04, S_sl=0.08, S_cas=0.0, selfcol=1.0, self_d=0.003, sf=5.0, vtk=1.0, w_band=1.0,
         w_neck=0.0, w_sisa=0.0, hds=1.0, hd0=3, hd1=9, hd2=36, hd3=48,
         arm_end=-1.0, arm_f0=12, arm_f1=60, q_ramp=0, selfarm=0, arm_gap=0.012, hood_bend=-1.0, cd=0.004, th=0.008, uarm=-1.0, uarm_band=0.12, z_ax=1.33, vcol=0, hood_soft=0,
         hood_scope=0, sweep=0, sw_r=0.15, sw_f0=5, sw_f1=30, sw_f2=36, sw_th=0.004, hcol=0, stop_open=0.0, sw_path=1, arm_x1=-1.0,
         settle_min=0.0, settle_tol=2.0, settle_n=2, ent_c=0.0, nar=0.0, cinch=0.0, cz0=6, cz1=36, hfric=-1.0, settle_hood=1, tfric=-1.0, snaps=1, w_plk=1.0, msym=0, pres=1, notp=0, cuff_on=1,
         bgrow=18, bth=-1.0, deltoid=0, dl_x=0.215, dl_y=0.0, dl_z=1.405, dl_a=0.055, dl_b=0.06, dl_c=0.045, dl_s0=1.0, dl_f=1,
         sand=0, sand_ov=1, sand_txy=1.0, sand_zs=1.0, sand_rot=0, neck_hs=-1.0, neck_ht=-1.0, bmx=-1.0, rig_tap=0.0, noobj_neck=0, sand_d=5.5, sand_k=200.0, relleno=0.0, relleno_h=12.0, relleno_g=15.0, relleno_r=0.0, relleno_min=1.0, sand_kc=100.0, sand_len=10.0, sand_tap=12.0, sand_nc=1, stop_f6=30.0,
         cf_hold=0.0, cf_ramp=12.0, cf_ch=34.0, cf_lr=0.0, wsym=0.0, tp_nocol=0.0, sep_h=0.0, sep_eps=0.0, tfric_f=0.0, tfric2=-1.0, tfric_r=6.0, rk_f0=2, rk_df=3, fmp=2, nrb=0, sand_lvl=0.0,
         pfb=0.0, pfb_f0=30, pfb_clip=0.1, pfb_sm=1, mano=0.0, q_ini=0.0, q_ini_f=12, arm_x0=0.21, arm_z0=1.40, ath=-1.0, arm_xi=-1.0, arm_zi=-1.0, wmin=0.01, wmax=1.0, muneca=0.0)
# RK (2026-10-10, CP85): wmax=<0..1> -> TOPE del peso de presion del lazo (antes fijo 1,0). wmin=wmax=k = presion CONSTANTE k x p0 en los 33 bolsillos (la
#   fibra inyectada es uniforme por canal; con el relleno en lente el tope lo pone el strut, no el lazo). Medido en RJh3 (_qc_RK/lente_vol.py): los canales
#   libres llegan al tope de la lente con w 0,05-0,12 y los 14 saturados (w 1,0) son los que el cuerpo aplasta (puno, hombro, canal alto bajo la tapeta):
#   la presion maxima ahi revienta el puno (replica RJh3b: bajo manga R 30 mm en f69). wmax=1.0 = identico.
# RI (2026-10-10): wmin=<0..1> -> PISO del peso de presion por bolsillo en el lazo de volumen (antes fijo 0,01). El relleno real es uniforme por canal; con
#   vol/obj >= 1 por geometria (hueco de la garganta, canesu) el lazo dejaba el canal alto del pecho en 0,10 y su cascara a 4,8 mm del forro en el CF
#   (RHh1 f72: fcR0 4,8 mm en |x| < 40 contra 20-30 en los costados). wmin=0.01 = identico.
# e2zs (2026-10-05): sand_lvl=<mm> (> sand_len; 0 = identico) -> el SANDWICH del cuello SOBREVIVE a las reconstrucciones del Cloth (lazo de presion por
#   bolsillo, nrb=0). Blender re-detecta los resortes internos sobre el MOLDE plano en cada reconstruccion (CP44) y ahi R y L estan SUPERPUESTAS (mismo uv,
#   normales opuestas): con el htR en z -sand_d sus rayos se alejaban de su hsR (R 0 de 215) y los del lado L tocaban la copia R coincidente (L 189 de 217).
#   Arreglo SOLO de reposo, traslaciones rigidas por pieza (no cambian estructurales, flexion ni costuras): hsR a z +sand_lvl y htR DETRAS de su hsR
#   (z sand_lvl + sand_d; sand_e2s.flat_levels). sand_rot=2 (requiere sand_lvl) -> ademas tri[0] de los triangulos que tocan los rayos SOBRE EL MOLDE = vertice
#   bajo el rayo (el ht cae a 0,1 mm de su vertice gemelo del hs): la re-deteccion da ataduras gemelas (reposo sand_d) en vez de diagonales de 11,3 mm.
#   Log 'PRED RECONSTRUCCION'. Sin sand_lvl y con sand_rot <= 1 = identico (copias: _papelera/sim_e2s_pre_e2zs.py, sand_e2s_pre_e2zs.py).
# e2zl (2026-10-01): pfit=<bolsillos_ref.json> (requiere nrb=1 y wini=) -> presion GLOBAL que sigue la trayectoria de una COMPLETA de referencia sin tocar
#   grupos: g(f) = ajuste rank-1 por area de W_ref(f,k) con los pesos fijos w = WINI (sum A W_ref w / sum A w^2), clave en f+1 de cada cuadro de control.
#   pfb=b > 0 -> LAZO sobre esa presion desde pfb_f0: c *= clip((r_ref(f) / mediana vol/obj)^b, 1 -+ pfb_clip), r_ref = mediana de vol/obj de la referencia en
#   el MISMO cuadro (media movil de 2*pfb_sm+1 controles), clave p0 x g(f) x c en f+1 insertada DIRECTO en la F-curve (fc.keyframe_points.insert): banco
#   _qc_e2zl/test_kf.py con la sonda = 0 reconstrucciones (s.uniform_pressure_force = v + keyframe_insert a mitad de sim SI reconstruye: 2 en 12 cuadros).
#   Con pramp= (pfb > 0): las claves de PRAMP quedan tal cual hasta pfb_f0 (f1-f30 = e2zk1/e2zjN bit a bit) y desde ahi g(f) x c (e2zl1: el rank-1 con
#   w = W final de e2zd2 sin pramp corto en f27, capucha-ht L +37,9 mm, por los bolsillos casi sin presion al arranque).
#   Sin pfit = identico (copia previa: _papelera/sim_e2s_pre_e2zl.py).
# e2zi (2026-10-01): nrb=1 -> el lazo de volumen NO reescribe el grupo 'presion' (solo para pres=0, la presim). Cada set_weights() cambia un grupo de
#   vertices -> Blender invalida la cache y RECONSTRUYE el Cloth en el cuadro siguiente (cuadro muerto: no avanza; f4, f7, ... f22) y re-detecta los
#   resortes internos con rayos sobre el REPOSO de ese cuadro. Con la rampa rk el reposo es 3D: aparecen resortes ht -> fs/tp/fc que en el molde miden
#   hasta 3,35 m (_qc_e2zi/resortes_rebuild.out) -> la presim explota al pasar a molde_plano (e2zi1p f23). nrb=0 = identico.
# e2zf (2026-10-01): fmp=N (defecto 2 = identico) -> molde_plano = 1 recien en fN: reposo FIJO en V0 hasta ahi (copia previa: _papelera/sim_e2s_pre_e2zf.py).
# e2ze (2026-10-01): rk=<npz> -> REPOSO EN RAMPA ARAP (_qc_e2ze/rampa_arap.py, CP38 opcion C): claves de reposo rk1..rk{K-1} (keys (K-1, NV0, 3) m) en escalones
#   CONSTANT desde rk_f0, una cada rk_df cuadros; molde_plano = 1 recien en rk_f0 + (K-1)*rk_df. Separadores (sep_h) = SEP_REST en todas. Sin rk = identico
#   (copia previa: _papelera/sim_e2s_pre_e2ze.py).
# e2zd (2026-09-30): sep_h=<mm> -> BROCHE CON ALTURA (mk_e2zd.py, clave "snap_sep" de la malla): por broche un separador rigido (tetraedro de 4 vertices
#   nuevos al final de la malla: base = copia de la cara de la pareja fcL/hsL, apice a sep_h mm sobre el pie del vertice t del tp, por la normal hacia la tp).
#   Costuras de largo 0: base -> cara ("broche base"), apice -> t ("broche"); los resortes "broche" viejos (tp -> pareja, largo 0) salen. Reposo = el mismo
#   tetraedro (base = triangulo del molde de la cara). Rigidez: flexion bend_max, compresion max; sin presion, sin autocolision, sin encoger.
#   Fuera de los dumps, del final_*.json y del .blend (solo se guardan los NV0 vertices de la malla). sep_h=0 = identico (copia: _papelera/sim_e2s_pre_e2zd.py).
# e2zb (2026-09-30): cf_hold=N -> los bolsillos del fc bajo la tapeta (canales cf_ch, digitos: 34 = fc3 y fc4, donde nace el cruce fcLxtp en z 1,39-1,45;
#   cf_lr 0 = R y L, 1 = solo L, 2 = solo R) van con peso de presion ~0 (1e-4: siguen en la cuenta de volumen de Blender) hasta fN; despues el peso
#   sube en rampa lineal 0 -> W en cf_ramp cuadros con W congelado (w0) y recien ahi el lazo de volumen los adapta, con el reloj del objetivo corrido N.
#   cf_hold=0 = identico a antes (copia previa: _papelera/sim_e2s_pre_e2zb.py).
# e2zb: wsym=1 -> el lazo de volumen promedia el peso de cada canal R con su espejo L (presion simetrica; el relleno real es el mismo por canal).
# e2e2+: sf = self_friction (e2e1: 5,0; tela/tela real 0,3-0,5) · vtk = factor del volumen objetivo (1 = lente de dos caras 4/3·A·h;
# 0,5 = una cara 2/3·A·h, contra el cuerpo). Defaults = e2e1.
# [ESC·f535] PQ (2026-10-10): esc=<npz> (vacio = identico) -> anillo del escote / anclas. npz: 'rig' ids -> flexion bend_max y compresion maxima
#   (pesos 1 en 'rigidez' y 'cascara', como la columna del cierre); 'pin' ids + 'co0' (m, cuadro 1) [+ 'co1' (m, desde esc_f1)] -> ANCLAS: un vertice
#   suelto por id, fijo (pin 1 en 'pin_anclas') y cosido a su vertice con un resorte de costura de largo 0 ('ancla escote'). El reposo del molde de la
#   prenda NO cambia (Blender toma el objetivo del pin y el reposo de la misma malla: un pin directo iria al molde plano). Las anclas siguen la clave
#   'anclas_cf' (0 en f1 -> 1 en esc_f1). Resortes internos que Blender detecta en f1 desde un ancla: el otro extremo queda con peso 0 en 'interno'
#   hasta el primer set_weights del lazo (ANC_PEND), como la guardia del relleno. Fuera de dumps (NV0) y del objeto final.
MESH = "m133_e2e3.json"; BODY = ""; DUMPS = set(); RK = ""; WINI = ""; PRAMP = ""; PFIT = ""; HREST = ""; ESC = ""; P["esc_f1"] = 8.0
# [ESC·f535] MN (2026-10-11, DIAGNOSTICO): mn_s<1 -> MENTON (caras del cuerpo con centro z 1,525-1,66, y <= -0,090, |x| < 0,09 = MEN de _qc_PR/analiza_PR.py)
#   en objetos aparte (torso y cabeza, misma friccion), escalado a mn_s hacia un pivote dentro de la cabeza hasta mn_f0 y repuesto lineal hasta mn_f1.
#   esc_r1>0 -> SOLTAR las anclas y el 'rig' de esc= en rampa lineal de esc_r0 a esc_r1 (pin 1 -> 0; rigidez y cascara -> pesos originales). Defaults = identico.
P["mn_s"] = 1.0; P["mn_f0"] = 12.0; P["mn_f1"] = 24.0; P["esc_r0"] = 0.0; P["esc_r1"] = 0.0; MNOBJ = []
# [ESC·f535] BI (2026-10-11): bi_w>0 y bi_k!=1 -> franja de FLEXION x bi_k en los vertices a <= bi_w mm (molde) de la costura escote-cuello
#   (cuello-capucha + vista-escote + vista-cuerpo), a cada lado (back fc fs hs hc ht; cierre y tapeta fuera); tope de flexion subido y el resto
#   REMAPEADO (misma flexion, como bmx). Sin reposo de flexion nuevo. Defaults = identico (el bloque no corre).
P["bi_w"] = 0.0; P["bi_k"] = 1.0
BI_COS = ["cuello-capucha", "vista-escote R", "vista-escote L", "vista-cuerpo R", "vista-cuerpo L"]   # [ESC·f535] BI: bi_cos=a_b_R,c_d (espacios = _) cambia las costuras
# [ESC·f535] CA (2026-10-11): cc_w>0 y cc_k!=1 -> franja de FLEXION x cc_k en los vertices de hsR/hsL/hc a <= cc_w mm (molde) de las costuras
#   hs-hc ("copa capucha R/L"), a cada lado, solo dentro de HOODSET (cuello, cierre y tapeta fuera); mismo mecanismo que bi_w (tope subido, resto
#   REMAPEADO). cc_w=15 = fila de la costura + la siguiente (arista 10 mm). Defaults = identico (el bloque no corre).
P["cc_w"] = 0.0; P["cc_k"] = 1.0
# [ESC·f535] PT (2026-10-11): pt_w>0 -> PUENTE escote-cuello (banco m10p, LEYES L1-2: margen 10 + pespunte en el canto = tela continua): margen de
#   costura del cuello (hsR/hsL/hc) de ~pt_w mm que cruza la costura cuello-capucha por DENTRO del cuerpo (a pt_off mm de la cascara en el V0) y se
#   cose en su canto al cuerpo (resortes 'puente canto'). Modulo _qc_PT/puente_PT.py (probado sin Blender). Reposo = molde (uv); flexion, cascara y
#   encoge heredadas del vertice del cuello; sin autocolision; dumps aparte XP_<tag>_f<n>.npy. Defaults = identico (copia _papelera/sim_e2s_pre_PT.py).
P["pt_w"] = 0.0; P["pt_off"] = 4.5
# [ESC·f535] HB (2026-10-11): pc_w>0 -> PUENTE sobre la costura COPA hs-hc ("copa capucha R/L") = banco 1 m10p (LEYES L1-2: margen + pespunte
#   en el canto = tela continua; C01b: hace falta un puente sobre la costura). Margen de hc de ~pc_w mm (continua el plano de hc en el molde, reposo
#   espejo de la franja real del hs) que cruza la costura por DENTRO de la capucha (a pc_off mm del hs en el V0) y se cose en su canto al hs
#   (resortes 'puente canto'). Mismo modulo _qc_PT/puente_PT.margen (COLLAR=hc, BODY=hsR/hsL) y misma maquinaria PTV del PT (pesos heredados de
#   su vertice de hc, sin autocolision, reposo PT-R, dumps XP). Defaults = identico (los bloques no corren). Copia de _qc_CAP/sim_e2s_CAP.py 49cb2298.
P["pc_w"] = 0.0; P["pc_off"] = 4.5
# [ESC·f535] HP (2026-10-11): hf=1 -> FORRO DE CAPUCHA del DXF (b17 [x][x] x2 + b19 [x][x][x], 210T; _qc_HP/forro_build.py -> forro_HP.json): frente a la
#   boca, base al escote y al canto libre del ht, copa del forro con los pares de la copa de la cascara. Sin plancha, sin autocolision (como los
#   forros de canal). hf_w=<peso> -> PRESION entre cascara (hs arriba de la linea forro/ht + hc) y forro: mismo grupo 'presion' que back/fc/fs/sl,
#   peso CONSTANTE (fuera del lazo de volumen: la capucha lleva plancha 1200[x], no fibra por canal). Dumps XF_<tag>_f<n>.npy. hf=0 = identico.
P["hf"] = 0.0; P["hf_w"] = 0.0; FHV = []; FHS = []
P["hf_sc"] = 0.0; P["hf_sb"] = 12.0   # [ESC·f535] HQ: autocolision forro-cascara de la capucha (ver _qc_HP/parcha_HQ.py)
for kv in argv[2:]:
    k, v = kv.split("=")
    if k == "mesh": MESH = v; continue
    if k == "esc": ESC = v; continue
    if k == "body": BODY = v; continue
    if k == "rk": RK = v; continue
    if k == "hrest": HREST = v; continue
    if k == "wini": WINI = v; continue
    if k == "pramp": PRAMP = v; continue
    if k == "pfit": PFIT = v; continue
    if k == "bi_cos": BI_COS = [t.replace("_", " ") for t in v.split(",") if t]; continue
    if k == "dumps": DUMPS = set(int(t) for t in v.split(",") if t); continue
    P[k] = float(v)
LOG = open(E2 + f"sim_{TAG}.log", "w")
def log(*a, sep=" "):
    LOG.write(sep.join(str(x) for x in a) + "\n"); LOG.flush()
log("params", P, "frames", NF)
D = json.load(open(E2 + MESH)); log("malla", MESH)
if P["snaps"] == 0:   # e2k biseccion de la torsion: sin los 7 broches de la tapeta (la tapeta queda cosida solo al fcR/hsR)
    _k = [i for i, nm in enumerate(D["sew_seam"]) if nm != "broche"]; log("broches: SIN broches (", len(D["sew"]) - len(_k), "resortes fuera)")
    D["sew"] = [D["sew"][i] for i in _k]; D["sew_seam"] = [D["sew_seam"][i] for i in _k]
TPV = set(range(*D["groups"]["tp"])) if P["notp"] > 0 else set()
if TPV:   # e2l DIAGNOSTICO (no es construccion): sin la tapeta -> se quitan sus resortes (costura tapeta y broches), queda fijada (pin) en el molde plano y sin autocolision
    _k = [i for i, (a_, b_) in enumerate(D["sew"]) if a_ not in TPV and b_ not in TPV]
    log("tapeta FUERA (diagnostico):", len(D["sew"]) - len(_k), "resortes quitados", sorted(set(D["sew_seam"][i] for i in range(len(D["sew"])) if i not in set(_k))), "| fijada y sin autocolision")
    D["sew"] = [D["sew"][i] for i in _k]; D["sew_seam"] = [D["sew_seam"][i] for i in _k]
sc = bpy.data.scenes.new("CAMPDIB_E2M")
try: bpy.context.window.scene = sc
except Exception: pass
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
col = bpy.data.collections.new("CampDib_E2M"); sc.collection.children.link(col)
sc.frame_start = 1; sc.frame_end = NF; sc.render.fps = 24
INST = D["inst"]; NV = len(D["v"])

def loft(name, secs, cap=True, mirror=False, poles=None):
    n = 48; bm = bmesh.new(); rings = []; sg = -1.0 if mirror else 1.0
    for z, a, b, yc in secs:
        rings.append([bm.verts.new((sg * a * math.sin(2 * math.pi * k / n), yc - b * math.cos(2 * math.pi * k / n), z)) for k in range(n)])
    def _f(vs): bm.faces.new(vs[::-1] if mirror else vs)
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(n):
            q = (r0[k], r0[(k + 1) % n], r1[(k + 1) % n], r1[k])
            if P["msym"] > 0:   # e2l: triangulos explicitos con la diagonal espejada entre mitades (k < n/2: r0[k]-r1[k+1]; resto: r0[k+1]-r1[k])
                if k < n // 2: _f((q[0], q[1], q[2])); _f((q[0], q[2], q[3]))
                else: _f((q[0], q[1], q[3])); _f((q[1], q[2], q[3]))
            else: _f(q)
    if cap:
        if P["msym"] > 0:   # e2l: tapas en abanico desde un vertice central (simetricas); poles = (z abajo, z arriba) si el polo no esta en el plano del anillo
            zb, zt = poles if poles else (secs[0][0], secs[-1][0])
            cb = bm.verts.new((0.0, secs[0][3], zb)); ct = bm.verts.new((0.0, secs[-1][3], zt))
            for k in range(n):
                _f((cb, rings[0][(k + 1) % n], rings[0][k])); _f((ct, rings[-1][k], rings[-1][(k + 1) % n]))
        else: _f(rings[0][::-1]); _f(rings[-1])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); ob = bpy.data.objects.new(name, me); col.objects.link(ob); return ob
def collider(ob, th=None):
    th = P["th"] if th is None else th
    ob.modifiers.new("col", 'COLLISION'); ob.collision.thickness_outer = th; ob.collision.cloth_friction = P["fric"]; ob.collision.damping = 0.5
    ob.hide_render = True; return ob
# maniqui = el de v4h
# e2e5, MANIQUI v2 (construccion del set): el de v4h tenia el frente plano (pecho -120 / cintura -110 / cadera -115 mm) y el cuello
# horizontal y centrado (el escote de 589 mm se apoyaba horizontal en z 1,50: caida CB->CF 10 mm, real 60-90). Se HUNDEN el vientre
# (hasta 22 mm) y el frente de la base del cuello (22-23 mm) dejando pecho, espalda y anchos: pecho 32 mm delante del vientre y
# ningun punto avanza sobre la pose de arranque (no hay interpenetracion en f1). Contorno de pecho sigue en 97 cm (L ~104).
def _rec(z, a, b, y, d): return (z, a, b - d / 2.0, y + d / 2.0)
TS = [(0.66, 0.19, 0.12, 0), _rec(0.80, 0.185, 0.115, 0, 0.010), _rec(0.95, 0.170, 0.110, 0, 0.022), _rec(1.10, 0.175, 0.115, 0, 0.015),
      (1.25, 0.185, 0.120, 0), (1.36, 0.195, 0.115, 0), _rec(1.42, 0.200, 0.105, 0, 0.005), _rec(1.46, 0.185, 0.090, 0, 0.022),
      _rec(1.49, 0.120, 0.075, 0.0, 0.023), _rec(1.51, 0.070, 0.062, 0.005, 0.012), (1.58, 0.062, 0.060, 0.01)]
if P["nar"] > 0:   # e2j: torso mas angosto bajo la axila (maniqui = construccion): -nar mm de semiancho entre z 1,20 y 1,36, a 0 en z 1,05 y 1,42; solo saca volumen
    def _tp(z): return float(np.clip(min((z - 1.05) / 0.15, (1.42 - z) / 0.06), 0.0, 1.0))
    TS = [(q[0], q[1] - P["nar"] / 1000.0 * _tp(q[0]), q[2], q[3]) for q in TS]
    log("maniqui: torso -", P["nar"], "mm de semiancho bajo la axila:", [(round(q[0], 2), round(q[1], 3)) for q in TS])
torso = collider(loft("CD_maniqui_torso", TS)); TFOBJ = [torso] if P["tfric"] >= 0 else []   # e2zu2: colisionadores que llevan tfric
if P["tfric"] >= 0: torso.collision.cloth_friction = P["tfric"]; log("torso: friccion", P["tfric"], "(mu ~", round(0.01 * P["tfric"], 2), "; camisa + cardigan contra forro 210T ~0,3-0,5)")
if P["msym"] > 0:   # e2l: cabeza = elipsoide 0,085 x 0,105 x 0,12 centrado en (0, 0,01, 1,67) como loft de 15 anillos con polos en abanico (triangulacion espejada)
    _hs = [(1.67 - 0.12 * math.cos(math.pi * j / 16), 0.085 * math.sin(math.pi * j / 16), 0.105 * math.sin(math.pi * j / 16), 0.01) for j in range(1, 16)]
    head = loft("CD_maniqui_cabeza", _hs, poles=(1.67 - 0.12, 1.67 + 0.12))
    log("maniqui SIMETRICO (msym): torso, brazos y cabeza con la triangulacion espejada; brazo L = espejo del R; tapas y polos en abanico")
else:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1, location=(0, 0.01, 1.67))
    head = bpy.context.active_object; head.name = "CD_maniqui_cabeza"; head.scale = (0.085, 0.105, 0.12)
    for c in head.users_collection: c.objects.unlink(head)
    col.objects.link(head)
if P["head"] > 0:
    collider(head)
    if P["hfric"] >= 0: head.collision.cloth_friction = P["hfric"]; log("cabeza: friccion", P["hfric"], "(torso/brazos", P["fric"], ")")
else: head.hide_render = True; log("cabeza: SIN colision (head=0)")
if P["hds"] < 1.0:   # e2g T1-C: la cabeza se retira (escala) mientras la capucha cae y vuelve cuando ya cayo; la tela no se toca
    _s0 = (0.085, 0.105, 0.12); _ss = tuple(v * P["hds"] for v in _s0)
    for _f, _v in ((1, _s0), (int(P["hd0"]), _s0), (int(P["hd1"]), _ss), (int(P["hd2"]), _ss), (int(P["hd3"]), _s0)):
        head.scale = _v; head.keyframe_insert("scale", frame=_f)
    log("cabeza: escala", P["hds"], "de f", int(P["hd0"]), "a f", int(P["hd1"]), "; vuelve de f", int(P["hd2"]), "a f", int(P["hd3"]))
arms = []
for sgn in (1, -1):
    secs = [(-0.64, 0.02, 0.02, 0), (-0.62, 0.040, 0.036, 0), (-0.40, 0.046, 0.044, 0), (-0.20, 0.055, 0.052, 0), (-0.05, 0.060, 0.058, 0), (0.0, 0.058, 0.056, 0)]
    if P["mano"] > 0:   # e2zw (2026-10-05): MANO. El brazo terminaba a 0,62 m del pivote (seccion 40 x 36 mm) y se cerraba en 20 mm: sin mano. El anillo del puno
        # trabaja a 7-14 mm de ese borde y en e2zv1b lo paso (manga L, f48-f60: radio minimo 47 -> 24, la manga entera cae 30-46 mm y arrastra cuello y ruedo).
        # mano=<m> prolonga el tubo <m> metros con la MISMA seccion (perimetro 239 mm = el de una mano real) y recien ahi lo cierra. mano=0 = identico.
        secs = [(-0.64 - P["mano"], 0.02, 0.02, 0), (-0.62 - P["mano"], 0.040, 0.036, 0)] + secs[1:]
    if P["muneca"] > 0:   # RK (2026-10-10, CP85): MUÑECA real. El tubo media 40x36 desde la mano hasta -0,62 y 46x44 en -0,40 (perimetro 265-280 mm en la zona del
        # puño, 0,48-0,62 m del pivote) y llenaba el puño de la M133 (manga 331 mm de perimetro: cascara a R 49 contra tubo a 43, forro sin lugar y crumpled,
        # costura bajo manga 17-30 mm en f66-f72). Un hombre L tiene 18-19 cm de muñeca y 23-25 de antebrazo bajo. muneca=<rx m>: puño de mano 40x36 hasta
        # 9 cm de la punta, muñeca rx x 0,9 rx en -0,62, antebrazo bajo 38x35 en -0,50; el resto igual. muneca=0 = identico.
        _rw = P["muneca"]; secs = [q for q in secs if not (-0.63 < q[0] < -0.61)]   # saca solo la seccion (-0.62, 40x36); la de -0.40 (46x44) queda
        if P["mano"] > 0: secs.append((-0.62 - P["mano"] + 0.09, 0.040, 0.036, 0))
        secs += [(-0.62, _rw, 0.9 * _rw, 0), (-0.50, 0.038, 0.035, 0)]; secs.sort()
    secs = [q for q in secs if q[0] <= P["arm_top"]] + [(P["arm_top"] + 0.02, 0.03, 0.03, 0)]
    ar = loft(f"CD_maniqui_brazo_{'R' if sgn > 0 else 'L'}", secs, mirror=(P["msym"] > 0 and sgn < 0)); ar.location = (P["arm_x0"] * sgn, 0, P["arm_z0"])
    ar.rotation_euler = (0, -sgn * math.radians(P["abd_end"]), 0); collider(ar, th=(P["ath"] if P["ath"] >= 0 else None)); arms.append(ar)
MANIQUI = [torso, head, *arms]
if P["mano"] > 0: log("brazos: MANO de", P["mano"], "m (misma seccion 40 x 36 mm que la muneca); el tubo termina a", round(0.64 + P["mano"], 3), "m del pivote")
if P["muneca"] > 0: log("brazos: MUÑECA real (RK) rx", P["muneca"], "m en -0,62 (perimetro ~", round(2 * math.pi * 0.95 * P["muneca"] * 1000), "mm), antebrazo bajo 38x35 en -0,50 | secciones (z, a, b):", [(q[0], round(q[1], 3), round(q[2], 3)) for q in secs])
if P["arm_end"] >= 0 and P["arm_end"] != P["abd_end"]:   # e2g T2-A: brazo animado abd_end -> arm_end (pre-roll hasta arm_f0, rampa hasta arm_f1)
    for ar, sgn in zip(arms, (1, -1)):
        for _f, _a in ((1, P["abd_end"]), (int(P["arm_f0"]), P["abd_end"]), (int(P["arm_f1"]), P["arm_end"])):
            ar.rotation_euler = (0, -sgn * math.radians(_a), 0); ar.keyframe_insert("rotation_euler", frame=_f)
    log("brazos:", P["abd_end"], "->", P["arm_end"], "grados entre f", int(P["arm_f0"]), "y f", int(P["arm_f1"]))
    if P["arm_x1"] > 0:   # CP11: el hombro del maniqui se abre mientras baja el brazo (hueco de axila constante: en e2i2 cedio la axila a 14 grados)
        for ar, sgn in zip(arms, (1, -1)):
            _xi = P["arm_xi"] if P["arm_xi"] > 0 else P["arm_x0"]; _zi = P["arm_zi"] if P["arm_zi"] > 0 else P["arm_z0"]   # RE: pivote de f1 (donde se armo el V0) -> arm_x0/arm_z0 en arm_f0
            for _f, _x, _z in ((1, _xi, _zi), (int(P["arm_f0"]), P["arm_x0"], P["arm_z0"]), (int(P["arm_f1"]), P["arm_x1"], P["arm_z0"])):
                ar.location = (_x * sgn, 0, _z); ar.keyframe_insert("location", frame=_f)
        log("brazos: pivote f1 x", P["arm_xi"], "z", P["arm_zi"], "(-1 = el de arm_f0) | x", P["arm_x0"], "z", P["arm_z0"], "->", P["arm_x1"], "| espesor", (P["ath"] if P["ath"] >= 0 else P["th"]), "entre f", int(P["arm_f0"]), "y f", int(P["arm_f1"]))

# ---- malla: capa interior separada off mm hacia adentro (normal de la cascara) salvo borde y pespuntes -> volumen inicial > 0
V0 = np.array(D["v"], float); F = np.array(D["f"]); LIN = D["lining"]
VN = np.zeros_like(V0); tri = V0[F]; fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
for j in range(3): np.add.at(VN, F[:, j], fn)
VN /= np.maximum(np.linalg.norm(VN, axis=1, keepdims=True), 1e-12)
fixed = set(D["border"]) | set(D["pinch"])
for n, nf in LIN.items():
    o = INST[n]["off"]; of = INST[nf]["off"]
    cnt = D["groups"][nf][1] - D["groups"][nf][0]
    for k in range(cnt):
        if of + k not in fixed: V0[of + k] = V0[o + k] - P["off"] * VN[o + k]
if P["deltoid"] > 0:   # e2n: deltoides (ver cabecera). Malla centrada en su origen (la escala crece alrededor del centro); L = espejo del R (msym)
    _dc = np.array([P["dl_x"], P["dl_y"], P["dl_z"]]); _da = np.array([P["dl_a"], P["dl_b"], P["dl_c"]]); _s0 = P["dl_s0"]; _mg = P["th"] + P["cd"]
    _es = [(-_da[2] * math.cos(math.pi * j / 16), _da[0] * math.sin(math.pi * j / 16), _da[1] * math.sin(math.pi * j / 16), 0.0) for j in range(1, 16)]
    for sgn in (1, -1):
        dl = loft(f"CD_maniqui_deltoides_{'R' if sgn > 0 else 'L'}", _es, mirror=(P["msym"] > 0 and sgn < 0), poles=(-_da[2], _da[2]))
        dl.location = (sgn * _dc[0], _dc[1], _dc[2]); collider(dl, th=(P["ath"] if P["ath"] >= 0 else None)); MANIQUI.append(dl)
        if _s0 < 1.0:
            for _f, _v in ((1, _s0), (int(P["dl_f"]), 1.0)): dl.scale = (_v, _v, _v); dl.keyframe_insert("scale", frame=_f)
            try:
                for fc in dl.animation_data.action.fcurves:
                    for k in fc.keyframe_points: k.interpolation = 'LINEAR'
            except Exception as e:   # Blender 5: acciones por capas/slots
                try:
                    for lay in dl.animation_data.action.layers:
                        for stp in lay.strips:
                            for cb in stp.channelbags:
                                for fc in cb.fcurves:
                                    for k in fc.keyframe_points: k.interpolation = 'LINEAR'
                except Exception as e2: log("deltoides: interpolacion no lineal", e, e2)
        _c = _dc * np.array([sgn, 1.0, 1.0])
        def _nin(s_): return int(((((V0 - _c) / (_da * s_ + _mg)) ** 2).sum(1) < 1.0).sum()), int(((((V0 - _c) / (_da * s_)) ** 2).sum(1) < 1.0).sum())
        log(f"deltoides {'R' if sgn > 0 else 'L'}: centro {np.round(_c, 3).tolist()} semiejes {np.round(_da, 3).tolist()} | escala {_s0} en f1 -> 1 en f{int(P['dl_f'])}"
            f" | arranque: vertices a < th+cd ({_mg * 1000:.0f} mm) / adentro: en f1 {_nin(_s0)} | a escala 1 {_nin(1.0)} | tope z {_c[2] + _da[2]:.3f}, afuera x {abs(_c[0]) + _da[0]:.3f}")
if BODY:   # e2o: cuerpo MPFB2 (torso + cabeza) como colisionador; el torso y la cabeza del maniqui quedan sin colision
    _B = np.load(E2 + BODY); _V20 = _B["V20"]; _V8 = _B["V8"]; _Vn = _B["Vin"]; _T = _B["T"]; _cab = _B["cabeza"].astype(bool)
    for _o in ((torso, head) if _cab.any() else (torso,)):   # sin caras de cabeza en el npz (ztop) la cabeza sigue siendo la del maniqui
        for _m in [m for m in _o.modifiers if m.type == 'COLLISION']: _o.modifiers.remove(_m)
        _o.hide_viewport = True; _o.hide_render = True
    BODYOBJ = []; _men = np.zeros(len(_T), bool)
    if P["mn_s"] < 1.0:   # [ESC·f535] MN: menton aparte (ver cabecera); pivote = centro de la caja de la cabeza en y, z (x = 0)
        _cen = _V20[_T].mean(1); _men = (_cen[:, 2] >= 1.525) & (_cen[:, 2] < 1.66) & (_cen[:, 1] <= -0.090) & (np.abs(_cen[:, 0]) < 0.09)
        _hb = _V20[np.unique(_T[_cab])]; MN_PIV = np.array([0.0, 0.5 * (_hb[:, 1].min() + _hb[:, 1].max()), 0.5 * (_hb[:, 2].min() + _hb[:, 2].max())])
        log(f"[ESC·f535] MENTON (MN): {int(_men.sum())} triangulos ({int((_men & _cab).sum())} de cabeza, {int((_men & ~_cab).sum())} del torso) | pivote {np.round(MN_PIV, 4).tolist()} | "
            f"escala {P['mn_s']} en f1-f{int(P['mn_f0'])}, lineal a 1 en f{int(P['mn_f1'])}")
    _parts = (("CD_cuerpo_L", ~_cab & ~_men), ("CD_cuerpo_L_cabeza", _cab & ~_men))
    if _men.any(): _parts += (("CD_cuerpo_L_menton", ~_cab & _men), ("CD_cuerpo_L_menton_cabeza", _cab & _men))
    for _nm, _mk in _parts:
        _t = _T[_mk]
        if len(_t) == 0: continue
        _u = np.unique(_t); _rm = -np.ones(len(_V20), int); _rm[_u] = np.arange(len(_u))
        _me = bpy.data.meshes.new(_nm); _me.from_pydata(_V20[_u].tolist(), [], _rm[_t].tolist()); _me.update()
        _ob = bpy.data.objects.new(_nm, _me); col.objects.link(_ob)
        _ob.shape_key_add(name="Basis"); _ka = _ob.shape_key_add(name="angosto", from_mix=False); _kb = _ob.shape_key_add(name="brazos_8", from_mix=False)
        for _i, _j in enumerate(_u): _ka.data[_i].co = tuple(_Vn[_j]); _kb.data[_i].co = tuple(_V8[_j])
        for _f, _v in ((1, 1.0), (int(P["bgrow"]), 0.0)): _ka.value = _v; _ka.keyframe_insert("value", frame=_f)
        if P["arm_end"] >= 0 and P["arm_end"] != P["abd_end"]:
            for _f, _v in ((1, 0.0), (int(P["arm_f0"]), 0.0), (int(P["arm_f1"]), 1.0)): _kb.value = _v; _kb.keyframe_insert("value", frame=_f)
        else: _kb.value = 0.0
        try:
            _ad = _me.shape_keys.animation_data; _fcs = []
            try: _fcs = list(_ad.action.fcurves)
            except Exception:
                for _lay in _ad.action.layers:
                    for _st in _lay.strips:
                        for _cb in _st.channelbags: _fcs += list(_cb.fcurves)
            for _fc in _fcs:
                if "angosto" in _fc.data_path:
                    for _k in _fc.keyframe_points: _k.interpolation = 'LINEAR'
        except Exception as _e: log("cuerpo: interpolacion del angosto no lineal", _e)
        collider(_ob, th=(P["bth"] if P["bth"] >= 0 else None))
        if _nm.endswith("cabeza") and P["hfric"] >= 0: _ob.collision.cloth_friction = P["hfric"]
        elif P["tfric"] >= 0: _ob.collision.cloth_friction = P["tfric"]; TFOBJ.append(_ob)
        MANIQUI.append(_ob); BODYOBJ.append(_ob)
        if _nm.startswith("CD_cuerpo_L_menton"):   # [ESC·f535] MN: origen en el pivote; escala con claves lineales
            import mathutils
            _me.transform(mathutils.Matrix.Translation(tuple(-MN_PIV)), shape_keys=True); _ob.location = tuple(MN_PIV)
            for _f, _v in ((1, P["mn_s"]), (int(P["mn_f0"]), P["mn_s"]), (int(P["mn_f1"]), 1.0)): _ob.scale = (_v, _v, _v); _ob.keyframe_insert("scale", frame=_f)
            _ad = _ob.animation_data; _fcs = []
            try: _fcs = list(_ad.action.fcurves)
            except Exception:
                for _lay in _ad.action.layers:
                    for _st in _lay.strips:
                        for _cb in _st.channelbags: _fcs += list(_cb.fcurves)
            for _fc in _fcs:
                for _k in _fc.keyframe_points: _k.interpolation = 'LINEAR'
            MNOBJ.append(_ob); log(f"[ESC·f535] MENTON: {_nm} {len(_t)} tri, friccion {_ob.collision.cloth_friction} | curvas de escala lineales {len(_fcs)}")
    import mathutils.kdtree
    def _nearest(_A, _Q):   # distancia al vertice mas cercano (mathutils.kdtree: Blender no trae scipy)
        _t = mathutils.kdtree.KDTree(len(_A))
        for _i, _p in enumerate(_A): _t.insert(tuple(_p), _i)
        _t.balance(); return np.array([_t.find(tuple(_q))[2] for _q in _Q])
    _dmin = _nearest(_Vn, V0); _d1 = _nearest(_V20, V0)
    log(f"cuerpo {BODY}: {len(_V20)} vertices, {len(_T)} triangulos ({int(_cab.sum())} de cabeza, friccion {P['hfric']}) | th {P['bth'] if P['bth'] >= 0 else P['th']} | "
        f"angosto 1 en f1 -> 0 en f{int(P['bgrow'])} | brazos_8 f{int(P['arm_f0'])}->f{int(P['arm_f1'])} | campera -> vertice del cuerpo mas cercano: angosto min {_dmin.min() * 1000:.1f} mm, "
        f"completo min {_d1.min() * 1000:.1f} mm (vertices a < 12 mm del completo: {int((_d1 < 0.012).sum())}) | torso del maniqui SIN colision; cabeza del maniqui {'SIN colision' if _cab.any() else 'CON colision (npz sin cabeza)'}")
if P["sand"] > 0 and P["sand_rot"] > 0:   # e2s: tri[0] de cada triangulo tocado = vertice mas cercano al impacto (Blender ata el rayo a tri[0])
    sys.path.insert(0, E2); import sand_e2s as _SE0
    _tm = bpy.data.meshes.new("_tmp_normales"); _tm.from_pydata(V0.tolist(), [], D["f"]); _tm.update()
    _vn = np.empty(NV * 3); _tm.vertices.foreach_get("normal", _vn); _vn = _vn.reshape(-1, 3); bpy.data.meshes.remove(_tm)
    _hits = _SE0.predict_hits(V0, F, _vn, P["sand_len"] / 1000.0, check_normal=P["sand_nc"] > 0)
    F, _nt, _nr = _SE0.rotate_for_ties(D, F, _hits); D["f"] = F.tolist()
    log(f"SANDWICH rotacion: {_nt} triangulos tocados por rayos ht-hs, {_nr} rotados (la normal no cambia)")
    if P["sand_rot"] >= 2:   # e2zs: tri[0] por los impactos SOBRE EL MOLDE (lo que Blender re-detecta en cada reconstruccion del Cloth)
        assert P["sand_lvl"] > P["sand_len"], "sand_rot=2 requiere sand_lvl > sand_len (sandwich R en su nivel: deteccion sin copias coincidentes)"
        _M, _Z2 = _SE0.flat_rest(D, F, _SE0.transl(D), P["sand_d"], P["sand_lvl"])
        _hm = _SE0.predict_hits(_M, F, _SE0.vnormals_np(_M, F), P["sand_len"] / 1000.0, check_normal=P["sand_nc"] > 0)
        F, _nt2, _nr2 = _SE0.rotate_for_ties(D, F, _hm, V=_M); D["f"] = F.tolist()
        log(f"SANDWICH rotacion por el MOLDE (e2zs): {_nt2} triangulos tocados por rayos ht-hs sobre el molde, {_nr2} rotados sobre la rotacion 3D")
NV0 = NV; SEPV = []; SEP_REST = {}
if P["sep_h"] > 0 and D.get("snap_sep") and P["snaps"] > 0 and not TPV:   # e2zd: broche con altura (ver cabecera)
    _kb = [i for i, nm in enumerate(D["sew_seam"]) if nm != "broche"]; _nold = len(D["sew"]) - len(_kb)
    D["sew"] = [D["sew"][i] for i in _kb]; D["sew_seam"] = [D["sew_seam"][i] for i in _kb]
    _h = P["sep_h"] / 1000.0; _UVa = np.array(D["uv"], float); _nv = []; _nuv = []; _nf = []; _msg = []
    for _it in D["snap_sep"]["items"]:
        _t = _it["t"]; _fv = list(_it["face"]); _bc = np.array(_it["bary"]); _B = V0[_fv]
        _n = np.cross(_B[1] - _B[0], _B[2] - _B[0]); _n /= np.linalg.norm(_n); _sg = 1.0 if np.dot(_n, V0[_t] - _bc @ _B) > 0 else -1.0
        _ap = _bc @ _B + _sg * _h * _n
        _R = np.c_[_UVa[_fv] / 1000.0, np.zeros(3)]; _zr = np.sign(np.cross(_R[1] - _R[0], _R[2] - _R[0])[2]); _apr = _bc @ _R + np.array([0.0, 0.0, _sg * _zr * _h])
        _i0 = NV0 + len(_nv); b0, b1, b2, ap = _i0, _i0 + 1, _i0 + 2, _i0 + 3
        # e2zu (2026-10-05): sep_eps=<mm> -> la base del separador nace a sep_eps mm de la cara (hacia la tp), no COINCIDENTE con ella. Con base coincidente
        #   Blender puede crear un resorte interno vertice<->copia de largo 0 y reposo 0: fb(0/0) = NaN, el gradiente conjugado no itera y TODO el Cloth queda
        #   congelado hasta la proxima reconstruccion (m133_e2zt1.json: broches 1, 2 y 4; f2-f3 sin dinamica en las 6 sims e2zt). sep_eps=0 = identico.
        _Bs = _B + _sg * (P["sep_eps"] / 1000.0) * _n
        _nv += [*_Bs.tolist(), _ap.tolist()]; _nuv += [(_R[k][:2] * 1000.0).tolist() for k in range(3)] + [(_apr[:2] * 1000.0).tolist()]
        for k in range(3): SEP_REST[_i0 + k] = tuple(_R[k])
        SEP_REST[ap] = tuple(_apr)
        _nf += ([[b0, b2, b1], [b0, b1, ap], [b1, b2, ap], [b2, b0, ap]] if _sg > 0 else [[b0, b1, b2], [b1, b0, ap], [b2, b1, ap], [b0, b2, ap]])
        D["sew"] += [[b0, _fv[0]], [b1, _fv[1]], [b2, _fv[2]], [ap, _t]]; D["sew_seam"] += ["broche base"] * 3 + ["broche"]
        _msg.append(f"t{_t}: apice-t {np.linalg.norm(_ap - V0[_t]) * 1000:.1f} mm")
    SEPV = list(range(NV0, NV0 + len(_nv))); V0 = np.vstack([V0, np.array(_nv)]); D["v"] = D["v"] + _nv; D["uv"] = D["uv"] + _nuv
    D["pocket"] = list(D["pocket"]) + [None] * len(_nv); F = np.vstack([F, np.array(_nf, int)]); D["f"] = F.tolist(); D["groups"]["snap_sep"] = [NV0, NV0 + len(_nv)]
    NV = len(V0)
    log(f"BROCHES CON ALTURA (e2zd): {len(D['snap_sep']['items'])} separadores de {P['sep_h']} mm | base a {P['sep_eps']} mm de la cara (e2zu; 0 = coincidente) | {_nold} resortes 'broche' viejos fuera | +{len(_nv)} vertices, +{len(_nf)} caras | " + " ".join(_msg))
ANCV = []; ANC_REST = {}; ANC_CO1 = None; ESC_RIG = []; ANC_PEND = {}; ESC_W0 = {}   # [ESC·f535] PQ: anclas del escote (ver cabecera de argumentos)
if ESC:
    _ez = np.load(E2 + ESC); ESC_RIG = [int(i) for i in _ez["rig"]] if "rig" in _ez.files else []
    _pi = [int(i) for i in _ez["pin"]] if "pin" in _ez.files else []
    assert not TPV and all(i < NV0 for i in ESC_RIG + _pi), "esc: ids fuera de la malla o con notp"
    if _pi:
        _c0 = np.array(_ez["co0"], float); assert _c0.shape == (len(_pi), 3), ("esc: co0", _c0.shape, len(_pi))
        _a0 = len(V0); ANCV = list(range(_a0, _a0 + len(_pi))); V0 = np.vstack([V0, _c0]); D["v"] = D["v"] + _c0.tolist()
        D["uv"] = D["uv"] + [D["uv"][i] for i in _pi]; D["pocket"] = list(D["pocket"]) + [None] * len(_pi); D["groups"]["anclas"] = [_a0, _a0 + len(_pi)]
        D["sew"] += [[a_, i_] for a_, i_ in zip(ANCV, _pi)]; D["sew_seam"] += ["ancla escote"] * len(_pi); NV = len(V0)
        for a_, c_ in zip(ANCV, _c0): ANC_REST[a_] = tuple(c_)
        if "co1" in _ez.files: ANC_CO1 = np.array(_ez["co1"], float)
        _d0 = np.linalg.norm(_c0 - V0[_pi], axis=1) * 1000
        log(f"[ESC·f535] ANCLAS (PQ): {ESC} | {len(_pi)} anclas fijas cosidas a su vertice | ancla-vertice en f1 p50 {np.median(_d0):.2f} max {_d0.max():.2f} mm | "
            f"co1 {'si, hasta f%d (desplazamiento max %.1f mm)' % (int(P['esc_f1']), 1000 * np.linalg.norm(ANC_CO1 - _c0, axis=1).max()) if ANC_CO1 is not None else 'no'}")
    log(f"[ESC·f535] ESC (PQ): rigidez maxima en {len(ESC_RIG)} vertices | anclas {len(ANCV)}")
PTV = []; PT_PAR = []   # [ESC·f535] PT: margen-puente del cuello (ver cabecera de argumentos)
if P["pt_w"] > 0:
    assert not ANCV, "pt_w con anclas (esc=) no probado"
    sys.path.insert(0, E2 + "_qc_PT"); import puente_PT as _PT
    _r = _PT.margen(D, V0, P["pt_w"], P["pt_off"]); _p0 = len(V0); _nm = len(_r["v"]); assert _nm > 0 and len(D["uv"]) == _p0, ("pt", _nm, len(D["uv"]), _p0)
    V0 = np.vstack([V0, np.array(_r["v"], float)]); D["v"] = D["v"] + _r["v"]; D["uv"] = D["uv"] + _r["uv"]; D["pocket"] = list(D["pocket"]) + [None] * _nm
    F = np.vstack([F, np.array(_r["f"], int)]); D["f"] = F.tolist(); D["groups"]["puente"] = [_p0, _p0 + _nm]
    D["sew"] += [[int(a_), int(b_)] for a_, b_ in _r["sew"]]; D["sew_seam"] += ["puente canto"] * len(_r["sew"])
    PTV = list(range(_p0, _p0 + _nm)); PT_PAR = [int(a_) for a_ in _r["par"]]; NV = len(V0)
    log(f"[ESC·f535] PUENTE (PT): {_r['msg']} | +{_nm} v, +{len(_r['f'])} caras, +{len(_r['sew'])} resortes 'puente canto' | NV {NV}")
if P["pc_w"] > 0:   # [ESC·f535] HB: margen-puente de hc sobre las costuras copa R y L (ver cabecera)
    assert P["pt_w"] <= 0 and not ANCV, "pc_w con pt_w o esc= no probado"
    sys.path.insert(0, E2 + "_qc_PT"); import puente_PT as _PT
    _PT.COLLAR = ("hc",); _PT.BODY = ("hsR", "hsL")
    _p0 = len(V0); _vs, _uvs, _fs, _ss, _pa, _ms = [], [], [], [], [], []
    for _sn in ("copa capucha R", "copa capucha L"):
        _r = _PT.margen(D, V0, P["pc_w"], P["pc_off"], seam=_sn); _k0 = len(_vs)   # margen() numera lo nuevo desde len(V0): correr por lo ya agregado
        _fs += [[(x_ if x_ < _p0 else x_ + _k0) for x_ in f_] for f_ in _r["f"]]; _ss += [(m_ + _k0, d_) for m_, d_ in _r["sew"]]
        _vs += _r["v"]; _uvs += _r["uv"]; _pa += [int(a_) for a_ in _r["par"]]; _ms.append(_sn + ": " + _r["msg"])
    _nm = len(_vs); assert _nm > 0 and len(D["uv"]) == _p0, ("pc", _nm, len(D["uv"]), _p0)
    V0 = np.vstack([V0, np.array(_vs, float)]); D["v"] = D["v"] + _vs; D["uv"] = D["uv"] + _uvs; D["pocket"] = list(D["pocket"]) + [None] * _nm
    F = np.vstack([F, np.array(_fs, int)]); D["f"] = F.tolist(); D["groups"]["puente"] = [_p0, _p0 + _nm]
    D["sew"] += [[int(a_), int(b_)] for a_, b_ in _ss]; D["sew_seam"] += ["puente canto"] * len(_ss)
    PTV = list(range(_p0, _p0 + _nm)); PT_PAR = _pa; NV = len(V0)
    log(f"[ESC·f535] PUENTE COPA (HB): +{_nm} v, +{len(_fs)} caras, +{len(_ss)} resortes 'puente canto' | NV {NV} || " + " || ".join(_ms))
if P["hf"] > 0:   # [ESC·f535] HP: forro de capucha (ver cabecera)
    _fj = json.load(open(E2 + __import__("os").environ.get("M133_FORRO", "_qc_HP/forro_HP.json"))); _p0 = len(V0); _nm = len(_fj["v"]); assert len(D["uv"]) == _p0, ("hf", len(D["uv"]), _p0)
    _dv = max(float(np.abs(V0[i] - np.array(D["v"][i])).max()) for i in _fj["pocket_shell"][:50]) * 1000
    V0 = np.vstack([V0, np.array(_fj["v"], float)]); D["v"] = D["v"] + _fj["v"]; D["uv"] = D["uv"] + _fj["uv"]; D["pocket"] = list(D["pocket"]) + [None] * _nm
    F = np.vstack([F, np.array(_fj["f"], int) + _p0]); D["f"] = F.tolist()
    for _n, (_a, _b) in _fj["groups"].items(): D["groups"][_n] = [_p0 + _a, _p0 + _b]
    _dec = lambda x_: int(x_) if x_ >= 0 else _p0 + (-int(x_) - 1)
    D["sew"] += [[_dec(a_), _dec(b_)] for a_, b_ in _fj["sew"]]; D["sew_seam"] += list(_fj["seam"])
    FHV = list(range(_p0, _p0 + _nm)); FHS = [int(i) for i in _fj["pocket_shell"]]; NV = len(V0)
    log(f"[ESC·f535] FORRO CAPUCHA (HP): +{_nm} v, +{len(_fj['f'])} caras, +{len(_fj['sew'])} resortes {sorted(set(_fj['seam']))} | NV {NV} | V0 cascara vs malla {_dv:.3f} mm || " + " || ".join(_fj["msg"]))
me = bpy.data.meshes.new("CD_campera"); me.from_pydata(V0.tolist(), D["sew"], D["f"])
gar = bpy.data.objects.new("CD_campera", me); col.objects.link(gar)
for name, (a, b) in D["groups"].items():
    vg = gar.vertex_groups.new(name=name); vg.add(list(range(a, b)), 1.0, 'REPLACE')
# reposo = molde plano desde f2 (Dynamic Mesh)
gar.shape_key_add(name="Basis"); kc = gar.shape_key_add(name="molde_plano", from_mix=False)
for i, (u, w) in enumerate(D["uv"]): kc.data[i].co = (u / 1000.0, w / 1000.0, 0.0)
RELLENO_F = []   # RI (2026-10-10, CP83): relleno=<peso> -> el forro de cada canal a z = -normal x relleno_h en el molde plano (traslacion rigida, isometrica):
#   los pares internos cascara-forro que Blender ya detectaba (reposo 0, peso 0 = inertes) pasan a reposo relleno_h = LOFT del relleno inyectado (tapa globos
#   y pone piso en el CF). Sin relleno = identico (copia _papelera/sim_e2s_pre_RI2.py). Requiere sand=1 y relleno_h < sand_len (deteccion sobre el molde).
if P["relleno"] > 0:
    assert P["sand"] > 0 and P["relleno_h"] < P["sand_len"], "relleno requiere sand=1 y relleno_h < sand_len"
    _UVa = np.array(D["uv"], float); _TL = {}
    if P["relleno_r"] > 0:   # RJ (2026-10-10, CP84): relleno_r=<mm> -> LENTE: espesor de reposo = relleno_h x perfil almohada de la distancia al pespunte/costura
        #   (0 en pespuntes, bordes y costuras; piso relleno_min), _qc_RJ/lente.py. Sin relleno_r = constante (RI, paredes en los pespuntes: ruedo +139, STOP f30).
        sys.path.insert(0, E2 + "_qc_RJ"); import lente as _LE
        _TL, _DL = _LE.espesores(D, F, P["relleno_h"], P["relleno_r"], P["relleno_min"]); _tt = np.array(list(_TL.values()))
        log(f"RELLENO LENTE (RJ): h {P['relleno_h']} r {P['relleno_r']} piso {P['relleno_min']} | {len(_TL)} v del forro | t media {_tt.mean():.2f} p50 {np.median(_tt):.1f} max {_tt.max():.1f}")
        for _ln in _LE.informe(D, F, _TL, _DL, P["relleno_h"], P["relleno_r"]).split("\n"):
            if "_f:" in _ln: log("RELLENO LENTE", _ln.strip())
    for _c, _fz in D["lining"].items():
        _a, _b = D["groups"][_c]; _t = F[(F[:, 0] >= _a) & (F[:, 0] < _b)][:300]
        _e1 = _UVa[_t[:, 1]] - _UVa[_t[:, 0]]; _e2 = _UVa[_t[:, 2]] - _UVa[_t[:, 0]]
        _sg = float(np.sign(np.sign(_e1[:, 0] * _e2[:, 1] - _e1[:, 1] * _e2[:, 0]).sum()))   # signo de la normal z de la cascara en el molde
        _a2, _b2 = D["groups"][_fz]
        for i in range(_a2, _b2): kc.data[i].co = (D["uv"][i][0] / 1000.0, D["uv"][i][1] / 1000.0, -_sg * _TL.get(i, P["relleno_h"]) / 1000.0)
        RELLENO_F += list(range(_a2, _b2))
    log("RELLENO (RI): forro", list(D["lining"].values()), "a z = -normal x", P["relleno_h"], "mm en el molde plano |", len(RELLENO_F), "vertices | peso", P["relleno"],
        "en 'interno' | guardia f1: peso 0 a <", P["relleno_g"], "mm de piezas no-canal en V0, se levanta en el primer set_weights del lazo")
for i, co_ in SEP_REST.items(): kc.data[i].co = co_   # e2zd: reposo del separador = el mismo tetraedro (no es plano)
for i, co_ in ANC_REST.items(): kc.data[i].co = co_   # [ESC·f535] PQ: el ancla no se mueve con el molde (delta 0 contra la Basis)
import os as _os
sys.path.insert(0, E2)
import sand_e2s as SE
SAND_T = SE.transl(D) if P["sand"] > 0 else None
SAND_Z = SE.flat_levels(D, F, P["sand_d"], P["sand_lvl"]) if (P["sand"] > 0 and P["sand_lvl"] > 0) else None   # e2zs (ver cabecera)
def _sand_co(i, u, w):   # e2s: reposo del ht superpuesto al hs (traslacion rigida del molde: no cambia su forma ni sus costuras)
    for s_ in "RL":
        a_, b_ = D["groups"]["ht" + s_]
        if a_ <= i < b_:   # control: sand_txy=0 sin trasladar en el plano; sand_zs = signo de z por lado (+1 = -d en los dos; -1 = L en +d)
            t_ = SAND_T[s_][0] * P["sand_txy"]; z_ = SAND_Z["ht" + s_] if SAND_Z else -P["sand_d"] * (1.0 if s_ == "R" else P["sand_zs"]); return ((u - t_[0]) / 1000.0, (w - t_[1]) / 1000.0, z_ / 1000.0)
        if SAND_Z:   # e2zs: el hs de cada lado en su nivel (R sube sand_lvl)
            a_, b_ = D["groups"]["hs" + s_]
            if a_ <= i < b_: return (u / 1000.0, w / 1000.0, SAND_Z["hs" + s_] / 1000.0)
    return (u / 1000.0, w / 1000.0, 0.0)
if P["sand"] > 0 and P["sand_ov"] > 0:
    for s_ in "RL":
        for g_ in ["ht" + s_] + (["hs" + s_] if SAND_Z else []):
            a_, b_ = D["groups"][g_]
            for i in range(a_, b_): kc.data[i].co = _sand_co(i, *D["uv"][i])
    if SAND_Z: log("SANDWICH NIVELES (e2zs): z del molde (mm)", {k_: round(v_, 2) for k_, v_ in SAND_Z.items() if not k_.startswith("n")}, "| normal del hs en el molde", {s_: SAND_Z["n" + s_] for s_ in "RL"})
    log("SANDWICH: reposo del ht superpuesto al hs en el molde plano, T", {s_: (np.round(SAND_T[s_][0], 2).tolist(), round(SAND_T[s_][1], 2), SAND_T[s_][3]) for s_ in "RL"}, "z", -P["sand_d"], "mm")
if HREST:   # RG (2026-10-09, CP78): hrest=<npz> (ids, co en m; _qc_RG/mk_hrest.py) -> REPOSO EN FORMA: esos vertices de la clave molde_plano pasan a una forma 3D ISOMETRICA al molde
    #   (doblado desarrollable: mismos largos de reposo, cambian solo los angulos de reposo). Sin hrest = identico (copia previa: _papelera/sim_e2s_pre_RG.py).
    assert P["cinch"] <= 0, "hrest con cinch > 0: la clave cordon reescribe el molde plano de todos los vertices (reaplicar hrest ahi)"
    _hz = np.load(E2 + HREST); _hi = _hz["ids"].astype(int); _hco = _hz["co"].astype(float); assert len(_hi) == len(_hco) and int(_hi.max()) < NV0, ("hrest: la malla no coincide", len(_hi), NV0)
    _mp = np.array([kc.data[int(_i)].co[:] for _i in _hi])
    for _i, _c in zip(_hi, _hco): kc.data[int(_i)].co = (float(_c[0]), float(_c[1]), float(_c[2]))
    _gn = sorted(set(_n for _n, (_a, _b) in D["groups"].items() for _i in (int(_hi.min()), int(_hi.max())) if _a <= _i < _b))
    log(f"REPOSO EN FORMA (RG): {HREST} | {len(_hi)} vertices de {_gn} | z del reposo {1000 * _hco[:, 2].min():.0f}..{1000 * _hco[:, 2].max():.0f} mm (molde plano: {1000 * _mp[:, 2].min():.0f}..{1000 * _mp[:, 2].max():.0f})")
if P["pc_w"] > 0:   # [ESC·f535] HB: reposo del margen = reposo de su vertice de hc + molde (PT-R; despues de relleno, sandwich y hrest)
    assert not HREST and not RK, "pc_w con hrest/rk no probado"
    log(f"[ESC·f535] PUENTE COPA (HB) reposo: {_PT.reposo(kc, PTV[0], PT_PAR, D['uv'])}")
FMP = int(P["fmp"])   # e2zf: fmp=N -> el reposo queda FIJO en V0 (Basis) hasta fN (control: separar arranque fuera de equilibrio de cambio de reposo); 2 = identico
if RK:   # e2ze: reposo en rampa ARAP (ver cabecera)
    _KZ = np.load(E2 + RK)["keys"]; _nk = len(_KZ); _f0 = int(P["rk_f0"]); _df = int(P["rk_df"]); FMP = _f0 + _nk * _df
    assert _KZ.shape[1] == NV0, ("rk: la malla no coincide", _KZ.shape, NV0)
    for _k in range(_nk):
        _kk = gar.shape_key_add(name=f"rk{_k + 1}", from_mix=False); _co = np.array(V0, float).copy(); _co[:NV0] = _KZ[_k]
        for i, co_ in SEP_REST.items(): _co[i] = co_
        _kk.data.foreach_set("co", _co.ravel())
        for f, v in ((1, 0.0), (_f0 + _k * _df, 1.0), (_f0 + (_k + 1) * _df, 0.0)): _kk.value = v; _kk.keyframe_insert("value", frame=f)
    log(f"RAMPA DE REPOSO (e2ze): {RK} | {_nk} claves ARAP desde f{_f0}, una cada {_df} cuadros | molde_plano = 1 en f{FMP}")
for f, v in ((1, 0.0), (FMP, 1.0)): kc.value = v; kc.keyframe_insert("value", frame=f)
log(f"molde_plano = 1 en f{FMP} (fmp {int(P['fmp'])}, rk {bool(RK)})")
if P["nrb"] > 0: log(f"NRB (e2zi): el lazo de volumen no reescribe 'presion' -> sin reconstrucciones del Cloth ni cuadros muertos" + (" | OJO: pres > 0 con pesos congelados" if P["pres"] > 0 else ""))
ad = gar.data.shape_keys.animation_data
# e2zi (2026-10-01) BUG de Blender 5.x: Action.fcurves ya no existe (acciones por capas) -> el try viejo fallaba ('interp ... no attribute fcurves', 190 de 200
#   logs) y las claves de reposo quedaban en BEZIER. Con 2 claves (molde_plano 1->2) no cambia nada en cuadros enteros, pero con la rampa rk los pesos se
#   SUMAN (f12: molde 0,5 + 4 claves rk ~0,6-0,9 = 3,6) -> reposo basura -> presim e2zh invalida (230 mm, 137 k cruces). Ahora: capas/canales, CONSTANT solo
#   en molde_plano y rk* (el cordon, si cinch > 0, sigue con su rampa), y log de los pesos por cuadro (suma 1 desde f2). Copia previa: _papelera/sim_e2s_pre_e2zi.py
try:
    _fcs = []
    try: _fcs = list(ad.action.fcurves)
    except Exception:
        for _lay in ad.action.layers:
            for _st in _lay.strips:
                for _cb in _st.channelbags: _fcs += list(_cb.fcurves)
    _rfc = [fc for fc in _fcs if 'key_blocks["molde_plano"]' in fc.data_path or 'key_blocks["rk' in fc.data_path]
    for fc in _rfc:
        for k in fc.keyframe_points: k.interpolation = 'CONSTANT'
    _wl = []
    for _f in range(1, min(FMP + 2, 61)):
        _w = {fc.data_path.split('"')[1]: fc.evaluate(_f) for fc in _rfc}; _nz = {k_: round(v_, 4) for k_, v_ in _w.items() if abs(v_) > 1e-9}
        _wl.append(f"f{_f} {_nz} suma {sum(_w.values()):.4f}")
    log(f"interp CONSTANT en {len(_rfc)} curvas de reposo de {len(_fcs)} | pesos por cuadro: " + " ; ".join(_wl))
except Exception as e: log("interp", e)
if ANCV and ANC_CO1 is not None:   # [ESC·f535] PQ: clave solo de las anclas (delta 0 exacto en la prenda: copia de la Basis), 0 en f1 -> 1 en esc_f1
    _kb0 = gar.data.shape_keys.key_blocks["Basis"]; _ka = gar.shape_key_add(name="anclas_cf", from_mix=False); _ka.relative_key = _kb0
    _cb = np.empty(len(_kb0.data) * 3); _kb0.data.foreach_get("co", _cb); _cb = _cb.reshape(-1, 3); _cb[ANCV] = ANC_CO1; _ka.data.foreach_set("co", _cb.ravel())
    for _f, _v in ((1, 0.0), (int(P["esc_f1"]), 1.0)): _ka.value = _v; _ka.keyframe_insert("value", frame=_f)
    _ka.value = 0.0
    log(f"[ESC·f535] ANCLAS: clave anclas_cf 0 en f1 -> 1 en f{int(P['esc_f1'])} | prenda delta max {np.abs(_cb[:ANCV[0]] - np.array([v.co[:] for v in _kb0.data])[:ANCV[0]]).max():.1e}")

BOCA = D.get("boca"); CORD = D["groups"].get("cord")
if BOCA and CORD and P["cinch"] > 0:   # e2k: tirado del cordon = reposo del tramo ojal-ojal x (1 - cinch), en rampa (el ancho de la cinta no cambia)
    kq = gar.shape_key_add(name="cordon", from_mix=False); kq.relative_key = kc
    for i, (u, w) in enumerate(D["uv"]): kq.data[i].co = _sand_co(i, u, w) if (P["sand"] > 0 and P["sand_ov"] > 0) else (u / 1000.0, w / 1000.0, 0.0)
    for i, co_ in SEP_REST.items(): kq.data[i].co = co_
    _c0 = D["uv"][CORD[0]][0]
    for i in range(*CORD):
        u, w = D["uv"][i]; kq.data[i].co = ((_c0 + (u - _c0) * (1.0 - P["cinch"])) / 1000.0, w / 1000.0, 0.0)
    for f, v in ((1, 0.0), (int(P["cz0"]), 0.0), (int(P["cz1"]), 1.0)): kq.value = v; kq.keyframe_insert("value", frame=f)
    log("cordon: tirado", P["cinch"], "| reposo ojal-ojal", D["inst"]["cord"]["largo_tunel_mm"], "->", round(D["inst"]["cord"]["largo_tunel_mm"] * (1 - P["cinch"]), 1), "mm entre f", int(P["cz0"]), "y f", int(P["cz1"]))
# ---- bolsillos: caras por bolsillo (centroide en el molde -> canal), area y volumen objetivo
UV = np.array(D["uv"]); PK = D["pocket"]; LX = D["lx"]
face_pk = np.full(len(F), -1); names = sorted(D["pocket_area_m2"]); idx = {n: i for i, n in enumerate(names)}
for n in ['back', 'fcR', 'fcL', 'fsR', 'fsL', 'slR', 'slL']:
    for nm in (n, n + "_f"):
        I = INST[nm]; a, b = I["foff"], I["foff"] + I["nf"]; cx = UV[F[a:b]].mean(1)[:, 0]
        ch = (np.array(LX[I["key"]])[None, :] < cx[:, None]).sum(1)
        face_pk[a:b] = [idx[f"{n}{c}"] for c in ch]
AREA = np.array([D["pocket_area_m2"][n] for n in names]); HK = np.array([P["h_sl"] if n.startswith("sl") else P["h_body"] for n in names])
VT = AREA * (4.0 / 3.0) * HK * P["vtk"]
vpk = collections.defaultdict(list)
for i, pk in enumerate(PK):
    if pk is not None and pk in idx: vpk[idx[pk]].append(i)
PLACK = set(D["placket"])
for k in vpk: vpk[k] = [i for i in vpk[k] if i not in PLACK]
W = np.full(len(names), P["w0"])
if WINI:   # e2zj: pesos de presion por bolsillo FIJOS desde f1 (los finales de un humo de control: bolsillos_<tag>.json); con nrb=1 no se reescriben
    _wj = json.load(open(E2 + WINI)); assert list(_wj["names"]) == list(names), "wini: otros bolsillos"; W = np.array(_wj["w"], float)
    log("WINI (e2zj): pesos de presion fijos desde", WINI, "| min/med/max", round(float(W.min()), 3), round(float(np.median(W)), 3), round(float(W.max()), 3))
vpres = gar.vertex_groups.new(name="presion")
# e2h (consulta B): franja bajo la axila (cuerpo: z_ax - banda .. z_ax, costado |x| > 0,12; manga: mitad interna, z > z_ax - 0,25): el objetivo de
# volumen de su parte del bolsillo y su peso de presion bajan en rampa 1 -> uarm, sincronizados con el brazo (arm_f0 -> arm_f1). El plumon real se comprime.
UA_IDS = set(); FR = np.zeros(len(names)); MF = [1.0]
if P["uarm"] >= 0:
    _body = [n for n in D["groups"] if n.split("_")[0] in ("back", "fcR", "fcL", "fsR", "fsL")]; _sl = [n for n in D["groups"] if n.split("_")[0] in ("slR", "slL")]
    for n in _body:
        a_, b_ = D["groups"][n]; ids = np.arange(a_, b_); m = (V0[ids, 2] > P["z_ax"] - P["uarm_band"]) & (V0[ids, 2] < P["z_ax"]) & (np.abs(V0[ids, 0]) > 0.12)
        UA_IDS |= set(ids[m].tolist())
    for n in _sl:
        a_, b_ = D["groups"][n]; ids = np.arange(a_, b_); sgx = 1.0 if n.startswith("slR") else -1.0
        ax = V0[ids].mean(0); m = (V0[ids, 2] > P["z_ax"] - 0.25) & ((V0[ids, 0] - ax[0]) * sgx < 0)
        UA_IDS |= set(ids[m].tolist())
    for k, ids in vpk.items(): FR[k] = np.mean([i in UA_IDS for i in ids]) if ids else 0.0
    log("franja bajo la axila:", len(UA_IDS), "vertices; fraccion por bolsillo >0:", {names[k]: round(float(FR[k]), 2) for k in range(len(names)) if FR[k] > 0})
HOLD = np.ones(len(names)); HK_ = []   # e2zb cf_hold: factor por bolsillo (1 = sin retener)
if P["cf_hold"] > 0:
    _sides = {0: "RL", 1: "L", 2: "R"}[int(P["cf_lr"])]
    HK_ = [idx[f"fc{s_}{c}"] for s_ in _sides for c in str(int(P["cf_ch"])) if f"fc{s_}{c}" in idx]; HOLD[HK_] = 0.0
    log("CF_HOLD: bolsillos", [names[k] for k in HK_], "sin presion hasta f", int(P["cf_hold"]), "+ rampa", int(P["cf_ramp"]), "cuadros |", sum(len(vpk[k]) for k in HK_ if k in vpk), "vertices")
def set_weights():
    global RELLENO_PEND, ANC_PEND
    if globals().get("RELLENO_PEND"):   # RI: levanta la guardia del relleno en la primera reescritura del lazo (reposo ya en el molde: la deteccion no ve avios)
        vint.add(RELLENO_PEND, float(P["relleno"]), 'REPLACE'); log(f"RELLENO: guardia levantada, {len(RELLENO_PEND)} vertices del forro al peso {P['relleno']}"); RELLENO_PEND = []
    if globals().get("ANC_PEND"):   # [ESC·f535] PQ: guardia de las anclas (mismo momento que la del relleno)
        for _j, _w in ANC_PEND.items(): vint.add([_j], float(_w), 'REPLACE')
        log(f"[ESC·f535] ANCLAS: guardia levantada, {len(ANC_PEND)} vertices vuelven a su peso interno"); ANC_PEND = {}
    for k, ids in vpk.items():
        wk = float(W[k]) if HOLD[k] >= 1.0 else max(float(W[k] * HOLD[k]), 1e-4)
        if FR[k] > 0 and MF[0] < 1.0:
            a_ = [i for i in ids if i not in UA_IDS]; b_ = [i for i in ids if i in UA_IDS]
            if a_: vpres.add(a_, wk, 'REPLACE')
            if b_: vpres.add(b_, wk * MF[0], 'REPLACE')
        else: vpres.add(ids, wk, 'REPLACE')
set_weights()
if PLACK: vpres.add(sorted(PLACK), 0.0, 'REPLACE')
if FHV and P["hf_w"] > 0:   # [ESC·f535] HP: presion cascara-forro de la capucha, peso constante (los ids no estan en vpk: set_weights no los toca)
    vpres.add(FHS + FHV, float(P["hf_w"]), 'REPLACE'); log(f"[ESC·f535] PRESION CAPUCHA (HP): peso {P['hf_w']} en {len(FHS)} v de cascara + {len(FHV)} v de forro (p0 {P['p0']})")
vrig = gar.vertex_groups.new(name="rigidez")
vrig.add(D["zipper"], 1.0, 'REPLACE'); vrig.add(D["placket"], P["w_plk"], 'REPLACE')
if P["w_plk"] != 1.0: log("tapeta: peso de rigidez", P["w_plk"], "(1 = flexion max, como el cierre)")
if P["cuff_on"] > 0: vrig.add(D["cuff"], P["w_cuff"], 'REPLACE')   # e2m: bug de e2k arreglado (el puno quedaba dentro del if de w_plk); cuff_on=0 reproduce e2k..e2m3
log("RIGIDEZ tapeta w_plk", P["w_plk"], "-> flexion", round(P["bending"] + (P["bend_max"] - P["bending"]) * P["w_plk"], 1), "| puno:", ("w_cuff %s" % P["w_cuff"]) if P["cuff_on"] > 0 else "SIN peso (flexion base, como e2k-e2m3)")
BAND = [i for n in D["band"].values() for i in range(*D["groups"][n])]; vrig.add(BAND, P['w_band'], 'REPLACE')
# e2g: rigidez por franja REAL (rig_e2g.py): columna del cuello chimenea (hs bajo la vista + ht) y franja de margenes de la costura de sisa
if D.get("rig_cuello") and P["w_neck"] > 0: vrig.add(D["rig_cuello"], P["w_neck"], 'REPLACE'); log("rigidez cuello", len(D["rig_cuello"]), "peso", P["w_neck"])
if D.get("rig_sisa") and P["w_sisa"] > 0: vrig.add(D["rig_sisa"], P["w_sisa"], 'REPLACE'); log("rigidez sisa", len(D["rig_sisa"]), "peso", P["w_sisa"])
if D.get("rig_costado") and P.get("w_cost", 0.0) > 0: vrig.add(D["rig_costado"], P["w_cost"], 'REPLACE'); log("rigidez costado (e2x: margenes de la costura del costado)", len(D["rig_costado"]), "peso", P["w_cost"])
# e2i: que es "capucha" para hood_bend/hood_soft. hood_scope=1: hs fuera de la huella del ht + hc (el cuello chimenea = hs bajo el ht + ht,
# que en la real lleva cascara + guata + vista, queda con la rigidez del cuerpo); hood_scope=0: hs + hc + ht (como e2h4/e2h6)
_ALLH = set(i for n in ("hsR", "hsL", "hc", "htR", "htL", "hb", "cord") if n in D["groups"] for i in range(*D["groups"][n]))
if P["hood_scope"] > 0 and D.get("rig_cuello"):
    _cue = set(D["rig_cuello"]); HOODSET = set(i for n in ("hsR", "hsL", "hc", "hb", "cord") if n in D["groups"] for i in range(*D["groups"][n])) - _cue - set(D["zipper"]) - set(D["placket"])
    log("capucha (hood_scope=1): ", len(HOODSET), "vertices sin el cuello (", len(_ALLH & _cue), "de cuello quedan como el cuerpo)")
else: HOODSET = _ALLH
if P["hood_bend"] >= 0:   # e2h: flexion propia de la capucha (hs, hc, ht); el resto conserva su flexion efectiva b = bending + (max - bending) w
    _b0, _bm = P["bending"], P["bend_max"]; _hb = P["hood_bend"]; _W = np.zeros(NV)
    for _gn in ("rigidez",):
        _vg = gar.vertex_groups[_gn]
        for _v in gar.data.vertices:
            for _g in _v.groups:
                if _g.group == _vg.index: _W[_v.index] = _g.weight
    _Wn = (_b0 + (_bm - _b0) * _W - _hb) / (_bm - _hb); _HOOD = HOODSET
    _Wn[list(_HOOD)] = 0.0
    for _i in range(NV): vrig.add([_i], float(_Wn[_i]), 'REPLACE')
    P["bending"] = _hb; log("flexion: capucha", _hb, "| resto igual (peso remapeado; base", _b0, "->", _hb, ")")
if P.get("pl_bh", -1.0) > 0:   # e2q PLANCHA: capucha mas rigida a la flexion que la base (panel de 3 capas: cascara + guata + forro)
    assert P["hood_bend"] < 0, "pl_bh requiere hood_bend < 0 (hood_bend remapea la base hacia abajo)"
    _wh = (P["pl_bh"] - P["bending"]) / (P["bend_max"] - P["bending"]); vrig.add(sorted(HOODSET), float(_wh), 'REPLACE')
    log("PLANCHA capucha: flexion", P["pl_bh"], "(peso", round(_wh, 5), ") en", len(HOODSET), "vertices | cuello w_neck", P["w_neck"], "-> flexion",
        round(P["bending"] + (P["bend_max"] - P["bending"]) * P["w_neck"], 1), "| tapeta w_plk", P["w_plk"], "| compresion capucha", "blanda" if P["hood_soft"] > 0 else P["compression"])
if P["bmx"] > 0 or P["neck_hs"] >= 0 or P["neck_ht"] >= 0:   # e2s PANEL ENTERO: flexion del cuello por capa (hs / ht) y tope de flexion bmx con el resto REMAPEADO (misma flexion)
    _b0 = P["bending"]; _bm = P["bend_max"]; _bn = max(P["bmx"], _bm); _W = np.zeros(NV); _vg = gar.vertex_groups["rigidez"]
    for _v in gar.data.vertices:
        for _g in _v.groups:
            if _g.group == _vg.index: _W[_v.index] = _g.weight
    _fx = _b0 + (_bm - _b0) * _W; _cue = np.array(sorted(set(D.get("rig_cuello", []))), int); _pcn = np.array([("ht" if n.startswith("ht") else ("hs" if n.startswith("hs") else "")) for n in SE.piece_of(D)[_cue]]) if len(_cue) else np.array([])
    if P["neck_hs"] >= 0: _fx[_cue[_pcn == "hs"]] = P["neck_hs"]
    if P["neck_ht"] >= 0: _fx[_cue[_pcn == "ht"]] = P["neck_ht"]
    _Wn = np.clip((_fx - _b0) / (_bn - _b0), 0.0, 1.0); _chg = np.where(np.abs(_Wn - _W) > 1e-9)[0]
    for _i in _chg: vrig.add([int(_i)], float(_Wn[_i]), 'REPLACE')
    P["bend_max"] = _bn
    log(f"PANEL ENTERO: tope de flexion {_bm} -> {_bn} ({len(_chg)} pesos remapeados) | cuello hs {P['neck_hs'] if P['neck_hs'] >= 0 else 'igual'} ({int((_pcn == 'hs').sum())} v) | cuello ht {P['neck_ht'] if P['neck_ht'] >= 0 else 'igual'} ({int((_pcn == 'ht').sum())} v) | "
        f"control: cierre {_b0 + (_bn - _b0) * _Wn[D['zipper'][0]]:.1f} tapeta {_b0 + (_bn - _b0) * _Wn[D['placket'][0]]:.1f} puno {_b0 + (_bn - _b0) * _Wn[D['cuff'][0]]:.1f} capucha {_b0 + (_bn - _b0) * _Wn[sorted(HOODSET)[0]]:.1f}")
if P["rig_tap"] > 0 and D.get("rig_cuello"):   # e2s: sin plancha en el margen de costura: la flexion del cuello (hs y ht) baja a la base junto a las costuras ht-hs
    # de la linea de menton (capucha-ht lado) y del borde CF del cuello (capucha-ht base); rampa lineal en rig_tap mm de molde. El escote (vista-escote) queda rigido.
    _vg = gar.vertex_groups["rigidez"]; _W = np.zeros(NV)
    for _v in gar.data.vertices:
        for _g in _v.groups:
            if _g.group == _vg.index: _W[_v.index] = _g.weight
    _S = np.array(D["sew"]); _N = np.array(D["sew_seam"]); _UVr = np.array(D["uv"], float); _pcr = SE.piece_of(D); _cue = np.array(sorted(set(D["rig_cuello"])), int); _nt = 0
    for s_ in "RL":
        _sv = set(_S[np.isin(_N, [f"capucha-ht lado {s_}", f"capucha-ht base {s_}"])].ravel().tolist())
        for pre in ("hs", "ht"):
            _ids = np.array([i for i in _cue if _pcr[i] == pre + s_]); _b = np.array(sorted(i for i in _sv if _pcr[i] == pre + s_))
            if not len(_ids) or not len(_b): continue
            _dm = np.min(np.linalg.norm(_UVr[_ids][:, None, :] - _UVr[_b][None, :, :], axis=2), axis=1); _f = np.clip(_dm / P["rig_tap"], 0.0, 1.0)
            for _i, _fi in zip(_ids, _f):
                if _fi < 1.0: vrig.add([int(_i)], float(_W[_i] * _fi), 'REPLACE'); _nt += 1
    log(f"RIGIDEZ cuello con rampa en las costuras lado/base: {_nt} vertices bajan (rampa {P['rig_tap']} mm)")
if SEPV: vrig.add(SEPV, 1.0, 'REPLACE'); log(f"broches con altura: flexion del separador {P['bend_max']} (peso 1) en {len(SEPV)} vertices")
if P["bi_w"] > 0 and P["bi_k"] != 1.0:   # [ESC·f535] BI: franja de flexion junto a la costura escote-cuello (ver cabecera); misma regla que _qc_BI/franja_BI.py
    _vg = gar.vertex_groups["rigidez"]; _W = np.zeros(NV)
    for _v in gar.data.vertices:
        for _g in _v.groups:
            if _g.group == _vg.index: _W[_v.index] = _g.weight
    _b0 = P["bending"]; _bm = P["bend_max"]; _fx = _b0 + (_bm - _b0) * _W
    _S = np.array(D["sew"]); _N = np.array(D["sew_seam"]); _UVr = np.array(D["uv"], float); _pcr = SE.piece_of(D)
    assert set(BI_COS) <= set(D["sew_seam"]), f"bi_cos: costura inexistente {set(BI_COS) - set(D['sew_seam'])}"
    _sv = np.unique(_S[np.isin(_N, BI_COS)].ravel())
    _av = set(D["zipper"]) | set(D["placket"]); _bi = []
    for _pn in sorted(set(_pcr[_sv])):   # piezas que tocan esas costuras
        _b = _sv[_pcr[_sv] == _pn]
        if not len(_b): continue
        _ids = np.arange(*D["groups"][_pn]); _dm = np.min(np.linalg.norm(_UVr[_ids][:, None, :] - _UVr[_b][None, :, :], axis=2), axis=1)
        _bi += [int(_i) for _i in _ids[_dm <= P["bi_w"]] if int(_i) not in _av]
    _bi = np.array(sorted(set(_bi)), int); _fx2 = _fx.copy(); _fx2[_bi] = _fx[_bi] * P["bi_k"]
    _bn = max(_bm, float(_fx2.max())); _Wn = np.clip((_fx2 - _b0) / (_bn - _b0), 0.0, 1.0); _chg = np.where(np.abs(_Wn - _W) > 1e-9)[0]
    for _i in _chg: vrig.add([int(_i)], float(_Wn[_i]), 'REPLACE')
    P["bend_max"] = _bn
    log(f"[ESC·f535] BI franja {BI_COS}: {len(_bi)} v a <= {P['bi_w']} mm, flexion x{P['bi_k']} (antes min/med/max {_fx[_bi].min():.1f}/{np.median(_fx[_bi]):.1f}/{_fx[_bi].max():.1f})"
        f" | tope {_bm} -> {_bn} ({len(_chg)} pesos remapeados) | control cierre {_b0 + (_bn - _b0) * _Wn[D['zipper'][0]]:.1f}")
if P["cc_w"] > 0 and P["cc_k"] != 1.0:   # [ESC·f535] CA: franja de flexion junto a las costuras hs-hc de la capucha (ver cabecera)
    _vg = gar.vertex_groups["rigidez"]; _W = np.zeros(NV)
    for _v in gar.data.vertices:
        for _g in _v.groups:
            if _g.group == _vg.index: _W[_v.index] = _g.weight
    _b0 = P["bending"]; _bm = P["bend_max"]; _fx = _b0 + (_bm - _b0) * _W
    _S = np.array(D["sew"]); _N = np.array(D["sew_seam"]); _UVr = np.array(D["uv"], float); _pcr = SE.piece_of(D)
    _sv = np.unique(_S[np.isin(_N, ["copa capucha R", "copa capucha L"])].ravel()); _cc = []; _fuera = 0
    for _pn in ("hsR", "hsL", "hc"):
        _b = _sv[_pcr[_sv] == _pn]
        if not len(_b): continue
        _ids = np.arange(*D["groups"][_pn]); _dm = np.min(np.linalg.norm(_UVr[_ids][:, None, :] - _UVr[_b][None, :, :], axis=2), axis=1)
        _sel = [int(_i) for _i in _ids[_dm <= P["cc_w"]]]; _cc += [_i for _i in _sel if _i in HOODSET]; _fuera += sum(1 for _i in _sel if _i not in HOODSET)
    _cc = np.array(sorted(set(_cc)), int); _fx2 = _fx.copy(); _fx2[_cc] = _fx[_cc] * P["cc_k"]
    _bn = max(_bm, float(_fx2.max())); _Wn = np.clip((_fx2 - _b0) / (_bn - _b0), 0.0, 1.0); _chg = np.where(np.abs(_Wn - _W) > 1e-9)[0]
    for _i in _chg: vrig.add([int(_i)], float(_Wn[_i]), 'REPLACE')
    P["bend_max"] = _bn; _ccs = set(_cc.tolist()); _ho = [i for i in sorted(HOODSET) if i not in _ccs][:1]
    log(f"[ESC·f535] CA franja copa capucha hs-hc: {len(_cc)} v a <= {P['cc_w']} mm ({_fuera} fuera de HOODSET), flexion x{P['cc_k']} (antes min/med/max {_fx[_cc].min():.1f}/{np.median(_fx[_cc]):.1f}/{_fx[_cc].max():.1f})"
        f" | tope {_bm} -> {_bn} ({len(_chg)} pesos remapeados) | control cierre {_b0 + (_bn - _b0) * _Wn[D['zipper'][0]]:.1f} capucha fuera de franja {_b0 + (_bn - _b0) * _Wn[_ho[0]]:.1f}")
log("bolsillos", len(names), "VT litros", np.round(VT * 1000, 2).tolist())
log("rigidez: cierre", len(D["zipper"]), "tapeta", len(D["placket"]), "puno", len(D["cuff"]), "cinta puno", len(BAND))

# e2b: capa interior ([x][x][x][x]) blanda a la compresion y embebido del pespunte (encoge la linea de acolchado: el valle entra)
vcas = gar.vertex_groups.new(name="cascara"); shell_ids = [i for n, (a, b) in D["groups"].items() if not n.endswith("_f") for i in range(a, b)]
vcas.add(shell_ids, 1.0, 'REPLACE')
if P["hood_soft"] > 0:   # e2h: capucha sin rigidez a la compresion en el plano (como la capa interior): la tela real pandea sin resistencia
    _hood = sorted(HOODSET); vcas.add(_hood, 0.0, 'REPLACE'); log("capucha: compresion blanda", P["soft"], "en", len(_hood), "vertices")
venc = gar.vertex_groups.new(name="encoge"); SMAX = max(P["S_body"], P["S_sl"], 1e-6)
pin_sl = [i for i in D["pinch"] if PK[i] is not None and PK[i].startswith("sl")]; pin_bd = [i for i in D["pinch"] if PK[i] is not None and not PK[i].startswith("sl")]
if P["S_cas"] > 0:   # [ESC·f535] (2026-10-10) transferencia del banco 4 (LEYES L4-1): exceso de cascara k = 1 + S_cas en los vertices CON bolsillo de las piezas con _f,
    #   fuera del pespunte (peso 0); todo lo demas k 1 (peso S_cas/(S_cas+SMAX)); pespuntes con el k de hoy. shrink_min = -S_cas. 0 = identico (copia _papelera/sim_e2s_pre_TF.py)
    _den = P["S_cas"] + SMAX; _pin = set(D["pinch"])
    _cas = [i for c_ in D["lining"] for i in range(*D["groups"][c_]) if PK[i] is not None and i not in _pin]
    venc.add(list(range(len(gar.data.vertices))), P["S_cas"] / _den, 'REPLACE'); venc.add(_cas, 0.0, 'REPLACE')
    venc.add(pin_bd, (P["S_cas"] + P["S_body"]) / _den, 'REPLACE'); venc.add(pin_sl, (P["S_cas"] + P["S_sl"]) / _den, 'REPLACE')
    log(f"[ESC·f535] EXCESO DE CASCARA S_cas {P['S_cas']}: {len(_cas)} v a k {1 + P['S_cas']:.3f} (peso 0) | resto k 1 (peso {P['S_cas'] / _den:.3f}) | pespunte cuerpo/manga peso {(P['S_cas'] + P['S_body']) / _den:.3f} / {(P['S_cas'] + P['S_sl']) / _den:.3f} | shrink_min {-P['S_cas']} max {SMAX}")
else:
    venc.add(pin_bd, P["S_body"] / SMAX, 'REPLACE'); venc.add(pin_sl, P["S_sl"] / SMAX, 'REPLACE')
log("capa interior blanda", P["soft"], "embebido pespunte cuerpo/manga", P["S_body"], P["S_sl"], "vertices", len(pin_bd), len(pin_sl))
# e2i (consulta A, paso 2): esfera colisionadora invisible que barre de delante de la coronilla a la espalda (sw_f0 -> sw_f1) y sale (-> sw_f2)
SWEEP = None
if P["sweep"] > 0:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=P["sw_r"], location=(0, -0.21, 1.92))
    SWEEP = bpy.context.active_object; SWEEP.name = "CD_barrido_esfera"
    for c in SWEEP.users_collection: c.objects.unlink(SWEEP)
    col.objects.link(SWEEP); collider(SWEEP, th=P["sw_th"])
    f0, f1, f2 = int(P["sw_f0"]), int(P["sw_f1"]), int(P["sw_f2"]); fa = f0 + round(0.28 * (f1 - f0)); fb = f0 + round(0.6 * (f1 - f0))
    KEYS = ((1, (0, -0.21, 1.92)), (f0, (0, -0.21, 1.92)), (fa, (0, -0.02, 1.90)), (fb, (0, 0.18, 1.74)), (f1, (0, 0.36, 1.50)), (f2, (0, 0.80, 1.75)))
    if P["sw_path"] == 2:   # CP11: por la linea media, de delante de la frente sobre la coronilla, atras y abajo por la nuca hasta la espalda alta,
        # y sale HACIA ATRAS en horizontal y despacio (la 1 salia hacia arriba a 7 cm/cuadro). Cuadros fijos 6-12-20-28-34-44.
        KEYS = ((1, (0, -0.25, 1.95)), (6, (0, -0.25, 1.95)), (12, (0, -0.05, 1.93)), (20, (0, 0.14, 1.84)), (28, (0, 0.30, 1.62)), (34, (0, 0.34, 1.50)), (44, (0, 0.75, 1.50)))
        P["sw_f0"], P["sw_f2"] = 6, 44
    for _f, _p in KEYS: SWEEP.location = _p; SWEEP.keyframe_insert("location", frame=_f)
    try:
        for fc in SWEEP.animation_data.action.fcurves:
            for k in fc.keyframe_points: k.interpolation = 'LINEAR'
    except Exception as e:   # Blender 5: acciones por capas/slots
        try:
            for lay in SWEEP.animation_data.action.layers:
                for stp in lay.strips:
                    for cb in stp.channelbags:
                        for fc in cb.fcurves:
                            for k in fc.keyframe_points: k.interpolation = 'LINEAR'
        except Exception as e2: log("barrido: interpolacion no lineal", e, e2)
    MANIQUI.append(SWEEP)
    _d0 = np.linalg.norm(V0 - np.array(KEYS[0][1]), axis=1)
    log("barrido: esfera r", P["sw_r"], "espesor", P["sw_th"], "keys", KEYS, "| arranque: vertices a < r+th+cd del centro:", int((_d0 < P["sw_r"] + P["sw_th"] + P["cd"]).sum()), "min", round(float(_d0.min() - P["sw_r"]) * 1000, 1), "mm de la superficie")
cm = gar.modifiers.new("cloth", 'CLOTH'); s = cm.settings
s.quality = int(P['quality']); s.mass = P['mass']; s.air_damping = P['air']
s.tension_stiffness = P['tension']; s.compression_stiffness = P['compression']; s.shear_stiffness = P['shear']; s.bending_stiffness = P['bending']
s.use_sewing_springs = True; s.sewing_force_max = P['sew_max']; s.use_dynamic_mesh = True
s.vertex_group_bending = "rigidez"; s.bending_stiffness_max = P["bend_max"]
if P["soft"] > 0:
    s.vertex_group_structural_stiffness = "cascara"; s.tension_stiffness_max = P["tension"]; s.compression_stiffness_max = P["compression"]
    s.compression_stiffness = P["soft"]
    if P["ent_c"] > P["compression"] and D.get("rig_cuello"):   # e2j: entretela = compresion ent_c en la franja del cuello; cascara sigue en compression
        _cue = sorted(set(D["rig_cuello"])); _ws = (P["compression"] - P["soft"]) / (P["ent_c"] - P["soft"])
        vcas.add(shell_ids, _ws, 'REPLACE')
        if P["hood_soft"] > 0: vcas.add(sorted(HOODSET), 0.0, 'REPLACE')
        vcas.add(_cue, 1.0, 'REPLACE'); s.compression_stiffness_max = P["ent_c"]
        log("entretela cuello: compresion", P["ent_c"], "en", len(_cue), "vertices (rig_cuello) | cascara peso", round(_ws, 4), "->", P["compression"], "| traccion", P["tension"], "igual | flexion sin tocar")
if P["soft"] > 0 and P.get("pl_hc", -1.0) > P["compression"] and P["ent_c"] <= P["compression"]:   # e2q PLANCHA: compresion de panel de la capucha
    assert P["hood_soft"] <= 0, "pl_hc requiere hood_soft=0"
    _ws = (P["compression"] - P["soft"]) / (P["pl_hc"] - P["soft"]); vcas.add(shell_ids, _ws, 'REPLACE'); vcas.add(sorted(HOODSET), 1.0, 'REPLACE')
    s.compression_stiffness_max = P["pl_hc"]
    log("PLANCHA capucha: compresion", P["pl_hc"], "en", len(HOODSET), "vertices | cascaras peso", round(_ws, 4), "->", P["compression"], "| capa interior", P["soft"], "| traccion", P["tension"], "igual")
if SEPV and P["soft"] > 0: vcas.add(SEPV, 1.0, 'REPLACE'); log(f"broches con altura: compresion del separador {s.compression_stiffness_max} (peso 1), traccion {s.tension_stiffness_max}")
if ESC_RIG:   # [ESC·f535] PQ: anillo del escote a flexion y compresion maximas (como la columna del cierre); va despues de todos los pesos de 'rigidez' y 'cascara'
    assert P["soft"] > 0, "esc rig requiere soft > 0 (cascara = grupo estructural)"
    def _wg(_g, _i):
        try: return float(_g.weight(_i))
        except RuntimeError: return 0.0
    if P["esc_r1"] > 0: ESC_W0 = {int(_i): (_wg(vrig, _i), _wg(vcas, _i)) for _i in ESC_RIG}   # [ESC·f535] MN: pesos originales para SOLTAR
    vrig.add(ESC_RIG, 1.0, 'REPLACE'); vcas.add(ESC_RIG, 1.0, 'REPLACE')
    log(f"[ESC·f535] ANILLO DEL ESCOTE (PQ): {len(ESC_RIG)} vertices a flexion {s.bending_stiffness_max} y compresion {s.compression_stiffness_max} (peso 1) | traccion {s.tension_stiffness_max}")
if PTV:   # [ESC·f535] PT: el margen hereda flexion, cascara y encoge de su vertice del cuello (despues de todos los pesos estaticos; antes del 1.er cuadro)
    _hw = {}
    for _g in (vrig, vcas, venc):
        _ws_ = []
        for _m, _a in zip(PTV, PT_PAR):
            try: _w = float(_g.weight(_a))
            except RuntimeError: _w = 0.0
            _g.add([_m], _w, 'REPLACE'); _ws_.append(_w)
        _hw[_g.name] = f"{min(_ws_):.3f}/{np.median(_ws_):.3f}/{max(_ws_):.3f}"
    log(f"[ESC·f535] PUENTE (PT): pesos heredados del cuello min/med/max {_hw} | flexion {s.bending_stiffness}->{s.bending_stiffness_max}")
s.shrink_min = -P["S_cas"] if P["S_cas"] > 0 else 0.0; s.shrink_max = SMAX; s.vertex_group_shrink = "encoge"   # [ESC·f535] S_cas
s.use_pressure = P["pres"] > 0; s.uniform_pressure_force = P["p0"]; s.pressure_factor = 1.0; s.vertex_group_pressure = "presion"
if PRAMP and s.use_pressure:   # e2zj: presion por OTRA VIA (sin tocar grupos): uniform_pressure_force animada = p0 x mediana(W control en f) / mediana(W control final)
    _cj = json.load(open(E2 + PRAMP))["ctrl"]; _mf = float(np.median(_cj[-1][2])); _ks = [(1, P["w0"] / _mf)] + [(int(c_[0]) + 1, float(np.median(c_[2])) / _mf) for c_ in _cj]
    for _f, _r in _ks: s.uniform_pressure_force = P["p0"] * _r; s.keyframe_insert("uniform_pressure_force", frame=_f)
    log("PRAMP (e2zj): uniform_pressure_force animada (cuadro, factor):", [(f_, round(r_, 3)) for f_, r_ in _ks])
PF = None
if PFIT and s.use_pressure:   # e2zl: presion global = trayectoria de la COMPLETA de referencia (rank-1 con w = WINI) + lazo opcional (ver cabecera)
    assert P["nrb"] > 0 and WINI and (P["pfb"] > 0 or not PRAMP), "pfit requiere nrb=1, wini= (y pfb > 0 si va con pramp)"
    _rj = json.load(open(E2 + PFIT)); assert list(_rj["names"]) == list(names), "pfit: otros bolsillos"
    _rf = np.array([c_[0] for c_ in _rj["ctrl"]], int); _rW = np.array([c_[2] for c_ in _rj["ctrl"]], float); _rR = np.array([float(np.median(c_[1])) for c_ in _rj["ctrl"]])
    _den = float((AREA * W * W).sum()); _g = (_rW * (AREA * W)[None, :]).sum(1) / _den; _g1 = float((AREA * P["w0"] * W).sum()) / _den
    _sm = int(P["pfb_sm"]); _rRs = np.array([_rR[max(0, i_ - _sm): i_ + _sm + 1].mean() for i_ in range(len(_rR))])
    _kk = [] if PRAMP else [(1, _g1)] + [(int(f_) + 1, float(g_)) for f_, g_ in zip(_rf, _g) if (P["pfb"] <= 0 or f_ + 1 <= P["pfb_f0"])]
    for _f, _r in _kk: s.uniform_pressure_force = P["p0"] * _r; s.keyframe_insert("uniform_pressure_force", frame=_f)   # con pramp: sus claves (BEZIER, = e2zk1) hasta pfb_f0
    _afc = []
    for _lay in gar.animation_data.action.layers:
        for _st in _lay.strips:
            for _cb in _st.channelbags: _afc += [fc for fc in _cb.fcurves if fc.data_path.endswith("uniform_pressure_force")]
    assert len(_afc) == 1, f"pfit: {len(_afc)} F-curves de uniform_pressure_force"
    if not PRAMP:
        for _kp in _afc[0].keyframe_points: _kp.interpolation = 'CONSTANT'
    PF = dict(f=_rf, g=_g, rr=_rR, rrs=_rRs, c=1.0, fc=_afc[0], log=[])
    log(f"PFIT (e2zl): referencia {PFIT} ({len(_rf)} controles f{_rf[0]}-f{_rf[-1]}) | w = WINI | g(f) rank-1 por area: f1 {_g1:.3f} " +
        " ".join(f"f{f_} {g_:.3f}" for f_, g_ in zip(_rf, _g) if f_ % 12 == 0 or f_ in (3, 6)) + (f" | claves previas {len(_kk)} (hasta f{_kk[-1][0]}) CONSTANT" if _kk else f" | claves previas = PRAMP {PRAMP} ({len(_afc[0].keyframe_points)}, sin tocar)")
        + (f" | LAZO pfb {P['pfb']} desde f{int(P['pfb_f0'])} clip {P['pfb_clip']} media movil {2 * _sm + 1} controles" if P["pfb"] > 0 else " | sin lazo"))
    log("PFIT evaluado en la F-curve (cuadro: factor):", " ".join(f"f{f_}:{_afc[0].evaluate(f_) / P['p0']:.3f}" for f_ in (1, 2, 3, 4, 5, 7, 10, 19, 28, 31, 40, 61, 100, 193)))
log("presion:", "PRENDIDA" if s.use_pressure else "APAGADA (use_pressure False)", "| p0", s.uniform_pressure_force, "| grupo", repr(s.vertex_group_pressure), "| factor", s.pressure_factor)
SAND_BM = None; SAND_W = None; SAND_RING = None
if P["sand"] > 0:   # e2s CUELLO SANDWICH (ver cabecera y sand_e2s.py)
    me.update(); _VNb = np.empty(NV * 3); me.vertices.foreach_get("normal", _VNb); _VNb = _VNb.reshape(-1, 3)
    _pairs = SE.predict(V0, F, _VNb, P["sand_len"] / 1000.0, check_normal=P["sand_nc"] > 0)
    _pc = SE.piece_of(D); SAND_W = SE.taper_w(D, P["sand_tap"]); _bad = set()
    _ancs = set(ANCV); _apairs = [(i_, j_) for i_, j_ in _pairs if i_ in _ancs or j_ in _ancs]   # [ESC·f535] PQ: los de las anclas van a la guardia ANC_PEND
    for i_, j_ in _pairs:
        if _ancs and (i_ in _ancs or j_ in _ancs): continue
        for x_, y_ in ((i_, j_), (j_, i_)):
            if _pc[x_].startswith("ht") and not (_pc[y_].startswith("hs") and _pc[y_][-1] == _pc[x_][-1]): _bad.add(x_)
    for i_ in _bad: SAND_W[i_] = 0.0
    vint = gar.vertex_groups.new(name="interno"); vint.add(list(range(NV)), 0.0, 'REPLACE')
    for i_, w_ in SAND_W.items(): vint.add([i_], float(w_), 'REPLACE')
    RELLENO_PEND = []
    if P["relleno"] > 0:   # RI: peso del relleno en el forro; guardia f1 = los pares que Blender detecta en 3D sobre el V0 contra avios (tp, zp, fa, bv, el, hs, hc) tendrian reposo de metros
        import mathutils as _mu
        # RIh2b (04:53) explotó en f2 (|d| p50 126 mm en TODAS las piezas): la guardia solo miraba piezas no-canal, pero en las costuras el forro de una pieza
        #   queda a < 14 mm del forro/cáscara de la VECINA (back_f–slR_f, fcR_f–fsR_f...): pares con reposo de metros y peso ½–1. Peligro = cualquier pieza
        #   que no sea la propia cáscara ni el propio forro (simétrico: también cubre el rayo que sale de la cáscara vecina y pega en este forro).
        _pc0 = np.empty(NV0, dtype=object)
        for p_, (a_, b_) in D["groups"].items(): _pc0[a_:b_] = p_
        _own = {}
        for _c, _fz in D["lining"].items(): _own[_fz] = {_c, _fz}
        _kd = _mu.kdtree.KDTree(NV0)
        for i in range(NV0): _kd.insert(V0[i].tolist(), i)
        _kd.balance(); _ok = []; _haz = collections.Counter()
        for i in RELLENO_F:
            _vec = [j_ for (_co, j_, _d) in _kd.find_range(V0[i].tolist(), P["relleno_g"] / 1000.0) if _pc0[j_] not in _own[_pc0[i]]]
            if _vec: RELLENO_PEND.append(i); _haz[_pc0[_vec[0]]] += 1
            else: _ok.append(i)
        if _ok: vint.add(_ok, float(P["relleno"]), 'REPLACE')
        log(f"RELLENO: peso {P['relleno']} en {len(_ok)} vertices del forro desde f1 | guardia (peso 0 hasta el primer set_weights del lazo): {len(RELLENO_PEND)} a < {P['relleno_g']} mm de otra pieza; por pieza vecina {dict(_haz.most_common(10))}")
    if ANCV:   # [ESC·f535] PQ: resortes internos ancla<->prenda que Blender crea en f1 (reposo de metros desde f2): el extremo de la prenda a peso 0 hasta el 1.er set_weights
        _ap = collections.Counter(); _nz = 0
        for i_, j_ in _apairs:
            k_ = j_ if i_ in _ancs else i_
            if k_ in _ancs or k_ in ANC_PEND or k_ in set(RELLENO_PEND): continue
            w_ = vint.weight(k_); _ap[_pc[k_]] += 1
            if w_ > 0: ANC_PEND[k_] = w_; vint.add([k_], 0.0, 'REPLACE'); _nz += 1
        _ns = np.array([np.linalg.norm(gar.data.vertices[a_].normal) for a_ in ANCV]); _nd = np.array([np.linalg.norm(np.array(gar.data.vertices[a_].normal) - V0[a_] / np.linalg.norm(V0[a_])) for a_ in ANCV])
        log(f"[ESC·f535] ANCLAS: {len(_apairs)} pares internos previstos en f1 con anclas, por pieza {dict(_ap)} | {_nz} a peso 0 hasta el 1.er set_weights | normal de ancla |n| {_ns.min():.3f}-{_ns.max():.3f}, dif. con posicion normalizada max {_nd.max():.3f}")
    s.use_internal_springs = True; s.internal_spring_max_length = P["sand_len"] / 1000.0; s.internal_spring_max_diversion = 0.0
    s.internal_spring_normal_check = P["sand_nc"] > 0; s.vertex_group_intern = "interno"
    s.internal_tension_stiffness = 0.0; s.internal_compression_stiffness = 0.0
    s.internal_tension_stiffness_max = P["sand_k"]; s.internal_compression_stiffness_max = P["sand_kc"]
    _R = np.array([kc.data[i].co[:] for i in range(NV)]); _ht = [(i_, j_) for i_, j_ in _pairs if _pc[i_].startswith("ht") or _pc[j_].startswith("ht")]
    _L3 = np.array([np.linalg.norm(V0[i_] - V0[j_]) for i_, j_ in _ht]) * 1000; _LR = np.array([np.linalg.norm(_R[i_] - _R[j_]) for i_, j_ in _ht]) * 1000
    _wt = np.array([0.5 * (SAND_W.get(i_, 0.0) + SAND_W.get(j_, 0.0)) for i_, j_ in _ht])
    _cnt = collections.Counter(tuple(sorted((_pc[i_], _pc[j_]))) for i_, j_ in _pairs)
    log(f"PRED resortes internos: {len(_pairs)} pares | por pieza: {_cnt.most_common(12)}")
    _hv = collections.Counter(x_ for i_, j_ in _ht for x_ in (i_, j_) if _pc[x_].startswith("ht") and SAND_W.get(x_, 0.0) > 0)
    _nht = sum(b_ - a_ for a_, b_ in (D["groups"]["htR"], D["groups"]["htL"])); _dpl = np.sqrt(np.maximum(_L3 ** 2 - 25.0, 0.0)) if len(_L3) else np.zeros(1)
    log(f"PRED cobertura: ht con >= 1 resorte con rigidez: {len(_hv)} de {_nht} (con 1: {sum(1 for v in _hv.values() if v == 1)}, 2: {sum(1 for v in _hv.values() if v == 2)}, 3+: {sum(1 for v in _hv.values() if v >= 3)}) | "
        f"desvio en el plano al arranque p50 {np.median(_dpl):.1f} p90 {np.percentile(_dpl, 90):.1f} mm")
    log(f"PRED con ht: {len(_ht)} (rigidez > 0: {int((_wt > 0).sum())}, peso medio {_wt[_wt > 0].mean():.2f}) | ht con resorte a otra pieza -> peso 0: {len(_bad)} | "
        f"largo 3D arranque p5/med/p95 {np.percentile(_L3[_wt > 0], [5, 50, 95]).round(1).tolist()} mm | reposo {np.percentile(_LR[_wt > 0], [5, 50, 95]).round(1).tolist()} mm | "
        f"reposo/3D med {np.median(_LR[_wt > 0] / np.maximum(_L3[_wt > 0], 1e-6)):.2f} p5 {np.percentile(_LR[_wt > 0] / np.maximum(_L3[_wt > 0], 1e-6), 5):.2f} p95 {np.percentile(_LR[_wt > 0] / np.maximum(_L3[_wt > 0], 1e-6), 95):.2f}")
    if SAND_Z or P["sand_rot"] >= 2:   # e2zs: lo que Blender va a re-detectar sobre el molde en cada reconstruccion del Cloth (misma logica que PRED)
        _prm = SE.predict(_R, F, SE.vnormals_np(_R, F), P["sand_len"] / 1000.0, check_normal=P["sand_nc"] > 0); _ms = []
        _stm = [(i_, j_) for i_, j_ in _prm if 0.5 * (SAND_W.get(i_, 0.0) + SAND_W.get(j_, 0.0)) > 0]
        _otr = collections.Counter(tuple(sorted((_pc[i_], _pc[j_]))) for i_, j_ in _stm if not ({_pc[i_][:2], _pc[j_][:2]} == {"hs", "ht"} and _pc[i_][-1] == _pc[j_][-1]))
        for s_ in "RL":
            _q = [(i_, j_) for i_, j_ in _stm if {_pc[i_], _pc[j_]} == {"hs" + s_, "ht" + s_}]; _lq = np.array([np.linalg.norm(_R[i_] - _R[j_]) for i_, j_ in _q]) * 1000 if _q else np.zeros(1)
            _n3 = sum(1 for (i_, j_), w_ in zip(_ht, _wt) if w_ > 0 and {_pc[i_], _pc[j_]} == {"hs" + s_, "ht" + s_}); _a, _b = D["groups"]["ht" + s_]
            _ms.append(f"{s_} {len(_q)} con rigidez (f1 3D: {_n3}), ht atados {len(set(x_ for p_ in _q for x_ in p_ if _pc[x_].startswith('ht')))} de {sum(1 for i_ in range(_a, _b) if SAND_W.get(i_, 0.0) > 0)} con peso, reposo p50 {np.median(_lq):.1f} mm, gemelas {int((_lq < P['sand_d'] + 0.2).sum())}")
        log("PRED RECONSTRUCCION (molde, e2zs): " + " | ".join(_ms) + (f" | OJO otros pares con rigidez: {dict(_otr)}" if _otr else " | sin otros pares con rigidez"))
    log("SANDWICH Blender:", "use_internal_springs", s.use_internal_springs, "max_length", round(s.internal_spring_max_length, 4), "diversion", s.internal_spring_max_diversion,
        "normal_check", s.internal_spring_normal_check, "grupo", repr(s.vertex_group_intern), "tension", s.internal_tension_stiffness, "->", s.internal_tension_stiffness_max,
        "compresion", s.internal_compression_stiffness, "->", s.internal_compression_stiffness_max)
    SAND_BM = SE.bary_map(D, SAND_T)
    _cc = np.array(D["sew"])[np.array(D["sew_seam"]) == "cuello-capucha"]; _bd = np.isin(_pc[_cc[:, 0]], ["back", "fcR", "fcL", "fsR", "fsL"]); SAND_RING = np.unique(np.where(_bd, _cc[:, 0], _cc[:, 1]))
def sand_log(X):   # e2s: espesor y deslizamiento del ht (peso 1) contra su punto del hs + ancho/fondo/CF del anillo del escote (como _qc_e2q/anillo_e2r.py)
    if SAND_BM is None: return ""
    st = SE.sand_stats(X, F, SAND_BM, SAND_W, 0.99); Pq = X[SAND_RING]; cf = Pq[np.argmin(np.abs(Pq[:, 0]) + 10 * (Pq[:, 1] > 0))]; cb = Pq[np.argmin(np.abs(Pq[:, 0]) + 10 * (Pq[:, 1] < 0))]
    return (f"SAND espesor med {st['esp_med']:.1f} p5 {st['esp_p5']:.1f} p95 {st['esp_p95']:.1f} | desliz med {st['desl_med']:.1f} p95 {st['desl_p95']:.1f} max {st['desl_max']:.1f} mm | "
            f"ANILLO ancho {(Pq[:, 0].max() - Pq[:, 0].min()) * 1000:.0f} fondo {(cb[1] - cf[1]) * 1000:.0f} mm CF y {cf[1]:+.3f} z {cf[2]:.3f}")
log("   arranque: " + sand_log(V0) if P["sand"] > 0 else "sin sandwich")
cs = cm.collision_settings; cs.collision_quality = 3; cs.distance_min = P["cd"]; cs.use_self_collision = False
if P["selfcol"] > 0 and D.get("autocol"):   # e2d: tapeta sobre el fcL sin atravesarlo (solo esas zonas; sin forro, sin bordes cosidos)
    # OJO: en Blender este grupo EXCLUYE (triangulos con todos sus vertices en el grupo no autocolisionan) -> se carga el complemento
    keep = set(D["autocol"])
    if P["selfarm"] > 0:   # e2g T2-A: colision manga-cuerpo (solo cascaras, a > 12 mm de los bordes): manga entera y costados del cuerpo bajo la axila
        UVs = np.array(D["uv"]); BRD = set(D["border"]); add = 0
        for n in ('slR', 'slL', 'back', 'fcR', 'fcL', 'fsR', 'fsL'):
            a_, b_ = D["groups"][n]; ids = np.arange(a_, b_); bd = np.array([i for i in ids if i in BRD])
            dmin = np.min(np.linalg.norm(UVs[ids][:, None, :] - UVs[bd][None, :, :], axis=2), axis=1)
            ok = dmin > P.get("sa_brd", 12.0)   # e2q: sa_brd = franja sin autocolision junto a los bordes (mm de molde; 12 = como e2g-e2p)
            if not n.startswith('sl'): ok &= (np.abs(V0[ids, 0]) > 0.13) & (V0[ids, 2] > 0.90) & (V0[ids, 2] < 1.36)
            keep |= set(ids[ok].tolist()); add += int(ok.sum())
        log("autocolision manga-cuerpo: +", add, "vertices | franja sin autocolision junto a los bordes", P.get("sa_brd", 12.0), "mm")
    if P["vcol"] > 0:   # e2h: la vista choca con la CASCARA (no con la capa interior: con la franja del fc en el grupo, chocarian cascara e interior)
        import mathutils.kdtree as _kdm
        class _KD:   # sin scipy en el Python de Blender: KDTree de mathutils (puntos 2D o 3D)
            def __init__(self, P):
                P = np.asarray(P, float); self.t = _kdm.KDTree(len(P))
                for i, p in enumerate(P): self.t.insert((p[0], p[1], p[2] if len(p) > 2 else 0.0), i)
                self.t.balance()
            def query(self, Q):
                Q = np.asarray(Q, float); return (np.array([self.t.find((q[0], q[1], q[2] if len(q) > 2 else 0.0))[2] for q in Q]),)
        UVs = np.array(D["uv"]); BRD = set(D["border"]); addv = 0; adds = 0; VIS = []
        for s_ in "RL":
            ins = D["inst"]["fa" + s_]; a_, b_ = D["groups"]["fa" + s_]; ids = np.arange(a_, b_); cs_ = ins["cs"]; per_ = ins["per"]; sB = np.array(ins["s"]); ob = ins["off"]
            sew_e = []
            for e in (0, 3, 4):   # bordes cosidos: CF, hombro, escote
                lo = cs_[e]; hi = cs_[(e + 1) % 5]; L_ = (hi - lo) % per_; rel = (sB - lo) % per_; sew_e += list(ob + np.where(rel <= L_ + 1e-6)[0])
            dmin = cKD = _KD(UVs[sew_e]).query(UVs[ids])[0]; okv = ids[dmin > 10.0]; keep |= set(okv.tolist()); addv += len(okv); VIS += list(ids)
        tr = _KD(V0[VIS])
        for n in ("fcR", "fsR", "fcL", "fsL"):
            a_, b_ = D["groups"][n]; ids = np.arange(a_, b_); bd = np.array([i for i in ids if i in BRD])
            dpat = np.min(np.linalg.norm(UVs[ids][:, None, :] - UVs[bd][None, :, :], axis=2), axis=1); d3 = tr.query(V0[ids])[0]
            ok = (dpat > 12.0) & (d3 < 0.025); keep |= set(ids[ok].tolist()); adds += int(ok.sum())
        log("autocolision vista-cascara: + vista", addv, "+ cascara fc/fs", adds, "vertices")
    if P["hcol"] > 0:   # e2i: la capucha se apoya en la espalda y los hombros sin atravesarlos (solo cascaras, a > 12 mm de los bordes)
        UVs = np.array(D["uv"]); addh = {}
        def _pborder(n):   # contorno de la pieza en la malla (aristas con una sola cara): D["border"] no trae la capucha (no tiene capa interior)
            a_, b_ = D["groups"][n]; fm = np.all((F >= a_) & (F < b_), axis=1); E_ = np.sort(np.concatenate([F[fm][:, [0, 1]], F[fm][:, [1, 2]], F[fm][:, [2, 0]]]), 1)
            u_, c_ = np.unique(E_, axis=0, return_counts=True); return np.unique(u_[c_ == 1])
        for n, zmin in (("hsR", 0), ("hsL", 0), ("hc", 0), ("back", 1.20), ("fsR", 1.35), ("fsL", 1.35)):
            a_, b_ = D["groups"][n]; ids = np.arange(a_, b_); bd = _pborder(n)
            dmin = np.min(np.linalg.norm(UVs[ids][:, None, :] - UVs[bd][None, :, :], axis=2), axis=1)
            ok = (dmin > 12.0) & (V0[ids, 2] > zmin)
            keep |= set(ids[ok].tolist()); addh[n] = int(ok.sum())
        log("autocolision capucha-espalda: +", addh, "total", sum(addh.values()))
    if FHV and P["hf_sc"] > 0:   # [ESC·f535] HQ: el forro de la capucha no atraviesa la cascara (ver _qc_HP/parcha_HQ.py)
        _UVq = np.array(D["uv"], float); _fsq = set(FHS) | set(FHV); _adq = {}
        for _nq in ("hsR", "hsL", "hc", "hcl", "hlR", "hlL"):
            _aq, _bq = D["groups"][_nq]; _fmq = np.all((F >= _aq) & (F < _bq), axis=1)
            _Eq = np.sort(np.concatenate([F[_fmq][:, [0, 1]], F[_fmq][:, [1, 2]], F[_fmq][:, [2, 0]]]), 1)
            _uq, _cq = np.unique(_Eq, axis=0, return_counts=True); _bdq = np.unique(_uq[_cq == 1]); _idq = np.array([i for i in range(_aq, _bq) if i in _fsq])
            _dq = np.array([np.min(np.linalg.norm(_UVq[_bdq] - _UVq[i], axis=1)) for i in _idq]); _okq = _idq[_dq > P["hf_sb"]]
            keep |= set(_okq.tolist()); _adq[_nq] = int(len(_okq))
        log(f"[ESC·f535] AUTOCOLISION FORRO-CASCARA CAPUCHA (HQ): + {_adq} vertices a > {P['hf_sb']} mm del contorno (molde) | total {sum(_adq.values())}")
    keep -= TPV
    if P["tp_nocol"] > 0:   # e2zc DIAGNOSTICO: la tapeta sin autocolision (sigue cosida y con broches) -> si la deriva del CF a L se va, la empuja el choque de la tp
        keep -= set(range(*D["groups"]["tp"])); log("tapeta SIN autocolision (diagnostico e2zc)")
    vac = gar.vertex_groups.new(name="sin_autocol"); vac.add([i for i in range(NV) if i not in keep], 1.0, 'REPLACE')
    cs.use_self_collision = True; cs.self_distance_min = P["self_d"]; cs.self_friction = P["sf"]; cs.vertex_group_self_collisions = "sin_autocol"
    log("autocolision", len(D["autocol"]), "vertices, distancia", P["self_d"])
if P["noobj_neck"] > 0 and D.get("rig_cuello"):   # e2s DIAGNOSTICO (no es construccion): el cuello (hs bajo la vista + ht) sin colision con el cuerpo
    vno = gar.vertex_groups.new(name="sin_colobj"); vno.add(sorted(set(D["rig_cuello"])), 1.0, 'REPLACE'); cs.vertex_group_object_collisions = "sin_colobj"
    log("DIAGNOSTICO: cuello sin colision con el cuerpo:", len(set(D["rig_cuello"])), "vertices | grupo", repr(cs.vertex_group_object_collisions))
if TPV:
    vpin = gar.vertex_groups.new(name="pin"); vpin.add(sorted(TPV), 1.0, 'REPLACE'); s.vertex_group_mass = "pin"; log("tapeta: pin en", len(TPV), "vertices")
if ANCV:   # [ESC·f535] PQ: solo las anclas van fijas (su objetivo = su posicion evaluada: Basis + clave anclas_cf)
    vpa = gar.vertex_groups.new(name="pin_anclas"); vpa.add(ANCV, 1.0, 'REPLACE'); s.vertex_group_mass = "pin_anclas"
    log("[ESC·f535] ANCLAS: pin en", len(ANCV), "vertices | grupo", repr(s.vertex_group_mass), "| rigidez del pin", s.pin_stiffness)
cm.point_cache.frame_start = 1; cm.point_cache.frame_end = NF
if SWEEP is not None:   # e2i: colision mas fina solo mientras la esfera se mueve (27-37 mm/cuadro)
    try:
        for _f, _c in ((1, 3), (int(P["sw_f0"]), 5), (int(P["sw_f2"]) + 3, 5), (int(P["sw_f2"]) + 4, 3)): cs.collision_quality = _c; cs.keyframe_insert("collision_quality", frame=_f)
        log("barrido: calidad de colision 5 entre f", int(P["sw_f0"]), "y f", int(P["sw_f2"]) + 3)
    except Exception as e: log("barrido: calidad de colision no animada", e)
if P["q_ramp"] > 0 and P["arm_end"] >= 0:   # e2g T2-A: calidad y colision mas finas solo en la ventana del movimiento
    try:
        for _f, _q, _c in ((1, int(P['quality']), 3), (int(P["arm_f0"]), int(P["q_ramp"]), 5), (int(P["arm_f1"]) + 6, int(P["q_ramp"]), 5), (int(P["arm_f1"]) + 12, int(P['quality']), 3)):
            s.quality = _q; s.keyframe_insert("quality", frame=_f); cs.collision_quality = _c; cs.keyframe_insert("collision_quality", frame=_f)
        log("calidad animada", int(P['quality']), "->", int(P["q_ramp"]), "en la rampa")
    except Exception as e: log("calidad animada: no se pudo", e)
# e2zz (2026-10-08, CP67): q_ini=<n> [q_ini_f=<F>, 12] -> MAS PASOS DEL SOLVER SOLO EN f1..F (golpe del reposo f1 -> f2: la axila pasa de area 0,58 a 1,0 del molde
#   en un cuadro y el pliegue queda dado vuelta). Medido (_qc_e2zz/t_quality.py, Blender 5.1): el Cloth fija dt = 1/quality al CREARSE; una clave de 'quality' sola
#   no cambia nada (bit a bit) y recien entra en la siguiente RECONSTRUCCION (aca el lazo de presion reescribe 'presion' cada K cuadros: f4, f7, f10, f13...).
#   Claves cuadro a cuadro, CONSTANT: n hasta F y el calendario que ya habia (evaluado ANTES de tocarlo, en float) desde F + 1. El log 'QINI' lee el dt REAL del
#   Cloth evaluado (ClothSimSettings + 32; layout validado con Cvi, gravedad y masa). q_ini=0 = identico (copia: _papelera/e2zz/sim_e2s_pre_e2zz.py).
QINI = None
if P["q_ini"] > 0:
    import ctypes as _ct
    def _qcurves():
        _o = []
        for _lay in gar.animation_data.action.layers:
            for _st in _lay.strips:
                for _cb in _st.channelbags: _o += [fc for fc in _cb.fcurves if fc.data_path.endswith(".settings.quality")]
        return _o
    if gar.animation_data is None or gar.animation_data.action is None or not _qcurves(): s.quality = int(P['quality']); s.keyframe_insert("quality", frame=1)
    _qfc = _qcurves(); assert len(_qfc) == 1, f"q_ini: {len(_qfc)} F-curves de quality"
    _qf = int(P["q_ini_f"]); _qb = {f_: float(_qfc[0].evaluate(f_)) for f_ in range(1, NF + 2)}
    for f_ in range(1, NF + 2): _qfc[0].keyframe_points.insert(f_, float(P["q_ini"]) if f_ <= _qf else _qb[f_])
    for _kp in _qfc[0].keyframe_points: _kp.interpolation = 'CONSTANT'
    _bad = [f_ for f_ in range(_qf + 1, NF + 2) if abs(_qfc[0].evaluate(f_) - _qb[f_]) > 1e-6]; assert not _bad, f"q_ini: el calendario viejo cambio en {_bad[:5]}"
    QINI = _qf; s.quality = int(P["q_ini"])
    log(f"q_ini: {int(P['q_ini'])} pasos del solver hasta f{_qf} | calendario viejo (float) f1 {_qb[1]:.2f} f4 {_qb[min(4, NF)]:.2f} f7 {_qb[min(7, NF)]:.2f} f10 {_qb[min(10, NF)]:.2f} "
        f"f{_qf + 1} {_qb[min(_qf + 1, NF)]:.2f} | nuevo f1 {_qfc[0].evaluate(1):.2f} f{_qf} {_qfc[0].evaluate(_qf):.2f} f{_qf + 1} {_qfc[0].evaluate(_qf + 1):.2f} | claves {len(_qfc[0].keyframe_points)}")
# e2zu2 (2026-10-05, CP58): FRICCION DEL CUERPO POR TIEMPO (ayuda de vestido). tfric_f=<F> tfric2=<v> [tfric_r=<R>, 6] -> los colisionadores que llevan tfric (el cuerpo sin la
#   cabeza) tienen tfric hasta el cuadro F, rampa lineal de R cuadros y tfric2 desde F+R (R <= 1 = escalon en F+1). Clave en CADA cuadro: el valor en cuadros enteros no depende de
#   la interpolacion (Blender 5.1: acciones por capas). La F-curve se evalua sobre la copia evaluada del colisionador (collision.cc lee collob->pd->pdef_cfrict): no hay edicion de
#   usuario a mitad de sim -> no reconstruye el Cloth (medido con la sonda: _qc_e2zu/prueba_tfric.out). El asentamiento cuenta desde el fin de la rampa.
#   tfric_f=0 = identico a antes (copia previa: _papelera/sim_e2s_pre_e2zu2.py).
TFK = None
if P["tfric_f"] > 0:
    TFOBJ = [_o for _o in TFOBJ if any(_m.type == 'COLLISION' for _m in _o.modifiers)]
    assert P["tfric"] >= 0 and P["tfric2"] >= 0 and TFOBJ, "tfric_f requiere tfric >= 0, tfric2 >= 0 y un colisionador con tfric"
    _tfF = int(P["tfric_f"]); _tfR = max(int(P["tfric_r"]), 1)
    TFK = [float(P["tfric"] + (P["tfric2"] - P["tfric"]) * min(max((_f - _tfF) / _tfR, 0.0), 1.0)) for _f in range(1, NF + 1)]
    for _o in TFOBJ:
        for _f in range(1, NF + 1): _o.collision.cloth_friction = TFK[_f - 1]; _o.collision.keyframe_insert("cloth_friction", frame=_f)
        _o.collision.cloth_friction = TFK[0]
    log(f"FRICCION POR TIEMPO (e2zu2): {[_o.name for _o in TFOBJ]} tfric {P['tfric']} hasta f{_tfF}, rampa de {_tfR} cuadros, {P['tfric2']} desde f{_tfF + _tfR} "
        f"(mu {0.01 * P['tfric']:.2f} -> {0.01 * P['tfric2']:.2f}) | claves f{_tfF}-f{_tfF + _tfR}: {[round(_v, 2) for _v in TFK[_tfF - 1:_tfF + _tfR]]}")
ew = s.effector_weights
for f, g in ((1, 0.0), (int(P["g0"]), 0.0), (int(P["g1"]), 1.0)): ew.gravity = g; ew.keyframe_insert("gravity", frame=f)
if P.get("tilt", 0) > 0:   # e2f capucha baja: gravedad inclinada hacia atras (+Y) al arranque = sacarse la capucha; vuelve a vertical
    th = math.radians(P["tilt"]); T1 = int(P.get("tiltf", 18)); gs = sc.gravity.length
    for f, v in ((1, (0, gs * math.sin(th), -gs * math.cos(th))), (T1, (0, gs * math.sin(th), -gs * math.cos(th))), (T1 + 12, (0, 0, -gs))):
        sc.gravity = v; sc.keyframe_insert("gravity", frame=f)
    log("gravedad inclinada", P["tilt"], "grados hacia atras hasta f", T1, "y vertical en f", T1 + 12)
SEW = np.array(D["sew"]); SEWN = D["sew_seam"]
FP = [np.where(face_pk == k)[0] for k in range(len(names))]
def coords():
    dg = bpy.context.evaluated_depsgraph_get(); ev = gar.evaluated_get(dg); m2 = ev.to_mesh()
    X = np.empty(len(m2.vertices) * 3); m2.vertices.foreach_get("co", X); ev.to_mesh_clear(); return X.reshape(-1, 3)
def volumes(X):
    out = np.zeros(len(names))
    for k, fi in enumerate(FP):
        T = X[F[fi]]; c = T.reshape(-1, 3).mean(0); T = T - c
        out[k] = np.einsum('ij,ij->i', T[:, 0], np.cross(T[:, 1], T[:, 2])).sum() / 6.0
    return out
# e2e2+: camino de carga del CF por cuadro (cfidx_e2e.py): pandeo del eje del cierre y la tapeta (largo / largo suavizado SG 101 mm, tramo
# interior), z de la esquina CF y del cuello CF, y R-L del ruedo por azimut (0 = CF, 90 = costado, 180 = CB).
import os
CFI = json.load(open(E2 + "cfidx_e2e3.json")) if os.path.exists(E2 + "cfidx_e2e3.json") else None
_xx = np.arange(-25, 26, dtype=float); SGC = np.linalg.pinv(np.stack([np.ones_like(_xx), _xx, _xx ** 2], 1))[0]
def _axis(X, B):
    B = np.array(B); ii = B[:, :3].astype(int); w = B[:, 3:]; return (X[ii] * w[:, :, None]).sum(1)
def _exc(P):
    S = np.stack([np.convolve(P[:, k], SGC[::-1], mode="valid") for k in range(3)], 1); R_ = P[25:-25]
    return 100.0 * (np.linalg.norm(np.diff(R_, axis=0), axis=1).sum() / np.linalg.norm(np.diff(S, axis=0), axis=1).sum() - 1.0)
def cf_metrics(X):
    H = X[CFI["hem"]] * 1000; az = np.degrees(np.arctan2(H[:, 0], -H[:, 1])); d = []
    for a0 in range(0, 180, 15):
        r_ = H[(az >= a0) & (az < a0 + 15), 2]; l_ = H[(az <= -a0) & (az > -a0 - 15), 2]
        if len(r_) and len(l_): d.append(np.median(r_) - np.median(l_))
    d = np.array(d); zc = X[CFI["cf_corner"], 2] * 1000; zn = X[CFI["cf_neck"], 2] * 1000; zb = np.median(H[np.abs(az) > 150, 2])
    return (f"CF: pandeo zp {_exc(_axis(X, CFI['zp'])):.1f}% tp {_exc(_axis(X, CFI['tp'])):.1f}% | esquina CF z {zc[0]:.0f}/{zc[1]:.0f} "
            f"cuello CF {zn[0]:.0f}/{zn[1]:.0f} ruedo CB {zb:.0f} mm | ruedo R-L max {np.abs(d).max():.0f} media {d.mean():.0f} mm (0-45: {d[:3].mean():.0f})")
def cf_nums(X):   # e2j: esquina CF (2), cuello CF (2), ruedo CB, en mm; e2k: + centro de la boca de la capucha (y, z)
    H = X[CFI["hem"]] * 1000; az = np.degrees(np.arctan2(H[:, 0], -H[:, 1]))
    bc = X[BOCA["path"]].mean(0) * 1000 if BOCA else np.zeros(3)
    return np.r_[X[CFI["cf_corner"], 2] * 1000, X[CFI["cf_neck"], 2] * 1000, np.median(H[np.abs(az) > 150, 2]), bc[1], bc[2]]
def boca_log(X):   # e2k: largo 3D del cordon (fila cosida) contra su reposo, costura de la boca, borde libre de la banda, centro de la boca
    if not BOCA: return ''
    def _L(ix): Q = X[ix]; return np.linalg.norm(np.diff(Q, axis=0), axis=1).sum() * 1000
    Lc = _L(BOCA["cord_row1"]) if CORD else 0.0; L0c = D["inst"]["cord"]["largo_tunel_mm"] if CORD else 1.0
    kv = 0.0
    try: kv = gar.data.shape_keys.key_blocks["cordon"].value
    except Exception: pass
    Lr = L0c * (1 - P["cinch"] * kv); bc = X[BOCA["path"]].mean(0) * 1000
    uniq = [g[0] for g in BOCA["grp"]]
    return (f"BOCA cordon 3D {Lc:.0f} / reposo {Lr:.0f} mm ({100 * (Lc / Lr - 1):+.1f} %) | costura boca {_L(uniq):.0f} (molde {BOCA['L_mm']:.0f}) | borde libre banda {_L(BOCA['hb_free']):.0f} (507,9) "
            f"| centro boca y {bc[1]:.0f} z {bc[2]:.0f} mm")
SET_F0 = int(P["arm_f1"]) if (P["arm_end"] >= 0 and P["arm_end"] != P["abd_end"]) else int(P["g1"])   # desde aca cuenta el asentamiento
if P["tfric_f"] > 0: SET_F0 = max(SET_F0, int(P["tfric_f"]) + max(int(P["tfric_r"]), 1)); log("asentamiento: cuenta desde f", SET_F0, "(fin de la rampa de friccion, e2zu2)")
SHIST = []; SETTLED = False
t0 = time.time(); CT = []; GHIST = {}; STOP = False
HP = np.array(sorted(HOODSET & set(i for n in ("hsR", "hsL", "hc") for i in range(*D["groups"][n]))))
ARMS = P["arm_end"] >= 0 and P["arm_end"] != P["abd_end"]
KEYSEAMS = ("costado R", "costado L", "bajo manga R", "bajo manga L", "sisa espalda R", "sisa frente R", "sisa espalda L", "sisa frente L", "elastico R", "elastico L")
def seam_max(X):
    L = np.linalg.norm(X[SEW[:, 0]] - X[SEW[:, 1]], axis=1) * 1000; GG = collections.defaultdict(float)
    for nm_, l_ in zip(SEWN, L): GG[nm_] = max(GG[nm_], l_)
    return GG
for f in range(1, NF + 1):
    sc.frame_set(f)
    if f in DUMPS: np.save(E2 + f"X_{TAG}_f{f}.npy", coords()[:NV0]); log("dump X cuadro", f)
    if PTV and f in DUMPS: np.save(E2 + f"XP_{TAG}_f{f}.npy", coords()[PTV[0]:PTV[-1] + 1])   # [ESC·f535] PT: el margen-puente aparte (X sigue con NV0 filas)
    if FHV and f in DUMPS: np.save(E2 + f"XF_{TAG}_f{f}.npy", coords()[FHV[0]:FHV[-1] + 1])   # [ESC·f535] HP: forro de capucha aparte
    if MNOBJ and f in (1, 2, int(P["mn_f0"]), int(P["mn_f0"]) + 1, int(0.5 * (P["mn_f0"] + P["mn_f1"])), int(P["mn_f1"])):
        log(f"   [ESC·f535] MENTON f{f} escala {[round(_o.scale[0], 3) for _o in MNOBJ]}")
    if P["esc_r1"] > 0 and P["esc_r0"] <= f < P["esc_r1"]:   # [ESC·f535] MN: SOLTAR en rampa (pesos para el paso f -> f+1; sueltas del todo en esc_r1)
        _t = min((f + 1 - P["esc_r0"]) / max(P["esc_r1"] - P["esc_r0"], 1.0), 1.0)
        for _i, (_wr, _wc) in ESC_W0.items(): vrig.add([_i], _wr + (1.0 - _wr) * (1.0 - _t), 'REPLACE'); vcas.add([_i], _wc + (1.0 - _wc) * (1.0 - _t), 'REPLACE')
        if ANCV: vpa.add(ANCV, 1.0 - _t, 'REPLACE')
        log(f"   [ESC·f535] SOLTAR f{f}: t {_t:.3f} | rigidez/cascara de {len(ESC_W0)} v hacia sus pesos originales | pin de {len(ANCV)} anclas {1.0 - _t:.3f}")
    if QINI is not None and (f <= QINI + 5 or f % 30 == 0 or f == NF):   # e2zz: pasos REALES del solver en este cuadro (solo lectura)
        _es = gar.evaluated_get(bpy.context.evaluated_depsgraph_get()).modifiers[cm.name].settings; _fl = (_ct.c_float * 8).from_address(_es.as_pointer() + 8)
        log(f"   QINI f{f} quality evaluada {_es.quality} | dt real {_fl[6]:.5f} = {1.0 / max(_fl[6], 1e-9):.1f} pasos | layout: Cvi {_fl[2]:.3f} g_z {_fl[5]:.3f} masa {_fl[7]:.4f}")
    if TFK is not None and (f <= 2 or f % 6 == 0 or f == NF or TFK[f - 1] != TFK[max(f - 2, 0)] or (f < NF and TFK[f] != TFK[f - 1])):   # e2zu2: friccion evaluada = clave
        _dg = bpy.context.evaluated_depsgraph_get(); _ev = [float(_o.evaluated_get(_dg).collision.cloth_friction) for _o in TFOBJ]
        log(f"   TFRIC f{f} clave {TFK[f - 1]:.3f} | evaluado {[round(_e, 3) for _e in _ev]}")
        assert max(abs(_e - TFK[f - 1]) for _e in _ev) < 1e-3, f"tfric evaluado {_ev} != clave {TFK[f - 1]} en f{f}"
    if f >= 2 and f % int(P["K"]) == 0:
        if P["uarm"] >= 0: MF[0] = 1.0 - (1.0 - P["uarm"]) * float(np.clip((f - P["arm_f0"]) / max(P["arm_f1"] - P["arm_f0"], 1), 0, 1))
        X = coords(); vol = volumes(X); tgt = VT * min(1.0, 0.15 + 0.85 * f / P["ramp"]) * (1.0 - FR * (1.0 - MF[0]))
        if len(HK_):   # e2zb cf_hold: reloj del objetivo corrido N para los retenidos; W congelado mientras la rampa no llega a 1
            fh = max(f - P["cf_hold"], 0.0); tgt[HK_] = VT[HK_] * min(1.0, 0.15 + 0.85 * fh / P["ramp"]); W0h = W[HK_].copy()
        W = np.clip(W * np.clip((tgt / np.maximum(vol, 1e-7)) ** 0.5, 0.8, 1.25), P["wmin"], P["wmax"])   # RI: piso wmin (0,01 = identico); RK: tope wmax (1,0 = identico)
        if P["wsym"] > 0:   # e2zb: mismo peso de presion en el canal R y su espejo L (mismo relleno inyectado por canal); 0 = identico
            for _k, _n in enumerate(names):
                if _n[2:3] == 'R' and _n.replace('R', 'L', 1) in idx: _j = idx[_n.replace('R', 'L', 1)]; W[_k] = W[_j] = 0.5 * (W[_k] + W[_j])
        if len(HK_):
            hf = float(np.clip((f - P["cf_hold"]) / max(P["cf_ramp"], 1.0), 0.0, 1.0))
            if hf < 1.0: W[HK_] = W0h
            HOLD[HK_] = hf
            if f % 6 == 0 or hf in (0.0, 1.0) and f - P["cf_hold"] in (0.0, P["cf_ramp"]): log(f"   CF_HOLD f{f} factor {hf:.2f} | W {np.round(W[HK_], 3).tolist()} | vol/obj {np.round(vol[HK_] / np.maximum(tgt[HK_], 1e-9), 2).tolist()}")
        if P["nrb"] <= 0: set_weights()   # e2zi: nrb=1 -> sin reescribir 'presion' (ver cabecera)
        r = vol / tgt; CT.append((f, np.round(r, 3).tolist(), np.round(W, 3).tolist()))
        if PF is not None:   # e2zl: lazo sobre la presion GLOBAL (clave directa en la F-curve: no reconstruye el Cloth)
            i_ = min(int(np.searchsorted(PF["f"], f)), len(PF["f"]) - 1); rm_ = float(np.median(r))
            pe_ = gar.evaluated_get(bpy.context.evaluated_depsgraph_get()).modifiers[cm.name].settings.uniform_pressure_force / P["p0"]   # ANTES de insertar (orden del banco)
            if P["pfb"] > 0 and f + 1 > P["pfb_f0"]:
                PF["c"] = float(np.clip(PF["c"] * np.clip((PF["rrs"][i_] / max(rm_, 1e-3)) ** P["pfb"], 1.0 - P["pfb_clip"], 1.0 + P["pfb_clip"]), 0.5, 2.0))
                kp_ = PF["fc"].keyframe_points.insert(f + 1, P["p0"] * float(PF["g"][i_]) * PF["c"]); kp_.interpolation = 'CONSTANT'
            PF["log"].append((f, round(rm_, 4), round(float(PF["rr"][i_]), 4), round(float(PF["g"][i_]), 4), round(PF["c"], 4), round(PF["fc"].evaluate(f + 1) / P["p0"], 4), round(pe_, 4)))
            if f % 6 == 0: log(f"   PFIT f{f} vol/obj med {rm_:.3f} ref {PF['rr'][i_]:.3f} (suav {PF['rrs'][i_]:.3f}) | g {PF['g'][i_]:.3f} c {PF['c']:.3f} -> factor f{f + 1} {PF['fc'].evaluate(f + 1) / P['p0']:.3f} | evaluado en f{f} {pe_:.3f}")
        if ARMS and f >= P["arm_f0"] and (f - int(P["arm_f0"])) % 15 == 0:   # e2i: un paso de 3 grados del brazo (0,2 grados/cuadro)
            GHIST[f] = seam_max(X); ang = P["abd_end"] + (P["arm_end"] - P["abd_end"]) * float(np.clip((f - P["arm_f0"]) / max(P["arm_f1"] - P["arm_f0"], 1), 0, 1))
            prev = GHIST.get(f - 15); dl = {k: round(GHIST[f][k] - prev[k], 1) for k in GHIST[f]} if prev else {}
            log(f"PASO f{f} brazo {ang:.1f} grados | " + " ".join(f"{k}:{GHIST[f][k]:.1f}" + (f"({dl[k]:+.1f})" if dl else "") for k in KEYSEAMS if k in GHIST[f]))
            if dl:
                worst = max(dl.items(), key=lambda kv: kv[1]); log(f"   peor apertura en 3 grados: {worst[0]} {worst[1]:+.1f} mm")
                if P["stop_open"] > 0 and worst[1] > P["stop_open"]: log(f"STOP: {worst[0]} abrio {worst[1]:+.1f} mm en 3 grados (> {P['stop_open']})"); STOP = True
        if f % 6 == 0:
            L = np.linalg.norm(X[SEW[:, 0]] - X[SEW[:, 1]], axis=1) * 1000
            log(f"f{f} t={time.time() - t0:.0f}s vol/obj min {r.min():.2f} med {np.median(r):.2f} max {r.max():.2f} | peso min {W.min():.2f} "
                f"med {np.median(W):.2f} max {W.max():.2f} n_sat {int((W >= 0.999).sum())} | costura media {L.mean():.1f} max {L.max():.0f} mm "
                f"z {X[:, 2].min():.3f}-{X[:, 2].max():.3f} finito {bool(np.isfinite(X).all())}")
            GG = collections.defaultdict(float)
            for (ia, ib), nm_, l_ in zip(SEW, SEWN, L): GG[nm_] = max(GG[nm_], l_)
            log("   por costura (max mm):", sorted(((round(v, 1), k) for k, v in GG.items()), reverse=True)[:6])
            if P["stop_f6"] > 0 and f <= 6 and L.max() > P["stop_f6"]:   # e2w5: guarda de arranque (e2w3/e2w4: cierre R 303/315 mm en f6 y 2 h perdidas)
                wk = max(GG.items(), key=lambda kv: kv[1]); log(f"STOP: f{f} costura {wk[0]} abierta {wk[1]:.0f} mm (> stop_f6 {P['stop_f6']:.0f}): arranque roto"); STOP = True
            if CFI: log("   " + cf_metrics(X))
            if CFI and f >= SET_F0:   # e2j: asentamiento (mm cada 6 cuadros)
                cn = cf_nums(X); SHIST.append((f, cn))
                if len(SHIST) > 1:
                    dd = cn - SHIST[-2][1]; dcf = float(np.abs(dd[:2]).max())
                    if P["settle_hood"] > 0 and BOCA: dcf = max(dcf, float(np.abs(dd[5:7]).max()))
                    log(f"   ASENT f{f} (+{f - SET_F0}) dz/6f esquina CF {dd[0]:+.1f}/{dd[1]:+.1f} cuello CF {dd[2]:+.1f}/{dd[3]:+.1f} ruedo CB {dd[4]:+.1f} mm | boca dy {dd[5]:+.1f} dz {dd[6]:+.1f} | esquina {cn[0]:.0f}")
                    SHIST[-1] = (f, cn, dcf)
                    if P["settle_min"] > 0 and f - SET_F0 >= P["settle_min"] and len(SHIST) > int(P["settle_n"]) and all(len(h) > 2 and h[2] < P["settle_tol"] for h in SHIST[-int(P["settle_n"]):]):
                        log(f"ESTABLE en f{f}: esquina CF < {P['settle_tol']} mm cada 6 cuadros en {int(P['settle_n'])} chequeos seguidos"); SETTLED = True
            HH = X[np.concatenate([np.arange(*D['groups'][n]) for n in ('hsR', 'hsL', 'hc')])]; log(f"   capucha: z {HH[:, 2].min():.3f}-{HH[:, 2].max():.3f} y max {HH[:, 1].max():.3f} | cabeza cubierta: {int(((HH[:, 2] > 1.72) & (np.abs(HH[:, 1] - 0.01) < 0.08)).sum())} vertices sobre la coronilla")
            if len(HP):   # e2i: capucha (sin cuello) apoyada: centroide y fraccion detras de la nuca (y > 0,10) y bajo z 1,62
                XH = X[HP]; log(f"   capucha sin cuello: centroide y {XH[:, 1].mean():.3f} z {XH[:, 2].mean():.3f} | z max {XH[:, 2].max():.3f} | detras de la nuca y bajo 1,62: {100.0 * np.mean((XH[:, 1] > 0.10) & (XH[:, 2] < 1.62)):.0f} %")
            if BOCA: log("   " + boca_log(X))
            if SAND_BM is not None: log("   " + sand_log(X))
            _z = X[np.arange(*D['groups']['zp'])]; _cs = {s_: X[np.array(D['sew'])[np.array(D['sew_seam']) == f'costado {s_}'].ravel()] for s_ in 'RL'}
            _cy = {s_: _c[(_c[:, 2] > 1.0) & (_c[:, 2] < 1.25), 1].mean() * 1000 for s_, _c in _cs.items()}
            log(f"   TORSION eje CF x pecho {_z[_z[:, 2] > 1.2, 0].mean() * 1000:+.0f} ruedo {_z[_z[:, 2] < 1.0, 0].mean() * 1000:+.0f} mm | costado y R {_cy['R']:+.0f} L {_cy['L']:+.0f}")
            _bk = X[np.arange(*D['groups']['back'])]; _xh = X[HP, 0].mean() * 1000 if len(HP) else 0.0
            log(f"   GIRO x prenda {X[:, 0].mean() * 1000:+.1f} | espalda ruedo x {_bk[_bk[:, 2] < 1.0, 0].mean() * 1000:+.1f} | cuello (zp z>1,40) x {_z[_z[:, 2] > 1.40, 0].mean() * 1000:+.1f} | capucha x {_xh:+.1f} mm")
            _pr = [(names[k], names[k].replace('R', 'L', 1)) for k in range(len(names)) if names[k][2:3] == 'R' and names[k].replace('R', 'L', 1) in names]
            _dw = sorted(((W[names.index(a_)] - W[names.index(b_)], a_[:2] + a_[3:]) for a_, b_ in _pr), key=lambda t: -abs(t[0]))[:4]
            _sR = sum(W[names.index(a_)] * AREA[names.index(a_)] for a_, b_ in _pr); _sL = sum(W[names.index(b_)] * AREA[names.index(b_)] for a_, b_ in _pr)
            log(f"   PRES R/L sum(W x area) {_sR * 1000:.1f}/{_sL * 1000:.1f} (x1000) | mayores dW R-L: " + " ".join(f"{nm_} {d_:+.2f}" for d_, nm_ in _dw))
            if SWEEP is not None: log(f"   esfera en {tuple(round(v, 3) for v in SWEEP.matrix_world.translation)}")
    if STOP: log("corrida cortada en f", f); break
    if SETTLED: log("asentamiento cumplido: fin en f", f); break
X = coords(); vol = volumes(X)
json.dump(dict(names=names, area_m2=AREA.tolist(), vt_m3=VT.tolist(), vol_m3=vol.tolist(), w=W.tolist(), ctrl=CT, **({"pfit": PF["log"], "pfit_cols": "f, vol/obj med, ref, g, c, factor f+1, factor evaluado en f"} if PF is not None else {})), open(E2 + f"bolsillos_{TAG}.json", "w"))
dg = bpy.context.evaluated_depsgraph_get(); ev = gar.evaluated_get(dg)
fin = bpy.data.meshes.new_from_object(ev); fo = bpy.data.objects.new("CD_campera_final", fin); col.objects.link(fo); fin.shade_smooth()
if SEPV or ANCV:   # e2zd: el separador del broche no va al objeto final (fuera del render); [ESC·f535] PQ: las anclas tampoco
    _bm = bmesh.new(); _bm.from_mesh(fin); _bm.verts.ensure_lookup_table(); bmesh.ops.delete(_bm, geom=[_bm.verts[i] for i in SEPV + ANCV], context='VERTS'); _bm.to_mesh(fin); _bm.free()
    log("broches con altura: separadores fuera del objeto final:", len(fin.vertices), "vertices (malla", NV0, ")")
G = collections.defaultdict(list)
for (a, b), nm in zip(D["sew"], SEWN): G[nm].append(1000 * float(np.linalg.norm(X[a] - X[b])))
rows = []
for nm, l in G.items():
    l = sorted(l); rows.append(f"{nm:34s} n {len(l):4d}  max {l[-1]:6.1f} mm  p95 {l[int(0.95 * (len(l) - 1))]:6.1f}  media {sum(l) / len(l):5.1f}")
open(E2 + f"costuras_gap_{TAG}.txt", "w", encoding="utf-8").write(chr(10).join(rows) + chr(10)); log(*rows, sep=chr(10))
if SEPV:   # e2zd: altura final de cada separador (apice a su base) y costuras del broche
    _hs = [float(np.dot(X[i0 + 3] - X[i0:i0 + 3].mean(0), np.cross(X[i0 + 1] - X[i0], X[i0 + 2] - X[i0]) / np.linalg.norm(np.cross(X[i0 + 1] - X[i0], X[i0 + 2] - X[i0])))) * 1000 for i0 in SEPV[::4]]
    log("broches con altura: altura final de los separadores (mm):", [round(abs(v), 1) for v in _hs])
json.dump(X[:NV0].tolist(), open(E2 + f"final_{TAG}.json", "w"))
log("t sim", round(time.time() - t0))
# ---- objeto final aplicado: sin cloth ni cache, sin shape keys; se borra la malla simulada
bpy.data.objects.remove(gar, do_unlink=True)
for o in MANIQUI: o.hide_render = True; o.hide_viewport = True
if P["renders"] > 0:
    sc.render.engine = 'BLENDER_WORKBENCH'; sh = sc.display.shading; sh.light = 'FLAT'; sh.color_type = 'SINGLE'; sh.single_color = (1, 1, 1)
    sc.render.film_transparent = True; sc.render.resolution_x = 1200; sc.render.resolution_y = 1200
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
    cam = bpy.data.cameras.new("CD_cam_orto"); cam.type = 'ORTHO'; co = bpy.data.objects.new("CD_cam_orto", cam); col.objects.link(co); sc.camera = co
    bb = np.array([fo.matrix_world @ mathutils.Vector(c) for c in fo.bound_box]); cx, cy, cz = (bb.min(0) + bb.max(0)) / 2
    cam.ortho_scale = float((bb.max(0) - bb.min(0)).max()) * 1.25
    for nm, loc, rot in (("frente", (cx, -3, cz), (90, 0, 0)), ("perfil", (3, cy, cz), (90, 0, 90)), ("espalda", (cx, 3, cz), (90, 0, 180))):
        co.location = loc; co.rotation_euler = tuple(math.radians(a) for a in rot)
        sc.render.filepath = E2 + f"sil_{nm}_{TAG}.png"; bpy.ops.render.render(write_still=True)
    log("ortho_scale", cam.ortho_scale, "bbox", np.round(bb.min(0), 3).tolist(), np.round(bb.max(0), 3).tolist())
    sh.light = 'STUDIO'; sh.single_color = (0.18, 0.36, 0.45); sc.render.film_transparent = False; sc.render.resolution_x = 900; sc.render.resolution_y = 900
    co.location = (cx + 2.1, cy - 2.1, cz + 0.2); co.rotation_euler = (math.radians(88), 0, math.radians(45))
    sc.render.filepath = E2 + f"vista_{TAG}.png"; bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=E2 + f"m133_{TAG}.blend")
log("fin", round(time.time() - t0))
