# 📦 Guide du Traitement par Lots Optimisé

## Vue d'ensemble

Le système de traitement par lots optimisé permet de traiter efficacement **des fichiers volumineux contenant des centaines d'entreprises** tout en respectant les contraintes d'espace disque limité.

## 🎯 Problème résolu

### Contraintes
- ✅ Espace disque limité (~30 GB total)
- ✅ Fichiers RNE de ~2-3 MB chacun (1380 fichiers disponibles)
- ✅ Besoin de traiter potentiellement des centaines d'entreprises

### Solution
**Traitement par lots avec nettoyage automatique** :
1. Grouper les entreprises par fichier RNE nécessaire
2. Télécharger et traiter par lots
3. Supprimer automatiquement après traitement
4. Paralléliser (3 fichiers RNE max simultanément)

## 🚀 Fonctionnement

### Activation automatique

Le mode batch s'active **automatiquement** quand :
- ✅ Nombre d'entreprises ≥ 50
- ✅ Enrichissement RNE activé dans la sidebar
- ✅ Module `enrichment_hybrid.py` disponible

### Les 3 phases

#### 📊 Phase 1 : Identification (API DINUM)
```
Pour chaque entreprise :
  → Recherche via API DINUM
  → Récupération du SIREN
  → Stockage temporaire en mémoire
```

**Affichage** : Barre de progression + nombre traité

#### 📦 Phase 2 : Regroupement optimal
```
Algorithme de groupement :
  1. Charger l'index léger (213 KB)
  2. Pour chaque SIREN :
     → Recherche binaire O(log n) dans l'index
     → Identifier le fichier RNE correspondant
  3. Grouper : {fichier_RNE: [siren1, siren2, ...]}
```

**Résultat** : Carte `filename → liste de SIRENs`

#### ⚡ Phase 3 : Traitement parallèle
```python
with ThreadPoolExecutor(max_workers=3):
    Pour chaque fichier RNE en parallèle :
      1. Télécharger (FTP INPI, ~7 secondes)
      2. Extraire les bilans des SIRENs du lot
      3. Formatter les données
      4. SUPPRIMER le fichier du cache
      5. Continuer avec le prochain lot
```

**Avantages** :
- 💾 Maximum 3 fichiers RNE en mémoire (≈ 7.5 MB)
- ⚡ Parallélisation : gain de 66% de temps
- 🗑️ Nettoyage automatique : pas de saturation disque

## 📊 Performances

### Exemple : 100 entreprises

**Répartition typique** :
- 8 fichiers RNE différents
- 12-13 entreprises par fichier en moyenne

**Temps de traitement** :
| Mode | Temps | Détail |
|------|-------|--------|
| Séquentiel | ~56s | 8 fichiers × 7s |
| Parallèle (3 workers) | ~19s | ⌈8/3⌉ × 7s |
| **Gain** | **66%** | 37s gagnées |

**Espace disque** :
| Mode | Stockage |
|------|----------|
| Tout télécharger | ~20 MB (8 fichiers) |
| Par lots (3 max) | ~7.5 MB (3 fichiers) |
| **Économie** | **62%** |

### Exemple : 500 entreprises

**Répartition typique** :
- 35 fichiers RNE différents
- 14-15 entreprises par fichier

**Temps** :
- Séquentiel : ~245s (4 min)
- Parallèle : ~82s (1.4 min)
- **Gain : 66%**

**Espace** :
- Maximum : ~7.5 MB (3 fichiers simultanés)
- Pas de saturation possible

## 🎨 Interface utilisateur

### Sidebar : Activation

```
🏛️ Enrichissement RNE
☑ Activer enrichissement FTP/RNE

✅ Enrichissement RNE activé
📈 Données sur plusieurs années
💾 Cache local (rapide)
🔄 Téléchargement à la demande

🚀 Mode optimisé pour gros volumes
À partir de 50 entreprises :
- 📦 Tri par fichiers RNE
- ⚡ Traitement parallèle (3 fichiers max)
- 🗑️ Nettoyage automatique
- 💾 Économie d'espace disque
```

