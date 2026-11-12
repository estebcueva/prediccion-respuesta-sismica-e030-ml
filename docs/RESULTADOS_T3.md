# T3 — Resultados de los modelos de predicción

Curso Aplicaciones de IA en Estructuras (UPC) · Grupo: Díaz, De la Cruz, Valdez, Mamani, Cueva · 12/11/2026

**Resultado principal.** Con 1 410 NLTHA válidos, **XGBoost** predice ln(MIDR) en sismos no vistos con σln = 0.337 y R² = 0.823. **Random Forest** predice Vb/W con R² = 0.945 y RMSE = 0.053. El mejor modelo de deriva cumple 4 de los 5 criterios de aceptación fijados en el T2. El que no cumple es R² test ≥ 0.85, que quedó en 0.823.

Código y salidas: `notebooks/modelos_t3.ipynb` · métricas en `data/resultados_modelos_t3.json` · figuras en `docs/figuras/t3_*.png`.

## 1. Datos usados

| Concepto | Valor |
| --- | --- |
| Archivos unidos | `resultados_mitad1_delacruz.csv` (928), `resultados_mitad2_B_guido.csv` (324), `resultados_mitad2_A_paulino.csv` (93), `resultados_mitad2_C_felix.csv` (77) |
| Casos totales | 1 422 (`data/dataset_sismico_peru.csv`, columna `archivo_origen` para trazabilidad) |
| Validación de integridad | `src/validar_integridad.py`: 18/18 PASS (R1–R13, D1–D5) |
| Excluidos | 12 fallas numéricas (`convergencia = 0`); 0 colapsos |
| Casos modelados | 1 410: train 1 089 (11 eventos) · test 321 (3 eventos) |
| Arquetipos | 35 de 40; registros 22; eventos 14 |
| Variables de entrada | 29 (las 31 del diccionario menos `Z`, que es constante, y `factor_escala`, que es una decisión del analista) |

## 2. Metodología

- **Modelos:** Ridge log-lineal (línea base), Random Forest, XGBoost, LightGBM y red neuronal MLP (2–3 capas ocultas).
- **Preprocesamiento:** ln en las variables de escala y estandarización para Ridge y MLP. La MLP también estandariza el target. Los árboles usan las variables originales.
- **Hiperparámetros:** búsqueda aleatoria de 20 combinaciones por modelo, con GroupKFold(5) por `eqid` dentro de train.
- **Selección:** el modelo con menor RMSE de validación cruzada. El test se usa una sola vez, para reportar.
- **Cumplimiento:** se compara el MIDR predicho con 0.007 y 0.00875. La clase positiva es "no cumple", porque un falso "cumple" es el error inseguro.

**Desviaciones respecto del plan T2:** la búsqueda usa 20 combinaciones en vez de 30, la validación cruzada es simple (no anidada) y la MLP se hizo en scikit-learn en vez de PyTorch. Las tres se deben al tiempo de cómputo disponible.

## 3. Resultados — ln(MIDR)

| Modelo | R² CV | σln CV | R² test | σln test | MAPE test MIDR (%) | Brecha R² |
| --- | --- | --- | --- | --- | --- | --- |
| Ridge (base) | 0.836 | 0.277 | 0.699 | 0.440 | 30.1 | 0.138 |
| Random Forest | 0.834 | 0.279 | 0.788 | 0.368 | 27.6 | 0.046 |
| **XGBoost** | **0.843** | **0.271** | **0.823** | **0.337** | **25.5** | **0.020** |
| LightGBM | 0.839 | 0.275 | 0.793 | 0.364 | 27.1 | 0.045 |
| Red neuronal MLP | 0.812 | 0.296 | 0.678 | 0.454 | 29.4 | 0.134 |

En validación cruzada los cinco modelos quedan cerca: σln entre 0.27 y 0.30. En sismos nuevos, en cambio, los modelos de árboles generalizan mejor. Ridge y la MLP pierden más de 0.13 de R², porque su forma suave no capta bien la no linealidad intensidad–deriva que se vio en el EDA del T2.

## 4. Resultados — Vb/W

| Modelo | R² CV | RMSE CV | R² test | RMSE test | MAPE test (%) |
| --- | --- | --- | --- | --- | --- |
| Ridge (base) | 0.882 | 0.068 | 0.887 | 0.075 | 17.8 |
| **Random Forest** | **0.936** | **0.050** | **0.945** | **0.053** | **12.4** |
| XGBoost | 0.934 | 0.051 | 0.944 | 0.053 | 13.0 |
| LightGBM | 0.933 | 0.051 | 0.944 | 0.053 | 13.2 |
| Red neuronal MLP | 0.921 | 0.056 | 0.915 | 0.066 | 13.1 |

