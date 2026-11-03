"""
e030.py — Parámetros y espectro de diseño de la Norma Técnica E.030.

VERSIONES
---------
* "2018": E.030-2018 (RM 355-2018-VIVIENDA).
* "2026": E.030 modificada por la RM 183-2026-VIVIENDA (28-abr-2026,
  publicada en El Peruano el 3-may-2026). Tablas transcritas del texto
  publicado: perfiles de suelo (Tabla 3), factor S (Tabla 4), TP/TL
  (Tabla 5), R0 (Tabla 10), distorsiones (Tabla 14) y tiempo-historia
  (arts. 47–49). La extracción del PDF tuvo ruido de OCR en los
  encabezados de las Tablas 4 y 5: CONFIRMAR los valores contra el PDF
  oficial antes de reportar resultados.

Unidades: periodos en s, aceleraciones en fracción de g.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

Z = {"Z1": 0.10, "Z2": 0.25, "Z3": 0.35, "Z4": 0.45}
U = {"A1": 1.5, "A2": 1.5, "B": 1.3, "C": 1.0}
CT = {"porticos": 35.0, "dual": 60.0, "muros": 60.0, "mdl": 60.0}

# ----------------------------------------------------------------------------
# E.030-2018
# ----------------------------------------------------------------------------
S_2018 = {
    "Z4": {"S0": 0.80, "S1": 1.00, "S2": 1.05, "S3": 1.10},
    "Z3": {"S0": 0.80, "S1": 1.00, "S2": 1.15, "S3": 1.20},
    "Z2": {"S0": 0.80, "S1": 1.00, "S2": 1.20, "S3": 1.40},
    "Z1": {"S0": 0.80, "S1": 1.00, "S2": 1.60, "S3": 2.00},
}
TP_TL_2018 = {"S0": (0.3, 3.0), "S1": (0.4, 2.5), "S2": (0.6, 2.0),
              "S3": (1.0, 1.6)}
VS30_2018 = {"S0": (1500.0, np.inf), "S1": (500.0, 1500.0),
             "S2": (180.0, 500.0), "S3": (0.0, 180.0)}
R0_2018 = {"porticos": 8.0, "dual": 7.0, "muros": 6.0, "mdl": 4.0}
DRIFT_2018 = {"concreto": 0.007, "mdl": 0.005}

# ----------------------------------------------------------------------------
# E.030-2026 (RM 183-2026-VIVIENDA)
# ----------------------------------------------------------------------------
# Tabla 3: perfiles por Vs30 (m/s). S5 = suelos excepcionales (licuables,
# etc.), requieren estudio de sitio y no se incluyen.
VS30_2026 = {"S0": (800.0, np.inf), "S1": (550.0, 800.0),
             "S2": (350.0, 550.0), "S3": (200.0, 350.0), "S4": (0.0, 200.0)}
# Tabla 4: factor S. Las tuplas son rangos que se interpolan linealmente con
# Vs30 dentro del perfil (extremo izquierdo ↔ Vs30 mayor del rango).
S_2026 = {
    "Z4": {"S0": 0.80, "S1": 1.00, "S2": (1.00, 1.10), "S3": (1.10, 1.20),
           "S4": None},                       # Z4-S4: análisis de sitio
    "Z3": {"S0": 0.80, "S1": 1.00, "S2": (1.00, 1.15), "S3": (1.15, 1.20),
           "S4": 1.30},
    "Z2": {"S0": 0.80, "S1": 1.00, "S2": (1.00, 1.30), "S3": (1.30, 1.40),
           "S4": 1.70},
    "Z1": {"S0": 0.80, "S1": 1.00, "S2": (1.00, 1.30), "S3": (1.30, 1.60),
           "S4": 2.40},
}
# Tabla 5: TP y TL (rangos interpolados con Vs30)
TP_2026 = {"S0": 0.3, "S1": 0.4, "S2": (0.4, 0.6), "S3": (0.6, 0.9), "S4": 1.2}
TL_2026 = {"S0": 3.0, "S1": 2.5, "S2": (2.5, 2.0), "S3": (2.0, 1.6), "S4": 1.6}
# Sin Vs30: S2 → TP 0.6, TL 2.0 ; S3 → TP 0.9, TL 1.6 (extremo conservador)
R0_2026 = {"porticos": 8.0, "dual": 7.0, "muros": 6.0, "mdl": 3.5}
DRIFT_2026 = {"concreto": 0.007, "mdl": 0.004}

# Tiempo-historia (ambas versiones): distorsión ≤ 1.25 × Tabla de límites
DRIFT_TH_FACTOR = 1.25
MIN_REGISTROS_TH = {"2018": 3, "2026": 7}


def _interp_vs(valor, vs30, rango_vs):
    """Interpola un valor tabulado (escalar o (v_alto, v_bajo)) con Vs30."""
    if valor is None or not isinstance(valor, tuple):
        return valor
    v_alto_vs, v_bajo_vs = valor          # valor en Vs30 alto / Vs30 bajo
    lo, hi = rango_vs
    if vs30 is None:
        return v_bajo_vs                  # extremo conservador
    r = float(np.clip((vs30 - lo) / (hi - lo), 0.0, 1.0))
    return v_bajo_vs + r * (v_alto_vs - v_bajo_vs)


def clasificar_suelo_vs30(vs30: float, version: str = "2026") -> str:
    tabla = VS30_2026 if version == "2026" else VS30_2018
    for perfil, (lo, hi) in tabla.items():
        if lo <= vs30 < hi:
            return perfil
    return list(tabla)[-1]


@dataclass
class ParametrosE030:
    version: str = "2026"
    zona: str = "Z4"
    suelo: str = "S1"
    categoria: str = "C"
    sistema: str = "porticos"
    vs30: float | None = None    # para interpolar S, TP, TL (2026)
    regular: bool = True
    Ia: float = 1.0
    Ip: float = 1.0
    Ts: float | None = None      # periodo predominante (2026: A/B en Z4)
    tablas: dict = field(default_factory=dict, repr=False)

    def __post_init__(self):
        if self.version not in ("2018", "2026"):
            raise ValueError("version debe ser '2018' o '2026'")
        if self.version == "2026" and self.zona == "Z4" and self.suelo == "S4":
            raise ValueError("E.030-2026: Z4-S4 exige análisis de respuesta "
                             "de sitio; no se cubre con el espectro tabulado.")
        if self.version == "2026" and self.Ts is not None:
            self._aplicar_regla_Ts()

    # ------------------------------------------------------------------
    def _aplicar_regla_Ts(self):
        """Art. 14.8 (2026): si Ts ≥ 0.65·TP se pasa al perfil siguiente
        menos favorable (o se exige estudio de sitio)."""
        orden = ["S0", "S1", "S2", "S3", "S4"]
        while self.Ts >= 0.65 * self.TP_TL[0]:
            i = orden.index(self.suelo)
            if i + 1 >= len(orden) - (1 if self.zona == "Z4" else 0):
                raise ValueError("Ts excede 0.65·TP del último perfil "
                                 "aplicable: se requiere estudio de sitio.")
            self.suelo = orden[i + 1]
            self.vs30 = None   # el perfil ya no corresponde al Vs30 medido

    @property
    def Z(self) -> float:
        return Z[self.zona]

    @property
    def U(self) -> float:
        return U[self.categoria]

    @property
    def S(self) -> float:
        if self.version == "2018":
            return S_2018[self.zona][self.suelo]
        return _interp_vs(S_2026[self.zona][self.suelo], self.vs30,
                          VS30_2026[self.suelo])

    @property
    def TP_TL(self) -> tuple[float, float]:
        if self.version == "2018":
            return TP_TL_2018[self.suelo]
        r = VS30_2026[self.suelo]
        return (_interp_vs(TP_2026[self.suelo], self.vs30, r),
                _interp_vs(TL_2026[self.suelo], self.vs30, r))

    @property
    def R0(self) -> float:
        return (R0_2026 if self.version == "2026" else R0_2018)[self.sistema]

    @property
    def R(self) -> float:
        return self.R0 * self.Ia * self.Ip

    @property
    def drift_limite(self) -> float:
        tabla = DRIFT_2026 if self.version == "2026" else DRIFT_2018
        return tabla["mdl" if self.sistema == "mdl" else "concreto"]

    @property
    def drift_limite_th(self) -> float:
        """Límite para resultados tiempo-historia (1.25 × Tabla)."""
        return DRIFT_TH_FACTOR * self.drift_limite

    @property
    def requiere_Ts(self) -> bool:
        return (self.version == "2026" and self.zona == "Z4"
                and self.categoria in ("A1", "A2", "B"))

    # ------------------------------------------------------------------
    def C(self, T) -> np.ndarray:
        """Factor de amplificación sísmica C(T)."""
        T = np.atleast_1d(np.asarray(T, dtype=float))
        TP, TL = self.TP_TL
        Ts = np.maximum(T, 1e-9)
        return np.where(T < TP, 2.5,
                        np.where(T < TL, 2.5 * TP / Ts, 2.5 * TP * TL / Ts ** 2))

    def Sa(self, T, R: float | None = None) -> np.ndarray:
        """Sa = Z·U·C·S / R (fracción de g)."""
        R = self.R if R is None else R
        return self.Z * self.U * self.C(T) * self.S / R

    def Sa_elastico(self, T) -> np.ndarray:
        """Espectro con R = 1: objetivo de escalamiento tiempo-historia."""
        return self.Sa(T, R=1.0)

    def periodo_aproximado(self, hn: float) -> float:
        return hn / CT[self.sistema]

    def cortante_estatico(self, T: float, P: float) -> float:
        """V = Z·U·C·S·P / R con C/R ≥ 0.11."""
        CR = max(float(self.C(T)[0]) / self.R, 0.11)
        return self.Z * self.U * self.S * CR * P


def comparar_versiones(zona="Z4", vs30=450.0, categoria="C",
                       sistema="dual", T=(0.2, 0.5, 1.0, 2.0)):
    """Tabla comparativa 2018 vs 2026 para un mismo sitio (mismo Vs30)."""
    import pandas as pd
    filas = []
    for v in ("2018", "2026"):
        suelo = clasificar_suelo_vs30(vs30, v)
        p = ParametrosE030(version=v, zona=zona, suelo=suelo,
                           categoria=categoria, sistema=sistema, vs30=vs30)
        TP, TL = p.TP_TL
        fila = dict(version=v, perfil=suelo, S=round(p.S, 3), TP=round(TP, 3),
                    TL=round(TL, 3), R0=p.R0, deriva=p.drift_limite)
        for t in T:
            fila[f"Sa_R1({t}s)"] = round(float(p.Sa_elastico(t)[0]), 3)
        filas.append(fila)
    return pd.DataFrame(filas)


if __name__ == "__main__":
    for vs in (300.0, 450.0, 650.0):
        print(f"\nVs30 = {vs:.0f} m/s")
        print(comparar_versiones(vs30=vs).to_string(index=False))
    p = ParametrosE030(version="2026", suelo="S1", categoria="B", Ts=0.30)
    print("\nRegla Ts: S1 con Ts=0.30 s →", p.suelo, "TP,TL =", p.TP_TL)
