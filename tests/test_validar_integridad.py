"""Prueba negativa: corrompe una copia del CSV de ejemplo y verifica que cada
regla afectada pase a FAIL."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from validar_integridad import controles_dominio, reglas_integridad  # noqa: E402

base = pd.read_csv(RAIZ / "data" / "dataset_sismico_peru_EJEMPLO.csv")


def codigos_fail(d):
    return {r.codigo for r in reglas_integridad(d) + controles_dominio(d) if not r.ok}


assert codigos_fail(base) == set(), "el ejemplo limpio debe pasar todo"

casos = {
    "R1": lambda d: d.assign(id_caso=d.id_caso.where(d.index != 1, d.id_caso[0])),
    "R2": lambda d: d.assign(particion=np.where(d.index == 0, "test", d.particion)),
    "R3": lambda d: d.assign(ln_MIDR=d.ln_MIDR + np.where(d.index == 2, 0.1, 0)),
    "R4": lambda d: d.assign(cumple_0007=1),
    "R7": lambda d: d.assign(sf_base=d.sf_base * np.where(d.index == 3, 1.1, 1)),
    "D1": lambda d: d.assign(T1_s=d.T1_s.where(d.index != 4)),
    "D2": lambda d: d.assign(Vb_W=np.where(d.index == 5, 1.8, d.Vb_W)),
    "D3": lambda d: d.assign(R0=np.where(d.sistema == "dual", 8, d.R0)),
    "D4": lambda d: d.assign(flag_sf_rango=1),
    "D5": lambda d: d.assign(densidad_muros_pct=np.where(d.sistema == "dual", 1.2,
                                                         d.densidad_muros_pct)),
}
for esperado, corromper in casos.items():
    fallan = codigos_fail(corromper(base.copy()))
    assert esperado in fallan, f"{esperado} no detectó la corrupción ({fallan})"
    print(f"OK  corrupción de {esperado} detectada → FAIL en {sorted(fallan)}")
print("Todas las pruebas negativas pasaron.")
