# 01 — Catálogo de Arquetipos Estructurales

**Dataset:** Respuesta sísmica no lineal de edificaciones peruanas de concreto armado (E.030-2026 · PEER NGA-West2)
**Componente:** población de edificios (unidad muestral estructural)
**Archivo de datos asociado:** `catalogo_arquetipos.csv` (40 filas × 41 columnas)
**Versión:** 1.0 · 1 de noviembre de 2026 · Ing. Rodrigo A. De la Cruz Herrera, CIP 325672

> **Origen de los números.** Todos los valores de este catálogo se calcularon, no se supusieron. La matriz se generó con muestreo estratificado de semilla fija (2026). Cada arquetipo se predimensionó y se rigidizó hasta cumplir la deriva de la E.030-2026, con un modelo elástico 3D en OpenSeesPy. El periodo T1 es modal, y el reparto del cortante entre muros y pórticos se verificó con un análisis estático. Los 40 arquetipos cumplen las tres condiciones de control (sección 7).

---

## 1. Resumen de la población

| Sistema | R0 | N | Pisos | ρw (%) | V en muros (%) | T1 modal (s) | W (MN) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Pórticos de CA | 8 | 13 | 3 – 8 | 0 | 0 | 0.30 – 0.73 | 8.0 – 44.3 |
| Dual | 7 | 14 | 6 – 15 | 0.23 – 0.82 | 31 – 61 | 0.46 – 1.28 | 14.4 – 109.6 |
| Muros estructurales | 6 | 13 | 4 – 15 | 1.12 – 2.88 | 86 – 98 | 0.17 – 1.30 | 21.2 – 73.3 |
| **Total** | | **40** | **3 – 15** | **0 – 2.88** | | **0.17 – 1.30** | **8.0 – 109.6** |

**Balance de los factores del diseño muestral:**

| Factor | Niveles | Conteo |
| --- | --- | --- |
| f'c (kg/cm²) | 210 / 280 / 350 | 14 / 12 / 14 |
| f'c por sistema | Pórticos · Dual · Muros | 5-4-4 · 5-4-5 · 4-4-5 |
| Categoría (U) | C (1.0) / B (1.3) / A2 (1.5) | 24 / 11 / 5 |
| Suelo E.030-2026 | S1 / S2 | 20 / 20 |
| Número de pisos | 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15 | 2, 3, 3, 5, 5, 4, 2, 3, 4, 2, 2, 3, 2 |
| Vanos en X | 3 / 4 / 5 | 11 / 14 / 15 |
| Vanos en Y | 3 / 4 / 5 | 10 / 19 / 11 |

---

## 2. Diseño de la matriz paramétrica

### 2.1 Variables y rangos

| Variable | Pórticos | Dual | Muros | Regla de muestreo |
| --- | --- | --- | --- | --- |
| Número de pisos | 3 – 8 | 6 – 15 | 4 – 15 | LHS, entero uniforme en el rango |
| Altura de entrepiso h | 2.70 – 3.50 m | ídem | ídem | LHS continuo, redondeo a 0.01 m |
| Vanos por dirección | 3 – 5 | 3 – 5 | 3 – 5 | Entero uniforme, independiente en X e Y |
| Luz de vano X | 4.0 – 7.0 m | ídem | ídem | LHS continuo |
| Luz de vano Y | $L_x \cdot U(0.85,\ 1.15)$, acotada a [4, 7] m | ídem | ídem | Plantas casi cuadradas en cada paño |
| f'c | {210, 280, 350} kg/cm² | ídem | ídem | LHS en 3 estratos (balance ±1) |
| Densidad de muros ρw | 0 | Salida de la calibración (sección 5) | 1.0 – 3.0 % | LHS continuo (muros) |
| Categoría de uso | C, B | C, B, A2 | C, B, A2 | Cuotas fijas por sistema, orden aleatorio |
| Suelo | S1 / S2 | ídem | ídem | LHS en 2 estratos; Vs30 uniforme dentro del perfil |
| Zona sísmica | Z4 | Z4 | Z4 | Fija |

**Densidad de muros** (por dirección):

$$
\rho_w = \frac{\sum_i L_{w,i}\, t_w}{A_{planta}}
$$

Cada dirección tiene la misma $\rho_w$ nominal. La longitud total se reparte en tramos simétricos de **8 m como máximo**, hasta dos por eje, y cada tramo mide a lo sumo el 40 % de la dimensión de planta paralela. El espesor base es $t_w = 0.25$ m; el diseño lo aumenta si hace falta (MUR-01 terminó con 0.30 m).

### 2.2 Restricciones normativas aplicadas al muestreo

| Restricción | Fuente | Efecto en la matriz |
| --- | --- | --- |
| Categoría A1 en Z4 exige aislamiento sísmico | E.030 (categoría y sistema estructural) | A1 excluida: no hay U = 1.5 en establecimientos de salud |
| Categoría A2 en Z4: concreto armado solo dual o muros | E.030, Tabla de categoría y sistema estructural (2018: Tabla 6) | Los 5 arquetipos A2 son dual (2) o muros (3); ningún pórtico es A2 |
| Pórticos de CA más altos son impracticables en Z4 con deriva 0.007 | Práctica de diseño; confirmado por el diseño automático | Pórticos limitados a 8 pisos |
| Plantas regulares | Alcance del estudio | $I_a = I_p = 1.0$; R = R0 |

---

## 3. Cargas y peso sísmico W

El peso sísmico sigue la regla de la E.030: carga muerta más un porcentaje de la carga viva que depende de la categoría (art. 26 de la versión 2018).

| Categoría | U | CM (kPa) | CV, E.020 (kPa) | % de CV en el peso | w por piso (kPa) |
| --- | --- | --- | --- | --- | --- |
| C (vivienda, oficinas) | 1.0 | 7.8 | 2.0 | 25 % | **8.30** |
| B (importantes: educación, etc.) | 1.3 | 7.8 | 2.5 | 50 % | **9.05** |
| A2 (esenciales, no hospitalarias) | 1.5 | 7.8 | 3.0 | 50 % | **9.30** |

