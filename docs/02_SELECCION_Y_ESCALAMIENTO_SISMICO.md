# 02 — Selección y Escalamiento Sísmico

**Dataset:** Respuesta sísmica no lineal de edificaciones peruanas de concreto armado (E.030-2026 · PEER NGA-West2)
**Componente:** registros sísmicos (unidad muestral de demanda) y matriz experimental
**Archivos de datos asociados:** `registros_seleccionados.csv` (esquema, sección 2.6) · `matriz_combinaciones.csv` (16 000 filas) · `tabla_escalamiento.csv` (40 filas)
**Versión:** 1.0 · 1 de noviembre de 2026 · Ing. Rodrigo A. De la Cruz Herrera, CIP 325672

---

## 1. Flujo de datos

```text
Flatfile NGA-West2 (≈ 21 000 registros triaxiales)
  │ F1 Mw ≥ 6.0 · F2 10 ≤ Rrup ≤ 100 km · F3 350 ≤ Vs30 < 800 m/s
  │ F4 frecuencia utilizable · F5 sin pulso · F6 máx. 3 por evento
  ▼
Candidatos (pares horizontales)
  │ Selección estratificada por bins Mw × Rrup → 100 pares (≥ 34 eventos)
  ▼
registros_seleccionados.csv (slot R001–R100 ↔ RSN, EQID)
  │ espectros SRSS 5 % · IMs sin escalar
  ▼
Escalamiento por arquetipo: sf_base (ajuste log-LSQ al espectro E.030-2026
con R = 1 en [0.2·T1, 1.5·T1]) × λ ∈ {0.25, 0.50, 1.00, 1.50}
  ▼
matriz_combinaciones.csv: 40 × 100 × 4 = 16 000 casos NLTHA
  ▼
dataset_sismico_peru.csv (Archivo 03)

Validación externa (aparte, nunca se mezcla con entrenamiento):
CISMID / IGP: Lima 1966, Lima 1974, Pisco 2007 → 40 × N_pares × 4 casos
```

---

## 2. Filtrado del flatfile PEER NGA-West2

### 2.1 Criterios

| Filtro | Columna del flatfile | Condición | Justificación |
| --- | --- | --- | --- |
| F1 Magnitud | `Earthquake Magnitude` | Mw ≥ 6.0 | Eventos con energía y duración capaces de llevar a la estructura al rango inelástico |
| F2 Distancia | `ClstD (km)` | 10 ≤ Rrup ≤ 100 km | Campo lejano: excluye la directividad y los pulsos de campo cercano; el límite superior evita registros de amplitud muy baja que exigirían factores de escala grandes |
| F3 Suelo | `Vs30 (m/s) selected for analysis` | 350 ≤ Vs30 < 800 m/s | S1 ∪ S2 de la **E.030-2026** (Tabla 3): coherencia con el suelo de los arquetipos |
| F4 Frecuencia utilizable | `Lowest Usable Freq - Ave. Component (Hz)` | ≤ 0.25 Hz (mínimo obligatorio: ≤ 0.51 Hz) | El espectro debe ser confiable hasta $1.5\,T_{1,max} = 1.5 \times 1.30 = 1.95$ s, es decir 0.51 Hz. El umbral de 0.25 Hz (4 s) da margen para el alargamiento del periodo en el rango inelástico |
| F5 Pulsos | Lista de registros con pulso de velocidad | Excluir | Los pulsos son un mecanismo de demanda distinto (Shahi y Baker, 2014) |
| F6 Registros por evento | `EQID` | Máximo 3 por evento | Evita que eventos muy registrados (Chi-Chi, Northridge, Wenchuan) dominen el dataset y desbalanceen los grupos por evento |
| F7 Componentes | Archivos `.AT2` | Dos horizontales ortogonales con el mismo dt | La E.030-2026 exige las componentes simultáneas (art. 28.6) y el mismo factor para ambas (art. 47.5) |

**Asignación del perfil E.030-2026 a cada registro:**

