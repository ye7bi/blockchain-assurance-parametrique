"""
plots.py — Fonctions de visualisation (1 graphique = 1 fichier)
================================================================
Chaque fonction plot_XX() :
  - reçoit les données pré-calculées
  - crée une figure autonome
  - la sauvegarde dans results/figures/
  - retourne le chemin du fichier généré
"""

from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from scipy.stats import lognorm

from .config import (
    TRIGGER, PAYOUT, LOADING, MU_LOG, SIGMA_LOG,
    N_ANNEES, N_ASSURES, FIGURES_DIR, MPL_STYLE,
)
from .climate import ClimateData
from .actuarial import ActuarialMetrics
from .portfolio import AggregateRisk, InsuredGain, StressResult
from .basis_risk import BasisRiskData

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _apply_style() -> None:
    plt.rcParams.update(MPL_STYLE)


def _save(fig: plt.Figure, filename: str) -> Path:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURES_DIR / filename
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {filename}")
    return path


# ═══════════════════════════════════════════════════════════════════════════════
# 01 — Distribution des précipitations
# ═══════════════════════════════════════════════════════════════════════════════

def plot_precipitation_distribution(climate: ClimateData) -> Path:
    _apply_style()
    fig, ax = plt.subplots(figsize=(9, 5))

    ax.hist(climate.precipitations, bins=100, color="#2196F3",
            alpha=0.65, edgecolor="none", density=True,
            label="Précipitations simulées")

    x = np.linspace(10, 2_200, 800)
    pdf = lognorm.pdf(x, s=SIGMA_LOG, scale=np.exp(MU_LOG))
    ax.plot(x, pdf, "r-", lw=2, label="PDF lognormale théorique")
    ax.axvline(TRIGGER, color="#FF5722", ls="--", lw=2,
               label=f"Trigger = {TRIGGER} mm")
    ax.fill_between(x[x < TRIGGER], pdf[x < TRIGGER],
                    alpha=0.22, color="#FF5722",
                    label=f"Zone sécheresse ({climate.p_drought_emp*100:.1f}%)")

    ax.set_xlim(0, 1_800)
    ax.set_xlabel("Précipitations annuelles (mm)")
    ax.set_ylabel("Densité de probabilité")
    ax.set_title("Distribution des précipitations annuelles\n"
                 f"Lognormale(μ={MU_LOG}, σ={SIGMA_LOG})  —  "
                 f"médiane théorique = {climate.median_th:.0f} mm/an")
    ax.legend(fontsize=9)

    fig.tight_layout()
    return _save(fig, "01_distribution_precipitations.png")


# ═══════════════════════════════════════════════════════════════════════════════
# 02 — Convergence Monte Carlo
# ═══════════════════════════════════════════════════════════════════════════════

def plot_monte_carlo_convergence(metrics: ActuarialMetrics) -> Path:
    _apply_style()
    fig, ax = plt.subplots(figsize=(9, 5))

    ax.plot(metrics.n_steps, metrics.means_conv,
            color="#9C27B0", lw=1.5, alpha=0.9, label="E[payout] cumulé")
    ax.fill_between(metrics.n_steps,
                    metrics.ic_inf_conv, metrics.ic_sup_conv,
                    alpha=0.25, color="#9C27B0", label="IC 95%")
    ax.axhline(metrics.E_payout, color="red", ls="--", lw=2,
               label=f"Convergence : {metrics.E_payout:.2f} €")

    ax.set_xscale("log")
    ax.set_xlabel("Nombre de simulations")
    ax.set_ylabel("E[payout] estimé (€)")
    ax.set_title("Convergence de la simulation Monte Carlo\n"
                 "Loi des grands nombres — payout individuel")
    ax.legend(fontsize=9)

    fig.tight_layout()
    return _save(fig, "02_convergence_monte_carlo.png")


# ═══════════════════════════════════════════════════════════════════════════════
# 03 — Distribution du payout (binaire)
# ═══════════════════════════════════════════════════════════════════════════════

