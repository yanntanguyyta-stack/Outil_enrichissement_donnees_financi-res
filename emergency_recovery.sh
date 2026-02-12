#!/bin/bash
set -e

echo "🚨 RÉCUPÉRATION D'URGENCE"
echo "========================"

# 1. Arrêter TOUS les processus
echo "1. Arrêt des processus..."
pkill -9 -f extract 2>/dev/null || true
pkill -9 -f convert 2>/dev/null || true
pkill -9 -f streamlit 2>/dev/null || true
sleep 2

# 2. Nettoyer le cache
echo "2. Nettoyage du cache..."
cd /workspaces/TestsMCP/rne_cache
rm -f stock_0003*.json stock_0004*.json stock_0005*.json stock_0006*.json stock_0007*.json 2>/dev/null || true

# 3. Compter les fichiers
FICHIERS=$(ls stock_*.json 2>/dev/null | wc -l)
echo "3. Fichiers restants: $FICHIERS"

# 4. Espace disque
echo "4. Espace disque:"
df -h /workspaces | grep /workspaces

# 5. Relancer Streamlit
echo "5. Relancement de Streamlit..."
cd /workspaces/TestsMCP
nohup streamlit run app.py --server.headless=true --server.port=8501 > streamlit.log 2>&1 &
STREAMLIT_PID=$!
echo $STREAMLIT_PID > streamlit.pid
sleep 3

# 6. Vérifier Streamlit
if ps -p $STREAMLIT_PID > /dev/null; then
    echo "✅ Streamlit actif (PID: $STREAMLIT_PID)"
    echo "🌐 http://localhost:8501"
else
    echo "❌ Erreur: Streamlit n'a pas démarré"
fi

echo ""
echo "========================"
echo "✅ RÉCUPÉRATION TERMINÉE"
echo "========================"
