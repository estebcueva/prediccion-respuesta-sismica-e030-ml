"""
gen_matriz.py — Matriz experimental de 16 000 combinaciones
(40 arquetipos × 100 pares de registros × 4 niveles de escala).

Los registros se identifican por "slot" (R001–R100) hasta que la selección
del flatfile NGA-West2 asigne un RSN a cada slot (tabla slot → RSN, EQID).
"""
import itertools
from pathlib import Path

import pandas as pd

NIVELES = (0.25, 0.50, 1.00, 1.50)
N_PARES = 100

DATA = Path(__file__).parents[1] / "data"
cat = pd.read_csv(DATA / "catalogo_arquetipos.csv")
slots = [f"R{i:03d}" for i in range(1, N_PARES + 1)]
filas = []
for (_, a), slot, nv in itertools.product(cat.iterrows(), slots, NIVELES):
    filas.append(dict(
        id_caso=f"{a.id_arquetipo}_{slot}_L{int(nv * 100):03d}",
        id_arquetipo=a.id_arquetipo, sistema=a.sistema, slot_registro=slot,
        nivel_escala=nv, T1_s=a.T1_s,
        T_ini_s=round(0.2 * a.T1_s, 3), T_fin_s=round(1.5 * a.T1_s, 3),
        Sa_obj_T1_g=round(nv * a.Sa_R1_g, 4)))
m = pd.DataFrame(filas)
m.to_csv(DATA / "matriz_combinaciones.csv", index=False)
print(len(m), "combinaciones")
print(m.groupby("sistema").size().to_dict())
print(m.groupby("nivel_escala").size().to_dict())
print(m.head(5).to_string(index=False))
assert m.id_caso.is_unique
# Tabla de escalamiento por arquetipo (para el documento)
t = cat[["id_arquetipo", "sistema", "T1_s", "Sa_R1_g"]].copy()
t["ventana"] = [f"{0.2 * x:.3f}–{1.5 * x:.3f}" for x in t.T1_s]
for nv in NIVELES:
    t[f"Sa_{nv:.2f}"] = (nv * t.Sa_R1_g).round(3)
t.to_csv(DATA / "tabla_escalamiento.csv", index=False)
