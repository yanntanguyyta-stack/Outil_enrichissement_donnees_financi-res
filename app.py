"""
Streamlit app for searching French companies using data.gouv.fr API.

Integration with datagouv-mcp:
  The app leverages the same data.gouv.fr APIs used by the datagouv-mcp server
  (https://github.com/datagouv/datagouv-mcp) to verify SIREN numbers and retrieve
  financial data for French companies. It accepts company names, SIRET, or SIREN
  numbers from a file or manual input, verifies them, and returns financial data.

IMPORTANT: This app only uses REAL data from the official French government API.
           No demo or fake data is returned. If a company is not found or if there's
           an API error, the result will be marked as "Not found" or "Error".
"""
import streamlit as st
import pandas as pd
from io import BytesIO
import re
import time

st.set_page_config(
    page_title="Recherche d'Entreprises",
    page_icon="🏢",
    layout="wide"
)

st.title("🏢 Recherche d'Entreprises Françaises")
st.markdown("**Recherchez des entreprises par nom** — le SIRET/SIREN est optionnel pour plus de précision")
st.info("💡 **API publique et gratuite** — Aucune authentification requise ! "
        "Cette application utilise l'API ouverte de l'État français.")
st.warning("⚠️ **Données financières** : Seules 10-20% des entreprises publient leurs comptes (GE, ETI, sociétés cotées). "
           "Les PME < 50 salariés ne sont pas obligées de publier. C'est normal si beaucoup de résultats affichent 'N/A'.")

# Check if we can import requests
try:
    import requests
    USE_API = True
    API_BASE_URL = "https://recherche-entreprises.api.gouv.fr"
    # Rate limiting: API limite ~250 req/min (4.17 req/sec)
    # Avec marge de sécurité de 50%: 2 req/sec max
    # Délai entre requêtes: 1/2 = 0.5 secondes
    API_DELAY_SECONDS = 0.5  # Marge de sécurité importante pour éviter les 429
    API_MAX_RETRIES = 3  # Nombre de tentatives en cas d'erreur 429
except ImportError:
    USE_API = False
    API_DELAY_SECONDS = 0

if not USE_API:
    st.error("❌ Module 'requests' non installé. Veuillez installer les dépendances : pip install -r requirements.txt")
    st.stop()


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
    """Search for a company by name, SIREN or SIRET using the API.
    
    Includes retry logic with exponential backoff for 429 errors.
    """
    # If SIRET, extract SIREN for the API search
    search_query = query.strip()
    if is_siret(search_query):
        search_query = extract_siren_from_siret(search_query)

    url = f"{API_BASE_URL}/search"
    params = {"q": search_query, "per_page": 1}
    
    # Retry logic avec backoff exponentiel pour les erreurs 429
    for attempt in range(API_MAX_RETRIES):
        try:
            # Rate limiting: respecter le délai entre requêtes
            time.sleep(API_DELAY_SECONDS)
            
            response = requests.get(url, params=params, timeout=10)
            
            # Gestion spécifique de l'erreur 429 (Too Many Requests)
            if response.status_code == 429:
                if attempt < API_MAX_RETRIES - 1:
                    # Backoff exponentiel: 1s, 2s, 4s...
                    backoff_time = 2 ** attempt
                    st.warning(f"⏳ Limite API atteinte pour '{query}'. "
                              f"Nouvelle tentative dans {backoff_time}s... "
                              f"(tentative {attempt + 1}/{API_MAX_RETRIES})")
                    time.sleep(backoff_time)
                    continue
                else:
                    st.error(f"❌ Limite API dépassée pour '{query}' après {API_MAX_RETRIES} tentatives. "
                            "Entreprise non récupérée.")
                    return None
            
            response.raise_for_status()

            data = response.json()
            if data.get("results") and len(data["results"]) > 0:
                return data["results"][0]
            return None
            
        except requests.exceptions.HTTPError as e:
            # HTTP errors (other than 429, which is handled above)
            if attempt == API_MAX_RETRIES - 1:
                st.warning(f"⚠️ Erreur HTTP pour '{query}': {str(e)}")
            return None
        except requests.exceptions.RequestException as e:
            # Network-related errors (connection, timeout, DNS)
            if attempt == API_MAX_RETRIES - 1:
                st.warning(f"⚠️ API non accessible pour '{query}': {str(e)}")
            return None
        except ValueError as e:
            # JSON parsing errors
            st.warning(f"⚠️ Erreur de format de réponse pour '{query}': {str(e)}")
            return None
        except Exception as e:
            # Unexpected errors
            st.warning(f"⚠️ Erreur inattendue pour '{query}': {str(e)}")
            return None
    
    return None


