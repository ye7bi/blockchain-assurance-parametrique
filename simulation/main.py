"""
main.py — Point d'entrée de la simulation
==========================================
Assurance Paramétrique Agricole sur Blockchain
ECE Paris — Master 2 MsC2 DEIA

Usage :
    python main.py

Sorties :
    results/figures/   → 12 graphiques individuels (.png)
    results/data/      → resultats_annuels.csv
"""

import time
from src.config import (
    MU_LOG, SIGMA_LOG, TRIGGER, PAYOUT, LOADING,
    N_SIMUL, N_ANNEES, N_ASSURES, FIGURES_DIR, DATA_DIR,
)
from src.climate    import generate_precipitation, print_climate_summary
from src.actuarial  import compute_actuarial_metrics, print_actuarial_summary
from src.portfolio  import (
    compute_aggregate_risk,
    simulate_annual_portfolio,
    simulate_insured_gain,
    run_stress_test,
    print_portfolio_summary,
    print_insured_summary,
    print_stress_summary,
)
from src.basis_risk import compute_basis_risk, print_basis_risk_summary
from src.plots      import (
    plot_precipitation_distribution,
    plot_monte_carlo_convergence,
    plot_payout_distribution,
    plot_aggregate_loss,
    plot_annual_profit,
    plot_loss_ratio,
    plot_insured_gain,
    plot_stress_test,
    plot_comparison,
    plot_basis_risk_scatter,
    plot_basis_risk_distribution,
    plot_basis_risk_sensitivity,
)


def main() -> None:
    t0 = time.perf_counter()

    # ── Création des répertoires ─────────────────────────────────────────────
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 66)
    print("  ASSURANCE PARAMÉTRIQUE AGRICOLE — SIMULATION MONTE CARLO")
    print("  ECE Paris  |  Master 2 MsC2 DEIA")
    print("=" * 66)
    print(f"\n  Modèle   : Lognormale(μ={MU_LOG}, σ={SIGMA_LOG})")
    print(f"  Trigger  : {TRIGGER} mm/an  |  Payout : {PAYOUT:,} €")
    print(f"  Loading  : {LOADING*100:.0f}%  |  Portefeuille : {N_ASSURES} assurés")
    print(f"  MC       : {N_SIMUL:,} scénarios  |  Horizon : {N_ANNEES} ans")

    # ── 1. Scénarios climatiques ─────────────────────────────────────────────
    print("\n" + "─" * 66)
    print("  ÉTAPE 1/5 — Scénarios climatiques")
    print("─" * 66)
    climate = generate_precipitation()
    print_climate_summary(climate)

    # ── 2. Métriques actuarielles ────────────────────────────────────────────
    print("\n" + "─" * 66)
    print("  ÉTAPE 2/5 — Calculs actuariels")
    print("─" * 66)
    metrics = compute_actuarial_metrics(climate)
    print_actuarial_summary(metrics)

    # ── 3. Portefeuille ──────────────────────────────────────────────────────
    print("\n" + "─" * 66)
    print("  ÉTAPE 3/5 — Simulation du portefeuille")
    print("─" * 66)
    agg    = compute_aggregate_risk(metrics)
    df     = simulate_annual_portfolio(metrics)
    ig     = simulate_insured_gain(metrics)
    stress = run_stress_test(climate.precipitations, metrics)

    print_portfolio_summary(df, metrics)
    print(f"\n[Risque agrégé]")
    print(f"  VaR 95%  (perte nette) : {agg.VaR_95:,.0f} €")
    print(f"  VaR 99%  (perte nette) : {agg.VaR_99:,.0f} €")
    print(f"  CVaR 99%               : {agg.CVaR_99:,.0f} €")
    print(f"  P(déficit assureur)    : {agg.p_deficit*100:.2f}%")

    print_insured_summary(ig)
    print_stress_summary(stress)

    # ── 4. Basis Risk ────────────────────────────────────────────────────────
    print("\n" + "─" * 66)
    print("  ÉTAPE 4/5 — Analyse du basis risk")
    print("─" * 66)
    br = compute_basis_risk()
    print_basis_risk_summary(br)

    # ── 5. Génération des graphiques ─────────────────────────────────────────
    print("\n" + "─" * 66)
    print("  ÉTAPE 5/5 — Génération des graphiques")
    print("─" * 66)

    plot_precipitation_distribution(climate)
    plot_monte_carlo_convergence(metrics)
    plot_payout_distribution(metrics)
    plot_aggregate_loss(agg)
    plot_annual_profit(df)
    plot_loss_ratio(df, climate)
    plot_insured_gain(ig)
    plot_stress_test(stress, metrics)
    plot_comparison(metrics)
    plot_basis_risk_scatter(br)
    plot_basis_risk_distribution(br)
    plot_basis_risk_sensitivity(br)

    # ── Résumé exécutif ──────────────────────────────────────────────────────
    elapsed = time.perf_counter() - t0
    print("\n" + "=" * 66)
    print("  RÉSUMÉ EXÉCUTIF")
    print("=" * 66)
    print(f"""
  PRODUIT
    Trigger : précipitations < {TRIGGER} mm/an  |  Payout : {PAYOUT:,} €

  ACTUARIAT
    P(sécheresse)            : {climate.p_drought_emp*100:.2f}%
    Prime pure               : {metrics.prime_pure:,.2f} €/an
    IC 95% prime             : [{metrics.ic_95_inf:.2f} ; {metrics.ic_95_sup:.2f}]
    Prime commerciale (+{LOADING*100:.0f}%)   : {metrics.prime_commerciale:,.2f} €/an
    Loss Ratio               : {metrics.loss_ratio*100:.1f}%
    Test KS (lognormalité)   : p = {climate.ks_pvalue:.3f}  {"✓" if climate.ks_pvalue > 0.05 else "✗ (N grand — déviation mineure)"}

  RISQUE PORTEFEUILLE ({N_ASSURES} assurés)
    Profit moyen assureur/an : {agg.E_profit:,.0f} €
    σ(profit)                : {agg.std_profit:,.0f} €
    VaR 99% (perte nette)    : {agg.VaR_99:,.0f} €
    CVaR 99% (ES)            : {agg.CVaR_99:,.0f} €
    P(déficit)               : {agg.p_deficit*100:.2f}%

  STRESS TEST
    −10% précip. → P(séch) {stress[1].p_drought*100:.1f}%  |  prime req. {stress[1].prime_req:.0f} €
    −20% précip. → P(séch) {stress[2].p_drought*100:.1f}%  |  prime req. {stress[2].prime_req:.0f} €
    −30% précip. → P(séch) {stress[3].p_drought*100:.1f}%  |  prime req. {stress[3].prime_req:.0f} €

  PERSPECTIVE ASSURÉ ({N_ANNEES} ans)
    Gain net moyen           : {ig.E_gain:,.0f} €
    % gain positif           : {ig.p_positive*100:.1f}%
    Coût loading annuel      : {ig.cout_loading:.0f} €/an

  BASIS RISK (ρ = {br.rho_cible})
    σ(basis risk)            : {br.std_basis_risk:,.0f} €
    % sous-assurés           : {br.n_sous_assures/br.n_total*100:.1f}%
    % sur-indemnisés         : {br.n_sur_indemnises/br.n_total*100:.1f}%

  SORTIES
    Graphiques (12)          : {FIGURES_DIR}
    Données CSV              : {DATA_DIR / "resultats_annuels.csv"}
    Temps d'exécution        : {elapsed:.1f} s
""")


if __name__ == "__main__":
    main()
