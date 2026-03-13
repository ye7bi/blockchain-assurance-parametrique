#!/usr/bin/env bash
# ============================================================
# compile.sh — Compilation du Beamer en PDF
# Usage : bash compile.sh
# ============================================================

set -e
cd "$(dirname "$0")"

echo "=== Compilation Beamer — Assurance Paramétrique ==="

# latexmk gère automatiquement les passes (TOC, refs, etc.)
latexmk -pdf \
        -interaction=nonstopmode \
        -file-line-error \
        presentation.tex

echo ""
echo "✅ PDF généré : $(pwd)/presentation.pdf"
echo "   Ouverture..."
xdg-open presentation.pdf 2>/dev/null &
