"""
basis_risk.py — Analyse du basis risk
=======================================
Le basis risk est l'écart entre la perte réelle de l'agriculteur
et le payout reçu (basé sur la station météo de référence).

Modèle bivarié lognormal (corrélation dans l'espace log) :
  ln(X_station)  ~ N(μ, σ²)
  ln(X_parcelle) = ρ·(ln(X_s)−μ)/σ·σ + √(1−ρ²)·ε·σ + μ
  avec ε ~ N(0,1) indépendant → Corr(ln X_s, ln X_p) = ρ
"""

import numpy as np
from dataclasses import dataclass

from .config import MU_LOG, SIGMA_LOG, TRIGGER, PAYOUT, N_BASIS, RHO_BASIS, RANDOM_SEED


@dataclass
class BasisRiskData:
    """Résultats de l'analyse du basis risk."""
    precip_station:   np.ndarray   # précipitations station (oracle)
    precip_parcelle:  np.ndarray   # précipitations parcelle réelle
    payout_recu:      np.ndarray   # indemnisation reçue (basée station)
    perte_reelle:     np.ndarray   # perte estimée (basée parcelle)
    basis_risk:       np.ndarray   # perte − payout = basis risk
    rho_cible:        float
    rho_empirique:    float
    E_basis_risk:     float
    std_basis_risk:   float
    n_sous_assures:   int          # sinistre réel mais pas de payout
    n_sur_indemnises: int          # payout mais pas de sinistre réel
    n_total:          int
    # Courbe sensibilité à ρ
    rhos_sens:        np.ndarray
    std_br_sens:      np.ndarray
    pct_sous_sens:    np.ndarray


def compute_basis_risk(
    rho: float = RHO_BASIS,
    n: int = N_BASIS,
    seed: int = RANDOM_SEED + 4,
) -> BasisRiskData:
    """
    Simule n paires (station, parcelle) corrélées avec coefficient ρ
    et calcule le basis risk pour chaque observation.

    Décomposition de Cholesky dans l'espace log :
      Z_s ~ N(0,1)  (station normalisée)
      Z_p = ρ·Z_s + √(1−ρ²)·ε  avec ε ~ N(0,1) indép.
      → Corr(Z_s, Z_p) = ρ  exactement
    """
    rng = np.random.default_rng(seed)

    # Espace log (normalisé)
    Z_s = rng.standard_normal(n)
    eps = rng.standard_normal(n)
    Z_p = rho * Z_s + np.sqrt(1 - rho**2) * eps

    # Retour espace lognormal
    precip_s = np.exp(MU_LOG + SIGMA_LOG * Z_s)
    precip_p = np.exp(MU_LOG + SIGMA_LOG * Z_p)

    # Vérification corrélation empirique
    rho_emp = float(np.corrcoef(MU_LOG + SIGMA_LOG * Z_s,
                                MU_LOG + SIGMA_LOG * Z_p)[0, 1])

    # Payout reçu (basé sur station oracle)
    payout_recu = np.where(precip_s < TRIGGER, float(PAYOUT), 0.0)

    # Perte réelle (non-linéaire : majoration si sécheresse sévère)
    deficit    = np.maximum(TRIGGER - precip_p, 0.0)
    perte_reel = np.where(
        precip_p < TRIGGER,
        PAYOUT * (1.0 + 0.4 * deficit / TRIGGER),
        0.0,
    )

    br = perte_reel - payout_recu

    n_sous = int(np.sum((perte_reel > 0) & (payout_recu == 0)))
    n_sur  = int(np.sum((perte_reel == 0) & (payout_recu > 0)))

    # Courbe de sensibilité σ(basis risk) en fonction de ρ
    rhos_s   = np.linspace(0.40, 0.99, 30)
    std_s    = np.empty(len(rhos_s))
    pct_s    = np.empty(len(rhos_s))
    rng2     = np.random.default_rng(seed + 99)

    for i, r in enumerate(rhos_s):
        Zs2   = rng2.standard_normal(20_000)
        ep2   = rng2.standard_normal(20_000)
        Zp2   = r * Zs2 + np.sqrt(1 - r**2) * ep2
        ps2   = np.exp(MU_LOG + SIGMA_LOG * Zs2)
        pp2   = np.exp(MU_LOG + SIGMA_LOG * Zp2)
        pr2   = np.where(ps2 < TRIGGER, float(PAYOUT), 0.0)
        def2  = np.maximum(TRIGGER - pp2, 0.0)
        prl2  = np.where(pp2 < TRIGGER, PAYOUT * (1 + 0.4 * def2 / TRIGGER), 0.0)
        br2   = prl2 - pr2
        std_s[i]  = float(np.std(br2))
        pct_s[i]  = float(np.mean((prl2 > 0) & (pr2 == 0))) * 100

    return BasisRiskData(
        precip_station   = precip_s,
        precip_parcelle  = precip_p,
        payout_recu      = payout_recu,
        perte_reelle     = perte_reel,
        basis_risk       = br,
        rho_cible        = rho,
        rho_empirique    = rho_emp,
        E_basis_risk     = float(np.mean(br)),
        std_basis_risk   = float(np.std(br)),
        n_sous_assures   = n_sous,
        n_sur_indemnises = n_sur,
        n_total          = n,
        rhos_sens        = rhos_s,
        std_br_sens      = std_s,
        pct_sous_sens    = pct_s,
    )


def print_basis_risk_summary(b: BasisRiskData) -> None:
    print("\n[Basis Risk] Analyse spatiale")
    print(f"  Corrélation cible (ρ)    : {b.rho_cible:.2f}")
    print(f"  Corrélation empirique    : {b.rho_empirique:.4f}  ✓")
    print(f"  E[basis risk]            : {b.E_basis_risk:,.0f} €")
    print(f"  σ(basis risk)            : {b.std_basis_risk:,.0f} €")
    print(f"  Cas sous-assurés         : {b.n_sous_assures:,} / {b.n_total:,}  "
          f"({b.n_sous_assures/b.n_total*100:.1f}%)")
    print(f"  Cas sur-indemnisés       : {b.n_sur_indemnises:,} / {b.n_total:,}  "
          f"({b.n_sur_indemnises/b.n_total*100:.1f}%)")
