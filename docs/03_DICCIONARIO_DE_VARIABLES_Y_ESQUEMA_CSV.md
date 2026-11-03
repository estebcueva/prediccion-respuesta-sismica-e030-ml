# 03 — Diccionario de Variables y Esquema CSV

**Dataset:** Respuesta sísmica no lineal de edificaciones peruanas de concreto armado (E.030-2026 · PEER NGA-West2)
**Componente:** matriz final de datos `dataset_sismico_peru.csv`
**Archivo de ejemplo asociado:** `dataset_sismico_peru_EJEMPLO.csv` (14 filas)
**Versión:** 1.0 · 1 de noviembre de 2026 · Ing. Rodrigo A. De la Cruz Herrera, CIP 325672

---

## 1. Estructura general

| Propiedad | Definición |
| --- | --- |
| Unidad de observación | **1 fila = 1 análisis tiempo-historia no lineal** (arquetipo × par de registros × nivel de escala × orientación) |
| Filas | 16 000 (entrenamiento + prueba) + 1 600 (validación externa peruana); 32 000 + 1 600 con rotación 0°/90° |
| Columnas | 57, en 7 bloques (sección 2) |
| Clave primaria | `id_caso` (único) |
| Claves foráneas | `id_arquetipo` → `catalogo_arquetipos.csv`; `id_registro` → `registros_seleccionados.csv` |
| Clave de grupo | `eqid`: **ningún evento puede estar en dos particiones** |
| Formato | CSV, UTF-8 sin BOM, separador coma, decimal punto, una fila de encabezados, sin columna de índice |
| Valores faltantes | Celda vacía (no `NaN`, `-999` ni `0`) |
| Precisión | 6 cifras significativas en reales; 0/1 en marcas |
| Unidades | SI (kN, m, s), aceleraciones en g, f'c en kg/cm² (convención peruana) |
| Tamaño estimado | ≈ 6–7 MB para 16 000 filas |
| Procedencia | Columna `fuente`: `NLTHA_fibras`, `NLTHA_imk` o `ilustrativo` (las filas de ejemplo de este documento) |

---

## 2. Encabezado exacto del CSV

```csv
id_caso,id_arquetipo,id_registro,eqid,nivel_escala,orientacion,dominio,particion,fuente,version_e030,sistema,R0,n_pisos,H_m,h_piso_m,area_planta_m2,T1_s,W_kN,densidad_muros_pct,fc_kgcm2,Z,U,S,TP_s,TL_s,Ts_s,C_T1,Vest_W,Sa_dis_R1_g,PGA_g,PGV_ms,Sa_T1_g,Sa_avg_g,Arias_ms,D5_95_s,HI_m,ASI_gs,Mw,Rrup_km,Vs30_est_ms,factor_escala,MIDR,ln_MIDR,cumple_0007,cumple_00875,Vb_W,colapso,convergencia,sf_base,flag_sf_rango,MIDR_x,MIDR_y,piso_critico,Vb_x_kN,Vb_y_kN,deriva_residual,t_cpu_s
```

| Bloque | Columnas | N.° | Rol |
| --- | --- | --- | --- |
| A. Identificación y trazabilidad | `id_caso` … `version_e030` | 10 | Claves, partición, procedencia. **No son variables de entrada** |
| B. X estructurales | `sistema` … `fc_kgcm2` | 10 | Features |
| C. X normativas E.030-2026 | `Z` … `Sa_dis_R1_g` | 9 | Features |
| D. X intensidad del registro (escalado) | `PGA_g` … `ASI_gs` | 8 | Features |
| E. Metadatos sísmicos | `Mw` … `factor_escala` | 4 | Features (ver nota sobre `factor_escala`) |
| F. Salidas y | `MIDR` … `Vb_W` | 5 | Targets y marcas de cumplimiento |
| G. Control de calidad y salidas auxiliares | `colapso` … `t_cpu_s` | 11 | Filtrado y auditoría. **Nunca usar como X** |

Variables de entrada: **31** (30 numéricas + 1 categórica).

---

## 3. Diccionario de variables

Las columnas "Rango" muestran el rango **real del catálogo** de 40 arquetipos (bloques B y C) o el **esperado** según la matriz de escalamiento (bloques D y E). "ln" marca las variables positivas que abarcan más de un orden de magnitud y conviene transformar con logaritmo natural.

### 3.1 Bloque A — Identificación y trazabilidad

