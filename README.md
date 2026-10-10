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

## Determinismo

Ver la seccion de determinismo del informe del proyecto: una corrida en Actions y una en Windows se comparan con
`scripts/comparar.py`; el umbral fijado de antemano es 0,1 mm de error maximo por vertice.
