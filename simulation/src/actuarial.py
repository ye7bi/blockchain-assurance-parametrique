"""
actuarial.py — Calculs actuariels
==================================
Prime pure, prime commerciale, VaR individuelle, convergence Monte Carlo.
"""

import numpy as np
from dataclasses import dataclass

from .config import PAYOUT, LOADING, N_SIMUL
from .climate import ClimateData


@dataclass
class ActuarialMetrics:
    """Métriques actuarielles au niveau individuel."""
    # Payout
    payouts:           np.ndarray   # vecteur des payouts simulés (N_SIMUL,)
    E_payout:          float        # espérance simulée
    E_payout_th:       float        # espérance théorique (p × C)
    std_payout:        float        # écart-type simulé
    std_payout_th:     float        # écart-type théorique (Bernoulli)
    # Prime
    prime_pure:        float        # prime nette = E[payout]
    prime_commerciale: float        # prime brute = prime_pure × (1 + λ)
    loading:           float        # chargement
    loss_ratio:        float        # LR = prime_pure / prime_commerciale
    # IC sur la prime
    ic_95_inf:         float
    ic_95_sup:         float
    # Convergence MC
    n_steps:           np.ndarray   # pas de convergence
    means_conv:        list         # E[payout] cumulé à chaque pas
    ic_sup_conv:       list
    ic_inf_conv:       list


def compute_actuarial_metrics(
    climate: ClimateData,
    payout: float = PAYOUT,
    loading: float = LOADING,
    n_simul: int = N_SIMUL,
) -> ActuarialMetrics:
    """
    Calcule toutes les métriques actuarielles à partir des données climatiques.

    Prime pure : π = E[payout] = p × C
    Prime comm.: π_c = π × (1 + λ)
    Loss Ratio  : LR = π / π_c = 1 / (1 + λ)
    """
    precip  = climate.precipitations
    p_th    = climate.p_drought_th

    # Payout binaire : C si précipitations < trigger, 0 sinon
    from .config import TRIGGER
    payouts = np.where(precip < TRIGGER, float(payout), 0.0)

    E_pay   = float(np.mean(payouts))
    std_pay = float(np.std(payouts))

    # Théorique (loi de Bernoulli)
    E_th    = p_th * payout
    std_th  = float(np.sqrt(p_th * (1 - p_th) * payout**2))

    # Primes
    pp   = E_pay
    pc   = pp * (1 + loading)
    lr   = pp / pc

    # IC 95% sur la prime (TCL)
    z95       = 1.96
    demi_ic   = z95 * std_pay / np.sqrt(n_simul)
    ic_inf    = pp - demi_ic
    ic_sup    = pp + demi_ic

    # Courbe de convergence Monte Carlo
    n_steps   = np.unique(np.logspace(2, np.log10(n_simul), 250).astype(int))
    means_c   = [float(np.mean(payouts[:n])) for n in n_steps]
    ic_s_c    = [E_pay + z95 * std_pay / np.sqrt(n) for n in n_steps]
    ic_i_c    = [E_pay - z95 * std_pay / np.sqrt(n) for n in n_steps]

    return ActuarialMetrics(
        payouts           = payouts,
        E_payout          = E_pay,
        E_payout_th       = E_th,
        std_payout        = std_pay,
        std_payout_th     = std_th,
        prime_pure        = pp,
        prime_commerciale = pc,
        loading           = loading,
        loss_ratio        = lr,
        ic_95_inf         = ic_inf,
        ic_95_sup         = ic_sup,
        n_steps           = n_steps,
        means_conv        = means_c,
        ic_sup_conv       = ic_s_c,
        ic_inf_conv       = ic_i_c,
    )


def print_actuarial_summary(m: ActuarialMetrics) -> None:
    print("\n[Actuariat] Métriques individuelles")
    print(f"  E[payout] simulé       : {m.E_payout:,.2f} €")
    print(f"  E[payout] théorique    : {m.E_payout_th:,.2f} €")
    print(f"  σ[payout] simulé       : {m.std_payout:,.2f} €")
    print(f"  σ[payout] théorique    : {m.std_payout_th:,.2f} €")
    print(f"  Prime pure             : {m.prime_pure:,.2f} €/an")
    print(f"  IC 95% prime pure      : [{m.ic_95_inf:.2f} ; {m.ic_95_sup:.2f}]")
    print(f"  Prime commerciale (+{m.loading*100:.0f}%): {m.prime_commerciale:,.2f} €/an")
    print(f"  Loss Ratio             : {m.loss_ratio*100:.1f}%")
