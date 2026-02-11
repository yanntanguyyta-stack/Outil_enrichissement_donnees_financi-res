# 🔧 Guide de Dépannage - Enrichissement RNE

## ❌ Erreur 502 (Bad Gateway)

### Cause

L'erreur **502** survient lorsque l'application essaie de télécharger le **ZIP complet de 3.5 GB** depuis le FTP INPI pour chaque fichier RNE nécessaire, ce qui cause un **timeout**.

```
⬇️  FTP: stock_000075.json (cela prend ~5-10 secondes)...
→ En réalité: télécharge 3.5 GB (30-60s)
→ Streamlit/navigateur timeout
→ Erreur 502
```

### Solution Immédiate

**Option 1 : Utiliser le cache (recommandé)**

Extrayez les fichiers localement une seule fois :

```bash
# 1. Télécharger le ZIP (si pas déjà fait)
cd /workspaces/TestsMCP
wget ftp://rneinpiro:vv8_rQ5f4M_2-E@www.inpi.net/stock_RNE_comptes_annuels_20250926_1000_v2.zip

# 2. Extraire pour des SIRENs spécifiques
python3 extract_rne_files.py --sirens 552100554 005880596 775665019

# Ou extraire tout (1380 fichiers, ~2-3 GB)
python3 extract_rne_files.py --all
```

Une fois extrait, le cache sera utilisé (< 1s par entreprise).

**Option 2 : Réduire la taille des lots**

Dans `enrichment_hybrid.py`, réduire le nombre de workers :

```python
MAX_CONCURRENT_FILES = 1  # Au lieu de 3
```

**Option 3 : Désactiver l'enrichissement RNE temporairement**

Dans la sidebar de l'application, décocher "📊 Activer enrichissement FTP/RNE".

---

## ⏱️ Timeouts et Performances

### Problème : "FTP timeout" ou "Connection reset"

**Causes possibles** :
- Serveur FTP INPI temporairement indisponible
- Connexion réseau instable
- Timeout trop court

**Solutions** :

1. **Augmenter le timeout** dans `enrichment_hybrid.py` :
```python
FTP_TIMEOUT = 120  # Au lieu de 60
```

2. **Vérifier la connexion** :
```bash
# Tester la connexion FTP
curl -v ftp://rneinpiro:vv8_rQ5f4M_2-E@www.inpi.net/
```

3. **Utiliser le retry automatique** (déjà implémenté) :
```python
FTP_MAX_RETRIES = 3  # Nombre de tentatives
```

---

## 💾 Problèmes de Cache

### Le cache ne se remplit pas

**Diagnostic** :
```bash
ls -lh /workspaces/TestsMCP/rne_cache/
```

Si vide, vérifier :

1. **Permissions** :
```bash
chmod 755 /workspaces/TestsMCP/rne_cache/
```

2. **Espace disque** :
```bash
df -h /workspaces
```

Si < 10% libre, nettoyer :
```bash
# Supprimer les logs
rm -f /workspaces/TestsMCP/*.log

# Supprimer l'ancien cache
rm -rf /workspaces/TestsMCP/rne_cache/*.json
```

### Le cache est corrompu

**Symptômes** :
- Erreurs JSON lors de la lecture
- "ValueError: Invalid JSON"

**Solution** :
```bash
# Supprimer et regénérer
rm -rf /workspaces/TestsMCP/rne_cache/
python3 extract_rne_files.py --files [fichiers_problématiques]
```

---

## 🚫 Erreurs FTP spécifiques

### "Login authentication failed"

**Cause** : Identifiants FTP incorrects ou expirés

**Solution** :

Vérifier les credentials dans `enrichment_hybrid.py` :
```python
FTP_USER = "rneinpiro"
FTP_PASSWORD = "vv8_rQ5f4M_2-E"
```

Tester manuellement :
```bash
ftp www.inpi.net
# Entrer: rneinpiro
# Mot de passe: vv8_rQ5f4M_2-E
```

### "550 File not found"

**Cause** : Le fichier demandé n'existe pas dans le ZIP

**Diagnostic** :
```bash
# Lister le contenu du ZIP
unzip -l stock_comptes_annuels.zip | grep stock_
```

