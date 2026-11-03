# Bitácora de Transparencia en el Uso de IA

**Curso:** Aplicaciones de IA en Estructuras — UPC · **Docente:** Ing. Kurt Soncco Sinchi
**Proyecto:** Predicción de demandas sísmicas (ln MIDR y Vb/W) en edificaciones de concreto armado en el Perú — E.030-2026 · PEER NGA-West2
**Periodo cubierto:** 27 de octubre – 2 de noviembre de 2026 (Entregas T1 y T2)

---

## 1. Herramienta utilizada

| Campo | Detalle |
| --- | --- |
| Herramienta | Claude (Anthropic), interfaz de chat con ejecución de código, búsqueda web y archivos |
| Modelo | Sesión configurada con `claude-opus-5-5` |
| Usuario que operó la herramienta | Rodrigo Alonso De la Cruz Herrera (e202527672) |
| Uso | Búsqueda bibliográfica, revisión normativa, redacción técnica, generación y prueba de código Python/OpenSeesPy, generación del catálogo y de las matrices de datos |
| Ejecución del código | El asistente ejecutó y probó el código en un entorno aislado (Python 3.13, OpenSeesPy, pandas). Las salidas reportadas en los documentos son las de esas ejecuciones |

---

## 2. Registro de prompts

Se registran todos los prompts de la sesión en orden cronológico. Los prompts largos se reproducen en su parte sustantiva; el texto íntegro está en el historial de la conversación.