| Vs30 de la estación (m/s) | Perfil |
| --- | --- |
| 550 – 800 | S1 |
| 350 – 550 | S2 |

Los registros de S1 en NGA-West2 son menos frecuentes que los de S2. Si la cuota de S1 no se llena, se acepta un reparto de hasta 35/65 y se documenta.

### 2.2 Selección de 100 pares por estratos

El filtro deja más candidatos que los necesarios. Los 100 pares se eligen por **muestreo estratificado** en bins de magnitud y distancia, con semilla fija, para cubrir el espacio sismológico de forma pareja.

**Cuotas objetivo (pares por bin):**

| Mw \ Rrup (km) | 10 – 30 | 30 – 60 | 60 – 100 | Total |
| --- | --- | --- | --- | --- |
| 6.0 – 6.5 | 9 | 9 | 7 | 25 |
| 6.5 – 7.0 | 11 | 13 | 11 | 35 |
| 7.0 – 7.5 | 6 | 10 | 9 | 25 |
| ≥ 7.5 | 4 | 6 | 5 | 15 |
| **Total** | **30** | **38** | **32** | **100** |

**Reglas dentro de cada bin:**

1. Priorizar eventos que aún no tengan registros seleccionados (diversidad de eventos).
2. Dentro de un evento, preferir estaciones con distancias distintas.
3. Si un bin no llena su cuota, el faltante pasa al bin vecino de distancia en la misma fila de magnitud.

**Mínimos de diversidad:** al menos 34 eventos distintos (100/3) y al menos 4 mecanismos de falla representados.

### 2.3 Partición por evento (fijada en la selección)

La partición se fija en el momento de la selección y se guarda como columna. Así ningún proceso posterior puede mezclar eventos entre conjuntos.

| Conjunto | Regla | Tamaño aproximado |
| --- | --- | --- |
| `train` | 80 % de los EQID, sorteo agrupado con semilla 2026 | ≈ 80 pares → ≈ 12 800 casos |
| `test` | 20 % de los EQID restantes | ≈ 20 pares → ≈ 3 200 casos |
| `valid_ext` | Registros peruanos de subducción (sección 3) | Fuera de los 16 000 |

Un mismo EQID nunca aparece en dos conjuntos.

### 2.4 Metadatos que se extraen por registro

| Campo del flatfile | Nombre en el dataset | Uso |
| --- | --- | --- |
| Record Sequence Number | `rsn` / `id_registro` | Clave del registro |
| EQID | `eqid` | Grupo de partición |
| Earthquake Name, YEAR | `evento`, `anio` | Trazabilidad |
| Earthquake Magnitude | `Mw` | Variable X |
| Mechanism Based on Rake Angle | `mecanismo` | Control de diversidad (0 rumbo, 1 normal, 2 inverso, 3 inverso-oblicuo, 4 normal-oblicuo) |
| ClstD (km) | `Rrup_km` | Variable X |
| Joyner-Boore Dist. (km) | `Rjb_km` | Trazabilidad |
| Vs30 (m/s) selected for analysis | `Vs30_est_ms` | Variable X y perfil |
| Lowest Usable Freq | `f_util_hz` | Control F4 |

### 2.5 Procesamiento

Los registros NGA-West2 ya vienen corregidos por PEER (línea base y filtrado). **No se vuelven a filtrar.** Se calculan:

- espectro de pseudoaceleración al 5 % por componente, en 150 periodos de 0.01 a 6 s (método exacto de Nigam y Jennings);
- espectro SRSS del par: $S_a^{SRSS}(T) = \sqrt{S_{a,1}^2 + S_{a,2}^2}$;
- medidas de intensidad sin escalar (definidas en el Archivo 03).

### 2.6 Esquema de `registros_seleccionados.csv`

