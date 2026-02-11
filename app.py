"""
Streamlit app for searching French companies using MCP server.
"""
import streamlit as st
import pandas as pd
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import asynccontextmanager
from io import BytesIO

st.set_page_config(
    page_title="Recherche d'Entreprises",
    page_icon="🏢",
    layout="wide"
)

st.title("🏢 Recherche d'Entreprises Françaises")
st.markdown("Recherchez des entreprises par nom ou SIREN en utilisant le serveur MCP data.gouv.fr")


@asynccontextmanager
async def get_mcp_client():
    """Create and manage MCP client connection."""
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@datagouv/mcp-server"],
        env=None
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def search_company(session, query):
    """Search for a company by name or SIREN."""
    try:
        result = await session.call_tool(
            "search_company",
            arguments={"query": query}
        )
        
        if result.content:
            for content in result.content:
                if hasattr(content, 'text'):
                    data = json.loads(content.text)
                    return data
        return None
    except Exception as e:
        st.error(f"Erreur lors de la recherche de '{query}': {str(e)}")
        return None


async def get_company_details(session, siren):
    """Get detailed information about a company by SIREN."""
    try:
        result = await session.call_tool(
            "get_company_details",
            arguments={"siren": siren}
        )
        
        if result.content:
            for content in result.content:
                if hasattr(content, 'text'):
                    data = json.loads(content.text)
                    return data
        return None
    except Exception as e:
        st.error(f"Erreur lors de la récupération des détails pour SIREN '{siren}': {str(e)}")
        return None


def extract_company_info(company_data):
    """Extract relevant information from company data."""
    info = {
        "Nom": company_data.get("nom_complet", company_data.get("nom_raison_sociale", "N/A")),
        "SIREN": company_data.get("siren", "N/A"),
        "CA": "N/A",
        "Résultat": "N/A",
        "Clôture": "N/A"
    }
    
    # Extract financial data if available
    if "finances" in company_data:
        finances = company_data["finances"]
        if isinstance(finances, list) and len(finances) > 0:
            latest_finance = finances[0]
            info["CA"] = latest_finance.get("chiffre_affaires", "N/A")
            info["Résultat"] = latest_finance.get("resultat_exercice", "N/A")
            info["Clôture"] = latest_finance.get("date_cloture_exercice", "N/A")
    
    return info


async def process_companies(queries):
    """Process multiple company queries."""
    results = []
    
    async with get_mcp_client() as session:
        for query in queries:
            query = query.strip()
            if not query:
                continue
            
            with st.spinner(f"Recherche de '{query}'..."):
                # Check if query is a SIREN (9 digits)
                if query.isdigit() and len(query) == 9:
                    # Direct SIREN lookup
                    details = await get_company_details(session, query)
                    if details:
                        info = extract_company_info(details)
                        results.append(info)
                else:
                    # Search by name first
                    search_results = await search_company(session, query)
                    if search_results and isinstance(search_results, list) and len(search_results) > 0:
                        # Get the first result's SIREN
                        first_result = search_results[0]
                        siren = first_result.get("siren")
                        
                        if siren:
                            # Get detailed information
                            details = await get_company_details(session, siren)
                            if details:
                                info = extract_company_info(details)
                                results.append(info)
                        else:
                            # Use basic info from search
                            info = extract_company_info(first_result)
                            results.append(info)
    
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
                results = asyncio.run(process_companies(queries))
            
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
    443061841
    Total Energies
    ```
    """)
    
    st.markdown("### 📊 Données extraites")
    st.markdown("""
    - Nom de l'entreprise
    - Numéro SIREN
    - Chiffre d'affaires (CA)
    - Résultat d'exercice
    - Date de clôture
    """)
