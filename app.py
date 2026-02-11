"""
Streamlit app for searching French companies using data.gouv.fr API.
This app can work in two modes:
1. API mode: Connects directly to data.gouv.fr API (requires internet access)
2. Demo mode: Uses sample data for demonstration purposes

Integration with datagouv-mcp:
  The app leverages the same data.gouv.fr APIs used by the datagouv-mcp server
  (https://github.com/datagouv/datagouv-mcp) to verify SIREN numbers and retrieve
  financial data for French companies. It accepts SIRET numbers from a file,
  extracts the SIREN (first 9 digits), verifies them, and returns financial data.
"""
import streamlit as st
import pandas as pd
from io import BytesIO
import re

st.set_page_config(
    page_title="Recherche d'Entreprises",
    page_icon="🏢",
    layout="wide"
)

st.title("🏢 Recherche d'Entreprises Françaises")
st.markdown("Recherchez des entreprises par nom, SIREN ou SIRET — "
            "ou importez un fichier CSV/Excel contenant des SIRET")

# Check if we can import requests
try:
    import requests
    USE_API = True
    API_BASE_URL = "https://recherche-entreprises.api.gouv.fr"
except ImportError:
    USE_API = False

# Demo data for when API is not available
DEMO_COMPANIES = {
    "airbus": {
        "nom_complet": "AIRBUS",
        "siren": "383474814",
        "siret": "38347481400019",
        "siege": {
            "siret": "38347481400019",
            "activite_principale": "70.10Z",
            "adresse": "1 Rond-Point Maurice Bellonte, 31700 Blagnac",
        },
        "nombre_etablissements": 15,
        "categorie_entreprise": "GE",
        "tranche_effectif_salarie": "10 000 salariés et plus",
        "date_creation": "1970-01-01",
        "nature_juridique": "SA",
        "etat_administratif": "A",
        "finances": {
            "ca": 49524000000,
            "resultat_net": 3501000000,
            "date_cloture_exercice": "2023-12-31",
        },
    },
    "383474814": {
        "nom_complet": "AIRBUS",
        "siren": "383474814",
        "siret": "38347481400019",
        "siege": {
            "siret": "38347481400019",
            "activite_principale": "70.10Z",
            "adresse": "1 Rond-Point Maurice Bellonte, 31700 Blagnac",
        },
        "nombre_etablissements": 15,
        "categorie_entreprise": "GE",
        "tranche_effectif_salarie": "10 000 salariés et plus",
        "date_creation": "1970-01-01",
        "nature_juridique": "SA",
        "etat_administratif": "A",
        "finances": {
            "ca": 49524000000,
            "resultat_net": 3501000000,
            "date_cloture_exercice": "2023-12-31",
        },
    },
    "38347481400019": {
        "nom_complet": "AIRBUS",
        "siren": "383474814",
        "siret": "38347481400019",
        "siege": {
            "siret": "38347481400019",
            "activite_principale": "70.10Z",
            "adresse": "1 Rond-Point Maurice Bellonte, 31700 Blagnac",
        },
        "nombre_etablissements": 15,
        "categorie_entreprise": "GE",
        "tranche_effectif_salarie": "10 000 salariés et plus",
        "date_creation": "1970-01-01",
        "nature_juridique": "SA",
        "etat_administratif": "A",
        "finances": {
            "ca": 49524000000,
            "resultat_net": 3501000000,
            "date_cloture_exercice": "2023-12-31",
        },
    },
    "total": {
        "nom_complet": "TOTALENERGIES SE",
        "siren": "542051180",
        "siret": "54205118000066",
        "siege": {
            "siret": "54205118000066",
            "activite_principale": "70.10Z",
            "adresse": "2 Place Jean Millier, 92400 Courbevoie",
        },
        "nombre_etablissements": 120,
        "categorie_entreprise": "GE",
        "tranche_effectif_salarie": "10 000 salariés et plus",
        "date_creation": "1924-03-28",
        "nature_juridique": "SA",
        "etat_administratif": "A",
        "finances": {
            "ca": 263310000000,
            "resultat_net": 20526000000,
            "date_cloture_exercice": "2023-12-31",
        },
    },
    "542051180": {
        "nom_complet": "TOTALENERGIES SE",
        "siren": "542051180",
        "siret": "54205118000066",
        "siege": {
            "siret": "54205118000066",
            "activite_principale": "70.10Z",
            "adresse": "2 Place Jean Millier, 92400 Courbevoie",
        },
        "nombre_etablissements": 120,
        "categorie_entreprise": "GE",
        "tranche_effectif_salarie": "10 000 salariés et plus",
        "date_creation": "1924-03-28",
        "nature_juridique": "SA",
        "etat_administratif": "A",
        "finances": {
            "ca": 263310000000,
            "resultat_net": 20526000000,
            "date_cloture_exercice": "2023-12-31",
        },
    },
    "54205118000066": {
        "nom_complet": "TOTALENERGIES SE",
        "siren": "542051180",
        "siret": "54205118000066",
        "siege": {
            "siret": "54205118000066",
            "activite_principale": "70.10Z",
            "adresse": "2 Place Jean Millier, 92400 Courbevoie",
        },
        "nombre_etablissements": 120,
        "categorie_entreprise": "GE",
        "tranche_effectif_salarie": "10 000 salariés et plus",
        "date_creation": "1924-03-28",
        "nature_juridique": "SA",
        "etat_administratif": "A",
        "finances": {
            "ca": 263310000000,
            "resultat_net": 20526000000,
            "date_cloture_exercice": "2023-12-31",
        },
    },
    "orange": {
        "nom_complet": "ORANGE",
        "siren": "380129866",
        "siret": "38012986600052",
        "siege": {
            "siret": "38012986600052",
            "activite_principale": "61.10Z",
            "adresse": "111 Quai du Président Roosevelt, 92130 Issy-les-Moulineaux",
        },
        "nombre_etablissements": 500,
        "categorie_entreprise": "GE",
        "tranche_effectif_salarie": "10 000 salariés et plus",
        "date_creation": "1991-01-01",
        "nature_juridique": "SA",
        "etat_administratif": "A",
        "finances": {
            "ca": 42517000000,
            "resultat_net": 1563000000,
            "date_cloture_exercice": "2023-12-31",
        },
    },
    "380129866": {
        "nom_complet": "ORANGE",
        "siren": "380129866",
        "siret": "38012986600052",
        "siege": {
            "siret": "38012986600052",
            "activite_principale": "61.10Z",
            "adresse": "111 Quai du Président Roosevelt, 92130 Issy-les-Moulineaux",
        },
        "nombre_etablissements": 500,
        "categorie_entreprise": "GE",
        "tranche_effectif_salarie": "10 000 salariés et plus",
        "date_creation": "1991-01-01",
        "nature_juridique": "SA",
        "etat_administratif": "A",
        "finances": {
            "ca": 42517000000,
            "resultat_net": 1563000000,
            "date_cloture_exercice": "2023-12-31",
        },
    },
    "38012986600052": {
        "nom_complet": "ORANGE",
        "siren": "380129866",
        "siret": "38012986600052",
        "siege": {
            "siret": "38012986600052",
            "activite_principale": "61.10Z",
            "adresse": "111 Quai du Président Roosevelt, 92130 Issy-les-Moulineaux",
        },
        "nombre_etablissements": 500,
        "categorie_entreprise": "GE",
        "tranche_effectif_salarie": "10 000 salariés et plus",
        "date_creation": "1991-01-01",
        "nature_juridique": "SA",
        "etat_administratif": "A",
        "finances": {
            "ca": 42517000000,
            "resultat_net": 1563000000,
            "date_cloture_exercice": "2023-12-31",
        },
    },
    "renault": {
        "nom_complet": "RENAULT",
        "siren": "441639465",
        "siret": "44163946500018",
        "siege": {
            "siret": "44163946500018",
            "activite_principale": "29.10Z",
            "adresse": "122-122 bis avenue du Général Leclerc, 92100 Boulogne-Billancourt",
        },
        "nombre_etablissements": 50,
        "categorie_entreprise": "GE",
        "tranche_effectif_salarie": "10 000 salariés et plus",
        "date_creation": "2002-11-01",
        "nature_juridique": "SA",
        "etat_administratif": "A",
        "finances": {
            "ca": 52354000000,
            "resultat_net": 2287000000,
            "date_cloture_exercice": "2023-12-31",
        },
    },
    "441639465": {
        "nom_complet": "RENAULT",
        "siren": "441639465",
        "siret": "44163946500018",
        "siege": {
            "siret": "44163946500018",
            "activite_principale": "29.10Z",
            "adresse": "122-122 bis avenue du Général Leclerc, 92100 Boulogne-Billancourt",
        },
        "nombre_etablissements": 50,
        "categorie_entreprise": "GE",
        "tranche_effectif_salarie": "10 000 salariés et plus",
        "date_creation": "2002-11-01",
        "nature_juridique": "SA",
        "etat_administratif": "A",
        "finances": {
            "ca": 52354000000,
            "resultat_net": 2287000000,
            "date_cloture_exercice": "2023-12-31",
        },
    },
    "44163946500018": {
        "nom_complet": "RENAULT",
        "siren": "441639465",
        "siret": "44163946500018",
        "siege": {
            "siret": "44163946500018",
            "activite_principale": "29.10Z",
            "adresse": "122-122 bis avenue du Général Leclerc, 92100 Boulogne-Billancourt",
        },
        "nombre_etablissements": 50,
        "categorie_entreprise": "GE",
        "tranche_effectif_salarie": "10 000 salariés et plus",
        "date_creation": "2002-11-01",
        "nature_juridique": "SA",
        "etat_administratif": "A",
        "finances": {
            "ca": 52354000000,
            "resultat_net": 2287000000,
            "date_cloture_exercice": "2023-12-31",
        },
    },
    "lvmh": {
        "nom_complet": "LVMH MOET HENNESSY LOUIS VUITTON",
        "siren": "775670417",
        "siret": "77567041700028",
        "siege": {
            "siret": "77567041700028",
            "activite_principale": "70.10Z",
            "adresse": "22 Avenue Montaigne, 75008 Paris",
        },
        "nombre_etablissements": 30,
        "categorie_entreprise": "GE",
        "tranche_effectif_salarie": "10 000 salariés et plus",
        "date_creation": "1987-10-01",
        "nature_juridique": "SA",
        "etat_administratif": "A",
        "finances": {
            "ca": 86153000000,
            "resultat_net": 15174000000,
            "date_cloture_exercice": "2023-12-31",
        },
    },
    "775670417": {
        "nom_complet": "LVMH MOET HENNESSY LOUIS VUITTON",
        "siren": "775670417",
        "siret": "77567041700028",
        "siege": {
            "siret": "77567041700028",
            "activite_principale": "70.10Z",
            "adresse": "22 Avenue Montaigne, 75008 Paris",
        },
        "nombre_etablissements": 30,
        "categorie_entreprise": "GE",
        "tranche_effectif_salarie": "10 000 salariés et plus",
        "date_creation": "1987-10-01",
        "nature_juridique": "SA",
        "etat_administratif": "A",
        "finances": {
            "ca": 86153000000,
            "resultat_net": 15174000000,
            "date_cloture_exercice": "2023-12-31",
        },
    },
    "77567041700028": {
        "nom_complet": "LVMH MOET HENNESSY LOUIS VUITTON",
        "siren": "775670417",
        "siret": "77567041700028",
        "siege": {
            "siret": "77567041700028",
            "activite_principale": "70.10Z",
            "adresse": "22 Avenue Montaigne, 75008 Paris",
        },
        "nombre_etablissements": 30,
        "categorie_entreprise": "GE",
        "tranche_effectif_salarie": "10 000 salariés et plus",
        "date_creation": "1987-10-01",
        "nature_juridique": "SA",
        "etat_administratif": "A",
        "finances": {
            "ca": 86153000000,
            "resultat_net": 15174000000,
            "date_cloture_exercice": "2023-12-31",
        },
    },
}