| Columna | Tipo | Descripción |
| --- | --- | --- |
| `slot_registro` | texto | R001–R100: enlace con `matriz_combinaciones.csv` |
| `rsn` | entero | RSN de NGA-West2 |
| `eqid` | entero | Evento |
| `evento`, `anio` | texto, entero | Nombre y año del sismo |
| `Mw` | real | Magnitud de momento |
| `mecanismo` | entero | 0–4 |
| `Rrup_km`, `Rjb_km` | real | Distancias |
| `Vs30_est_ms` | real | Vs30 de la estación |
| `suelo_e030` | categórica | S1 / S2 (E.030-2026) |
| `f_util_hz` | real | Frecuencia mínima utilizable |
| `bin_Mw`, `bin_Rrup` | texto | Estrato de la selección |
| `archivo_h1`, `archivo_h2` | texto | Nombres de los `.AT2` horizontales |
| `dt_s`, `npts` | real, entero | Paso y número de puntos |
| `dominio` | texto | `NGA-West2` |
| `particion` | texto | `train` / `test` |

---

## 3. Catálogo de validación externa: acelerogramas peruanos de subducción

### 3.1 Por qué existe y cómo se usa

NGA-West2 solo contiene sismos **corticales**. La amenaza que controla el diseño en Lima es la **subducción interplaca**, con más duración y más ciclos de carga. Estos registros forman un conjunto separado (`dominio = Peru_subduccion`, `particion = valid_ext`): se procesan y escalan con el mismo procedimiento, pero **nunca entran en el entrenamiento**. Sirven para medir cuánto se degrada la predicción al cambiar de tipo de fuente.

### 3.2 Eventos

| EQID interno | Evento | Fecha | Mw | Fuente de Mw | Tipo |
| --- | --- | --- | --- | --- | --- |
| 9001 | Lima | 17-oct-1966 | 8.1 | Beck y Nishenko (1990) | Subducción interfase |
| 9002 | Lima | 03-oct-1974 | 8.1 | Beck y Nishenko (1990) | Subducción interfase |
| 9003 | Pisco | 15-ago-2007 | 8.0 | USGS | Subducción interfase |

Los EQID desde 9001 evitan choques con los de NGA-West2.

### 3.3 Estaciones y registros candidatos

**Lima 1966 y Lima 1974** (registros analógicos digitalizados):

| EQID | Estación | Institución | Componentes | PGA por componente (gal) | Fuente |
| --- | --- | --- | --- | --- | --- |
| 9001 | Parque de la Reserva (sede IGP, Av. Arequipa, Lima) | IGP | N08E, N82W, UP | N08E: 269.3 · N82W: 180.6 · UP: 94.25 | USGS OFR 77-587 |
| 9002 | Parque de la Reserva (sede IGP, Av. Arequipa, Lima) | IGP | N08E, N82W, UP | Completar desde la ficha digital | USGS OFR 77-587 |
| 9002 | Las Gardenias (residencia Huaco, Surco) | — | L, T, V | Completar desde la ficha digital | USGS OFR 77-587; CISMID |

**Pisco 2007** (red digital). Distancia = mínima al plano de falla (modelo de Ji y Zeng, 2007). Tipo de sitio = estimación de GEER.

