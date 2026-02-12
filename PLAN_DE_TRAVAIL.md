# Plan de travail — Refonte enrichissement RNE

## Objectif

Remplacer l'architecture actuelle (cache JSON 15 GB + FTP à la demande) par une solution fiable, compacte et performante basée sur une base SQLite locale contenant **uniquement les données financières indispensables** (6 métriques × 5 ans par SIRET).

---

## Diagnostic actuel

| Problème | Impact | Sévérité |
|----------|--------|----------|
| Cache JSON = **15 GB** sur un disque de 32 GB | Saturation disque, 71% occupé | 🔴 Critique |
| Chaque cache miss télécharge le **ZIP complet de 3.5 GB** | 30-60s par entreprise, timeout fréquents | 🔴 Critique |
| Identifiants FTP **en clair** dans 6+ fichiers source | Sécurité | 🔴 Critique |
| **5 modules d'enrichissement** redondants | Maintenance impossible | 🟡 Important |
| **~20 scripts** obsolètes (cleanup, debug, extraction) | Confusion, dette technique | 🟡 Important |
| Tests `test_app.py` cassés (fonctions supprimées) | Pas de CI possible | 🟡 Important |
| Fonction `load_ranges_index()` définie **2 fois** | Bug silencieux | 🟠 Moyen |
| Nom du ZIP FTP hardcodé avec date | Casse à chaque MAJ INPI | 🟠 Moyen |
| Pas de `.gitignore` | Risque de commit 15 GB de cache | 🟡 Important |

---

## Architecture cible

```
┌──────────────────────────────────────────────────────────────────┐
│                    INITIALISATION (une seule fois)                │
│                                                                  │
│  FTP INPI ──► build_rne_db.py ──► rne_finances.db (~200-350 MB) │
│  (ZIP 3.5 GB)   Extrait 6 métriques    SQLite compact           │
│                 sur 5 ans max           Indexé par SIREN         │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                   UTILISATION QUOTIDIENNE                         │
│                                                                  │
│  Utilisateur ──► app.py (Streamlit) ──► enrichment.py            │
│                                          ├── API DINUM (légal)   │
│                                          └── SQLite (finances)   │
│                                              < 1 ms par requête  │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                   MISE À JOUR (trimestrielle)                    │
│                                                                  │
│  update_rne_db.py ──► Détecte nouveau ZIP ──► Reconstruit DB     │
└──────────────────────────────────────────────────────────────────┘
```

### Gains attendus

| Métrique | Avant | Après | Gain |
|----------|-------|-------|------|
| Stockage | 15 GB (cache JSON) | ~200-350 MB (SQLite) | **97%** |
| Temps enrichissement | 0-60s (aléatoire) | **< 1 ms** | **×60 000** |
| Fiabilité | Dépend du FTP en continu | 100% offline | **Stable** |
| Fichiers Python | 42 | ~15 | **-65%** |
| Modules enrichissement | 5 | 1 | **-80%** |
| Dépendance FTP | À chaque requête | Trimestrielle | **Minime** |

### Structure SQLite

```sql
CREATE TABLE bilans (
    id INTEGER PRIMARY KEY,
    siren TEXT NOT NULL,          -- 9 caractères
    date_cloture TEXT NOT NULL,   -- YYYY-MM-DD
    date_depot TEXT,
    type_bilan TEXT,              -- C (complet), S (simplifié), K (consolidé)
    chiffre_affaires INTEGER,     -- FA (m1)
    resultat_net INTEGER,         -- HN (m1)
    resultat_exploitation INTEGER,-- GC (m1)
    total_actif INTEGER,          -- BJ (m1)
    capitaux_propres INTEGER,     -- DL (m1)
    effectif INTEGER,             -- HY (m1)
    -- m2 = exercice précédent
    ca_precedent INTEGER,         -- FA (m2)
    rn_precedent INTEGER,         -- HN (m2)
    re_precedent INTEGER,         -- GC (m2)
    ta_precedent INTEGER,         -- BJ (m2)
    cp_precedent INTEGER,         -- DL (m2)
    eff_precedent INTEGER         -- HY (m2)
);
CREATE INDEX idx_siren ON bilans(siren);
CREATE INDEX idx_siren_date ON bilans(siren, date_cloture DESC);
```

---

## Phases de travail

### Phase 1 — Fondations (priorité haute)

- [ ] **1.1** Créer `.env` avec les identifiants FTP et `.env.example` sans valeurs
- [ ] **1.2** Créer `.gitignore` (exclure `rne_cache/`, `*.db`, `rne_siren_index.json`, `__pycache__/`, `.env`)
- [ ] **1.3** Créer `build_rne_db.py` — Script de construction de la base SQLite
  - Peut fonctionner depuis le cache existant (1094 fichiers) OU depuis le FTP
  - Extrait les 6 métriques (FA, HN, GC, BJ, DL, HY) avec m1 et m2
  - Filtre : ne garder que les bilans des 5 dernières années
  - Conversion des montants (suppression zéros, détection centimes)
  - Progression affichée + résumé final