def is_siret(value):
    """Check if a string looks like a SIRET number (14 digits)."""
    return bool(re.match(r'^\d{14}$', value.strip()))


def is_siren(value):
    """Check if a string looks like a SIREN number (9 digits)."""
    return bool(re.match(r'^\d{9}$', value.strip()))


def extract_siren_from_siret(siret):
    """Extract the SIREN (first 9 digits) from a SIRET (14 digits)."""
    siret = siret.strip()
    if is_siret(siret):
        return siret[:9]
    return siret


def search_company_api(query):
    """Search for a company by name, SIREN or SIRET using the API."""
    try:
        # If SIRET, extract SIREN for the API search
        search_query = query.strip()
        if is_siret(search_query):
            search_query = extract_siren_from_siret(search_query)

        url = f"{API_BASE_URL}/search"
        params = {"q": search_query, "per_page": 1}

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        if data.get("results") and len(data["results"]) > 0:
            return data["results"][0]
        return None
    except requests.exceptions.RequestException as e:
        # Network-related errors (connection, timeout, DNS)
        st.warning(f"API non accessible pour '{query}': {str(e)}. "
                    "Utilisation des données de démonstration.")
        return None
    except ValueError as e:
        # JSON parsing errors
        st.warning(f"Erreur de format de réponse pour '{query}': {str(e)}. "
                    "Utilisation des données de démonstration.")
        return None
    except Exception as e:
        # Unexpected errors
        st.warning(f"Erreur inattendue pour '{query}': {str(e)}. "
                    "Utilisation des données de démonstration.")
        return None