def plot_payout_distribution(metrics: ActuarialMetrics) -> Path:
    _apply_style()
    fig, ax = plt.subplots(figsize=(7, 5))

    freq_0 = float(np.mean(metrics.payouts == 0)) * 100
    freq_C = float(np.mean(metrics.payouts == PAYOUT)) * 100

    bars = ax.bar(
        [f"Pas d'indemnisation\n(0 €)", f"Indemnisation\n({PAYOUT:,} €)"],
        [freq_0, freq_C],
        color=["#4CAF50", "#FF5722"],
        alpha=0.85, edgecolor="white", linewidth=1.5,
    )
    for bar, val in zip(bars, [freq_0, freq_C]):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.4,
                f"{val:.1f}%", ha="center", fontweight="bold", fontsize=12)

    ax.set_ylim(0, max(freq_0, freq_C) * 1.18)
    ax.set_ylabel("Fréquence (%)")
    ax.set_title("Distribution du payout paramétrique\n"
                 f"E[payout] = {metrics.E_payout:.0f} €  "
                 f"|  Prime pure = {metrics.prime_pure:.0f} €  "
                 f"|  Prime comm. = {metrics.prime_commerciale:.0f} €")

    # Annotation box
    ax.text(0.98, 0.97,
            f"P(déclenchement) = {freq_C:.1f}%\n"
            f"Loading = {LOADING*100:.0f}%\n"
            f"Loss Ratio = {metrics.loss_ratio*100:.1f}%",
            transform=ax.transAxes, fontsize=9,
            va="top", ha="right",
            bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.85))

    fig.tight_layout()
    return _save(fig, "03_distribution_payout.png")


# ═══════════════════════════════════════════════════════════════════════════════
# 04 — Distribution des pertes agrégées (portefeuille)
# ═══════════════════════════════════════════════════════════════════════════════

def plot_aggregate_loss(agg: AggregateRisk) -> Path:
    _apply_style()
    fig, ax = plt.subplots(figsize=(9, 5))

    ax.hist(agg.pertes_nettes / 1_000, bins=120, color="#F44336",
            alpha=0.70, edgecolor="none", density=True)

    for val, col, lab in [
        (agg.VaR_95,  "orange",  f"VaR 95% = {agg.VaR_95/1000:.0f} k€"),
        (agg.VaR_99,  "darkred", f"VaR 99% = {agg.VaR_99/1000:.0f} k€"),
        (agg.CVaR_99, "purple",  f"CVaR 99% = {agg.CVaR_99/1000:.0f} k€"),
    ]:
        ax.axvline(val / 1_000, color=col, ls="--", lw=2, label=lab)

    ax.axvline(0, color="black", lw=1.5, label="Seuil de déficit")

    ax.set_xlabel("Perte nette portefeuille (k€)  [positif = déficit]")
    ax.set_ylabel("Densité")
    ax.set_title(f"Distribution des pertes agrégées\n"
                 f"{N_ASSURES} assurés  —  "
                 f"P(déficit) = {agg.p_deficit*100:.2f}%  —  "
                 f"Profit moyen = {agg.E_profit/1000:.0f} k€/an")
    ax.legend(fontsize=9)

    fig.tight_layout()
    return _save(fig, "04_distribution_pertes_portefeuille.png")


# ═══════════════════════════════════════════════════════════════════════════════
# 05 — Profit annuel assureur
# ═══════════════════════════════════════════════════════════════════════════════

def plot_annual_profit(df) -> Path:
    _apply_style()
    fig, ax = plt.subplots(figsize=(10, 5))

    colors = ["#4CAF50" if p >= 0 else "#F44336"
              for p in df["profit_assureur_eur"]]
    ax.bar(df["annee"], df["profit_assureur_eur"] / 1_000,
           color=colors, alpha=0.85, edgecolor="white")
    ax.axhline(0, color="black", lw=1)
    moy = df["profit_assureur_eur"].mean()
    ax.axhline(moy / 1_000, color="blue", ls="--", lw=2,
               label=f"Profit moyen : {moy/1000:.0f} k€/an")

    # Annotations années déficitaires
    for _, row in df[df["profit_assureur_eur"] < 0].iterrows():
        ax.annotate("⚠",
                    xy=(row["annee"], row["profit_assureur_eur"] / 1_000 - 2),
                    ha="center", fontsize=11, color="#F44336")

    ax.set_xlabel("Année")
    ax.set_ylabel("Profit assureur (k€)")
    ax.set_title(f"Profit annuel de l'assureur\n"
                 f"Portefeuille de {N_ASSURES} assurés sur {N_ANNEES} ans")
    ax.legend(fontsize=9)

    fig.tight_layout()
    return _save(fig, "05_profit_annuel_assureur.png")


# ═══════════════════════════════════════════════════════════════════════════════
# 06 — Taux de sinistralité annuel
# ═══════════════════════════════════════════════════════════════════════════════

