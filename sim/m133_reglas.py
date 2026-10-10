"""Reglas de la M133 (campera inflada con capucha, cuello sandwich, tapeta con broches): todo lo que nombra piezas.

GENERADO por tools/partir_sim.py desde sim/origen/sim_e2s.py (sha256 340a0129c64238e427ad53428dc00bea4dbe053d7de9668c54b64455ca74a1de): cada funcion es un bloque
del original, sin reescribir, que el nucleo llama con `_regla(ES, "nombre")`. Los datos que ya se pudieron sacar del codigo estan en
`m133_reglas.json`. Una prenda nueva escribe su propio `<id>_reglas.py` solo con lo que tenga (o ninguno).
"""
import bpy, bmesh, json, math, sys, time, mathutils, collections, os
import numpy as np


def filtrar_costuras_diagnostico(ES):
    """snaps=0 / notp: quita los broches o la tapeta (tp) de las costuras. (sim_e2s.py L120-L127)"""
    # e2k biseccion de la torsion: sin los 7 broches de la tapeta (la tapeta queda cosida solo al fcR/hsR)
    if ES.P['snaps'] == 0:
        _k = [i for i, nm in enumerate(ES.D['sew_seam']) if nm != 'broche']
        ES.log('broches: SIN broches (', len(ES.D['sew']) - len(_k), 'resortes fuera)')
        ES.D['sew'] = [ES.D['sew'][i] for i in _k]
        ES.D['sew_seam'] = [ES.D['sew_seam'][i] for i in _k]
    ES.TPV = set(range(*ES.D['groups']['tp'])) if ES.P['notp'] > 0 else set()
    # e2l DIAGNOSTICO (no es construccion): sin la tapeta -> se quitan sus resortes (costura tapeta y broches), queda fijada (pin) en el molde plano y sin autocolision
    if ES.TPV:
        _k = [i for i, (a_, b_) in enumerate(ES.D['sew']) if a_ not in ES.TPV and b_ not in ES.TPV]
        ES.log('tapeta FUERA (diagnostico):', len(ES.D['sew']) - len(_k), 'resortes quitados', sorted(set((ES.D['sew_seam'][i] for i in range(len(ES.D['sew'])) if i not in set(_k)))), '| fijada y sin autocolision')
        ES.D['sew'] = [ES.D['sew'][i] for i in _k]
        ES.D['sew_seam'] = [ES.D['sew_seam'][i] for i in _k]


def sandwich_rotar_caras(ES):
    """sand_rot: rota tri[0] de las caras del cuello (ht/hs) para que Blender ate gemelas. (sim_e2s.py L293-L305)"""
    # e2s: tri[0] de cada triangulo tocado = vertice mas cercano al impacto (Blender ata el rayo a tri[0])
    # e2zs: tri[0] por los impactos SOBRE EL MOLDE (lo que Blender re-detecta en cada reconstruccion del Cloth)
    if ES.P['sand'] > 0 and ES.P['sand_rot'] > 0:
        import m133_sandwich as _SE0
        _tm = bpy.data.meshes.new('_tmp_normales')
        _tm.from_pydata(ES.V0.tolist(), [], ES.D['f'])
        _tm.update()
        _vn = np.empty(ES.NV * 3)
        _tm.vertices.foreach_get('normal', _vn)
        _vn = _vn.reshape(-1, 3)
        bpy.data.meshes.remove(_tm)
        _hits = _SE0.predict_hits(ES.V0, ES.F, _vn, ES.P['sand_len'] / 1000.0, check_normal=ES.P['sand_nc'] > 0)
        ES.F, _nt, _nr = _SE0.rotate_for_ties(ES.D, ES.F, _hits)
        ES.D['f'] = ES.F.tolist()
        ES.log(f'SANDWICH rotacion: {_nt} triangulos tocados por rayos ht-hs, {_nr} rotados (la normal no cambia)')
        if ES.P['sand_rot'] >= 2:
            assert ES.P['sand_lvl'] > ES.P['sand_len'], 'sand_rot=2 requiere sand_lvl > sand_len (sandwich R en su nivel: deteccion sin copias coincidentes)'
            _M, _Z2 = _SE0.flat_rest(ES.D, ES.F, _SE0.transl(ES.D), ES.P['sand_d'], ES.P['sand_lvl'])
            _hm = _SE0.predict_hits(_M, ES.F, _SE0.vnormals_np(_M, ES.F), ES.P['sand_len'] / 1000.0, check_normal=ES.P['sand_nc'] > 0)
            ES.F, _nt2, _nr2 = _SE0.rotate_for_ties(ES.D, ES.F, _hm, V=_M)
            ES.D['f'] = ES.F.tolist()
            ES.log(f'SANDWICH rotacion por el MOLDE (e2zs): {_nt2} triangulos tocados por rayos ht-hs sobre el molde, {_nr2} rotados sobre la rotacion 3D')