| Estación | Institución | Ciudad | PGA NS (gal) | PGA EW (gal) | PGA (g) | Rrup (km) | Sitio (GEER) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Parcona | IGP | Ica | 455.0 | 488.0 | 0.498 | 39.4 | Suelo |
| ICA2 | CISMID | Ica (Universidad) | 334.1 | 272.3 | 0.341 | 36.7 | Suelo |
| Rinconada | CERESIS | Lima | 115.0 | 111.0 | 0.117 | 99.3 | Suelo |
| Callao | CISMID | Callao | 101.0 | 95.8 | 0.103 | 111.1 | Suelo |
| A. Nac. Rectores | CERESIS | Lima | 65.2 | 85.3 | 0.087 | 100.1 | Terreno firme |
| La Molina | CISMID | Lima | 69.1 | 78.7 | 0.080 | 96.8 | Suelo |
| Rímac | CISMID | Lima | 45.1 | 73.9 | 0.075 | 111.1 | Terreno firme |
| U. Católica | PUCP | Lima | 59.6 | 67.0 | 0.068 | 106.7 | Terreno firme |
| Mayorazgo | IGP | Lima | 59.7 | 55.0 | 0.061 | 103.0 | Suelo |
| San Isidro | CISMID | Lima | 58.8 | 54.1 | 0.060 | 103.7 | Terreno firme |
| Ceresis | CERESIS | Lima | 58.0 | 58.7 | 0.060 | 102.4 | Terreno firme |
| Ancón | IGP | Ancón | 54.7 | 58.4 | 0.060 | 137.5 | Suelo |
| E1 (Atarjea) | Sedapal | Lima | 50.0 | 54.9 | 0.056 | 106.2 | Suelo (en terraplén: excluir) |
| La Molina (LMO) | IGP | Lima | 21.2 | 25.3 | 0.026 | 100.3 | Roca |
| Ñaña (NNA) | IGP | Lima | 18.7 | 22.1 | 0.023 | 105.4 | Roca |
| E2 (Atarjea) | Sedapal | Lima | 12.7 | 20.6 | 0.021 | 105.9 | Roca |

"Terreno firme" corresponde al conglomerado de Lima (grava densa, ligeramente cementada).

### 3.4 Selección recomendada para la validación

| EQID | Registros | Pares | Criterio |
| --- | --- | --- | --- |
| 9001 | Parque de la Reserva | 1 | Único registro disponible |
| 9002 | Parque de la Reserva, Las Gardenias | 2 | Únicos registros disponibles |
| 9003 | ICA2, Parcona | 2 | Campo cercano a la fuente, PGA alta |
| 9003 | Rinconada, Callao, La Molina (CISMID), U. Católica, San Isidro | 5 | Lima a ~100 km, PGA ≥ 0.06 g, suelo o terreno firme |
| **Total** | | **10** | |

Combinaciones de validación: **40 arquetipos × 10 pares × 4 niveles = 1 600 casos.**

**Quedan excluidos** E1 (sobre un terraplén), las estaciones en roca con PGA < 0.03 g (LMO, NNA, E2), porque exigirían factores de escala > 10, y Ancón (Rrup > 100 km).

### 3.5 Datos a completar por registro peruano

El catálogo no inventa datos que no están verificados. Para cada registro se deben completar desde la ficha oficial (CISMID-UNI / REDACIS, IGP):

| Campo | Comentario |
| --- | --- |
| Vs30 de la estación | Desde estudios de microzonificación o medición. Sin Vs30, `suelo_e030` queda vacío y el caso se marca |
| Rrup de 1966 y 1974 | A calcular con el modelo de ruptura del evento |
| dt, número de puntos, unidades | Normalmente gal (cm/s²) |
| Corrección aplicada | Los registros crudos se corrigen: tendencia lineal + Butterworth pasa-banda de orden 4, 0.10–25 Hz, acausal |
| f_util | Los registros analógicos de 1966 y 1974 tienen una frecuencia utilizable mayor que los digitales: verificar que cubra $1.5\,T_1$ |

### 3.6 Advertencia sobre factores de escala

Los registros de Lima del sismo de Pisco 2007 tienen PGA entre 0.06 y 0.12 g. El objetivo E.030 al nivel 1.00 está entre 0.34 y 1.77 g en $S_a(T_1)$. Los factores base serán grandes (≈ 4 a 10) y varios superarán el rango [0.2, 5] (sección 4.4). En la prueba con un acelerograma sintético de tipo subducción (PGA 0.09 g), el factor base fue 4.81 para POR-07 y **6.14 para MUR-04** (fuera de rango). Esos casos se conservan con la marca `flag_sf_rango = 0` y se analizan por separado.

---

## 4. Matriz de escalamiento multinivel

### 4.1 Espectro objetivo