| Columna | Tipo | Valores | Descripción |
| --- | --- | --- | --- |
| `id_caso` | texto | `{id_arquetipo}_R{id_registro}_L{λ×100}_O{orientación}` | Clave primaria. Ej.: `DUA-04_R1158_L100_O0` |
| `id_arquetipo` | texto | POR-01…MUR-13 | Clave del catálogo (Archivo 01) |
| `id_registro` | entero | RSN de NGA-West2; 90 000+ para registros peruanos | Clave del registro |
| `eqid` | entero | EQID de NGA-West2; 9001–9003 para Perú | **Grupo** para la partición y la validación cruzada |
| `nivel_escala` | real | 0.25, 0.50, 1.00, 1.50 | λ |
| `orientacion` | entero | 0 = (H1→X, H2→Y); 1 = intercambiadas | Rotación 0°/90° |
| `dominio` | categórica | `NGA-West2`, `Peru_subduccion` | Tipo de fuente sísmica |
| `particion` | categórica | `train`, `test`, `valid_ext` | Fijada por evento en la selección (Archivo 02, sección 2.3) |
| `fuente` | categórica | `NLTHA_fibras`, `NLTHA_imk`, `ilustrativo` | Procedencia de la fila |
| `version_e030` | texto | `2026` (o `2018`) | Versión normativa del diseño y del espectro objetivo |

### 3.2 Bloque B — Variables estructurales (X)

| Columna | Unidad | Tipo | Rango (catálogo) | ln | Definición / fuente |
| --- | --- | --- | --- | --- | --- |
| `sistema` | — | categórica | porticos, dual, muros | | Sistema E.030, verificado por reparto de cortante (Archivo 01, sección 5). Codificar one-hot |
| `R0` | — | real | 6, 7, 8 | | Coeficiente básico de reducción. Redundante con `sistema` (relación 1 a 1) |
| `n_pisos` | — | entero | 3 – 15 | | Número de pisos |
| `H_m` | m | real | 8.37 – 48.90 | | Altura total $h_n = n_{pisos} \cdot h$ |
| `h_piso_m` | m | real | 2.70 – 3.49 | | Altura de entrepiso (normaliza la deriva) |
| `area_planta_m2` | m² | real | 224.7 – 1200.5 | ✓ | $L_x \cdot L_y$ |
| `T1_s` | s | real | 0.168 – 1.301 | ✓ | Periodo modal, $\max(T_{1x}, T_{1y})$, modelo elástico 3D con corte en muros |
| `W_kN` | kN | real | 8 008 – 109 606 | ✓ | Peso sísmico $w \cdot A_{planta} \cdot n_{pisos}$ (Archivo 01, sección 3) |
| `densidad_muros_pct` | % | real | 0 – 2.88 | | $\rho_w = \sum L_w t_w / A_{planta}$ por dirección |
| `fc_kgcm2` | kg/cm² | entero | 210, 280, 350 | | Resistencia a compresión del concreto |

### 3.3 Bloque C — Variables normativas E.030-2026 (X)

| Columna | Unidad | Tipo | Rango (catálogo) | ln | Definición / fuente |
| --- | --- | --- | --- | --- | --- |
| `Z` | g | real | 0.45 | | Factor de zona (Z4). **Constante**: no aporta información; se conserva por completitud y para extender el dataset a otras zonas |
| `U` | — | real | 1.0, 1.3, 1.5 | | Factor de uso (C, B, A2) |
| `S` | — | real | 1.000 – 1.094 | | Factor de suelo, interpolado con Vs30 en S2 |
| `TP_s` | s | real | 0.400 – 0.588 | | Periodo de inicio de la rama descendente |
| `TL_s` | s | real | 2.03 – 2.50 | | Periodo de inicio de la rama de desplazamiento constante |
| `Ts_s` | s | real | 0.150 – 0.331 | | Periodo predominante del terreno (valor de referencia 120/Vs30; Archivo 01, sección 7.6). Determinístico en función del Vs30 del sitio: redundante |
| `C_T1` | — | real | 0.768 – 2.500 | | Factor de amplificación $C(T_1)$ |
| `Vest_W` | — | real | 0.050 – 0.295 | | Coeficiente sísmico de diseño: $Z U C S / R$ con $C/R \ge 0.11$ |
| `Sa_dis_R1_g` | g | real | 0.346 – 1.768 | ✓ | Objetivo de escalamiento $Z U C(T_1) S$ (R = 1) |

$$
C(T)=
\begin{cases}
2.5 & T<T_P\\
2.5\,T_P/T & T_P\le T<T_L\\
2.5\,T_P T_L/T^2 & T\ge T_L
\end{cases}
$$

### 3.4 Bloque D — Intensidad del registro, ya escalado (X)

Todas se calculan sobre el par horizontal; el valor del par es la **media geométrica** de las dos componentes, salvo $D_{5-95}$, que se promedia. Están **escaladas** por `factor_escala`.