### Affichage pendant le traitement

**Mode batch activé** :
```
🚀 Mode d'optimisation activé pour 150 entreprises

Traitement par lots optimisé :
- 📊 Phase 1: Récupération des SIRENs via API DINUM
- 📦 Phase 2: Tri et regroupement par fichier RNE
- ⚡ Phase 3: Téléchargement parallèle (3 fichiers max simultanés)
- 🗑️ Nettoyage automatique après chaque lot

📊 Phase 1: Identification des entreprises
Recherche 73/150: Entreprise ABC...
[████████████████████████░░░░░░░░] 48%

📦 Phase 2-3: Enrichissement RNE par lots
📦 Fichiers traités: 8/23 - Actuel: stock_000145.json
[████████░░░░░░░░░░░░░░░░░░░░░░░░] 35%

✅ Traitement terminé : 150 entreprises traitées
```

## 🔧 Configuration

### Paramètres dans `enrichment_hybrid.py`

```python
# Nombre max de fichiers RNE téléchargés simultanément
MAX_CONCURRENT_FILES = 3

# Taille moyenne d'un fichier RNE (pour estimation)
AVG_RNE_FILE_SIZE_MB = 2.5
```

### Paramètres dans `app.py`

```python
# Seuil d'activation du mode batch
BATCH_THRESHOLD = 50  # Minimum entreprises pour activer
```

### Personnalisation

Pour ajuster selon vos besoins :

**Plus de performance (+ espace disque)** :
```python
MAX_CONCURRENT_FILES = 3
LIMITED_SPACE_MODE = False
# Nécessite ~240 MB de cache (3 × 80 MB)
```

**Moins d'espace disque (mode actuel, recommandé)** :
```python
MAX_CONCURRENT_FILES = 1  # 1 fichier à la fois
LIMITED_SPACE_MODE = True  # Nettoyage agressif
# Seulement ~80 MB de cache temporaire
# + 84 fichiers de base (000001-000084) = 5.2 GB pérennes
```

## 📋 API du module

### Fonctions principales

#### `group_sirens_by_rne_file(sirens: List[str]) -> Dict[str, List[str]]`
Groupe les SIRENs par fichier RNE.

```python
sirens = ["552100554", "005880596", "775665019"]
grouped = group_sirens_by_rne_file(sirens)
# {
#   "stock_000498.json": ["552100554"],
#   "stock_000001.json": ["005880596"],
#   "stock_000534.json": ["775665019"]
# }
```

#### `process_batch(filename, sirens, max_bilans=10, cleanup=True) -> Dict`
Traite un lot de SIRENs depuis un même fichier RNE.

```python
results = process_batch(
    "stock_000498.json",
    ["552100554"],
    max_bilans=10,
    cleanup=True  # Supprimer après traitement
)
```

#### `enrich_batch_parallel(sirens, max_bilans=10, max_workers=3, progress_callback=None) -> Dict`
Enrichissement parallèle optimisé.

```python
def progress(completed, total, current_file):
    print(f"{completed}/{total}: {current_file}")

results = enrich_batch_parallel(
    sirens=["552100554", "005880596"],
    max_bilans=10,
    max_workers=3,
    progress_callback=progress
)
```

## 🧪 Tests

### Lancer les tests

```bash
python3 test_batch_processing.py
```

**Tests disponibles** :
1. ✅ Regroupement par fichier RNE
2. ✅ Traitement d'un lot unique (nécessite FTP)
3. ✅ Traitement parallèle (nécessite FTP)
4. ✅ Simulation gros volume (sans FTP)

### Tests unitaires rapides

```bash
# Test sans connexion FTP
python3 test_batch_processing.py <<< "n"

# Test complet avec FTP
python3 test_batch_processing.py <<< "o"
```

