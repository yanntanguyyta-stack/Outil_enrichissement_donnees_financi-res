# 🏢 Recherche d'Entreprises Françaises - Application Modernisée

Application Streamlit modernisée pour rechercher et enrichir les données d'entreprises françaises avec l'API officielle de l'État et les données financières du RNE (INPI).

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-latest-red.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

---

## ✨ Nouveautés v2.0

### 🎨 Interface Modernisée
- ✅ Design avec **gradients et couleurs professionnelles**
- ✅ **Cards stylées** pour une meilleure organisation
- ✅ **Métriques visuelles** avec indicateurs temps réel
- ✅ **Double vue** : tableau complet ET cartes détaillées
- ✅ **Sidebar réorganisée** avec expanders et sections claires
- ✅ **CSS personnalisé** pour un look moderne

### 💾 Solution de Stockage RNE Optimisée
- ✅ **Index ultra-léger** : 213 KB au lieu de 27 GB ! **(Réduction 355x)**
- ✅ **Approche hybride** : API DINUM + Index ranges + FTP RNE à la demande
- ✅ **Cache intelligent** pour performances optimales
- ✅ **Stockage minimal** : ~50 KB + cache temporaire
- ✅ **3 solutions documentées** : Gratuite (FTP), VPS ($3-6/mois), S3 ($8-20/mois)

### 📦 Traitement par Lots Optimisé (Nouveau !)
- ✅ **Gestion automatique** des gros volumes (50+ entreprises)
- ✅ **Traitement parallèle** : 3 fichiers RNE simultanés
- ✅ **Nettoyage automatique** : pas de saturation disque
- ✅ **Gain de performance** : 66% plus rapide qu'en séquentiel
- ✅ **Économie d'espace** : maximum 7.5 MB de cache
- ✅ **Interface intuitive** : barres de progression en temps réel

---

## 🚀 Démarrage Rapide

### Option 1 : GitHub Codespaces (Recommandé)
```bash
# Le conteneur de développement configure tout automatiquement
streamlit run app.py
```

### Option 2 : Local
```bash
# Installer les dépendances
pip install -r requirements.txt

# Lancer l'application
streamlit run app.py
```

---

## 📊 Fonctionnalités

### 1. Recherche d'Entreprises
- 🔍 **Par nom** (recommandé) : "Total Energies", "Airbus", etc.
- 🔢 **Par SIREN** (9 chiffres) : "552100554"
- 📋 **Par SIRET** (14 chiffres) : "55210055400010"
- 📁 **Import fichier** : CSV ou Excel (1 ou 2 colonnes)

### 2. Données Enrichies

#### 🔍 Identification
- SIREN, SIRET, Nom complet, Sigle
- Vérification automatique

#### 🏢 Structure & État
- État administratif (Active/Cessée)
- Date de création
- Catégorie d'entreprise (GE, ETI, PME, etc.)
- Nature juridique
- Activité principale (code NAF)

#### 💰 Finances *(10-20% des entreprises publient)*
- Chiffre d'affaires
- Résultat net
- Année des finances
- Indicateur de publication

#### 📍 Localisation
- Adresse complète du siège
- Code postal, Commune, Département, Région
- Coordonnées GPS (latitude/longitude)

#### 👥 Organisation
- Effectifs salariés (tranche)
- Nombre d'établissements
- Liste des dirigeants et leurs fonctions
- Commissaires aux comptes

#### 🏆 Certifications & Labels
- Qualiopi, RGE, Bio, ESS
- Société à mission
- Service public
- Conventions collectives (IDCC)

### 3. Export des Données
- 📥 **CSV** : Format universel
- 📊 **Excel** : Format Microsoft (.xlsx)

---

## 💾 Enrichissement RNE (Données Financières)

### Architecture Optimisée

```
API DINUM (Gratuit)
    ↓ Recherche entreprise
Obtenir SIREN
    ↓ 
Index Ultra-Léger (213 KB)
    ↓ Recherche binaire O(log n)
FTP INPI (Gratuit)
    ↓ Télécharger 1 fichier (~2-3 MB)
Cache Local
    ↓ Réutilisation
Données Financières
```

