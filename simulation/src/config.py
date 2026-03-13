"""
config.py — Paramètres centralisés du modèle
=============================================
Toute modification du modèle passe ici.
"""

from pathlib import Path

# ─── Chemins ─────────────────────────────────────────────────────────────────
ROOT_DIR    = Path(__file__).resolve().parent.parent
FIGURES_DIR = ROOT_DIR / "results" / "figures"
DATA_DIR    = ROOT_DIR / "results" / "data"

# ─── Paramètres climatiques ───────────────────────────────────────────────────
# Distribution lognormale des précipitations annuelles (mm)
# Calibration : France méditerranéenne
#   exp(6.3) ≈ 545 mm/an  →  médiane observée
#   P(X < 400) = Φ((ln400 − 6.3)/0.3) = Φ(−1.03) ≈ 15.2%
MU_LOG    = 6.30   # paramètre μ de ln(X) ~ N(μ, σ²)
SIGMA_LOG = 0.30   # paramètre σ
TRIGGER   = 400    # seuil de déclenchement (mm/an)

# ─── Paramètres financiers ────────────────────────────────────────────────────
PAYOUT    = 5_000  # indemnisation fixe (€)
LOADING   = 0.25   # chargement commercial (25%)

# ─── Paramètres de simulation ─────────────────────────────────────────────────
N_SIMUL      = 100_000  # scénarios Monte Carlo (prime, convergence)
N_ANNEES     = 20       # horizon de projection (années)
N_ASSURES    = 500      # taille du portefeuille
N_SIM_ASSURE = 50_000   # simulations pour distribution gain assuré
N_PORT_SIM   = 100_000  # simulations pertes agrégées portefeuille
N_BASIS      = 50_000   # simulations basis risk
RANDOM_SEED  = 42       # graine pour reproductibilité

# ─── Paramètres basis risk ────────────────────────────────────────────────────
RHO_BASIS = 0.75   # corrélation spatiale station météo / parcelle (espace log)

# ─── Style matplotlib ─────────────────────────────────────────────────────────
MPL_STYLE = {
    "font.family"      : "DejaVu Sans",
    "font.size"        : 11,
    "axes.titlesize"   : 13,
    "axes.labelsize"   : 11,
    "figure.facecolor" : "white",
    "axes.facecolor"   : "#F8F9FA",
    "axes.grid"        : True,
    "grid.alpha"       : 0.4,
    "axes.spines.top"  : False,
    "axes.spines.right": False,
}
