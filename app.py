"""
Streamlit app for searching French companies using data.gouv.fr API.
This app can work in two modes:
1. API mode: Connects directly to data.gouv.fr API (requires internet access)
2. Demo mode: Uses sample data for demonstration purposes
"""
import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(
    page_title="Recherche d'Entreprises",
    page_icon="🏢",
    layout="wide"
)

st.title("🏢 Recherche d'Entreprises Françaises")
st.markdown("Recherchez des entreprises par nom ou SIREN")

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
        "ca": 49524000000,
        "resultat": 3501000000,
        "cloture": "2023-12-31"
    },
    "383474814": {
        "nom_complet": "AIRBUS",
        "siren": "383474814",
        "ca": 49524000000,
        "resultat": 3501000000,
        "cloture": "2023-12-31"
    },
    "total": {
        "nom_complet": "TOTALENERGIES SE",
        "siren": "542051180",
        "ca": 263310000000,
        "resultat": 20526000000,
        "cloture": "2023-12-31"
    },
    "542051180": {
        "nom_complet": "TOTALENERGIES SE",
        "siren": "542051180",
        "ca": 263310000000,
        "resultat": 20526000000,
        "cloture": "2023-12-31"
    },
    "orange": {
        "nom_complet": "ORANGE",
        "siren": "380129866",
        "ca": 42517000000,
        "resultat": 1563000000,
        "cloture": "2023-12-31"
    },
    "380129866": {
        "nom_complet": "ORANGE",
        "siren": "380129866",
        "ca": 42517000000,
        "resultat": 1563000000,
        "cloture": "2023-12-31"
    },
    "renault": {
        "nom_complet": "RENAULT",
        "siren": "441639465",
        "ca": 52354000000,
        "resultat": 2287000000,
        "cloture": "2023-12-31"
    },
    "441639465": {
        "nom_complet": "RENAULT",
        "siren": "441639465",
        "ca": 52354000000,
        "resultat": 2287000000,
        "cloture": "2023-12-31"
    },
    "lvmh": {
        "nom_complet": "LVMH MOET HENNESSY LOUIS VUITTON",
        "siren": "775670417",
        "ca": 86153000000,
        "resultat": 15174000000,
        "cloture": "2023-12-31"
    },
    "775670417": {
        "nom_complet": "LVMH MOET HENNESSY LOUIS VUITTON",
        "siren": "775670417",
        "ca": 86153000000,
        "resultat": 15174000000,
        "cloture": "2023-12-31"
    }
}


def search_company_api(query):
    """Search for a company by name or SIREN using the API."""
    try:
        url = f"{API_BASE_URL}/search"
        params = {"q": query, "per_page": 1}
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if data.get("results") and len(data["results"]) > 0:
            return data["results"][0]
        return None
    except requests.exceptions.RequestException as e:
        # Network-related errors (connection, timeout, DNS)
        st.warning(f"API non accessible pour '{query}': {str(e)}. Utilisation des données de démonstration.")
        return None
    except ValueError as e:
        # JSON parsing errors
        st.warning(f"Erreur de format de réponse pour '{query}': {str(e)}. Utilisation des données de démonstration.")
        return None
    except Exception as e:
        # Unexpected errors
        st.warning(f"Erreur inattendue pour '{query}': {str(e)}. Utilisation des données de démonstration.")
        return None


def search_company_demo(query):
    """Search for a company using demo data."""
    query_lower = query.lower().strip()
    
    # Direct lookup
    if query_lower in DEMO_COMPANIES:
        return DEMO_COMPANIES[query_lower]
    
    # Partial match
    for key, value in DEMO_COMPANIES.items():
        if query_lower in key or query_lower in value["nom_complet"].lower():
            return value
    
    return None


