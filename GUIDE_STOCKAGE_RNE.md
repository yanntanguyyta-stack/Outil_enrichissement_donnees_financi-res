# Solution de Stockage Optimisée pour les Données RNE

## ❌ Problème Initial
- Disque à 100% plein (30 GB / 32 GB)
- ZIP RNE: 3,5 GB
- Fichiers extraits: 24 GB
- **Total: 27,5 GB** rien que pour le RNE !

## ✅ Solution Retenue: Téléchargement à la Demande

### Architecture
```
┌─────────────────────────────────────────────────────────┐
│  FTP INPI (www.inpi.net)                                │
│  └── stock_comptes_annuels.zip (3,5 GB)                │
│      └── stock_000001.json ... stock_001380.json       │
└─────────────────────────────────────────────────────────┘
                        ▼
            Créer un index léger (1 fois)
                        ▼
┌─────────────────────────────────────────────────────────┐
│  Repo Git                                               │
│  └── rne_siren_index.json (~10-50 MB)                  │
│      Format: {"SIREN": {"file": "stock_XXXXX.json"}}   │
└─────────────────────────────────────────────────────────┘
                        ▼
            Recherche d'entreprise par SIREN
                        ▼
┌─────────────────────────────────────────────────────────┐
│  Cache local temporaire (rne_cache/)                    │
│  └── Seulement les fichiers téléchargés (~10-100 MB)   │
└─────────────────────────────────────────────────────────┘
```

### Avantages

1. **Stockage minimal**: ~10-50 MB au lieu de 27,5 GB (500x moins)
2. **Toujours à jour**: Données directement depuis l'INPI
3. **Rapide**: Cache local pour éviter les re-téléchargements
4. **Pas de limite**: Espace disque presque illimité sur le FTP
5. **Gratuit**: Pas de coût Git LFS

### Fichiers Créés

#### 1. `create_rne_index.py`
Crée l'index léger mappant SIREN → fichier JSON
```bash
python3 create_rne_index.py --create    # Créer l'index
python3 create_rne_index.py --verify    # Vérifier l'index
python3 create_rne_index.py --cleanup   # Nettoyer les gros fichiers
```

#### 2. `enrichment_rne_ondemand.py`
Module d'enrichissement qui télécharge à la demande
```python
from enrichment_rne_ondemand import enrich_with_rne_ondemand

data = enrich_with_rne_ondemand("552100554")  # EDF
# Télécharge seulement le fichier nécessaire depuis le FTP
```

#### 3. `rne_siren_index.json` (à versionner)
Index léger (~10-50 MB) à committer dans Git
```json
{
  "index": {
    "552100554": {"file": "stock_000123.json", "count": 15},
    "005880596": {"file": "stock_000456.json", "count": 8}
  },
  "stats": {
    "total_companies": 4500000,
    "total_bilans": 12000000
  }
}
```

### Workflow d'Utilisation

#### Installation Initiale (1 fois)
```bash
# 1. Vérifier que le ZIP est téléchargé
ls -lh stock_comptes_annuels.zip

# 2. Créer l'index
python3 create_rne_index.py --create

# 3. Nettoyer les gros fichiers
python3 create_rne_index.py --cleanup
# Ceci supprime le ZIP et rne_data/ (libère ~27 GB)

# 4. Committer l'index dans Git
git add rne_siren_index.json
git commit -m "Ajout index RNE léger"
```

#### Utilisation Quotidienne
```python
# Les fichiers sont téléchargés automatiquement à la demande
from enrichment_rne_ondemand import enrich_with_rne_ondemand

data = enrich_with_rne_ondemand("552100554", max_results=5)
# → Télécharge seulement stock_XXXXX.json depuis le FTP (si pas en cache)
# → ~75 MB pour 1 fichier au lieu de 27 GB
```

#### Mise à Jour (tous les 6 mois)
```bash
# Quand l'INPI publie une nouvelle version:
# 1. Télécharger le nouveau ZIP
wget ftp://rneinpiro:vv8_rQ5f4M_2-E@www.inpi.net/stock_RNE_comptes_annuels_YYYYMMDD.zip

# 2. Recréer l'index
python3 create_rne_index.py --create

# 3. Nettoyer et committer
python3 create_rne_index.py --cleanup
git add rne_siren_index.json
git commit -m "MAJ index RNE $(date +%Y-%m-%d)"
```

### Comparaison des Solutions

| Solution | Stockage Local | Coût | Maintenance | Vitesse |
|----------|---------------|------|-------------|---------|
| **Tout extraire** | 27 GB | 😡 | 😊 Aucune | 😊 Très rapide |
| **Git LFS** | Variable | 😡 $$$$ | 😐 Moyenne | 😐 Moyen |
| **FTP à la demande** ✅ | 10-50 MB | 😊 Gratuit | 😊 Facile | 😊 Rapide avec cache |

### Cache Local

Le cache (`rne_cache/`) stocke temporairement les fichiers téléchargés:
- Évite de re-télécharger les mêmes fichiers
- Peut être nettoyé à tout moment sans perte de données
- Taille typique: 50-500 MB (selon usage)

```bash
# Nettoyer le cache si nécessaire
rm -rf rne_cache/
# Les fichiers seront re-téléchargés à la demande
```

### Limitations

1. **Première indexation longue**: ~30-60 minutes pour créer l'index (1 fois)
2. **Requiert connexion FTP**: Pour télécharger les fichiers à la demande
3. **Légèrement plus lent**: Premier accès télécharge depuis FTP (~5-10 secondes par fichier)

### Recommandations

✅ **À faire:**
- Committer seulement `rne_siren_index.json` dans Git
- Ajouter `rne_cache/` au `.gitignore`
- Mettre à jour l'index tous les 6 mois

❌ **À éviter:**
- Ne PAS committer le ZIP 3,5 GB
- Ne PAS committer `rne_data/` (24 GB)
- Ne PAS utiliser Git LFS (coûte cher)

### Questions Fréquentes

**Q: Que se passe-t-il si le FTP est indisponible?**
R: Les fichiers en cache restent disponibles. Pour une redondance totale, gardez une copie du ZIP en backup externe.

**Q: Puis-je utiliser cette solution en production?**
R: Oui, mais ajoutez une gestion d'erreur robuste et éventuellement un cache Redis partagé.

**Q: Combien de temps prend un enrichissement?**
R: 
- Avec cache: <1 seconde
- Sans cache (1er accès): ~5-10 secondes (téléchargement FTP)

**Q: Puis-je traiter plusieurs entreprises en parallèle?**
R: Oui, utilisez `concurrent.futures` pour paralléliser les téléchargements.

---

## Conclusion

Cette solution réduit le stockage de **27 GB à 10-50 MB** (facteur 500x) tout en maintenant l'accès à toutes les données via le FTP INPI. C'est la solution optimale pour un projet dans un environnement avec contraintes d'espace disque.
