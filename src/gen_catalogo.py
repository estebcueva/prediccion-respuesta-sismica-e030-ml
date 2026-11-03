"""
gen_catalogo.py — Catálogo de 40 arquetipos de CA para el dataset sísmico.

Matriz paramétrica estratificada (LHS con semilla fija) por sistema:
  pórticos (R0=8) 13 · dual (R0=7) 14 · muros (R0=6) 13
f'c ∈ {210, 280, 350} kg/cm²; h = 2.7–3.5 m; 3–5 vanos; luces 4–7 m;
densidad de muros 0 % / 0.5–1.5 % / 1.5–3.0 %; Z4; S1/S2 (E.030-2026);
U = 1.0 (C), 1.3 (B), 1.5 (A2; solo dual/muros, E.030 Tabla de
categoría y sistema estructural).

Para cada arquetipo se calcula:
  * W (peso sísmico E.030: CM + %CV por categoría)
  * T1 aproximado E.030 (hn/CT) y T1 modal (modelo elástico 3D OpenSeesPy,
    tras el control de deriva E.030-2026)
  * Parámetros E.030-2026: S, TP, TL interpolados con Vs30; Ts de referencia;
    C(T1), Sa elástico (R=1), V/W de diseño
  * % del cortante basal tomado por los muros (verifica la clasificación
    pórticos / dual / muros de la E.030)
"""
import sys
import time
from pathlib import Path

import numpy as np
import openseespy.opensees as ops
import pandas as pd
from scipy.stats import qmc

sys.path.insert(0, str(Path(__file__).parent))
from arquetipos import Arquetipo                       # noqa: E402
from e030 import CT, ParametrosE030                     # noqa: E402
import modelo_opensees as mo                           # noqa: E402

SEED = 2026
FC = np.array([210.0, 280.0, 350.0])
CM_KPA = 7.8                                    # carga muerta total por piso
CV_KPA = {"C": 2.0, "B": 2.5, "A2": 3.0}        # E.020 (vivienda/aulas/esencial)
ALFA_CV = {"C": 0.25, "B": 0.50, "A2": 0.50}    # E.030: % de CV en el peso
U_DE = {"C": 1.0, "B": 1.3, "A2": 1.5}
SIST = {
    #          n   pisos     rho_w (%)      categorías (C, B, A2)
    "porticos": (13, (3, 8),  (0.0, 0.0),   (9, 4, 0)),
    "dual":     (14, (6, 15), (30., 60.),   (8, 4, 2)),   # % V en muros (objetivo)
    "muros":    (13, (4, 15), (1.0, 3.0),   (7, 3, 3)),
}
H_SUELO_TS = 30.0   # m, columna de suelo para Ts de referencia = 4·H/Vs30


def generar():
    rng = np.random.default_rng(SEED)
    arqs = []
    for sistema, (n, (p0, p1), (r0, r1), cats) in SIST.items():
        U = qmc.LatinHypercube(d=7, seed=rng).random(n)
        categorias = (["C"] * cats[0] + ["B"] * cats[1] + ["A2"] * cats[2])
        rng.shuffle(categorias)
        for k, u in enumerate(U):
            pisos = int(np.clip(np.floor(p0 + u[0] * (p1 - p0 + 1)), p0, p1))
            h = round(2.7 + 0.8 * u[1], 2)
            Lx = round(4.0 + 3.0 * u[2], 2)
            Ly = round(float(np.clip(Lx * (0.85 + 0.30 * u[6]), 4.0, 7.0)), 2)
            fc = float(FC[min(int(u[3] * 3), 2)])
            # Pórticos: ρw = 0. Muros: ρw muestreada en [1.0, 3.0] %.
            # Dual: se muestrea el % de cortante objetivo en los muros
            # (30–60 %, dentro del 20–70 % de la E.030); ρw se calibra
            # después (calibrar_dual) y resulta una salida del diseño.
            if sistema == "muros":
                rho = round((r0 + u[4] * (r1 - r0)) / 100.0, 4)
            else:
                rho = 0.0
            pct_obj = (r0 + u[4] * (r1 - r0)) if sistema == "dual" else None
            suelo = "S1" if u[5] < 0.5 else "S2"
            # Vs30 dentro del rango del perfil (E.030-2026, Tabla 3)
            v = (u[5] * 2) % 1.0
            vs30 = round(550 + 250 * v) if suelo == "S1" else round(350 + 200 * v)
            cat = categorias[k]
            a = Arquetipo(
                id=f"{sistema[:3].upper()}-{k + 1:02d}", sistema=sistema,
                n_pisos=pisos, h_piso=h,
                n_vanos_x=int(rng.integers(3, 6)), n_vanos_y=int(rng.integers(3, 6)),
                L_vano_x=Lx, L_vano_y=Ly, fc_kgcm2=fc, rho_muros=rho,
                w_sismico=CM_KPA + ALFA_CV[cat] * CV_KPA[cat],
                suelo=suelo, vs30_sitio=float(vs30), categoria=cat)
            arqs.append((a, pct_obj))
    return arqs


