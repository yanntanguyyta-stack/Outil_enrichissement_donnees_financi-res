# TestsMCP
un repo pour les requêtes ponctuelles osint

## 🏢 Application de Recherche d'Entreprises

Application Streamlit pour rechercher des entreprises françaises via l'API officielle de data.gouv.fr.

### Fonctionnalités

- Recherche d'entreprises par nom ou numéro SIREN
- Extraction automatique des données d'entreprise (Nom, SIREN, informations de base)
- Affichage des résultats dans un tableau interactif
- Export des données en CSV ou XLSX

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

- **Entrée :** Noms d'entreprises ou numéros SIREN (un par ligne)
- **Sortie :** Tableau avec Nom, SIREN, CA, Résultat, Date de clôture
- **Export :** CSV ou XLSX

### API utilisée

Cette application utilise l'[API Recherche Entreprises](https://recherche-entreprises.api.gouv.fr/docs/) de data.gouv.fr pour obtenir les informations sur les entreprises françaises.