def broches_con_altura(ES):
    """sep_h: separador rigido por broche de la tapeta (clave snap_sep de la malla). (sim_e2s.py L307-L330)"""
    # e2zd: broche con altura (ver cabecera)
    # e2zu (2026-10-05): sep_eps=<mm> -> la base del separador nace a sep_eps mm de la cara (hacia la tp), no COINCIDENTE con ella. Con base coincidente
    #   Blender puede crear un resorte interno vertice<->copia de largo 0 y reposo 0: fb(0/0) = NaN, el gradiente conjugado no itera y TODO el Cloth queda
    #   congelado hasta la proxima reconstruccion (m133_e2zt1.json: broches 1, 2 y 4; f2-f3 sin dinamica en las 6 sims e2zt). sep_eps=0 = identico.
    if ES.P['sep_h'] > 0 and ES.D.get('snap_sep') and (ES.P['snaps'] > 0) and (not ES.TPV):
        _kb = [i for i, nm in enumerate(ES.D['sew_seam']) if nm != 'broche']
        _nold = len(ES.D['sew']) - len(_kb)
        ES.D['sew'] = [ES.D['sew'][i] for i in _kb]
        ES.D['sew_seam'] = [ES.D['sew_seam'][i] for i in _kb]
        _h = ES.P['sep_h'] / 1000.0
        _UVa = np.array(ES.D['uv'], float)
        _nv = []
        _nuv = []
        _nf = []
        _msg = []
        for _it in ES.D['snap_sep']['items']:
            _t = _it['t']
            _fv = list(_it['face'])
            _bc = np.array(_it['bary'])
            _B = ES.V0[_fv]
            _n = np.cross(_B[1] - _B[0], _B[2] - _B[0])
            _n /= np.linalg.norm(_n)
            _sg = 1.0 if np.dot(_n, ES.V0[_t] - _bc @ _B) > 0 else -1.0
            _ap = _bc @ _B + _sg * _h * _n
            _R = np.c_[_UVa[_fv] / 1000.0, np.zeros(3)]
            _zr = np.sign(np.cross(_R[1] - _R[0], _R[2] - _R[0])[2])
            _apr = _bc @ _R + np.array([0.0, 0.0, _sg * _zr * _h])
            _i0 = ES.NV0 + len(_nv)
            b0, b1, b2, ap = (_i0, _i0 + 1, _i0 + 2, _i0 + 3)
            _Bs = _B + _sg * (ES.P['sep_eps'] / 1000.0) * _n
            _nv += [*_Bs.tolist(), _ap.tolist()]
            _nuv += [(_R[k][:2] * 1000.0).tolist() for k in range(3)] + [(_apr[:2] * 1000.0).tolist()]
            for k in range(3):
                ES.SEP_REST[_i0 + k] = tuple(_R[k])
            ES.SEP_REST[ap] = tuple(_apr)
            _nf += [[b0, b2, b1], [b0, b1, ap], [b1, b2, ap], [b2, b0, ap]] if _sg > 0 else [[b0, b1, b2], [b1, b0, ap], [b2, b1, ap], [b0, b2, ap]]
            ES.D['sew'] += [[b0, _fv[0]], [b1, _fv[1]], [b2, _fv[2]], [ap, _t]]
            ES.D['sew_seam'] += ['broche base'] * 3 + ['broche']
            _msg.append(f't{_t}: apice-t {np.linalg.norm(_ap - ES.V0[_t]) * 1000:.1f} mm')
        ES.SEPV = list(range(ES.NV0, ES.NV0 + len(_nv)))
        ES.V0 = np.vstack([ES.V0, np.array(_nv)])
        ES.D['v'] = ES.D['v'] + _nv
        ES.D['uv'] = ES.D['uv'] + _nuv
        ES.D['pocket'] = list(ES.D['pocket']) + [None] * len(_nv)
        ES.F = np.vstack([ES.F, np.array(_nf, int)])
        ES.D['f'] = ES.F.tolist()
        ES.D['groups']['snap_sep'] = [ES.NV0, ES.NV0 + len(_nv)]
        ES.NV = len(ES.V0)
        ES.log(f"BROCHES CON ALTURA (e2zd): {len(ES.D['snap_sep']['items'])} separadores de {ES.P['sep_h']} mm | base a {ES.P['sep_eps']} mm de la cara (e2zu; 0 = coincidente) | {_nold} resortes 'broche' viejos fuera | +{len(_nv)} vertices, +{len(_nf)} caras | " + ' '.join(_msg))


def sandwich_reposo(ES):
    """sand: reposo del ht superpuesto a su hs en el molde plano (niveles por lado). (sim_e2s.py L339-L359)"""
    pass
    pass
    import m133_sandwich as SE
    ES.SE = SE
    ES.SAND_T = ES.SE.transl(ES.D) if ES.P['sand'] > 0 else None
    # e2zs (ver cabecera)
    ES.SAND_Z = ES.SE.flat_levels(ES.D, ES.F, ES.P['sand_d'], ES.P['sand_lvl']) if ES.P['sand'] > 0 and ES.P['sand_lvl'] > 0 else None
    # e2s: reposo del ht superpuesto al hs (traslacion rigida del molde: no cambia su forma ni sus costuras)
    # control: sand_txy=0 sin trasladar en el plano; sand_zs = signo de z por lado (+1 = -d en los dos; -1 = L en +d)
    # e2zs: el hs de cada lado en su nivel (R sube sand_lvl)
    def _sand_co(i, u, w):
        for s_ in 'RL':
            a_, b_ = ES.D['groups']['ht' + s_]
            if a_ <= i < b_:
                t_ = ES.SAND_T[s_][0] * ES.P['sand_txy']
                z_ = ES.SAND_Z['ht' + s_] if ES.SAND_Z else -ES.P['sand_d'] * (1.0 if s_ == 'R' else ES.P['sand_zs'])
                return ((u - t_[0]) / 1000.0, (w - t_[1]) / 1000.0, z_ / 1000.0)
            if ES.SAND_Z:
                a_, b_ = ES.D['groups']['hs' + s_]
                if a_ <= i < b_:
                    return (u / 1000.0, w / 1000.0, ES.SAND_Z['hs' + s_] / 1000.0)
        return (u / 1000.0, w / 1000.0, 0.0)
    ES._sand_co = _sand_co
    if ES.P['sand'] > 0 and ES.P['sand_ov'] > 0:
        for s_ in 'RL':
            for g_ in ['ht' + s_] + (['hs' + s_] if ES.SAND_Z else []):
                a_, b_ = ES.D['groups'][g_]
                for i in range(a_, b_):
                    ES.kc.data[i].co = ES._sand_co(i, *ES.D['uv'][i])
        if ES.SAND_Z:
            ES.log('SANDWICH NIVELES (e2zs): z del molde (mm)', {k_: round(v_, 2) for k_, v_ in ES.SAND_Z.items() if not k_.startswith('n')}, '| normal del hs en el molde', {s_: ES.SAND_Z['n' + s_] for s_ in 'RL'})
        ES.log('SANDWICH: reposo del ht superpuesto al hs en el molde plano, T', {s_: (np.round(ES.SAND_T[s_][0], 2).tolist(), round(ES.SAND_T[s_][1], 2), ES.SAND_T[s_][3]) for s_ in 'RL'}, 'z', -ES.P['sand_d'], 'mm')


