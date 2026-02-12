#!/bin/bash
# Diagnostic final du système

echo "════════════════════════════════════════════════════════════════"
echo "✅ RÉSUMÉ - ENRICHISSEMENT RNE"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Cache
FICHIERS=$(ls /workspaces/TestsMCP/rne_cache/stock_*.json 2>/dev/null | wc -l)
TAILLE=$(du -sh /workspaces/TestsMCP/rne_cache 2>/dev/null | cut -f1)
echo "📁 Cache RNE: $FICHIERS fichiers ($TAILLE)"

# Disque
DISQUE=$(df -h /workspaces | tail -1 | awk '{print $3"/"$2" ("$5")"}')
echo "💾 Espace disque: $DISQUE"

# Streamlit
if pgrep -f "streamlit run" > /dev/null; then
    echo "🚀 Streamlit: ✅ Actif (http://localhost:8501)"
else
    echo "🚀 Streamlit: ❌ Arrêté"
fi

echo ""
echo "🆕 NOUVEAU : Mode 'RNE seul' disponible !"
echo "   → Sidebar > Enrichissement RNE > Mode: 'RNE seul'"
echo "   → Idéal si vous avez déjà des SIRETs validés"
echo "   → Plus rapide (pas de recherche Pappers)"
echo ""
echo "════════════════════════════════════════════════════════════════"
