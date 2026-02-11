# Comparaison des Solutions de Stockage RNE

## 🎯 Contexte

Vous avez 3 éléments à disposition :
1. **API DINUM** (gratuite) : recherche d'entreprises → SIREN
2. **FTP INPI** (gratuit) : 3,5 GB de données financières
3. **Structure des données** : SIRENs triés numériquement dans 1380 fichiers

## 💡 Solutions Possibles

### Solution 1️⃣ : Index Ultra-Léger par Ranges ✅ **RECOMMANDÉE**

**Architecture :**
```
API DINUM → Obtenir SIREN
    ↓
Index ranges (50 KB) → Trouver fichier
    ↓
FTP INPI → Télécharger 1 fichier (~2-3 MB)
    ↓
Cache local → Éviter re-téléchargement
```

**Avantages :**
- ✅ Stockage minimal : **50 KB** (vs 27 GB)
- ✅ Gratuit (pas de serveur)
- ✅ Simple à maintenir
- ✅ Toujours à jour (FTP INPI)
- ✅ Rapide avec cache (5-10s premier accès, <1s après)

**Inconvénients :**
- ⚠️ Nécessite connexion FTP pour nouveaux fichiers
- ⚠️ Télécharge le ZIP complet 3,5 GB (à optimiser)

**Implémentation :**
```bash
# 1. Créer l'index (1 fois, ~30 min)
python3 create_rne_index_ranges.py

# 2. Utiliser
python3 enrichment_hybrid.py
```

**Fichiers créés :**
- `rne_siren_ranges.json` (~50 KB) → À committer dans Git
- `enrichment_hybrid.py` → Module d'enrichissement
- `rne_cache/` → Cache local (~50-500 MB selon usage, à gitignore)

---

### Solution 2️⃣ : Stockage Distant (S3/GCS/Azure)

**Architecture :**
```
API DINUM → Obtenir SIREN
    ↓
Votre API REST → Index + fichiers JSON sur S3
    ↓
Retour données financières
```

**Options de stockage :**

#### A. Amazon S3 + CloudFront

**Coûts mensuels estimés :**
- Stockage 3,5 GB : ~$0,08/mois
- Transfert sortant 100 GB/mois : ~$9/mois
- CloudFront : ~$8,50/mois
- **Total : ~$17-20/mois**

**Avantages :**
- ✅ Accès rapide partout (CDN)
- ✅ Scalabilité infinie
- ✅ Haute disponibilité (99,99%)

**Setup :**
```bash
# Upload vers S3
aws s3 cp stock_comptes_annuels.zip s3://mon-bucket-rne/
aws s3 cp rne_siren_ranges.json s3://mon-bucket-rne/

# Extraction en Lambda/Fargate à la demande
```

#### B. Google Cloud Storage

**Coûts mensuels estimés :**
- Stockage 3,5 GB : ~$0,07/mois
- Transfert sortant 100 GB/mois : ~$12/mois
- **Total : ~$12-15/mois**

**Setup :**
```bash
gsutil cp stock_comptes_annuels.zip gs://mon-bucket-rne/
```

#### C. Azure Blob Storage

**Coûts mensuels estimés :**
- Stockage 3,5 GB : ~$0,07/mois
- Transfert sortant 100 GB/mois : ~$8/mois
- **Total : ~$8-12/mois**

#### D. Serveur VPS personnel (Hetzner, OVH, etc.)

**Coûts mensuels :**
- VPS 40 GB : ~€3-5/mois (~$3-6)
- Bande passante illimitée

**Avantages :**
- ✅ Coût fixe prévisible
- ✅ Contrôle total
- ✅ Pas de limites de transfert

**Inconvénients :**
- ⚠️ Maintenance serveur
- ⚠️ Moins scalable
- ⚠️ Une seule région

**Setup :**
```bash
# Sur le VPS
scp stock_comptes_annuels.zip user@vps:/data/rne/

# API Flask/FastAPI
@app.get("/rne/{siren}")
def get_rne_data(siren: str):
    # Lire fichier local et retourner données
    ...
```

---

### Solution 3️⃣ : Hybrid Cloud (Index local + Fichiers cloud)

**Architecture :**
```
Local : rne_siren_ranges.json (50 KB)
Cloud : 1380 fichiers JSON sur S3 (~3,5 GB décompressé)

API DINUM → SIREN
    ↓
Index local → Fichier
    ↓
S3 GET → Télécharger 1 fichier (2-3 MB)
    ↓
Cache local
```