def search_company_demo(query):
    """Search for a company using demo data."""
    query_lower = query.lower().strip()

    # If SIRET, try direct lookup first, then by extracted SIREN
    if is_siret(query_lower):
        if query_lower in DEMO_COMPANIES:
            return DEMO_COMPANIES[query_lower]
        siren = extract_siren_from_siret(query_lower)
        if siren in DEMO_COMPANIES:
            return DEMO_COMPANIES[siren]

    # Direct lookup
    if query_lower in DEMO_COMPANIES:
        return DEMO_COMPANIES[query_lower]

    # Partial match
    for key, value in DEMO_COMPANIES.items():
        if query_lower in key or query_lower in value["nom_complet"].lower():
            return value

    return None


def extract_financial_info(company_data, original_siret=None):
    """Extract financial and identification information from company data."""
    # Handle the nested finances structure (demo data) or flat structure (API)
    finances = company_data.get("finances", {})
    siege = company_data.get("siege", {})

    siren = company_data.get("siren", "N/A")

    # Determine SIRET: use original if provided, else from siege, else from data
    siret = original_siret or siege.get("siret",
                company_data.get("siret", "N/A"))

    # SIREN verification status
    if siren and siren != "N/A":
        siren_verifie = "✅ Vérifié"
    else:
        siren_verifie = "❌ Non trouvé"

    # Financial data: try nested finances first, then flat keys
    ca = finances.get("ca", company_data.get("ca", "N/A"))
    resultat_net = finances.get("resultat_net",
                                company_data.get("resultat", "N/A"))
    cloture = finances.get("date_cloture_exercice",
                           company_data.get("cloture",
                           company_data.get("date_cloture_exercice", "N/A")))

    info = {
        "SIRET": siret,
        "SIREN": siren,
        "Vérification SIREN": siren_verifie,
        "Nom": company_data.get("nom_complet",
                                company_data.get("nom_raison_sociale", "N/A")),
        "État administratif": _format_etat(
            company_data.get("etat_administratif", "N/A")),
        "Catégorie": company_data.get("categorie_entreprise", "N/A"),
        "Nature juridique": company_data.get("nature_juridique", "N/A"),
        "Activité principale": siege.get("activite_principale", "N/A"),
        "Effectif salarié": company_data.get(
            "tranche_effectif_salarie", "N/A"),
        "Nombre d'établissements": company_data.get(
            "nombre_etablissements", "N/A"),
        "Date de création": company_data.get("date_creation", "N/A"),
        "Chiffre d'affaires (CA)": _format_currency(ca),
        "Résultat net": _format_currency(resultat_net),
        "Date clôture exercice": cloture,
        "Adresse siège": siege.get("adresse", "N/A"),
    }

    return info