def plot_loss_ratio(df, climate: ClimateData) -> Path:
    _apply_style()
    fig, ax = plt.subplots(figsize=(10, 5))

    p_th     = climate.p_drought_th
    sigma_bi = np.sqrt(p_th * (1 - p_th) / N_ASSURES)

    ax.plot(df["annee"], df["taux_sinistralite"] * 100,
            "o-", color="#FF9800", lw=2, ms=7,
            markerfacecolor="white", markeredgewidth=2,
            label="Taux sinistralité observé")
    ax.axhline(p_th * 100, color="red", ls="--", lw=2,
               label=f"Taux théorique : {p_th*100:.1f}%")
    ax.fill_between(df["annee"],
                    (p_th - 2 * sigma_bi) * 100,
                    (p_th + 2 * sigma_bi) * 100,
                    alpha=0.20, color="red",
                    label="±2σ (loi binomiale)")

    ax.set_xlabel("Année")
    ax.set_ylabel("Taux de sinistralité (%)")
    ax.set_title("Taux de sinistralité annuel\n"
                 f"Loi binomiale B({N_ASSURES}, {p_th:.3f})")
    ax.legend(fontsize=9)

    fig.tight_layout()
    return _save(fig, "06_taux_sinistralite.png")


# ═══════════════════════════════════════════════════════════════════════════════
# 07 — Gain net de l'assuré
# ═══════════════════════════════════════════════════════════════════════════════

def plot_insured_gain(ig: InsuredGain) -> Path:
    _apply_style()
    fig, ax = plt.subplots(figsize=(9, 5))

    ax.hist(ig.gains, bins=70, color="#00BCD4",
            alpha=0.75, edgecolor="none")

    ymax = ax.get_ylim()[1]
    ax.fill_betweenx([0, ymax], float(ig.gains.min()), 0,
                     alpha=0.12, color="red", label="Zone de perte nette")
    ax.fill_betweenx([0, ymax], 0, float(ig.gains.max()),
                     alpha=0.08, color="green", label="Zone de gain net")
    ax.axvline(ig.E_gain, color="red", ls="--", lw=2,
               label=f"Moyenne : {ig.E_gain:.0f} €")
    ax.axvline(ig.median_gain, color="orange", ls=":", lw=2,
               label=f"Médiane : {ig.median_gain:.0f} €")
    ax.axvline(0, color="black", lw=1.5, label="Seuil de rentabilité")

    ax.set_xlabel(f"Gain net de l'assuré sur {N_ANNEES} ans (€)")
    ax.set_ylabel("Fréquence")
    ax.set_title(f"Distribution du gain net de l'assuré\n"
                 f"{N_ANNEES} ans  —  "
                 f"{ig.p_positive*100:.1f}% d'assurés avec gain positif  —  "
                 f"Coût loading = {ig.cout_loading:.0f} €/an")
    ax.legend(fontsize=9)

    fig.tight_layout()
    return _save(fig, "07_gain_net_assure.png")


# ═══════════════════════════════════════════════════════════════════════════════
# 08 — Stress test climatique
# ═══════════════════════════════════════════════════════════════════════════════

