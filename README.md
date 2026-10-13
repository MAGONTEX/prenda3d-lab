# prenda3d-lab

**Open garment simulation from real sewing patterns.** `prenda3d` builds 3D garments from the flat pattern pieces a
factory cuts (panels, seams, trims), sews them on a body and simulates the cloth in Blender (5.1, CPU, headless). The
goal is a garment that behaves like the real one in every state (hood up or down, zipped or open) so it can later be
animated. Maintained by Parka Supply Co (Magontex S.A., Buenos Aires). The method is being written up so anyone can
reuse it.

## What lives here

| Path | What it is |
|---|---|
| `sim/` | the simulator core (`nucleo.py`, `lanzar.py`) and per-garment rules |
| `lab/` | synthetic test benches: strips, panels, cylinders, layer sandwiches, quilted channels |
| `prendas/<code>/` | public garment packages: meshes, bodies, recipes (no factory files, photos or supplier data) |
| `scripts/` | queue tools, the garment packager (allow-list + leak scan) and result comparison |
| `resultados/`, `resultados_prendas/` | small metrics JSON per test run (seam gaps, intersections, relief, measurements) |

## How CI is used

Every GitHub Actions run here is a **test of the simulator**: a bench or garment variant is simulated and measured in the
same job, and only a small metrics JSON is committed back. Runs are started by a push to a queue folder or by hand.

Rules we keep so the project stays a good CI citizen:
- No scheduled (cron) runs and no jobs that re-trigger themselves.
- Every job has a hard `timeout-minutes`; the matrix has a `max-parallel` cap.
- Smoke test first (2 variants), then the wide batch; a batch only runs when it answers a question.
- No rendering farms: final renders run elsewhere; CI keeps small viewport images as QC evidence only.
- Heavy outputs (`.npy`) are short-lived artifacts, never committed.

## License

- Code (`sim/`, `lab/`, `scripts/`, workflows): [MIT](LICENSE).
- Garment data (`prendas/`): [CC BY 4.0](prendas/LICENSE) - credit "Parka Supply Co - prenda3d".

---

## Laboratorio (español)

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
`out/` como artifact (`.npy`, `res_*.json`, `sim_*.log`, `tiempos.txt`).

## Correr en local

```
blender -b --factory-startup -t 4 --python lab/correr.py -- tanda=lab/tandas/b1_bisagra.json salida=out/b1_bisagra
python scripts/comparar.py out_a out_b 0.1
```

La version de Blender debe ser la misma en ambos lados: el simulador lee estado interno del Cloth por offsets de memoria
(`sim/offsets.py`) y falla fuerte si la version no es la validada (5.1).

## Determinismo (medido 2026-10-10)

- Actions contra Actions: identico bit a bit (0,000000 mm) en 527 archivos, con 1 y con 4 hilos.
- Prendas enteras (`prenda.yml`, M133, 2026-10-13): con los mismos hilos repite bit a bit; con otro numero de hilos NO
  (1, 2 y 4 hilos dan bits distintos). Los controles y las palancas de una misma comparacion van con el mismo `pack` y los
  mismos `hilos`: una corrida con `"pack": 2` (`-t 2`) no es identica bit a bit a una de 4 hilos. Ver `prendas/README.md`.
- Windows (laptop) contra Actions: NO coincide. Error maximo 34 mm (banco b2), 102 mm (b1), 191 mm (b3); el umbral era 0,1 mm.
- La laptop tampoco repite exacto entre corridas en b1 y b3 (hasta 1,9 y 130 mm); b2 si repite.
- Regla: comparar variantes solo dentro de una misma plataforma. En Actions es seguro; no mezclar con corridas locales.

Comando de comparacion: `python scripts/comparar.py carpeta_a carpeta_b 0.1`.

## Cola autonoma [ESC·f535]
`cola/<tanda>.json` (mismo formato que `lab/tandas/`) -> el workflow `cola.yml` (push a `cola/` o a mano; sin cron) la
mueve a `tomadas/`, corre cada tanda en su propio trabajo (hasta 20 en paralelo), calcula las metricas y commitea
`resultados/<tanda>.json` (resumen chico); los `.npy` quedan como artifact `npy-<tanda>-<run>` 14 dias. Termina en
`hecho/` o `fallo/`. Validador y pasos: `scripts/cola.py`. Solo bancos sinteticos del laboratorio.

## Prendas enteras [ESC·f535]
Cola aparte (`cola_prendas/`, workflow `prenda.yml`) para correr prendas enteras con `sim/lanzar.py`. Guia: `prendas/README.md`.