def extract_company_info(company_data):
    """Extract relevant information from company data."""
    # Handle both API format and demo format
    info = {
        "Nom": company_data.get("nom_complet", company_data.get("nom_raison_sociale", "N/A")),
        "SIREN": company_data.get("siren", "N/A"),
        "CA": company_data.get("ca", "N/A"),
        "Résultat": company_data.get("resultat", "N/A"),
        "Clôture": company_data.get("cloture", company_data.get("date_cloture_exercice", "N/A"))
    }
    
    # Format numeric values for display
    if isinstance(info["CA"], (int, float)) and info["CA"] != "N/A":
        info["CA"] = f"{info['CA']:,.0f} €"
    
    if isinstance(info["Résultat"], (int, float)) and info["Résultat"] != "N/A":
        info["Résultat"] = f"{info['Résultat']:,.0f} €"
    
    return info


def process_companies(queries):
    """Process multiple company queries."""
    results = []
    
    for query in queries:
        query = query.strip()
        if not query:
            continue
        
        with st.spinner(f"Recherche de '{query}'..."):
            company_data = None
            
            # Try API first if available
            if USE_API:
                company_data = search_company_api(query)
            
            # Fall back to demo data
            if not company_data:
                company_data = search_company_demo(query)
            
            if company_data:
                info = extract_company_info(company_data)
                results.append(info)
            else:
                st.warning(f"⚠️ Entreprise '{query}' non trouvée")
    
    return results


def create_download_button(df, file_format):
    """Create download button for CSV or XLSX."""
    if file_format == "CSV":
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Télécharger CSV",
            data=csv,
            file_name="entreprises.csv",
            mime="text/csv",
        )
    elif file_format == "XLSX":
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Entreprises')
        output.seek(0)
        st.download_button(
            label="📥 Télécharger XLSX",
            data=output,
            file_name="entreprises.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


# Main UI
st.markdown("### Saisie des Entreprises")
st.markdown("Entrez les noms d'entreprises ou numéros SIREN (un par ligne)")

# Input text area
user_input = st.text_area(
    "Noms d'entreprises ou numéros SIREN",
    height=150,
    placeholder="Exemple:\nAirbus\n443061841\nTotal Energies"
)

# Search button
if st.button("🔍 Rechercher", type="primary"):
    if user_input:
        # Split input by lines
        queries = [line.strip() for line in user_input.split('\n') if line.strip()]
        
        if queries:
            # Process companies
            with st.spinner("Traitement en cours..."):
                results = process_companies(queries)
            
            if results:
                # Create DataFrame
                df = pd.DataFrame(results)
                
                # Display results
                st.markdown("### Résultats")
                st.dataframe(df, use_container_width=True)
                
                # Export options
                st.markdown("### Exporter les Résultats")
                col1, col2 = st.columns(2)
                
                with col1:
                    create_download_button(df, "CSV")
                
                with col2:
                    create_download_button(df, "XLSX")
                
                st.success(f"✅ {len(results)} entreprise(s) trouvée(s)")
            else:
                st.warning("⚠️ Aucune entreprise trouvée")
        else:
            st.warning("⚠️ Veuillez entrer au moins un nom ou SIREN")
    else:
        st.warning("⚠️ Veuillez entrer des noms d'entreprises ou numéros SIREN")

# Sidebar with instructions
with st.sidebar:
    st.markdown("### ℹ️ Instructions")
    st.markdown("""
    1. Entrez les noms d'entreprises ou numéros SIREN
    2. Un nom ou SIREN par ligne
    3. Cliquez sur "Rechercher"
    4. Exportez les résultats en CSV ou XLSX
    
    **Format SIREN:** 9 chiffres
    
    **Exemple:**
    ```
    Airbus
    LVMH
    Renault
    Orange
    Total
    ```
    """)
    
    # Show mode
    if USE_API:
        st.info("🌐 Mode: API (data.gouv.fr)")
    else:
        st.warning("📊 Mode: Démonstration (données d'exemple)")
    
    st.markdown("### 📊 Données extraites")
    st.markdown("""
    - Nom de l'entreprise
    - Numéro SIREN
    - Chiffre d'affaires (CA)
    - Résultat d'exercice
    - Date de clôture
    """)
