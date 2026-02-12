"""
Streamlit app for searching French companies using data.gouv.fr API.

Uses the unified enrichment module (enrichment.py) which combines:
  - DINUM API for company identification
  - SQLite database for financial data (built from RNE/INPI)

IMPORTANT: This app only uses REAL data from the official French government API.
           No demo or fake data is returned.
"""
import streamlit as st
import pandas as pd
from io import BytesIO
from pathlib import Path
import re
import time
import requests

# Import unified enrichment module
try:
    from enrichment import get_finances, db_available, db_age_days
    FINANCES_AVAILABLE = True
except ImportError:
    FINANCES_AVAILABLE = False

st.set_page_config(
    page_title="Recherche Entreprises",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Minimalist CSS ──
st.markdown("""
<style>
    /* Clean, minimal spacing */
    .block-container { padding-top: 2rem; max-width: 960px; }

    /* Subtle header */
    .app-header {
        padding: 1.2rem 0 0.8rem 0;
        border-bottom: 2px solid #e0e0e0;
        margin-bottom: 1.5rem;
    }
    .app-header h1 { font-size: 1.6rem; font-weight: 600; margin: 0; color: #1a1a2e; }
    .app-header p  { font-size: 0.9rem; color: #666; margin: 0.3rem 0 0 0; }

    /* Clean buttons */
    .stButton > button {
        border-radius: 6px;
        font-weight: 500;
        padding: 0.5rem 1.5rem;
    }

    /* Compact metrics */
    [data-testid="stMetricValue"] { font-size: 1.5rem; font-weight: 600; }

    /* Remove sidebar shadow */
    [data-testid="stSidebar"] { background: #fafafa; }
</style>
""", unsafe_allow_html=True)

# ── Header ──
st.markdown("""
<div class="app-header">
    <h1>🏢 Recherche d'Entreprises</h1>
    <p>Données officielles — API DINUM &amp; RNE / INPI</p>
</div>
""", unsafe_allow_html=True)

# DB age warning
if FINANCES_AVAILABLE and db_available():
    age = db_age_days()
    if age is not None and age > 90:
        st.warning(f"⚠️ Base financière datée de {age} jours. Lancez `python update_rne_db.py` pour la mettre à jour.")

# API configuration
USE_API = True
API_BASE_URL = "https://recherche-entreprises.api.gouv.fr"
API_DELAY_SECONDS = 0.5
API_MAX_RETRIES = 3


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


def extract_financial_info(company_data, original_siret=None, rne_data=None):
    """Extract comprehensive information from company data.

    Args:
        company_data: Données de l'API DINUM
        original_siret: SIRET original de la requête
        rne_data: Données financières SQLite/RNE (optionnel)
    """
    
    # Base structures
    finances = company_data.get("finances") or {}
    siege = company_data.get("siege") or {}
    complements = company_data.get("complements") or {}
    dirigeants = company_data.get("dirigeants") or []
    
    siren = company_data.get("siren", "N/A")
    siret = original_siret or siege.get("siret", company_data.get("siret", "N/A"))
    
    # SIREN verification status
    siren_verifie = "✅ Vérifié" if siren and siren != "N/A" else "❌ Non trouvé"
    
    # Financial data - utiliser RNE en priorité si disponible, sinon DINUM
    ca = "N/A"
    resultat_net = "N/A"
    annee_finance = "N/A"
    finances_publiees = "Non"
    nb_exercices_rne = 0
    source_finances = "N/A"
    
    # Priorité aux données RNE si disponibles
    if rne_data and rne_data.get("success"):
        bilans = rne_data.get("bilans", [])
        if bilans:
            # Prendre le bilan le plus récent
            latest_bilan = bilans[0]
            annee_finance = latest_bilan.get("date_cloture", "N/A")
            ca = latest_bilan.get("chiffre_affaires"
, "N/A")
            resultat_net = latest_bilan.get("resultat_net", "N/A")
            nb_exercices_rne = len(bilans)
            finances_publiees = "Oui"
            source_finances = f"RNE ({nb_exercices_rne} exercice(s))"
    # Sinon, utiliser les données DINUM
    elif finances:
        # L'API retourne un dict avec l'année comme clé: {"2024": {"ca": ..., "resultat_net": ...}}
        latest_year = max(finances.keys()) if finances else None
        if latest_year:
            annee_finance = latest_year
            year_data = finances[latest_year]
            ca = year_data.get("ca", "N/A")
            resultat_net = year_data.get("resultat_net", "N/A")
            finances_publiees = "Oui"
            source_finances = "API DINUM"
    
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
        "Source finances": source_finances,
        "Année finances": annee_finance,
        "Chiffre d'affaires (CA)": _format_currency(ca),
        "Résultat net": _format_currency(resultat_net),
        "Nb exercices (RNE)": nb_exercices_rne if nb_exercices_rne > 0 else "N/A",
        
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

    if USE_API and total > 1:
        estimated_time = total * API_DELAY_SECONDS
        if estimated_time > 5:
            st.info(f"⏱️ {total} entreprise(s) — ~{int(estimated_time)}s")

    progress_bar = st.progress(0) if total > 1 else None

    for idx, query_data in enumerate(queries, 1):
        if isinstance(query_data, tuple):
            name, siret_siren = query_data
            query = (
                siret_siren.strip()
                if siret_siren
                and str(siret_siren).strip()
                and str(siret_siren).strip() != "nan"
                else name.strip()
            )
            display_name = (
                name
                if name and str(name).strip() and str(name).strip() != "nan"
                else query
            )
        else:
            query = query_data.strip()
            display_name = query

        if not query:
            continue

        if progress_bar:
            progress_bar.progress(idx / total)

        with st.spinner(f"Recherche {idx}/{total}: {display_name[:40]}..."):
            original_siret = query if is_siret(query) else None
            company_data = search_company_api(query)
            rne_data = None

            # Enrich with SQLite finances if available
            if company_data and FINANCES_AVAILABLE:
                siren = company_data.get("siren")
                if siren:
                    rne_data = get_finances(siren)

            if company_data:
                info = extract_financial_info(company_data, original_siret, rne_data)
                results.append(info)
            else:
                results.append(
                    {
                        "SIRET": original_siret or "N/A",
                        "SIREN": extract_siren_from_siret(query)
                        if is_siret(query)
                        else "N/A",
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
                    }
                )

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
    """Display results in a clean, minimal layout."""
    if not results:
        st.info("Aucun résultat.")
        return

    df = pd.DataFrame(results)
    for col in df.columns:
        df[col] = df[col].astype(str)

    verified = sum(1 for r in results if r.get("Vérification SIREN") == "✅ Vérifié")
    not_found = len(results) - verified
    with_finances = sum(1 for r in results if r.get("Données financières publiées") == "Oui")

    # Compact summary row
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    c1.metric("Trouvées", verified)
    c2.metric("Avec finances", with_finances)
    c3.metric("Non trouvées", not_found)

    # Data table
    st.dataframe(df, use_container_width=True, height=min(400, 60 + len(results) * 35))

    # Download row
    col_a, col_b = st.columns(2)
    with col_a:
        create_download_button(df, "CSV", section_key)
    with col_b:
        create_download_button(df, "XLSX", section_key)



# ── Main UI ──────────────────────────────────────────

tab_file, tab_manual = st.tabs(["📁 Import fichier", "✏️ Saisie manuelle"])

with tab_file:
    st.markdown("#### Importer un fichier")
    st.caption("CSV ou Excel — colonnes détectées automatiquement (nom, SIRET, SIREN)")

    uploaded_file = st.file_uploader(
        "Fichier CSV / Excel",
        type=["csv", "xlsx", "xls"],
    )

    if uploaded_file is not None:
        siret_list = read_uploaded_file(uploaded_file)
        if siret_list:
            st.info(f"{len(siret_list)} entrée(s) détectée(s)")
            if st.button("🔍 Lancer la recherche", type="primary", key="btn_file"):
                results = process_companies(siret_list)
                display_results(results, section_key="file")

with tab_manual:
    st.markdown("#### Recherche manuelle")
    st.caption("Un nom, SIREN ou SIRET par ligne")

    user_input = st.text_area(
        "Entreprises",
        height=120,
        placeholder="Airbus\nTotal Energies\n383474814",
    )

    if st.button("🔍 Rechercher", type="primary", key="btn_manual"):
        if user_input:
            queries = [l.strip() for l in user_input.split("\n") if l.strip()]
            if queries:
                results = process_companies(queries)
                display_results(results, section_key="manual")
            else:
                st.warning("Entrez au moins une entreprise.")
        else:
            st.warning("Entrez au moins une entreprise.")

# ── Sidebar (minimal) ──

with st.sidebar:
    st.markdown("### ℹ️ À propos")
    st.caption("Données officielles via l'API de l'État français.")

    if FINANCES_AVAILABLE and db_available():
        st.success("✅ Base financière SQLite disponible")
        age = db_age_days()
        if age is not None:
            st.caption(f"Dernière mise à jour : il y a {age} jour(s)")
    else:
        st.info("💡 Pas de base financière locale. Seules les données DINUM sont utilisées.")

    st.markdown("---")
    st.caption("⚠️ Seules 10-20 % des entreprises publient leurs comptes.")
    st.markdown("[API Recherche Entreprises](https://recherche-entreprises.api.gouv.fr/)")