def extract_financial_info(company_data, original_siret=None):
    """Extract comprehensive information from company data including financial, 
    legal, geographic, and leadership data."""
    
    # Base structures
    finances = company_data.get("finances") or {}
    siege = company_data.get("siege") or {}
    complements = company_data.get("complements") or {}
    dirigeants = company_data.get("dirigeants") or []
    
    siren = company_data.get("siren", "N/A")
    siret = original_siret or siege.get("siret", company_data.get("siret", "N/A"))
    
    # SIREN verification status
    siren_verifie = "✅ Vérifié" if siren and siren != "N/A" else "❌ Non trouvé"
    
    # Financial data - récupérer l'année la plus récente
    ca = "N/A"
    resultat_net = "N/A"
    annee_finance = "N/A"
    finances_publiees = "Non"
    
    if finances:
        # L'API retourne un dict avec l'année comme clé: {"2024": {"ca": ..., "resultat_net": ...}}
        latest_year = max(finances.keys()) if finances else None
        if latest_year:
            annee_finance = latest_year
            year_data = finances[latest_year]
            ca = year_data.get("ca", "N/A")
            resultat_net = year_data.get("resultat_net", "N/A")
            finances_publiees = "Oui"
    
    # Dirigeants - formater la liste
    dirigeants_str = "N/A"
    if dirigeants:
        dir_list = []
        for d in dirigeants[:5]:  # Limiter à 5 premiers
            if d.get("type_dirigeant") == "personne physique":
                nom = f"{d.get('prenoms', '')} {d.get('nom', '')}".strip()
                qualite = d.get('qualite', '')
                dir_list.append(f"{nom} ({qualite})")
            else:
                denom = d.get('denomination', '')
                qualite = d.get('qualite', '')
                dir_list.append(f"{denom} ({qualite})")
        dirigeants_str = " | ".join(dir_list)
        if len(dirigeants) > 5:
            dirigeants_str += f" | ... (+{len(dirigeants)-5})"
    
    # Coordonnées géographiques
    latitude = siege.get("latitude", "N/A")
    longitude = siege.get("longitude", "N/A")
    coords = f"{latitude}, {longitude}" if latitude != "N/A" and longitude != "N/A" else "N/A"
    
    # Certifications et labels
    certifications = []
    if complements.get("est_qualiopi"):
        certifications.append("Qualiopi")
    if complements.get("est_rge"):
        certifications.append("RGE")
    if complements.get("est_bio"):
        certifications.append("Bio")
    if complements.get("est_ess"):
        certifications.append("ESS")
    if complements.get("est_societe_mission"):
        certifications.append("Société à mission")
    if complements.get("est_service_public"):
        certifications.append("Service public")
    certifications_str = ", ".join(certifications) if certifications else "Aucune"
    
    # Conventions collectives
    idcc_list = complements.get("liste_idcc", [])
    idcc_str = ", ".join(idcc_list) if idcc_list else "N/A"
    
    info = {
        # Identification
        "SIRET": siret,
        "SIREN": siren,
        "Vérification SIREN": siren_verifie,
        "Nom": company_data.get("nom_complet", company_data.get("nom_raison_sociale", "N/A")),
        "Sigle": company_data.get("sigle", "N/A"),
        
        # État et structure
        "État administratif": _format_etat(company_data.get("etat_administratif", "N/A")),
        "Date de création": company_data.get("date_creation", "N/A"),
        "Catégorie": company_data.get("categorie_entreprise", "N/A"),
        "Nature juridique": company_data.get("nature_juridique", "N/A"),
        
        # Activité
        "Activité principale": siege.get("activite_principale", "N/A"),
        "Effectif salarié": company_data.get("tranche_effectif_salarie", "N/A"),
        "Année effectif": company_data.get("annee_tranche_effectif_salarie", "N/A"),
        "Nombre d'établissements": company_data.get("nombre_etablissements", "N/A"),
        "Établissements ouverts": company_data.get("nombre_etablissements_ouverts", "N/A"),
        
        # Finances
        "Données financières publiées": finances_publiees,
        "Année finances": annee_finance,
        "Chiffre d'affaires (CA)": _format_currency(ca),
        "Résultat net": _format_currency(resultat_net),
        
        # Localisation
        "Adresse siège": siege.get("geo_adresse", siege.get("adresse", "N/A")),
        "Code postal": siege.get("code_postal", "N/A"),
        "Commune": siege.get("libelle_commune", "N/A"),
        "Département": siege.get("departement", "N/A"),
        "Région": siege.get("region", "N/A"),
        "Coordonnées GPS": coords,
        
        # Dirigeants
        "Dirigeants": dirigeants_str,
        
        # Certifications et labels
        "Certifications": certifications_str,
        "Conventions collectives (IDCC)": idcc_str,
        
        # Compléments
        "Organisme de formation": "Oui" if complements.get("est_organisme_formation") else "Non",
        "Entrepreneur spectacle": "Oui" if complements.get("est_entrepreneur_spectacle") else "Non",
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
    """Process multiple company queries.
    
    Args:
        queries: List of strings (company names) or tuples (name, siret/siren)
    """
    results = []
    total = len(queries)
    
    # Estimation du temps si on utilise l'API
    if USE_API and total > 1:
        estimated_time = total * API_DELAY_SECONDS
        if estimated_time > 5:
            st.info(f"⏱️ Traitement de {total} entreprise(s). "
                   f"Temps estimé : ~{int(estimated_time)} secondes "
                   f"(rate limiting API respecté)")

    for idx, query_data in enumerate(queries, 1):
        # query_data peut être un string ou un tuple (nom, siret/siren)
        if isinstance(query_data, tuple):
            name, siret_siren = query_data
            # Utiliser le SIRET/SIREN en priorité s'il existe
            query = siret_siren.strip() if siret_siren and str(siret_siren).strip() and str(siret_siren).strip() != 'nan' else name.strip()
            display_name = name if name and str(name).strip() and str(name).strip() != 'nan' else query
        else:
            query = query_data.strip()
            display_name = query
            
        if not query:
            continue

        # Progress indicator pour les gros fichiers
        if total > 5:
            progress_text = f"({idx}/{total})"
        else:
            progress_text = ""
            
        with st.spinner(f"Recherche {progress_text} '{display_name}'..."):
            company_data = None
            original_siret = query if is_siret(query) else None

            # Recherche via l'API publique
            company_data = search_company_api(query)

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
    """Read company data from an uploaded CSV or Excel file.
    
    Returns:
        List of tuples (name, siret_siren) or strings if only one column
    """
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

        # Detect name column
        name_col = None
        for col in df.columns:
            col_lower = col.lower().strip()
            if any(keyword in col_lower for keyword in ['nom', 'name', 'entreprise', 'societe', 'société', 'company', 'raison']):
                name_col = col
                st.info(f"✅ Colonne de noms détectée : '{col}'")
                break
        
        # Detect SIRET column
        siret_col = None
        for col in df.columns:
            col_lower = col.lower().strip()
            if 'siret' in col_lower:
                siret_col = col
                st.info(f"✅ Colonne SIRET détectée : '{col}'")
                break

        # Detect SIREN column (only if no SIRET)
        siren_col = None
        if siret_col is None:
            for col in df.columns:
                col_lower = col.lower().strip()
                if 'siren' in col_lower:
                    siren_col = col
                    st.info(f"✅ Colonne SIREN détectée : '{col}'")
                    break

        # Determine what data we have
        id_col = siret_col or siren_col
        
        if name_col and id_col:
            # Best case: both name and SIRET/SIREN
            st.success(f"🎯 Mode optimal : Noms + SIRET/SIREN détectés")
            values = []
            for _, row in df.iterrows():
                name = row[name_col] if pd.notna(row[name_col]) else None
                id_val = row[id_col] if pd.notna(row[id_col]) else None
                # Skip empty rows
                if name or id_val:
                    values.append((str(name) if name else '', str(id_val) if id_val else ''))
            return values
            
        elif name_col:
            # Only names
            st.info(f"📋 Mode : Noms uniquement (colonne '{name_col}')")
            values = df[name_col].dropna().astype(str).str.strip()
            return [v for v in values if v and v != 'nan']
            
        elif id_col:
            # Only SIRET/SIREN
            st.info(f"📋 Mode : SIRET/SIREN uniquement (colonne '{id_col}')")
            values = df[id_col].dropna().astype(str).str.strip()
            return [v for v in values if v and v != 'nan']
            
        else:
            # Fallback: use first column
            first_col = df.columns[0]
            st.warning(f"⚠️ Aucune colonne reconnue. Utilisation de la première colonne : '{first_col}'")
            values = df[first_col].dropna().astype(str).str.strip()
            return [v for v in values if v and v != 'nan']

        return []
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
        
        # Convert all columns to string to avoid Arrow serialization issues
        for col in df.columns:
            df[col] = df[col].astype(str)

        # Display results
        st.markdown("### 📊 Résultats — Données enrichies")
        st.markdown("*Données d'identification, financières, géographiques, dirigeants et certifications*")
        st.dataframe(df, use_container_width=True)

        # Summary
        verified = sum(1 for r in results
                       if r.get("Vérification SIREN") == "✅ Vérifié")
        not_found = len(results) - verified
        with_finances = sum(1 for r in results
                           if r.get("Données financières publiées") == "Oui")
        
        st.markdown(
            f"**Résumé :** {verified} SIREN vérifié(s), "
            f"{not_found} non trouvé(s) sur {len(results)} entrée(s) | "
            f"💰 {with_finances} avec données financières ({(with_finances/len(results)*100):.0f}%)")

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
    "📁 Import fichier",
    "✏️ Recherche par nom",
])