$$
W = w \cdot A_{planta} \cdot n_{pisos}
$$

**CM = 7.8 kPa** agrupa la losa aligerada o maciza, los acabados, la tabiquería y el peso propio repartido de vigas, columnas y muros. Con esa CM, w queda en 8.3–9.3 kPa, alrededor de 0.85–0.95 tf/m², el orden de magnitud habitual en Lima.

**Simplificación declarada.** La azotea se toma con el mismo w que los pisos típicos. La E.030 permite 25 % de CV en azoteas, de modo que W queda sobreestimado entre 0.5 % y 3 % según el número de pisos.

---

## 4. Periodo fundamental T1

Se reportan dos estimaciones:

| Estimación | Fórmula / método | Columna |
| --- | --- | --- |
| Aproximada E.030 | $T = h_n / C_T$, con $C_T = 35$ en pórticos de CA y $C_T = 60$ en dual y muros (art. 28.4 de la versión 2018) | `T1_E030_s` |
| Modal | Modelo elástico 3D, secciones brutas, diafragma rígido, base empotrada; modo con mayor masa efectiva en cada dirección. Muros como elementos Timoshenko (flexión + corte, $A_v = 5A/6$) | `T1x_s`, `T1y_s` |
| **Valor del dataset** | $T_1 = \max(T_{1x},\ T_{1y})$ | `T1_s` |

**Cociente T1 modal / T1 E.030:**

| Sistema | Mínimo | Mediana | Máximo |
| --- | --- | --- | --- |
| Pórticos | 0.65 | 1.19 | 1.30 |
| Dual | 1.19 | 1.44 | 2.27 |
| Muros | 0.72 | 1.15 | 1.81 |

**Lectura.** La fórmula de la E.030 subestima el periodo de los duales, porque usa el mismo $C_T = 60$ que para muros cuando los pórticos aportan entre 39 % y 69 % de la rigidez. Para escalar los registros se usa siempre el **T1 modal**: el escalamiento se hace en el rango $[0.2T_1,\ 1.5T_1]$ del edificio real, no del de la fórmula.

**Por qué los muros incluyen corte.** En muros robustos ($H/L_w < 3$), la deformación por corte es comparable a la de flexión. Un modelo solo a flexión daba periodos de 0.06–0.09 s en edificios de muros de 4 a 7 pisos, valores físicamente irreales. Con corte incluido y tramos de 8 m como máximo, los edificios de muros de 4 a 7 pisos quedan en 0.17–0.29 s y los de 11 a 15 pisos en 0.67–1.30 s.

---

## 5. Clasificación del sistema por reparto de cortante

La E.030 define el sistema por el porcentaje del cortante basal que toman los muros:

| Sistema E.030 | Cortante en muros |
| --- | --- |
| Pórticos | ≤ 20 % (al menos 80 % en columnas) |
| Dual | Entre 20 % y 70 % |
| Muros estructurales | ≥ 70 % |

Se verificó con un análisis estático elástico en X, con la distribución de fuerzas en altura de la E.030, sumando las reacciones de la base de los muros frente a las totales (`pct_V_muros`).

**Calibración de los duales.** En una primera versión, los duales con ρw muestreada entre 0.5 % y 1.5 % dieron entre 87 % y 99 % de cortante en muros: eran sistemas de muros mal etiquetados. La versión final muestrea un **cortante objetivo en muros de 30 % a 60 %** y ajusta por bisección la longitud de los dos muros por dirección hasta alcanzarlo (tolerancia ±2 puntos). En los duales, ρw es una **salida** del diseño (0.23–0.82 %). Además, el control de deriva rigidiza primero el pórtico, para no desplazar el reparto.

**Resultado:** los 40 arquetipos quedan clasificados igual que su etiqueta (`sistema` = `sistema_por_V`). Pórticos: 0 %. Duales: 31–61 %. Muros: 86–98 %.

---

## 6. Tabla matricial de los 40 arquetipos

### 6.1 Geometría, materiales y reparto de cortante