def cordon(ES):
    """cinch: tirado del cordon de la boca de la capucha (shape key 'cordon'). (sim_e2s.py L403-L412)"""
    ES.BOCA = ES.D.get('boca')
    ES.CORD = ES.D['groups'].get('cord')
    # e2k: tirado del cordon = reposo del tramo ojal-ojal x (1 - cinch), en rampa (el ancho de la cinta no cambia)
    if ES.BOCA and ES.CORD and (ES.P['cinch'] > 0):
        kq = ES.gar.shape_key_add(name='cordon', from_mix=False)
        kq.relative_key = ES.kc
        for i, (u, w) in enumerate(ES.D['uv']):
            kq.data[i].co = ES._sand_co(i, u, w) if ES.P['sand'] > 0 and ES.P['sand_ov'] > 0 else (u / 1000.0, w / 1000.0, 0.0)
        for i, co_ in ES.SEP_REST.items():
            kq.data[i].co = co_
        _c0 = ES.D['uv'][ES.CORD[0]][0]
        for i in range(*ES.CORD):
            u, w = ES.D['uv'][i]
            kq.data[i].co = ((_c0 + (u - _c0) * (1.0 - ES.P['cinch'])) / 1000.0, w / 1000.0, 0.0)
        for ES.f, v in ((1, 0.0), (int(ES.P['cz0']), 0.0), (int(ES.P['cz1']), 1.0)):
            kq.value = v
            kq.keyframe_insert('value', frame=ES.f)
        ES.log('cordon: tirado', ES.P['cinch'], '| reposo ojal-ojal', ES.D['inst']['cord']['largo_tunel_mm'], '->', round(ES.D['inst']['cord']['largo_tunel_mm'] * (1 - ES.P['cinch']), 1), 'mm entre f', int(ES.P['cz0']), 'y f', int(ES.P['cz1']))


def franja_axila(ES):
    """uarm: franja bajo la axila en cuerpo (back/fc/fs) y manga (sl). (sim_e2s.py L436-L446)"""
    if ES.P['uarm'] >= 0:
        _body = [n for n in ES.D['groups'] if n.split('_')[0] in ('back', 'fcR', 'fcL', 'fsR', 'fsL')]
        _sl = [n for n in ES.D['groups'] if n.split('_')[0] in ('slR', 'slL')]
        for n in _body:
            a_, b_ = ES.D['groups'][n]
            ids = np.arange(a_, b_)
            m = (ES.V0[ids, 2] > ES.P['z_ax'] - ES.P['uarm_band']) & (ES.V0[ids, 2] < ES.P['z_ax']) & (np.abs(ES.V0[ids, 0]) > 0.12)
            ES.UA_IDS |= set(ids[m].tolist())
        for n in _sl:
            a_, b_ = ES.D['groups'][n]
            ids = np.arange(a_, b_)
            sgx = 1.0 if n.startswith('slR') else -1.0
            ax = ES.V0[ids].mean(0)
            m = (ES.V0[ids, 2] > ES.P['z_ax'] - 0.25) & ((ES.V0[ids, 0] - ax[0]) * sgx < 0)
            ES.UA_IDS |= set(ids[m].tolist())
        for k, ids in ES.vpk.items():
            ES.FR[k] = np.mean([i in ES.UA_IDS for i in ids]) if ids else 0.0
        ES.log('franja bajo la axila:', len(ES.UA_IDS), 'vertices; fraccion por bolsillo >0:', {ES.names[k]: round(float(ES.FR[k]), 2) for k in range(len(ES.names)) if ES.FR[k] > 0})


def retener_bolsillos_cf(ES):
    """cf_hold: bolsillos del fc bajo la tapeta sin presion al arranque. (sim_e2s.py L448-L451)"""
    if ES.P['cf_hold'] > 0:
        _sides = {0: 'RL', 1: 'L', 2: 'R'}[int(ES.P['cf_lr'])]
        ES.HK_ = [ES.idx[f'fc{s_}{c}'] for s_ in _sides for c in str(int(ES.P['cf_ch'])) if f'fc{s_}{c}' in ES.idx]
        ES.HOLD[ES.HK_] = 0.0
        ES.log('CF_HOLD: bolsillos', [ES.names[k] for k in ES.HK_], 'sin presion hasta f', int(ES.P['cf_hold']), '+ rampa', int(ES.P['cf_ramp']), 'cuadros |', sum((len(ES.vpk[k]) for k in ES.HK_ if k in ES.vpk)), 'vertices')


def zona_capucha(ES):
    """HOODSET: que vertices son capucha (hs/hc/hb/cord, con o sin cuello). (sim_e2s.py L472-L478)"""
    # e2i: que es "capucha" para hood_bend/hood_soft. hood_scope=1: hs fuera de la huella del ht + hc (el cuello chimenea = hs bajo el ht + ht,
    # que en la real lleva cascara + guata + vista, queda con la rigidez del cuerpo); hood_scope=0: hs + hc + ht (como e2h4/e2h6)
    _ALLH = set((i for n in ('hsR', 'hsL', 'hc', 'htR', 'htL', 'hb', 'cord') if n in ES.D['groups'] for i in range(*ES.D['groups'][n])))
    if ES.P['hood_scope'] > 0 and ES.D.get('rig_cuello'):
        _cue = set(ES.D['rig_cuello'])
        ES.HOODSET = set((i for n in ('hsR', 'hsL', 'hc', 'hb', 'cord') if n in ES.D['groups'] for i in range(*ES.D['groups'][n]))) - _cue - set(ES.D['zipper']) - set(ES.D['placket'])
        ES.log('capucha (hood_scope=1): ', len(ES.HOODSET), 'vertices sin el cuello (', len(_ALLH & _cue), 'de cuello quedan como el cuerpo)')
    else:
        ES.HOODSET = _ALLH


