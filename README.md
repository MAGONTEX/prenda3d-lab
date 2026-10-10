# prenda3d-lab

[ESC·f535] Laboratorio de simulacion de tela (Cloth de Blender 5.1.0, CPU, sin interfaz) para validar el codigo de un simulador de
prendas. Cada "banco" es una tanda de escenas SINTETICAS minimas (tiras, panel, cilindro, sandwich de capas, canelon) que se
simulan con el nucleo del simulador y devuelven posiciones de vertices (`.npy`) y metricas.

Este repo existe para correr esos bancos gratis en GitHub Actions. No contiene moldes, fotos ni datos de ninguna prenda real.

## Que hay

| Carpeta | Contenido |
|---|---|
| `sim/` | nucleo del simulador (`nucleo.py`) y reglas del sandwich |
| `lab/` | armado de escenas (`escena.py`), corredor (`correr.py`), metricas (`metricas.py`), escenas y tandas |
| `lab/escenas/` | escenas sinteticas en json (se regeneran con `python lab/escena.py`) |
| `lab/tandas/` | un json por banco: receta, cuadros y variantes |
| `prenda3d/receta.py`, `datos_m133/` | lector de recetas de parametros |
| `scripts/comparar.py` | compara dos carpetas de `.npy` (error maximo en mm) |

## Correr en GitHub Actions

Actions > banco > Run workflow (o `gh workflow run banco.yml -f tandas="b1_bisagra b2_salto b3_sandwich" -f hilos=4`).
Baja `blender-5.1.0-linux-x64` de download.blender.org (cache entre corridas, SHA-256 verificado), corre las tandas y sube
`out/` como artifact (`.npy`, `res_*.json`, `sim_*.log`, `tiempos.txt`). Tambien corre solo cada noche (06:17 UTC).

## Correr en local

```
blender -b --factory-startup -t 4 --python lab/correr.py -- tanda=lab/tandas/b1_bisagra.json salida=out/b1_bisagra
python scripts/comparar.py out_a out_b 0.1
```

La version de Blender debe ser la misma en ambos lados: el simulador lee estado interno del Cloth por offsets de memoria
(`sim/offsets.py`) y falla fuerte si la version no es la validada (5.1).

## Determinismo (medido 2026-10-10)

- Actions contra Actions: identico bit a bit (0,000000 mm) en 527 archivos, con 1 y con 4 hilos.
- Windows (laptop) contra Actions: NO coincide. Error maximo 34 mm (banco b2), 102 mm (b1), 191 mm (b3); el umbral era 0,1 mm.
- La laptop tampoco repite exacto entre corridas en b1 y b3 (hasta 1,9 y 130 mm); b2 si repite.
- Regla: comparar variantes solo dentro de una misma plataforma. En Actions es seguro; no mezclar con corridas locales.

Comando de comparacion: `python scripts/comparar.py carpeta_a carpeta_b 0.1`.

## Cola autonoma [ESC·f535]
`cola/<tanda>.json` (mismo formato que `lab/tandas/`) -> el workflow `cola.yml` (push a `cola/`, cada 2 h o a mano) la
mueve a `tomadas/`, corre cada tanda en su propio trabajo (hasta 20 en paralelo), calcula las metricas y commitea
`resultados/<tanda>.json` (resumen chico); los `.npy` quedan como artifact `npy-<tanda>-<run>` 14 dias. Termina en
`hecho/` o `fallo/`. Validador y pasos: `scripts/cola.py`. Solo bancos sinteticos del laboratorio.