### Avantages
- ✅ **213 KB** de stockage (vs 27 GB avant)
- ✅ **Gratuit** (pas de serveur externe)
- ✅ **Rapide** : <1s avec cache, ~5-10s sans
- ✅ **À jour** : Données directement depuis l'INPI
- ✅ **1,5M entreprises** indexées

### Utilisation

```python
from enrichment_hybrid import enrich_from_api_dinum_and_rne

# Enrichir une entreprise
data = enrich_from_api_dinum_and_rne("552100554")  # EDF

# Afficher
print(f"CA: {data['bilans'][0]['chiffre_affaires']} €")
```

### Configuration Initiale (Une Seule Fois)

```bash
# 1. Télécharger les données RNE (3,5 GB)
wget ftp://rneinpiro:vv8_rQ5f4M_2-E@www.inpi.net/stock_RNE_comptes_annuels_*.zip \
  -O stock_comptes_annuels.zip

# 2. Créer l'index léger (~20 minutes)
python3 create_rne_index_ranges.py

# 3. Tester
python3 test_hybrid_approach.py

# 4. Nettoyer (libère 3,5 GB)
rm stock_comptes_annuels.zip
```

**📖 Documentation complète :** Voir [README_RNE_OPTIMAL.md](README_RNE_OPTIMAL.md) et [COMPARAISON_SOLUTIONS_STOCKAGE.md](COMPARAISON_SOLUTIONS_STOCKAGE.md)

---

## 📦 Traitement par Lots (Gros Volumes)

### Pour Fichiers Volumineux (50+ entreprises)

Le système **active automatiquement** un mode optimisé qui :

1. **📊 Phase 1** : Récupère tous les SIRENs (API DINUM)
2. **📦 Phase 2** : Groupe par fichier RNE (tri intelligent)
3. **⚡ Phase 3** : Télécharge en parallèle (3 fichiers max)
4. **🗑️ Phase 4** : Nettoie automatiquement après chaque lot

### Performances

| Volume | Fichiers RNE | Temps séquentiel | Temps parallèle | Gain |
|--------|--------------|------------------|-----------------|------|
| 50 ent. | ~5 fichiers | ~35s | ~12s | 66% |
| 100 ent. | ~8 fichiers | ~56s | ~19s | 66% |
| 500 ent. | ~35 fichiers | ~245s | ~82s | 66% |

### Espace Disque

- **Mode standard** : 1 fichier à la fois (~2.5 MB)
- **Mode batch** : Max 3 fichiers (~7.5 MB)
- **Nettoyage** : Automatique après chaque lot

### Utilisation

```python
from enrichment_hybrid import enrich_batch_parallel

# Liste de SIRENs
sirens = ["552100554", "005880596", "775665019", ...]  # 100+ SIRENs

# Traitement par lots optimisé
results = enrich_batch_parallel(
    sirens,
    max_bilans=10,       # Nombre d'exercices par entreprise
    max_workers=3,       # Fichiers RNE en parallèle
    progress_callback=callback  # Optionnel
)
```

### Interface Streamlit

Lorsque vous uploadez un fichier CSV avec **50+ entreprises** :

1. ✅ Message : "🚀 **Mode d'optimisation activé** pour X entreprises"
2. ✅ Barre de progression Phase 1 (identification)
3. ✅ Barre de progression Phase 2-3 (enrichissement RNE)
4. ✅ Résumé final avec statistiques

**📖 Guide complet :** [GUIDE_TRAITEMENT_LOTS.md](GUIDE_TRAITEMENT_LOTS.md)

---

## 📁 Structure du Projet

