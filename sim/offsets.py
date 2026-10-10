"""Unico lugar donde el simulador lee el estado interno del Cloth por OFFSETS DE MEMORIA (ctypes sobre punteros de RNA).

Es la unica forma de ver el `dt` real y los resortes, pero depende del layout de los structs de C de UNA version de Blender.
Si la version cambia, toda lectura FALLA FUERTE (RuntimeError) hasta que alguien revalide los offsets y suba BLENDER_VALIDADO.

LECTURAS deja constancia de cada lectura que existe hoy (quien, que struct, que offset, como se valido).
"""
import ctypes

BLENDER_VALIDADO = (5, 1)
LECTURAS = [
    dict(donde="sim/nucleo.py bucle(), log QINI (solo con q_ini > 0)", struct="ClothSimSettings (settings.as_pointer() del modificador EVALUADO)",
         offset=8, tipo="8 float32", campos={2: "Cvi = air_damping", 5: "gravedad z", 6: "dt real del solver", 7: "mass"},
         validado="_qc_e2zz/t_quality.py (Blender 5.1): Cvi, gravedad y masa coinciden con las propiedades RNA"),
    dict(donde="sim/origen/sonda_cloth.py (sonda aparte, --python antes del simulador)", struct="ClothModifierData -> clothObject* (offset buscado por firma: 3 punteros RNA seguidos)",
         offset=None, tipo="Cloth {verts* +0, springs* +8, numsprings u32 +16, mvert_num u32 +20, last_frame i32 +72}; ClothVertex x en +28, stride 168",
         campos={}, validado="la propia sonda detecta offset de x y stride contra la malla evaluada y avisa si no son 28 / 168"),
]


class LayoutDesconocido(RuntimeError):
    pass


def verificar_version(bpy):
    v = tuple(bpy.app.version[:2])
    if v != BLENDER_VALIDADO:
        raise LayoutDesconocido(f"offsets del Cloth validados solo en Blender {BLENDER_VALIDADO[0]}.{BLENDER_VALIDADO[1]}; esta es {v[0]}.{v[1]}. "
                                "Revalidar sim/offsets.py (LECTURAS) antes de leer memoria: un offset corrido devuelve basura sin avisar.")
    return v


def floats_sim_settings(settings, bpy):
    """8 float32 de ClothSimSettings desde +8. Control de cordura: masa y air_damping leidos por offset == los de RNA; dt en (0, 1]."""
    verificar_version(bpy)
    fl = (ctypes.c_float * 8).from_address(settings.as_pointer() + 8)
    if abs(fl[7] - settings.mass) > 1e-6 * max(1.0, abs(settings.mass)) or abs(fl[2] - settings.air_damping) > 1e-5 * max(1.0, abs(settings.air_damping)) or not (0.0 < fl[6] <= 1.0):
        raise LayoutDesconocido(f"ClothSimSettings: el layout no es el esperado (masa por offset {fl[7]} vs RNA {settings.mass}; Cvi {fl[2]} vs {settings.air_damping}; dt {fl[6]})")
    return fl
