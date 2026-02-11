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
import requests

# Import enrichissement RNE
try:
    from enrichment_hybrid import enrich_from_api_dinum_and_rne, enrich_batch_parallel
    RNE_AVAILABLE = True
except ImportError:
    RNE_AVAILABLE = False
    print("⚠️ Module enrichment_hybrid non disponible")

st.set_page_config(
    page_title="Recherche d'Entreprises",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé pour un design moderne
st.markdown("""
<style>
    /* En-tête avec gradient */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
    }
    
    .main-header h1 {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    
    .main-header p {
        font-size: 1.1rem;
        opacity: 0.95;
    }
    
    /* Cards stylées */
    .info-card {
        background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 5px solid #2196F3;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.07);
    }
    
    .warning-card {
        background: linear-gradient(135deg, #FFF3E0 0%, #FFE0B2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 5px solid #FF9800;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.07);
    }
    
    /* Tabs améliorés */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f2f6;
        border-radius: 10px 10px 0 0;
        padding: 10px 20px;
        font-weight: 600;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
    }
    
    /* Boutons améliorés */
    .stButton > button {
        border-radius: 25px;
        padding: 0.6rem 2rem;
        font-weight: 600;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    
    /* DataFrames stylés */
    .dataframe {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    
    /* Sidebar amélioré */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
    
    /* Métriques stylées */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
        color: #667eea;
    }
    
    /* Success messages */
    .element-container .stSuccess {
        background: linear-gradient(135deg, #C8E6C9 0%, #A5D6A7 100%);
        border-radius: 10px;
        border-left: 5px solid #4CAF50;
    }
</style>
""", unsafe_allow_html=True)

# En-tête moderne
st.markdown("""
<div class="main-header">
    <h1>🏢 Recherche d'Entreprises Françaises</h1>
    <p>Explorez les données officielles des entreprises françaises en quelques clics</p>
</div>
""", unsafe_allow_html=True)

# Informations avec cards stylées
st.markdown("""
<div class="info-card">
    <strong>💡 API Publique et Gratuite</strong><br>
    Aucune authentification requise ! Cette application utilise l'API ouverte de l'État français pour vous fournir des données officielles et à jour.
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="warning-card">
    <strong>⚠️ Note sur les données financières</strong><br>
    Seules 10-20% des entreprises publient leurs comptes (GE, ETI, sociétés cotées). 
    Les PME de moins de 50 salariés ne sont pas obligées de publier. Il est normal que beaucoup de résultats affichent 'N/A'.
</div>
""", unsafe_allow_html=True)

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


def extract_financial_info(company_data, original_siret=None, rne_data=None):
    """Extract comprehensive information from company data including financial, 
    legal, geographic, and leadership data.
    
    Args:
        company_data: Données de l'API DINUM
        original_siret: SIRET original de la requête
        rne_data: Données financières RNE (optionnel)
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
    """Process multiple company queries with optimized batch processing for large volumes.
    
    Args:
        queries: List of strings (company names) or tuples (name, siret/siren)
    """
    results = []
    total = len(queries)
    
    # Seuil pour activer le mode batch optimisé
    BATCH_THRESHOLD = 50
    use_batch_mode = (total >= BATCH_THRESHOLD and 
                      'use_rne' in st.session_state and 
                      st.session_state.use_rne and 
                      RNE_AVAILABLE)
    
    # MODE BATCH OPTIMISÉ pour gros volumes avec RNE
    if use_batch_mode:
        st.info(f"🚀 **Mode d'optimisation activé** pour {total} entreprises")
        st.markdown("""
        **Traitement par lots optimisé :**
        - 📊 Phase 1: Récupération des SIRENs via API DINUM
        - 📦 Phase 2: Tri et regroupement par fichier RNE
        - ⚡ Phase 3: Téléchargement parallèle (3 fichiers max simultanés)
        - 🗑️ Nettoyage automatique après chaque lot
        """)
        
        # Phase 1: Récupération des SIRENs
        st.markdown("### 📊 Phase 1: Identification des entreprises")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        company_mapping = {}  # {siren: (company_data, original_query)}
        queries_without_siren = []  # Entreprises non trouvées
        
        for idx, query_data in enumerate(queries, 1):
            if isinstance(query_data, tuple):
                name, siret_siren = query_data
                query = siret_siren.strip() if siret_siren and str(siret_siren).strip() and str(siret_siren).strip() != 'nan' else name.strip()
                display_name = name if name and str(name).strip() and str(name).strip() != 'nan' else query
            else:
                query = query_data.strip()
                display_name = query
            
            if not query:
                continue
            
            status_text.text(f"Recherche {idx}/{total}: {display_name[:50]}...")
            progress_bar.progress(idx / total)
            
            original_siret = query if is_siret(query) else None
            company_data = search_company_api(query)
            
            if company_data and company_data.get("siren"):
                siren = company_data["siren"]
                company_mapping[siren] = (company_data, original_siret, display_name)
            else:
                queries_without_siren.append((query, display_name, original_siret))
        
        status_text.text(f"✅ Phase 1 terminée: {len(company_mapping)} entreprises identifiées")
        
        # Phase 2 & 3: Enrichissement RNE par lots
        if company_mapping:
            st.markdown("### 📦 Phase 2-3: Enrichissement RNE par lots")
            
            sirens_list = list(company_mapping.keys())
            
            # Callback pour afficher la progression
            batch_progress = st.progress(0)
            batch_status = st.empty()
            
            def progress_callback(completed, total_files, current_file):
                batch_progress.progress(completed / total_files)
                batch_status.text(f"📦 Fichiers traités: {completed}/{total_files} - Actuel: {current_file}")
            
            # Traitement par lots parallèle
            rne_results = enrich_batch_parallel(
                sirens_list, 
                max_bilans=10, 
                max_workers=3,
                progress_callback=progress_callback
            )
            
            batch_status.text(f"✅ Enrichissement RNE terminé: {len([r for r in rne_results.values() if r.get('success')])} réussis")
            
            # Fusion des données
            for siren, (company_data, original_siret, display_name) in company_mapping.items():
                rne_data = rne_results.get(siren)
                info = extract_financial_info(company_data, original_siret, rne_data)
                results.append(info)
        
        # Ajouter les entreprises non trouvées
        for query, display_name, original_siret in queries_without_siren:
            results.append({
                "SIRET": original_siret or "N/A",
                "SIREN": extract_siren_from_siret(query) if is_siret(query) else "N/A",
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
        
        st.success(f"✅ **Traitement terminé** : {len(results)} entreprises traitées")
        
    # MODE STANDARD pour petits volumes
    else:
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
                    # Enrichissement RNE si activé (mode simple)
                    rne_data = None
                    if 'use_rne' in st.session_state and st.session_state.use_rne:
                        siren = company_data.get("siren")
                        if siren and RNE_AVAILABLE:
                            try:
                                with st.spinner(f"🏛️ Enrichissement RNE pour {siren}..."):
                                    rne_data = enrich_from_api_dinum_and_rne(siren, max_bilans=10)
                            except Exception as e:
                                st.warning(f"⚠️ Erreur enrichissement RNE pour {siren}: {str(e)}")
                    
                    info = extract_financial_info(company_data, original_siret, rne_data)
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

        # Summary avec métriques visuelles
        verified = sum(1 for r in results
                       if r.get("Vérification SIREN") == "✅ Vérifié")
        not_found = len(results) - verified
        with_finances = sum(1 for r in results
                           if r.get("Données financières publiées") == "Oui")
        
        # En-tête avec métriques
        st.markdown("---")
        st.markdown("### 📊 Résultats de la Recherche")
        
        # Métriques en colonnes
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="🏢 Total",
                value=len(results),
                delta="entreprises"
            )
        
        with col2:
            st.metric(
                label="✅ Vérifiées",
                value=verified,
                delta=f"{(verified/len(results)*100):.0f}%" if results else "0%"
            )
        
        with col3:
            st.metric(
                label="💰 Avec finances",
                value=with_finances,
                delta=f"{(with_finances/len(results)*100):.0f}%" if results else "0%"
            )
        
        with col4:
            st.metric(
                label="❌ Non trouvées",
                value=not_found,
                delta=f"{(not_found/len(results)*100):.0f}%" if results else "0%",
                delta_color="inverse"
            )
        
        st.markdown("---")
        
        # Affichage avec tabs pour différentes vues
        tab_table, tab_cards = st.tabs(["📋 Vue Tableau", "🎴 Vue Cartes"])
        
        with tab_table:
            st.markdown("*Données complètes : identification, finances, géographie, dirigeants et certifications*")
            st.dataframe(df, use_container_width=True, height=500)
        
        with tab_cards:
            # Vue en cartes pour les premières entreprises
            st.markdown("*Vue détaillée des premières entreprises*")
            for idx, result in enumerate(results[:5]):  # Limiter à 5 pour la vue carte
                with st.expander(f"🏢 {result.get('Nom', 'N/A')}", expanded=(idx==0)):
                    col_a, col_b = st.columns(2)
                    
                    with col_a:
                        st.markdown("**🔍 Identification**")
                        st.markdown(f"- **SIREN:** {result.get('SIREN', 'N/A')}")
                        st.markdown(f"- **SIRET:** {result.get('SIRET', 'N/A')}")
                        st.markdown(f"- **Statut:** {result.get('Vérification SIREN', 'N/A')}")
                        st.markdown(f"- **État:** {result.get('État administratif', 'N/A')}")
                        
                        st.markdown("**💰 Finances**")
                        ca_value = result.get("Chiffre d'affaires (CA)", 'N/A')
                        st.markdown(f"- **CA:** {ca_value}")
                        st.markdown(f"- **Résultat:** {result.get('Résultat net', 'N/A')}")
                        st.markdown(f"- **Année:** {result.get('Année finances', 'N/A')}")
                    
                    with col_b:
                        st.markdown("**📍 Localisation**")
                        st.markdown(f"- **Adresse:** {result.get('Adresse siège', 'N/A')}")
                        st.markdown(f"- **Ville:** {result.get('Commune', 'N/A')}")
                        st.markdown(f"- **Région:** {result.get('Région', 'N/A')}")
                        
                        st.markdown("**👥 Organisation**")
                        st.markdown(f"- **Effectif:** {result.get('Effectif salarié', 'N/A')}")
                        st.markdown(f"- **Catégorie:** {result.get('Catégorie', 'N/A')}")
                        nb_etab = result.get("Nombre d'établissements", 'N/A')
                        st.markdown(f"- **Établissements:** {nb_etab}")
            
            if len(results) > 5:
                st.info(f"💡 {len(results) - 5} autres entreprises disponibles dans la vue tableau")

        # Export options avec style amélioré
        st.markdown("---")
        st.markdown("### 📥 Télécharger les Résultats")
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            create_download_button(df, "CSV", section_key)
        with col2:
            create_download_button(df, "XLSX", section_key)
        with col3:
            st.markdown("*Exportez toutes les données en CSV ou Excel*")

        st.success(f"✅ Traitement terminé : {len(results)} entreprise(s) analysée(s)")
    else:
        st.warning("⚠️ Aucun résultat trouvé")


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
    st.markdown("## 📚 Guide d'Utilisation")
    
    # Instructions avec expanders pour une meilleure organisation
    with st.expander("🔍 **Recherche par Nom**", expanded=True):
        st.markdown("""
        **Simple et rapide :**
        1. Entrez les noms d'entreprises
        2. L'API trouve automatiquement les données
        3. Aucune clé API nécessaire !
        
        💡 *Méthode recommandée*
        """)
    
    with st.expander("📁 **Import de Fichier**"):
        st.markdown("""
        **Format optimal (2 colonnes) :**
        - Colonne A : Nom entreprise
        - Colonne B : SIRET/SIREN (optionnel)
        
        **Format simple (1 colonne) :**
        - Noms d'entreprises OU SIRET/SIREN
        
        📊 Formats : CSV, Excel (.xlsx, .xls)
        """)
    
    with st.expander("📊 **Données Enrichies**"):
        st.markdown("""
        **🔍 Identification**
        - SIRET, SIREN, Nom, Sigle
        
        **🏢 Structure**
        - État, Catégorie, Nature juridique
        - Date de création, Activité (NAF)
        
        **💰 Finances** *(10-20% publient)*
        - Chiffre d'affaires
        - Résultat net
        
        **📍 Localisation**
        - Adresse complète
        - Coordonnées GPS
        
        **👥 Organisation**
        - Effectifs, Dirigeants
        - Nombre d'établissements
        
        **🏆 Certifications**
        - Qualiopi, RGE, Bio, ESS
        - Société à mission
        """)
    
    st.markdown("---")
    
    # Informations techniques avec style
    st.markdown("### ⚙️ Configuration")
    st.success("🌐 **API Publique Active**")
    st.caption("recherche-entreprises.api.gouv.fr")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("⏱️ Délai", f"{API_DELAY_SECONDS}s")
    with col_b:
        st.metric("🔄 Tentatives", API_MAX_RETRIES)
    
    st.markdown("---")
    
    # Option d'enrichissement RNE
    st.markdown("### 🏛️ Enrichissement RNE")
    
    if RNE_AVAILABLE:
        use_rne = st.checkbox(
            "📊 Activer enrichissement FTP/RNE",
            value=False,
            help="Récupère les données financières sur plusieurs années depuis le serveur FTP RNE (INPI)",
            key="use_rne"  # Stocké dans session_state
        )
        
        if use_rne:
            st.success("""
            ✅ **Enrichissement RNE activé**
            
            📈 Données sur **plusieurs années**
            💾 Cache local (rapide)
            🔄 Téléchargement à la demande
            """)
            
            st.info("""
            **🚀 Mode optimisé pour gros volumes**
            
            À partir de 50 entreprises :
            - 📦 Tri par fichiers RNE
            - ⚡ Traitement parallèle (3 fichiers max)
            - 🗑️ Nettoyage automatique
            - 💾 Économie d'espace disque
            """)
        else:
            st.info("""
            💡 **Enrichissement RNE disponible**
            
            Activez pour obtenir l'historique complet des finances.
            """)
    else:
        st.warning("""
        ⚠️ **Module RNE non disponible**
        
        Pour l'activer, vérifiez enrichment_hybrid.py
        """)
        if "use_rne" not in st.session_state:
            st.session_state.use_rne = False
    
    st.markdown("---")
    
    # Note importante sur les finances
    st.markdown("### ⚠️ Note Importante")
    st.warning("""
    **Données financières limitées**
    
    Seules 10-20% des entreprises publient leurs comptes :
    - Grandes Entreprises (GE)
    - ETI (Entreprises de Taille Intermédiaire)
    - Sociétés cotées
    
    Les PME < 50 salariés ne sont **pas obligées** de publier.
    """)
    
    st.markdown("---")
    
    # Source et crédits
    st.markdown("### 🔗 Sources")
    st.markdown("""
    **Données officielles**
    
    📊 [API Recherche d'Entreprises](https://recherche-entreprises.api.gouv.fr/)
    
    🤝 Inspiré par [datagouv-mcp](https://github.com/datagouv/datagouv-mcp)
    
    🇫🇷 [data.gouv.fr](https://www.data.gouv.fr)
    """)
