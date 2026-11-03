# Estructura del repositorio

```text
sismo-ml-peru-e030/
├── README.md                          Portada: badges, estado, integrantes, inicio rápido
├── ESTRUCTURA_REPO.md                 Este archivo
├── requirements.txt                   Dependencias (Python ≥ 3.10)
├── .gitignore                         Excluye registros crudos (.AT2), flatfile y cachés
│
├── data/                              ── DATOS (CSV, UTF-8, separador coma) ──
│   ├── catalogo_arquetipos.csv        40 arquetipos diseñados · 41 columnas
│   ├── matriz_combinaciones.csv       16 000 casos planificados (arquetipo × slot × λ)
│   ├── tabla_escalamiento.csv         Sa objetivo E.030-2026 por arquetipo y nivel λ
│   ├── dataset_sismico_peru_EJEMPLO.csv  14 NLTHA ilustrativos · 57 columnas
│   ├── dataset_sismico_peru.csv       [se genera] matriz final 16 000 (+1 600) filas
│   ├── registros_seleccionados.csv    [se genera] 100 pares NGA-West2 (slot ↔ RSN)
│   ├── at2/                           [no versionado] registros PEER RSN*_*.AT2
│   └── peru/                          [no versionado] acelerogramas CISMID / IGP
│
├── src/                               ── CÓDIGO ──
│   ├── e030.py                        Parámetros y espectro E.030 (2018 y 2026)
│   ├── arquetipos.py                  Clase Arquetipo (geometría, pesos, materiales)
│   ├── modelo_opensees.py             Diseño E.030, modelo 3D OpenSeesPy, NLTHA bidireccional
│   ├── registros.py                   Lectura .AT2, espectros, IMs, escalamiento, Perú
│   ├── gen_catalogo.py                Genera data/catalogo_arquetipos.csv
│   ├── gen_matriz.py                  Genera matriz_combinaciones.csv y tabla_escalamiento.csv
│   ├── procesar_flatfile.py           Flatfile NGA-West2 → registros_seleccionados.csv
│   ├── campana_nltha.py               Corre los NLTHA → dataset_sismico_peru.csv
│   └── validar_integridad.py          13 reglas + 5 controles, reporte PASS/FAIL
│
├── notebooks/
│   └── eda_t2.ipynb                   EDA de la Entrega T2 (ejecutado, con salidas)
│
├── tests/
│   └── test_validar_integridad.py     Prueba negativa: corrompe datos y exige FAIL
│
└── docs/                              ── DOCUMENTACIÓN ──
    ├── 01_CATALOGO_ARQUETIPOS_ESTRUCTURALES.md
    ├── 02_SELECCION_Y_ESCALAMIENTO_SISMICO.md
    ├── 03_DICCIONARIO_DE_VARIABLES_Y_ESQUEMA_CSV.md
    ├── INFORME_T2_EDA_Y_PLAN_ML.md    Informe de la Entrega T2
    ├── bitacora_prompts.md            Bitácora obligatoria de transparencia de IA
    ├── presentacion_T2_guion.md       Contenido y guion de las 4 diapositivas
    └── figuras/                       Figuras exportadas por el notebook
        ├── eda_catalogo_T1_cortante.png
        ├── eda_targets.png
        ├── eda_SaT1_vs_MIDR.png
        ├── eda_spearman_dataset.png
        ├── eda_spearman_catalogo.png
        └── eda_sobrerresistencia.png
```

## Flujo de datos

```text
                    gen_catalogo.py                    gen_matriz.py
E.030-2026 ─────────► catalogo_arquetipos.csv ─────────► matriz_combinaciones.csv
(e030.py,             (40 edificios diseñados)           tabla_escalamiento.csv
 modelo_opensees.py)            │
                                │            procesar_flatfile.py
Flatfile NGA-West2 + .AT2 ──────┼──────────► registros_seleccionados.csv (100 pares)
                                ▼                        │
                         campana_nltha.py ◄──────────────┘
                                │   (OpenSeesPy, NLTHA bidireccional, E.030-2026)
                                ▼
                     dataset_sismico_peru.csv  (57 columnas)
                                │
                 validar_integridad.py  ──► 18 controles PASS/FAIL
                                │
                     notebooks/eda_t2.ipynb  ──► docs/figuras/*.png
```

## Dependencias entre módulos

| Script | Importa | Lee | Escribe |
| --- | --- | --- | --- |
| `gen_catalogo.py` | `arquetipos`, `e030`, `modelo_opensees` | — | `data/catalogo_arquetipos.csv` |
| `gen_matriz.py` | — | `catalogo_arquetipos.csv` | `matriz_combinaciones.csv`, `tabla_escalamiento.csv` |
| `procesar_flatfile.py` | `registros` | flatfile, `.AT2` | `registros_seleccionados.csv` |
| `campana_nltha.py` | `arquetipos`, `e030`, `registros`, `modelo_opensees`, `validar_integridad` | catálogo, registros, `.AT2` | `dataset_sismico_peru.csv` (+ `_errores.csv`) |
| `validar_integridad.py` | — | cualquier CSV de 57 columnas | reporte por consola |
| `eda_t2.ipynb` | — | catálogo y dataset (o el EJEMPLO) | `docs/figuras/*.png` |

## Qué se versiona y qué no

| Se versiona | No se versiona (`.gitignore`) |
| --- | --- |
| Código, notebooks con salidas, documentación, figuras | Registros `.AT2` de PEER y acelerogramas peruanos |
| CSV del catálogo, matriz, tabla de escalamiento y ejemplo | Flatfile de NGA-West2 |
| `dataset_sismico_peru.csv` cuando exista (≈ 6–7 MB) | Archivos de error de la campaña, cachés de Python y Jupyter |

## Comandos Git para subir cambios

```bash
git pull                                   # traer lo último del grupo
git add src/ data/*.csv notebooks/ docs/ README.md ESTRUCTURA_REPO.md
git commit -m "T2: EDA, validación de integridad e informe"
git push
```