Para cada arquetipo $b$, el objetivo es el espectro E.030-2026 con R = 1 (Archivo 01, sección 7.5):

$$
S_a^{obj,b}(T) = Z\,U_b\,C_b(T)\,S_b
$$

### 4.2 Factor base por par y arquetipo

Se usa el mismo factor para ambas componentes (art. 47.5). Es el que mejor ajusta el SRSS al objetivo en la ventana normativa, por mínimos cuadrados en escala logarítmica:

$$
sf_{0}^{b,r} = \exp\!\left(\frac{1}{n}\sum_{T_j \in [0.2T_1^b,\ 1.5T_1^b]} \ln\frac{S_a^{obj,b}(T_j)}{S_a^{SRSS,r}(T_j)}\right)
$$

### 4.3 Niveles

$$
sf^{b,r,\lambda} = \lambda \cdot sf_0^{b,r}, \qquad \lambda \in \{0.25,\ 0.50,\ 1.00,\ 1.50\}
$$

| λ | Código | Interpretación | Rango de respuesta esperado |
| --- | --- | --- | --- |
| 0.25 | `L025` | Sismo frecuente (servicio) | Elástico |
| 0.50 | `L050` | Sismo ocasional | Inicio de fluencia |
| 1.00 | `L100` | Sismo de diseño E.030 (10 % en 50 años, R = 1) | Inelástico moderado |
| 1.50 | `L150` | Sismo raro / máximo considerado | Inelástico severo; posible colapso |

**Escalamiento de las IM.** Las IM se calculan una vez por par sin escalar y se escalan analíticamente, lo que es exacto porque el escalamiento en amplitud es lineal:

| IM | Exponente de sf |
| --- | --- |
| PGA, PGV, Sa(T1), Sa_avg, HI, ASI, CAV | 1 |
| Intensidad de Arias | 2 |
| D5-95 | 0 |

### 4.4 Control del factor de escala

| Condición | Marca | Tratamiento |
| --- | --- | --- |
| $0.2 \le sf_0 \le 5.0$ | `flag_sf_rango = 1` | Caso normal |
| $sf_0 < 0.2$ o $sf_0 > 5.0$ | `flag_sf_rango = 0` | Se corre y se guarda; el análisis decide si excluirlo |

Un factor muy grande distorsiona la relación entre amplitud, duración y contenido de frecuencias del registro original. Se marca en lugar de descartarlo, para que la matriz se mantenga completa (16 000 casos) y la decisión quede trazable.

### 4.5 Verificación normativa por arquetipo (art. 47.5)

Para cada arquetipo, al nivel λ = 1.00 y con los pares de entrenamiento:

$$
\overline{S_a^{SRSS}}(T) = \frac{1}{N}\sum_{r=1}^{N} sf_0^{b,r}\, S_a^{SRSS,r}(T) \ \ge\ S_a^{obj,b}(T), \qquad \forall\,T \in [0.2T_1^b,\ 1.5T_1^b]
$$

con N ≥ 7 pares (art. 47.1). Por cada arquetipo se reporta la razón mínima y el factor global adicional que haría cumplir el criterio. El ajuste log-LSQ deja el promedio aritmético algo por debajo del objetivo en algunos periodos; el factor adicional suele estar entre 1.1 y 1.3. Ese factor **no** se aplica a los 16 000 casos (que cubren un rango de intensidades); se usa solo para reportar un "sismo de diseño conforme" y compararlo con 1.25 × 0.007 (art. 49.2).

### 4.6 Objetivos espectrales por arquetipo y nivel

$S_a^{obj}(T_1)$ en g para cada nivel; la ventana es el rango donde se ajusta el factor. Es el objetivo del espectro **SRSS** del par. La IM `Sa_avg_g` del dataset (media geométrica de las componentes) queda en ≈ objetivo/√2 (Archivo 03, sección 3.4).