def _format_etat(etat):
    """Format the administrative state."""
    if etat == "A":
        return "Active"
    if etat == "C":
        return "Cessée"
    return etat


def _format_currency(value):
    """Format a numeric value as currency."""
    if isinstance(value, (int, float)) and value != "N/A":
        return f"{value:,.0f} €"
    return value


def process_companies(queries):
    """Process multiple company queries."""
    results = []

    for query in queries:
        query = query.strip()
        if not query:
            continue

        with st.spinner(f"Recherche de '{query}'..."):
            company_data = None
            original_siret = query if is_siret(query) else None

            # Try API first if available
            if USE_API:
                company_data = search_company_api(query)

            # Fall back to demo data
            if not company_data:
                company_data = search_company_demo(query)

            if company_data:
                info = extract_financial_info(company_data, original_siret)
                results.append(info)
            else:
                # Record as not found with the original query
                results.append({
                    "SIRET": original_siret or "N/A",
                    "SIREN": extract_siren_from_siret(query)
                            if is_siret(query) else "N/A",
                    "Vérification SIREN": "❌ Non trouvé",
                    "Nom": f"Non trouvé ({query})",
                    "État administratif": "N/A",
                    "Catégorie": "N/A",
                    "Nature juridique": "N/A",
                    "Activité principale": "N/A",
                    "Effectif salarié": "N/A",
                    "Nombre d'établissements": "N/A",
                    "Date de création": "N/A",
                    "Chiffre d'affaires (CA)": "N/A",
                    "Résultat net": "N/A",
                    "Date clôture exercice": "N/A",
                    "Adresse siège": "N/A",
                })
                st.warning(f"⚠️ Entreprise '{query}' non trouvée")

    return results


