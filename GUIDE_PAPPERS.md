# 🚀 Guide d'utilisation - Enrichissement Pappers.fr

## 📋 Vue d'ensemble

Ce module enrichit vos données d'entreprises avec **l'historique financier complet** depuis l'API Pappers.fr.

**Workflow en 2 étapes:**
1. **API publique** (`app.py`) → Données de base gratuites
2. **API Pappers** (`app_pappers.py`) → Historique financier détaillé

---

## 🔧 Installation

### 1. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 2. Obtenir une clé API Pappers

1. Créez un compte sur [pappers.fr/api](https://www.pappers.fr/api)
2. Choisissez un plan:
   - **Gratuit**: 100 requêtes/mois (test)
   - **Starter**: 20-30€/mois, ~500 req/mois
   - **Pro**: 50-100€/mois, ~2000 req/mois

### 3. Configurer la clé API

```bash
# Copier le template
cp .env.example .env

# Éditer le fichier .env
nano .env
```

**Contenu du fichier `.env`:**
```env
PAPPERS_API_KEY=votre_clé_api_ici
PAPPERS_DELAY_SECONDS=0.5
```

**Ajuster le délai selon votre plan:**
- Gratuit: `2.0` secondes
- Starter: `0.5` secondes  
- Pro: `0.2` secondes

---

## 🎯 Utilisation

### Option 1: Interface Streamlit (Recommandé)

```bash
streamlit run app_pappers.py
```

**Étapes:**
1. Vérifiez que la clé API est configurée ✅
2. Importez le fichier Excel/CSV avec colonne SIREN
3. Cliquez sur "Lancer l'enrichissement"
4. Téléchargez le fichier enrichi

### Option 2: Module Python

```python
from enrichment_pappers import enrich_with_pappers
import pandas as pd

# Charger vos données
df = pd.read_excel('mes_entreprises.xlsx')

# Enrichir avec Pappers
enriched_df = enrich_with_pappers(df, siren_column='SIREN')

# Exporter
enriched_df.to_excel('entreprises_enrichies.xlsx', index=False)
```

### Option 3: Test rapide

```bash
python enrichment_pappers.py
```

---

## 📊 Données enrichies

**Colonnes ajoutées (par année):**

| Colonne | Description | Exemple |
|---------|-------------|---------|
| `Pappers_CA_2024` | Chiffre d'affaires 2024 | 47 131 317 € |
| `Pappers_Resultat_2024` | Résultat net 2024 | -4 496 719 € |
| `Pappers_Effectif_2024` | Nombre de salariés 2024 | 125 |
| `Pappers_Annees_Disponibles` | Nombre d'années disponibles | 8 |
| `Pappers_Derniere_Annee` | Dernière année de données | 2024 |

**Historique:** Jusqu'à 10 années de données financières par entreprise.

---

## 🔄 Workflow complet recommandé

```
1. app.py (API publique gratuite)
   ↓ Export Excel
2. app_pappers.py (API Pappers payante)
   ↓ Export enrichi
3. Analyse dans Excel/Power BI
```

**Avantages:**
- ✅ Minimiser les coûts (API publique d'abord)
- ✅ Historique financier complet (Pappers ensuite)
- ✅ Données structurées prêtes pour l'analyse

---

## ⚙️ Configuration avancée

### Rate Limiting

Le module respecte automatiquement les limites de votre abonnement:

```python
# Dans .env
PAPPERS_DELAY_SECONDS=0.5  # 2 requêtes/seconde
```

### Retry Logic

- **3 tentatives** automatiques en cas d'erreur 429
- **Backoff exponentiel**: 0.5s → 1s → 2s

### Timeout

- **30 secondes** par requête API

---

## 🐛 Dépannage

### ❌ "Clé API non configurée"

**Solution:**
```bash
# Vérifier que .env existe
ls -la .env

# Vérifier le contenu
cat .env

# La clé doit être différente de 'votre_cle_api_ici'
```

### ❌ "Colonne SIREN introuvable"

**Solution:**
- Votre fichier doit contenir une colonne nommée "SIREN"
- Accepte aussi: "siren", "Siren", "N° SIREN", etc.

### ❌ Rate limit 429

**Solution:**
```env
# Augmenter le délai dans .env
PAPPERS_DELAY_SECONDS=1.0
```

### ❌ "Données non trouvées"

**Causes possibles:**
- SIREN invalide (doit être 9 chiffres)
- Entreprise radiée/fermée
- Données financières non publiées

---

## 📈 Statistiques attendues

**Taux de succès typique:**
- **GE/ETI**: ~95% (presque toutes publient)
- **PME > 50 salariés**: ~60%
- **PME < 50 salariés**: ~30%
- **Micro-entreprises**: ~5%

**Nombre d'années:**
- Grandes entreprises: 8-10 ans
- PME: 3-5 ans
- Récentes: 1-2 ans

---

## 💡 Bonnes pratiques

### Optimiser les coûts

```python
# Filtrer avant d'enrichir
df_grandes = df[df['Effectif'] > 50]  # Seulement les grandes
enriched = enrich_with_pappers(df_grandes)
```

### Batch processing

```python
# Traiter par lots de 100
for i in range(0, len(df), 100):
    batch = df[i:i+100]
    enriched_batch = enrich_with_pappers(batch)
    enriched_batch.to_excel(f'batch_{i}.xlsx', index=False)
```

### Sauvegarder la progression

```python
# Checkpoint tous les 50 SIREN
enriched_df.to_excel('progress_checkpoint.xlsx', index=False)
```

---

## 📞 Support

- **Documentation Pappers**: [pappers.fr/api/documentation](https://www.pappers.fr/api/documentation)
- **Status API**: [status.pappers.fr](https://status.pappers.fr)
- **Tarifs**: [pappers.fr/api/tarifs](https://www.pappers.fr/api/tarifs)

---

## 🎓 Exemples avancés

### Analyser l'évolution du CA

```python
# Calculer la croissance moyenne
for year in range(2020, 2025):
    ca_col = f'Pappers_CA_{year}'
    if ca_col in df.columns:
        df[f'Growth_{year}'] = df[ca_col] / df[f'Pappers_CA_{year-1}'] - 1
```

### Détecter les entreprises en difficulté

```python
# Résultat net négatif 2 années consécutives
df['En_Difficulte'] = (
    (df['Pappers_Resultat_2024'] < 0) & 
    (df['Pappers_Resultat_2023'] < 0)
)
```

---

✅ **Vous êtes prêt !** Lancez `streamlit run app_pappers.py` pour commencer.