| Columna | Unidad | Tipo | Rango esperado | ln | Definición |
| --- | --- | --- | --- | --- | --- |
| `PGA_g` | g | real | ≈ 0.03 – 2.5 | ✓ | $\max_t \lvert \ddot u_g(t) \rvert$ |
| `PGV_ms` | m/s | real | ≈ 0.02 – 3 | ✓ | $\max_t \lvert \dot u_g(t) \rvert$, con $\dot u_g = \int \ddot u_g\,dt$ |
| `Sa_T1_g` | g | real | ≈ 0.04 – 3 | ✓ | Pseudoaceleración espectral al 5 % en $T_1$ (interpolación log-log) |
| `Sa_avg_g` | g | real | ≈ 0.05 – 2.0 | ✓ | Media geométrica de $S_a$ en 20 periodos de $[0.2T_1,\ 1.5T_1]$: $\exp\!\big(\tfrac{1}{20}\sum_j \ln S_a(T_j)\big)$. El escalamiento ajusta el espectro **SRSS** del par al objetivo; como el SRSS de dos componentes similares es ≈ √2 veces cada una, resulta `Sa_avg_g` ≈ λ · `Sa_dis_R1_g` / √2 |
| `Arias_ms` | m/s | real | ≈ 0.01 – 50 | ✓ | $I_a = \dfrac{\pi}{2g}\displaystyle\int_0^{t_f} \ddot u_g^2\,dt$ |
| `D5_95_s` | s | real | ≈ 3 – 60 | ✓ | Tiempo entre el 5 % y el 95 % de $I_a$. **No depende de la escala** |
| `HI_m` | m | real | ≈ 0.02 – 5 | ✓ | Intensidad de Housner: $\displaystyle\int_{0.1}^{2.5} PS_v(T,\,5\%)\,dT$, con $PS_v = S_a\,g\,T/2\pi$ |
| `ASI_gs` | g·s | real | ≈ 0.01 – 2 | ✓ | Intensidad espectral de aceleración: $\displaystyle\int_{0.1}^{0.5} S_a(T,\,5\%)\,dT$ |

**Exponentes de escalamiento:** PGA, PGV, $S_a$, $S_{a,avg}$, HI y ASI escalan con $sf^1$; Arias con $sf^2$; $D_{5-95}$ con $sf^0$. Se calculan una vez por par (sin escalar) y se escalan analíticamente.

**Nota sobre HI.** Housner la definió con 20 % de amortiguamiento. Aquí se usa el 5 % para reutilizar el mismo espectro; se debe declarar.

### 3.5 Bloque E — Metadatos sísmicos (X)

| Columna | Unidad | Tipo | Rango esperado | ln | Definición |
| --- | --- | --- | --- | --- | --- |
| `Mw` | — | real | 6.0 – 7.9 (NGA-West2); 8.0 – 8.1 (Perú) | | Magnitud de momento |
| `Rrup_km` | km | real | 10 – 100 (NGA-West2); 36.7 – 111 (Perú) | ✓ | Distancia mínima al plano de ruptura |
| `Vs30_est_ms` | m/s | real | 350 – 800 | ✓ | Vs30 de la **estación** de registro (no del edificio) |
| `factor_escala` | — | real | ≈ 0.05 – 7.5 | ✓ | $sf = \lambda \cdot sf_0$ aplicado a ambas componentes |

**Nota sobre `factor_escala`.** Se incluye porque es un metadato real del experimento. Como variable de entrada, sin embargo, describe una decisión del analista y no una propiedad del sismo, y su efecto ya está contenido en las IM escaladas. Se recomienda excluirlo de X en el modelo principal y usarlo solo para diagnosticar si los errores crecen con factores grandes.

**Las dos variables Vs30.** `Vs30_est_ms` es el suelo de la estación donde se grabó el sismo (controla la forma espectral del registro). El suelo del edificio entra por `S`, `TP_s`, `TL_s` y `Ts_s`. No deben confundirse.

### 3.6 Bloque F — Variables de salida (y)

#### Deriva máxima de entrepiso

Para el piso $i$, con desplazamientos del centro de masa $u_i^x(t)$, $u_i^y(t)$:

$$
\theta_i^{x}(t)=\frac{u_i^{x}(t)-u_{i-1}^{x}(t)}{h_i},\qquad
\theta_i^{y}(t)=\frac{u_i^{y}(t)-u_{i-1}^{y}(t)}{h_i}
$$

$$
\mathrm{MIDR}=\max_t\ \max_i\ \max\!\big(\lvert\theta_i^{x}(t)\rvert,\ \lvert\theta_i^{y}(t)\rvert\big)
$$

| Columna | Unidad | Tipo | Rango | Definición |
| --- | --- | --- | --- | --- |
| `MIDR` | — | real | (0, 0.10] | Deriva máxima de entrepiso. Si hay colapso, se acota en 0.10 |
| `ln_MIDR` | — | real | (−∞, −2.303] | **Target 1**: $\ln(\mathrm{MIDR})$, logaritmo **natural** |
| `cumple_0007` | 0/1 | entero | 0, 1 | 1 si MIDR ≤ 0.007 (límite de la Tabla de distorsiones, concreto armado) |
| `cumple_00875` | 0/1 | entero | 0, 1 | 1 si MIDR ≤ 0.00875 = 1.25 × 0.007, límite para resultados tiempo-historia (art. 49.2) |
| `Vb_W` | — | real | ≈ 0.02 – 1.5 | **Target 2**: cortante basal normalizado |