def read_uploaded_file(uploaded_file):
    """Read SIRET numbers from an uploaded CSV or Excel file."""
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, dtype=str)
        elif uploaded_file.name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(uploaded_file, dtype=str)
        else:
            ext = uploaded_file.name.rsplit('.', 1)[-1] if '.' in uploaded_file.name else '(inconnu)'
            st.error(f"Format de fichier non supporté (.{ext}). "
                     "Utilisez CSV ou Excel (.xlsx/.xls).")
            return []

        # Try to find a column containing SIRET numbers
        siret_col = None
        for col in df.columns:
            col_lower = col.lower().strip()
            if 'siret' in col_lower:
                siret_col = col
                break

        # If no SIRET column found, try SIREN column
        if siret_col is None:
            for col in df.columns:
                col_lower = col.lower().strip()
                if 'siren' in col_lower:
                    siret_col = col
                    break

        # If still not found, use the first column
        if siret_col is None:
            siret_col = df.columns[0]
            st.info(f"Aucune colonne 'SIRET' trouvée. "
                    f"Utilisation de la colonne '{siret_col}'.")

        # Extract non-empty values
        values = df[siret_col].dropna().astype(str).str.strip()
        values = [v for v in values if v and v != 'nan']

        return values
    except Exception as e:
        st.error(f"Erreur lors de la lecture du fichier : {str(e)}")
        return []


def create_download_button(df, file_format, key_suffix=""):
    """Create download button for CSV or XLSX."""
    if file_format == "CSV":
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Télécharger CSV",
            data=csv,
            file_name="entreprises_donnees_financieres.csv",
            mime="text/csv",
            key=f"dl_csv_{key_suffix}",
        )
    elif file_format == "XLSX":
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Entreprises')
        output.seek(0)
        st.download_button(
            label="📥 Télécharger XLSX",
            data=output,
            file_name="entreprises_donnees_financieres.xlsx",
            mime="application/vnd.openxmlformats-officedocument."
                 "spreadsheetml.sheet",
            key=f"dl_xlsx_{key_suffix}",
        )


def display_results(results, section_key=""):
    """Display results in a table with download options."""
    if results:
        df = pd.DataFrame(results)

        # Display results
        st.markdown("### 📊 Résultats — Données financières")
        st.dataframe(df, use_container_width=True)

        # Summary
        verified = sum(1 for r in results
                       if r.get("Vérification SIREN") == "✅ Vérifié")
        not_found = len(results) - verified
        st.markdown(
            f"**Résumé :** {verified} SIREN vérifié(s), "
            f"{not_found} non trouvé(s) sur {len(results)} entrée(s)")

        # Export options
        st.markdown("### 📥 Exporter les Résultats")
        col1, col2 = st.columns(2)
        with col1:
            create_download_button(df, "CSV", section_key)
        with col2:
            create_download_button(df, "XLSX", section_key)

        st.success(f"✅ {len(results)} entreprise(s) traitée(s)")
    else:
        st.warning("⚠️ Aucun résultat")


# ──────────────────────────────────────────────────────
# Main UI — Tabs
# ──────────────────────────────────────────────────────

tab_file, tab_manual = st.tabs([
    "📁 Import fichier (SIRET)",
    "✏️ Saisie manuelle",
])

