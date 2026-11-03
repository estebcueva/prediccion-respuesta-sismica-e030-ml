"""
arquetipos.py — Definición paramétrica de los 40 arquetipos estructurales.

Cada arquetipo es un edificio regular de concreto armado en planta rectangular
con grilla ortogonal de vanos. Los parámetros se muestrean con un hipercubo
latino estratificado por sistema estructural y número de pisos, con semilla
fija para que la población sea reproducible (criterio de Computabilidad, PCS).

Unidades base del proyecto: kN, m, s.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from scipy.stats import qmc

KGF_CM2_TO_KPA = 98.0665  # 1 kgf/cm² = 98.0665 kPa


@dataclass
class Arquetipo:
    id: str
    sistema: str             # "porticos" | "dual" | "muros"
    n_pisos: int
    h_piso: float            # m
    n_vanos_x: int
    n_vanos_y: int
    L_vano_x: float          # m
    L_vano_y: float          # m
    fc_kgcm2: float          # f'c en kg/cm²
    fy_kgcm2: float = 4200.0
    rho_muros: float = 0.0   # área de muros / área en planta, por dirección
    t_muro: float = 0.25     # m
    w_sismico: float = 10.0  # kPa (CM + 25 % CV, práctica peruana ~1 tf/m²)
    zona: str = "Z4"
    suelo: str = "S1"
    vs30_sitio: float = 600.0  # m/s, define S, TP y TL interpolados (E.030-2026)
    categoria: str = "C"

    # ---------------- propiedades derivadas ----------------
    @property
    def fc_kpa(self) -> float:
        return self.fc_kgcm2 * KGF_CM2_TO_KPA

    @property
    def fy_kpa(self) -> float:
        return self.fy_kgcm2 * KGF_CM2_TO_KPA

    @property
    def Lx(self) -> float:
        return self.n_vanos_x * self.L_vano_x

    @property
    def Ly(self) -> float:
        return self.n_vanos_y * self.L_vano_y

    @property
    def area_planta(self) -> float:
        return self.Lx * self.Ly

    @property
    def H(self) -> float:
        return self.n_pisos * self.h_piso

    @property
    def W_piso(self) -> float:
        """Peso sísmico por piso (kN)."""
        return self.w_sismico * self.area_planta

    @property
    def W_total(self) -> float:
        return self.W_piso * self.n_pisos

    @property
    def Ec_kpa(self) -> float:
        """E.060: Ec = 15000·sqrt(f'c) [kg/cm²] → kPa."""
        return 15000.0 * np.sqrt(self.fc_kgcm2) * KGF_CM2_TO_KPA

    def to_dict(self) -> dict:
        d = asdict(self)
        d.update(H=self.H, area_planta=self.area_planta, W_total=self.W_total)
        return d


# ----------------------------------------------------------------------------
# Generación de la población
# ----------------------------------------------------------------------------
RANGOS_PISOS = {"porticos": (3, 8), "dual": (5, 15), "muros": (4, 15)}
RANGOS_RHO_MUROS = {"porticos": (0.0, 0.0), "dual": (0.008, 0.018),
                    "muros": (0.018, 0.030)}
N_POR_SISTEMA = {"porticos": 13, "dual": 14, "muros": 13}   # total = 40


def generar_arquetipos(seed: int = 2026) -> list[Arquetipo]:
    """Población de 40 arquetipos (LHS estratificado por sistema).

    Variables muestreadas por arquetipo (5D):
      u0 → número de pisos dentro del rango del sistema
      u1 → altura de entrepiso 2.7–3.5 m
      u2 → luz de vano 4–7 m (x); y = x·[0.8–1.2] acotado a 4–7 m
      u3 → f'c 210–350 kg/cm² (redondeado a 210, 245, 280, 315, 350)
      u4 → densidad de muros (dual/muros) y suelo S1/S2
    """
    rng = np.random.default_rng(seed)
    out: list[Arquetipo] = []
    fc_clases = np.array([210, 245, 280, 315, 350], dtype=float)
    for sistema, n in N_POR_SISTEMA.items():
        sampler = qmc.LatinHypercube(d=5, seed=rng)
        U = sampler.random(n)
        p_lo, p_hi = RANGOS_PISOS[sistema]
        r_lo, r_hi = RANGOS_RHO_MUROS[sistema]
        for k, u in enumerate(U):
            n_pisos = int(np.clip(np.round(p_lo + u[0] * (p_hi - p_lo)), p_lo, p_hi))
            h_piso = round(2.7 + 0.8 * u[1], 2)
            Lx = round(4.0 + 3.0 * u[2], 2)
            Ly = round(float(np.clip(Lx * (0.8 + 0.4 * rng.random()), 4.0, 7.0)), 2)
            fc = float(fc_clases[min(int(u[3] * 5), 4)])
            rho = round(r_lo + u[4] * (r_hi - r_lo), 4)
            # Suelo E.030-2026 (Tabla 3): S1 = Vs30 550–800 m/s (grava de
            # Lima), S2 = 350–550 m/s. Vs30 se muestrea dentro del rango.
            suelo = "S1" if rng.random() < 0.5 else "S2"
            vs30 = float(rng.uniform(550, 800) if suelo == "S1"
                         else rng.uniform(350, 550))
            # Categoría de uso: C (vivienda/oficinas), B (importantes),
            # A2 (esenciales no hospitalarias). A1 en Z4 exige aislamiento
            # sísmico (E.030), por eso se excluye de la población.
            categoria = str(rng.choice(["C", "B", "A2"], p=[0.60, 0.25, 0.15]))
            nvx = int(rng.integers(3, 6))
            nvy = int(rng.integers(3, 6))
            out.append(Arquetipo(
                id=f"{sistema[:3].upper()}-{k + 1:02d}",
                sistema=sistema, n_pisos=n_pisos, h_piso=h_piso,
                n_vanos_x=nvx, n_vanos_y=nvy, L_vano_x=Lx, L_vano_y=Ly,
                fc_kgcm2=fc, rho_muros=rho, suelo=suelo, vs30_sitio=round(vs30),
                categoria=categoria,
            ))
    return out


def tabla_arquetipos(arqs: list[Arquetipo]) -> pd.DataFrame:
    return pd.DataFrame([a.to_dict() for a in arqs])


if __name__ == "__main__":
    arqs = generar_arquetipos()
    df = tabla_arquetipos(arqs)
    print(len(df), "arquetipos")
    print(df.groupby("sistema")[["n_pisos", "fc_kgcm2", "rho_muros"]]
            .agg(["min", "max"]))
    df.to_csv("../data/arquetipos.csv", index=False)
