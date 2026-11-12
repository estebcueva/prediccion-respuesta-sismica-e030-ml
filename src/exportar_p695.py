"""
exportar_p695.py — Set lejano (far-field) de FEMA P695 → data/at2 + registros_seleccionados.csv

Alternativa a la descarga desde la web de PEER (que no atiende fines de semana):
los 22 pares del set "far-field" de FEMA P695 (FEMA, 2009) son registros de la
base PEER NGA (mismos RSN que en NGA-West2) y se distribuyen en el paquete de
Python `fema-p695` (PyPI, licencia MIT). Este script:

  1. escribe cada componente horizontal como archivo PEER .AT2 en data/at2/
     (RSN<n>_<EVENTO>_<COMP>.AT2, aceleración en g), que lee registros.leer_at2;
  2. genera data/registros_seleccionados.csv con las columnas que usa
     campana_nltha.py (rsn, eqid, Mw, Rrup_km, Vs30_est_ms, dominio, particion…),
     con partición train/test por EVENTO (semilla fija) para GroupKFold.

Los .AT2 se generan en cada PC y NO se suben a GitHub (.gitignore los excluye).

Uso:
    pip install fema-p695
    python src/exportar_p695.py
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from e030 import clasificar_suelo_vs30  # noqa: E402  (Tabla 3, E.030-2026)

RAIZ = Path(__file__).resolve().parents[1]
SEMILLA = 2026
BINS_MW = [6.0, 6.5, 7.0, 7.5, 10.0]
ETQ_MW = ["6.0-6.5", "6.5-7.0", "7.0-7.5", ">=7.5"]
BINS_R = [0.0, 10.0, 30.0, 60.0, 100.0001]
ETQ_R = ["<10", "10-30", "30-60", "60-100"]


def _limpio(txt: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "", txt).upper()[:10] or "EQ"


def _comp_seguro(txt: str) -> str:
    """Código de componente sin las cadenas que registros.rsn_a_archivos usa
    para descartar verticales (UP, DWN, -V, VER, ...V.AT2)."""
    c = _limpio(txt)
    for patron in ("UP", "DWN", "VER"):
        c = c.replace(patron, "")
    return c.rstrip("V") or "H"


def escribir_at2(ruta: Path, acc_g: np.ndarray, dt: float, titulo: str, comp: str) -> None:
    lineas = [
        "PEER NGA STRONG MOTION DATABASE RECORD (exportado desde FEMA P695 far-field)",
        f"{titulo}, {comp}",
        "ACCELERATION TIME SERIES IN UNITS OF G",
        f"NPTS= {len(acc_g):7d}, DT= {dt:.4f} SEC",
    ]
    vals = [f"{v: .7E}" for v in acc_g]
    filas = ["  ".join(vals[i:i + 5]) for i in range(0, len(vals), 5)]
    ruta.write_text("\n".join(lineas + filas) + "\n", encoding="latin-1")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--at2", default=str(RAIZ / "data" / "at2"))
    ap.add_argument("--salida", default=str(RAIZ / "data" / "registros_seleccionados.csv"))
    args = ap.parse_args()

    try:
        from fema_p695.groundmotions import load_ground_motions
    except ImportError as e:
        raise SystemExit("Falta el paquete: ejecute  pip install fema-p695") from e

    gm = load_ground_motions("farfield")
    rec, tsr = gm.records, gm.ground_motions
    carpeta = Path(args.at2)
    carpeta.mkdir(parents=True, exist_ok=True)

    eventos = {n: i + 1 for i, n in enumerate(sorted(rec.EarthquakeName.unique()))}
    filas = []
    for rid, r in rec.iterrows():
        rsn = int(r.RecordSequenceNumber)
        archivos = []
        for comp in ("a", "b"):
            g = tsr.loc[(rid, comp)]
            nombre_comp = str(g.ComponentName).split("/")[-1]
            ruta = carpeta / f"RSN{rsn}_P695_{comp.upper()}{_comp_seguro(nombre_comp)}.AT2"
            escribir_at2(ruta, np.asarray(g.RecordedAcceleration, dtype=float), float(g.DT),
                         f"{r.EarthquakeName} {int(r.EarthquakeYear)}, {r.RecordingStationName}",
                         nombre_comp)
            archivos.append((ruta.name, float(g.DT), int(g.NumPoints)))
        filas.append(dict(
            rsn=rsn, eqid=eventos[r.EarthquakeName], evento=r.EarthquakeName,
            anio=int(r.EarthquakeYear), estacion=r.RecordingStationName,
            Mw=float(r.EarthquakeMagnitude), mecanismo=r.FaultType,
            Rrup_km=float(r.SiteDistanceClosestToPlane), Rjb_km=float(r.SiteDistanceJoynerBoore),
            Vs30_est_ms=float(r.SiteVs30), suelo_e030=clasificar_suelo_vs30(float(r.SiteVs30), "2026"),
            f_util_hz=float(r.LowestUsableFrequency),
            archivo_h1=archivos[0][0], archivo_h2=archivos[1][0],
            dt_s=archivos[0][1], npts=archivos[0][2],
            dominio="NGA-West2 (FEMA P695 far-field)"))

    sel = pd.DataFrame(filas)
    sel["bin_Mw"] = pd.cut(sel.Mw, BINS_MW, right=False, labels=ETQ_MW).astype(str)
    sel["bin_Rrup"] = pd.cut(sel.Rrup_km, BINS_R, right=False, labels=ETQ_R).astype(str)

    # Partición por EVENTO: ~20 % de los eventos a test (semilla fija)
    rng = np.random.default_rng(SEMILLA)
    ev = np.array(sorted(sel.eqid.unique()))
    rng.shuffle(ev)
    test = set(ev[:max(1, int(round(0.20 * len(ev))))])
    sel["particion"] = np.where(sel.eqid.isin(test), "test", "train")

    sel = sel.sort_values(["bin_Mw", "bin_Rrup", "rsn"]).reset_index(drop=True)
    sel.insert(0, "slot_registro", [f"R{i:03d}" for i in range(1, len(sel) + 1)])
    sel.to_csv(args.salida, index=False)

    assert sel.groupby("eqid").particion.nunique().max() == 1, "evento en 2 particiones"
    print(f"{len(sel)} pares · {sel.eqid.nunique()} eventos · {2 * len(sel)} archivos .AT2 en {carpeta}")
    print("Partición:", sel.particion.value_counts().to_dict(),
          "· eventos test:", sel.loc[sel.particion == "test", "evento"].unique().tolist())
    print("Perfil E.030-2026 de la estación:", sel.suelo_e030.value_counts().to_dict())
    print(f"→ {args.salida}")


if __name__ == "__main__":
    main()