- [ ] **1.4** Créer `enrichment.py` — Module d'enrichissement unique et simplifié
  - `enrich(siren)` → données DINUM + finances SQLite
  - `enrich_batch(sirens)` → traitement par lot
  - `get_finances(siren, years=5)` → finances seules depuis SQLite
  - Identifiants via `.env` (python-dotenv)
- [ ] **1.5** Créer `update_rne_db.py` — Script de mise à jour trimestrielle
  - Détecte automatiquement le nom du ZIP le plus récent sur le FTP
  - Télécharge + reconstruit la DB
  - Garde l'ancienne DB en backup pendant la reconstruction

### Phase 2 — Intégration (priorité haute)

- [ ] **2.1** Mettre à jour `app.py` pour utiliser `enrichment.py` au lieu de `enrichment_hybrid.py`
- [ ] **2.2** Mettre à jour `app_pappers.py` si nécessaire
- [ ] **2.3** Corriger `test_app.py` pour refléter l'API actuelle
- [ ] **2.4** Écrire des tests pour `enrichment.py` et `build_rne_db.py`
- [ ] **2.5** Valider le fonctionnement end-to-end avec des SIRENs réels

### Phase 3 — Nettoyage (priorité moyenne)

- [ ] **3.1** Supprimer les modules d'enrichissement obsolètes :
  - `enrichment_hybrid.py`
  - `enrichment_rne.py`
  - `enrichment_rne_ondemand.py`
  - `enrichment_s3.py`
- [ ] **3.2** Supprimer les scripts utilitaires obsolètes :
  - `cleanup_cache.py`, `quick_cleanup.py`, `do_cleanup.py`, `final_fix.py`
  - `convert_cache_streaming.py`
  - `check_status.py`, `check_system.py`, `write_status.py`
  - `download_rne.py`, `download_rne_data.py`
  - `extract_all_rne.py`, `extract_rne_files.py`, `extract_rne_sample.py`
  - `create_rne_index.py`, `create_index_simple.py`, `create_rne_index_ranges.py`
  - `index_rne_data.py`, `setup_rne_data.py`
  - `analyze_rne.py`, `debug_specific_siren.py`, `explore_api.py`
  - `emergency_recovery.sh`, `diagnostic_rne.sh`, `status_final.sh`
- [ ] **3.3** Supprimer les guides devenus obsolètes et consolider la documentation
- [ ] **3.4** Supprimer le cache JSON `rne_cache/` une fois la DB construite
- [ ] **3.5** Supprimer `rne_siren_index.json` (115 MB) et `rne_siren_ranges.json`
- [ ] **3.6** Mettre à jour `requirements.txt` (ajouter `python-dotenv`, retirer `pysftp` si non utilisé)
- [ ] **3.7** Mettre à jour `README.md` avec la nouvelle architecture

### Phase 4 — Pérennisation (priorité basse)

- [ ] **4.1** Ajouter un check au démarrage de l'app : alerte si la DB a > 3 mois
- [ ] **4.2** Logging structuré (`logging` au lieu de `print()`)
- [ ] **4.3** Type hints cohérents sur tout le code
- [ ] **4.4** Dockeriser l'application (optionnel)

---

## Ordre d'exécution recommandé

```
1.1 (.env) + 1.2 (.gitignore)          ← 5 min
         │
         ▼
1.3 (build_rne_db.py)                  ← 2h (code + construction DB depuis cache)
         │
         ▼
1.4 (enrichment.py)                    ← 1h
         │
         ▼
2.1-2.2 (intégration app.py)           ← 1h
         │
         ▼
2.3-2.5 (tests + validation)           ← 1h
         │
         ▼
3.x (nettoyage massif)                 ← 30 min
         │
         ▼
1.5 (update_rne_db.py)                 ← 30 min
         │
         ▼
4.x (pérennisation)                    ← optionnel
```

**Temps total estimé : ~6-7h de travail**

---

## Critères de succès

- [ ] `rne_finances.db` construite et < 500 MB
- [ ] Enrichissement d'un SIREN en < 100 ms (DINUM + SQLite)
- [ ] Enrichissement batch de 1000 SIRENs en < 30s
- [ ] Aucun identifiant en clair dans le code
- [ ] Tous les tests passent
- [ ] Moins de 20 fichiers Python dans le projet
- [ ] Zéro dépendance au FTP en fonctionnement normal