def cuello_flexion_por_capa(ES):
    """bmx / neck_hs / neck_ht: flexion del cuello por capa. (sim_e2s.py L495-L507)"""
    # e2s PANEL ENTERO: flexion del cuello por capa (hs / ht) y tope de flexion bmx con el resto REMAPEADO (misma flexion)
    if ES.P['bmx'] > 0 or ES.P['neck_hs'] >= 0 or ES.P['neck_ht'] >= 0:
        _b0 = ES.P['bending']
        _bm = ES.P['bend_max']
        _bn = max(ES.P['bmx'], _bm)
        _W = np.zeros(ES.NV)
        _vg = ES.gar.vertex_groups['rigidez']
        for _v in ES.gar.data.vertices:
            for _g in _v.groups:
                if _g.group == _vg.index:
                    _W[_v.index] = _g.weight
        _fx = _b0 + (_bm - _b0) * _W
        _cue = np.array(sorted(set(ES.D.get('rig_cuello', []))), int)
        _pcn = np.array(['ht' if n.startswith('ht') else 'hs' if n.startswith('hs') else '' for n in ES.SE.piece_of(ES.D)[_cue]]) if len(_cue) else np.array([])
        if ES.P['neck_hs'] >= 0:
            _fx[_cue[_pcn == 'hs']] = ES.P['neck_hs']
        if ES.P['neck_ht'] >= 0:
            _fx[_cue[_pcn == 'ht']] = ES.P['neck_ht']
        _Wn = np.clip((_fx - _b0) / (_bn - _b0), 0.0, 1.0)
        _chg = np.where(np.abs(_Wn - _W) > 1e-09)[0]
        for _i in _chg:
            ES.vrig.add([int(_i)], float(_Wn[_i]), 'REPLACE')
        ES.P['bend_max'] = _bn
        ES.log(f"PANEL ENTERO: tope de flexion {_bm} -> {_bn} ({len(_chg)} pesos remapeados) | cuello hs {(ES.P['neck_hs'] if ES.P['neck_hs'] >= 0 else 'igual')} ({int((_pcn == 'hs').sum())} v) | cuello ht {(ES.P['neck_ht'] if ES.P['neck_ht'] >= 0 else 'igual')} ({int((_pcn == 'ht').sum())} v) | control: cierre {_b0 + (_bn - _b0) * _Wn[ES.D['zipper'][0]]:.1f} tapeta {_b0 + (_bn - _b0) * _Wn[ES.D['placket'][0]]:.1f} puno {_b0 + (_bn - _b0) * _Wn[ES.D['cuff'][0]]:.1f} capucha {_b0 + (_bn - _b0) * _Wn[sorted(ES.HOODSET)[0]]:.1f}")


def cuello_rampa_costuras(ES):
    """rig_tap: la flexion del cuello baja junto a las costuras capucha-ht. (sim_e2s.py L508-L523)"""
    # e2s: sin plancha en el margen de costura: la flexion del cuello (hs y ht) baja a la base junto a las costuras ht-hs
    # de la linea de menton (capucha-ht lado) y del borde CF del cuello (capucha-ht base); rampa lineal en rig_tap mm de molde. El escote (vista-escote) queda rigido.
    if ES.P['rig_tap'] > 0 and ES.D.get('rig_cuello'):
        _vg = ES.gar.vertex_groups['rigidez']
        _W = np.zeros(ES.NV)
        for _v in ES.gar.data.vertices:
            for _g in _v.groups:
                if _g.group == _vg.index:
                    _W[_v.index] = _g.weight
        _S = np.array(ES.D['sew'])
        _N = np.array(ES.D['sew_seam'])
        _UVr = np.array(ES.D['uv'], float)
        _pcr = ES.SE.piece_of(ES.D)
        _cue = np.array(sorted(set(ES.D['rig_cuello'])), int)
        _nt = 0
        for s_ in 'RL':
            _sv = set(_S[np.isin(_N, [f'capucha-ht lado {s_}', f'capucha-ht base {s_}'])].ravel().tolist())
            for pre in ('hs', 'ht'):
                _ids = np.array([i for i in _cue if _pcr[i] == pre + s_])
                _b = np.array(sorted((i for i in _sv if _pcr[i] == pre + s_)))
                if not len(_ids) or not len(_b):
                    continue
                _dm = np.min(np.linalg.norm(_UVr[_ids][:, None, :] - _UVr[_b][None, :, :], axis=2), axis=1)
                _f = np.clip(_dm / ES.P['rig_tap'], 0.0, 1.0)
                for _i, _fi in zip(_ids, _f):
                    if _fi < 1.0:
                        ES.vrig.add([int(_i)], float(_W[_i] * _fi), 'REPLACE')
                        _nt += 1
        ES.log(f"RIGIDEZ cuello con rampa en las costuras lado/base: {_nt} vertices bajan (rampa {ES.P['rig_tap']} mm)")