## 💡 Conseils d'utilisation

### Pour des fichiers très volumineux (1000+ entreprises)

1. **Utilisez le mode RNE activé** pour bénéficier du batch
2. **Laissez le temps** : ~1-2 min par 100 entreprises
3. **Surveillez l'espace disque** : reste stable (~7 MB cache)
4. **Exportez régulièrement** les résultats

### Limitation de l'API DINUM

- 250 requêtes / minute
- Délai appliqué : 0.5s entre requêtes
- 100 entreprises = ~50s phase 1

### En cas de problème

**Erreur "Limit API atteinte"** :
- Le système retry automatiquement (backoff exponentiel)
- Maximum 3 tentatives par entreprise

**Fichier RNE non trouvé** :
- Vérifiez la connexion FTP
- Certains SIRENs peuvent être hors limites RNE

**Manque d'espace** :
- Réduire `MAX_CONCURRENT_FILES` à 2
- Vérifier `/workspaces` : `df -h`

## 🎓 Algorithme détaillé

### Complexité

| Opération | Complexité |
|-----------|------------|
| Recherche dans index | O(log n) par SIREN |
| Groupement | O(m × log n), m=nb SIRENs |
| Téléchargement | O(k/w), k=fichiers, w=workers |
| Extraction | O(m) |
| **Total** | **O(m × log n + k/w + m)** |

Pour 100 entreprises :
- m = 100 SIRENs
- n = 1380 fichiers (index)
- k ≈ 8 fichiers RNE
- w = 3 workers

→ O(100 × 11 + 3 + 100) ≈ O(1203) opérations

### Pseudo-code complet

```python
def traiter_fichier_volumineux(fichier_csv):
    # Phase 1: Identification
    sirens_map = {}
    for entreprise in fichier_csv:
        data = api_dinum.recherche(entreprise.nom)
        if data.siren:
            sirens_map[data.siren] = (data, entreprise)
    
    # Phase 2: Groupement optimal
    index = charger_index_ranges()  # 213 KB
    groupes = {}
    for siren in sirens_map.keys():
        fichier_rne = recherche_binaire(siren, index)
        groupes[fichier_rne].append(siren)
    
    # Phase 3: Traitement parallèle
    resultats = {}
    with ThreadPool(workers=3) as pool:
        futures = []
        for fichier_rne, sirens_lot in groupes.items():
            future = pool.submit(
                telecharger_traiter_nettoyer,
                fichier_rne,
                sirens_lot
            )
            futures.append(future)
        
        for future in as_completed(futures):
            resultats.update(future.result())
    
    return resultats

def telecharger_traiter_nettoyer(fichier, sirens):
    # Télécharger
    data = ftp.download(fichier)  # ~7s
    
    # Traiter
    bilans = {}
    for siren in sirens:
        bilans[siren] = extraire_bilans(data, siren)
    
    # Nettoyer (crucial!)
    os.remove(cache / fichier)
    
    return bilans
```

## 📚 Références

- **Index RNE** : [rne_siren_ranges.json](rne_siren_ranges.json) (213 KB)
- **Module** : [enrichment_hybrid.py](enrichment_hybrid.py)
- **Tests** : [test_batch_processing.py](test_batch_processing.py)
- **Guide stockage** : [GUIDE_STOCKAGE_RNE.md](GUIDE_STOCKAGE_RNE.md)

## 🎉 Résumé

Le traitement par lots optimisé vous permet de :

- ✅ **Traiter des centaines d'entreprises** sans saturer le disque
- ✅ **Gagner 66% de temps** grâce à la parallélisation
- ✅ **Économiser 62% d'espace** avec le nettoyage automatique
- ✅ **Interface simple** : activation automatique dès 50 entreprises
- ✅ **Robustesse** : retry automatique, gestion d'erreurs

**Mode d'emploi** : Uploadez votre fichier CSV, activez l'enrichissement RNE, et laissez le système optimiser automatiquement ! 🚀
