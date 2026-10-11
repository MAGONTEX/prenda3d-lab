"""[ESC·f535] prenda3d/lab/zozo/zz_angosto.py - canal ANGOSTO sintetico: el almohadon 145x300 h10 escalado en x (ancho).
Escala v (3D) y uv (molde) en x por el mismo factor: misma topologia, mismos pines y costuras, celdas de 10 x 10*k mm.
    python lab/zozo/zz_angosto.py [k=0.3333]     # (desde Diseño/prenda3d) escribe lab/escenas/zz_angosto_h10.json (ZOZO,
                                                 # sin separar) y zz_angosto_n48.json (Blender, con la separacion +-1 mm)
"""
import json
import os
import sys

LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
k = float(sys.argv[1].split("=")[1]) if len(sys.argv) > 1 else 1 / 3
for src, dst in (("b5_almohadon_h10", "zz_angosto_h10"), ("zz_canal_h10", "zz_angosto_n48")):
    D = json.load(open(os.path.join(LAB, "escenas", src + ".json"), encoding="utf-8"))
    D["v"] = [[x * k, y, z] for x, y, z in D["v"]]; D["uv"] = [[u * k, w] for u, w in D["uv"]]
    D["lab"] = dict(D["lab"], ancho=D["lab"]["ancho"] * k, w=D["lab"].get("w", D["lab"]["ancho"]) * k, escena=dst)
    json.dump(D, open(os.path.join(LAB, "escenas", dst + ".json"), "w", encoding="utf-8"))
    print("[ESC·f535]", dst, "ancho", round(D["lab"]["ancho"], 2), "nv", len(D["v"]))