**Por qué el logaritmo.** La deriva condicionada a la intensidad sigue aproximadamente una distribución lognormal. En escala ln la dispersión es casi constante (homocedasticidad), los errores se leen como factores multiplicativos ($e^{\varepsilon}$) y el rango de 0.0005 a 0.10 (más de dos órdenes de magnitud) se comprime a −7.6 … −2.3. Si se quiere log base 10: $\log_{10}\mathrm{MIDR} = \ln\mathrm{MIDR}/\ln 10$.

**Marca de control normativo.** `cumple_0007` permite usar el dataset para clasificación del cumplimiento. La clase de interés es "no cumple" (`cumple_0007 = 0`). Se guardan ambos umbrales porque la E.030-2026 aplica 0.007 al análisis lineal y 1.25 × 0.007 al tiempo-historia.

#### Cortante basal normalizado

$$
V_{b,x}(t)=-\sum_{j\in\text{base}}R_{j,x}(t),\qquad
V_{b,y}(t)=-\sum_{j\in\text{base}}R_{j,y}(t)
$$

$$
\frac{V_b}{W}=\frac{1}{W}\,\max_t\sqrt{V_{b,x}(t)^2+V_{b,y}(t)^2}
$$

Es adimensional y se compara directamente con `Vest_W`. El cociente $\Omega = (V_b/W)/\text{Vest\_W}$ estima la sobrerresistencia del arquetipo. **En los casos con colapso, `Vb_W` no es representativo** (el análisis se detiene): se conserva, pero se excluye del target 2.

### 3.7 Bloque G — Control de calidad y salidas auxiliares (no son X)

| Columna | Unidad | Tipo | Definición | Uso |
| --- | --- | --- | --- | --- |
| `colapso` | 0/1 | entero | 1 si MIDR > 0.10, o no convergencia con MIDR ≥ 0.04 | Filtro de Vb/W; análisis de colapso |
| `convergencia` | 0/1 | entero | 0 si el análisis no convergió con MIDR < 0.04 (falla numérica) | **Excluir las filas con 0** |
| `sf_base` | — | real | $sf_0$ = `factor_escala` / `nivel_escala` | Trazabilidad |
| `flag_sf_rango` | 0/1 | entero | 1 si $0.2 \le sf_0 \le 5.0$ | Filtro opcional (Archivo 02, sección 4.4) |
| `MIDR_x`, `MIDR_y` | — | real | Deriva máxima por dirección | Diagnóstico de bidireccionalidad |
| `piso_critico` | — | entero | Piso donde ocurre MIDR | Diagnóstico del mecanismo |
| `Vb_x_kN`, `Vb_y_kN` | kN | real | Cortante basal máximo por dirección | Diagnóstico |
| `deriva_residual` | — | real | Deriva máxima al final de la vibración libre | Daño residual |
| `t_cpu_s` | s | real | Tiempo de cómputo del caso | Presupuesto |

---

## 4. Reglas de integridad del dataset

Cada regla se puede verificar automáticamente sobre el CSV. Si alguna falla, la fila está mal construida.

| N.° | Regla | Tipo |
| --- | --- | --- |
| R1 | `id_caso` es único | Clave |
| R2 | Cada `eqid` aparece en una sola `particion` | Fuga de información |
| R3 | `ln_MIDR` = ln(`MIDR`) (tolerancia 1e-6) | Coherencia de target |
| R4 | `cumple_0007` = 1 ⇔ `MIDR` ≤ 0.007; `cumple_00875` = 1 ⇔ `MIDR` ≤ 0.00875 | Coherencia de marcas |
| R5 | Si `colapso` = 0: `MIDR` = max(`MIDR_x`, `MIDR_y`) | Coherencia de salidas |
| R6 | Si `colapso` = 1: `MIDR` = 0.10 | Convención de colapso |
| R7 | `factor_escala` = `nivel_escala` × `sf_base` | Escalamiento |
| R8 | Mismo (`id_arquetipo`, `id_registro`): `D5_95_s` constante; `PGA_g`/`factor_escala` y `Arias_ms`/`factor_escala`² constantes entre niveles | Escalamiento de las IM |
| R9 | Mismo `id_registro`: `PGA_g`/`factor_escala` (PGA sin escalar) constante entre arquetipos | Unicidad del registro |
| R10 | Mismo `id_arquetipo`: los bloques B y C son idénticos en todas sus filas | Join con el catálogo |
| R11 | `Sa_dis_R1_g` = `Z`·`U`·`C_T1`·`S`; `Vest_W` = máx(`Sa_dis_R1_g`/`R0`, 0.11·`Z`·`U`·`S`) | Normativa |
| R12 | `Vb_W` > 0, `MIDR` > 0, `T1_s` > 0 | Dominio |
| R13 | `dominio` = `Peru_subduccion` ⇔ `particion` = `valid_ext` | Separación de la validación externa |