| ID     | Sistema   |   T1 (s) | Ventana 0.2T1–1.5T1 (s)   |   0.25× (g) |   0.50× (g) |   1.00× (g) |   1.50× (g) |
|:-------|:----------|---------:|:--------------------------|------------:|------------:|------------:|------------:|
| POR-01 | Pórticos  |    0.401 | 0.080–0.602               |       0.298 |       0.596 |       1.192 |       1.788 |
| POR-02 | Pórticos  |    0.422 | 0.084–0.633               |       0.266 |       0.532 |       1.065 |       1.598 |
| POR-03 | Pórticos  |    0.727 | 0.145–1.091               |       0.155 |       0.31  |       0.619 |       0.928 |
| POR-04 | Pórticos  |    0.483 | 0.097–0.724               |       0.303 |       0.606 |       1.212 |       1.818 |
| POR-05 | Pórticos  |    0.519 | 0.104–0.778               |       0.388 |       0.777 |       1.554 |       2.331 |
| POR-06 | Pórticos  |    0.517 | 0.103–0.776               |       0.218 |       0.436 |       0.871 |       1.306 |
| POR-07 | Pórticos  |    0.356 | 0.071–0.534               |       0.306 |       0.611 |       1.222 |       1.833 |
| POR-08 | Pórticos  |    0.545 | 0.109–0.818               |       0.318 |       0.636 |       1.271 |       1.906 |
| POR-09 | Pórticos  |    0.62  | 0.124–0.930               |       0.182 |       0.363 |       0.726 |       1.089 |
| POR-10 | Pórticos  |    0.64  | 0.128–0.960               |       0.176 |       0.352 |       0.703 |       1.054 |
| POR-11 | Pórticos  |    0.694 | 0.139–1.041               |       0.174 |       0.348 |       0.696 |       1.044 |
| POR-12 | Pórticos  |    0.578 | 0.116–0.867               |       0.235 |       0.47  |       0.939 |       1.408 |
| POR-13 | Pórticos  |    0.299 | 0.060–0.449               |       0.366 |       0.732 |       1.463 |       2.194 |
| DUA-01 | Dual      |    1.086 | 0.217–1.629               |       0.109 |       0.218 |       0.437 |       0.656 |
| DUA-02 | Dual      |    0.835 | 0.167–1.252               |       0.193 |       0.386 |       0.773 |       1.16  |
| DUA-03 | Dual      |    0.892 | 0.178–1.338               |       0.126 |       0.252 |       0.504 |       0.756 |
| DUA-04 | Dual      |    0.63  | 0.126–0.945               |       0.178 |       0.357 |       0.714 |       1.071 |
| DUA-05 | Dual      |    0.732 | 0.146–1.098               |       0.22  |       0.44  |       0.881 |       1.322 |
| DUA-06 | Dual      |    0.457 | 0.091–0.685               |       0.441 |       0.882 |       1.763 |       2.644 |
| DUA-07 | Dual      |    0.613 | 0.123–0.919               |       0.276 |       0.551 |       1.102 |       1.653 |
| DUA-08 | Dual      |    1.126 | 0.225–1.689               |       0.13  |       0.26  |       0.519 |       0.778 |
| DUA-09 | Dual      |    0.645 | 0.129–0.968               |       0.27  |       0.54  |       1.081 |       1.622 |
| DUA-10 | Dual      |    0.518 | 0.104–0.777               |       0.306 |       0.613 |       1.226 |       1.839 |
| DUA-11 | Dual      |    0.786 | 0.157–1.179               |       0.228 |       0.457 |       0.914 |       1.371 |
| DUA-12 | Dual      |    0.917 | 0.183–1.376               |       0.16  |       0.319 |       0.638 |       0.957 |
| DUA-13 | Dual      |    1.24  | 0.248–1.860               |       0.091 |       0.182 |       0.363 |       0.544 |
| DUA-14 | Dual      |    1.281 | 0.256–1.921               |       0.088 |       0.176 |       0.351 |       0.526 |
| MUR-01 | Muros     |    0.683 | 0.137–1.025               |       0.274 |       0.548 |       1.097 |       1.646 |
| MUR-02 | Muros     |    1.301 | 0.260–1.951               |       0.086 |       0.173 |       0.346 |       0.519 |
| MUR-03 | Muros     |    0.708 | 0.142–1.062               |       0.159 |       0.318 |       0.636 |       0.954 |
| MUR-04 | Muros     |    0.168 | 0.034–0.252               |       0.308 |       0.616 |       1.231 |       1.847 |
| MUR-05 | Muros     |    1.184 | 0.237–1.776               |       0.095 |       0.19  |       0.38  |       0.57  |
| MUR-06 | Muros     |    0.669 | 0.134–1.004               |       0.261 |       0.522 |       1.043 |       1.564 |
| MUR-07 | Muros     |    0.258 | 0.052–0.387               |       0.366 |       0.732 |       1.463 |       2.194 |
| MUR-08 | Muros     |    0.709 | 0.142–1.063               |       0.206 |       0.412 |       0.825 |       1.237 |
| MUR-09 | Muros     |    0.185 | 0.037–0.277               |       0.392 |       0.784 |       1.567 |       2.35  |
| MUR-10 | Muros     |    0.525 | 0.105–0.788               |       0.272 |       0.544 |       1.087 |       1.63  |
| MUR-11 | Muros     |    0.294 | 0.059–0.441               |       0.284 |       0.568 |       1.135 |       1.703 |
| MUR-12 | Muros     |    0.839 | 0.168–1.258               |       0.201 |       0.402 |       0.805 |       1.208 |
| MUR-13 | Muros     |    0.418 | 0.084–0.627               |       0.442 |       0.884 |       1.768 |       2.652 |