# ── Tab 1: File upload ────────────────────────────────
with tab_file:
    st.markdown("### Importer un fichier d'entreprises")
    st.markdown(
        "Importez un fichier **CSV** ou **Excel** :\n\n"
        "**Format recommandé (2 colonnes) :**\n"
        "- Colonne A : Nom entreprise\n"
        "- Colonne B : SIRET ou SIREN (optionnel)\n\n"
        "**Format simple (1 colonne) :**\n"
        "- Noms d'entreprises OU SIRET/SIREN"
    )

    uploaded_file = st.file_uploader(
        "Choisir un fichier CSV ou Excel",
        type=["csv", "xlsx", "xls"],
        help="Le fichier peut contenir des noms d'entreprises, SIRET, ou SIREN. "
             "L'app détectera automatiquement le type de données.",
    )

    if uploaded_file is not None:
        siret_list = read_uploaded_file(uploaded_file)

        if siret_list:
            st.info(f"📋 {len(siret_list)} entrée(s) trouvée(s) "
                    "dans le fichier.")

            # Show preview
            with st.expander("Aperçu des données importées"):
                preview_data = []
                for item in siret_list[:10]:
                    if isinstance(item, tuple):
                        name, id_val = item
                        type_val = "SIRET" if is_siret(id_val) else ("SIREN" if is_siren(id_val) else "—")
                        preview_data.append({
                            "Nom entreprise": name if name and name != 'nan' else "—",
                            "SIRET/SIREN": id_val if id_val and id_val != 'nan' else "—",
                            "Type ID": type_val,
                        })
                    else:
                        s = item
                        type_val = "SIRET" if is_siret(s) else ("SIREN" if is_siren(s) else "Nom")
                        preview_data.append({
                            "Valeur importée": s,
                            "Type": type_val,
                        })
                st.dataframe(pd.DataFrame(preview_data),
                             use_container_width=True)
                if len(siret_list) > 10:
                    st.caption(f"… et {len(siret_list) - 10} autre(s)")

            if st.button("🔍 Rechercher et enrichir les données",
                         type="primary", key="btn_file"):
                with st.spinner("Traitement en cours..."):
                    results = process_companies(siret_list)
                display_results(results, section_key="file")

