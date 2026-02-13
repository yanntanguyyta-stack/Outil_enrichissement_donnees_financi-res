# 🏢 Recherche d'Entreprises Françaises

Application Streamlit pour rechercher et enrichir les données d'entreprises françaises via l'API officielle de l'État et une base SQLite locale (données financières RNE / INPI).

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-latest-red.svg)

---

## Architecture

```
Utilisateur ──► app.py (Streamlit) ──► API DINUM (identification)
                                   └── rne_finances.db (SQLite, finances)
                                        < 1 ms par requête
```

**Construction de la base (une seule fois) :**
```
FTP INPI (ZIP 3.5 GB) ──► build_rne_db.py ──► rne_finances.db (~250-450 MB)
```

**Mise à jour trimestrielle :**
```
python update_rne_db.py
```

---

## Démarrage rapide

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. (Optionnel) Construire la base financière
#    Copier .env.example en .env et renseigner FTP_USER / FTP_PASSWORD
python build_rne_db.py --from-ftp

# 3. Lancer l'application
streamlit run app.py
```

> Sans la base SQLite, l'application fonctionne avec les seules données de l'API DINUM.

---

## Fonctionnalités

| Catégorie | Détails |
|-----------|---------|
| **Recherche** | Par nom, SIREN (9 chiffres), SIRET (14 chiffres), fichier CSV/Excel |
| **Identification** | SIREN, SIRET, nom, état administratif, date de création |
| **Finances** | CA, résultat net, résultat d'exploitation, total actif, capitaux propres, effectif (jusqu'à 7 ans) |
| **Localisation** | Adresse, code postal, commune, département, région, GPS |
| **Organisation** | Effectifs, dirigeants, nombre d'établissements |
| **Certifications** | Qualiopi, RGE, Bio, ESS, société à mission |
| **Export** | CSV et Excel (.xlsx) |

> ⚠️ Seules 10-20 % des entreprises publient leurs comptes annuels.

---

## Structure du projet

```
TestsMCP/
├── app.py                    # Application Streamlit (interface minimale)
├── enrichment.py             # Module d'enrichissement unifié (API + SQLite)
├── build_rne_db.py           # Construction de la base SQLite depuis cache/FTP
├── update_rne_db.py          # Mise à jour trimestrielle de la base
├── enrichment_pappers.py     # Enrichissement alternatif via Pappers
├── app_pappers.py            # Application Pappers (complémentaire)
├── test_app.py               # Tests de l'application
├── test_build_and_enrichment.py  # Tests des modules build/enrichment
├── requirements.txt          # Dépendances
├── .env.example              # Template de configuration
├── .gitignore                # Fichiers exclus du dépôt
├── PLAN_DE_TRAVAIL.md        # Plan de refonte détaillé
└── README.md                 # Ce fichier
```

---

## Configuration

Copiez `.env.example` en `.env` et renseignez vos identifiants :

```env
FTP_HOST=www.inpi.net
FTP_USER=votre_utilisateur
FTP_PASSWORD=votre_mot_de_passe
```

Réglages optionnels pour les quotas API DINUM (imports volumineux) :

```env
DINUM_API_DELAY_SECONDS=0.8
DINUM_API_MAX_DELAY_SECONDS=8
DINUM_IMPORT_MAX_COMPANIES=1500
```

---

## Tests

```bash
python -m pytest test_app.py test_build_and_enrichment.py -v
```

---

## Sources

- [API Recherche d'Entreprises](https://recherche-entreprises.api.gouv.fr/)
- [INPI — Registre National des Entreprises](https://www.inpi.net/)
- [data.gouv.fr](https://www.data.gouv.fr)

---

**Version** : 3.0 — Février 2026
