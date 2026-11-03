"""
campana_nltha.py — Genera data/dataset_sismico_peru.csv (esquema de 57 columnas,
docs/03) corriendo los NLTHA de la matriz arquetipo × registro × nivel.

Entradas:
  data/catalogo_arquetipos.csv        (gen_catalogo.py)
  data/registros_seleccionados.csv    (procesar_flatfile.py) o registros_peru.csv
  carpeta con los .AT2 (o .txt peruanos ya convertidos a .AT2)

Cada caso se escribe apenas termina (reanudable: los id_caso existentes se saltan).

Uso:
    python src/campana_nltha.py --registros data/registros_seleccionados.csv \
        --at2 data/at2 --procesos 8
    python src/campana_nltha.py ... --arquetipos POR-07 --niveles 1.0 --max-casos 2   # piloto
"""
from __future__ import annotations

import argparse
import sys
import time
import traceback
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from arquetipos import Arquetipo                                      # noqa: E402
from e030 import ParametrosE030                                        # noqa: E402
from registros import (PERIODOS, espectro_respuesta, espectro_srss,   # noqa: E402
                       factor_escala_par, ims_par, leer_par_horizontal)
from validar_integridad import COLUMNAS                                # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
NIVELES = (0.25, 0.50, 1.00, 1.50)
EXP_IM = {"PGA": 1, "PGV": 1, "Sa_T1": 1, "Sa_avg": 1, "Arias": 2,
          "D5_95": 0, "HI": 1, "ASI": 1}


def arquetipo_de(r: dict) -> Arquetipo:
    return Arquetipo(
        id=r["id_arquetipo"], sistema=r["sistema"], n_pisos=int(r["n_pisos"]),
        h_piso=r["h_piso_m"], n_vanos_x=int(r["vanos_x"]), n_vanos_y=int(r["vanos_y"]),
        L_vano_x=r["luz_x_m"], L_vano_y=r["luz_y_m"], fc_kgcm2=float(r["fc_kgcm2"]),
        rho_muros=r["densidad_muros_pct"] / 100, w_sismico=r["w_kPa"],
        suelo=r["suelo"], vs30_sitio=float(r["Vs30_ms"]), categoria=r["categoria"])


def id_caso(aid, rsn, nivel, ori):
    return f"{aid}_R{int(rsn)}_L{int(round(nivel * 100)):03d}_O{ori}"