def plot_stress_test(stress_results: list[StressResult],
                     metrics: ActuarialMetrics) -> Path:
    _apply_style()
    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(13, 5))

    labels     = [r.label      for r in stress_results]
    primes_req = [r.prime_req  for r in stress_results]
    probs      = [r.p_drought * 100 for r in stress_results]
    profits    = [r.profit_port / 1_000 for r in stress_results]
    x          = np.arange(len(labels))

    # — Gauche : prime requise + P(sécheresse) —
    ax2 = ax_left.twinx()
    bars = ax_left.bar(x, primes_req, width=0.5,
                       color="#FF7043", alpha=0.80, label="Prime requise (€)")
    ax_left.axhline(metrics.prime_commerciale, color="blue",
                    ls=":", lw=1.5,
                    label=f"Prime actuelle = {metrics.prime_commerciale:.0f} €")
    ax2.plot(x, probs, "b-o", lw=2, ms=8,
             markerfacecolor="white", markeredgewidth=2,
             label="P(sécheresse) %")
    ax_left.set_xticks(x)
    ax_left.set_xticklabels(labels)
    ax_left.set_ylabel("Prime requise (€)", color="#FF7043")
    ax2.set_ylabel("P(sécheresse) %", color="blue")
    ax_left.set_title("Prime requise & probabilité\nde sécheresse par scénario")
    h1, l1 = ax_left.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax_left.legend(h1 + h2, l1 + l2, fontsize=8, loc="upper left")

    # — Droite : profit du portefeuille —
    colors_p = ["#4CAF50" if p >= 0 else "#F44336" for p in profits]
    ax_right.bar(x, profits, width=0.5, color=colors_p, alpha=0.85, edgecolor="white")
    ax_right.axhline(0, color="black", lw=1.2)
    ax_right.set_xticks(x)
    ax_right.set_xticklabels(labels)
    ax_right.set_ylabel("Profit portefeuille (k€)")
    ax_right.set_title(f"Impact sur le profit assureur\n"
                       f"({N_ASSURES} assurés, prime fixe = {metrics.prime_commerciale:.0f} €)")
    for xi, p in zip(x, profits):
        ax_right.text(xi, p + (1 if p >= 0 else -3),
                      f"{p:.0f}k", ha="center", fontsize=9, fontweight="bold")

    fig.suptitle("Stress Test Climatique — Assurance Paramétrique",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _save(fig, "08_stress_test.png")


# ═══════════════════════════════════════════════════════════════════════════════
# 09 — Comparaison paramétrique vs assurance traditionnelle
# ═══════════════════════════════════════════════════════════════════════════════

def plot_comparison(metrics: ActuarialMetrics) -> Path:
    _apply_style()
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # — Gauche : radar normalisé —
    criteres = ["Coût\nadmin.", "Délai\nrègl.", "Risque\nmoral",
                "Basis\nrisk", "Transpa-\nrence", "Accessibi-\nlité"]

    # Scores bruts (direction : plus grand = meilleur)
    score_param = [8.3, 10.0, 9.0, 4.0, 10.0, 5.0]
    score_trad  = [2.0,  1.5, 2.5, 9.5,  3.0, 8.5]

    x = np.arange(len(criteres))
    w = 0.35
    ax = axes[0]
    ax.bar(x - w/2, score_param, w, label="Paramétrique blockchain",
           color="#4CAF50", alpha=0.82)
    ax.bar(x + w/2, score_trad,  w, label="Traditionnelle",
           color="#9E9E9E", alpha=0.82)
    ax.set_xticks(x)
    ax.set_xticklabels(criteres, fontsize=9)
    ax.set_ylim(0, 12)
    ax.set_ylabel("Score (0 = pire  /  10 = meilleur)")
    ax.set_title("Comparaison multi-critères\n(scores normalisés)")
    ax.legend(fontsize=9)

    # Annotations valeurs réelles
    raw_param = ["~5%",  "<1 min", "Nul",   "Présent", "Code public", "Wallet"]
    raw_trad  = ["~30%", "30-90 j", "Élevé", "Nul",    "Opaque",     "Papier"]
    for xi, (vp, vt) in enumerate(zip(raw_param, raw_trad)):
        ax.text(xi - w/2, score_param[xi] + 0.3, vp,
                ha="center", fontsize=7, color="#2E7D32")
        ax.text(xi + w/2, score_trad[xi]  + 0.3, vt,
                ha="center", fontsize=7, color="#424242")

    # — Droite : tableau synthétique —
    ax2 = axes[1]
    ax2.axis("off")
    data = [
        ["Critère",              "Paramétrique",       "Traditionnelle"],
        ["Déclenchement",        "Automatique (<1 min)", "Expertise (30-90 j)"],
        ["Coût admin.",          "~5-10% prime",       "~30-40% prime"],
        ["Risque moral",         "Éliminé",            "Élevé"],
        ["Basis risk",           "Présent",            "Nul"],
        ["Transparence",         "Code public",        "Contrat privé"],
        ["Couverture légale",    "⚠ Limitée",         "✓ Complète"],
        ["Prime commerciale",    f"{metrics.prime_commerciale:.0f} €/an",
                                 f"{metrics.prime_commerciale*1.4:.0f} €/an"],
        ["Payout",               "Fixe (5 000 €)",     "Perte réelle"],
    ]
    tbl = ax2.table(cellText=data[1:], colLabels=data[0],
                    cellLoc="center", loc="center",
                    bbox=[0, 0, 1, 1])
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    for (r, c), cell in tbl.get_celld().items():
        if r == 0:
            cell.set_facecolor("#1565C0")
            cell.set_text_props(color="white", fontweight="bold")
        elif r % 2 == 0:
            cell.set_facecolor("#E3F2FD")
        cell.set_edgecolor("#BDBDBD")
    ax2.set_title("Synthèse comparative", pad=12, fontweight="bold")

    fig.suptitle("Assurance Paramétrique vs Assurance Traditionnelle",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _save(fig, "09_comparaison_param_vs_trad.png")


# ═══════════════════════════════════════════════════════════════════════════════
# 10 — Basis Risk : scatter station vs parcelle
# ═══════════════════════════════════════════════════════════════════════════════

def plot_basis_risk_scatter(br: BasisRiskData) -> Path:
    _apply_style()
    fig, ax = plt.subplots(figsize=(7, 6))

    idx = np.random.default_rng(0).choice(br.n_total, 4_000, replace=False)
    sc = ax.scatter(
        br.precip_station[idx], br.precip_parcelle[idx],
        c=br.basis_risk[idx],
        cmap="RdYlGn_r", alpha=0.45, s=12,
        vmin=-PAYOUT * 0.5, vmax=PAYOUT * 1.2,
    )
    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_label("Basis risk (€)  [positif = sous-assuré]", fontsize=9)

    ax.axvline(TRIGGER, color="red",  ls="--", lw=1.5,
               label=f"Trigger station ({TRIGGER} mm)")
    ax.axhline(TRIGGER, color="blue", ls="--", lw=1.5,
               label=f"Trigger parcelle ({TRIGGER} mm)")

    # Quadrants
    ax.text(50,  1700, "Sous-assuré\n(perte, pas de payout)",
            color="red",   fontsize=8, alpha=0.8)
    ax.text(600, 100,  "Sur-indemnisé\n(payout, pas de perte)",
            color="blue",  fontsize=8, alpha=0.8)
    ax.text(600, 1700, "Alignement\npayout ↔ perte",
            color="green", fontsize=8, alpha=0.8)

    ax.set_xlim(0, 1_600)
    ax.set_ylim(0, 1_900)
    ax.set_xlabel("Précipitations station météo / Oracle (mm)")
    ax.set_ylabel("Précipitations parcelle réelle (mm)")
    ax.set_title(f"Basis Risk — Station vs Parcelle\n"
                 f"ρ = {br.rho_cible}  |  σ(BR) = {br.std_basis_risk:.0f} €")
    ax.legend(fontsize=9)

    fig.tight_layout()
    return _save(fig, "10_basis_risk_scatter.png")


# ═══════════════════════════════════════════════════════════════════════════════
# 11 — Basis Risk : distribution
# ═══════════════════════════════════════════════════════════════════════════════

def plot_basis_risk_distribution(br: BasisRiskData) -> Path:
    _apply_style()
    fig, ax = plt.subplots(figsize=(9, 5))

    br_nonzero = br.basis_risk[br.basis_risk != 0]
    ax.hist(br_nonzero, bins=70, color="#FF7043",
            alpha=0.75, edgecolor="none", density=True)
    ax.axvline(br.E_basis_risk, color="red", ls="--", lw=2,
               label=f"Moyenne : {br.E_basis_risk:.0f} €")
    ax.axvline(0, color="black", lw=1.5, label="Alignement parfait")

    ax.fill_between(
        np.linspace(ax.get_xlim()[0], 0, 10),
        0, 0.0001,   # juste pour la légende
        alpha=0, color="white",
    )

    # Annotations
    ax.text(0.02, 0.95,
            f"Sous-assurés : {br.n_sous_assures/br.n_total*100:.1f}%\n"
            f"Sur-indemnisés : {br.n_sur_indemnises/br.n_total*100:.1f}%\n"
            f"σ(BR) = {br.std_basis_risk:.0f} €",
            transform=ax.transAxes, fontsize=9, va="top",
            bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.85))

    ax.set_xlabel("Basis risk (€)  =  Perte réelle − Payout reçu")
    ax.set_ylabel("Densité")
    ax.set_title("Distribution du basis risk\n"
                 "(événements avec perte ou payout actifs)")
    ax.legend(fontsize=9)

    fig.tight_layout()
    return _save(fig, "11_basis_risk_distribution.png")


# ═══════════════════════════════════════════════════════════════════════════════
# 12 — Basis Risk : sensibilité à ρ
# ═══════════════════════════════════════════════════════════════════════════════

def plot_basis_risk_sensitivity(br: BasisRiskData) -> Path:
    _apply_style()
    fig, ax = plt.subplots(figsize=(9, 5))
    ax2 = ax.twinx()

    ax.plot(br.rhos_sens, br.std_br_sens, "r-o",
            ms=5, lw=2, label="σ(basis risk) €")
    ax2.plot(br.rhos_sens, br.pct_sous_sens, "b--s",
             ms=5, lw=2, label="% cas sous-assurés")
    ax.axvline(br.rho_cible, color="green", ls=":", lw=2,
               label=f"ρ modèle = {br.rho_cible}")

    ax.set_xlabel("Corrélation spatiale ρ (station ↔ parcelle)")
    ax.set_ylabel("σ(basis risk) €", color="red")
    ax2.set_ylabel("% cas sous-assurés", color="blue")
    ax.set_title("Sensibilité du basis risk à la corrélation spatiale ρ\n"
                 "Plus ρ est faible → plus le basis risk est élevé")

    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=9, loc="upper right")

    fig.tight_layout()
    return _save(fig, "12_basis_risk_sensibilite.png")
