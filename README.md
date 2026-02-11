# TestsMCP
un repo pour les requêtes ponctuelles osint

## 🏢 Application de Recherche d'Entreprises

Application Streamlit pour rechercher des entreprises françaises via l'API officielle de l'État, inspirée du projet [datagouv-mcp](https://github.com/datagouv/datagouv-mcp).

### Fonctionnalités

- **Import fichier** : importez un fichier CSV ou Excel contenant des SIRET pour vérifier les SIREN et récupérer les données financières en lot
- **Saisie manuelle** : recherche d'entreprises par nom, numéro SIREN ou SIRET
- Extraction automatique du SIREN depuis le SIRET (9 premiers chiffres)
- Vérification du SIREN via l'API de l'État
- Récupération des données financières (CA, résultat net, date de clôture)
- Données d'identification complètes (état administratif, catégorie, activité NAF, effectifs, etc.)
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

### Format des données

- **Entrée (fichier)** : fichier CSV ou Excel avec une colonne SIRET (14 chiffres)
- **Entrée (manuelle)** : noms d'entreprises, SIREN (9 chiffres) ou SIRET (14 chiffres), un par ligne
- **Sortie** : tableau avec SIRET, SIREN, statut de vérification, nom, état administratif, catégorie, nature juridique, activité principale, effectif salarié, nombre d'établissements, date de création, CA, résultat net, date de clôture, adresse du siège
- **Export** : CSV ou XLSX

### API utilisée

Cette application utilise l'[API Recherche d'Entreprises](https://recherche-entreprises.api.gouv.fr/) de l'État français pour vérifier les SIREN et récupérer les données financières.

### Intégration datagouv-mcp

Ce projet s'inspire du serveur MCP [datagouv-mcp](https://github.com/datagouv/datagouv-mcp) qui permet aux chatbots IA d'interroger les données de [data.gouv.fr](https://www.data.gouv.fr). L'application utilise les mêmes API gouvernementales pour la vérification des SIREN et la récupération des données financières des entreprises françaises.