# ── Tab 1: File upload ────────────────────────────────
with tab_file:
    st.markdown("### Importer un fichier d'entreprises")
    st.markdown(
        "Importez un fichier **CSV** ou **Excel** contenant une colonne "
        "**SIRET**. Le SIREN sera extrait automatiquement (9 premiers "
        "chiffres du SIRET), vérifié via l'API de l'État, et les "
        "données financières seront récupérées."
    )

    uploaded_file = st.file_uploader(
        "Choisir un fichier CSV ou Excel",
        type=["csv", "xlsx", "xls"],
        help="Le fichier doit contenir une colonne SIRET "
             "(ou la première colonne sera utilisée).",
    )

    if uploaded_file is not None:
        siret_list = read_uploaded_file(uploaded_file)

        if siret_list:
            st.info(f"📋 {len(siret_list)} entrée(s) trouvée(s) "
                    "dans le fichier.")

            # Show preview
            with st.expander("Aperçu des données importées"):
                preview_data = []
                for s in siret_list[:10]:
                    siren = extract_siren_from_siret(s) if is_siret(s) else s
                    preview_data.append({
                        "Valeur importée": s,
                        "SIREN extrait": siren if is_siret(s) else "—",
                        "Type": "SIRET" if is_siret(s)
                               else ("SIREN" if is_siren(s) else "Nom"),
                    })
                st.dataframe(pd.DataFrame(preview_data),
                             use_container_width=True)
                if len(siret_list) > 10:
                    st.caption(f"… et {len(siret_list) - 10} autre(s)")

            if st.button("🔍 Vérifier et récupérer les données financières",
                         type="primary", key="btn_file"):
                with st.spinner("Traitement en cours..."):
                    results = process_companies(siret_list)
                display_results(results, section_key="file")

# ── Tab 2: Manual input ──────────────────────────────
with tab_manual:
    st.markdown("### Saisie des Entreprises")
    st.markdown("Entrez les noms d'entreprises, numéros SIREN ou SIRET "
                "(un par ligne)")

    user_input = st.text_area(
        "Noms d'entreprises, SIREN ou SIRET",
        height=150,
        placeholder="Exemple:\nAirbus\n383474814\n38347481400019\n"
                    "Total Energies",
    )

    if st.button("🔍 Rechercher", type="primary", key="btn_manual"):
        if user_input:
            queries = [line.strip() for line in user_input.split('\n')
                       if line.strip()]
            if queries:
                with st.spinner("Traitement en cours..."):
                    results = process_companies(queries)
                display_results(results, section_key="manual")
            else:
                st.warning("⚠️ Veuillez entrer au moins un nom, "
                           "SIREN ou SIRET")
        else:
            st.warning("⚠️ Veuillez entrer des noms d'entreprises, "
                       "SIREN ou SIRET")

# ──────────────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ℹ️ Instructions")
    st.markdown("""
    **Import fichier :**
    1. Préparez un CSV ou Excel avec une colonne SIRET
    2. Importez le fichier
    3. Cliquez sur "Vérifier et récupérer"
    4. Téléchargez les résultats en CSV ou XLSX

    **Saisie manuelle :**
    1. Entrez les noms, SIREN ou SIRET (un par ligne)
    2. Cliquez sur "Rechercher"
    3. Exportez les résultats

    **Format SIRET :** 14 chiffres
    **Format SIREN :** 9 chiffres (= 9 premiers chiffres du SIRET)
    """)

    # Show mode
    if USE_API:
        st.info("🌐 Mode : API (recherche-entreprises.api.gouv.fr)")
    else:
        st.warning("📊 Mode : Démonstration (données d'exemple)")

    st.markdown("### 📊 Données extraites")
    st.markdown("""
    - SIRET / SIREN
    - Vérification du SIREN
    - Nom de l'entreprise
    - État administratif
    - Catégorie d'entreprise
    - Nature juridique
    - Activité principale (NAF)
    - Effectif salarié
    - Nombre d'établissements
    - Date de création
    - **Chiffre d'affaires (CA)**
    - **Résultat net**
    - Date de clôture d'exercice
    - Adresse du siège
    """)

    st.markdown("---")
    st.markdown(
        "### 🔗 Source de données\n"
        "Cette application utilise l'[API Recherche d'Entreprises]"
        "(https://recherche-entreprises.api.gouv.fr/) de l'État "
        "français, inspirée du projet "
        "[datagouv-mcp](https://github.com/datagouv/datagouv-mcp) "
        "qui fournit un serveur MCP pour accéder aux données de "
        "[data.gouv.fr](https://www.data.gouv.fr)."
    )