| ID     | Sistema   |   R0 |   Pisos |   h (m) |   H (m) |   Vanos X |   Vanos Y |   Luz X (m) |   Luz Y (m) |   Planta (m²) |   f'c (kg/cm²) |   ρw (%) |   V muros (%) |
|:-------|:----------|-----:|--------:|--------:|--------:|----------:|----------:|------------:|------------:|--------------:|---------------:|---------:|--------------:|
| POR-01 | Pórticos  |    8 |       4 |    2.94 |   11.76 |         3 |         5 |        4.02 |        4    |         241.2 |            280 |     0    |           0   |
| POR-02 | Pórticos  |    8 |       4 |    2.87 |   11.48 |         4 |         3 |        6.93 |        6.9  |         573.8 |            210 |     0    |           0   |
| POR-03 | Pórticos  |    8 |       6 |    3.4  |   20.4  |         3 |         3 |        5.59 |        4.77 |         240   |            210 |     0    |           0   |
| POR-04 | Pórticos  |    8 |       6 |    2.98 |   17.88 |         5 |         5 |        6.08 |        5.37 |         816.2 |            280 |     0    |           0   |
| POR-05 | Pórticos  |    8 |       8 |    3.49 |   27.92 |         5 |         3 |        4.78 |        4.57 |         327.7 |            350 |     0    |           0   |
| POR-06 | Pórticos  |    8 |       5 |    3.13 |   15.65 |         4 |         4 |        5.88 |        6.58 |         619   |            280 |     0    |           0   |
| POR-07 | Pórticos  |    8 |       3 |    3.24 |    9.72 |         5 |         3 |        5.69 |        5.14 |         438.7 |            350 |     0    |           0   |
| POR-08 | Pórticos  |    8 |       8 |    3.27 |   26.16 |         4 |         4 |        5.05 |        5.16 |         416.9 |            210 |     0    |           0   |
| POR-09 | Pórticos  |    8 |       5 |    3.34 |   16.7  |         5 |         4 |        4.33 |        4.49 |         388.8 |            280 |     0    |           0   |
| POR-10 | Pórticos  |    8 |       6 |    3.08 |   18.48 |         4 |         4 |        4.63 |        4.49 |         332.6 |            210 |     0    |           0   |
| POR-11 | Pórticos  |    8 |       7 |    3.05 |   21.35 |         4 |         3 |        6.46 |        6.93 |         537.2 |            350 |     0    |           0   |
| POR-12 | Pórticos  |    8 |       7 |    2.7  |   18.9  |         3 |         3 |        5.16 |        5.92 |         274.9 |            350 |     0    |           0   |
| POR-13 | Pórticos  |    8 |       3 |    2.79 |    8.37 |         3 |         5 |        6.68 |        7    |         701.4 |            210 |     0    |           0   |
| DUA-01 | Dual      |    7 |      10 |    3.32 |   33.2  |         4 |         4 |        5.3  |        5.51 |         467.2 |            210 |     0.39 |          49.1 |
| DUA-02 | Dual      |    7 |      12 |    3.03 |   36.36 |         3 |         4 |        4.67 |        4.01 |         224.7 |            280 |     0.73 |          34   |
| DUA-03 | Dual      |    7 |       9 |    2.94 |   26.46 |         4 |         3 |        5.92 |        5.56 |         395   |            350 |     0.23 |          34.5 |
| DUA-04 | Dual      |    7 |       6 |    2.77 |   16.62 |         5 |         3 |        4.6  |        4.18 |         288.4 |            350 |     0.3  |          51.9 |
| DUA-05 | Dual      |    7 |      11 |    2.82 |   31.02 |         5 |         5 |        6.86 |        7    |        1200.5 |            280 |     0.27 |          35   |
| DUA-06 | Dual      |    7 |       7 |    3.24 |   22.68 |         5 |         5 |        5.98 |        6.33 |         946.3 |            210 |     0.34 |          31   |
| DUA-07 | Dual      |    7 |       7 |    3.49 |   24.43 |         4 |         4 |        6.76 |        5.93 |         641.4 |            280 |     0.43 |          61   |
| DUA-08 | Dual      |    7 |      14 |    3.37 |   47.18 |         3 |         4 |        6.3  |        6.71 |         507.3 |            280 |     0.55 |          41.6 |
| DUA-09 | Dual      |    7 |      10 |    3.15 |   31.5  |         4 |         5 |        6.56 |        6.42 |         842.3 |            210 |     0.4  |          50   |
| DUA-10 | Dual      |    7 |       8 |    3.19 |   25.52 |         5 |         4 |        4.14 |        4    |         331.2 |            350 |     0.51 |          43.2 |
| DUA-11 | Dual      |    7 |      13 |    3.05 |   39.65 |         4 |         4 |        4.9  |        5.49 |         430.4 |            350 |     0.74 |          40.6 |
| DUA-12 | Dual      |    7 |      14 |    2.7  |   37.8  |         4 |         5 |        4.37 |        4.83 |         422.1 |            210 |     0.82 |          46.1 |
| DUA-13 | Dual      |    7 |      11 |    3.41 |   37.51 |         3 |         3 |        5.17 |        5.18 |         241   |            350 |     0.49 |          53.9 |
| DUA-14 | Dual      |    7 |      15 |    2.91 |   43.65 |         4 |         5 |        5.7  |        5.25 |         598.5 |            210 |     0.4  |          32.8 |
| MUR-01 | Muros     |    6 |      13 |    2.93 |   38.09 |         3 |         5 |        4.78 |        5.43 |         389.3 |            350 |     1.49 |          87.8 |
| MUR-02 | Muros     |    6 |      14 |    3.08 |   43.12 |         5 |         4 |        4.24 |        4.05 |         343.4 |            280 |     1.12 |          86.9 |
| MUR-03 | Muros     |    6 |      11 |    2.73 |   30.03 |         4 |         4 |        5.38 |        5.98 |         514.8 |            210 |     1.36 |          86.2 |
| MUR-04 | Muros     |    6 |       5 |    2.81 |   14.05 |         3 |         4 |        6.84 |        6.22 |         510.5 |            210 |     2.26 |          96.4 |
| MUR-05 | Muros     |    6 |      15 |    3.26 |   48.9  |         4 |         4 |        6.51 |        5.65 |         588.5 |            210 |     1.99 |          87.2 |
| MUR-06 | Muros     |    6 |      11 |    3.18 |   34.98 |         5 |         4 |        6.05 |        5.29 |         640.1 |            350 |     2.54 |          95.8 |
| MUR-07 | Muros     |    6 |       6 |    3.2  |   19.2  |         5 |         4 |        5.13 |        5.66 |         580.7 |            280 |     2.88 |          97.9 |
| MUR-08 | Muros     |    6 |      10 |    2.85 |   28.5  |         3 |         5 |        4.22 |        4.19 |         265.2 |            350 |     1.79 |          92.6 |
| MUR-09 | Muros     |    6 |       4 |    3.36 |   13.44 |         5 |         4 |        5.64 |        5.29 |         596.7 |            350 |     1.62 |          98   |
| MUR-10 | Muros     |    6 |       8 |    3.41 |   27.28 |         5 |         4 |        6.3  |        6.72 |         846.7 |            350 |     1.3  |          94   |
| MUR-11 | Muros     |    6 |       7 |    3.02 |   21.14 |         5 |         3 |        6.65 |        6.96 |         694.3 |            210 |     2.71 |          94   |
| MUR-12 | Muros     |    6 |      12 |    3.46 |   41.52 |         3 |         5 |        4.59 |        4.67 |         321.5 |            280 |     2.22 |          93.6 |
| MUR-13 | Muros     |    6 |       9 |    3    |   27    |         5 |         4 |        5.56 |        5.48 |         609.4 |            280 |     2.61 |          95.5 |