**Lectura.** En los arquetipos rígidos (T1 < TP) el objetivo está en la meseta $2.5\,Z\,U\,S$: 1.13–1.77 g a nivel de diseño. En los flexibles cae hasta 0.34 g (DUA-14, 15 pisos). El nivel 1.50 lleva los arquetipos A2 de muros hasta 2.65 g (MUR-13): son los casos con mayor probabilidad de colapso del dataset.

---

## 5. Generación de las 16 000 combinaciones

### 5.1 Diseño factorial completo

$$
N = N_{arq} \times N_{pares} \times N_{niveles} = 40 \times 100 \times 4 = 16\,000
$$

Cada combinación es un NLTHA bidireccional independiente, con las dos componentes horizontales simultáneas (art. 28.6).

**Clave del caso:**

```text
id_caso = {id_arquetipo}_R{rsn}_L{λ×100, 3 dígitos}_O{orientación}
ejemplo:  DUA-04_R001158_L100_O0
```

Antes de asignar los RSN, `matriz_combinaciones.csv` usa slots: `DUA-04_R042_L100`. La tabla `registros_seleccionados.csv` (slot → RSN) completa la clave.

### 5.2 Conteos

| Desglose | Casos |
| --- | --- |
| Pórticos (13 arquetipos) | 5 200 |
| Dual (14 arquetipos) | 5 600 |
| Muros (13 arquetipos) | 5 200 |
| Por nivel λ (cada uno) | 4 000 |
| Por par de registros (cada uno) | 160 |
| Por arquetipo (cada uno) | 400 |
| **Total entrenamiento + prueba** | **16 000** |
| Validación externa peruana (10 pares) | 1 600 |
| Opcional: rotación 0°/90° (componentes intercambiadas) | +16 000 → 32 000 |

### 5.3 Esquema de `matriz_combinaciones.csv`

| Columna | Tipo | Descripción |
| --- | --- | --- |
| `id_caso` | texto | Clave con slot (se reescribe con el RSN tras la selección) |
| `id_arquetipo` | texto | Enlace con el catálogo |
| `sistema` | categórica | Para conteos y estratificación |
| `slot_registro` | texto | R001–R100 |
| `nivel_escala` | real | λ |
| `T1_s` | real | Periodo del arquetipo |
| `T_ini_s`, `T_fin_s` | real | Ventana de escalamiento 0.2T1 y 1.5T1 |
| `Sa_obj_T1_g` | real | λ · Sa(T1) con R = 1 |