---

## 5. Filas de ejemplo

**Cómo se generaron.** Las respuestas (MIDR, Vb/W y salidas auxiliares) son **resultados reales del modelo no lineal** en OpenSeesPy (fibras, 3D, bidireccional), corridos sobre tres arquetipos del catálogo: POR-07 (pórtico de 3 pisos), DUA-04 (dual de 6 pisos) y MUR-04 (muros de 5 pisos). Los **acelerogramas son sintéticos**: ruido blanco filtrado (Kanai-Tajimi) con envolvente. Uno es de tipo cortical (Mw 6.9, D5-95 ≈ 13 s) y otro de tipo subducción (Mw 8.0, D5-95 ≈ 38 s). Sus identificadores (`id_registro` 900001 y 900101; `eqid` 900 y 9901) son **ficticios**: no corresponden a registros de NGA-West2, CISMID ni IGP. Por eso todas las filas llevan `fuente = ilustrativo` y **no deben mezclarse con el dataset real**.

### 5.1 Contenido completo del archivo de ejemplo

```csv
id_caso,id_arquetipo,id_registro,eqid,nivel_escala,orientacion,dominio,particion,fuente,version_e030,sistema,R0,n_pisos,H_m,h_piso_m,area_planta_m2,T1_s,W_kN,densidad_muros_pct,fc_kgcm2,Z,U,S,TP_s,TL_s,Ts_s,C_T1,Vest_W,Sa_dis_R1_g,PGA_g,PGV_ms,Sa_T1_g,Sa_avg_g,Arias_ms,D5_95_s,HI_m,ASI_gs,Mw,Rrup_km,Vs30_est_ms,factor_escala,MIDR,ln_MIDR,cumple_0007,cumple_00875,Vb_W,colapso,convergencia,sf_base,flag_sf_rango,MIDR_x,MIDR_y,piso_critico,Vb_x_kN,Vb_y_kN,deriva_residual,t_cpu_s
POR-07_R900001_L025_O0,POR-07,900001,900,0.25,0,NGA-West2,train,ilustrativo,2026,porticos,8,3,9.72,3.24,438.7,0.356,10924,0,350,0.45,1,1.086,0.572,2.07,0.317,2.5,0.1527,1.222,0.0905482,0.0783898,0.27043,0.210659,0.157829,12.645,0.348103,0.0884827,6.9,32,410,0.467682,0.0015473,-6.47125,1,1,0.243023,0,1,1.87073,1,0.0015473,0.00149685,2,2257.47,2263.84,1.54771e-05,191.727
POR-07_R900001_L050_O0,POR-07,900001,900,0.5,0,NGA-West2,train,ilustrativo,2026,porticos,8,3,9.72,3.24,438.7,0.356,10924,0,350,0.45,1,1.086,0.572,2.07,0.317,2.5,0.1527,1.222,0.181096,0.15678,0.54086,0.421317,0.631315,12.645,0.696206,0.176965,6.9,32,410,0.935365,0.00295284,-5.82499,1,1,0.404228,0,1,1.87073,1,0.00243873,0.00295284,2,3266.65,3416.19,1.06015e-05,207.893
POR-07_R900001_L100_O0,POR-07,900001,900,1,0,NGA-West2,train,ilustrativo,2026,porticos,8,3,9.72,3.24,438.7,0.356,10924,0,350,0.45,1,1.086,0.572,2.07,0.317,2.5,0.1527,1.222,0.362193,0.313559,1.08172,0.842634,2.52526,12.645,1.39241,0.353931,6.9,32,410,1.87073,0.0102372,-4.58173,0,0,0.556071,0,1,1.87073,1,0.0102372,0.0063285,1,5654.06,4439.56,0.000292918,233.432
POR-07_R900001_L150_O0,POR-07,900001,900,1.5,0,NGA-West2,train,ilustrativo,2026,porticos,8,3,9.72,3.24,438.7,0.356,10924,0,350,0.45,1,1.086,0.572,2.07,0.317,2.5,0.1527,1.222,0.543289,0.470339,1.62258,1.26395,5.68184,12.645,2.08862,0.530896,6.9,32,410,2.80609,0.0141498,-4.25805,0,0,0.554797,0,1,1.87073,1,0.0141498,0.0106698,1,5889.27,4911.3,0.000680643,241.671
DUA-04_R900001_L025_O0,DUA-04,900001,900,0.25,0,NGA-West2,train,ilustrativo,2026,dual,7,6,16.62,2.77,288.4,0.63,14363,0.3,350,0.45,1,1,0.4,2.5,0.205,1.586,0.102,0.714,0.0763055,0.0660596,0.128117,0.136924,0.112083,12.645,0.293348,0.074565,6.9,32,410,0.394119,0.00169333,-6.38106,1,1,0.10834,0,1,1.57648,1,0.00169333,0.000853293,3,1422.34,860.487,3.98138e-05,394.893
DUA-04_R900001_L050_O0,DUA-04,900001,900,0.5,0,NGA-West2,train,ilustrativo,2026,dual,7,6,16.62,2.77,288.4,0.63,14363,0.3,350,0.45,1,1,0.4,2.5,0.205,1.586,0.102,0.714,0.152611,0.132119,0.256234,0.273848,0.448331,12.645,0.586697,0.14913,6.9,32,410,0.788238,0.00282635,-5.86877,1,1,0.170983,0,1,1.57648,1,0.00282635,0.00251778,3,2097.82,1893.32,2.53973e-05,521.253
DUA-04_R900001_L100_O0,DUA-04,900001,900,1,0,NGA-West2,train,ilustrativo,2026,dual,7,6,16.62,2.77,288.4,0.63,14363,0.3,350,0.45,1,1,0.4,2.5,0.205,1.586,0.102,0.714,0.305222,0.264238,0.512468,0.547696,1.79332,12.645,1.17339,0.29826,6.9,32,410,1.57648,0.00564445,-5.17708,1,1,0.296555,0,1,1.57648,1,0.00556938,0.00564445,2,3143.19,3212.25,0.000119817,531.887
DUA-04_R900001_L150_O0,DUA-04,900001,900,1.5,0,NGA-West2,train,ilustrativo,2026,dual,7,6,16.62,2.77,288.4,0.63,14363,0.3,350,0.45,1,1,0.4,2.5,0.205,1.586,0.102,0.714,0.457833,0.396357,0.768703,0.821543,4.03498,12.645,1.76009,0.44739,6.9,32,410,2.36471,0.0124502,-4.38602,0,0,0.369924,0,1,1.57647,1,0.0124502,0.00945672,2,4537.82,3204.36,0.000384352,623.585
MUR-04_R900001_L025_O0,MUR-04,900001,900,0.25,0,NGA-West2,train,ilustrativo,2026,muros,6,5,14.05,2.81,510.5,0.168,21187,2.26,210,0.45,1,1.094,0.588,2.03,0.331,2.5,0.2051,1.231,0.10982,0.0950743,0.246285,0.222779,0.232163,12.645,0.422193,0.107315,6.9,32,410,0.567224,0.000177581,-8.63608,1,1,0.231532,0,1,2.2689,1,0.00017161,0.000177581,4,4195.38,3821.88,9.89869e-07,694.739
MUR-04_R900001_L050_O0,MUR-04,900001,900,0.5,0,NGA-West2,train,ilustrativo,2026,muros,6,5,14.05,2.81,510.5,0.168,21187,2.26,210,0.45,1,1.094,0.588,2.03,0.331,2.5,0.2051,1.231,0.219641,0.190149,0.492569,0.445557,0.928653,12.645,0.844386,0.214631,6.9,32,410,1.13445,0.000494437,-7.61209,1,1,0.416522,0,1,2.2689,1,0.000494437,0.000358044,4,8041.95,6539.94,2.47234e-06,836.577
MUR-04_R900001_L100_O0,MUR-04,900001,900,1,0,NGA-West2,train,ilustrativo,2026,muros,6,5,14.05,2.81,510.5,0.168,21187,2.26,210,0.45,1,1.094,0.588,2.03,0.331,2.5,0.2051,1.231,0.439282,0.380297,0.985139,0.891114,3.71461,12.645,1.68877,0.429262,6.9,32,410,2.2689,0.0020048,-6.21221,1,1,0.851204,0,1,2.2689,1,0.0020048,0.00144943,4,16182,13774.8,8.37691e-06,1172.14
MUR-04_R900001_L150_O0,MUR-04,900001,900,1.5,0,NGA-West2,train,ilustrativo,2026,muros,6,5,14.05,2.81,510.5,0.168,21187,2.26,210,0.45,1,1.094,0.588,2.03,0.331,2.5,0.2051,1.231,0.658923,0.570446,1.47771,1.33667,8.35787,12.645,2.53316,0.643892,6.9,32,410,3.40334,0.004617,-5.37801,1,1,1.08781,0,1,2.26889,1,0.004617,0.00216367,4,21182.3,15930.4,5.26741e-05,1307.45
POR-07_R900101_L100_O0,POR-07,900101,9901,1,0,Peru_subduccion,valid_ext,ilustrativo,2026,porticos,8,3,9.72,3.24,438.7,0.356,10924,0,350,0.45,1,1.086,0.572,2.07,0.317,2.5,0.1527,1.222,0.443471,0.744183,0.928843,0.865797,8.99183,37.93,1.95958,0.356916,8,105,450,4.81012,0.0103787,-4.568,0,0,0.552179,0,1,4.81012,1,0.00923212,0.0103787,1,5919.12,5531.56,0.000181992,581.284
MUR-04_R900101_L100_O0,MUR-04,900101,9901,1,0,Peru_subduccion,valid_ext,ilustrativo,2026,muros,6,5,14.05,2.81,510.5,0.168,21187,2.26,210,0.45,1,1.094,0.588,2.03,0.331,2.5,0.2051,1.231,0.566452,0.950555,1.02118,0.91286,14.6705,37.93,2.503,0.455893,8,105,450,6.14404,0.00168338,-6.38695,1,1,0.739443,0,1,6.14404,0,0.00168338,0.00145151,4,14397.4,13475.9,2.65315e-06,2790.33
```

