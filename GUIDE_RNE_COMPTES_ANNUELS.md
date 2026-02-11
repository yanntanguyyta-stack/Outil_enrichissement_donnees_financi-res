# Guide des Données RNE - Comptes Annuels

## 📊 Vue d'ensemble

Le Registre National des Entreprises (RNE) de l'INPI fournit accès aux comptes annuels déposés par les entreprises françaises.

### 🔑 Accès SFTP/FTP

- **Hôte**: www.inpi.net
- **Utilisateur**: rneinpiro
- **Protocole**: FTP (port 21)
- **Fichier**: `stock_RNE_comptes_annuels_20250926_1000_v2.zip` (3,6 GB)

### 📦 Structure des données

- **1380 fichiers JSON** (~70 MB chacun)
- **Format**: JSONL (1 ligne = 1 array contenant tous les bilans d'une plage d'entreprises)
- **Encodage**: UTF-8

## 🏢 Structure d'un enregistrement

```json
{
  "siren": "005880596",
  "denomination": "GEDIMO HOLDING",
  "dateDepot": "2017-11-10",
  "dateCloture": "2016-12-31",
  "numChrono": "6473",
  "confidentiality": "Public",
  "typeBilan": "C",
  "bilanSaisi": {
    "bilan": {
      "identite": {
        "siren": "005880596",
        "dateClotureExercice": "2016-12-31",
        "codeGreffe": "4402",
        "codeActivite": "6420Z",
        "denomination": "GEDIMO HOLDING",
        "adresse": "44460 SAINT-NICOLAS-DE-REDON"
      },
      "detail": {
        "pages": [
          {
            "numero": 1,
            "liasses": [
              {
                "code": "AF",
                "m1": "000000000020264",
                "m2": "000000000020264"
              }
            ]
          }
        ]
      }
    }
  }
}
```

## 📋 Codes de Liasse Fiscale

Les codes de liasse correspondent aux lignes des formulaires fiscaux français (liasse fiscale Cerfa).

### Principaux codes du Bilan (Formulaire 2050/2051)

| Code | Libellé | Description |
|------|---------|-------------|
| **AF** | Capital souscrit non appelé | Actif immobilisé |
| **BB** | Total Actif Immobilisé | Somme des immobilisations |
| **BJ** | Total Actif | Total de l'actif du bilan |
| **BX** | Stocks et en-cours | Stock de marchandises |
| **BZ** | Créances clients | Créances clients et comptes rattachés |
| **CB** | Disponibilités | Trésorerie |
| **DL** | Capitaux propres | Fonds propres de l'entreprise |
| **DN** | Capital social | Capital social |
| **DT** | Résultat de l'exercice | Bénéfice ou perte de l'année |
| **EB** | Dettes financières | Emprunts et dettes financières |
| **EE** | Dettes fournisseurs | Dettes fournisseurs |

### Principaux codes du Compte de Résultat (Formulaire 2052/2053)

| Code | Libellé | Description |
|------|---------|-------------|
| **FA** | Chiffre d'affaires net | CA HT |
| **FC** | Production stockée | Variation de stock |
| **FL** | Total produits d'exploitation | Produits d'exploitation |
| **FP** | Achats consommés | Achats de marchandises |
| **FR** | Charges externes | Services extérieurs |
| **FT** | Impôts et taxes | Taxes et impôts |
| **FU** | Frais de personnel | Salaires et charges |
| **FV** | Dotations aux amortissements | Amortissements |
| **FW** | Autres charges | Autres charges d'exploitation |
| **FX** | Total charges d'exploitation | Total charges |
| **GC** | Résultat d'exploitation | Résultat opérationnel |
| **HN** | Résultat net | Résultat final (bénéfice/perte) |

### Colonnes des liasses

- **m1**: Valeur N (exercice en cours)
- **m2**: Valeur N-1 (exercice précédent)
- **m3**: Valeur brute (pour certains postes)
- **m4**: Amortissements (pour certains postes)

## 💡 Cas d'usage

### 1. Récupérer le CA d'une entreprise

```python
# Rechercher le code FA (Chiffre d'affaires)
for liasse in bilan["detail"]["pages"][0]["liasses"]:
    if liasse["code"] == "FA":
        chiffre_affaires = int(liasse["m1"])
```

### 2. Récupérer le résultat net

```python
# Rechercher le code HN (Résultat net)
for liasse in bilan["detail"]["pages"][0]["liasses"]:
    if liasse["code"] == "HN":
        resultat_net = int(liasse["m1"])
```

### 3. Récupérer l'effectif

L'effectif n'est pas dans les codes de liasse mais peut être présent dans d'autres champs.

## 🔍 Avantages du RNE vs Pappers

| Critère | RNE/INPI | Pappers |
|---------|----------|---------|
| **Source** | Données officielles | Agrégateur |
| **Coût** | Gratuit (accès FTP) | Payant (API) |
| **Historique** | Tous les bilans déposés | Limité à 10 ans |
| **Fraîcheur** | Mise à jour régulière | Temps réel |
| **Complétude** | 100% des dépôts | Dépend de la collecte |
| **Facilité** | Traitement batch | API REST simple |

## 🚀 Recommandations

1. **Télécharger le fichier complet** une fois par semaine/mois
2. **Indexer les données** dans une base locale (SQLite, PostgreSQL)
3. **Créer un index SIREN** pour recherche rapide
4. **Combiner avec l'API publique** pour les données d'identification
5. **Utiliser comme backup** quand Pappers atteint les limites

## 📝 Notes importantes

- Les montants sont en **centimes d'euros** (diviser par 100)
- Format: **15 caractères numériques avec zéros initiaux**
- Certains codes peuvent être absents si non applicable
- Le `typeBilan` peut être:
  - `C`: Consolidé
  - `S`: Social
  - `N`: Normal

## 🔗 Références

- [Documentation INPI](https://www.inpi.fr/)
- [Format de la liasse fiscale](https://www.impots.gouv.fr/)
- [Codes des formulaires Cerfa 2050-2053](https://www.impots.gouv.fr/formulaire/2050-sd/bilan-simplifie)
