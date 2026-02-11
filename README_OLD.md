# TestsMCP
un repo pour les requêtes ponctuelles osint

## 🏢 Application de Recherche d'Entreprises

Application Streamlit pour rechercher des entreprises françaises via l'API officielle de l'État, inspirée du projet [datagouv-mcp](https://github.com/datagouv/datagouv-mcp).

### 🔑 Aucune authentification requise !

L'API Recherche d'Entreprises est **100% publique et gratuite** - aucune clé API nécessaire.

### ⚠️ Données réelles uniquement

L'application utilise **UNIQUEMENT des données réelles** de l'API officielle. Si une entreprise n'est pas trouvée ou si l'API est indisponible, le résultat sera marqué comme "Non trouvé" ou "Erreur". **Aucune donnée de démonstration ou fictive n'est utilisée**.

### Fonctionnalités

- **🔍 Recherche par nom** (recommandé) : entrez simplement les noms d'entreprises
- **Import fichier optimisé** : 
  - Format optimal : 2 colonnes (Nom + SIRET/SIREN)
  - Format simple : 1 colonne (Noms ou SIRET/SIREN)
- **Recherche flexible** : par nom, SIRET (14 chiffres) ou SIREN (9 chiffres)
- **Rate limiting intelligent** : respect automatique des limites API (~250 req/min) avec marge de sécurité de 10%
- **Données enrichies** :
  - ✅ Identification complète (SIREN, SIRET, nom, sigle)
  - ✅ Données financières (CA, résultat net avec année)
  - ✅ Localisation précise (adresse, GPS, département, région)
  - ✅ **Dirigeants et direction** (noms, fonctions, commissaires aux comptes)
  - ✅ **Certifications et labels** (Qualiopi, RGE, Bio, ESS, Société à mission)
  - ✅ Conventions collectives (IDCC)
  - ✅ Effectifs et établissements
- Affichage des résultats dans un tableau interactif
- **Export des données en CSV ou XLSX** (livrable final)

### Utilisation dans Codespaces

1. Ouvrez ce repository dans GitHub Codespaces
2. Le conteneur de développement installera automatiquement les dépendances
3. Lancez l'application :
   ```bash
   streamlit run app.py
   ```
4. Accédez à l'application via le port 8501

### Utilisation en local

1. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```

2. Lancez l'application :
   ```bash
   streamlit run app.py
   ```

3. Testez avec les fichiers d'exemple :
   - `exemple_fichier_optimal.csv` : format avec 2 colonnes (Nom + SIRET)
   - `exemple_fichier_simple.csv` : format avec 1 colonne (Noms uniquement)

### Format des données

**Entrée (fichier CSV/Excel) - Format recommandé :**
```csv
Nom,SIRET
Airbus,38347481400019
Total Energies,54205118000066
Orange,38012986600052
```

**Entrée (fichier CSV/Excel) - Format simple :**
```csv
Nom
Airbus
Total Energies
Orange
```

**Sortie - Données enrichies (35+ colonnes) :**
- Identification : SIRET, SIREN, Nom, Sigle, Vérification
- Structure : État, Catégorie, Nature juridique, Date création
- Activité : NAF, Effectifs, Établissements
- Finances : Année, CA, Résultat net
- Localisation : Adresse, Code postal, Commune, Département, Région, GPS
- **Dirigeants** : Liste nominative avec fonctions
- **Certifications** : Qualiopi, RGE, Bio, ESS, etc.
- **Conventions collectives** : IDCC
- Autres : Organisme de formation, Entrepreneur spectacle

**Export** : CSV ou XLSX avec toutes les données

### ⚡ Rate Limiting

L'application respecte automatiquement les limites de l'API (~250 requêtes/minute) avec une **marge de sécurité de 50%**, soit environ 2 requêtes par seconde maximum (délai de 0.5s entre chaque requête).

**Gestion intelligente des erreurs 429 :**
- Retry automatique avec backoff exponentiel (1s, 2s, 4s...)
- Jusqu'à 3 tentatives par requête
- Marqué comme "Non trouvé" si toutes les tentatives échouent

Pour les gros fichiers, le temps de traitement sera indiqué.

### API utilisée

Cette application utilise l'[API Recherche d'Entreprises](https://recherche-entreprises.api.gouv.fr/) de l'État français pour vérifier les SIREN et récupérer les données financières.

### Intégration datagouv-mcp

Ce projet s'inspire du serveur MCP [datagouv-mcp](https://github.com/datagouv/datagouv-mcp) qui permet aux chatbots IA d'interroger les données de [data.gouv.fr](https://www.data.gouv.fr). L'application utilise les mêmes API gouvernementales pour la vérification des SIREN et la récupération des données financières des entreprises françaises.
