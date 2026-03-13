"""
climate.py — Génération des scénarios climatiques
==================================================
Simule les précipitations annuelles selon une loi lognormale
et valide l'ajustement par un test de Kolmogorov-Smirnov.
"""

import numpy as np
from dataclasses import dataclass
from scipy.stats import lognorm, kstest

from .config import MU_LOG, SIGMA_LOG, TRIGGER, N_SIMUL, RANDOM_SEED


@dataclass
class ClimateData:
    """Résultat de la simulation climatique."""
    precipitations: np.ndarray   # N_SIMUL valeurs (mm)
    p_drought_emp:  float        # P(X < trigger) empirique
    p_drought_th:   float        # P(X < trigger) théorique (CDF)
    ks_stat:        float        # statistique KS
    ks_pvalue:      float        # p-value du test KS
    median_th:      float        # médiane théorique (exp(μ))
    mean_th:        float        # moyenne théorique (exp(μ + σ²/2))


def generate_precipitation(
    n: int = N_SIMUL,
    mu: float = MU_LOG,
    sigma: float = SIGMA_LOG,
    trigger: float = TRIGGER,
    seed: int = RANDOM_SEED,
) -> ClimateData:
    """
    Génère n scénarios de précipitations annuelles selon LN(μ, σ).

    Paramètres
    ----------
    n       : nombre de scénarios
    mu      : paramètre μ de la loi lognormale
    sigma   : paramètre σ de la loi lognormale
    trigger : seuil de sécheresse (mm)
    seed    : graine aléatoire

    Retourne
    --------
    ClimateData : struct contenant les précipitations et les métriques
    """
    rng = np.random.default_rng(seed)
    precip = rng.lognormal(mean=mu, sigma=sigma, size=n)

    p_emp = float(np.mean(precip < trigger))
    p_th  = float(lognorm.cdf(trigger, s=sigma, scale=np.exp(mu)))

    # Test KS sur les log-précipitations (normalité)
    ks_stat, ks_p = kstest(np.log(precip), "norm", args=(mu, sigma))

    return ClimateData(
        precipitations = precip,
        p_drought_emp  = p_emp,
        p_drought_th   = p_th,
        ks_stat        = float(ks_stat),
        ks_pvalue      = float(ks_p),
        median_th      = float(np.exp(mu)),
        mean_th        = float(np.exp(mu + 0.5 * sigma**2)),
    )


def print_climate_summary(data: ClimateData) -> None:
    print("\n[Climat] Résultats de la simulation")
    print(f"  Médiane théorique    : {data.median_th:.0f} mm/an")
    print(f"  Moyenne théorique    : {data.mean_th:.0f} mm/an")
    print(f"  P(sécheresse) emp.   : {data.p_drought_emp*100:.2f}%")
    print(f"  P(sécheresse) th.    : {data.p_drought_th*100:.2f}%")
    ks_ok = "✓ validé" if data.ks_pvalue > 0.05 else "✗ rejeté"
    print(f"  Test KS lognormalité : stat={data.ks_stat:.5f}  p={data.ks_pvalue:.3f}  {ks_ok}")
