# Predicción de Demandas Sísmicas en Edificaciones de Concreto Armado usando Machine Learning Supervisado

## 📌 Información del Proyecto
* **Curso:** Aplicaciones de IA en Estructuras
* **Institución:** Universidad Peruana de Ciencias Aplicadas (UPC)
* **Docente Auditado:** Ing. Kurt Soncco Sinchi (`@AI-EPE-UPC`)
* **Entrega:** Trabajo Final 1 (TF1 / T1)

---

## 👥 Integrantes del Equipo
* **Paulino Antonio Díaz Hinostroza** | Código: `e201572251` | Email: `e201572251@upc.edu.pe`
* **Rodrigo Alonso De la Cruz Herrera** | Código: `e202527672` | Email: `e202527672@upc.edu.pe`
* **Guido Eduardo Valdez Tejeira** | Código: `e202528480` | Email: `e202528480@upc.edu.pe`
* **Felix Mamani Huanca** | Código: `e202527091` | Email: `e202527091@upc.edu.pe`
* **Johnny Esteban Cueva Moncada** | Código: `e202527071` | Email: `e202527071@upc.edu.pe`

---

## 📝 Descripción del Problema Estructural
En el Perú, el diseño sismorresistente se rige por la **Norma Técnica E.030 (RM 183-2026-VIVIENDA)**, la cual exige verificar la fuerza cortante en la base y controlar rigurosamente la deriva relativa máxima de entrepiso ($\Delta \le 0.007$ para estructuras de concreto armado).

Evaluar la respuesta sísmica no lineal mediante análisis tiempo-historia (NLTHA) ante múltiples acelerogramas requiere modelos complejos en programas como OpenSees o ETABS, lo que genera un alto costo computacional y demanda tiempos prolongados de ejecución.

El presente proyecto implementa un **modelo sustituto (Surrogate Model)** basado en **Machine Learning Supervisado** (Random Forest, XGBoost, LightGBM y Redes Neuronales) para estimar de forma instantánea:
1. **Deriva Máxima de Entrepiso ($\text{MIDR}$)** en escala logarítmica.
2. **Coeficiente de Cortante Basal Normalizado ($V_b / W$)**.

---

## 📊 Dataset y Variables
* **Fuente Principal:** PEER NGA-West2 Ground Motion Database.
* **Validación Externa:** Registros peruanos de subducción (CISMID / IGP - Lima 1966, Lima 1974, Pisco 2007).
* **Predictoras ($X$):**
  * *Símicas:* $PGA$, $PGV$, $S_a(T_1)$, Magnitud $M_w$, Distancia $R_{rup}$, Intensidad de Arias, Duración $D_{5-95}$.
  * *Geotécnicas (E.030):* Velocidad de onda de corte $V_{s30}$, perfiles $S_1$ y $S_2$.
  * *Estructurales:* Período fundamental $T_1$, número de pisos (3 a 15), altura $H$, peso total $W$, resistencia del concreto $f'_c$, factor $R_0$ (Pórticos $R_0=8$, Dual $R_0=7$, Muros $R_0=6$).
* **Variables Objetivo ($y$):** $\log(\text{MIDR})$ y $V_b/W$.

---

## 🔬 Marco Veridical Data Science (PCS Framework)
* **Predictibilidad ($P$):** Evaluación mediante $R^2$, $RMSE$, $MAE$ y clasificación del límite normativo $0.007$ (Matriz de Confusión y $F1\text{-Score}$).
* **Computabilidad ($C$):** Entorno virtual en Python (`.venv`), notebooks reproducibles y control de versiones transparente en GitHub.
* **Estabilidad ($S$):** Validación cruzada con `GroupKFold` por evento sísmico y análisis de sensibilidad ante variaciones en $V_{s30}$ e incertidumbres espectrales.