### 6.2 Secciones de diseño, peso y parámetros dinámicos

`Muros X = 2x3.7` significa 2 tramos de muro alineados con X, de 3.7 m cada uno. La deriva de diseño es la inelástica E.030 ($0.75\,R\,\Delta_{el}$, método estático con T1 modal).

| ID     |   Columna (m) | Viga b×h (m)   | Muros X (n×Lw m)   | Muros Y (n×Lw m)   | tw (m)   | Cat.   |   U |   w (kPa) | W (kN)   |   T1 E.030 (s) |   T1x modal (s) |   T1y modal (s) |   T1 (s) |   Deriva diseño |
|:-------|--------------:|:---------------|:-------------------|:-------------------|:---------|:-------|----:|----------:|:---------|---------------:|----------------:|----------------:|---------:|----------------:|
| POR-01 |          0.5  | 0.25x0.50      | -                  | -                  | -        | C      | 1   |      8.3  | 8 008    |          0.336 |           0.401 |           0.386 |    0.401 |          0.0062 |
| POR-02 |          0.65 | 0.35x0.75      | -                  | -                  | -        | C      | 1   |      8.3  | 19 050   |          0.328 |           0.414 |           0.422 |    0.422 |          0.0063 |
| POR-03 |          0.55 | 0.30x0.65      | -                  | -                  | -        | C      | 1   |      8.3  | 11 951   |          0.583 |           0.727 |           0.698 |    0.727 |          0.0065 |
| POR-04 |          0.75 | 0.30x0.80      | -                  | -                  | -        | B      | 1.3 |      9.05 | 44 322   |          0.511 |           0.483 |           0.464 |    0.483 |          0.0063 |
| POR-05 |          0.95 | 0.25x0.80      | -                  | -                  | -        | B      | 1.3 |      9.05 | 23 723   |          0.798 |           0.501 |           0.519 |    0.519 |          0.0064 |
| POR-06 |          0.65 | 0.30x0.75      | -                  | -                  | -        | C      | 1   |      8.3  | 25 690   |          0.447 |           0.499 |           0.517 |    0.517 |          0.0059 |
| POR-07 |          0.5  | 0.30x0.65      | -                  | -                  | -        | C      | 1   |      8.3  | 10 924   |          0.278 |           0.353 |           0.356 |    0.356 |          0.0053 |
| POR-08 |          1.2  | 0.25x0.80      | -                  | -                  | -        | B      | 1.3 |      9.05 | 30 186   |          0.747 |           0.541 |           0.545 |    0.545 |          0.0062 |
| POR-09 |          0.5  | 0.25x0.55      | -                  | -                  | -        | C      | 1   |      8.3  | 16 137   |          0.477 |           0.605 |           0.62  |    0.62  |          0.0066 |
| POR-10 |          0.55 | 0.25x0.60      | -                  | -                  | -        | C      | 1   |      8.3  | 16 564   |          0.528 |           0.64  |           0.634 |    0.64  |          0.0063 |
| POR-11 |          0.65 | 0.35x0.75      | -                  | -                  | -        | C      | 1   |      8.3  | 31 212   |          0.61  |           0.661 |           0.694 |    0.694 |          0.0065 |
| POR-12 |          0.55 | 0.30x0.70      | -                  | -                  | -        | C      | 1   |      8.3  | 15 973   |          0.54  |           0.557 |           0.578 |    0.578 |          0.0068 |
| POR-13 |          0.65 | 0.35x0.80      | -                  | -                  | -        | B      | 1.3 |      9.05 | 19 043   |          0.239 |           0.299 |           0.293 |    0.299 |          0.0054 |
| DUA-01 |          0.7  | 0.30x0.60      | 2x3.7              | 2x3.7              | 0.25     | C      | 1   |      8.3  | 38 782   |          0.553 |           1.074 |           1.086 |    1.086 |          0.007  |
| DUA-02 |          0.85 | 0.25x0.65      | 2x3.3              | 2x3.3              | 0.25     | B      | 1.3 |      9.05 | 24 405   |          0.606 |           0.835 |           0.771 |    0.835 |          0.0067 |
| DUA-03 |          0.55 | 0.30x0.65      | 2x1.9              | 2x1.9              | 0.25     | C      | 1   |      8.3  | 29 505   |          0.441 |           0.883 |           0.892 |    0.892 |          0.0066 |
| DUA-04 |          0.4  | 0.25x0.50      | 2x1.8              | 2x1.8              | 0.25     | C      | 1   |      8.3  | 14 363   |          0.277 |           0.622 |           0.63  |    0.63  |          0.0069 |
| DUA-05 |          1.05 | 0.35x0.80      | 2x7.4              | 2x7.4              | 0.25     | C      | 1   |      8.3  | 109 606  |          0.517 |           0.728 |           0.732 |    0.732 |          0.0066 |
| DUA-06 |          1.25 | 0.30x0.80      | 2x8.0              | 4x8.0              | 0.25     | A2     | 1.5 |      9.3  | 61 606   |          0.378 |           0.457 |           0.407 |    0.457 |          0.0067 |
| DUA-07 |          0.75 | 0.35x0.75      | 2x5.6              | 2x5.6              | 0.25     | A2     | 1.5 |      9.3  | 41 754   |          0.407 |           0.613 |           0.594 |    0.613 |          0.007  |
| DUA-08 |          1.05 | 0.35x0.80      | 2x5.7              | 2x5.7              | 0.25     | B      | 1.3 |      9.05 | 64 272   |          0.786 |           1.126 |           1.112 |    1.126 |          0.0065 |
| DUA-09 |          1.25 | 0.30x0.75      | 4x8.0              | 4x8.0              | 0.25     | C      | 1   |      8.3  | 69 911   |          0.525 |           0.645 |           0.635 |    0.645 |          0.0064 |
| DUA-10 |          0.65 | 0.25x0.65      | 2x3.4              | 2x3.4              | 0.25     | C      | 1   |      8.3  | 21 992   |          0.425 |           0.513 |           0.518 |    0.518 |          0.0054 |
| DUA-11 |          1.05 | 0.25x0.75      | 2x6.4              | 2x6.4              | 0.25     | B      | 1.3 |      9.05 | 50 638   |          0.661 |           0.761 |           0.786 |    0.786 |          0.0064 |
| DUA-12 |          0.95 | 0.25x0.60      | 2x6.9              | 2x6.9              | 0.25     | B      | 1.3 |      9.05 | 53 485   |          0.63  |           0.907 |           0.917 |    0.917 |          0.0065 |
| DUA-13 |          0.55 | 0.25x0.60      | 2x2.4              | 2x2.4              | 0.25     | C      | 1   |      8.3  | 22 006   |          0.625 |           1.24  |           1.24  |    1.24  |          0.0067 |
| DUA-14 |          0.95 | 0.30x0.65      | 2x4.8              | 2x4.8              | 0.25     | C      | 1   |      8.3  | 74 513   |          0.728 |           1.281 |           1.222 |    1.281 |          0.0062 |
| MUR-01 |          0.9  | 0.25x0.50      | 12x5.7             | 6x8.0              | 0.30     | A2     | 1.5 |      9.3  | 47 070   |          0.635 |           0.683 |           0.611 |    0.683 |          0.0068 |
| MUR-02 |          0.55 | 0.25x0.40      | 2x7.7              | 4x5.2              | 0.25     | C      | 1   |      8.3  | 39 908   |          0.719 |           1.16  |           1.301 |    1.301 |          0.0067 |
| MUR-03 |          0.65 | 0.30x0.55      | 4x7.1              | 4x7.1              | 0.25     | C      | 1   |      8.3  | 46 997   |          0.501 |           0.697 |           0.708 |    0.708 |          0.005  |
| MUR-04 |          0.5  | 0.35x0.65      | 6x7.7              | 6x7.7              | 0.25     | C      | 1   |      8.3  | 21 187   |          0.234 |           0.168 |           0.164 |    0.168 |          0.001  |
| MUR-05 |          0.8  | 0.30x0.60      | 6x7.9              | 6x7.9              | 0.25     | C      | 1   |      8.3  | 73 269   |          0.815 |           1.184 |           1.152 |    1.184 |          0.0055 |
| MUR-06 |          0.5  | 0.30x0.55      | 10x6.6             | 10x6.6             | 0.25     | C      | 1   |      8.3  | 58 440   |          0.583 |           0.669 |           0.666 |    0.669 |          0.0066 |
| MUR-07 |          0.4  | 0.30x0.55      | 10x6.7             | 10x6.7             | 0.25     | B      | 1.3 |      9.05 | 31 533   |          0.32  |           0.257 |           0.258 |    0.258 |          0.0022 |
| MUR-08 |          0.45 | 0.25x0.40      | 4x5.0              | 4x5.6              | 0.25     | B      | 1.3 |      9.05 | 24 003   |          0.475 |           0.709 |           0.622 |    0.709 |          0.007  |
| MUR-09 |          0.35 | 0.30x0.55      | 6x6.5              | 6x6.5              | 0.25     | B      | 1.3 |      9.05 | 21 601   |          0.224 |           0.185 |           0.18  |    0.185 |          0.0015 |
| MUR-10 |          0.5  | 0.35x0.65      | 6x7.4              | 6x7.4              | 0.25     | C      | 1   |      8.3  | 56 222   |          0.455 |           0.525 |           0.52  |    0.525 |          0.005  |
| MUR-11 |          0.65 | 0.35x0.65      | 8x8.0              | 10x7.6             | 0.25     | C      | 1   |      8.3  | 40 337   |          0.352 |           0.294 |           0.286 |    0.294 |          0.0021 |
| MUR-12 |          0.7  | 0.25x0.45      | 12x5.5             | 4x8.0              | 0.25     | A2     | 1.5 |      9.3  | 35 883   |          0.692 |           0.839 |           0.826 |    0.839 |          0.007  |
| MUR-13 |          0.55 | 0.30x0.55      | 8x8.0              | 8x8.0              | 0.25     | A2     | 1.5 |      9.3  | 51 005   |          0.45  |           0.418 |           0.418 |    0.418 |          0.0054 |

