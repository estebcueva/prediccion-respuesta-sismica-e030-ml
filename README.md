# Predicción de Demandas Sísmicas en Edificaciones de Concreto Armado en el Perú con Machine Learning Supervisado

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![OpenSeesPy](https://img.shields.io/badge/OpenSeesPy-NLTHA%203D-informational)
![Norma](https://img.shields.io/badge/Norma-E.030--2026%20(RM%20183--2026--VIVIENDA)-red)
![Datos](https://img.shields.io/badge/Registros-PEER%20NGA--West2-blueviolet)
![Estado](https://img.shields.io/badge/Estado-T3%20%C2%B7%20modelos%20entrenados-brightgreen)
![Integridad](https://img.shields.io/badge/Integridad-18%2F18%20PASS%20(dataset%20real)-brightgreen)
![Campa%C3%B1a](https://img.shields.io/badge/Campa%C3%B1a%20NLTHA-1%20422%20casos-blue)

**Curso:** Aplicaciones de IA en Estructuras — Universidad Peruana de Ciencias Aplicadas (UPC)
**Docente:** Ing. Kurt Soncco Sinchi

| Integrante | Código | Correo |
| --- | --- | --- |
| Paulino Antonio Díaz Hinostroza | e201572251 | e201572251@upc.edu.pe |
| Rodrigo Alonso De la Cruz Herrera | e202527672 | e202527672@upc.edu.pe |
| Guido Eduardo Valdez Tejeira | e202528480 | e202528480@upc.edu.pe |
| Felix Mamani Huanca | e202527091 | e202527091@upc.edu.pe |
| Johnny Esteban Cueva Moncada | e202527071 | e202527071@upc.edu.pe |

---

## Qué hace este proyecto

Un análisis tiempo-historia no lineal (NLTHA) de un edificio tarda de minutos a horas. Este proyecto construye una base de datos de **16 000 NLTHA**: 40 edificios peruanos de concreto armado diseñados con la **E.030-2026**, 100 pares de acelerogramas de **PEER NGA-West2** y 4 niveles de intensidad. Con esa base se entrenan modelos de Machine Learning que predicen en milisegundos:

- **ln(MIDR)**: logaritmo natural de la deriva máxima de entrepiso, con su marca de cumplimiento del límite de 0.007;
- **Vb/W**: cortante basal normalizado por el peso.

La validación externa usa sismos peruanos de **subducción** (Lima 1966, Lima 1974, Pisco 2007), un tipo de fuente que no existe en NGA-West2.

> **Campaña ejecutada para la T3.** Por el límite de memoria computacional, y con la conformidad del docente, la campaña se redujo al set **far-field de FEMA P695** (22 pares de registros PEER NGA, mismos RSN de NGA-West2, 14 sismos) con 3 niveles de intensidad (0.5, 1.0 y 1.5). Se completaron **1 422 NLTHA de 35 arquetipos** (54 % de los 2 640 previstos). Resultados en [`docs/RESULTADOS_T3.md`](docs/RESULTADOS_T3.md).

## Estado del proyecto

| Componente | Estado | Archivo |
| --- | --- | --- |
| Catálogo de 40 arquetipos diseñados (E.030-2026) | ✅ Completo y verificado | `data/catalogo_arquetipos.csv` |
| Matriz experimental 40 × 100 × 4 = 16 000 casos | ✅ Generada (con slots de registro) | `data/matriz_combinaciones.csv` |
| Objetivos espectrales por arquetipo y nivel | ✅ | `data/tabla_escalamiento.csv` |
| Selección de registros | ✅ Set far-field de FEMA P695 (22 pares, 14 sismos); la selección propia desde el flatfile NGA-West2 queda para una ampliación | `src/exportar_p695.py`, `src/procesar_flatfile.py` |
| Campaña NLTHA → `dataset_sismico_peru.csv` | ✅ 1 422 NLTHA, 35 de 40 arquetipos (DUA-04, DUA-10, MUR-01, MUR-03 y POR-06 no se ejecutaron) | `src/campana_nltha.py`, `data/dataset_sismico_peru.csv` |
| Verificación de integridad (13 reglas + 5 controles) | ✅ 18/18 PASS sobre el dataset real; prueba negativa OK | `src/validar_integridad.py` |
| EDA (Entrega T2) | ✅ Ejecutado | `notebooks/eda_t2.ipynb` |
| Entrenamiento de modelos (T3) | ✅ Ridge, Random Forest, XGBoost, LightGBM y red neuronal MLP; GroupKFold por evento y prueba retenida | `notebooks/modelos_t3.ipynb`, `docs/RESULTADOS_T3.md` |

> **Sobre los datos de ejemplo.** `data/dataset_sismico_peru_EJEMPLO.csv` contiene 14 NLTHA reales del modelo, pero con acelerogramas **sintéticos** e identificadores ficticios (`fuente = ilustrativo`). Sirve para probar el flujo; no es un resultado del estudio.

## Inicio rápido

```bash
git clone https://github.com/estebcueva/prediccion-respuesta-sismica-e030-ml.git
cd prediccion-respuesta-sismica-e030-ml
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 1. Verificar la integridad del dataset de ejemplo (18 controles)
python src/validar_integridad.py data/dataset_sismico_peru_EJEMPLO.csv

# 2. Reproducir el EDA
jupyter notebook notebooks/eda_t2.ipynb

# 2b. Validar el dataset real y reproducir los modelos de la T3 (~10 min)
pip install scikit-learn xgboost lightgbm shap
python src/validar_integridad.py data/dataset_sismico_peru.csv
jupyter notebook notebooks/modelos_t3.ipynb

# 3. (Opcional) Regenerar el catálogo y la matriz (~3 min)
python src/gen_catalogo.py && python src/gen_matriz.py

# 4. Con el flatfile y los .AT2 de PEER descargados:
python src/procesar_flatfile.py --flatfile data/NGA_West2_flatfile.csv --at2 data/at2
python src/campana_nltha.py --at2 data/at2 --arquetipos POR-07 --max-casos 4   # piloto
python src/campana_nltha.py --at2 data/at2 --procesos 32                       # campaña
python src/validar_integridad.py --estricto
```

La estructura completa está en [`ESTRUCTURA_REPO.md`](ESTRUCTURA_REPO.md).

## Documentación

| Documento | Contenido |
| --- | --- |
| [`docs/01_CATALOGO_ARQUETIPOS_ESTRUCTURALES.md`](docs/01_CATALOGO_ARQUETIPOS_ESTRUCTURALES.md) | Población de 40 edificios y parámetros E.030-2026 |
| [`docs/02_SELECCION_Y_ESCALAMIENTO_SISMICO.md`](docs/02_SELECCION_Y_ESCALAMIENTO_SISMICO.md) | Filtros NGA-West2, registros peruanos, escalamiento multinivel |
| [`docs/03_DICCIONARIO_DE_VARIABLES_Y_ESQUEMA_CSV.md`](docs/03_DICCIONARIO_DE_VARIABLES_Y_ESQUEMA_CSV.md) | 57 columnas, 31 features, targets, 13 reglas de integridad |
| [`docs/INFORME_T2_EDA_Y_PLAN_ML.md`](docs/INFORME_T2_EDA_Y_PLAN_ML.md) | Informe de la Entrega T2 |
| [`docs/RESULTADOS_T3.md`](docs/RESULTADOS_T3.md) | Resultados de la Entrega T3: métricas, criterios de aceptación, SHAP y limitaciones |
| [`docs/bitacora_prompts.md`](docs/bitacora_prompts.md) | Bitácora de transparencia en el uso de IA (T1–T3) |

## Resultados principales (T3)

| Target | Mejor modelo | R² en sismos no vistos | Error |
| --- | --- | --- | --- |
| ln(MIDR) | XGBoost | 0.823 | σln = 0.337 |
| Vb/W | Random Forest | 0.945 | RMSE = 0.053 |

El mejor modelo de deriva cumple 4 de los 5 criterios de aceptación fijados en el T2; no alcanza R² ≥ 0.85 en la prueba retenida. Detalle y limitaciones en [`docs/RESULTADOS_T3.md`](docs/RESULTADOS_T3.md).

## Verificaciones vigentes

- Los 40 arquetipos cumplen la deriva inelástica de diseño ≤ 0.007, la regla Ts < 0.65·TP y la clasificación E.030 del sistema por reparto de cortante (pórticos 0 %, duales 31–61 %, muros 86–98 % del cortante en muros).
- **Pendientes:** contrastar las Tablas 4 y 5 de la E.030-2026 con el PDF oficial; completar el Vs30 de las estaciones peruanas; validar en ETABS de 4 a 6 arquetipos.

## Uso de IA

Este repositorio se desarrolló con asistencia de un modelo de IA (Claude, de Anthropic). Los prompts, las sugerencias aceptadas y rechazadas, y la declaración de auditoría del grupo están en [`docs/bitacora_prompts.md`](docs/bitacora_prompts.md).
