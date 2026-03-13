# Smart Contracts & Assurance Paramétrique Agricole

**ECE Paris — ING4 FIQ Groupe 3**
Rania WAHBI · Antoine SERAC · Louis JEAATE
Enseignant : Yann FORNIER

---

## Structure du projet

```
├── latex/
│   ├── presentation.tex   # Source LaTeX (Beamer)
│   ├── presentation.pdf   # Présentation compilée
│   ├── figures/           # Graphiques générés par la simulation
│   └── compile.sh         # Script de compilation
│
├── simulation/
│   ├── main.py            # Point d'entrée
│   ├── src/               # Modules (actuarial, climate, portfolio, basis_risk, plots)
│   └── results/           # Figures PNG + CSV générés
│
└── smart_contract/
    └── AgricultureInsurance.sol   # Contrat Solidity
```

## Lancer la simulation

```bash
cd simulation
python main.py
```

Les résultats (12 figures + CSV) sont générés dans `simulation/results/`.