**Solution** :
- Vérifier que le SIREN est dans les limites RNE
- Utiliser `test_hybrid_approach.py` pour tester

---

## 🔍 Erreurs de Recherche SIREN

### "SIREN hors limites RNE"

**Cause** : Le SIREN cherché n'est pas dans l'index

**Explication** :

L'index RNE couvre 1,5M entreprises, mais pas toutes. Certains cas :
- Entreprises trop récentes
- Entreprises sans bilans publiés
- SIRENs invalides

**Diagnostic** :
```python
from enrichment_hybrid import find_file_for_siren, load_ranges_index

index_data = load_ranges_index()
ranges = index_data['ranges']

siren = "123456789"
filename = find_file_for_siren(siren, ranges)
print(f"Fichier: {filename}")  # None si hors limites
```

**Solution** :

Utiliser uniquement l'API DINUM (désactiver RNE) pour ces entreprises.

---

## 🐛 Erreurs d'Extraction

### "MemoryError" lors de l'extraction

**Cause** : Pas assez de RAM pour charger le ZIP de 3.5 GB

**Solution directe** :

Extraire fichier par fichier depuis le terminal :

```bash
# Lister les fichiers dans le ZIP
unzip -l stock_comptes_annuels.zip | head -20

# Extraire un fichier spécifique
unzip -j stock_comptes_annuels.zip "stock_000498.json" -d rne_cache/
```

**Solution alternative** :

Utiliser `extract_rne_files.py` qui gère mieux la mémoire :
```bash
python3 extract_rne_files.py --files stock_000498.json stock_000534.json
```

---

## ⚡ Optimisations

### Pour usage intensif (100+ entreprises)

**1. Pré-extraction complète (recommandé)**

```bash
# Extraire tous les fichiers une fois
python3 extract_rne_files.py --all

# Résultat: ~2-3 GB de cache, mais accès < 1s
```

**Avantages** :
- ✅ Pas de timeout
- ✅ Traitement parallèle efficace
- ✅ Pas de téléchargements répétés

**Inconvénients** :
- ❌ Utilise 2-3 GB d'espace disque

**2. Extraction à la demande**

Pour économiser l'espace, extraire au fur et à mesure :

```python
# Dans votre code
sirens = ["552100554", "005880596", ...]  # Vos SIRENs

# Script d'extraction
import subprocess
subprocess.run([
    "python3", 
    "extract_rne_files.py", 
    "--sirens"
] + sirens)

# Puis utiliser l'enrichissement
results = enrich_batch_parallel(sirens)
```

### Pour espace disque limité

**Configuration dans `enrichment_hybrid.py`** :

```python
MAX_CONCURRENT_FILES = 1  # Au lieu de 3
# Cache max: 2.5 MB au lieu de 7.5 MB
```

**Nettoyage automatique renforcé** :

```python
# Après chaque recherche
import shutil
shutil.rmtree("/workspaces/TestsMCP/rne_cache")
```

---

## 📊 Diagnostic Avancé

### Vérifier l'état complet du système

```bash
#!/bin/bash

echo "=== DIAGNOSTIC ENRICHISSEMENT RNE ==="
echo ""

echo "1. Espace disque:"
df -h /workspaces | tail -1

echo ""
echo "2. Cache RNE:"
du -sh /workspaces/TestsMCP/rne_cache 2>/dev/null || echo "Pas de cache"
ls /workspaces/TestsMCP/rne_cache/*.json 2>/dev/null | wc -l | xargs echo "Fichiers:"

echo ""
echo "3. Index:"
ls -lh /workspaces/TestsMCP/rne_siren_ranges.json 2>/dev/null || echo "Index manquant!"

echo ""
echo "4. ZIP RNE:"
ls -lh /workspaces/TestsMCP/stock_comptes_annuels.zip 2>/dev/null || echo "ZIP non téléchargé"

echo ""
echo "5. Connexion FTP:"
timeout 5 curl -s ftp://rneinpiro:vv8_rQ5f4M_2-E@www.inpi.net/ >/dev/null 2>&1 && echo "✅ OK" || echo "❌ Échec"

echo ""
echo "6. Python modules:"
python3 -c "from enrichment_hybrid import *; print('✅ Module chargé')" 2>&1

echo ""
echo "=== FIN DIAGNOSTIC ==="
```