### 6.3 Parámetros normativos E.030-2026 por arquetipo

| ID     | Suelo   |   Vs30 (m/s) |     S |   TP (s) |   TL (s) |   Ts ref. (s) |   0.65·TP (s) | Ts exigido   |    Z |   U |   C(T1) |   Sa R=1 (g) |   V/W diseño |
|:-------|:--------|-------------:|------:|---------:|---------:|--------------:|--------------:|:-------------|-----:|----:|--------:|-------------:|-------------:|
| POR-01 | S2      |          431 | 1.06  |    0.519 |    2.203 |         0.278 |         0.337 | No           | 0.45 | 1   |   2.5   |        1.192 |       0.149  |
| POR-02 | S1      |          672 | 1     |    0.4   |    2.5   |         0.179 |         0.26  | No           | 0.45 | 1   |   2.367 |        1.065 |       0.1331 |
| POR-03 | S1      |          799 | 1     |    0.4   |    2.5   |         0.15  |         0.26  | No           | 0.45 | 1   |   1.375 |        0.619 |       0.0774 |
| POR-04 | S1      |          661 | 1     |    0.4   |    2.5   |         0.182 |         0.26  | Sí           | 0.45 | 1.3 |   2.071 |        1.212 |       0.1514 |
| POR-05 | S2      |          425 | 1.062 |    0.525 |    2.188 |         0.282 |         0.341 | Sí           | 0.45 | 1.3 |   2.5   |        1.554 |       0.1942 |
| POR-06 | S1      |          741 | 1     |    0.4   |    2.5   |         0.162 |         0.26  | No           | 0.45 | 1   |   1.936 |        0.871 |       0.1089 |
| POR-07 | S2      |          378 | 1.086 |    0.572 |    2.07  |         0.317 |         0.372 | No           | 0.45 | 1   |   2.5   |        1.222 |       0.1527 |
| POR-08 | S2      |          490 | 1.03  |    0.46  |    2.35  |         0.245 |         0.299 | Sí           | 0.45 | 1.3 |   2.11  |        1.271 |       0.1589 |
| POR-09 | S1      |          744 | 1     |    0.4   |    2.5   |         0.161 |         0.26  | No           | 0.45 | 1   |   1.613 |        0.726 |       0.0907 |
| POR-10 | S1      |          586 | 1     |    0.4   |    2.5   |         0.205 |         0.26  | No           | 0.45 | 1   |   1.562 |        0.703 |       0.0879 |
| POR-11 | S2      |          526 | 1.012 |    0.424 |    2.44  |         0.228 |         0.276 | No           | 0.45 | 1   |   1.528 |        0.696 |       0.087  |
| POR-12 | S2      |          483 | 1.034 |    0.467 |    2.333 |         0.248 |         0.304 | No           | 0.45 | 1   |   2.018 |        0.939 |       0.1173 |
| POR-13 | S1      |          603 | 1     |    0.4   |    2.5   |         0.199 |         0.26  | Sí           | 0.45 | 1.3 |   2.5   |        1.463 |       0.1828 |
| DUA-01 | S2      |          532 | 1.009 |    0.418 |    2.455 |         0.226 |         0.272 | No           | 0.45 | 1   |   0.962 |        0.437 |       0.0624 |
| DUA-02 | S2      |          516 | 1.017 |    0.434 |    2.415 |         0.233 |         0.282 | Sí           | 0.45 | 1.3 |   1.3   |        0.773 |       0.1105 |
| DUA-03 | S1      |          755 | 1     |    0.4   |    2.5   |         0.159 |         0.26  | No           | 0.45 | 1   |   1.121 |        0.504 |       0.072  |
| DUA-04 | S1      |          586 | 1     |    0.4   |    2.5   |         0.205 |         0.26  | No           | 0.45 | 1   |   1.586 |        0.714 |       0.102  |
| DUA-05 | S2      |          413 | 1.069 |    0.537 |    2.158 |         0.291 |         0.349 | No           | 0.45 | 1   |   1.833 |        0.881 |       0.1259 |
| DUA-06 | S2      |          461 | 1.044 |    0.489 |    2.277 |         0.26  |         0.318 | Sí           | 0.45 | 1.5 |   2.5   |        1.763 |       0.2518 |
| DUA-07 | S1      |          791 | 1     |    0.4   |    2.5   |         0.152 |         0.26  | Sí           | 0.45 | 1.5 |   1.632 |        1.102 |       0.1574 |
| DUA-08 | S1      |          669 | 1     |    0.4   |    2.5   |         0.179 |         0.26  | Sí           | 0.45 | 1.3 |   0.888 |        0.519 |       0.0742 |
| DUA-09 | S2      |          379 | 1.086 |    0.571 |    2.072 |         0.317 |         0.371 | No           | 0.45 | 1   |   2.213 |        1.081 |       0.1544 |
| DUA-10 | S2      |          370 | 1.09  |    0.58  |    2.05  |         0.324 |         0.377 | No           | 0.45 | 1   |   2.5   |        1.226 |       0.1752 |
| DUA-11 | S2      |          476 | 1.037 |    0.474 |    2.315 |         0.252 |         0.308 | Sí           | 0.45 | 1.3 |   1.507 |        0.914 |       0.1306 |
| DUA-12 | S1      |          706 | 1     |    0.4   |    2.5   |         0.17  |         0.26  | Sí           | 0.45 | 1.3 |   1.091 |        0.638 |       0.0911 |
| DUA-13 | S1      |          655 | 1     |    0.4   |    2.5   |         0.183 |         0.26  | No           | 0.45 | 1   |   0.806 |        0.363 |       0.0518 |
| DUA-14 | S1      |          593 | 1     |    0.4   |    2.5   |         0.202 |         0.26  | No           | 0.45 | 1   |   0.781 |        0.351 |       0.0502 |
| MUR-01 | S2      |          514 | 1.018 |    0.436 |    2.41  |         0.233 |         0.283 | Sí           | 0.45 | 1.5 |   1.597 |        1.097 |       0.1829 |
| MUR-02 | S1      |          559 | 1     |    0.4   |    2.5   |         0.215 |         0.26  | No           | 0.45 | 1   |   0.768 |        0.346 |       0.0576 |
| MUR-03 | S1      |          637 | 1     |    0.4   |    2.5   |         0.188 |         0.26  | No           | 0.45 | 1   |   1.413 |        0.636 |       0.106  |
| MUR-04 | S2      |          362 | 1.094 |    0.588 |    2.03  |         0.331 |         0.382 | No           | 0.45 | 1   |   2.5   |        1.231 |       0.2051 |
| MUR-05 | S1      |          752 | 1     |    0.4   |    2.5   |         0.16  |         0.26  | No           | 0.45 | 1   |   0.845 |        0.38  |       0.0634 |
| MUR-06 | S2      |          379 | 1.086 |    0.571 |    2.072 |         0.317 |         0.371 | No           | 0.45 | 1   |   2.134 |        1.043 |       0.1738 |
| MUR-07 | S1      |          615 | 1     |    0.4   |    2.5   |         0.195 |         0.26  | Sí           | 0.45 | 1.3 |   2.5   |        1.463 |       0.2438 |
| MUR-08 | S1      |          706 | 1     |    0.4   |    2.5   |         0.17  |         0.26  | Sí           | 0.45 | 1.3 |   1.411 |        0.825 |       0.1376 |
| MUR-09 | S2      |          407 | 1.072 |    0.543 |    2.143 |         0.295 |         0.353 | Sí           | 0.45 | 1.3 |   2.5   |        1.567 |       0.2612 |
| MUR-10 | S2      |          464 | 1.043 |    0.486 |    2.285 |         0.259 |         0.316 | No           | 0.45 | 1   |   2.315 |        1.087 |       0.1811 |
| MUR-11 | S2      |          533 | 1.008 |    0.417 |    2.458 |         0.225 |         0.271 | No           | 0.45 | 1   |   2.5   |        1.135 |       0.1891 |
| MUR-12 | S1      |          674 | 1     |    0.4   |    2.5   |         0.178 |         0.26  | Sí           | 0.45 | 1.5 |   1.192 |        0.805 |       0.1341 |
| MUR-13 | S2      |          455 | 1.048 |    0.495 |    2.263 |         0.264 |         0.322 | Sí           | 0.45 | 1.5 |   2.5   |        1.768 |       0.2946 |