El cortante basal se predice mejor que la deriva, con R² de 0.94 en sismos nuevos. Los árboles representan la saturación de Vb/W por sistema (la sobrerresistencia) que el modelo lineal no capta.

## 5. Cumplimiento de deriva (XGBoost, test)

| Límite | Casos "no cumple" | Precisión | Recall | F1 | Falsos "cumple" (inseguros) | Falsos "no cumple" |
| --- | --- | --- | --- | --- | --- | --- |
| 0.007 | 151 | 0.909 | 0.861 | 0.884 | 21 | 13 |
| 0.00875 | 119 | 0.865 | 0.756 | 0.807 | 29 | 14 |

## 6. Criterios de aceptación (fijados en el T2)

| Criterio | Valor | ¿Cumple? |
| --- | --- | --- |
| R² test ln(MIDR) ≥ 0.85 | 0.823 | No |
| σln test ≤ 0.35 | 0.337 | Sí |
| F1 "no cumple" (0.007) ≥ 0.85 | 0.884 | Sí |
| Brecha R² CV − test ≤ 0.05 | 0.020 | Sí |
| El mejor modelo supera a Ridge | σln CV 0.271 vs 0.277 | Sí |

## 7. Interpretación (SHAP)

- **ln(MIDR):** las variables más influyentes son la intensidad de Housner (HI), T1, Sa_avg y PGA. La deriva crece con la intensidad y es menor en edificios rígidos (T1 bajo) y en los diseñados con mayor cortante (Vest/W alto) o mayor densidad de muros. Es el comportamiento físico esperado.
- **Vb/W:** dominan Sa_avg, Sa(T1), T1 y la demanda de diseño (Sa_dis, C_T1). El cortante sigue a la intensidad espectral cerca del periodo hasta que el sistema satura.
- Mw y Rrup aparecen en la deriva con peso moderado. Con solo 11 eventos de entrenamiento, pueden estar actuando en parte como "huella" del evento; debe verificarse con más sismos.

Figuras: `t3_pred_vs_real.png`, `t3_comparacion_modelos.png`, `t3_shap_midr.png`, `t3_shap_vbw.png`.

## 8. Limitaciones

1. **Campaña reducida.** Se tienen 1 422 de los 2 640 NLTHA previstos (54 %), con autorización del docente por el límite de memoria computacional.
2. **Arquetipos faltantes.** No hay resultados de DUA-04, DUA-10, MUR-01, MUR-03 ni POR-06, porque no se entregó la parte D. El modelo no se evalúa en ellos.
3. **Cobertura desigual.** Solo 3 de 35 arquetipos tienen sus 66 casos completos. Además, 7 de los 22 registros tienen 15 casos o menos, porque las corridas se cortaron antes de llegar a ellos. El modelo aprende más de los primeros registros del orden de corrida.
4. **Prueba pequeña.** El test tiene 3 eventos (321 casos), así que las métricas de test tienen alta varianza. El mismo modelo podría quedar por encima o por debajo de 0.85 con otros 3 sismos.
5. **Sesgo no conservador.** En el test, XGBoost subestima la deriva en los niveles altos (sesgo de ln −0.12 a 1.0× y −0.14 a 1.5×) y en pórticos (−0.20, es decir, ≈ 18 % menos deriva). Para uso práctico se necesitaría un factor de corrección o más datos en ese rango.
6. **Sin colapsos.** No hubo ningún colapso (MIDR máx. 5.8 %), así que el modelo no sirve para predecir colapso. Tampoco hay validación externa con sismos peruanos de subducción (`valid_ext`).
7. **Registros.** Se usó el set far-field de FEMA P695 en vez de la selección propia de NGA-West2. Solo 9 de 22 estaciones están en suelos S1/S2.

## 9. Conclusión

Un modelo sustituto con XGBoost estima la deriva máxima de entrepiso en sismos no vistos con un error típico de ≈ 34 % en escala logarítmica, y el cortante basal normalizado con R² ≈ 0.94. Esto basta para una evaluación preliminar rápida, no para diseño. El siguiente paso es completar la campaña (incluida la parte D y los registros con pocos casos) y repetir el entrenamiento con validación externa peruana.
