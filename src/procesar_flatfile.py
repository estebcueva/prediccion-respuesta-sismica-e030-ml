"""
procesar_flatfile.py — Del flatfile PEER NGA-West2 a registros_seleccionados.csv.

Pasos (docs/02, sección 2):
  F1 Mw ≥ 6.0 · F2 10 ≤ Rrup ≤ 100 km · F3 350 ≤ Vs30 < 800 m/s (S1 ∪ S2, E.030-2026)
  F4 frecuencia mínima utilizable ≤ 0.25 Hz · F5 sin pulso (lista opcional)
  F6 máximo 3 registros por evento
  → selección estratificada por bins Mw × Rrup con cuotas (100 pares)
  → partición por evento: 80 % train / 20 % test (semilla fija)
  → asignación de slots R001…R100 (enlace con matriz_combinaciones.csv)

Uso:
    python src/procesar_flatfile.py --flatfile data/NGA_West2_flatfile.csv \
        [--at2 data/at2] [--pulsos data/rsn_pulsos.txt] [--n 100]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from registros import (FiltroSeleccion, cargar_flatfile, leer_at2,   # noqa: E402
                       rsn_a_archivos, seleccionar_registros)

RAIZ = Path(__file__).resolve().parents[1]
SEMILLA = 2026
BINS_MW = [6.0, 6.5, 7.0, 7.5, 10.0]
ETQ_MW = ["6.0-6.5", "6.5-7.0", "7.0-7.5", ">=7.5"]
BINS_R = [10.0, 30.0, 60.0, 100.0001]
ETQ_R = ["10-30", "30-60", "60-100"]
# Cuotas objetivo (docs/02, sección 2.2): filas = Mw, columnas = Rrup
CUOTAS = pd.DataFrame([[9, 9, 7], [11, 13, 11], [6, 10, 9], [4, 6, 5]],
                      index=ETQ_MW, columns=ETQ_R)


def asignar_bins(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["bin_Mw"] = pd.cut(df.mw, BINS_MW, right=False, labels=ETQ_MW).astype(str)
    df["bin_Rrup"] = pd.cut(df.rrup, BINS_R, right=False, labels=ETQ_R).astype(str)
    return df


def seleccion_estratificada(cand: pd.DataFrame, n: int, rng) -> pd.DataFrame:
    """Llena las cuotas por bin priorizando eventos aún no usados; el faltante
    de un bin pasa al bin vecino de distancia en la misma fila de Mw."""
    cuotas = (CUOTAS * n / CUOTAS.values.sum()).round().astype(int)
    elegidos, eventos_usados = [], set()
    for mw in ETQ_MW:
        arrastre = 0
        for r in ETQ_R:
            meta = cuotas.loc[mw, r] + arrastre
            pool = cand[(cand.bin_Mw == mw) & (cand.bin_Rrup == r)]
            pool = pool.sample(frac=1.0, random_state=int(rng.integers(1e9)))
            nuevos = pool[~pool.eqid.isin(eventos_usados)]
            repet = pool[pool.eqid.isin(eventos_usados)]
            toma = pd.concat([nuevos, repet]).head(meta)
            elegidos.append(toma)
            eventos_usados |= set(toma.eqid)
            arrastre = meta - len(toma)
        if arrastre:
            print(f"[aviso] bin Mw {mw}: faltaron {arrastre} pares tras recorrer las distancias")
    sel = pd.concat(elegidos)
    return sel.drop_duplicates("rsn")


def particionar(sel: pd.DataFrame, rng, frac_test: float = 0.20) -> pd.Series:
    eventos = np.array(sorted(sel.eqid.unique()))
    rng.shuffle(eventos)
    n_test = max(1, int(round(frac_test * len(eventos))))
    test = set(eventos[:n_test])
    return sel.eqid.map(lambda e: "test" if e in test else "train")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--flatfile", required=True)
    ap.add_argument("--at2", default=None, help="carpeta con RSN*_*.AT2 (opcional)")
    ap.add_argument("--pulsos", default=None, help="archivo de texto con RSN a excluir")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--salida", default=str(RAIZ / "data" / "registros_seleccionados.csv"))
    args = ap.parse_args()
    rng = np.random.default_rng(SEMILLA)

    ff = cargar_flatfile(args.flatfile)
    excl = tuple(int(x) for x in Path(args.pulsos).read_text().split()) if args.pulsos else ()
    filtro = FiltroSeleccion(mw_min=6.0, rrup_min=10.0, rrup_max=100.0,
                             suelos=("S1", "S2"), max_por_evento=3, T_max_util=4.0,
                             excluir_rsn=excl, version_e030="2026", semilla=SEMILLA)
    cand = asignar_bins(seleccionar_registros(ff, filtro))
    print(f"Flatfile: {len(ff)} registros → candidatos tras F1–F6: {len(cand)} "
          f"({cand.eqid.nunique()} eventos)")

    sel = seleccion_estratificada(cand, args.n, rng)
    sel["particion"] = particionar(sel, rng)
    sel = sel.sort_values(["bin_Mw", "bin_Rrup", "rsn"]).reset_index(drop=True)
    sel["slot_registro"] = [f"R{i:03d}" for i in range(1, len(sel) + 1)]
    sel["dominio"] = "NGA-West2"

    for c in ("archivo_h1", "archivo_h2", "dt_s", "npts"):
        sel[c] = None
    if args.at2:
        for i, r in sel.iterrows():
            h = rsn_a_archivos(args.at2, int(r.rsn))
            if len(h) >= 2:
                a, dt = leer_at2(h[0])
                sel.loc[i, ["archivo_h1", "archivo_h2", "dt_s", "npts"]] = \
                    [h[0].name, h[1].name, dt, len(a)]

    ren = {"mw": "Mw", "rrup": "Rrup_km", "rjb": "Rjb_km", "vs30": "Vs30_est_ms",
           "f_util": "f_util_hz", "suelo_e030": "suelo_e030"}
    sel = sel.rename(columns=ren)
    cols = ["slot_registro", "rsn", "eqid", "evento", "anio", "Mw", "mecanismo",
            "Rrup_km", "Rjb_km", "Vs30_est_ms", "suelo_e030", "f_util_hz",
            "bin_Mw", "bin_Rrup", "archivo_h1", "archivo_h2", "dt_s", "npts",
            "dominio", "particion"]
    sel = sel[[c for c in cols if c in sel.columns]]
    sel.to_csv(args.salida, index=False)

    # ---------------- reporte de control ----------------
    print(f"\nSeleccionados: {len(sel)} pares de {sel.eqid.nunique()} eventos "
          f"(objetivo {args.n} pares, ≥ 34 eventos)")
    print("Pares por bin (Mw × Rrup):")
    print(pd.crosstab(sel.bin_Mw, sel.bin_Rrup, margins=True).to_string())
    print("Suelo:", sel.suelo_e030.value_counts().to_dict())
    print("Partición (pares):", sel.particion.value_counts().to_dict(),
          "· eventos test:", sel.loc[sel.particion == "test", "eqid"].nunique())
    assert sel.groupby("eqid").particion.nunique().max() == 1, "evento en 2 particiones"
    assert sel.groupby("eqid").size().max() <= 3, "más de 3 registros por evento"
    if len(sel) < args.n:
        print(f"[aviso] solo {len(sel)} pares: revisar filtros o ampliar el flatfile")
    print(f"→ {args.salida}")


if __name__ == "__main__":
    main()
