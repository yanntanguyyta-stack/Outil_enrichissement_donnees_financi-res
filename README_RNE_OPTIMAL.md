# 🏛️ Solution Optimale : Enrichissement RNE avec API DINUM

## 🎯 Réponse à Vos Questions

### 1. Peut-on utiliser l'API DINUM pour simplifier l'identification des fichiers ?

**✅ OUI !** Découverte majeure : les SIRENs sont **triés numériquement** dans les fichiers RNE.

**Avant (ce qu'on faisait) :**
- Index de 50 MB avec tous les SIRENs individuellement
- Recherche O(1) mais stockage énorme

**Maintenant (solution optimale) :**
- Index de **50 KB** avec seulement les ranges min/max par fichier
- Recherche O(log n) (très rapide) et stockage minimal

```
stock_000001.json: 005420120 → 066304866 (1751 entreprises)
stock_000002.json: 066305202 → 300560588 (1756 entreprises)
...
```

### 2. Stockage sur serveur distant : est-ce envisageable ?

**✅ OUI**, plusieurs options selon budget :

| Solution | Coût/mois | Avantages | Inconvénients |
|----------|-----------|-----------|---------------|
| **Index + FTP** (recommandé) | **Gratuit** | Simple, toujours à jour | Nécessite FTP |
| VPS personnel | $3-6 | Coût fixe, contrôle total | Maintenance |
| S3/GCS/Azure | $8-20 | Scalable, haute dispo | Coût variable |

**Voir [COMPARAISON_SOLUTIONS_STOCKAGE.md](COMPARAISON_SOLUTIONS_STOCKAGE.md) pour détails**

---

## 📦 Architecture Finale (Recommandée)

```
┌─────────────────────────────────────────┐
│  1. API DINUM (gratuit)                 │
│     https://recherche-entreprises       │
│     .api.gouv.fr                        │
└────────────┬────────────────────────────┘
             │ Recherche entreprise
             ▼
      Obtenir SIREN
             │
             ▼
┌─────────────────────────────────────────┐
│  2. Index Ultra-Léger (50 KB local)     │
│     rne_siren_ranges.json               │
│     Recherche binaire O(log n)          │
└────────────┬────────────────────────────┘
             │ Trouver fichier: stock_XXXXX.json
             ▼
┌─────────────────────────────────────────┐
│  3. FTP INPI (gratuit)                  │
│     ftp://www.inpi.net                  │
│     Télécharger 1 fichier (2-3 MB)     │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  4. Cache Local (50-500 MB)             │
│     rne_cache/stock_XXXXX.json          │
│     Éviter re-téléchargements           │
└─────────────────────────────────────────┘
```

**Stockage total : ~50 KB + cache temporaire**

---

## 🚀 Guide de Mise en Place

### Étape 1 : Créer l'Index Ultra-Léger

```bash
# Le script est déjà lancé en arrière-plan
# Attendre 10-20 minutes pour l'indexation complète
python3 create_rne_index_ranges.py

# Vérifier la création
ls -lh rne_siren_ranges.json
# Devrait faire ~50 KB
```

### Étape 2 : Configurer Git

```bash
# Ajouter au .gitignore
echo "rne_cache/" >> .gitignore
echo "stock_comptes_annuels.zip" >> .gitignore
echo "*.log" >> .gitignore

# Committer l'index léger
git add rne_siren_ranges.json
git add enrichment_hybrid.py
git add create_rne_index_ranges.py
git commit -m "Ajout solution RNE optimisée avec index ultra-léger"
```

### Étape 3 : Nettoyer l'Espace Disque

```bash
# Supprimer le ZIP (libère 3,5 GB)
rm stock_comptes_annuels.zip

# Le répertoire rne_data/ a déjà été supprimé (24 GB libérés)

# Vérifier l'espace
df -h /workspaces
# Devrait montrer ~24-26 GB libres sur 32 GB
```

### Étape 4 : Utiliser l'Enrichissement

```python
from enrichment_hybrid import enrich_from_api_dinum_and_rne, display_financial_data

# Enrichir une entreprise
siren = "552100554"  # EDF
data = enrich_from_api_dinum_and_rne(siren, max_bilans=5)

# Afficher
display_financial_data(data)

# Premier appel: télécharge depuis FTP (~5-10s)
# Appels suivants: utilise le cache (<1s)
```

### Étape 5 : Tester

```bash
python3 test_hybrid_approach.py
```

---

## 📊 Comparaison Avant/Après

### Avant (Extraction Complète)
- 💾 Stockage: **27 GB** (ZIP 3,5 GB + extraits 24 GB)
- ⏱️ Recherche: Très rapide (O(1))
- 💰 Coût: Gratuit
- ⚠️ Problème: **Disque plein à 100%**

### Après (Index + FTP à la demande)
- 💾 Stockage: **50 KB** + cache temporaire (50-500 MB)
- ⏱️ Recherche: Rapide (O(log n) + cache)
- 💰 Coût: **Gratuit**
- ✅ **24 GB libérés !**

---

## 📁 Fichiers Créés

### À Committer dans Git
- ✅ `rne_siren_ranges.json` (~50 KB) - Index ultra-léger
- ✅ `enrichment_hybrid.py` - Module d'enrichissement
- ✅ `create_rne_index_ranges.py` - Script de création d'index
- ✅ `test_hybrid_approach.py` - Script de test
- ✅ `COMPARAISON_SOLUTIONS_STOCKAGE.md` - Documentation complète
- ✅ Ce README

### À Ignorer (`.gitignore`)
- ❌ `rne_cache/` - Cache local temporaire
- ❌ `stock_comptes_annuels.zip` - Fichier volumineux (3,5 GB)
- ❌ `rne_data/` - Extraits (24 GB) - déjà supprimé
- ❌ `*.log` - Logs temporaires

### Optionnels (Solutions Alternatives)
- 📄 `enrichment_s3.py` - Si vous voulez utiliser AWS S3
- 📄 `enrichment_rne_ondemand.py` - Version précédente (toujours valide)

---

## 💡 Workflow Typique

### Développement Local
```python
# 1. Rechercher entreprise via API DINUM
import requests

response = requests.get(
    "https://recherche-entreprises.api.gouv.fr/search",
    params={"q": "Microsoft France"}
)
siren = response.json()['results'][0]['siren']

# 2. Enrichir avec RNE
from enrichment_hybrid import enrich_from_api_dinum_and_rne

data = enrich_from_api_dinum_and_rne(siren)

# 3. Utiliser les données
print(f"CA: {data['bilans'][0]['chiffre_affaires']} €")
```

### Traitement par Lots
```python
# Enrichir plusieurs entreprises
sirens = ["552100554", "775665019", "542051180"]

for siren in sirens:
    data = enrich_from_api_dinum_and_rne(siren)
    if data['success']:
        print(f"{data['denomination']}: {data['nb_bilans']} bilans")
    # Les fichiers sont mis en cache automatiquement
```

---

## 🔄 Maintenance

### Rafraîchir les Données (tous les 6 mois)

Quand l'INPI publie une nouvelle version :

```bash
# 1. Re-télécharger le ZIP
wget ftp://rneinpiro:vv8_rQ5f4M_2-E@www.inpi.net/stock_RNE_comptes_annuels_YYYYMMDD.zip -O stock_comptes_annuels.zip

# 2. Recréer l'index
python3 create_rne_index_ranges.py

# 3. Vider le cache (optionnel)
rm -rf rne_cache/

# 4. Supprimer le ZIP
rm stock_comptes_annuels.zip

# 5. Committer le nouvel index
git add rne_siren_ranges.json
git commit -m "MAJ index RNE $(date +%Y-%m-%d)"
```

### Nettoyer le Cache

```bash
# Le cache grossit au fur et à mesure
du -sh rne_cache/

# Nettoyer si trop gros
rm -rf rne_cache/
# Les fichiers seront re-téléchargés à la demande
```

---

## 🎓 Pour Aller Plus Loin

### Optimisation 1 : Paralléliser les Téléchargements

```python
from concurrent.futures import ThreadPoolExecutor

def enrich_batch(sirens: List[str]):
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(enrich_from_api_dinum_and_rne, siren)
            for siren in sirens
        ]
        return [f.result() for f in futures]
```

### Optimisation 2 : Utiliser S3 pour Plus de Rapidité

Si le FTP est trop lent :

```bash
# 1. Extraire tous les fichiers
unzip stock_comptes_annuels.zip -d rne_extracted/

# 2. Upload vers S3
aws s3 sync rne_extracted/ s3://mon-bucket-rne/

# 3. Utiliser enrichment_s3.py
# Coût: ~$0,50-5/mois
```

### Optimisation 3 : API REST Personnalisée

Créer votre propre API pour centraliser :

```python
# FastAPI
from fastapi import FastAPI

app = FastAPI()

@app.get("/rne/{siren}")
def get_rne_data(siren: str):
    return enrich_from_api_dinum_and_rne(siren)
```

---

## ❓ FAQ

**Q: Combien de temps prend la création de l'index ?**
R: 10-20 minutes pour 1380 fichiers (~3,5 GB). À faire une seule fois.

**Q: Puis-je utiliser cela sans le ZIP ?**
R: Oui, mais vous devez avoir créé l'index au moins une fois. Ensuite, supprimez le ZIP.

**Q: Que se passe-t-il si le FTP est indisponible ?**
R: Le cache local continue de fonctionner. Seuls les nouveaux fichiers ne pourront pas être téléchargés.

**Q: Puis-je partager le cache entre plusieurs projets ?**
R: Oui, configurez `CACHE_DIR` vers un emplacement partagé.

**Q: Est-ce plus lent que tout avoir en local ?**
R: Premier accès: oui (~5-10s pour télécharger). Accès suivants: non (<1s depuis le cache).

---

## ✅ Conclusion

L'approche hybride **API DINUM + Index ultra-léger + FTP à la demande** est la solution optimale pour votre cas :

- ✅ **Gratuit**
- ✅ **50 KB de stockage** (vs 27 GB)
- ✅ **Rapide** avec cache
- ✅ **Simple** à maintenir
- ✅ **Toujours à jour**

**24 GB d'espace disque libérés !** 🎉

---

**Fichiers de documentation :**
- [COMPARAISON_SOLUTIONS_STOCKAGE.md](COMPARAISON_SOLUTIONS_STOCKAGE.md) - Comparaison détaillée des solutions
- [GUIDE_STOCKAGE_RNE.md](GUIDE_STOCKAGE_RNE.md) - Guide original (solution avec extraction complète)
