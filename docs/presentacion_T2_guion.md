# Presentación T2 — Guion (4 diapositivas, 5 minutos)

La presentación está publicada como deck de Slides (exportable a PowerPoint o PDF). Aquí van el contenido de cada lámina y el guion para decir en voz alta, de 1 minuto cada uno; el minuto restante queda para preguntas.


## Diapositiva 1 — Carátula

**En pantalla:**

- Aplicaciones de IA en Estructuras · UPC · Entrega T2
- Predicción de demandas sísmicas en edificios de concreto armado del Perú con Machine Learning
- Deriva máxima ln(MIDR) y cortante basal Vb/W · Norma E.030-2026 · PEER NGA-West2 Docente: Ing. Kurt Soncco Sinchi

| Integrante | Código | Correo |
| --- | --- | --- |
| Paulino Antonio Díaz Hinostroza | e201572251 | e201572251@upc.edu.pe |
| Rodrigo Alonso De la Cruz Herrera | e202527672 | e202527672@upc.edu.pe |
| Guido Eduardo Valdez Tejeira | e202528480 | e202528480@upc.edu.pe |
| Felix Mamani Huanca | e202527091 | e202527091@upc.edu.pe |
| Johnny Esteban Cueva Moncada | e202527071 | e202527071@upc.edu.pe |

- Repositorio: https://github.com/estebcueva/prediccion-respuesta-sismica-e030-ml

**Guion:** (≈ 1 minuto) Buenos días. Somos el grupo de Paulino Díaz, Rodrigo De la Cruz, Guido Valdez, Felix Mamani y Johnny Cueva. Nuestro proyecto busca predecir con inteligencia artificial cuánto se deforma y cuánta fuerza recibe un edificio de concreto armado peruano durante un sismo. Predecimos dos cosas: la deriva máxima de entrepiso, que es lo que la norma E.030 limita a 0.007, y el cortante basal dividido entre el peso del edificio. Trabajamos con la norma vigente, la E.030 modificada en 2026, y con la base de sismos PEER NGA-West2 de la Universidad de California en Berkeley. En esta segunda entrega presentamos la base de datos, el análisis exploratorio y el plan para entrenar los modelos. Todo el código, los datos y la bitácora de uso de IA están en nuestro repositorio de GitHub, cuyo enlace ven en pantalla.


## Diapositiva 2 — El problema

**En pantalla:**

- El problema: un análisis no lineal tarda minutos u horas
- Hoy: OpenSees / ETABS
- 3 – 38 min
- por edificio y por sismo (medido en nuestras pruebas)
- 16 000 casos ≈ 4 000 horas de CPU
- Con IA: modelo entrenado
- milisegundos
- por predicción, con su error medido
- se entrena una sola vez con los análisis
- La E.030 estima la deriva con un factor lineal (0.75·R·Δ) que no ve la duración del sismo ni el daño acumulado. El análisis no lineal sí lo ve, pero es caro: la IA aprende del análisis no lineal.
- 2 / 4 · Tiempos: OpenSeesPy 3D, 1 CPU, registros de 30–80 s

**Guion:** (≈ 1 minuto) ¿Por qué usar IA? Para saber cómo se comporta de verdad un edificio en un sismo fuerte, hay que hacer un análisis tiempo-historia no lineal: simular segundo a segundo cómo se agrietan las vigas, fluye el acero y se degradan los elementos. En nuestras pruebas con OpenSees, un solo análisis tardó entre 3 y 38 minutos, según el edificio y la duración del sismo. Nuestra base completa son 16 000 análisis: unas 4 000 horas de computadora. La norma E.030 evita ese costo con una fórmula lineal: la deriva elástica por 0.75 R. Es práctica, pero no ve la duración del sismo ni el daño que se acumula. Nuestra propuesta es hacer los análisis caros una sola vez, enseñarle a un modelo de IA lo que salió de ellos y después predecir la respuesta de un edificio nuevo en milisegundos, sabiendo cuánto se puede equivocar.


## Diapositiva 3 — Los datos y el EDA

