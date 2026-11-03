"""
validar_integridad.py — Verificación automática de integridad de
dataset_sismico_peru.csv (esquema de 57 columnas, docs/03).

Comprueba:
  * R1–R13 : las 13 reglas de integridad del diccionario de datos (docs/03, sección 4).
  * D1–D5  : controles de dominio físico y normativo adicionales:
      D1 sin nulos en las features críticas y los targets
      D2 Vb/W dentro de [0.02, 1.50]
      D3 R0 consistente con el sistema (pórticos 8, dual 7, muros 6)
      D4 flag_sf_rango = 0 exactamente cuando sf_base está fuera de [0.2, 5.0]
      D5 densidad de muros de los duales dentro de [0.20, 0.90] %

Uso:
    python src/validar_integridad.py                      # data/dataset_sismico_peru.csv
    python src/validar_integridad.py data/dataset_sismico_peru_EJEMPLO.csv
    python src/validar_integridad.py <csv> --estricto     # código de salida 1 si algo falla

Las filas con convergencia = 0 (falla numérica) se reportan pero no invalidan
el archivo: se excluyen del entrenamiento, no se borran.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
CSV_POR_DEFECTO = RAIZ / "data" / "dataset_sismico_peru.csv"

COLUMNAS = (
    "id_caso,id_arquetipo,id_registro,eqid,nivel_escala,orientacion,dominio,"
    "particion,fuente,version_e030,sistema,R0,n_pisos,H_m,h_piso_m,"
    "area_planta_m2,T1_s,W_kN,densidad_muros_pct,fc_kgcm2,Z,U,S,TP_s,TL_s,"
    "Ts_s,C_T1,Vest_W,Sa_dis_R1_g,PGA_g,PGV_ms,Sa_T1_g,Sa_avg_g,Arias_ms,"
    "D5_95_s,HI_m,ASI_gs,Mw,Rrup_km,Vs30_est_ms,factor_escala,MIDR,ln_MIDR,"
    "cumple_0007,cumple_00875,Vb_W,colapso,convergencia,sf_base,flag_sf_rango,"
    "MIDR_x,MIDR_y,piso_critico,Vb_x_kN,Vb_y_kN,deriva_residual,t_cpu_s"
).split(",")

FEATURES_X = [
    "sistema", "R0", "n_pisos", "H_m", "h_piso_m", "area_planta_m2", "T1_s",
    "W_kN", "densidad_muros_pct", "fc_kgcm2",                       # estructurales (10)
    "Z", "U", "S", "TP_s", "TL_s", "Ts_s", "C_T1", "Vest_W", "Sa_dis_R1_g",  # E.030 (9)
    "PGA_g", "PGV_ms", "Sa_T1_g", "Sa_avg_g", "Arias_ms", "D5_95_s",
    "HI_m", "ASI_gs",                                               # intensidad (8)
    "Mw", "Rrup_km", "Vs30_est_ms", "factor_escala",                # sismo (4)
]
TARGETS = ["MIDR", "ln_MIDR", "Vb_W"]
R0_ESPERADO = {"porticos": 8, "dual": 7, "muros": 6}
LIM_0007, LIM_00875, MIDR_COLAPSO = 0.007, 0.00875, 0.10
SF_MIN, SF_MAX = 0.2, 5.0
VBW_MIN, VBW_MAX = 0.02, 1.50
RHO_DUAL_MIN, RHO_DUAL_MAX = 0.20, 0.90
TOL = 1e-4


@dataclass
class Resultado:
    codigo: str
    nombre: str
    ok: bool
    detalle: str
    filas: list


def _filas(mask: pd.Series, d: pd.DataFrame, n: int = 5) -> list:
    return d.loc[mask, "id_caso"].head(n).tolist()


def _rel_ptp(x: pd.Series) -> float:
    m = float(np.mean(x))
    return float(np.ptp(x)) / abs(m) if m else float(np.ptp(x))


# ---------------------------------------------------------------------------
# R1–R13
# ---------------------------------------------------------------------------
def reglas_integridad(d: pd.DataFrame) -> list[Resultado]:
    out = []

    dup = d.id_caso.duplicated(keep=False)
    out.append(Resultado("R1", "id_caso único", not dup.any(),
                         f"{int(dup.sum())} filas con id repetido", _filas(dup, d)))

    n_part = d.groupby("eqid").particion.nunique()
    malos = n_part[n_part > 1].index
    m = d.eqid.isin(malos)
    out.append(Resultado("R2", "cada eqid en una sola partición (sin fuga)",
                         len(malos) == 0, f"eventos en >1 partición: {list(malos)[:10]}",
                         _filas(m, d)))

    m = ~np.isclose(d.ln_MIDR, np.log(d.MIDR.clip(lower=1e-12)), atol=1e-5)
    out.append(Resultado("R3", "ln_MIDR = ln(MIDR)", not m.any(),
                         f"{int(m.sum())} filas incoherentes", _filas(m, d)))

    m = ((d.cumple_0007 == 1) != (d.MIDR <= LIM_0007)) | \
        ((d.cumple_00875 == 1) != (d.MIDR <= LIM_00875))
    out.append(Resultado("R4", "marcas cumple_0007 / cumple_00875 coherentes",
                         not m.any(), f"{int(m.sum())} filas incoherentes", _filas(m, d)))

    nc = d.colapso == 0
    m = nc & ~np.isclose(d.MIDR, d[["MIDR_x", "MIDR_y"]].max(axis=1), rtol=TOL)
    out.append(Resultado("R5", "sin colapso: MIDR = max(MIDR_x, MIDR_y)", not m.any(),
                         f"{int(m.sum())} filas incoherentes", _filas(m, d)))

    m = (d.colapso == 1) & ~np.isclose(d.MIDR, MIDR_COLAPSO)
    out.append(Resultado("R6", "colapso: MIDR = 0.10", not m.any(),
                         f"{int(m.sum())} filas con colapso y MIDR ≠ 0.10", _filas(m, d)))

    m = ~np.isclose(d.factor_escala, d.nivel_escala * d.sf_base, rtol=TOL)
    out.append(Resultado("R7", "factor_escala = nivel_escala · sf_base", not m.any(),
                         f"{int(m.sum())} filas incoherentes", _filas(m, d)))

    g = d.assign(pga0=d.PGA_g / d.factor_escala,
                 ia0=d.Arias_ms / d.factor_escala ** 2).groupby(["id_arquetipo", "id_registro"])
    malos = [k for k, x in g if (x.D5_95_s.nunique() > 1 or _rel_ptp(x.pga0) > TOL
                                 or _rel_ptp(x.ia0) > TOL)]
    out.append(Resultado("R8", "IM escaladas coherentes entre niveles (D5-95, PGA, Arias)",
                         not malos, f"pares (arquetipo, registro) incoherentes: {malos[:5]}", []))

    pga0 = (d.PGA_g / d.factor_escala).groupby(d.id_registro).agg(_rel_ptp)
    malos = list(pga0[pga0 > TOL].index)
    out.append(Resultado("R9", "PGA sin escalar única por registro", not malos,
                         f"registros incoherentes: {malos[:10]}", []))

    cols_bc = FEATURES_X[:19]
    nun = d.groupby("id_arquetipo")[cols_bc].nunique(dropna=False)
    malos = list(nun.index[(nun > 1).any(axis=1)])
    out.append(Resultado("R10", "bloques B y C constantes por arquetipo", not malos,
                         f"arquetipos incoherentes: {malos[:10]}", []))

    sa = d.Z * d.U * d.C_T1 * d.S
    ve = np.maximum(d.Sa_dis_R1_g / d.R0, 0.11 * d.Z * d.U * d.S)
    m = ~np.isclose(d.Sa_dis_R1_g, sa, rtol=3e-3) | ~np.isclose(d.Vest_W, ve, rtol=3e-3)
    out.append(Resultado("R11", "Sa_dis = Z·U·C·S y Vest/W = max(ZUCS/R, 0.11·ZUS)",
                         not m.any(), f"{int(m.sum())} filas incoherentes", _filas(m, d)))

    m = (d[["Vb_W", "MIDR", "T1_s"]] <= 0).any(axis=1)
    out.append(Resultado("R12", "MIDR, Vb/W y T1 positivos", not m.any(),
                         f"{int(m.sum())} filas con valores ≤ 0", _filas(m, d)))

    m = (d.dominio == "Peru_subduccion") != (d.particion == "valid_ext")
    out.append(Resultado("R13", "dominio Perú ⇔ partición valid_ext", not m.any(),
                         f"{int(m.sum())} filas incoherentes", _filas(m, d)))
    return out


# ---------------------------------------------------------------------------
# D1–D5
# ---------------------------------------------------------------------------
def controles_dominio(d: pd.DataFrame) -> list[Resultado]:
    out = []
    criticas = FEATURES_X + TARGETS
    nul = d[criticas].isna()
    m = nul.any(axis=1)
    cols = list(nul.columns[nul.any()])
    out.append(Resultado("D1", "sin nulos en las 31 features y los targets", not m.any(),
                         f"{int(m.sum())} filas con nulos; columnas: {cols}", _filas(m, d)))

    usar = d.colapso == 0          # Vb/W no es representativo en colapso
    m = usar & ~d.Vb_W.between(VBW_MIN, VBW_MAX)
    out.append(Resultado("D2", f"Vb/W en [{VBW_MIN}, {VBW_MAX}] (casos sin colapso)",
                         not m.any(), f"{int(m.sum())} filas fuera de rango", _filas(m, d)))

    m = d.R0 != d.sistema.map(R0_ESPERADO)
    out.append(Resultado("D3", "R0: pórticos 8 · dual 7 · muros 6", not m.any(),
                         f"{int(m.sum())} filas incoherentes", _filas(m, d)))

    fuera = ~d.sf_base.between(SF_MIN, SF_MAX)
    m = (d.flag_sf_rango == 1) == fuera
    out.append(Resultado("D4", f"flag_sf_rango = 0 ⇔ sf_base ∉ [{SF_MIN}, {SF_MAX}]",
                         not m.any(), f"{int(m.sum())} filas con marca incorrecta", _filas(m, d)))

    dual = d.sistema == "dual"
    m = dual & ~d.densidad_muros_pct.between(RHO_DUAL_MIN, RHO_DUAL_MAX)
    out.append(Resultado("D5", f"ρw de duales en [{RHO_DUAL_MIN}, {RHO_DUAL_MAX}] %",
                         not m.any(), f"{int(m.sum())} filas fuera de rango", _filas(m, d)))
    return out


# ---------------------------------------------------------------------------
def validar(ruta: Path) -> tuple[list[Resultado], pd.DataFrame]:
    d = pd.read_csv(ruta)
    faltan = [c for c in COLUMNAS if c not in d.columns]
    if faltan:
        raise SystemExit(f"ERROR de esquema: faltan columnas {faltan}")
    extra = [c for c in d.columns if c not in COLUMNAS]
    if extra:
        print(f"[aviso] columnas no previstas en el esquema: {extra}")
    return reglas_integridad(d) + controles_dominio(d), d


def reporte(res: list[Resultado], d: pd.DataFrame, ruta: Path) -> int:
    ancho = 72
    print("=" * ancho)
    print(f" VERIFICACIÓN DE INTEGRIDAD — {ruta.name}")
    print(f" {len(d)} filas · {d.shape[1]} columnas · {d.id_arquetipo.nunique()} arquetipos · "
          f"{d.id_registro.nunique()} registros · {d.eqid.nunique()} eventos")
    fuentes = ", ".join(f"{k}={v}" for k, v in d.fuente.value_counts().items())
    print(f" fuente: {fuentes}")
    print("=" * ancho)
    for r in res:
        print(f" [{'PASS' if r.ok else 'FAIL'}] {r.codigo:<4} {r.nombre}")
        if not r.ok:
            print(f"        → {r.detalle}")
            if r.filas:
                print(f"        → ejemplos: {r.filas}")
    n_fail = sum(not r.ok for r in res)
    print("-" * ancho)
    print(f" Resumen: {len(res) - n_fail}/{len(res)} PASS · {n_fail} FAIL")
    nconv = int((d.convergencia == 0).sum())
    ncol = int((d.colapso == 1).sum())
    nsf = int((d.flag_sf_rango == 0).sum())
    print(f" Informativo: {ncol} colapsos · {nconv} fallas numéricas (excluir del "
          f"entrenamiento) · {nsf} casos con sf fuera de rango")
    if (d.fuente == "ilustrativo").any():
        print(" AVISO: hay filas con fuente = 'ilustrativo' (acelerogramas sintéticos).")
        print("        No deben mezclarse con el dataset de entrenamiento real.")
    print("=" * ancho)
    return n_fail


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("csv", nargs="?", default=str(CSV_POR_DEFECTO))
    ap.add_argument("--estricto", action="store_true",
                    help="termina con código 1 si alguna regla falla")
    args = ap.parse_args()
    ruta = Path(args.csv)
    if not ruta.exists():
        raise SystemExit(f"No existe {ruta}. ¿Corriste la campaña NLTHA? "
                         f"Para probar: python src/validar_integridad.py "
                         f"data/dataset_sismico_peru_EJEMPLO.csv")
    res, d = validar(ruta)
    n_fail = reporte(res, d, ruta)
    if args.estricto and n_fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