---

## 7. Parámetros normativos E.030-2026 aplicados

Referencia: Norma E.030 modificada por la **RM 183-2026-VIVIENDA** (28-abr-2026; publicada en El Peruano el 3-may-2026).

> **Verificación pendiente.** Las Tablas 4 (S) y 5 (TP, TL) se transcribieron de una extracción del PDF con ruido en los encabezados de columna. La lectura adoptada es coherente con el texto del artículo y da continuidad entre perfiles (S, TP y TL coinciden en los bordes S1/S2 y S2/S3). Antes de usar el dataset en la tesis, conviene contrastar las dos tablas con el PDF oficial.

### 7.1 Zonificación

| Parámetro | Valor | Nota |
| --- | --- | --- |
| Zona | Z4 (costa: Lima, Callao, Ica) | Fija en los 40 arquetipos |
| Z | 0.45 g | PGA en suelo rígido, 10 % de excedencia en 50 años. **Constante en el dataset** |

### 7.2 Factor de uso U

| Categoría | U | Arquetipos | Sistemas admitidos en Z4 (CA) |
| --- | --- | --- | --- |
| A1 (salud) | 1.5 + aislamiento | 0 | Exige aislamiento: fuera de alcance |
| A2 (esenciales) | 1.5 | 5 | Dual, muros |
| B (importantes) | 1.3 | 11 | Pórticos, dual, muros |
| C (comunes) | 1.0 | 24 | Pórticos, dual, muros |

