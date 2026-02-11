#!/bin/bash
# Script de diagnostic pour l'enrichissement RNE

echo "================================================================================"
echo "🔍 DIAGNOSTIC ENRICHISSEMENT RNE"
echo "================================================================================"
echo ""

# 1. Espace disque
echo "📁 1. ESPACE DISQUE"
echo "--------------------------------------------------------------------------------"
df -h /workspaces | tail -1
DISK_USAGE=$(df /workspaces | tail -1 | awk '{print $5}' | tr -d '%')
if [ $DISK_USAGE -gt 90 ]; then
    echo "⚠️  ATTENTION: Disque presque plein ($DISK_USAGE% utilisé)"
    echo "   → Nettoyer avec: rm -rf rne_cache/*.json"
else
    echo "✅ Espace disque OK ($DISK_USAGE% utilisé)"
fi
echo ""

# 2. Cache RNE
echo "💾 2. CACHE RNE"
echo "--------------------------------------------------------------------------------"
if [ -d "/workspaces/TestsMCP/rne_cache" ]; then
    CACHE_SIZE=$(du -sh /workspaces/TestsMCP/rne_cache 2>/dev/null | cut -f1)
    CACHE_FILES=$(ls /workspaces/TestsMCP/rne_cache/*.json 2>/dev/null | wc -l)
    echo "📦 Taille cache: $CACHE_SIZE"
    echo "📄 Fichiers en cache: $CACHE_FILES"
    
    if [ $CACHE_FILES -gt 0 ]; then
        echo "✅ Cache disponible (accès rapide)"
    else
        echo "⚠️  Cache vide (premier accès sera lent)"
        echo "   → Recommandation: python3 extract_rne_files.py --all"
    fi
else
    echo "⚠️  Répertoire cache absent"
    mkdir -p /workspaces/TestsMCP/rne_cache
    echo "✅ Créé: /workspaces/TestsMCP/rne_cache"
fi
echo ""

# 3. Index RNE
echo "📋 3. INDEX RNE"
echo "--------------------------------------------------------------------------------"
if [ -f "/workspaces/TestsMCP/rne_siren_ranges.json" ]; then
    INDEX_SIZE=$(ls -lh /workspaces/TestsMCP/rne_siren_ranges.json | awk '{print $5}')
    echo "✅ Index présent ($INDEX_SIZE)"
else
    echo "❌ Index manquant!"
    echo "   → Créer avec: python3 create_rne_index_ranges.py"
fi
echo ""

# 4. ZIP RNE
echo "📦 4. ZIP RNE"
echo "--------------------------------------------------------------------------------"
if [ -f "/workspaces/TestsMCP/stock_comptes_annuels.zip" ]; then
    ZIP_SIZE=$(ls -lh /workspaces/TestsMCP/stock_comptes_annuels.zip | awk '{print $5}')
    echo "✅ ZIP présent ($ZIP_SIZE)"
else
    echo "⚠️  ZIP non téléchargé"
    echo "   → Télécharger avec:"
    echo "   wget ftp://rneinpiro:vv8_rQ5f4M_2-E@www.inpi.net/stock_RNE_comptes_annuels_20250926_1000_v2.zip"
fi
echo ""

# 5. Connexion FTP
echo "🌐 5. CONNEXION FTP INPI"
echo "--------------------------------------------------------------------------------"
timeout 10 curl -s ftp://rneinpiro:vv8_rQ5f4M_2-E@www.inpi.net/ >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Connexion FTP OK"
else
    echo "❌ Connexion FTP échec (timeout ou serveur indisponible)"
    echo "   → Vérifier la connexion réseau"
    echo "   → Le serveur INPI peut être temporairement indisponible"
fi
echo ""

# 6. Modules Python
echo "🐍 6. MODULES PYTHON"
echo "--------------------------------------------------------------------------------"
cd /workspaces/TestsMCP
python3 -c "from enrichment_hybrid import *" 2>&1 | grep -q "ImportError"
if [ $? -eq 1 ]; then
    echo "✅ Module enrichment_hybrid chargé"
else
    echo "❌ Erreur import enrichment_hybrid"
    echo "   → Vérifier: python3 -c 'from enrichment_hybrid import *'"
fi

python3 -c "import streamlit" 2>&1 | grep -q "ImportError"
if [ $? -eq 1 ]; then
    echo "✅ Streamlit installé"
else
    echo "❌ Streamlit manquant"
    echo "   → Installer avec: pip install streamlit"
fi
echo ""

# 7. Test rapide
echo "🧪 7. TEST FONCTIONNEL"
echo "--------------------------------------------------------------------------------"
if [ -f "/workspaces/TestsMCP/rne_siren_ranges.json" ]; then
    echo "Test de recherche dans l'index..."
    TEST_OUTPUT=$(python3 -c "
from enrichment_hybrid import find_file_for_siren, load_ranges_index
index_data = load_ranges_index()
if index_data:
    ranges = index_data['ranges']
    filename = find_file_for_siren('552100554', ranges)
    print(f'Test SIREN 552100554 → {filename}')
else:
    print('❌ Erreur chargement index')
" 2>&1)
    
    if echo "$TEST_OUTPUT" | grep -q "stock_"; then
        echo "✅ $TEST_OUTPUT"
    else
        echo "❌ $TEST_OUTPUT"
    fi
else
    echo "⏭️  Index absent, test ignoré"
fi
echo ""

# 8. Logs récents
echo "📝 8. LOGS RÉCENTS"
echo "--------------------------------------------------------------------------------"
if [ -f "/workspaces/TestsMCP/streamlit.log" ]; then
    echo "Dernières erreurs dans streamlit.log:"
    grep -i "error\|exception\|traceback" /workspaces/TestsMCP/streamlit.log | tail -3
    if [ $? -ne 0 ]; then
        echo "✅ Aucune erreur récente"
    fi
else
    echo "ℹ️  Pas de log Streamlit"
fi
echo ""

# Résumé et recommandations
echo "================================================================================"
echo "📊 RÉSUMÉ & RECOMMANDATIONS"
echo "================================================================================"

ISSUES=0

# Vérifications
if [ $DISK_USAGE -gt 90 ]; then
    echo "❌ Espace disque critique"
    ISSUES=$((ISSUES+1))
fi

if [ ! -f "/workspaces/TestsMCP/rne_siren_ranges.json" ]; then
    echo "❌ Index manquant → python3 create_rne_index_ranges.py"
    ISSUES=$((ISSUES+1))
fi

CACHE_FILES=$(ls /workspaces/TestsMCP/rne_cache/*.json 2>/dev/null | wc -l)
if [ $CACHE_FILES -eq 0 ]; then
    echo "⚠️  Cache vide → Premier accès sera lent (risque 502)"
    echo "   Recommandation: python3 extract_rne_files.py --all"
    ISSUES=$((ISSUES+1))
fi

if [ $ISSUES -eq 0 ]; then
    echo ""
    echo "✅ Système opérationnel!"
    echo ""
    echo "Pour tester:"
    echo "  streamlit run app.py"
else
    echo ""
    echo "⚠️  $ISSUES problème(s) détecté(s)"
    echo ""
    echo "Setup rapide recommandé:"
    echo "  1. python3 create_rne_index_ranges.py  # Si index manquant"
    echo "  2. python3 extract_rne_files.py --all  # Pour éviter erreurs 502"
    echo "  3. streamlit run app.py"
fi

echo ""
echo "Pour plus d'aide: cat TROUBLESHOOTING_RNE.md"
echo "================================================================================"