def sandwich_resortes_internos(ES):
    """sand: resortes internos ht-hs, pesos, PRED y sand_log(). (sim_e2s.py L613-L659)"""
    ES.SAND_BM = None
    SAND_W = None
    SAND_RING = None
    # e2s CUELLO SANDWICH (ver cabecera y sand_e2s.py)
    # e2zs: lo que Blender va a re-detectar sobre el molde en cada reconstruccion del Cloth (misma logica que PRED)
    if ES.P['sand'] > 0:
        ES.me.update()
        _VNb = np.empty(ES.NV * 3)
        ES.me.vertices.foreach_get('normal', _VNb)
        _VNb = _VNb.reshape(-1, 3)
        _pairs = ES.SE.predict(ES.V0, ES.F, _VNb, ES.P['sand_len'] / 1000.0, check_normal=ES.P['sand_nc'] > 0)
        _pc = ES.SE.piece_of(ES.D)
        SAND_W = ES.SE.taper_w(ES.D, ES.P['sand_tap'])
        _bad = set()
        for i_, j_ in _pairs:
            for x_, y_ in ((i_, j_), (j_, i_)):
                if _pc[x_].startswith('ht') and (not (_pc[y_].startswith('hs') and _pc[y_][-1] == _pc[x_][-1])):
                    _bad.add(x_)
        for i_ in _bad:
            SAND_W[i_] = 0.0
        vint = ES.gar.vertex_groups.new(name='interno')
        vint.add(list(range(ES.NV)), 0.0, 'REPLACE')
        for i_, w_ in SAND_W.items():
            vint.add([i_], float(w_), 'REPLACE')
        ES.s.use_internal_springs = True
        ES.s.internal_spring_max_length = ES.P['sand_len'] / 1000.0
        ES.s.internal_spring_max_diversion = 0.0
        ES.s.internal_spring_normal_check = ES.P['sand_nc'] > 0
        ES.s.vertex_group_intern = 'interno'
        ES.s.internal_tension_stiffness = 0.0
        ES.s.internal_compression_stiffness = 0.0
        ES.s.internal_tension_stiffness_max = ES.P['sand_k']
        ES.s.internal_compression_stiffness_max = ES.P['sand_kc']
        _R = np.array([ES.kc.data[i].co[:] for i in range(ES.NV)])
        _ht = [(i_, j_) for i_, j_ in _pairs if _pc[i_].startswith('ht') or _pc[j_].startswith('ht')]
        _L3 = np.array([np.linalg.norm(ES.V0[i_] - ES.V0[j_]) for i_, j_ in _ht]) * 1000
        _LR = np.array([np.linalg.norm(_R[i_] - _R[j_]) for i_, j_ in _ht]) * 1000
        _wt = np.array([0.5 * (SAND_W.get(i_, 0.0) + SAND_W.get(j_, 0.0)) for i_, j_ in _ht])
        _cnt = collections.Counter((tuple(sorted((_pc[i_], _pc[j_]))) for i_, j_ in _pairs))
        ES.log(f'PRED resortes internos: {len(_pairs)} pares | por pieza: {_cnt.most_common(12)}')
        _hv = collections.Counter((x_ for i_, j_ in _ht for x_ in (i_, j_) if _pc[x_].startswith('ht') and SAND_W.get(x_, 0.0) > 0))
        _nht = sum((b_ - a_ for a_, b_ in (ES.D['groups']['htR'], ES.D['groups']['htL'])))
        _dpl = np.sqrt(np.maximum(_L3 ** 2 - 25.0, 0.0)) if len(_L3) else np.zeros(1)
        ES.log(f'PRED cobertura: ht con >= 1 resorte con rigidez: {len(_hv)} de {_nht} (con 1: {sum((1 for v in _hv.values() if v == 1))}, 2: {sum((1 for v in _hv.values() if v == 2))}, 3+: {sum((1 for v in _hv.values() if v >= 3))}) | desvio en el plano al arranque p50 {np.median(_dpl):.1f} p90 {np.percentile(_dpl, 90):.1f} mm')
        ES.log(f'PRED con ht: {len(_ht)} (rigidez > 0: {int((_wt > 0).sum())}, peso medio {_wt[_wt > 0].mean():.2f}) | ht con resorte a otra pieza -> peso 0: {len(_bad)} | largo 3D arranque p5/med/p95 {np.percentile(_L3[_wt > 0], [5, 50, 95]).round(1).tolist()} mm | reposo {np.percentile(_LR[_wt > 0], [5, 50, 95]).round(1).tolist()} mm | reposo/3D med {np.median(_LR[_wt > 0] / np.maximum(_L3[_wt > 0], 1e-06)):.2f} p5 {np.percentile(_LR[_wt > 0] / np.maximum(_L3[_wt > 0], 1e-06), 5):.2f} p95 {np.percentile(_LR[_wt > 0] / np.maximum(_L3[_wt > 0], 1e-06), 95):.2f}')
        if ES.SAND_Z or ES.P['sand_rot'] >= 2:
            _prm = ES.SE.predict(_R, ES.F, ES.SE.vnormals_np(_R, ES.F), ES.P['sand_len'] / 1000.0, check_normal=ES.P['sand_nc'] > 0)
            _ms = []
            _stm = [(i_, j_) for i_, j_ in _prm if 0.5 * (SAND_W.get(i_, 0.0) + SAND_W.get(j_, 0.0)) > 0]
            _otr = collections.Counter((tuple(sorted((_pc[i_], _pc[j_]))) for i_, j_ in _stm if not ({_pc[i_][:2], _pc[j_][:2]} == {'hs', 'ht'} and _pc[i_][-1] == _pc[j_][-1])))
            for s_ in 'RL':
                _q = [(i_, j_) for i_, j_ in _stm if {_pc[i_], _pc[j_]} == {'hs' + s_, 'ht' + s_}]
                _lq = np.array([np.linalg.norm(_R[i_] - _R[j_]) for i_, j_ in _q]) * 1000 if _q else np.zeros(1)
                _n3 = sum((1 for (i_, j_), w_ in zip(_ht, _wt) if w_ > 0 and {_pc[i_], _pc[j_]} == {'hs' + s_, 'ht' + s_}))
                _a, _b = ES.D['groups']['ht' + s_]
                _ms.append(f"{s_} {len(_q)} con rigidez (f1 3D: {_n3}), ht atados {len(set((x_ for p_ in _q for x_ in p_ if _pc[x_].startswith('ht'))))} de {sum((1 for i_ in range(_a, _b) if SAND_W.get(i_, 0.0) > 0))} con peso, reposo p50 {np.median(_lq):.1f} mm, gemelas {int((_lq < ES.P['sand_d'] + 0.2).sum())}")
            ES.log('PRED RECONSTRUCCION (molde, e2zs): ' + ' | '.join(_ms) + (f' | OJO otros pares con rigidez: {dict(_otr)}' if _otr else ' | sin otros pares con rigidez'))
        ES.log('SANDWICH Blender:', 'use_internal_springs', ES.s.use_internal_springs, 'max_length', round(ES.s.internal_spring_max_length, 4), 'diversion', ES.s.internal_spring_max_diversion, 'normal_check', ES.s.internal_spring_normal_check, 'grupo', repr(ES.s.vertex_group_intern), 'tension', ES.s.internal_tension_stiffness, '->', ES.s.internal_tension_stiffness_max, 'compresion', ES.s.internal_compression_stiffness, '->', ES.s.internal_compression_stiffness_max)
        ES.SAND_BM = ES.SE.bary_map(ES.D, ES.SAND_T)
        _cc = np.array(ES.D['sew'])[np.array(ES.D['sew_seam']) == 'cuello-capucha']
        _bd = np.isin(_pc[_cc[:, 0]], ['back', 'fcR', 'fcL', 'fsR', 'fsL'])
        SAND_RING = np.unique(np.where(_bd, _cc[:, 0], _cc[:, 1]))
    # e2s: espesor y deslizamiento del ht (peso 1) contra su punto del hs + ancho/fondo/CF del anillo del escote (como _qc_e2q/anillo_e2r.py)
    def sand_log(X):
        if ES.SAND_BM is None:
            return ''
        st = ES.SE.sand_stats(X, ES.F, ES.SAND_BM, SAND_W, 0.99)
        Pq = X[SAND_RING]
        cf = Pq[np.argmin(np.abs(Pq[:, 0]) + 10 * (Pq[:, 1] > 0))]
        cb = Pq[np.argmin(np.abs(Pq[:, 0]) + 10 * (Pq[:, 1] < 0))]
        return f"SAND espesor med {st['esp_med']:.1f} p5 {st['esp_p5']:.1f} p95 {st['esp_p95']:.1f} | desliz med {st['desl_med']:.1f} p95 {st['desl_p95']:.1f} max {st['desl_max']:.1f} mm | ANILLO ancho {(Pq[:, 0].max() - Pq[:, 0].min()) * 1000:.0f} fondo {(cb[1] - cf[1]) * 1000:.0f} mm CF y {cf[1]:+.3f} z {cf[2]:.3f}"
    ES.sand_log = sand_log
    ES.log('   arranque: ' + ES.sand_log(ES.V0) if ES.P['sand'] > 0 else 'sin sandwich')