### 5.2 Vista resumida (columnas clave)

| id_caso                |    λ |     sf |   Sa(T1) g |   Sa_avg g |   PGA g |   D5-95 s |      MIDR |   ln MIDR |   ≤0.007 |   ≤0.00875 |   Vb/W |   Vest/W |   colapso |   conv. |   sf en rango |   piso crít. |
|:-----------------------|-----:|-------:|-----------:|-----------:|--------:|----------:|----------:|----------:|---------:|-----------:|-------:|---------:|----------:|--------:|--------------:|-------------:|
| POR-07_R900001_L025_O0 | 0.25 | 0.4677 |     0.2704 |     0.2107 | 0.09055 |     12.64 | 0.001547  |    -6.471 |        1 |          1 | 0.243  |   0.1527 |         0 |       1 |             1 |            2 |
| POR-07_R900001_L050_O0 | 0.5  | 0.9354 |     0.5409 |     0.4213 | 0.1811  |     12.64 | 0.002953  |    -5.825 |        1 |          1 | 0.4042 |   0.1527 |         0 |       1 |             1 |            2 |
| POR-07_R900001_L100_O0 | 1    | 1.871  |     1.082  |     0.8426 | 0.3622  |     12.64 | 0.01024   |    -4.582 |        0 |          0 | 0.5561 |   0.1527 |         0 |       1 |             1 |            1 |
| POR-07_R900001_L150_O0 | 1.5  | 2.806  |     1.623  |     1.264  | 0.5433  |     12.64 | 0.01415   |    -4.258 |        0 |          0 | 0.5548 |   0.1527 |         0 |       1 |             1 |            1 |
| DUA-04_R900001_L025_O0 | 0.25 | 0.3941 |     0.1281 |     0.1369 | 0.07631 |     12.64 | 0.001693  |    -6.381 |        1 |          1 | 0.1083 |   0.102  |         0 |       1 |             1 |            3 |
| DUA-04_R900001_L050_O0 | 0.5  | 0.7882 |     0.2562 |     0.2738 | 0.1526  |     12.64 | 0.002826  |    -5.869 |        1 |          1 | 0.171  |   0.102  |         0 |       1 |             1 |            3 |
| DUA-04_R900001_L100_O0 | 1    | 1.576  |     0.5125 |     0.5477 | 0.3052  |     12.64 | 0.005644  |    -5.177 |        1 |          1 | 0.2966 |   0.102  |         0 |       1 |             1 |            2 |
| DUA-04_R900001_L150_O0 | 1.5  | 2.365  |     0.7687 |     0.8215 | 0.4578  |     12.64 | 0.01245   |    -4.386 |        0 |          0 | 0.3699 |   0.102  |         0 |       1 |             1 |            2 |
| MUR-04_R900001_L025_O0 | 0.25 | 0.5672 |     0.2463 |     0.2228 | 0.1098  |     12.64 | 0.0001776 |    -8.636 |        1 |          1 | 0.2315 |   0.2051 |         0 |       1 |             1 |            4 |
| MUR-04_R900001_L050_O0 | 0.5  | 1.134  |     0.4926 |     0.4456 | 0.2196  |     12.64 | 0.0004944 |    -7.612 |        1 |          1 | 0.4165 |   0.2051 |         0 |       1 |             1 |            4 |
| MUR-04_R900001_L100_O0 | 1    | 2.269  |     0.9851 |     0.8911 | 0.4393  |     12.64 | 0.002005  |    -6.212 |        1 |          1 | 0.8512 |   0.2051 |         0 |       1 |             1 |            4 |
| MUR-04_R900001_L150_O0 | 1.5  | 3.403  |     1.478  |     1.337  | 0.6589  |     12.64 | 0.004617  |    -5.378 |        1 |          1 | 1.088  |   0.2051 |         0 |       1 |             1 |            4 |
| POR-07_R900101_L100_O0 | 1    | 4.81   |     0.9288 |     0.8658 | 0.4435  |     37.93 | 0.01038   |    -4.568 |        0 |          0 | 0.5522 |   0.1527 |         0 |       1 |             1 |            1 |
| MUR-04_R900101_L100_O0 | 1    | 6.144  |     1.021  |     0.9129 | 0.5665  |     37.93 | 0.001683  |    -6.387 |        1 |          1 | 0.7394 |   0.2051 |         0 |       1 |             0 |            4 |