def _trabajo(t):
    import modelo_opensees as mo
    c, g, nivel, ori, ims0, sf0, carpeta, tipo = t
    base = dict(id_caso=id_caso(c["id_arquetipo"], g["rsn"], nivel, ori))
    try:
        a = arquetipo_de(c)
        s = mo.disenar(a, version_e030="2026")
        a1, a2, dt = leer_par_horizontal(carpeta, int(g["rsn"]))
        if ori == 1:
            a1, a2 = a2, a1
        sf = sf0 * nivel
        t0 = time.time()
        r = mo.correr_caso(a, s, a1, a2, dt, sf, tipo=tipo)
        im = {k: ims0[k] * sf ** e for k, e in EXP_IM.items()}
        midr = r["MIDR"]
        return {**base,
            "id_arquetipo": c["id_arquetipo"], "id_registro": int(g["rsn"]),
            "eqid": int(g["eqid"]), "nivel_escala": nivel, "orientacion": ori,
            "dominio": g["dominio"], "particion": g["particion"],
            "fuente": f"NLTHA_{tipo}", "version_e030": "2026",
            "sistema": c["sistema"], "R0": c["R0"], "n_pisos": int(c["n_pisos"]),
            "H_m": c["H_m"], "h_piso_m": c["h_piso_m"], "area_planta_m2": c["area_planta_m2"],
            "T1_s": c["T1_s"], "W_kN": c["W_kN"], "densidad_muros_pct": c["densidad_muros_pct"],
            "fc_kgcm2": int(c["fc_kgcm2"]), "Z": c["Z"], "U": c["U"], "S": c["S"],
            "TP_s": c["TP_s"], "TL_s": c["TL_s"], "Ts_s": c["Ts_ref_s"], "C_T1": c["C_T1"],
            "Vest_W": c["V_W"], "Sa_dis_R1_g": c["Sa_R1_g"],
            "PGA_g": im["PGA"], "PGV_ms": im["PGV"], "Sa_T1_g": im["Sa_T1"],
            "Sa_avg_g": im["Sa_avg"], "Arias_ms": im["Arias"], "D5_95_s": im["D5_95"],
            "HI_m": im["HI"], "ASI_gs": im["ASI"],
            "Mw": g["Mw"], "Rrup_km": g["Rrup_km"], "Vs30_est_ms": g["Vs30_est_ms"],
            "factor_escala": sf, "MIDR": midr, "ln_MIDR": float(np.log(midr)),
            "cumple_0007": int(midr <= 0.007), "cumple_00875": int(midr <= 0.00875),
            "Vb_W": r["Vb_W"], "colapso": r["colapso"], "convergencia": r["convergencia"],
            "sf_base": sf0, "flag_sf_rango": int(0.2 <= sf0 <= 5.0),
            "MIDR_x": r["MIDR_x"], "MIDR_y": r["MIDR_y"], "piso_critico": r["piso_critico"],
            "Vb_x_kN": r["Vb_x"], "Vb_y_kN": r["Vb_y"],
            "deriva_residual": r["deriva_residual"], "t_cpu_s": time.time() - t0}
    except Exception as e:                       # el caso falla, la campaña sigue
        return {**base, "_error": f"{type(e).__name__}: {e}",
                "_traza": traceback.format_exc(limit=2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registros", default=str(RAIZ / "data" / "registros_seleccionados.csv"))
    ap.add_argument("--at2", required=True)
    ap.add_argument("--salida", default=str(RAIZ / "data" / "dataset_sismico_peru.csv"))
    ap.add_argument("--procesos", type=int, default=2)
    ap.add_argument("--arquetipos", nargs="*")
    ap.add_argument("--niveles", nargs="*", type=float, default=list(NIVELES))
    ap.add_argument("--max-casos", type=int)
    ap.add_argument("--rotar", action="store_true", help="agrega orientación 1 (X↔Y)")
    ap.add_argument("--tipo", default="fibras", choices=["fibras", "imk"])
    args = ap.parse_args()

    cat = pd.read_csv(RAIZ / "data" / "catalogo_arquetipos.csv")
    if args.arquetipos:
        cat = cat[cat.id_arquetipo.isin(args.arquetipos)]
    regs = pd.read_csv(args.registros)
    salida = Path(args.salida)
    hechos = set(pd.read_csv(salida).id_caso) if salida.exists() else set()

    tareas = []
    for _, g in regs.iterrows():
        a1, a2, dt = leer_par_horizontal(args.at2, int(g.rsn))
        sa1, sa2 = espectro_respuesta(a1, dt), espectro_respuesta(a2, dt)
        srss = espectro_srss(sa1, sa2)
        for _, c in cat.iterrows():
            p = ParametrosE030(version="2026", zona="Z4", suelo=c.suelo,
                               categoria=c.categoria, sistema=c.sistema, vs30=float(c.Vs30_ms))
            ims0 = ims_par(a1, a2, dt, sa1, sa2, c.T1_s, PERIODOS)
            sf0 = factor_escala_par(srss, c.T1_s, p)
            for nv in args.niveles:
                for ori in ((0, 1) if args.rotar else (0,)):
                    if id_caso(c.id_arquetipo, g.rsn, nv, ori) not in hechos:
                        tareas.append((c.to_dict(), g.to_dict(), nv, ori, ims0, sf0,
                                       args.at2, args.tipo))
    if args.max_casos:
        tareas = tareas[:args.max_casos]
    print(f"{len(tareas)} casos pendientes · {args.procesos} procesos · ya hechos: {len(hechos)}")

    errores = salida.with_name(salida.stem + "_errores.csv")
    t0 = time.time()
    with Pool(args.procesos) as pool:
        for i, fila in enumerate(pool.imap_unordered(_trabajo, tareas), 1):
            if "_error" in fila:
                pd.DataFrame([fila]).to_csv(errores, mode="a", index=False,
                                            header=not errores.exists())
                print(f"  {i}/{len(tareas)} {fila['id_caso']} ERROR {fila['_error']}")
                continue
            pd.DataFrame([fila])[COLUMNAS].to_csv(salida, mode="a", index=False,
                                                  header=not salida.exists(),
                                                  float_format="%.6g")
            el = time.time() - t0
            print(f"  {i}/{len(tareas)} {fila['id_caso']} MIDR={fila['MIDR']:.4f} "
                  f"Vb/W={fila['Vb_W']:.3f} conv={fila['convergencia']} "
                  f"[{el / i:.0f} s/caso · ETA {el / i * (len(tareas) - i) / 3600:.1f} h]")


if __name__ == "__main__":
    main()