| N.° | Fecha y hora (Lima) | Prompt (resumen fiel o texto literal) | Producto obtenido |
| --- | --- | --- | --- |
| P1 | 27-oct 19:43 | «PEER NGA-West2 Ground Motion Database (Pacific Earthquake Engineering Research Center). Predicción de Demandas Sísmicas (Deriva Máxima de Entrepiso y Cortante Basal) en Edificaciones de Concreto Armado en el Perú mediante Algoritmos de Regresión Supervisada y la Base de Datos PEER NGA-West2 — buscame data de estos dos temas.» | Estado del arte: datos de NGA-West2, antecedentes de ML para deriva y cortante, antecedentes peruanos, advertencia cortical vs. subducción |
| P2 | 27-oct 19:44 | «Crea un Claude Doc a partir de tu última respuesta.» | Documento en línea (parcial) |
| P3 | 27-oct 19:45 | «dame el documento en archivo .md» | `estado-del-arte-nga-west2-ml.md` |
| P4 | 27-oct 19:46 | «dame data de: Aterrizar una idea de Machine Learning para predecir respuesta sísmica en edificaciones en Perú en base a la Norma E.030 y el dataset PEER NGA-West2» | Propuesta metodológica; detección de la modificación E.030 por la RM 183-2026-VIVIENDA |
| P5 | 27-oct 19:47 | «crea el documento y pasamelo en archivo .md» | `propuesta-ml-respuesta-sismica-e030-nga-west2.md` |
| P6 | 27-oct 19:50 | Texto pegado: «Observación Crítica para la Sustentación: Cortical vs. Subducción … Base Mixta (Recomendada) … Delimitación explícita …» | Estrategias de defensa ante el jurado: duración como feature, chequeo de dominio, opción NGA-Sub |
| P7 | 27-oct 19:54 | «Actúa como un Investigador Principal y PhD … genera la documentación técnica exhaustiva … 5 archivos .md independientes, sin resumir ni omitir detalles técnicos ni bloques de código Python/OpenSeesPy: 01 Planteamiento y marco normativo · 02 Generación de arquetipos OpenSeesPy · 03 Procesamiento de registros · 04 Pipeline ML y métricas · 05 Interpretabilidad SHAP e informe IEEE» | 5 documentos con 13 scripts probados; marco PCS; GroupKFold; SHAP |
| P8 | 01-nov 14:11 | «Actúa como un Especialista en Ingeniería de Datos Sísmicos y Estructurales. **No necesito que generes informes de sustentación, código de entrenamiento de Machine Learning ni plantillas de redacción.** Mi único objetivo es construir … una BASE DE DATOS … 3 archivos: 01 Catálogo de arquetipos (f'c = 210, 280 y 350 kg/cm²) · 02 Selección y escalamiento sísmico (16 000 combinaciones) · 03 Diccionario de variables y esquema CSV» | Catálogo de 40 arquetipos diseñados; matriz de 16 000 casos; esquema de 57 columnas; 14 filas de ejemplo con NLTHA |
| P9 | 02-nov 17:08 | «Actúa como un Investigador Principal … desarrolla formalmente los entregables de la SEGUNDA ENTREGA (T2 / TF2) … 6 bloques: estructura del repositorio, `validar_integridad.py`, notebook EDA, informe T2, bitácora de prompts, presentación de 4 diapositivas.» | Este repositorio, el informe T2, esta bitácora y la presentación |

---

## 3. Análisis crítico de las sugerencias de la IA

### 3.1 Sugerencias aceptadas

| Sugerencia de la IA | Motivo técnico de la aceptación | Dónde quedó |
| --- | --- | --- |
| Adoptar la **E.030-2026** (RM 183-2026-VIVIENDA) en lugar de la 2018 | Es la norma vigente desde mayo de 2026; cambia la clasificación de suelos (S, TP y TL interpolados con Vs30), exige Ts para categorías A y B en Z4 y el sismo bidireccional | `src/e030.py`, docs/01 |
| **Deformación por corte en muros** ($A_v = 5A/6$) y tramos de muro de máximo 8 m | Sin corte, los muros de 4 a 7 pisos daban T1 = 0.06–0.09 s, físicamente irreal. Con la corrección: 0.17–1.30 s. La verificación manual con la fórmula de voladizo flexión-corte coincidió con el modelo | `src/modelo_opensees.py` |
| **Recalibrar los duales** por reparto de cortante (31–61 % en muros) | La IA detectó que los "duales" con ρw = 0.5–1.5 % tenían 87–99 % del cortante en muros, es decir, eran sistemas de muros según la E.030. Se aceptó porque la etiqueta del sistema define R0 y, con ella, la demanda | `src/gen_catalogo.py`, docs/01 §5 |
| Predecir **ln(MIDR)** en lugar de MIDR | Distribución aproximadamente lognormal; dispersión homogénea; error interpretable como factor | docs/03, informe T2 |
| **GroupKFold por evento sísmico** | Evita la fuga de información del efecto del evento; la prueba numérica mostró un RMSE 32 % optimista con K-Fold aleatorio | Informe T2 §3.3 |
| Distinguir **colapso** de **falla numérica** | Una no convergencia con deriva de 0.0033 habría quedado como "colapso" con MIDR = 0.10, un dato falso. Ahora se marca `convergencia = 0` y se excluye | `modelo_opensees.py`, docs/03 |
| **Validación externa con subducción peruana**, separada del entrenamiento | Responde a la principal objeción metodológica: NGA-West2 solo tiene sismos corticales | docs/02 §3 |
| Usar el **T1 modal** (no $h_n/C_T$) para escalar | La fórmula subestima el periodo de los duales en un 44 % (mediana) | docs/01 §4 |

### 3.2 Sugerencias rechazadas o modificadas por el grupo

| Sugerencia de la IA | Decisión del grupo | Razón |
| --- | --- | --- |
| f'c en **5 clases** (210, 245, 280, 315, 350 kg/cm²) en la primera versión de los arquetipos (P7) | **Modificada:** 3 clases, 210 / 280 / 350 (P8) | Valores de uso estándar en la práctica peruana; balance más claro entre clases (14 / 12 / 14) |
| Entregar código de entrenamiento de ML, plantillas de informe IEEE y SHAP en la fase de datos (P7) | **Rechazada para la fase de datos** (P8: «No necesito … código de entrenamiento … ni plantillas») | El grupo priorizó construir y validar la base de datos antes de modelar; el entrenamiento se deja para la T3 |
| Excluir `factor_escala` de las features por ser una decisión del experimento y no una propiedad del sismo | **Modificada:** se mantiene en el esquema como metadato (P8); su uso como feature se decidirá con la prueba de estabilidad de la T3 | Es información trazable del experimento; el informe T2 la incluye solo en la variante "completa" de features |
| Conjunto de reglas de integridad R1–R13 (coherencia interna del CSV) | **Ampliada:** el grupo exigió controles de dominio físico (nulos, rango de Vb/W, R0 por sistema, ρw de duales, marca del factor de escala) | Se implementaron como D1–D5, además de R1–R13 (18 controles en total) |

### 3.3 Errores de la IA detectados durante el proceso

Se registran para que el docente y el grupo los consideren en la auditoría. Todos se detectaron y corrigieron con pruebas automáticas:

1. Solucionador de autovalores mal configurado con diafragma rígido (fallo de ARPACK): corregido.
2. Identificación incorrecta del periodo por dirección (masa efectiva mal normalizada): corregida.
3. Muros más largos que la planta en la primera versión del diseño automático: corregido.
4. Falso colapso por falla numérica en muros (rama de tracción del concreto muy rígida): corregido.
5. Dos afirmaciones de documentación corregidas tras verificar con los datos: el número de columnas del catálogo (41, no 42) y la relación entre `Sa_avg` y el objetivo E.030 (≈ objetivo/√2, porque el escalamiento se hace sobre el espectro SRSS).

### 3.4 Información que la IA no pudo verificar

| Dato | Estado | Responsable de cerrarlo |
| --- | --- | --- |
| Tablas 4 y 5 de la E.030-2026 (S, TP y TL) | Transcritas de un PDF con ruido en los encabezados | Grupo: contrastar con el PDF oficial |
| Vs30 de las estaciones peruanas (CISMID, IGP) | No figura en las fuentes consultadas | Grupo: estudios de microzonificación |
| PGA del registro de Lima 1974 | No reportada en las fuentes consultadas | Grupo: ficha digital del registro |
| Desempeño de los modelos de ML con datos reales | La campaña NLTHA no se ha ejecutado | T3 |

---

## 4. Declaración de autoría y auditoría técnica

El grupo declara que:

1. Las decisiones finales sobre el problema, el alcance del dataset y la norma aplicada son del grupo, incluida la aceptación o el rechazo de cada sugerencia de la sección 3.
2. Parte del código, de la redacción y de los cálculos se generó con asistencia de IA, como se detalla en las secciones 2 y 3.
3. Todo contenido generado por IA fue o será revisado por los integrantes antes de su entrega. Los valores numéricos del catálogo y de los ejemplos se obtuvieron ejecutando el código; no se escribieron a mano.
4. Las filas con `fuente = ilustrativo` provienen de acelerogramas sintéticos y no se presentan como resultados del estudio.
5. Ningún integrante presentará como propio un resultado que no haya entendido y verificado.

**Registro de auditoría.** Cada integrante marca lo que revisó personalmente, firma y fecha. Esta tabla la completa cada integrante; la IA no puede declarar auditorías en su nombre.

| Integrante | Código | Elementos revisados (marcar) | Firma | Fecha |
| --- | --- | --- | --- | --- |
| Paulino Antonio Díaz Hinostroza | e201572251 | ☐ Normativa E.030 ☐ Modelo OpenSees ☐ Datos/CSV ☐ EDA ☐ Informe | | |
| Rodrigo Alonso De la Cruz Herrera | e202527672 | ☐ Normativa E.030 ☐ Modelo OpenSees ☐ Datos/CSV ☐ EDA ☐ Informe | | |
| Guido Eduardo Valdez Tejeira | e202528480 | ☐ Normativa E.030 ☐ Modelo OpenSees ☐ Datos/CSV ☐ EDA ☐ Informe | | |
| Felix Mamani Huanca | e202527091 | ☐ Normativa E.030 ☐ Modelo OpenSees ☐ Datos/CSV ☐ EDA ☐ Informe | | |
| Johnny Esteban Cueva Moncada | e202527071 | ☐ Normativa E.030 ☐ Modelo OpenSees ☐ Datos/CSV ☐ EDA ☐ Informe | | |

**Verificaciones mínimas sugeridas para la auditoría:**

- [ ] Ejecutar `python src/validar_integridad.py data/dataset_sismico_peru_EJEMPLO.csv` y obtener 18/18 PASS.
- [ ] Ejecutar `python tests/test_validar_integridad.py` y obtener "Todas las pruebas negativas pasaron".
- [ ] Reejecutar `notebooks/eda_t2.ipynb` sin errores.
- [ ] Verificar a mano un arquetipo: T1 aproximado ($h_n/C_T$), W y C(T1) contra `catalogo_arquetipos.csv`.
- [ ] Contrastar una fila de la Tabla 4/5 de la E.030-2026 con el PDF oficial.
