"""
registros.py — Procesamiento del flatfile PEER NGA-West2, lectura de
registros .AT2, espectros de respuesta, medidas de intensidad (IM),
escalamiento espectral multinivel E.030 e integración de la base de
validación peruana (subducción).

Unidades: aceleración en g, velocidad en m/s, desplazamiento en m, t en s.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.integrate import cumulative_trapezoid
from scipy.signal import butter, detrend, sosfiltfilt

from e030 import ParametrosE030, clasificar_suelo_vs30

G_ACC = 9.80665
PERIODOS = np.round(np.concatenate([
    np.arange(0.01, 0.10, 0.01), np.arange(0.10, 1.00, 0.02),
    np.arange(1.00, 3.00, 0.05), np.arange(3.00, 6.01, 0.10)]), 3)

# ----------------------------------------------------------------------------
# 1. Flatfile NGA-West2
# ----------------------------------------------------------------------------
# Nombres de columna del flatfile público de NGA-West2. Verificar contra la
# versión descargada: PEER ha publicado revisiones con encabezados distintos.
COLUMNAS_NGA = {
    "rsn": "Record Sequence Number",
    "eqid": "EQID",
    "evento": "Earthquake Name",
    "anio": "YEAR",
    "mw": "Earthquake Magnitude",
    "mecanismo": "Mechanism Based on Rake Angle",
    "rrup": "ClstD (km)",
    "rjb": "Joyner-Boore Dist. (km)",
    "vs30": "Vs30 (m/s) selected for analysis",
    "f_util": "Lowest Usable Freq - Ave. Component (Hz)",
    "estacion": "Station Name",
}

MECANISMOS = {0: "strike-slip", 1: "normal", 2: "reverse",
              3: "reverse-oblique", 4: "normal-oblique"}


def cargar_flatfile(ruta: str | Path, columnas: dict | None = None
                    ) -> pd.DataFrame:
    """Lee el flatfile (.csv o .xlsx) y lo normaliza a nombres cortos."""
    columnas = columnas or COLUMNAS_NGA
    ruta = Path(ruta)
    df = (pd.read_excel(ruta) if ruta.suffix.lower() in (".xls", ".xlsx")
          else pd.read_csv(ruta))
    faltan = [v for v in columnas.values() if v not in df.columns]
    obligatorias = {columnas[k] for k in ("rsn", "eqid", "mw", "rrup", "vs30")}
    if obligatorias & set(faltan):
        raise KeyError(f"Columnas obligatorias ausentes en el flatfile: "
                       f"{sorted(obligatorias & set(faltan))}. Ajustar "
                       f"COLUMNAS_NGA a los encabezados de su versión.")
    inv = {v: k for k, v in columnas.items() if v in df.columns}
    df = df[list(inv)].rename(columns=inv)
    # El flatfile usa -999 como valor faltante
    df = df.replace(-999, np.nan)
    return df


@dataclass
class FiltroSeleccion:
    mw_min: float = 6.0
    rrup_min: float = 10.0
    rrup_max: float = 100.0
    suelos: tuple = ("S1", "S2")
    max_por_evento: int = 3
    T_max_util: float = 4.0     # periodo máximo que debe ser utilizable
    excluir_rsn: tuple = ()     # p. ej. registros con pulso (lista de PEER)
    version_e030: str = "2026"  # define los rangos de Vs30 de cada perfil
    semilla: int = 2026


def seleccionar_registros(ff: pd.DataFrame, f: FiltroSeleccion
                          ) -> pd.DataFrame:
    """Aplica los filtros sismológicos y de suelo E.030."""
    d = ff.copy()
    d["suelo_e030"] = d["vs30"].apply(
        lambda v: clasificar_suelo_vs30(v, f.version_e030) if pd.notna(v) else None)
    m = (
        (d["mw"] >= f.mw_min)
        & d["rrup"].between(f.rrup_min, f.rrup_max)
        & d["suelo_e030"].isin(f.suelos)
        & ~d["rsn"].isin(f.excluir_rsn)
    )
    if "f_util" in d:
        # Frecuencia mínima utilizable ≤ 1/(T_max) para que el espectro
        # sea confiable hasta 1.5·T1 de los edificios más flexibles.
        m &= (d["f_util"].isna()) | (d["f_util"] <= 1.0 / f.T_max_util)
    d = d[m]
    rng = np.random.default_rng(f.semilla)
    # Máximo n registros por evento: se priorizan distancias distintas
    # (muestreo aleatorio reproducible dentro de cada EQID).
    partes = []
    for _, g in d.groupby("eqid"):
        if len(g) > f.max_por_evento:
            idx = rng.choice(g.index, f.max_por_evento, replace=False)
            g = g.loc[np.sort(idx)]
        partes.append(g)
    sel = pd.concat(partes).sort_values("rsn").reset_index(drop=True)
    return sel


def resumen_seleccion(sel: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "registros": [len(sel)],
        "eventos": [sel["eqid"].nunique()],
        "Mw": [f"{sel['mw'].min():.1f}–{sel['mw'].max():.1f}"],
        "Rrup_km": [f"{sel['rrup'].min():.0f}–{sel['rrup'].max():.0f}"],
        "Vs30": [f"{sel['vs30'].min():.0f}–{sel['vs30'].max():.0f}"],
        "S1": [(sel["suelo_e030"] == "S1").sum()],
        "S2": [(sel["suelo_e030"] == "S2").sum()],
    })


# ----------------------------------------------------------------------------
# 2. Lectura de registros
# ----------------------------------------------------------------------------
_RE_NPTS = re.compile(r"NPTS\s*=\s*(\d+)", re.I)
_RE_DT = re.compile(r"DT\s*=\s*([0-9.Ee+-]+)", re.I)


def leer_at2(ruta: str | Path) -> tuple[np.ndarray, float]:
    """Lee un archivo PEER .AT2 → (aceleración en g, dt)."""
    with open(ruta, encoding="latin-1") as fh:
        lineas = fh.readlines()
    cab = lineas[3]
    npts = int(_RE_NPTS.search(cab).group(1))
    dt = float(_RE_DT.search(cab).group(1))
    vals = np.array(" ".join(lineas[4:]).split(), dtype=float)
    return vals[:npts], dt


def rsn_a_archivos(carpeta: str | Path, rsn: int) -> list[Path]:
    """Archivos .AT2 horizontales de un RSN (patrón RSN<n>_*.AT2)."""
    arch = sorted(Path(carpeta).glob(f"RSN{rsn}_*.AT2"))
    return [p for p in arch if not re.search(r"(UP|DWN|-V|V\.AT2|VER)",
                                              p.name.upper())]


def leer_par_horizontal(carpeta, rsn) -> tuple[np.ndarray, np.ndarray, float]:
    h = rsn_a_archivos(carpeta, rsn)
    if len(h) < 2:
        raise FileNotFoundError(f"RSN {rsn}: se esperaban 2 componentes "
                                f"horizontales, hay {len(h)}")
    a1, dt1 = leer_at2(h[0])
    a2, dt2 = leer_at2(h[1])
    if abs(dt1 - dt2) > 1e-9:
        raise ValueError(f"RSN {rsn}: dt distinto entre componentes")
    n = min(len(a1), len(a2))
    return a1[:n], a2[:n], dt1


def corregir_registro(acc: np.ndarray, dt: float, f_lo: float = 0.10,
                      f_hi: float = 25.0, orden: int = 4) -> np.ndarray:
    """Corrección de línea base + filtro Butterworth pasa-banda acausal.

    Los registros NGA-West2 ya vienen procesados por PEER: usar solo para
    registros crudos (p. ej. CISMID/IGP).
    """
    a = detrend(acc, type="linear")
    nyq = 0.5 / dt
    f_hi = min(f_hi, 0.95 * nyq)
    sos = butter(orden, [f_lo / nyq, f_hi / nyq], btype="band", output="sos")
    n_pad = int(1.5 * orden / f_lo / dt)
    a = np.pad(a, (n_pad, n_pad))
    a = sosfiltfilt(sos, a)[n_pad:-n_pad]
    return a


# ----------------------------------------------------------------------------
# 3. Espectro de respuesta (método exacto por tramos lineales)
# ----------------------------------------------------------------------------
def espectro_respuesta(acc: np.ndarray, dt: float,
                       T: np.ndarray = PERIODOS, xi: float = 0.05) -> np.ndarray:
    """Pseudoaceleración Sa(T) en g. Nigam & Jennings (1969), vectorizado."""
    T = np.asarray(T, dtype=float)
    w = 2 * np.pi / T
    wd = w * np.sqrt(1 - xi ** 2)
    e = np.exp(-xi * w * dt)
    s, c = np.sin(wd * dt), np.cos(wd * dt)
    xs = xi / np.sqrt(1 - xi ** 2)
    a11 = e * (xs * s + c)
    a12 = e * s / wd
    a21 = -w / np.sqrt(1 - xi ** 2) * e * s
    a22 = e * (c - xs * s)
    t1 = (2 * xi ** 2 - 1) / (w ** 2 * dt)
    t2 = 2 * xi / (w ** 3 * dt)
    b11 = e * ((t1 + xi / w) * s / wd + (t2 + 1 / w ** 2) * c) - t2
    b12 = -e * (t1 * s / wd + t2 * c) - 1 / w ** 2 + t2
    b21 = (e * ((t1 + xi / w) * (c - xs * s) - (t2 + 1 / w ** 2)
                * (wd * s + xi * w * c)) + 1 / (w ** 2 * dt))
    b22 = (-e * (t1 * (c - xs * s) - t2 * (wd * s + xi * w * c))
           - 1 / (w ** 2 * dt))
    ag = acc * G_ACC
    u = np.zeros_like(T)
    v = np.zeros_like(T)
    umax = np.zeros_like(T)
    for i in range(len(ag) - 1):
        u, v = (a11 * u + a12 * v + b11 * ag[i] + b12 * ag[i + 1],
                a21 * u + a22 * v + b21 * ag[i] + b22 * ag[i + 1])
        np.maximum(umax, np.abs(u), out=umax)
    return umax * w ** 2 / G_ACC


def espectro_srss(sa1: np.ndarray, sa2: np.ndarray) -> np.ndarray:
    return np.sqrt(sa1 ** 2 + sa2 ** 2)


# ----------------------------------------------------------------------------
# 4. Medidas de intensidad
# ----------------------------------------------------------------------------
def _interp_sa(T_obj, T=PERIODOS, sa=None):
    return float(np.exp(np.interp(np.log(T_obj), np.log(T), np.log(sa))))


def medidas_intensidad(acc: np.ndarray, dt: float, sa: np.ndarray,
                       T1: float | None = None, T=PERIODOS) -> dict:
    """IMs escalares de una componente (acc en g, sa calculado con T)."""
    ag = acc * G_ACC
    vel = cumulative_trapezoid(ag, dx=dt, initial=0.0)
    dis = cumulative_trapezoid(vel, dx=dt, initial=0.0)
    ia_t = np.pi / (2 * G_ACC) * cumulative_trapezoid(ag ** 2, dx=dt, initial=0.0)
    ia = ia_t[-1]
    t5 = np.searchsorted(ia_t, 0.05 * ia) * dt
    t95 = np.searchsorted(ia_t, 0.95 * ia) * dt
    w = 2 * np.pi / T
    psv = sa * G_ACC / w
    m_hi = (T >= 0.1) & (T <= 2.5)
    m_asi = (T >= 0.1) & (T <= 0.5)
    out = dict(
        PGA=float(np.abs(acc).max()),
        PGV=float(np.abs(vel).max()),
        PGD=float(np.abs(dis).max()),
        Arias=float(ia),
        D5_95=float(t95 - t5),
        CAV=float(np.trapezoid(np.abs(ag), dx=dt)),
        HI=float(np.trapezoid(psv[m_hi], T[m_hi])),     # Housner (5 %)
        ASI=float(np.trapezoid(sa[m_asi], T[m_asi])),   # Von Thun
    )
    if T1 is not None:
        Tr = np.linspace(0.2 * T1, 1.5 * T1, 20)
        sar = np.exp(np.interp(np.log(Tr), np.log(T), np.log(sa)))
        out["Sa_T1"] = _interp_sa(T1, T, sa)
        out["Sa_avg"] = float(np.exp(np.mean(np.log(sar))))   # media geométrica
    return out


def ims_par(acc1, acc2, dt, sa1, sa2, T1=None, T=PERIODOS) -> dict:
    """IMs de un par horizontal: media geométrica de las dos componentes."""
    i1 = medidas_intensidad(acc1, dt, sa1, T1, T)
    i2 = medidas_intensidad(acc2, dt, sa2, T1, T)
    out = {}
    for k in i1:
        out[k] = float(np.sqrt(i1[k] * i2[k])) if k != "D5_95" else \
            float(0.5 * (i1[k] + i2[k]))
    return out


# ----------------------------------------------------------------------------
# 5. Escalamiento espectral E.030 (SRSS) y multinivel
# ----------------------------------------------------------------------------
NIVELES = (0.25, 0.50, 1.00, 1.50)


def factor_escala_par(sa_srss: np.ndarray, T1: float, p: ParametrosE030,
                      T=PERIODOS) -> float:
    """Factor que ajusta el SRSS de UN par al espectro E.030 (R = 1) en
    [0.2·T1, 1.5·T1], en sentido de mínimos cuadrados logarítmicos.

    Se usa para el entrenamiento multinivel (cada par aislado). La
    verificación normativa del conjunto se hace con verificar_suite_e030().
    """
    m = (T >= 0.2 * T1) & (T <= 1.5 * T1)
    objetivo = p.Sa_elastico(T[m])
    return float(np.exp(np.mean(np.log(objetivo / sa_srss[m]))))


def verificar_suite_e030(srss_escalados: list[np.ndarray], T1: float,
                         p: ParametrosE030, T=PERIODOS,
                         factor_minimo: float = 1.0) -> dict:
    """Criterio normativo del conjunto de registros escalados.

    E.030-2026 (art. 47.5) y E.030-2018 (art. 30): con el MISMO factor para
    ambas componentes, el promedio de los espectros SRSS no debe ser menor
    que el espectro de diseño con R = 1 en el rango [0.2·T1, 1.5·T1].
    Número mínimo de pares: 7 (2026, art. 47.1) o 3 (2018). La respuesta de
    diseño es el promedio de los máximos (2026, art. 49.1); en 2018, el
    promedio solo si hay 7 pares o más (si no, el máximo).

    Devuelve el factor global adicional (≥ 1) que haría cumplir el criterio.
    """
    from e030 import MIN_REGISTROS_TH
    m = (T >= 0.2 * T1) & (T <= 1.5 * T1)
    prom = np.mean(np.vstack(srss_escalados), axis=0)
    razon = prom[m] / (factor_minimo * p.Sa_elastico(T[m]))
    n = len(srss_escalados)
    if p.version == "2026":
        usar = "promedio"
    else:
        usar = "promedio" if n >= 7 else "maximo"
    return dict(n_pares=n, n_min=MIN_REGISTROS_TH[p.version],
                suficientes=n >= MIN_REGISTROS_TH[p.version],
                razon_min=float(razon.min()),
                factor_adicional=float(max(1.0, 1.0 / razon.min())),
                cumple=bool(razon.min() >= 1.0), usar=usar)


def casos_multinivel(sel: pd.DataFrame, arqs_T1: dict, params: dict,
                     sa_srss: dict, niveles=NIVELES,
                     sf_min: float = 0.2, sf_max: float = 5.0
                     ) -> pd.DataFrame:
    """Tabla de casos (arquetipo × registro × nivel) con su factor total.

    arqs_T1: {id_arquetipo: T1}; params: {id_arquetipo: ParametrosE030};
    sa_srss: {rsn: espectro SRSS sin escalar}. Se descartan los casos cuyo
    factor base cae fuera de [sf_min, sf_max] para no distorsionar el
    contenido de frecuencias del registro.
    """
    filas = []
    for aid, T1 in arqs_T1.items():
        p = params[aid]
        for _, r in sel.iterrows():
            sf0 = factor_escala_par(sa_srss[r.rsn], T1, p)
            if not (sf_min <= sf0 <= sf_max):
                continue
            for lv in niveles:
                filas.append(dict(arquetipo=aid, rsn=int(r.rsn),
                                  eqid=int(r.eqid), nivel=lv,
                                  sf_base=sf0, sf=sf0 * lv))
    return pd.DataFrame(filas)


# ----------------------------------------------------------------------------
# 6. Base de validación peruana (subducción)
# ----------------------------------------------------------------------------
# Metadatos de evento conocidos. La estación, Vs30 y el formato del
# archivo deben completarse con la ficha oficial del registro (CISMID-UNI,
# REDACIS, o IGP). Los EQID 9001+ evitan choques con los de NGA-West2.
CATALOGO_PERU = [
    dict(eqid=9001, evento="Lima 1966", fecha="1966-10-17", mw=8.1,
         tipo_fuente="subduccion_interfase"),
    dict(eqid=9002, evento="Lima 1974", fecha="1974-10-03", mw=8.1,
         tipo_fuente="subduccion_interfase"),
    dict(eqid=9003, evento="Pisco 2007", fecha="2007-08-15", mw=8.0,
         tipo_fuente="subduccion_interfase"),
]


def leer_registro_peruano(ruta: str | Path, dt: float, columnas=(0, 1),
                          filas_cabecera: int = 0, unidad: str = "cm/s2",
                          sep: str | None = None
                          ) -> tuple[np.ndarray, np.ndarray]:
    """Lector genérico de archivos de texto en columnas (CISMID/IGP).

    columnas: índices de las dos componentes horizontales (p. ej. EW, NS).
    unidad: "cm/s2" (gal), "m/s2" o "g".
    """
    datos = np.loadtxt(ruta, skiprows=filas_cabecera, delimiter=sep)
    c1, c2 = datos[:, columnas[0]], datos[:, columnas[1]]
    conv = {"cm/s2": 1 / (100 * G_ACC), "m/s2": 1 / G_ACC, "g": 1.0}[unidad]
    return c1 * conv, c2 * conv


def procesar_validacion_peru(fichas: list[dict], T1_ref: float | None = None
                             ) -> tuple[pd.DataFrame, dict]:
    """fichas: [{eqid, ruta, dt, columnas, filas_cabecera, unidad,
    estacion, vs30, rrup}]. Devuelve (tabla de metadatos+IMs, espectros).

    Se corrige línea base y se filtra (registros crudos), se calculan los
    espectros por componente y SRSS, y se etiqueta el tipo de fuente para
    que el análisis de transferibilidad pueda separar ambos dominios.
    """
    cat = {c["eqid"]: c for c in CATALOGO_PERU}
    filas, espectros = [], {}
    for k, f in enumerate(fichas):
        a1, a2 = leer_registro_peruano(f["ruta"], f["dt"],
                                       f.get("columnas", (0, 1)),
                                       f.get("filas_cabecera", 0),
                                       f.get("unidad", "cm/s2"))
        a1 = corregir_registro(a1, f["dt"])
        a2 = corregir_registro(a2, f["dt"])
        sa1 = espectro_respuesta(a1, f["dt"])
        sa2 = espectro_respuesta(a2, f["dt"])
        rsn = 90000 + k
        espectros[rsn] = dict(sa1=sa1, sa2=sa2, srss=espectro_srss(sa1, sa2),
                              acc1=a1, acc2=a2, dt=f["dt"])
        ev = cat[f["eqid"]]
        fila = dict(rsn=rsn, eqid=f["eqid"], evento=ev["evento"],
                    mw=ev["mw"], tipo_fuente=ev["tipo_fuente"],
                    estacion=f.get("estacion"), vs30=f.get("vs30"),
                    rrup=f.get("rrup"), dt=f["dt"], npts=len(a1))
        fila["suelo_e030"] = (clasificar_suelo_vs30(f["vs30"])
                              if f.get("vs30") else None)
        fila.update(ims_par(a1, a2, f["dt"], sa1, sa2, T1_ref))
        filas.append(fila)
    return pd.DataFrame(filas), espectros


def chequeo_dominio(ims_entrenamiento: pd.DataFrame, ims_peru: pd.DataFrame,
                    variables=("D5_95", "Arias", "PGV", "ASI", "HI")
                    ) -> pd.DataFrame:
    """Percentil de cada registro peruano dentro de la distribución de
    entrenamiento. Valores < 2.5 o > 97.5 = extrapolación (declararlo)."""
    filas = []
    for _, r in ims_peru.iterrows():
        fila = dict(rsn=r.rsn, evento=r.evento)
        for v in variables:
            ref = ims_entrenamiento[v].dropna().values
            fila[f"pct_{v}"] = float((ref < r[v]).mean() * 100)
        fila["fuera_de_dominio"] = any(
            not 2.5 <= fila[f"pct_{v}"] <= 97.5 for v in variables)
        filas.append(fila)
    return pd.DataFrame(filas)