def porcentaje_cortante_muros(a, s, p, T):
    """% del cortante basal estático (dirección X) que toman los muros."""
    muros = mo.construir_modelo(a, s, tipo="elastico")
    if not muros:
        return 0.0
    ops.remove("loadPattern", 1)
    V = p.cortante_estatico(T, a.W_total)
    k = 1.0 if T <= 0.5 else min(0.75 + 0.5 * T, 2.0)
    z = np.array([a.h_piso * i for i in range(1, a.n_pisos + 1)])
    alfa = z ** k / np.sum(z ** k)
    ops.timeSeries("Linear", 100)
    ops.pattern("Plain", 100, 100)
    for i, fi in enumerate(alfa * V, start=1):
        ops.load(mo._tag_master(i), fi, 0, 0, 0, 0, 0)
    ops.system("UmfPack"); ops.numberer("RCM"); ops.constraints("Transformation")
    ops.test("NormDispIncr", 1e-8, 10); ops.algorithm("Linear")
    ops.integrator("LoadControl", 1.0); ops.analysis("Static"); ops.analyze(1)
    ops.reactions()
    base = mo.nodos_base(a, len(muros))
    n_col = (a.n_vanos_x + 1) * (a.n_vanos_y + 1)
    v_tot = -sum(ops.nodeReaction(nd, 1) for nd in base)
    v_mur = -sum(ops.nodeReaction(nd, 1) for nd in base[n_col:])
    ops.wipe()
    return 100.0 * v_mur / v_tot


def calibrar_dual(a, pct_obj, n_iter=12):
    """Ajusta la longitud de los 2 muros por dirección (y con ella ρw) hasta
    que los muros tomen pct_obj % del cortante basal (bisección en Lw)."""
    lo, hi = 1.5, mo._L_muro_max(a, "x")
    mejor = None
    for _ in range(n_iter):
        Lw = 0.5 * (lo + hi)
        a.rho_muros = round(2 * Lw * a.t_muro / a.area_planta, 5)
        s = mo.disenar(a, version_e030="2026")
        p = ParametrosE030(version="2026", zona=a.zona, suelo=a.suelo,
                           categoria=a.categoria, sistema=a.sistema,
                           vs30=a.vs30_sitio)
        pct = porcentaje_cortante_muros(a, s, p, s.T1x)
        if mejor is None or abs(pct - pct_obj) < abs(mejor[2] - pct_obj):
            mejor = (a.rho_muros, s, pct)
        if abs(pct - pct_obj) < 2.0:
            break
        lo, hi = (Lw, hi) if pct < pct_obj else (lo, Lw)
    a.rho_muros = mejor[0]
    return mejor[1]


def clasificar(pct):
    """E.030: pórticos ≥ 80 % en columnas; muros ≥ 70 % en muros; dual entre."""
    if pct <= 20:
        return "porticos"
    if pct >= 70:
        return "muros"
    return "dual"


def main():
    t0 = time.time()
    filas = []
    for a, pct_obj in generar():
        s = (calibrar_dual(a, pct_obj) if a.sistema == "dual"
             else mo.disenar(a, version_e030="2026"))
        p = ParametrosE030(version="2026", zona=a.zona, suelo=a.suelo,
                           categoria=a.categoria, sistema=a.sistema,
                           vs30=a.vs30_sitio)
        T1 = max(s.T1x, s.T1y)
        TP, TL = p.TP_TL
        Ts = 4 * H_SUELO_TS / a.vs30_sitio
        pct = porcentaje_cortante_muros(a, s, p, s.T1x)
        filas.append(dict(
            id_arquetipo=a.id, sistema=a.sistema, R0=p.R0, n_pisos=a.n_pisos,
            h_piso_m=a.h_piso, H_m=round(a.H, 2),
            vanos_x=a.n_vanos_x, vanos_y=a.n_vanos_y,
            luz_x_m=a.L_vano_x, luz_y_m=a.L_vano_y,
            area_planta_m2=round(a.area_planta, 1),
            fc_kgcm2=int(a.fc_kgcm2), densidad_muros_pct=round(100 * a.rho_muros, 2),
            categoria=a.categoria, U=p.U, w_kPa=round(a.w_sismico, 2),
            W_kN=round(a.W_total, 0),
            col_m=s.b_col, viga_m=f"{s.b_viga:.2f}x{s.h_viga:.2f}",
            muros_x=f"{s.n_muros_x}x{s.L_muro:.1f}" if s.n_muros_x else "-",
            muros_y=f"{s.n_muros_y}x{s.L_muro_y:.1f}" if s.n_muros_y else "-",
            t_muro_m=s.t_muro if s.n_muros_x else np.nan,
            T1_E030_s=round(a.H / CT[a.sistema], 3),
            T1x_s=round(s.T1x, 3), T1y_s=round(s.T1y, 3), T1_s=round(T1, 3),
            suelo=a.suelo, Vs30_ms=int(a.vs30_sitio), S=round(p.S, 3),
            TP_s=round(TP, 3), TL_s=round(TL, 3), Ts_ref_s=round(Ts, 3),
            Ts_lim_s=round(0.65 * TP, 3), Ts_exigido=int(p.requiere_Ts),
            Z=p.Z, C_T1=round(float(p.C(T1)[0]), 3),
            Sa_R1_g=round(float(p.Sa_elastico(T1)[0]), 3),
            V_W=round(p.cortante_estatico(T1, 1.0), 4),
            deriva_diseno=round(s.drift_inelastico, 4),
            pct_V_muros=round(pct, 1), sistema_por_V=clasificar(pct),
        ))
    df = pd.DataFrame(filas)
    df.to_csv(Path(__file__).parents[1] / "data" / "catalogo_arquetipos.csv", index=False)
    print(f"{time.time() - t0:.0f} s")
    print(df.to_string(index=False))
    print("\nCumplen deriva 0.007:", (df.deriva_diseno <= 0.007).all())
    print("Ts < 0.65 TP en todos:", (df.Ts_ref_s < df.Ts_lim_s).all())
    print("Clasificación por cortante coincide:",
          (df.sistema == df.sistema_por_V).sum(), "de", len(df))
    print(df.groupby("sistema")[["fc_kgcm2"]].value_counts().unstack())
    print(df.groupby(["sistema", "categoria"]).size().unstack(fill_value=0))
    print(df.groupby(["sistema", "suelo"]).size().unstack(fill_value=0))


if __name__ == "__main__":
    main()