Primeras filas (archivo real):

```csv
id_caso,id_arquetipo,sistema,slot_registro,nivel_escala,T1_s,T_ini_s,T_fin_s,Sa_obj_T1_g
POR-01_R001_L025,POR-01,porticos,R001,0.25,0.401,0.08,0.602,0.298
POR-01_R001_L050,POR-01,porticos,R001,0.5,0.401,0.08,0.602,0.596
POR-01_R001_L100,POR-01,porticos,R001,1.0,0.401,0.08,0.602,1.192
POR-01_R001_L150,POR-01,porticos,R001,1.5,0.401,0.08,0.602,1.788
POR-01_R002_L025,POR-01,porticos,R002,0.25,0.401,0.08,0.602,0.298
```

### 5.4 Pérdidas esperadas y su registro

No todas las combinaciones producen una fila utilizable. Nada se borra: cada caso queda en el dataset con su marca.

| Situación | Marca en el dataset | ¿Entra al entrenamiento? |
| --- | --- | --- |
| Análisis completo | `convergencia = 1`, `colapso = 0` | Sí |
| Colapso (MIDR > 10 %, o no convergencia con MIDR ≥ 4 %) | `colapso = 1`, MIDR acotado a 0.10 | Sí para ln(MIDR); no para Vb/W |
| Falla numérica (no convergencia con MIDR < 4 %) | `convergencia = 0` | No |
| Factor de escala fuera de [0.2, 5] | `flag_sf_rango = 0` | A decidir y documentar |

### 5.5 Presupuesto de cómputo

En las pruebas, un caso tomó de 1.5 a 7.5 minutos en edificios de 3 a 6 pisos con registros de 15 s. Con registros reales de 20 a 60 s y edificios de hasta 15 pisos, se estiman unos 15 minutos de promedio: **≈ 4 000 horas-CPU** para los 16 000 casos (≈ 5 días en 32 núcleos). Conviene correr primero un piloto (4 arquetipos × 20 pares × 4 niveles = 320 casos) para medir el tiempo real y la tasa de fallas numéricas.

---

## Fuentes

1. Ancheta, T. D., et al. (2014). NGA-West2 database. *Earthquake Spectra*, 30(3), 989–1005. PEER Report 2013/03: https://peer.berkeley.edu/publications/2013-03
2. Shahi, S. K., y Baker, J. W. (2014). An efficient algorithm to identify strong-velocity pulses in multicomponent ground motions. *Bulletin of the Seismological Society of America*, 104(5), 2456–2466.
3. Beck, S. L., y Nishenko, S. P. (1990). Variations in the mode of great earthquake rupture along the Central Peru Subduction Zone. *Geophysical Research Letters*, 17(11). https://zenodo.org/record/1231396
4. U.S. Geological Survey (1977). *Strong-motion earthquake accelerograms digitization and analysis: records from Lima, Peru, 1951 to 1974*. Open-File Report 77-587. https://pubs.usgs.gov/of/1977/0587/report.pdf
5. GEER (2007). *Pisco, Peru Earthquake of August 15, 2007 — Seismology, Table 1: strong-motion stations*. https://geerassociation.org/components/com_geer_reports/geerfiles/Peru_2007/Seismology_Table1.htm
6. CISMID-UNI. *Sismo de Lima del 3 de octubre de 1974*. https://www.cismid.uni.edu.pe/wp-content/uploads/2024/10/SISMO-LIMA-74_.1.pdf
7. Nigam, N. C., y Jennings, P. C. (1969). Calculation of response spectra from strong-motion earthquake records. *BSSA*, 59(2), 909–922.
8. Ministerio de Vivienda (2026). RM 183-2026-VIVIENDA, E.030, arts. 28.6 y 47–49.
