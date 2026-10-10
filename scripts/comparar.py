"""[ESC·f535] Compara dos carpetas de salida del laboratorio (X_<tag>_f<N>.npy, posiciones en METROS).

    python scripts/comparar.py A B [umbral_mm=0.1]

Por cada .npy comun: error maximo = max sobre vertices de la distancia euclidea |A-B| en mm. Imprime el peor caso por banco y
sale 1 si alguno supera el umbral. Archivos que estan en una carpeta y no en la otra se reportan (y cuentan como fallo).
"""
import glob
import os
import sys

import numpy as np


def main():
    A, B = sys.argv[1], sys.argv[2]; umbral = float(sys.argv[3]) if len(sys.argv) > 3 else 0.1
    fa = {os.path.relpath(p, A): p for p in glob.glob(os.path.join(A, "**", "X_*.npy"), recursive=True)}
    fb = {os.path.relpath(p, B): p for p in glob.glob(os.path.join(B, "**", "X_*.npy"), recursive=True)}
    solo = sorted(set(fa) ^ set(fb)); comunes = sorted(set(fa) & set(fb)); peor = {}; rms = {}; mal = 0
    for k in comunes:
        a, b = np.load(fa[k]), np.load(fb[k])
        if a.shape != b.shape:
            print("FORMA DISTINTA", k, a.shape, b.shape); mal += 1; continue
        d = np.linalg.norm((a - b).reshape(-1, a.shape[-1]), axis=1) * 1000.0
        banco = k.split(os.sep)[0]; peor[banco] = max(peor.get(banco, 0.0), float(d.max())); rms.setdefault(banco, []).append(float(np.sqrt((d ** 2).mean())))
    for b_ in sorted(peor):
        print(f"{b_:14s} max {peor[b_]:.6f} mm  rms_medio {np.mean(rms[b_]):.6f} mm  ({len(rms[b_])} archivos)")
    glob_max = max(peor.values()) if peor else float("nan")
    print(f"TOTAL {len(comunes)} archivos comunes, {len(solo)} en solo una carpeta, error maximo global {glob_max:.6f} mm (umbral {umbral} mm)")
    for s in solo[:10]:
        print("  solo en una:", s)
    return 0 if (not solo and not mal and glob_max < umbral) else 1


if __name__ == "__main__":
    sys.exit(main())