### 7.3 Perfiles de suelo S1 y S2 (E.030-2026, Tabla 3)

| Perfil | Vs30 (m/s) | N60 | Su (kPa) | Arquetipos | Vs30 muestreado (m/s) |
| --- | --- | --- | --- | --- | --- |
| S1 — roca o suelo muy rígido | 550 – 800 | > 50 | > 100 | 20 | 559 – 799 |
| S2 — suelo intermedio | 350 – 550 | 30 – 50 | 80 – 100 | 20 | 362 – 533 |

### 7.4 Factor S y periodos TP, TL en Z4

| Perfil | S | TP (s) | TL (s) |
| --- | --- | --- | --- |
| S1 | 1.00 | 0.40 | 2.50 |
| S2 | 1.10 → 1.00 | 0.60 → 0.40 | 2.00 → 2.50 |

En S2, los tres valores se **interpolan linealmente con Vs30**. Con $r = (V_{s30} - 350)/200 \in [0, 1]$:

$$
S = 1.10 - 0.10\,r, \qquad T_P = 0.60 - 0.20\,r, \qquad T_L = 2.00 + 0.50\,r
$$

Ejemplo de comprobación (POR-01, Vs30 = 431 m/s): $r = 0.405$ → S = 1.060, TP = 0.519 s, TL = 2.203 s, que coincide con la tabla 6.3. Sin Vs30 medido, la norma manda usar el extremo conservador (S2: TP = 0.6 s, TL = 2.0 s).

### 7.5 Factor de amplificación y espectro

$$
C(T) =
\begin{cases}
2.5 & T < T_P \\[2pt]
2.5\,\dfrac{T_P}{T} & T_P \le T < T_L \\[6pt]
2.5\,\dfrac{T_P\,T_L}{T^2} & T \ge T_L
\end{cases}
\qquad
S_a^{R=1}(T) = Z\,U\,C(T)\,S
\qquad
\frac{V}{W} = \frac{Z\,U\,C\,S}{R},\ \ \frac{C}{R} \ge 0.11
$$

$S_a^{R=1}(T_1)$ (`Sa_R1_g`) es el **objetivo de escalamiento** de los registros (Archivo 02). $V/W$ (`V_W`) es el coeficiente sísmico de diseño estático.

### 7.6 Periodo predominante del terreno Ts

| Aspecto | Regla E.030-2026 | Tratamiento en el catálogo |
| --- | --- | --- |
| Obligatoriedad | Categorías A y B en Z4 (art. 14.2) | `Ts_exigido = 1` en los 16 arquetipos A2 o B |
| Medición | Vibración ambiental, H/V, ≥ 3 registros de ≥ 30 min, criterios SESAME | No hay medición: se usa un **valor de referencia** |
| Valor de referencia | — | $T_s = 4H/V_{s30}$ con H = 30 m, es decir $T_s = 120/V_{s30}$ (s). Rango: 0.150–0.331 s |
| Control (art. 14.8) | $T_s < 0.65\,T_P$; si no, perfil siguiente menos favorable o estudio de sitio | **Cumple en los 40 arquetipos**: ninguno cambia de perfil |

