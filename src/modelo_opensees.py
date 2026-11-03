"""
modelo_opensees.py — Diseño simplificado E.030, modelo 3D no lineal en
OpenSeesPy y análisis tiempo-historia bidireccional (NLTHA).

Unidades: kN, m, s.  g = 9.80665 m/s².

Hipótesis de modelado (declararlas en la tesis):
  * Edificio regular, diafragma rígido por piso (rigidDiaphragm), base empotrada.
  * Masa sísmica concentrada en el nodo maestro de cada piso (centro de masa
    = centro geométrico), con inercia rotacional de planta rectangular.
  * Columnas y muros: forceBeamColumn con secciones de fibras
    (Concrete02 confinado/no confinado + Steel02). Muros como "columna ancha"
    (wide-column); MVLEM queda como mejora futura.
  * Vigas: dos opciones
      - "fibras": forceBeamColumn de fibras.
      - "imk":    elemento elástico + rótulas concentradas IMKPeakOriented
                  (Ibarra-Medina-Krawinkler) en ambos extremos, calibradas
                  con las ecuaciones empíricas de Haselton et al. (2016).
  * Excentricidad accidental, interacción suelo-estructura y losas no se
    modelan.
  * El diseño es un PREDIMENSIONAMIENTO con verificación de deriva E.030
    (control de rigidez). El diseño por resistencia E.060 de cada arquetipo
    debe verificarse por separado (p. ej. ETABS en una muestra).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import openseespy.opensees as ops

from arquetipos import Arquetipo
from e030 import ParametrosE030

G_ACC = 9.80665
FY_REF = 420e3       # kPa (4200 kg/cm² ≈ 412 MPa; se usa el valor del arquetipo)
ES = 200e6           # kPa
AREA_BARRA = 2.84e-4  # m², barra de 3/4"


# ============================================================================
# 1. Predimensionamiento + verificación de deriva E.030
# ============================================================================
@dataclass
class Secciones:
    b_col: float
    h_col: float
    b_viga: float
    h_viga: float
    L_muro: float = 0.0          # longitud de cada muro alineado con X (m)
    L_muro_y: float = 0.0        # longitud de cada muro alineado con Y (m)
    n_muros_x: int = 0           # número de muros alineados con X
    n_muros_y: int = 0           # número de muros alineados con Y
    t_muro: float = 0.25
    rho_col: float = 0.015
    rho_viga_sup: float = 0.008
    rho_viga_inf: float = 0.005
    rho_muro_alma: float = 0.0025
    rho_muro_borde: float = 0.015
    iteraciones: int = 0
    drift_elastico_x: float = float("nan")
    drift_elastico_y: float = float("nan")
    drift_inelastico: float = float("nan")
    T1x: float = float("nan")
    T1y: float = float("nan")
    historial: list = field(default_factory=list)


def _redondear(x: float, paso: float = 0.05) -> float:
    return math.ceil(x / paso - 1e-9) * paso


def predimensionar(a: Arquetipo) -> Secciones:
    L = max(a.L_vano_x, a.L_vano_y)
    h_viga = _redondear(max(L / 11.0, 0.40))
    b_viga = _redondear(max(0.25, 0.5 * h_viga))
    # Columna interior: P = w · área tributaria · n_pisos ; A = P / (0.45 f'c)
    P = 1.25 * a.w_sismico * a.L_vano_x * a.L_vano_y * a.n_pisos   # kN
    A = P / (0.45 * a.fc_kpa)
    lado_min = 0.40 if a.sistema == "porticos" else 0.35
    lado = _redondear(max(math.sqrt(A), lado_min))
    s = Secciones(b_col=lado, h_col=lado, b_viga=b_viga, h_viga=h_viga,
                  t_muro=a.t_muro)
    if a.sistema in ("dual", "muros"):
        # Longitud total de muros por dirección: ρw·Ap / tw. Se reparte en
        # el menor número PAR de muros (≥ 2, simétricos) cuya longitud no
        # supere L_MURO_MAX ni el 40 % de la dimensión de planta paralela.
        for d in ("x", "y"):
            L_tot = a.rho_muros * a.area_planta / a.t_muro
            L_max = _L_muro_max(a, d)
            n = 2
            while L_tot / n > L_max and n + 2 <= _n_ejes(a, d):
                n += 2
            Lw = max(min(_redondear(L_tot / n, 0.10), L_max), 1.5)
            if d == "x":
                s.L_muro, s.n_muros_x = Lw, n
            else:
                s.L_muro_y, s.n_muros_y = Lw, n
    return s


L_MURO_MAX = 8.0   # m, longitud máxima de un tramo de muro (práctica local)


def _L_muro_max(a: Arquetipo, d: str) -> float:
    """Longitud máxima de un tramo de muro: el menor entre 8 m y el 40 % de
    la dimensión de planta paralela (caben dos tramos por eje)."""
    return min(L_MURO_MAX,
               math.floor(0.40 * (a.Lx if d == "x" else a.Ly) * 10) / 10)


def _n_ejes(a: Arquetipo, d: str) -> int:
    """Posiciones disponibles para muros: hasta 2 tramos por eje. Un muro
    alineado con X va sobre un eje y = cte (hay n_vanos_y + 1 ejes); uno
    alineado con Y, sobre x = cte."""
    return 2 * ((a.n_vanos_y if d == "x" else a.n_vanos_x) + 1)


def disenar(a: Arquetipo, version_e030: str = "2026",
            max_iter: int = 30, verbose: bool = False) -> Secciones:
    """Incrementa rigidez hasta cumplir deriva inelástica ≤ límite E.030.

    Deriva inelástica (regular) = 0.75·R·Δelástica, con fuerzas del método
    estático equivalente usando T1 del análisis modal y C/R ≥ 0.11.
    """
    p = ParametrosE030(version=version_e030, zona=a.zona, suelo=a.suelo,
                       categoria=a.categoria, sistema=a.sistema,
                       vs30=a.vs30_sitio)
    s = predimensionar(a)
    for it in range(max_iter):
        construir_modelo(a, s, tipo="elastico")
        Tx, Ty = _periodos_por_direccion(a)
        dx, dy = _deriva_estatica_e030(a, s, p, Tx, Ty)
        factor_inel = 0.75 * p.R if p.regular else 0.85 * p.R
        d_inel = factor_inel * max(dx, dy)
        s.historial.append(dict(it=it, Tx=Tx, Ty=Ty, d_inel=d_inel,
                                col=s.b_col, Lwx=s.L_muro, Lwy=s.L_muro_y,
                                nwx=s.n_muros_x, nwy=s.n_muros_y))
        if verbose:
            print(f"  it {it}: Tx={Tx:.3f} Ty={Ty:.3f} deriva={d_inel:.4f} "
                  f"col={s.b_col:.2f} muros X={s.n_muros_x}x{s.L_muro:.1f} "
                  f"Y={s.n_muros_y}x{s.L_muro_y:.1f} tw={s.t_muro:.2f}")
        s.T1x, s.T1y = Tx, Ty
        s.drift_elastico_x, s.drift_elastico_y = dx, dy
        s.drift_inelastico = d_inel
        s.iteraciones = it
        if d_inel <= p.drift_limite:
            break
        if a.sistema == "porticos" or (a.sistema == "dual" and s.b_col < 1.0):
            # Dual: se rigidiza primero el pórtico, para conservar el reparto
            # de cortante 20–70 % en muros que define al sistema (E.030).
            s.b_col = s.h_col = _redondear(s.b_col * 1.10)
            s.h_viga = _redondear(s.h_viga * 1.05)
        else:
            # En la dirección que no cumple: 1° alargar muros hasta el tope;
            # 2° agregar muros en ejes libres; 3° engrosar (≤ 0.40 m).
            # Columnas × 1.05 en paralelo.
            dirs = [d for d, dd in (("x", dx), ("y", dy))
                    if factor_inel * dd > p.drift_limite]
            for d in dirs:
                Lk, nk = ("L_muro", "n_muros_x") if d == "x" else ("L_muro_y", "n_muros_y")
                L, n, Lmax = getattr(s, Lk), getattr(s, nk), _L_muro_max(a, d)
                if L < Lmax:
                    setattr(s, Lk, min(_redondear(L * 1.15, 0.10), Lmax))
                elif n + 2 <= _n_ejes(a, d):
                    setattr(s, nk, n + 2)
                elif s.t_muro < 0.40:
                    s.t_muro = round(s.t_muro + 0.05, 2)
            s.b_col = s.h_col = _redondear(s.b_col * 1.05)
    ops.wipe()
    return s


def _eigen(n: int) -> list[float]:
    """Autovalores con manejador Transformation (necesario por rigidDiaphragm).

    Las masas solo existen en los nodos maestros (3 GDL por piso). ARPACK
    falla cuando n se acerca a ese número, así que en edificios bajos se usa
    el solver denso fullGenLapack (lento, pero robusto).
    """
    ops.wipeAnalysis()
    ops.constraints("Transformation")
    ops.numberer("RCM")
    ops.system("UmfPack")
    n_gdl_masa = 3 * len([t for t in ops.getNodeTags() if t % 1000 == 999])
    if n_gdl_masa >= 2 * n + 2:
        return ops.eigen(n)                     # ARPACK (rápido)
    return ops.eigen("-fullGenLapack", n)       # denso (modelos pequeños)


def _periodos_por_direccion(a: Arquetipo) -> tuple[float, float]:
    """T1 en X e Y: el modo con mayor participación de masa en cada dirección."""
    n = min(6, 3 * a.n_pisos)
    lam = _eigen(n)
    masters = [_tag_master(k) for k in range(1, a.n_pisos + 1)]
    m = a.W_piso / G_ACC
    best = {1: (0.0, None), 2: (0.0, None)}
    for i, l in enumerate(lam, start=1):
        for d in (1, 2):
            # OpenSees normaliza los modos respecto de la masa (ΦᵀMΦ = 1),
            # por lo que la masa efectiva es directamente (Σ m·φ)².
            phi = np.array([ops.nodeEigenvector(t, i, d) for t in masters])
            meff = float(np.sum(m * phi)) ** 2
            if meff > best[d][0]:
                best[d] = (meff, 2 * np.pi / np.sqrt(l))
    return best[1][1], best[2][1]


def _deriva_estatica_e030(a: Arquetipo, s: "Secciones", p: ParametrosE030,
                          Tx: float, Ty: float) -> tuple[float, float]:
    """Deriva elástica máxima con fuerzas del método estático equivalente.

    Se reconstruye el modelo elástico por dirección (sin cargas de gravedad)
    para que cada análisis parta de un estado limpio.
    """
    derivas = []
    for d, T in ((1, Tx), (2, Ty)):
        construir_modelo(a, s, tipo="elastico")
        ops.remove("loadPattern", 1)
        V = p.cortante_estatico(T, a.W_total)
        k = 1.0 if T <= 0.5 else min(0.75 + 0.5 * T, 2.0)
        alturas = np.array([a.h_piso * i for i in range(1, a.n_pisos + 1)])
        Pi = np.full(a.n_pisos, a.W_piso)
        alfa = Pi * alturas ** k / np.sum(Pi * alturas ** k)
        ops.timeSeries("Linear", 100)
        ops.pattern("Plain", 100, 100)
        for i, fi in enumerate(alfa * V, start=1):
            carga = [0.0] * 6
            carga[d - 1] = fi
            ops.load(_tag_master(i), *carga)
        ops.system("UmfPack"); ops.numberer("RCM")
        ops.constraints("Transformation"); ops.test("NormDispIncr", 1e-8, 10)
        ops.algorithm("Linear"); ops.integrator("LoadControl", 1.0)
        ops.analysis("Static"); ops.analyze(1)
        u = np.array([0.0] + [ops.nodeDisp(_tag_master(i), d)
                               for i in range(1, a.n_pisos + 1)])
        derivas.append(float(np.max(np.abs(np.diff(u))) / a.h_piso))
    return derivas[0], derivas[1]


# ============================================================================
# 2. Construcción del modelo 3D
# ============================================================================
def _tag(i: int, j: int, k: int) -> int:
    return k * 1000 + j * 20 + i + 1


def _tag_muro(w: int, k: int) -> int:
    return k * 1000 + 900 + w


def _tag_master(k: int) -> int:
    return k * 1000 + 999


def _orden_ejes(n_ejes: int) -> list[int]:
    """Ejes en orden simétrico: fachadas primero, luego hacia el centro."""
    orden, i, j = [], 0, n_ejes - 1
    while i <= j:
        orden.append(i)
        if j != i:
            orden.append(j)
        i, j = i + 1, j - 1
    return orden


def _ubicacion_muros(a: Arquetipo, s: Secciones
                     ) -> list[tuple[float, float, str, float]]:
    """(x, y, orientación, longitud) de cada tramo de muro.

    Muros alineados con X sobre ejes y = cte; alineados con Y sobre x = cte.
    Los tramos se reparten por turnos en los ejes, en orden simétrico
    (fachadas primero, luego ejes interiores). Un eje con un tramo lo lleva
    centrado; con dos, en los cuartos de la luz (L/4 y 3L/4).
    """
    if a.sistema == "porticos":
        return []
    muros = []
    for ori, n, Lw, n_ejes_, paso, L_par in (
            ("x", s.n_muros_x, s.L_muro, a.n_vanos_y + 1, a.L_vano_y, a.Lx),
            ("y", s.n_muros_y, s.L_muro_y, a.n_vanos_x + 1, a.L_vano_x, a.Ly)):
        orden = _orden_ejes(n_ejes_)
        cuenta = {k: 0 for k in orden}
        for i in range(n):
            cuenta[orden[i % len(orden)]] += 1
        for k, c in cuenta.items():
            pos = [0.5] if c == 1 else ([0.25, 0.75] if c == 2 else [])
            for f in pos:
                if ori == "x":
                    muros.append((f * L_par, k * paso, "x", Lw))
                else:
                    muros.append((k * paso, f * L_par, "y", Lw))
    return muros


def _materiales(a: Arquetipo):
    fc = a.fc_kpa
    fy = a.fy_kpa
    Ec = a.Ec_kpa
    eps0 = 2 * fc / Ec
    # 1: concreto no confinado (recubrimiento)
    # Tracción: ft = 0.04 f'c con ablandamiento lineal hasta εt ≈ 0.002
    # (pendiente moderada: evita saltos de rigidez que impiden converger
    # a los elementos de fuerza de los muros).
    ft = 0.04 * fc
    Ets = ft / 0.002
    ops.uniaxialMaterial("Concrete02", 1, -fc, -eps0, -0.2 * fc, -0.006,
                         0.1, ft, Ets)
    # 2: concreto confinado (núcleo), Mander simplificado: f'cc = 1.3 f'c
    fcc = 1.3 * fc
    ops.uniaxialMaterial("Concrete02", 2, -fcc, -2 * fcc / Ec, -0.2 * fcc,
                         -0.020, 0.1, ft, Ets)
    # 3: acero de refuerzo (Menegotto-Pinto)
    ops.uniaxialMaterial("Steel02", 3, fy, ES, 0.01, 18.0, 0.925, 0.15)
    # 4: material rígido para grados de libertad no plastificables
    ops.uniaxialMaterial("Elastic", 4, 1.0e12)


def _seccion_rect_fibras(tag: int, dy: float, dz: float, rho: float,
                         a: Arquetipo, rec: float = 0.04,
                         rho_borde: float | None = None, nf: int = 10):
    """Sección de fibras rectangular. dy, dz: dimensiones en ejes locales y, z.

    Si rho_borde no es None se modela como muro: refuerzo distribuido rho
    en el alma y concentrado rho_borde en elementos de borde (10 % de L
    a cada extremo, sobre la dimensión mayor).
    """
    Gc = a.Ec_kpa / 2.4
    J = _torsion_rect(dy, dz)
    ops.section("Fiber", tag, "-GJ", 0.2 * Gc * J)
    y1, z1 = dy / 2.0, dz / 2.0
    yc, zc = y1 - rec, z1 - rec
    nfy = max(nf, int(dy / 0.05)) if dy > 1.0 else nf
    nfz = max(nf, int(dz / 0.05)) if dz > 1.0 else nf
    # núcleo confinado
    ops.patch("rect", 2, nfy, nfz, -yc, -zc, yc, zc)
    # recubrimiento (4 franjas)
    ops.patch("rect", 1, nfy, 2, -y1, zc, y1, z1)
    ops.patch("rect", 1, nfy, 2, -y1, -z1, y1, -zc)
    ops.patch("rect", 1, 2, nfz, -y1, -zc, -yc, zc)
    ops.patch("rect", 1, 2, nfz, yc, -zc, y1, zc)
    if rho_borde is None:
        As = rho * dy * dz
        n_bar = max(4, math.ceil(As / AREA_BARRA))
        n_cara = max(2, math.ceil(n_bar / 4) + 1)
        ab = As / (4 * n_cara - 4)
        ops.layer("straight", 3, n_cara, ab, -yc, zc, yc, zc)
        ops.layer("straight", 3, n_cara, ab, -yc, -zc, yc, -zc)
        if n_cara > 2:
            esp = 2 * zc / (n_cara - 1)
            ops.layer("straight", 3, n_cara - 2, ab, -yc, -zc + esp, -yc, zc - esp)
            ops.layer("straight", 3, n_cara - 2, ab, yc, -zc + esp, yc, zc - esp)
    else:
        largo_en_y = dy >= dz
        Lw, tw = (dy, dz) if largo_en_y else (dz, dy)
        Lb = 0.10 * Lw
        Ab = rho_borde * Lb * tw / 4.0          # 4 barras por elemento de borde
        n_alma = max(2, int((Lw - 2 * Lb) / 0.20))
        Aa = rho * (Lw - 2 * Lb) * tw / (2 * n_alma)
        e = tw / 2.0 - rec
        for s in (-1, 1):
            c = s * (Lw / 2.0 - rec)
            c2 = s * (Lw / 2.0 - Lb)
            if largo_en_y:
                ops.layer("straight", 3, 2, Ab, c, -e, c, e)
                ops.layer("straight", 3, 2, Ab, c2, -e, c2, e)
            else:
                ops.layer("straight", 3, 2, Ab, -e, c, e, c)
                ops.layer("straight", 3, 2, Ab, -e, c2, e, c2)
        a0 = -(Lw / 2.0 - Lb) + 0.10
        a1 = (Lw / 2.0 - Lb) - 0.10
        for s in (-e, e):
            if largo_en_y:
                ops.layer("straight", 3, n_alma, Aa, a0, s, a1, s)
            else:
                ops.layer("straight", 3, n_alma, Aa, s, a0, s, a1)


def _seccion_viga_fibras(tag: int, b: float, h: float, rho_sup: float,
                         rho_inf: float, a: Arquetipo, rec: float = 0.05):
    """Viga: y local = ancho b, z local = peralte h (vertical)."""
    Gc = a.Ec_kpa / 2.4
    ops.section("Fiber", tag, "-GJ", 0.2 * Gc * _torsion_rect(b, h))
    y1, z1 = b / 2.0, h / 2.0
    yc, zc = y1 - rec, z1 - rec
    ops.patch("rect", 2, 6, 12, -yc, -zc, yc, zc)
    ops.patch("rect", 1, 6, 2, -y1, zc, y1, z1)
    ops.patch("rect", 1, 6, 2, -y1, -z1, y1, -zc)
    ops.patch("rect", 1, 2, 12, -y1, -zc, -yc, zc)
    ops.patch("rect", 1, 2, 12, yc, -zc, y1, zc)
    d = h - rec
    As_sup = rho_sup * b * d
    As_inf = rho_inf * b * d
    ops.layer("straight", 3, 3, As_sup / 3, -yc, zc, yc, zc)
    ops.layer("straight", 3, 3, As_inf / 3, -yc, -zc, yc, -zc)


def _torsion_rect(dy: float, dz: float) -> float:
    a_, b_ = max(dy, dz), min(dy, dz)
    return a_ * b_ ** 3 * (1 / 3 - 0.21 * b_ / a_ * (1 - b_ ** 4 / (12 * a_ ** 4)))


# ---------------------------------------------------------------------------
# Rótulas IMK — calibración Haselton et al. (2016), ACI Struct. J. 113(6)
# ---------------------------------------------------------------------------
def parametros_imk_haselton(nu: float, rho_sh: float, fc_mpa: float,
                            s_d: float, rho: float, asl: float = 1.0,
                            sn: float = 12.0) -> dict:
    """Ecuaciones empíricas de calibración (componentes de CA conformes).

    nu: carga axial normalizada P/(Ag f'c); rho_sh: cuantía transversal;
    s_d: espaciamiento de estribos / peralte efectivo; rho: cuantía
    longitudinal en tracción; sn: parámetro de pandeo de barras.
    Devuelve θp, θpc, λ (energía normalizada), Mc/My y EIy/EIg.
    """
    theta_p = (0.12 * (1 + 0.55 * asl) * 0.16 ** nu
               * (0.02 + 40 * rho_sh) ** 0.43 * 0.54 ** (0.01 * fc_mpa)
               * 0.66 ** (0.1 * sn) * 2.27 ** (10 * rho))
    theta_pc = min(0.76 * 0.031 ** nu * (0.02 + 40 * rho_sh) ** 1.02, 0.10)
    lam = 170.7 * 0.27 ** nu * 0.10 ** s_d
    mc_my = 1.25 * 0.89 ** nu * 0.91 ** (0.01 * fc_mpa)
    eiy = float(np.clip(-0.07 + 0.59 * nu + 0.07 * 3.0, 0.20, 0.60))
    return dict(theta_p=theta_p, theta_pc=theta_pc, lam=lam,
                mc_my=mc_my, EIy_EIg=eiy)


def _material_imk(tag: int, My_pos: float, My_neg: float, EI: float,
                  L: float, prm: dict, n: float = 10.0) -> float:
    """Crea IMKPeakOriented para un resorte en serie con elemento elástico.

    Rigidez del resorte K = (n+1)·6EI/L (doble curvatura; Ibarra y
    Krawinkler 2005). Energía cíclica Et = λ·My·θy → Λ = λ·θy.
    Retorna la rigidez elástica modificada del elemento: EI·(n+1)/n.
    """
    K = (n + 1) * 6.0 * EI / L
    th_y = max(My_pos, My_neg) / (6.0 * EI / L)
    Lam = prm["lam"] * th_y
    tu = 0.25
    ops.uniaxialMaterial(
        "IMKPeakOriented", tag, K,
        prm["theta_p"], prm["theta_pc"], tu, My_pos, prm["mc_my"], 0.10,
        prm["theta_p"], prm["theta_pc"], tu, My_neg, prm["mc_my"], 0.10,
        Lam, Lam, Lam, Lam, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0)
    return (n + 1) / n


# ---------------------------------------------------------------------------
def construir_modelo(a: Arquetipo, s: Secciones, tipo: str = "fibras"):
    """tipo: "elastico" (diseño), "fibras" o "imk" (vigas con rótulas IMK)."""
    ops.wipe()
    ops.model("basic", "-ndm", 3, "-ndf", 6)
    nx, ny, nz = a.n_vanos_x, a.n_vanos_y, a.n_pisos
    xs = [i * a.L_vano_x for i in range(nx + 1)]
    ys = [j * a.L_vano_y for j in range(ny + 1)]
    muros = _ubicacion_muros(a, s)

    # ---------------- nodos, masas y diafragmas ----------------
    for k in range(nz + 1):
        z = k * a.h_piso
        for j, y in enumerate(ys):
            for i, x in enumerate(xs):
                ops.node(_tag(i, j, k), x, y, z)
                if k == 0:
                    ops.fix(_tag(i, j, k), 1, 1, 1, 1, 1, 1)
        for w, (x, y, _, _) in enumerate(muros):
            ops.node(_tag_muro(w, k), x, y, z)
            if k == 0:
                ops.fix(_tag_muro(w, k), 1, 1, 1, 1, 1, 1)
        if k > 0:
            m = a.W_piso / G_ACC
            Iz = m * (a.Lx ** 2 + a.Ly ** 2) / 12.0
            ops.node(_tag_master(k), a.Lx / 2.0, a.Ly / 2.0, z)
            ops.fix(_tag_master(k), 0, 0, 1, 1, 1, 0)
            ops.mass(_tag_master(k), m, m, 0.0, 0.0, 0.0, Iz)
            esclavos = [_tag(i, j, k) for j in range(ny + 1) for i in range(nx + 1)]
            esclavos += [_tag_muro(w, k) for w in range(len(muros))]
            ops.rigidDiaphragm(3, _tag_master(k), *esclavos)

    # ---------------- transformaciones ----------------
    ops.geomTransf("PDelta", 1, 1.0, 0.0, 0.0)   # columnas/muros: z_local = X
    ops.geomTransf("Linear", 2, 0.0, 0.0, 1.0)   # vigas en X:     z_local = Z
    ops.geomTransf("Linear", 3, 0.0, 0.0, 1.0)   # vigas en Y:     z_local = Z

    Ec = a.Ec_kpa
    Gc = Ec / 2.4
    ele = 1

    # ---------------- columnas ----------------
    dy_c, dz_c = s.h_col, s.b_col
    if tipo == "elastico":
        A = dy_c * dz_c
        Iz, Iy = dz_c * dy_c ** 3 / 12, dy_c * dz_c ** 3 / 12
        J = _torsion_rect(dy_c, dz_c)
    else:
        _materiales(a)
        _seccion_rect_fibras(10, dy_c, dz_c, s.rho_col, a)
        ops.beamIntegration("Lobatto", 10, 10, 5)
    for k in range(1, nz + 1):
        for j in range(ny + 1):
            for i in range(nx + 1):
                ni, nj = _tag(i, j, k - 1), _tag(i, j, k)
                if tipo == "elastico":
                    ops.element("elasticBeamColumn", ele, ni, nj, A, Ec, Gc,
                                J, Iy, Iz, 1)
                else:
                    ops.element("forceBeamColumn", ele, ni, nj, 1, 10,
                                "-iter", 20, 1e-10)
                ele += 1

    # ---------------- muros (columna ancha) ----------------
    for w, (_, _, ori, Lw) in enumerate(muros):
        dy_w, dz_w = (Lw, s.t_muro) if ori == "y" else (s.t_muro, Lw)
        # Rigidez a corte de los muros (indispensable en muros robustos,
        # H/Lw < 3, donde domina la deformación por corte): Av = 5/6·A.
        Av = 5.0 / 6.0 * dy_w * dz_w
        if tipo != "elastico":
            _seccion_rect_fibras(100 + w, dy_w, dz_w, s.rho_muro_alma, a,
                                 rho_borde=s.rho_muro_borde)
            # Corte elástico agregado a la sección de fibras (Aggregator):
            # rigidez G·Av, como recomienda ASCE 41 para muros (0.4·Ec·Aw).
            ops.uniaxialMaterial("Elastic", 300 + w, Gc * Av)
            ops.section("Aggregator", 500 + w, 300 + w, "Vy", 300 + w, "Vz",
                        "-section", 100 + w)
            ops.beamIntegration("Lobatto", 100 + w, 500 + w, 5)
        for k in range(1, nz + 1):
            ni, nj = _tag_muro(w, k - 1), _tag_muro(w, k)
            if tipo == "elastico":
                A = dy_w * dz_w
                ops.element("ElasticTimoshenkoBeam", ele, ni, nj, Ec, Gc, A,
                            _torsion_rect(dy_w, dz_w),
                            dy_w * dz_w ** 3 / 12, dz_w * dy_w ** 3 / 12,
                            Av, Av, 1)
            else:
                ops.element("forceBeamColumn", ele, ni, nj, 1, 100 + w,
                            "-iter", 20, 1e-10)
            ele += 1

    # ---------------- vigas ----------------
    b, h = s.b_viga, s.h_viga
    A_v = b * h
    Iy_v, Iz_v = b * h ** 3 / 12, h * b ** 3 / 12
    J_v = _torsion_rect(b, h)
    if tipo == "fibras":
        _seccion_viga_fibras(30, b, h, s.rho_viga_sup, s.rho_viga_inf, a)
        ops.beamIntegration("Lobatto", 30, 30, 5)
    nodo_extra = 600000
    mat_imk = 1000

    def viga(ni: int, nj: int, transf: int, L: float, dir_rot: int):
        nonlocal ele, nodo_extra, mat_imk
        if tipo == "elastico":
            ops.element("elasticBeamColumn", ele, ni, nj, A_v, Ec, Gc, J_v,
                        Iy_v, Iz_v, transf)
            ele += 1
        elif tipo == "fibras":
            ops.element("forceBeamColumn", ele, ni, nj, transf, 30,
                        "-iter", 20, 1e-10)
            ele += 1
        else:  # imk: resorte - elástico - resorte
            d = h - 0.05
            fy = a.fy_kpa
            My_neg = s.rho_viga_sup * b * d * fy * 0.9 * d
            My_pos = s.rho_viga_inf * b * d * fy * 0.9 * d
            prm = parametros_imk_haselton(
                nu=0.0, rho_sh=0.005, fc_mpa=a.fc_kpa / 1000.0, s_d=0.25,
                rho=s.rho_viga_sup)
            EI = prm["EIy_EIg"] * Ec * Iy_v
            extremos = []
            for n_orig in (ni, nj):
                x, y, z = ops.nodeCoord(n_orig)
                ops.node(nodo_extra, x, y, z)
                mat_imk += 1
                fac = _material_imk(mat_imk, My_pos, My_neg, EI, L, prm)
                mats, dirs = [], []
                for dd in range(1, 7):
                    mats.append(mat_imk if dd == dir_rot else 4)
                    dirs.append(dd)
                ops.element("zeroLength", ele, n_orig, nodo_extra,
                            "-mat", *mats, "-dir", *dirs)
                ele += 1
                extremos.append(nodo_extra)
                nodo_extra += 1
            ops.element("elasticBeamColumn", ele, extremos[0], extremos[1],
                        A_v, Ec, Gc, J_v, Iy_v * prm["EIy_EIg"] * fac,
                        Iz_v, transf)
            ele += 1

    for k in range(1, nz + 1):
        for j in range(ny + 1):
            for i in range(nx):
                viga(_tag(i, j, k), _tag(i + 1, j, k), 2, a.L_vano_x, 5)
        for i in range(nx + 1):
            for j in range(ny):
                viga(_tag(i, j, k), _tag(i, j + 1, k), 3, a.L_vano_y, 4)

    # ---------------- cargas de gravedad (1.0 CM + 0.25 CV) ----------------
    ops.timeSeries("Constant", 1)
    ops.pattern("Plain", 1, 1)
    # Muros: carga de la franja tributaria de 1/2 vano a cada lado del muro
    # (la carga axial de compresión es determinante en su respuesta).
    for w, (_, _, ori, Lw) in enumerate(muros):
        b_trib = a.L_vano_y if ori == "x" else a.L_vano_x
        for k in range(1, nz + 1):
            ops.load(_tag_muro(w, k), 0.0, 0.0, -a.w_sismico * Lw * b_trib,
                     0.0, 0.0, 0.0)
    for k in range(1, nz + 1):
        for j in range(ny + 1):
            for i in range(nx + 1):
                fx = 0.5 if i in (0, nx) else 1.0
                fy_ = 0.5 if j in (0, ny) else 1.0
                P = a.w_sismico * a.L_vano_x * a.L_vano_y * fx * fy_
                ops.load(_tag(i, j, k), 0.0, 0.0, -P, 0.0, 0.0, 0.0)
    return muros


def periodos(n: int = 3) -> np.ndarray:
    lam = _eigen(n)
    return 2 * np.pi / np.sqrt(np.array(lam))


def nodos_base(a: Arquetipo, n_muros: int) -> list[int]:
    base = [_tag(i, j, 0) for j in range(a.n_vanos_y + 1)
            for i in range(a.n_vanos_x + 1)]
    return base + [_tag_muro(w, 0) for w in range(n_muros)]


# ============================================================================
# 3. Análisis de gravedad, modal, amortiguamiento y NLTHA bidireccional
# ============================================================================
def analisis_gravedad(n_pasos: int = 10) -> bool:
    ops.constraints("Transformation")
    ops.numberer("RCM")
    ops.system("UmfPack")
    ops.test("NormDispIncr", 1e-6, 50)
    ops.algorithm("Newton")
    ops.integrator("LoadControl", 1.0 / n_pasos)
    ops.analysis("Static")
    ok = ops.analyze(n_pasos)
    ops.loadConst("-time", 0.0)
    return ok == 0


def amortiguamiento_rayleigh(xi: float = 0.05, modos=(1, 3)) -> np.ndarray:
    """Rayleigh con rigidez comprometida (evita fuerzas espurias post-fluencia)."""
    n = max(modos)
    lam = np.array(_eigen(n))
    w = np.sqrt(lam)
    wi, wj = w[modos[0] - 1], w[modos[1] - 1]
    alfa_m = xi * 2 * wi * wj / (wi + wj)
    beta_k = xi * 2 / (wi + wj)
    ops.rayleigh(alfa_m, 0.0, 0.0, beta_k)
    return 2 * np.pi / w


@dataclass
class ResultadoNLTHA:
    MIDR: float
    MIDR_x: float
    MIDR_y: float
    piso_critico: int
    Vb_x: float
    Vb_y: float
    Vb: float
    Vb_W: float
    deriva_residual: float
    colapso: int
    convergencia: int
    t_final: float


def nltha_bidireccional(a: Arquetipo, n_muros: int, acc_x: np.ndarray,
                        acc_y: np.ndarray, dt: float, factor: float = 1.0,
                        dt_analisis: float | None = None,
                        t_libre: float = 1.0, deriva_colapso: float = 0.10,
                        deriva_inestable: float = 0.04,
                        ) -> ResultadoNLTHA:
    """NLTHA con las dos componentes horizontales actuando simultáneamente.

    acc_x, acc_y: aceleraciones en g (mismo dt). factor: escala aplicada a
    ambas componentes. Se asume que el modelo ya pasó gravedad y Rayleigh.

    Colapso: MIDR > deriva_colapso, o no convergencia con MIDR ≥
    deriva_inestable. Una no convergencia con deriva menor se reporta como
    falla numérica (convergencia = 0) y el caso no se usa para entrenar.
    """
    npts = min(len(acc_x), len(acc_y))
    ops.timeSeries("Path", 2, "-dt", dt, "-values", *acc_x[:npts],
                   "-factor", factor * G_ACC)
    ops.timeSeries("Path", 3, "-dt", dt, "-values", *acc_y[:npts],
                   "-factor", factor * G_ACC)
    ops.pattern("UniformExcitation", 2, 1, "-accel", 2)
    ops.pattern("UniformExcitation", 3, 2, "-accel", 3)

    ops.wipeAnalysis()
    ops.constraints("Transformation")
    ops.numberer("RCM")
    ops.system("UmfPack")
    ops.test("NormDispIncr", 1e-6, 50)
    ops.algorithm("Newton")
    ops.integrator("Newmark", 0.5, 0.25)
    ops.analysis("Transient")

    dt_a = dt_analisis or min(dt, 0.01)
    t_total = npts * dt + t_libre
    masters = [_tag_master(k) for k in range(1, a.n_pisos + 1)]
    base = nodos_base(a, n_muros)
    h = a.h_piso
    MIDR_x = MIDR_y = MIDR = 0.0
    piso_crit = 1
    Vbx = Vby = Vb = 0.0
    colapso = 0
    algoritmos = [("NewtonLineSearch", "-type", "Bisection"),
                  ("ModifiedNewton", "-initial"), ("KrylovNewton",),
                  ("Broyden", 8)]
    falla_numerica = False
    t = 0.0
    while t < t_total - 1e-9:
        ok = ops.analyze(1, dt_a)
        if ok != 0:
            # Subdivisión adaptativa: algoritmos alternativos con pasos
            # 1/4, 1/20 y 1/100 del original, y tolerancia relajada al final.
            for n_sub, tol in ((4, 1e-6), (20, 1e-6), (100, 1e-5)):
                ops.test("NormDispIncr", tol, 100)
                for alg in algoritmos:
                    ops.algorithm(*alg)
                    ok = ops.analyze(n_sub, dt_a / n_sub)
                    if ok == 0:
                        break
                if ok == 0:
                    break
            ops.test("NormDispIncr", 1e-6, 50)
            ops.algorithm("Newton")
        if ok != 0:
            # Sin convergencia: con deriva grande es inestabilidad dinámica
            # (colapso); con deriva pequeña es una falla numérica, el caso
            # NO se etiqueta como colapso y se excluye del entrenamiento.
            if MIDR >= deriva_inestable:
                colapso = 1
            else:
                falla_numerica = True
            break
        t = ops.getTime()
        ux = np.array([0.0] + [ops.nodeDisp(m, 1) for m in masters])
        uy = np.array([0.0] + [ops.nodeDisp(m, 2) for m in masters])
        dx = np.abs(np.diff(ux)) / h
        dy = np.abs(np.diff(uy)) / h
        dmax = np.maximum(dx, dy)
        if dx.max() > MIDR_x:
            MIDR_x = float(dx.max())
        if dy.max() > MIDR_y:
            MIDR_y = float(dy.max())
        if dmax.max() > MIDR:
            MIDR = float(dmax.max())
            piso_crit = int(np.argmax(dmax)) + 1
        ops.reactions()
        vx = -sum(ops.nodeReaction(n, 1) for n in base)
        vy = -sum(ops.nodeReaction(n, 2) for n in base)
        Vbx, Vby = max(Vbx, abs(vx)), max(Vby, abs(vy))
        Vb = max(Vb, math.hypot(vx, vy))
        if MIDR > deriva_colapso:
            colapso = 1
            break
    ux = np.array([0.0] + [ops.nodeDisp(m, 1) for m in masters])
    uy = np.array([0.0] + [ops.nodeDisp(m, 2) for m in masters])
    resid = float(np.max(np.maximum(np.abs(np.diff(ux)), np.abs(np.diff(uy)))) / h)
    if colapso:
        MIDR = max(MIDR, deriva_colapso)
    return ResultadoNLTHA(
        MIDR=MIDR, MIDR_x=MIDR_x, MIDR_y=MIDR_y, piso_critico=piso_crit,
        Vb_x=Vbx, Vb_y=Vby, Vb=Vb, Vb_W=Vb / a.W_total,
        deriva_residual=resid, colapso=colapso,
        convergencia=int(not falla_numerica), t_final=float(t))


def correr_caso(a: Arquetipo, s: Secciones, acc_x, acc_y, dt, factor,
                tipo: str = "fibras", **kw) -> dict:
    """Pipeline completo de un caso: modelo → gravedad → Rayleigh → NLTHA."""
    muros = construir_modelo(a, s, tipo=tipo)
    if not analisis_gravedad():
        ops.wipe()
        return dict(error="gravedad")
    T = amortiguamiento_rayleigh(0.05, (1, 3))
    r = nltha_bidireccional(a, len(muros), acc_x, acc_y, dt, factor, **kw)
    ops.wipe()
    out = dict(T1_nl=T[0], T2_nl=T[1], T3_nl=T[2])
    out.update(r.__dict__)
    return out