**En pantalla:**

- Los datos y lo que encontramos en el EDA
- 40
- edificios diseñados con la E.030-2026 (3–15 pisos)
- 16 000
- casos: 40 × 100 sismos × 4 intensidades
- 31
- variables de entrada por caso (57 columnas)
- 18/18
- controles de calidad aprobados
- 1. Corregimos los duales. Sus muros tomaban 87–99 % del cortante (eran edificios de muros); ahora toman 31–61 %, como exige la E.030.
- 2. La fórmula de la norma se queda corta. En los duales, el periodo real es 44 % mayor que hn/CT.
- 3. La respuesta no es lineal. Al fluir, la deriva crece más rápido (pendiente 0.93 → 1.43) y el cortante del pórtico se estanca: sobrerresistencia Ω ≈ 3.6.
- 3 / 4 · Hallazgo 3: 14 análisis de ejemplo con sismos sintéticos; se confirmará con la campaña completa

**Guion:** (≈ 1 minuto) Nuestra base tiene 40 edificios: pórticos, duales y muros, de 3 a 15 pisos, con concreto de 210, 280 y 350, todos diseñados con la E.030-2026 y verificados: cumplen la deriva de 0.007. Cada edificio se analiza con 100 sismos reales a 4 intensidades: 16 000 casos, cada uno con 31 variables de entrada. Un script revisa automáticamente 18 reglas de calidad, y todas pasan. El análisis exploratorio dejó tres hallazgos. Primero, nuestros duales en realidad se comportaban como edificios de muros; los recalibramos para que los muros tomen entre 31 y 61 por ciento del cortante. Segundo, la fórmula de periodo de la norma subestima en 44 por ciento el periodo de los duales, así que usamos el periodo modal. Tercero, la respuesta no es lineal: cuando el edificio fluye, la deriva crece más rápido y el cortante se estanca. Por eso necesitamos modelos no lineales. Este último resultado viene de 14 casos de ejemplo y lo confirmaremos con la campaña completa.


## Diapositiva 4 — El plan de IA y el marco VDS

**En pantalla:**

- El plan de IA: probar con sismos que el modelo nunca vio
- Modelos a comparar
- Regresión lineal (referencia)
- Random Forest
- XGBoost
- LightGBM
- Red neuronal
- Validación por sismo
- Un mismo sismo nunca está en entrenamiento y en prueba a la vez (GroupKFold).
- Mezclarlos al azar daba un error 32 % más bajo que el real.
- Prueba final: sismos peruanos de Lima 1966, 1974 y Pisco 2007.
- Garantía VDS
- Predice: se mide con sismos nuevos.
- Se reproduce: código, datos y semillas en GitHub.
- Es estable: ante cambios de suelo (Vs30), semilla y tipo de sismo.
- Siguiente paso (T3): correr los 16 000 análisis y entrenar los cinco modelos.
- 4 / 4 · Meta: R² ≥ 0.85 en ln(MIDR) y F1 ≥ 0.85 al detectar «no cumple 0.007»

**Guion:** (≈ 1 minuto) ¿Cómo vamos a entrenar y evaluar? Compararemos cinco modelos, desde una regresión lineal, que es nuestra referencia física, hasta XGBoost, LightGBM y una red neuronal. Lo más importante es cómo los evaluamos. Cada sismo aparece en cientos de filas, porque lo aplicamos a 40 edificios y a 4 intensidades. Si mezclamos las filas al azar, el modelo reconoce el sismo en lugar de aprender, y el error sale optimista: en nuestra prueba, 32 por ciento más bajo que el real. Por eso separamos por sismo, con GroupKFold: un sismo está en entrenamiento o en prueba, nunca en ambos. Y la prueba final será con sismos peruanos de subducción que el modelo nunca vio. Seguimos el marco VDS: el modelo debe predecir sismos nuevos, todo debe poder reproducirse desde GitHub, y los resultados deben ser estables si cambiamos el suelo, la semilla o el tipo de sismo. El siguiente paso es correr los 16 000 análisis y entrenar. Gracias.