def autocol_manga_cuerpo(ES):
    """selfarm: autocolision manga-cuerpo. (sim_e2s.py L664-L672)"""
    # e2g T2-A: colision manga-cuerpo (solo cascaras, a > 12 mm de los bordes): manga entera y costados del cuerpo bajo la axila
    # e2q: sa_brd = franja sin autocolision junto a los bordes (mm de molde; 12 = como e2g-e2p)
    if ES.P['selfarm'] > 0:
        UVs = np.array(ES.D['uv'])
        BRD = set(ES.D['border'])
        add = 0
        for n in ('slR', 'slL', 'back', 'fcR', 'fcL', 'fsR', 'fsL'):
            a_, b_ = ES.D['groups'][n]
            ids = np.arange(a_, b_)
            bd = np.array([i for i in ids if i in BRD])
            dmin = np.min(np.linalg.norm(UVs[ids][:, None, :] - UVs[bd][None, :, :], axis=2), axis=1)
            ok = dmin > ES.P.get('sa_brd', 12.0)
            if not n.startswith('sl'):
                ok &= (np.abs(ES.V0[ids, 0]) > 0.13) & (ES.V0[ids, 2] > 0.9) & (ES.V0[ids, 2] < 1.36)
            ES.keep |= set(ids[ok].tolist())
            add += int(ok.sum())
        ES.log('autocolision manga-cuerpo: +', add, 'vertices | franja sin autocolision junto a los bordes', ES.P.get('sa_brd', 12.0), 'mm')


def autocol_vista(ES):
    """vcol: la vista (fa) choca con la cascara fc/fs. (sim_e2s.py L673-L694)"""
    # e2h: la vista choca con la CASCARA (no con la capa interior: con la franja del fc en el grupo, chocarian cascara e interior)
    # sin scipy en el Python de Blender: KDTree de mathutils (puntos 2D o 3D)
    # bordes cosidos: CF, hombro, escote
    if ES.P['vcol'] > 0:
        import mathutils.kdtree as _kdm
    
        class _KD:
    
            def __init__(self, P):
                P = np.asarray(P, float)
                self.t = _kdm.KDTree(len(P))
                for i, p in enumerate(P):
                    self.t.insert((p[0], p[1], p[2] if len(p) > 2 else 0.0), i)
                self.t.balance()
    
            def query(self, Q):
                Q = np.asarray(Q, float)
                return (np.array([self.t.find((q[0], q[1], q[2] if len(q) > 2 else 0.0))[2] for q in Q]),)
        UVs = np.array(ES.D['uv'])
        BRD = set(ES.D['border'])
        addv = 0
        adds = 0
        VIS = []
        for s_ in 'RL':
            ins = ES.D['inst']['fa' + s_]
            a_, b_ = ES.D['groups']['fa' + s_]
            ids = np.arange(a_, b_)
            cs_ = ins['cs']
            per_ = ins['per']
            sB = np.array(ins['s'])
            ob = ins['off']
            sew_e = []
            for e in (0, 3, 4):
                lo = cs_[e]
                hi = cs_[(e + 1) % 5]
                L_ = (hi - lo) % per_
                rel = (sB - lo) % per_
                sew_e += list(ob + np.where(rel <= L_ + 1e-06)[0])
            dmin = cKD = _KD(UVs[sew_e]).query(UVs[ids])[0]
            okv = ids[dmin > 10.0]
            ES.keep |= set(okv.tolist())
            addv += len(okv)
            VIS += list(ids)
        tr = _KD(ES.V0[VIS])
        for n in ('fcR', 'fsR', 'fcL', 'fsL'):
            a_, b_ = ES.D['groups'][n]
            ids = np.arange(a_, b_)
            bd = np.array([i for i in ids if i in BRD])
            dpat = np.min(np.linalg.norm(UVs[ids][:, None, :] - UVs[bd][None, :, :], axis=2), axis=1)
            d3 = tr.query(ES.V0[ids])[0]
            ok = (dpat > 12.0) & (d3 < 0.025)
            ES.keep |= set(ids[ok].tolist())
            adds += int(ok.sum())
        ES.log('autocolision vista-cascara: + vista', addv, '+ cascara fc/fs', adds, 'vertices')


def autocol_capucha(ES):
    """hcol: la capucha se apoya en espalda y hombros. (sim_e2s.py L695-L705)"""
    # e2i: la capucha se apoya en la espalda y los hombros sin atravesarlos (solo cascaras, a > 12 mm de los bordes)
    # contorno de la pieza en la malla (aristas con una sola cara): D["border"] no trae la capucha (no tiene capa interior)
    if ES.P['hcol'] > 0:
        UVs = np.array(ES.D['uv'])
        addh = {}
    
        def _pborder(n):
            a_, b_ = ES.D['groups'][n]
            fm = np.all((ES.F >= a_) & (ES.F < b_), axis=1)
            E_ = np.sort(np.concatenate([ES.F[fm][:, [0, 1]], ES.F[fm][:, [1, 2]], ES.F[fm][:, [2, 0]]]), 1)
            u_, c_ = np.unique(E_, axis=0, return_counts=True)
            return np.unique(u_[c_ == 1])
        for n, zmin in (('hsR', 0), ('hsL', 0), ('hc', 0), ('back', 1.2), ('fsR', 1.35), ('fsL', 1.35)):
            a_, b_ = ES.D['groups'][n]
            ids = np.arange(a_, b_)
            bd = _pborder(n)
            dmin = np.min(np.linalg.norm(UVs[ids][:, None, :] - UVs[bd][None, :, :], axis=2), axis=1)
            ok = (dmin > 12.0) & (ES.V0[ids, 2] > zmin)
            ES.keep |= set(ids[ok].tolist())
            addh[n] = int(ok.sum())
        ES.log('autocolision capucha-espalda: +', addh, 'total', sum(addh.values()))