### 5.3 Verificación de las reglas de integridad sobre el ejemplo

```text
OK   R1 id_caso único
OK   R2 eqid en una sola partición
OK   R3 ln_MIDR = ln(MIDR)
OK   R4 marcas de cumplimiento
OK   R5 MIDR = max(MIDR_x, MIDR_y)
OK   R6 colapso ⇒ MIDR = 0.10
OK   R7 sf = λ·sf_base
OK   R8 escalamiento de IM
OK   R9 PGA sin escalar única por registro
OK   R10 bloques B y C constantes por arquetipo
OK   R11 Sa_dis y Vest coherentes
OK   R12 dominio positivo
OK   R13 Perú ⇔ valid_ext
(14, 57)
```

### 5.4 Lectura de los ejemplos

| Observación | Filas | Interpretación |
| --- | --- | --- |
| La deriva crece de forma no lineal con λ | POR-07: 0.0015 → 0.0030 → 0.0102 → 0.0141 | Duplicar la intensidad de 0.25 a 0.50 duplica la deriva (rango elástico); de 0.50 a 1.00 la multiplica por 3.4 (fluencia). Es la no linealidad que el muestreo multinivel debe capturar |
| El cortante se satura | POR-07: Vb/W = 0.556 (λ = 1.0) y 0.555 (λ = 1.5) | El pórtico alcanzó su resistencia lateral: más intensidad ya no aumenta Vb, solo la deriva. Sobrerresistencia Ω = 0.556 / 0.153 ≈ 3.6 |
| El edificio de muros sigue casi elástico | MUR-04: MIDR ≤ 0.0046 y Vb/W hasta 1.09 | Edificio muy rígido (T1 = 0.17 s): el cortante sigue creciendo con λ y la deriva es pequeña. Ω ≈ 0.851 / 0.205 ≈ 4.2 al nivel de diseño |
| Cumplimiento normativo | POR-07 a λ = 1.0: MIDR = 0.0102 → `cumple_0007 = 0` y `cumple_00875 = 0` | Con **un** registro sintético no se juzga el diseño: la E.030 exige el promedio de ≥ 7 pares. La marca sirve como etiqueta de clasificación por caso |
| Mecanismo | `piso_critico`: pórtico POR-07 = piso 1 en λ ≥ 1.0; muros MUR-04 = piso 4 de 5 | Pórtico: deriva concentrada en el primer piso. Muros: voladizo a flexión, la deriva entre pisos crece hacia los pisos altos |
| Subducción vs. cortical (POR-07, λ = 1.0) | Sa_avg 0.866 vs. 0.843 g; D5-95 37.9 vs. 12.6 s; Arias 9.0 vs. 2.5 m/s; MIDR 0.0104 vs. 0.0102 | Con intensidad espectral similar, el registro largo triplica la duración y casi cuadruplica la energía, pero en este caso la deriva casi no cambia. El efecto de la duración se manifiesta más en la degradación y el colapso que en la deriva máxima. Es justo lo que la validación externa debe medir con muchos casos |
| Factor de escala fuera de rango | MUR-04 con el registro de subducción: sf_base = 6.14 → `flag_sf_rango = 0` | Un registro débil (PGA 0.09 g) llevado al espectro de un edificio rígido de categoría C. Se conserva marcado (Archivo 02, sección 4.4) |
| Escalamiento coherente | Mismo par: `D5_95_s` = 12.645 s en los 12 casos; `PGA_g`/`factor_escala` = 0.1936 en los 3 arquetipos | Confirma las reglas R8 y R9 |
| Sa_avg vs. objetivo | POR-07, λ = 1.0: Sa_avg = 0.843 g; Sa_dis/√2 = 1.222/√2 = 0.864 g | El escalamiento se hace sobre el SRSS; la IM del par es la media geométrica de componentes |

---

## 6. Archivos del dataset y relaciones

```text
catalogo_arquetipos.csv  (40)   ── id_arquetipo ──┐
                                                  ├──► dataset_sismico_peru.csv (16 000 + 1 600)
registros_seleccionados.csv (100 + 10) ── id_registro / eqid ──┘
matriz_combinaciones.csv (16 000) ── plan de ejecución: qué casos correr
```

| Archivo | Filas | Clave | Contenido |
| --- | --- | --- | --- |
| `catalogo_arquetipos.csv` | 40 | `id_arquetipo` | Población de edificios (Archivo 01) |
| `registros_seleccionados.csv` | 100 + 10 | `id_registro` | Registros y metadatos (Archivo 02) |
| `matriz_combinaciones.csv` | 16 000 | `id_caso` | Plan experimental (Archivo 02) |
| `dataset_sismico_peru.csv` | 16 000 + 1 600 | `id_caso` | Matriz final (este documento) |
