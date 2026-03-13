# Smart Contracts & Assurance Paramétrique Agricole

**ECE Paris · ING4 Finance et Ingénierie Quantitative · Groupe 3**

Rania WAHBI · Antoine SERAC · Louis JEAATE · Professeur Yann FORNIER · 2025-2026

---

## Présentation

Ce projet modélise une **assurance paramétrique agricole contre la sécheresse** déployée sous forme de smart contract Ethereum/Polygon. Dès que les précipitations annuelles passent sous **400 mm**, le contrat verse automatiquement **5 000 €** à l'assuré — sans intervention humaine, sans expertise, en moins d'une minute.

Le travail couvre l'intégralité de la chaîne :

- Modélisation actuarielle du risque climatique (loi lognormale, calibration, test KS)
- Simulation financière Monte Carlo (N = 100 000, VaR, CVaR, stress test GIEC)
- Analyse du risque moral et comparaison avec l'assurance traditionnelle
- Fiabilité des oracles Chainlink et vecteurs d'attaque
- Rentabilité assureur & assuré sur 20 ans

---

## Résultats clés

| Indicateur | Valeur |
|---|---|
| P(sécheresse déclencheuse) | **15,2 %** (≈ 1 fois / 6-7 ans) |
| Prime pure | 760 €/an |
| Prime commerciale (LR = 80 %) | **950 €/an** |
| Profit assureur moyen | ~100 k€/an (N = 500 assurés) |
| P(déficit annuel) | **0,89 %** |
| CVaR 99 % | 9 k€ |
| σ(basis risk) | 1 870 € |

---

## Structure

```
├── latex/
│   ├── presentation.tex       # Source Beamer (30+ slides)
│   ├── presentation.pdf       # PDF compilé
│   ├── figures/               # 12 graphiques (PNG)
│   └── compile.sh             # Compilation locale
│
├── simulation/
│   ├── main.py                # Point d'entrée
│   └── src/
│       ├── config.py          # Paramètres du modèle
│       ├── climate.py         # Génération scénarios climatiques
│       ├── actuarial.py       # Prime, IC, test KS, VaR
│       ├── portfolio.py       # Rentabilité, stress test
│       ├── basis_risk.py      # Modèle bivarié, σ(BR)
│       └── plots.py           # 12 figures
│
└── smart_contract/
    └── AgricultureInsurance.sol   # Contrat Solidity (Ethereum/Polygon)
```

> Les résultats générés (`simulation/results/`) ne sont pas versionnés — relancer `python main.py` pour les reproduire.

---

## Lancer la simulation

```bash
cd simulation
pip install numpy scipy matplotlib pandas
python main.py
# → génère simulation/results/figures/ (12 PNG) + simulation/results/data/resultats_annuels.csv
```

## Compiler la présentation

```bash
cd latex
bash compile.sh        # nécessite latexmk + pdflatex
```

Le PDF compilé est disponible directement : [`latex/presentation.pdf`](latex/presentation.pdf).

Pour **Overleaf** : créer un projet, uploader `presentation.tex` + le dossier `figures/`.

---

## Livrables

| # | Livrable | Fichier(s) |
|---|---|---|
| L1 | Modélisation actuarielle (lognormale, calibration, MC) | `src/actuarial.py`, `src/climate.py` |
| L2 | Simulation financière (VaR, CVaR, stress test) | `src/portfolio.py` |
| L3 | Analyse du risque moral | Slides 14–15, `presentation.tex` |
| L4 | Fiabilité des oracles Chainlink | Slide 16, `AgricultureInsurance.sol` |
| L5 | Rentabilité assureur & assuré | `src/portfolio.py`, slides 10–13 |