**Coûts mensuels :**
- Stockage S3 : ~$0,08/mois
- Transfert (1 file/requête) : ~$0,10-1/mois
- **Total : ~$0,20-2/mois**

**Setup :**
```python
import boto3

s3 = boto3.client('s3')

def get_file_from_s3(filename):
    response = s3.get_object(Bucket='mon-bucket-rne', Key=filename)
    return json.loads(response['Body'].read())
```

---

## 📊 Tableau Comparatif

| Solution | Coût mensuel | Stockage local | Vitesse | Maintenance | Scalabilité |
|----------|-------------|----------------|---------|-------------|-------------|
| **Index ranges + FTP** ✅ | **Gratuit** | **50 KB** | Rapide (cache) | Très faible | Moyenne |
| S3 + CloudFront | $17-20 | 50 KB | Très rapide | Moyenne | Excellente |
| Google Cloud Storage | $12-15 | 50 KB | Très rapide | Moyenne | Excellente |
| Azure Blob | $8-12 | 50 KB | Rapide | Moyenne | Excellente |
| VPS personnel | $3-6 | 50 KB | Rapide | Élevée | Faible |
| Hybrid (Index + S3) | $0,20-2 | 50 KB | Rapide | Faible | Bonne |

---

## 🎯 Recommandations

### Pour un projet personnel/MVP
→ **Solution 1 (Index + FTP)** : Gratuit, simple, largement suffisant

### Pour une startup/small business
→ **Solution 3 (Hybrid)** : $0,20-2/mois, bon compromis

### Pour une application en production avec fort trafic
→ **S3 + CloudFront** ou **Azure** : $8-20/mois, excellentes performances

### Pour contrôler les coûts et trafic modéré
→ **VPS personnel** : $3-6/mois, coût fixe

---

## 🚀 Implémentation Recommandée (Solution 1)

### Étape 1 : Créer l'index
```bash
python3 create_rne_index_ranges.py
# → Crée rne_siren_ranges.json (~50 KB)
```

### Étape 2 : Configuration Git
```bash
# .gitignore
rne_cache/
stock_comptes_annuels.zip
*.log

# Committer l'index
git add rne_siren_ranges.json
git commit -m "Ajout index RNE ultra-léger par ranges"
```

### Étape 3 : Utilisation
```python
from enrichment_hybrid import enrich_from_api_dinum_and_rne

# Enrichir une entreprise
data = enrich_from_api_dinum_and_rne("552100554")  # EDF

# Premier appel: télécharge depuis FTP (~5-10s)
# Appels suivants: utilise le cache (<1s)
```

### Étape 4 : Optimisation (optionnel)

Si le téléchargement du ZIP complet (3,5 GB) est trop lent, deux options :

**A. Extraire tous les fichiers une fois et les héberger**
```bash
# Extraire
unzip stock_comptes_annuels.zip -d rne_extracted/

# Upload vers S3/GCS (solution hybrid)
aws s3 sync rne_extracted/ s3://mon-bucket-rne/

# Modifier enrichment_hybrid.py pour télécharger depuis S3
```

**B. Range requests HTTP (avancé)**
```python
# Télécharger seulement une partie du ZIP via FTP
# Requiert calcul des offsets (complexe)
```

---

## 💰 Calcul des Coûts pour Production

**Hypothèses :**
- 1000 requêtes/jour
- 30% cache hit rate
- 700 fichiers uniques téléchargés/jour
- Taille moyenne fichier : 2,5 MB

**Solution 1 (FTP gratuit) :**
- Bande passante: 700 × 2,5 MB × 30 jours = 52 GB/mois
- Coût FTP : **Gratuit**
- Coût stockage cache local : **Gratuit**
- **Total : $0/mois**

**Solution 3 (S3 Hybrid) :**
- Stockage : 3,5 GB × $0,023 = $0,08
- Transfert sortant : 52 GB × $0,09 = $4,68
- Requêtes GET : 21 000 × $0,0004/1000 = $0,008
- **Total : $4,77/mois**

**Solution VPS :**
- VPS 40 GB Hetzner : **€3,29/mois** (~$3,50)
- Bande passante illimitée incluse
- **Total : $3,50/mois**

---

## ✅ Conclusion

Pour votre cas avec l'API DINUM déjà en place :

1. **Commencez avec Solution 1** (Index + FTP) : Gratuit, rapide à mettre en place
2. **Si trop lent** : Passez à Solution 3 (Index + S3) : ~$0,50-5/mois
3. **Si fort trafic** : VPS personnel à €3-5/mois avec bande passante illimitée

L'index ultra-léger par ranges combiné à l'API DINUM est la solution optimale pour 99% des cas !
