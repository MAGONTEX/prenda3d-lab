# Prendas enteras en GitHub Actions [ESC·f535]

El workflow `prenda.yml` corre simulaciones de prendas ENTERAS (Blender 5.1.0, CPU, `sim/lanzar.py` + `sim/nucleo.py` +
`sim/<codigo>_reglas.py`). Cada variante es un trabajo: 4 vCPU, hasta 20 a la vez, tope 6 h. Es la misma mecanica que `cola.yml`
(tomar con git mv + push como candado, matriz, cerrar), en carpetas propias para no mezclarse con los bancos ni con el worker del VPS.

Regla de plataforma (CPU-GRATIS.md §3): las variantes que se comparan entre si van TODAS en Actions. Actions repite bit a bit;
la laptop no, y no coincide con Actions. Nunca comparar una corrida de Actions con una de la laptop salvo a ojo (STOP, costuras, tiempos).

## Que hay

| Ruta | Que es |
|---|---|
| `prendas/<codigo>/prenda_publica.json` | prenda.json por LISTA BLANCA (sin DXF, notas, nombres ni proveedores; materiales = mat1..) |
| `prendas/<codigo>/*.json`, `*.npz` | malla V0/S (json), cuerpo (npz), recetas, rk/hrest si hacen falta |
| `sim/lanzar.py`, `sim/nucleo.py`, `sim/<codigo>_reglas.*` | el simulador (copia del paquete; reglas saneadas) |
| `cola_prendas/` -> `tomadas_prendas/` -> `hecho_prendas/` o `fallo_prendas/` | la cola |
| `resultados_prendas/<tanda>.json` | resumen chico por variante (estado, STOP, costuras peores, tiempos, ASENT) |
| `scripts/prendas.py` | validar / tomar / preparar / resumir / cerrar |
| `scripts/empaquetar_prenda.py` | arma `prendas/<codigo>/` desde la carpeta privada de la prenda (corre en la laptop) |

## 1. Subir una prenda (o una malla nueva) — en la laptop

OBLIGATORIO pasar por el empaquetador: aplica la lista blanca y escanea todo con la lista PRIVADA de patrones
(`Diseño/prenda3d/tools/limpieza_patrones.txt`: nombres de proveedores de las cuatro camperas, moldes DXF, el `prenda.json` original, fotos)
mas rutas personales, claves y texto en chino. Si encuentra algo, sale con 1 y NO se commitea. Nunca copiar prenda.json a mano.

```
D="../WEB MAYORISTA/Diseño"
python scripts/empaquetar_prenda.py --carpeta "$D/higgsfield/50-w2057" --paquete "$D/prenda3d" --codigo w2057 \
  --malla w2057_s1.json [--malla w2057_s2.json] --cuerpo cuerpo_W2057_piel20.npz --receta sim/receta_c1.json \
  [--extra m1195_s5_rk.npz] [--extra sim/ficha_m1195.py] --patrones "$D/prenda3d/tools/limpieza_patrones.txt"
python sim/lanzar.py --validar prenda=prendas/w2057/prenda_publica.json receta=prendas/w2057/receta_c1.json entradas=prendas/w2057 nf=40
git add prendas/w2057/<archivos> sim/w2057_reglas.py sim/w2057_reglas.json     # rutas explicitas
```
- `--malla` repetible: la primera queda como malla por defecto en `prenda_publica.json`.
- Lo que el nucleo lee de la carpeta de entradas (rk, hrest, modulos como `sim/ficha_m1195.py`) va con `--extra` y la misma ruta relativa.
- Si cambia el nucleo o lanzar.py del paquete, copiarlos a `sim/` y revisar el diff (el `origen/sim_e2s.py` de aca esta saneado: no se pisa).
- Nunca suben: DXF, fotos, nombres de proveedores, claves, rutas personales de Windows.

## 2. Encolar

`cola_prendas/<nombre>.json` (nombre = archivo, `a-z 0-9 _`). Cada campo se busca en la variante, despues en su grupo, despues en la tanda:

```json
{"nombre": "m1195_r9", "prenda": "m1195", "hilos": 4, "tmo_min": 330, "nota": "r9: G0 = c6, G1 = bc2, 5 replicas c/u",
 "grupos": {
  "G0": {"malla": "m1195_s5.json", "receta": "receta_c6.json", "cuerpo": "cuerpo_M1195_sim5.npz", "rk": "m1195_s5_rk.npz",
         "nf": 150, "dumps": [2, 6, 36, 48, 72, 96, 120, 150]},
  "G1": {"malla": "m1195_bc2.json", "receta": "receta_bc2.json", "cuerpo": "cuerpo_M1195_bc2.npz", "hrest": "m1195_bc2_hrest.npz",
         "nf": 120, "dumps": [2, 6, 36, 48, 72, 96, 120]}},
 "params": {},
 "variantes": [{"tag": "m1195_g0_a1", "grupo": "G0", "params": {"air": 1.001}},
               {"tag": "m1195_g1_a1", "grupo": "G1", "params": {"air": 1.001}}]}
```
- Campos: `receta` `malla` `cuerpo` `nf` `dumps` `params` `rk` `wini` `pramp` `pfit` `hrest` `base` (archivos: relativos a `prendas/<prenda>/`),
  `script` (defecto `sim/lanzar.py`), `hilos` (1..4, defecto 4), `tmo_min` (defecto 330).
- `params` se suman sobre la receta: tanda -> grupo -> variante (gana el ultimo). Clave desconocida = error del lanzador.
- `renders` queda en 0 (sin GPU); pedir `"params": {"renders": 1}` solo para probar.
- Antes del push: `python scripts/prendas.py validar cola_prendas/<nombre>.json` (debe decir OK).
- `git add cola_prendas/<nombre>.json && git commit -m "[ESC·f535] prendas: encola <nombre>" && git push` -> el push dispara `prenda.yml`.
  Tambien corre cada 2 h y a mano: `gh workflow run prenda.yml -R MAGONTEX/prenda3d-lab`. Mas de 20 variantes: toma de a 20 y se relanza.

## 3. Bajar resultados

- Resumen: `git pull` -> `resultados_prendas/<nombre>.json` (estado OK/FALLO, por variante: estado FIN/STOP/ESTABLE/ERROR, cuadros,
  `t_sim_s`, `stop`, `costura_ultimo_cuadro`, `costuras_peores`, `asent`, `avisos`, `id_corrida`).
- Logs y `.npy` (14 dias): `gh run download <run_id> -R MAGONTEX/prenda3d-lab -n prenda-<nombre>--<tag>-<run_id> -D <carpeta>`.
  Adentro: `sim_<tag>.log`, `blender.out`, `cmd.txt`, `receta_<tag>.json`, `corridas/<id>.json` (manifest con sha de todo),
  `X_<tag>_f<N>.npy`, `X_<tag>_final.npy`, `costuras_gap_<tag>.txt`. El run id esta en `url` del resumen.
- Estado en vivo: `gh run list -R MAGONTEX/prenda3d-lab -w prenda` y `gh run view <run_id> -R MAGONTEX/prenda3d-lab`.

## Validacion (2026-10-11)

Ver `resultados_prendas/w2057_val40.json`: W2057 c1 (malla s1, receta c1) a 40 cuadros con `-t 4` contra la corrida c1 de la laptop.