```
TestsMCP/
├── app.py                          # 🎨 Application Streamlit modernisée
├── requirements.txt                # Dépendances Python
│
├── enrichment_hybrid.py            # 💾 Module RNE optimisé (recommandé)
├── enrichment_s3.py                # ☁️  Alternative avec AWS S3
├── enrichment_pappers.py           # 📊 Alternative avec API Pappers
│
├── create_rne_index_ranges.py     # 🔧 Créer l'index ultra-léger
├── test_hybrid_approach.py        # 🧪 Tester la solution RNE
├── test_batch_processing.py       # 🧪 Tester le traitement par lots
│
├── rne_siren_ranges.json          # 📋 Index léger (213 KB) ✅ À committer
├── rne_cache/                      # 💾 Cache temporaire (gitignore)
│
├── README_RNE_OPTIMAL.md           # 📖 Guide solution RNE
├── COMPARAISON_SOLUTIONS_STOCKAGE.md # 📊 Comparaison des solutions
├── GUIDE_STOCKAGE_RNE.md           # 📚 Guide détaillé
├── GUIDE_TRAITEMENT_LOTS.md        # 📦 Guide traitement par lots
└── GUIDE_PAPPERS.md                # 📚 Guide API Pappers
```

---

## ⚙️ Configuration Technique

### Rate Limiting
- **Délai** : 0,5s entre requêtes
- **Tentatives** : 3 maximum
- **API Limite** : ~250 req/min (respecté avec marge 50%)

### Cache RNE
- **Localisation** : `rne_cache/`
- **Taille** : 50-500 MB selon usage
- **Nettoyage** : `rm -rf rne_cache/` (fichiers re-téléchargés à la demande)

---

## ⚠️ Notes Importantes

### Données Financières
Seules **10-20%** des entreprises publient leurs comptes annuels :
- ✅ Grandes Entreprises (GE)
- ✅ ETI (Entreprises de Taille Intermédiaire)
- ✅ Sociétés cotées

Les PME < 50 salariés **ne sont pas obligées** de publier. Il est **normal** que 80% des résultats affichent "N/A" pour les finances.

### Authentification
**Aucune clé API n'est nécessaire** ! L'API Recherche d'Entreprises de l'État français est **100% publique et gratuite**.

---

## 🔗 Sources de Données

### API Principales
- 🇫🇷 [API Recherche d'Entreprises](https://recherche-entreprises.api.gouv.fr/) - Identification et données de base
- 🏛️  [FTP RNE INPI](ftp://www.inpi.net/) - Données financières officielles
- 📊 [data.gouv.fr](https://www.data.gouv.fr) - Données publiques

### Inspirations
- 🤝 [datagouv-mcp](https://github.com/datagouv/datagouv-mcp) - Serveur MCP pour data.gouv.fr

---

## 🎓 Guides & Documentation

| Guide | Description |
|-------|-------------|
| [README_RNE_OPTIMAL.md](README_RNE_OPTIMAL.md) | Solution optimisée RNE avec index ultra-léger |
| [COMPARAISON_SOLUTIONS_STOCKAGE.md](COMPARAISON_SOLUTIONS_STOCKAGE.md) | Comparaison FTP gratuit vs VPS vs S3 |
| [GUIDE_STOCKAGE_RNE.md](GUIDE_STOCKAGE_RNE.md) | Guide détaillé des solutions de stockage |
| [GUIDE_PAPPERS.md](GUIDE_PAPPERS.md) | Alternative avec API Pappers |
| [GUIDE_RNE_COMPTES_ANNUELS.md](GUIDE_RNE_COMPTES_ANNUELS.md) | Format des comptes annuels RNE |

---

## 🐛 Dépannage

### L'index RNE n'est pas créé
```bash
python3 create_rne_index_ranges.py
```

### Le cache est trop gros
```bash
rm -rf rne_cache/  # Les fichiers seront re-téléchargés à la demande
```

### Erreur FTP
Vérifiez que les identifiants FTP sont corrects dans `enrichment_hybrid.py`

---

## 📊 Statistiques

- **1,5M entreprises** dans l'index RNE
- **1380 fichiers** JSON sur le FTP INPI
- **213 KB** d'index (réduction 355x vs index complet)
- **12M+ bilans** disponibles

---

## 📝 Licence

MIT License - Voir le fichier LICENSE pour plus de détails.

---

## 🙏 Remerciements

- **État français** pour l'API publique gratuite
- **INPI** pour les données RNE accessibles via FTP
- **datagouv-mcp** pour l'inspiration du projet

---

**Auteur** : yanntanguyyta-stack  
**Version** : 2.0  
**Date** : Février 2026
