"""
portfolio.py — Simulation du portefeuille & stress test
=========================================================
- Distribution des pertes agrégées (N_ASSURES assurés × N_PORT_SIM scénarios)
- Rentabilité annuelle sur N_ANNEES ans
- Gain net de l'assuré sur 20 ans
- Stress test climatique
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field

from .config import (
    MU_LOG, SIGMA_LOG, TRIGGER, PAYOUT, LOADING,
    N_ANNEES, N_ASSURES, N_SIM_ASSURE, N_PORT_SIM, RANDOM_SEED,
    DATA_DIR,
)
from .actuarial import ActuarialMetrics


# ─── Pertes agrégées ─────────────────────────────────────────────────────────

@dataclass
class AggregateRisk:
    """Distribution des pertes agrégées du portefeuille."""
    pertes_nettes:  np.ndarray   # perte nette par scénario (>0 = déficit)
    profits:        np.ndarray   # profit par scénario
    E_profit:       float
    std_profit:     float
    VaR_95:         float        # perte nette au quantile 95%
    VaR_99:         float
    CVaR_95:        float        # Expected Shortfall 95%
    CVaR_99:        float
    p_deficit:      float        # P(profit < 0)
    primes_an:      float


def compute_aggregate_risk(
    metrics: ActuarialMetrics,
    n_assures: int = N_ASSURES,
    n_sim: int = N_PORT_SIM,
    seed: int = RANDOM_SEED + 1,
) -> AggregateRisk:
    """
    Simule n_sim scénarios annuels pour un portefeuille de n_assures assurés.
    Calcule VaR et CVaR sur la distribution des pertes agrégées.
    """
    rng = np.random.default_rng(seed)
    precip_mat  = rng.lognormal(MU_LOG, SIGMA_LOG, (n_sim, n_assures))
    payout_mat  = np.where(precip_mat < TRIGGER, float(PAYOUT), 0.0)
    pertes_tot  = payout_mat.sum(axis=1)           # sinistres agrégés par scénario

    primes_an   = n_assures * metrics.prime_commerciale
    profits     = primes_an - pertes_tot
    pertes_net  = -profits                          # >0 = mauvais pour assureur

    VaR_95  = float(np.percentile(pertes_net, 95))
    VaR_99  = float(np.percentile(pertes_net, 99))
    CVaR_95 = float(np.mean(pertes_net[pertes_net >= VaR_95]))
    CVaR_99 = float(np.mean(pertes_net[pertes_net >= VaR_99]))

    return AggregateRisk(
        pertes_nettes = pertes_net,
        profits       = profits,
        E_profit      = float(np.mean(profits)),
        std_profit    = float(np.std(profits)),
        VaR_95        = VaR_95,
        VaR_99        = VaR_99,
        CVaR_95       = CVaR_95,
        CVaR_99       = CVaR_99,
        p_deficit     = float(np.mean(profits < 0)),
        primes_an     = primes_an,
    )


# ─── Rentabilité annuelle ─────────────────────────────────────────────────────

def simulate_annual_portfolio(
    metrics: ActuarialMetrics,
    n_annees: int = N_ANNEES,
    n_assures: int = N_ASSURES,
    seed: int = RANDOM_SEED + 2,
) -> pd.DataFrame:
    """
    Simule la rentabilité année par année sur n_annees ans.

    Retourne un DataFrame avec une ligne par année.
    Exporte aussi un CSV dans results/data/.
    """
    rng  = np.random.default_rng(seed)
    rows = []

    for annee in range(1, n_annees + 1):
        precip    = rng.lognormal(MU_LOG, SIGMA_LOG, n_assures)
        nb_sin    = int((precip < TRIGGER).sum())
        primes    = n_assures * metrics.prime_commerciale
        indemn    = nb_sin * PAYOUT
        profit    = primes - indemn

        rows.append({
            "annee"            : annee,
            "precip_moy_mm"    : round(float(np.mean(precip)), 1),
            "nb_sinistres"     : nb_sin,
            "taux_sinistralite": round(nb_sin / n_assures, 4),
            "primes_col_eur"   : round(primes, 2),
            "indemnisations_eur": round(indemn, 2),
            "profit_assureur_eur": round(profit, 2),
            "profit_par_assure_eur": round(profit / n_assures, 2),
        })

    df = pd.DataFrame(rows)

    csv_path = DATA_DIR / "resultats_annuels.csv"
    df.to_csv(csv_path, index=False)
    print(f"  CSV exporté → {csv_path}")

    return df


def print_portfolio_summary(df: pd.DataFrame, metrics: ActuarialMetrics) -> None:
    print("\n[Portefeuille] Rentabilité annuelle")
    print(f"  Prime commerciale/assuré  : {metrics.prime_commerciale:,.2f} €/an")
    print(f"  Profit moyen assureur/an  : {df['profit_assureur_eur'].mean():,.0f} €")
    print(f"  Profit par assuré/an      : {df['profit_par_assure_eur'].mean():,.2f} €")
    print(f"  Taux sinistralité moyen   : {df['taux_sinistralite'].mean()*100:.2f}%")
    print(f"  Années déficitaires       : {(df['profit_assureur_eur'] < 0).sum()} / {len(df)}")


# ─── Gain net de l'assuré ─────────────────────────────────────────────────────

@dataclass
class InsuredGain:
    """Distribution du gain net de l'assuré sur N_ANNEES ans."""
    gains:          np.ndarray
    E_gain:         float
    median_gain:    float
    p_positive:     float        # % d'assurés avec gain net positif
    cout_loading:   float        # coût annuel du loading = −E_gain / N_ANNEES