def autocol_tapeta_diagnostico(ES):
    """tp_nocol: tapeta sin autocolision (diagnostico). (sim_e2s.py L707-L708)"""
    # e2zc DIAGNOSTICO: la tapeta sin autocolision (sigue cosida y con broches) -> si la deriva del CF a L se va, la empuja el choque de la tp
    if ES.P['tp_nocol'] > 0:
        ES.keep -= set(range(*ES.D['groups']['tp']))
        ES.log('tapeta SIN autocolision (diagnostico e2zc)')


def metricas_definir(ES):
    """cf_metrics / cf_nums / boca_log: metricas del eje CF, ruedo y boca de la capucha. (sim_e2s.py L786-L818)"""
    # e2e2+: camino de carga del CF por cuadro (cfidx_e2e.py): pandeo del eje del cierre y la tapeta (largo / largo suavizado SG 101 mm, tramo
    # interior), z de la esquina CF y del cuello CF, y R-L del ruedo por azimut (0 = CF, 90 = costado, 180 = CB).
    import os
    ES.CFI = json.load(open(ES.RUTA(ES.RD['indices_cf']))) if ES.RD.get('indices_cf') and os.path.exists(ES.RUTA(ES.RD['indices_cf'])) else None
    _xx = np.arange(-25, 26, dtype=float)
    SGC = np.linalg.pinv(np.stack([np.ones_like(_xx), _xx, _xx ** 2], 1))[0]
    def _axis(X, B):
        B = np.array(B)
        ii = B[:, :3].astype(int)
        w = B[:, 3:]
        return (X[ii] * w[:, :, None]).sum(1)
    def _exc(P):
        S = np.stack([np.convolve(P[:, k], SGC[::-1], mode='valid') for k in range(3)], 1)
        R_ = P[25:-25]
        return 100.0 * (np.linalg.norm(np.diff(R_, axis=0), axis=1).sum() / np.linalg.norm(np.diff(S, axis=0), axis=1).sum() - 1.0)
    def cf_metrics(X):
        H = X[ES.CFI['hem']] * 1000
        az = np.degrees(np.arctan2(H[:, 0], -H[:, 1]))
        d = []
        for a0 in range(0, 180, 15):
            r_ = H[(az >= a0) & (az < a0 + 15), 2]
            l_ = H[(az <= -a0) & (az > -a0 - 15), 2]
            if len(r_) and len(l_):
                d.append(np.median(r_) - np.median(l_))
        d = np.array(d)
        zc = X[ES.CFI['cf_corner'], 2] * 1000
        zn = X[ES.CFI['cf_neck'], 2] * 1000
        zb = np.median(H[np.abs(az) > 150, 2])
        return f"CF: pandeo zp {_exc(_axis(X, ES.CFI['zp'])):.1f}% tp {_exc(_axis(X, ES.CFI['tp'])):.1f}% | esquina CF z {zc[0]:.0f}/{zc[1]:.0f} cuello CF {zn[0]:.0f}/{zn[1]:.0f} ruedo CB {zb:.0f} mm | ruedo R-L max {np.abs(d).max():.0f} media {d.mean():.0f} mm (0-45: {d[:3].mean():.0f})"
    ES.cf_metrics = cf_metrics
    # e2j: esquina CF (2), cuello CF (2), ruedo CB, en mm; e2k: + centro de la boca de la capucha (y, z)
    def cf_nums(X):
        H = X[ES.CFI['hem']] * 1000
        az = np.degrees(np.arctan2(H[:, 0], -H[:, 1]))
        bc = X[ES.BOCA['path']].mean(0) * 1000 if ES.BOCA else np.zeros(3)
        return np.r_[X[ES.CFI['cf_corner'], 2] * 1000, X[ES.CFI['cf_neck'], 2] * 1000, np.median(H[np.abs(az) > 150, 2]), bc[1], bc[2]]
    ES.cf_nums = cf_nums
    # e2k: largo 3D del cordon (fila cosida) contra su reposo, costura de la boca, borde libre de la banda, centro de la boca
    def boca_log(X):
        if not ES.BOCA:
            return ''
    
        def _L(ix):
            Q = X[ix]
            return np.linalg.norm(np.diff(Q, axis=0), axis=1).sum() * 1000
        Lc = _L(ES.BOCA['cord_row1']) if ES.CORD else 0.0
        L0c = ES.D['inst']['cord']['largo_tunel_mm'] if ES.CORD else 1.0
        kv = 0.0
        try:
            kv = ES.gar.data.shape_keys.key_blocks['cordon'].value
        except Exception as _e_av:
            ES.avisar1("boca: sin la clave 'cordon' (cinch=0), tirado 0", _e_av)
        Lr = L0c * (1 - ES.P['cinch'] * kv)
        bc = X[ES.BOCA['path']].mean(0) * 1000
        uniq = [g[0] for g in ES.BOCA['grp']]
        return f"BOCA cordon 3D {Lc:.0f} / reposo {Lr:.0f} mm ({100 * (Lc / Lr - 1):+.1f} %) | costura boca {_L(uniq):.0f} (molde {ES.BOCA['L_mm']:.0f}) | borde libre banda {_L(ES.BOCA['hb_free']):.0f} (507,9) | centro boca y {bc[1]:.0f} z {bc[2]:.0f} mm"
    ES.boca_log = boca_log


def capucha_sin_cuello(ES):
    """HP: vertices de la capucha sin el cuello, para el log. (sim_e2s.py L823-L823)"""
    ES.HP = np.array(sorted(ES.HOODSET & set((i for n in ('hsR', 'hsL', 'hc') for i in range(*ES.D['groups'][n])))))