# ── Tab 2: Manual input ──────────────────────────────
with tab_manual:
    st.markdown("### Recherche d'Entreprises par Nom")
    st.markdown("**Entrez les noms d'entreprises** (un par ligne). "
                "Vous pouvez aussi ajouter SIREN ou SIRET pour plus de précision.")

    user_input = st.text_area(
        "Noms d'entreprises (ou SIRET/SIREN)",
        height=150,
        placeholder="Exemple:\nAirbus\nTotal Energies\nOrange\nRenault\n\n"
                    "Ou avec SIRET/SIREN:\n383474814\n38347481400019",
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
    **🔍 Recherche par nom (recommandé) :**
    1. Entrez simplement les noms d'entreprises
    2. L'API trouvera automatiquement les données
    3. Aucune authentification requise !
    
    **📁 Import fichier :**
    Format optimal : 2 colonnes
    - Colonne A : Nom entreprise
    - Colonne B : SIRET ou SIREN (optionnel)
    
    Format simple : 1 colonne
    - Noms d'entreprises OU SIRET/SIREN
    
    **⏱️ Rate Limiting :**
    L'application respecte automatiquement les limites
    de l'API (~250 req/min max) avec marge de sécurité.

    **💡 SIRET/SIREN (optionnel) :**
    - **SIRET :** 14 chiffres
    - **SIREN :** 9 chiffres
    - Utilisez-les pour une recherche plus précise
    """)

    # Show mode
    st.success("🌐 Mode : API publique (recherche-entreprises.api.gouv.fr)")
    st.caption(f"⏱️ Rate limiting : {API_DELAY_SECONDS}s entre requêtes | Max {API_MAX_RETRIES} tentatives")

    st.markdown("### 📊 Données extraites (enrichies)")
    st.markdown("""
    **🔍 Identification :**
    - SIRET / SIREN / Sigle
    - Nom complet
    - Vérification SIREN
    
    **🏢 État et structure :**
    - État administratif
    - Date de création
    - Catégorie d'entreprise
    - Nature juridique
    - Activité principale (NAF)
    
    **👥 Effectifs et établissements :**
    - Tranche d'effectif salarié
    - Année de l'effectif
    - Nombre total d'établissements
    - Établissements ouverts
    
    **💰 Données financières :**
    - Année des finances
    - **Données financières publiées** (Oui/Non)
    - Chiffre d'affaires (CA)
    - Résultat net
    
    ⚠️ **Important** : Seules les GE, ETI et sociétés cotées
    publient leurs comptes. ~80% des entreprises françaises
    (PME, micro-entreprises) n'y sont PAS obligées.
    
    **📍 Localisation :**
    - Adresse complète du siège
    - Code postal, Commune
    - Département, Région
    - Coordonnées GPS (latitude/longitude)
    
    **👤 Dirigeants :**
    - Liste des dirigeants et leurs fonctions
    - Direction générale
    - Commissaires aux comptes
    
    **🏆 Certifications et labels :**
    - Qualiopi, RGE, Bio, ESS
    - Société à mission
    - Service public
    - Conventions collectives (IDCC)
    
    **✨ Autres :**
    - Organisme de formation
    - Entrepreneur spectacle
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