def simulate_insured_gain(
    metrics: ActuarialMetrics,
    n_annees: int = N_ANNEES,
    n_sim: int = N_SIM_ASSURE,
    seed: int = RANDOM_SEED + 3,
) -> InsuredGain:
    """
    Simule le gain net de n_sim assurés sur n_annees ans (vectorisé).

    gain_net = Σ payouts reçus − Σ primes payées
    """
    rng        = np.random.default_rng(seed)
    precip_mat = rng.lognormal(MU_LOG, SIGMA_LOG, (n_sim, n_annees))
    payouts    = np.where(precip_mat < TRIGGER, float(PAYOUT), 0.0)
    total_pay  = payouts.sum(axis=1)
    total_prim = n_annees * metrics.prime_commerciale
    gains      = total_pay - total_prim

    E_gain = float(np.mean(gains))

    return InsuredGain(
        gains        = gains,
        E_gain       = E_gain,
        median_gain  = float(np.median(gains)),
        p_positive   = float(np.mean(gains > 0)),
        cout_loading = -E_gain / n_annees,
    )


def print_insured_summary(ig: InsuredGain, n_annees: int = N_ANNEES) -> None:
    print("\n[Assuré] Gain net sur", n_annees, "ans")
    print(f"  E[gain net]            : {ig.E_gain:,.0f} €")
    print(f"  Médiane                : {ig.median_gain:,.0f} €")
    print(f"  % gain net > 0         : {ig.p_positive*100:.1f}%")
    print(f"  Coût loading annuel    : {ig.cout_loading:.0f} €/an")


# ─── Stress test ──────────────────────────────────────────────────────────────

@dataclass
class StressResult:
    label:        str
    facteur:      float
    p_drought:    float
    prime_req:    float
    profit_port:  float          # profit attendu du portefeuille


def run_stress_test(
    precipitations: np.ndarray,
    metrics: ActuarialMetrics,
    n_assures: int = N_ASSURES,
) -> list[StressResult]:
    """
    Applique 5 scénarios de stress (réduction des précipitations)
    et calcule la prime requise + le profit pour chaque scénario.
    """
    scenarios = [
        ("Normal",  1.00),
        ("−10%",    0.90),
        ("−20%",    0.80),
        ("−30%",    0.70),
        ("−40%",    0.60),
    ]
    results = []
    for label, f in scenarios:
        precip_s = precipitations * f
        p_s      = float(np.mean(precip_s < TRIGGER))
        prim_s   = p_s * PAYOUT * (1 + LOADING)
        prof_s   = n_assures * metrics.prime_commerciale - n_assures * p_s * PAYOUT
        results.append(StressResult(
            label       = label,
            facteur     = f,
            p_drought   = p_s,
            prime_req   = prim_s,
            profit_port = prof_s,
        ))
    return results


def print_stress_summary(results: list[StressResult]) -> None:
    print("\n[Stress test] Scénarios climatiques")
    for r in results:
        signe = "PROFIT" if r.profit_port >= 0 else "DÉFICIT"
        print(f"  {r.label:8s} → P(séch)={r.p_drought*100:5.1f}%  "
              f"Prime req.={r.prime_req:,.0f}€  "
              f"Profit portefeuille={r.profit_port:,.0f}€  [{signe}]")