**Advertencia de uso.** `Ts_s` es una función determinística de `Vs30_ms`. Como variable del dataset es redundante (correlación 1 con 1/Vs30) y solo documenta el cumplimiento del art. 14.8. Para un sitio real se reemplaza por el Ts medido.

---

## 8. Diccionario de columnas de `catalogo_arquetipos.csv`

| Columna | Tipo | Unidad | Descripción |
| --- | --- | --- | --- |
| `id_arquetipo` | texto | — | Clave primaria: `POR-nn`, `DUA-nn`, `MUR-nn` |
| `sistema` | categórica | — | `porticos`, `dual`, `muros` |
| `R0` | real | — | Coeficiente básico de reducción (8 / 7 / 6) |
| `n_pisos` | entero | — | Número de pisos |
| `h_piso_m` | real | m | Altura de entrepiso |
| `H_m` | real | m | Altura total $h_n$ |
| `vanos_x`, `vanos_y` | entero | — | Número de vanos por dirección |
| `luz_x_m`, `luz_y_m` | real | m | Luz de vano |
| `area_planta_m2` | real | m² | Área de planta |
| `fc_kgcm2` | entero | kg/cm² | Resistencia del concreto |
| `densidad_muros_pct` | real | % | ρw por dirección |
| `categoria` | categórica | — | `C`, `B`, `A2` |
| `U` | real | — | Factor de uso |
| `w_kPa` | real | kPa | Peso sísmico por unidad de área |
| `W_kN` | real | kN | Peso sísmico total |
| `col_m` | real | m | Lado de columna cuadrada (diseño final) |
| `viga_m` | texto | m | Sección de viga b×h |
| `muros_x`, `muros_y` | texto | — | `n×Lw` por dirección; `-` si no hay |
| `t_muro_m` | real | m | Espesor de muro (vacío en pórticos) |
| `T1_E030_s` | real | s | $h_n/C_T$ |
| `T1x_s`, `T1y_s` | real | s | Periodo modal por dirección |
| `T1_s` | real | s | max(T1x, T1y): periodo del dataset |
| `suelo` | categórica | — | `S1`, `S2` |
| `Vs30_ms` | entero | m/s | Vs30 del sitio |
| `S`, `TP_s`, `TL_s` | real | —, s, s | Parámetros de sitio E.030-2026 (interpolados) |
| `Ts_ref_s` | real | s | Ts de referencia (120/Vs30) |
| `Ts_lim_s` | real | s | 0.65·TP (límite del art. 14.8) |
| `Ts_exigido` | 0/1 | — | 1 si la categoría es A o B |
| `Z` | real | g | 0.45 |
| `C_T1` | real | — | C(T1) |
| `Sa_R1_g` | real | g | Z·U·C(T1)·S: objetivo de escalamiento |
| `V_W` | real | — | Coeficiente sísmico de diseño |
| `deriva_diseno` | real | — | Deriva inelástica de diseño (≤ 0.007) |
| `pct_V_muros` | real | % | Cortante basal en muros (análisis estático X) |
| `sistema_por_V` | categórica | — | Clasificación E.030 según `pct_V_muros` |

---

## 9. Controles de calidad del catálogo

| Control | Criterio | Resultado |
| --- | --- | --- |
| Deriva de diseño | ≤ 0.007 (E.030-2026, concreto armado) | 40/40 (máximo 0.0070) |
| Periodo predominante | $T_s < 0.65\,T_P$ (art. 14.8) | 40/40 |
| Coherencia del sistema | `sistema` = `sistema_por_V` | 40/40 |
| A2 solo en dual/muros | E.030 en Z4 | 5/5 |
| Unicidad de la clave | `id_arquetipo` único | Sí |
| Reproducibilidad | Semilla 2026; diseño determinístico | Mismo catálogo en cada corrida |

## 10. Limitaciones del catálogo

1. **Diseño por rigidez, no por resistencia.** El diseño controla la deriva; las cuantías de acero son representativas (columnas 1.5 %, vigas 0.8 % / 0.5 %, muros 0.25 % en el alma y 1.5 % en los bordes), no el resultado de un diseño E.060 elemento por elemento. Se recomienda validar en ETABS 4 a 6 arquetipos (uno por sistema y altura) y comparar periodo y deriva.
2. **Plantas regulares y simétricas.** No hay arquetipos irregulares ($I_a$, $I_p$ < 1).
3. **Base empotrada.** Sin interacción suelo-estructura, ni siquiera en S2.
4. **Las cargas del 100 % + 30 % ortogonal no se aplican al diseño.** En plantas simétricas su efecto en la deriva es pequeño y queda dentro del margen del método estático.
5. **Muros sin aberturas ni acoplamiento.** Los tramos son rectangulares y continuos en altura.

## Fuentes

1. Ministerio de Vivienda, Construcción y Saneamiento (2026). *RM N° 183-2026-VIVIENDA, que modifica la Norma Técnica E.030 Diseño Sismorresistente*. El Peruano, 3 de mayo de 2026. https://cdn.www.gob.pe/uploads/document/file/9902956/8081915-rm-183-2026-vivienda-modifica-norma-tecnica-e-030.pdf
2. Ministerio de Vivienda, Construcción y Saneamiento (2018). *Norma Técnica E.030 Diseño Sismorresistente* (RM 355-2018-VIVIENDA): artículos de estimación del peso, periodo fundamental aproximado y categoría–sistema estructural.
3. Ministerio de Vivienda, Construcción y Saneamiento. *Norma Técnica E.020 Cargas*.
4. SESAME (2004). *Guidelines for the implementation of the H/V spectral ratio technique on ambient vibrations*. European Commission.