def simetria_presion(ES):
    """wsym: mismo peso de presion en el canal R y su espejo L (nombres xxR/xxL). (sim_e2s.py L846-L848)"""
    # e2zb: mismo peso de presion en el canal R y su espejo L (mismo relleno inyectado por canal); 0 = identico
    if ES.P['wsym'] > 0:
        for _k, _n in enumerate(ES.names):
            if _n[2:3] == 'R' and _n.replace('R', 'L', 1) in ES.idx:
                _j = ES.idx[_n.replace('R', 'L', 1)]
                ES.W[_k] = ES.W[_j] = 0.5 * (ES.W[_k] + ES.W[_j])


def metrica_cf_y_asentamiento(ES):
    """log CF + corte por asentamiento (SETTLED). (sim_e2s.py L881-L890)"""
    if ES.CFI:
        ES.log('   ' + ES.cf_metrics(ES.X))
    # e2j: asentamiento (mm cada 6 cuadros)
    if ES.CFI and ES.f >= ES.SET_F0:
        cn = ES.cf_nums(ES.X)
        ES.SHIST.append((ES.f, cn))
        if len(ES.SHIST) > 1:
            dd = cn - ES.SHIST[-2][1]
            dcf = float(np.abs(dd[:2]).max())
            if ES.P['settle_hood'] > 0 and ES.BOCA:
                dcf = max(dcf, float(np.abs(dd[5:7]).max()))
            ES.log(f'   ASENT f{ES.f} (+{ES.f - ES.SET_F0}) dz/6f esquina CF {dd[0]:+.1f}/{dd[1]:+.1f} cuello CF {dd[2]:+.1f}/{dd[3]:+.1f} ruedo CB {dd[4]:+.1f} mm | boca dy {dd[5]:+.1f} dz {dd[6]:+.1f} | esquina {cn[0]:.0f}')
            ES.SHIST[-1] = (ES.f, cn, dcf)
            if ES.P['settle_min'] > 0 and ES.f - ES.SET_F0 >= ES.P['settle_min'] and (len(ES.SHIST) > int(ES.P['settle_n'])) and all((len(h) > 2 and h[2] < ES.P['settle_tol'] for h in ES.SHIST[-int(ES.P['settle_n']):])):
                ES.log(f"ESTABLE en f{ES.f}: esquina CF < {ES.P['settle_tol']} mm cada 6 cuadros en {int(ES.P['settle_n'])} chequeos seguidos")
                ES.SETTLED = True


def metricas_por_cuadro(ES):
    """log de capucha, boca, sandwich, torsion, giro y presion R/L. (sim_e2s.py L891-L904)"""
    HH = ES.X[np.concatenate([np.arange(*ES.D['groups'][n]) for n in ('hsR', 'hsL', 'hc')])]
    ES.log(f'   capucha: z {HH[:, 2].min():.3f}-{HH[:, 2].max():.3f} y max {HH[:, 1].max():.3f} | cabeza cubierta: {int(((HH[:, 2] > 1.72) & (np.abs(HH[:, 1] - 0.01) < 0.08)).sum())} vertices sobre la coronilla')
    # e2i: capucha (sin cuello) apoyada: centroide y fraccion detras de la nuca (y > 0,10) y bajo z 1,62
    if len(ES.HP):
        XH = ES.X[ES.HP]
        ES.log(f'   capucha sin cuello: centroide y {XH[:, 1].mean():.3f} z {XH[:, 2].mean():.3f} | z max {XH[:, 2].max():.3f} | detras de la nuca y bajo 1,62: {100.0 * np.mean((XH[:, 1] > 0.1) & (XH[:, 2] < 1.62)):.0f} %')
    if ES.BOCA:
        ES.log('   ' + ES.boca_log(ES.X))
    if ES.SAND_BM is not None:
        ES.log('   ' + ES.sand_log(ES.X))
    _z = ES.X[np.arange(*ES.D['groups']['zp'])]
    _cs = {s_: ES.X[np.array(ES.D['sew'])[np.array(ES.D['sew_seam']) == f'costado {s_}'].ravel()] for s_ in 'RL'}
    _cy = {s_: _c[(_c[:, 2] > 1.0) & (_c[:, 2] < 1.25), 1].mean() * 1000 for s_, _c in _cs.items()}
    ES.log(f"   TORSION eje CF x pecho {_z[_z[:, 2] > 1.2, 0].mean() * 1000:+.0f} ruedo {_z[_z[:, 2] < 1.0, 0].mean() * 1000:+.0f} mm | costado y R {_cy['R']:+.0f} L {_cy['L']:+.0f}")
    _bk = ES.X[np.arange(*ES.D['groups']['back'])]
    _xh = ES.X[ES.HP, 0].mean() * 1000 if len(ES.HP) else 0.0
    ES.log(f'   GIRO x prenda {ES.X[:, 0].mean() * 1000:+.1f} | espalda ruedo x {_bk[_bk[:, 2] < 1.0, 0].mean() * 1000:+.1f} | cuello (zp z>1,40) x {_z[_z[:, 2] > 1.4, 0].mean() * 1000:+.1f} | capucha x {_xh:+.1f} mm')
    _pr = [(ES.names[k], ES.names[k].replace('R', 'L', 1)) for k in range(len(ES.names)) if ES.names[k][2:3] == 'R' and ES.names[k].replace('R', 'L', 1) in ES.names]
    _dw = sorted(((ES.W[ES.names.index(a_)] - ES.W[ES.names.index(b_)], a_[:2] + a_[3:]) for a_, b_ in _pr), key=lambda t: -abs(t[0]))[:4]
    _sR = sum((ES.W[ES.names.index(a_)] * ES.AREA[ES.names.index(a_)] for a_, b_ in _pr))
    _sL = sum((ES.W[ES.names.index(b_)] * ES.AREA[ES.names.index(b_)] for a_, b_ in _pr))
    ES.log(f'   PRES R/L sum(W x area) {_sR * 1000:.1f}/{_sL * 1000:.1f} (x1000) | mayores dW R-L: ' + ' '.join((f'{nm_} {d_:+.2f}' for d_, nm_ in _dw)))