Sauvegarder dans `diagnostic_rne.sh` et exécuter :
```bash
chmod +x diagnostic_rne.sh
./diagnostic_rne.sh
```

---

## 🆘 Cas Spécifiques

### Erreur lors du traitement par lots (50+ entreprises)

**Symptôme** : L'application freeze ou crash

**Causes probables** :
1. Trop de téléchargements simultanés
2. Timeout Streamlit
3. Mémoire insuffisante

**Solutions** :

**Option A** : Réduire la taille des lots

Dans `app.py` :
```python
BATCH_THRESHOLD = 100  # Au lieu de 50
```

**Option B** : Désactiver le mode batch

```python
# Dans app.py, fonction process_companies()
use_batch_mode = False  # Forcer mode standard
```

**Option C** : Pré-extraire avant traitement

```bash
# 1. Identifier les SIRENs (via API DINUM)
# 2. Extraire les fichiers nécessaires
python3 extract_rne_files.py --sirens [liste]
# 3. Lancer le traitement (utilisera le cache)
```

---

## 📧 Support

Si le problème persiste :

1. **Vérifier les logs** :
```bash
tail -100 /workspaces/TestsMCP/streamlit.log
```

2. **Mode debug** :

Dans `enrichment_hybrid.py`, ajouter au début de `download_json_from_ftp()` :
```python
import traceback
try:
    # ... code existant
except Exception as e:
    traceback.print_exc()
    raise
```

3. **Créer un rapport** :
```bash
python3 diagnostic_rne.sh > diagnostic_$(date +%Y%m%d_%H%M%S).txt
```

Et partager le fichier généré.

---

## ✅ Checklist de Prévention

Avant d'utiliser l'enrichissement RNE intensivement :

- [ ] Index créé (`rne_siren_ranges.json` présent)
- [ ] ZIP téléchargé (`stock_comptes_annuels.zip` présent)
- [ ] Fichiers extraits dans `rne_cache/` (au moins les principaux)
- [ ] Connexion FTP testée
- [ ] Espace disque > 3 GB disponible
- [ ] Test avec 1-2 SIRENs d'abord

**Commande de préparation complète** :

```bash
# Setup complet (exécuter une fois)
cd /workspaces/TestsMCP

# 1. Télécharger ZIP (si absent)
[ ! -f stock_comptes_annuels.zip ] && \
  wget ftp://rneinpiro:vv8_rQ5f4M_2-E@www.inpi.net/stock_RNE_comptes_annuels_20250926_1000_v2.zip \
  -O stock_comptes_annuels.zip

# 2. Créer index (si absent)
[ ! -f rne_siren_ranges.json ] && \
  python3 create_rne_index_ranges.py

# 3. Extraire fichiers courants (100 premiers fichiers)
python3 extract_rne_files.py --files $(unzip -l stock_comptes_annuels.zip | grep "stock_0000" | awk '{print $4}' | head -100)

# 4. Tester
python3 -c "from enrichment_hybrid import enrich_from_api_dinum_and_rne; print(enrich_from_api_dinum_and_rne('552100554'))"

echo "✅ Setup terminé!"
```

---

## 🎯 Résumé des Erreurs

| Erreur | Cause | Solution Rapide |
|--------|-------|-----------------|
| **502** | Timeout FTP (3.5 GB) | Extraire localement avec `extract_rne_files.py` |
| **Timeout** | FTP lent | Augmenter `FTP_TIMEOUT` à 120s |
| **MemoryError** | ZIP trop gros | Extraire fichier par fichier |
| **File not found** | SIREN hors RNE | Vérifier avec `find_file_for_siren()` |
| **Login failed** | Credentials FTP | Vérifier user/password |
| **Cache corrompu** | JSON invalide | `rm -rf rne_cache/` et réextraire |
| **Disk full** | Plus d'espace | Nettoyer cache: `rm rne_cache/*.json` |

---

**En cas de doute, la solution la plus sûre reste l'extraction locale complète** :

```bash
python3 extract_rne_files.py --all
```

Cela évite 99% des erreurs liées au FTP et garantit des performances optimales.
