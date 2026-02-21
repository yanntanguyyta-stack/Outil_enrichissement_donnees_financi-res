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
import math
import os

# Import unified enrichment module
try:
    from enrichment import get_finances, db_available, db_age_days
    FINANCES_AVAILABLE = True
except ImportError:
    FINANCES_AVAILABLE = False

st.set_page_config(
    page_title="Enrichissement Données Entreprises",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Modern CSS ──
st.markdown("""
<style>
    /* ── Global layout ── */
    .block-container { padding-top: 1.5rem; max-width: 1100px; }

    /* ── App header ── */
    .app-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 1.8rem 2rem;
        border-radius: 16px;
        margin-bottom: 1.8rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    }
    .app-header h1 {
        font-size: 1.8rem;
        font-weight: 700;
        margin: 0 0 0.3rem 0;
        color: #ffffff;
        letter-spacing: -0.3px;
    }
    .app-header p {
        font-size: 0.9rem;
        color: rgba(255,255,255,0.7);
        margin: 0;
    }
    .app-header .badge {
        display: inline-block;
        background: rgba(255,255,255,0.15);
        color: rgba(255,255,255,0.9);
        border-radius: 20px;
        padding: 0.15rem 0.7rem;
        font-size: 0.75rem;
        margin-left: 0.5rem;
        vertical-align: middle;
        backdrop-filter: blur(4px);
    }

    /* ── Section headings ── */
    .section-heading {
        font-size: 1.05rem;
        font-weight: 600;
        color: #1a1a2e;
        margin: 1.5rem 0 0.8rem 0;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }
    .section-heading::after {
        content: '';
        flex: 1;
        height: 1px;
        background: linear-gradient(to right, #e0e4f0, transparent);
        margin-left: 0.5rem;
    }

    /* ── Source cards ── */
    .source-card {
        background: #f8f9fc;
        border: 1px solid #e4e8f0;
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
        transition: all 0.2s;
        cursor: pointer;
    }
    .source-card:hover {
        border-color: #4285F4;
        box-shadow: 0 2px 12px rgba(66,133,244,0.12);
        background: #fff;
    }
    .source-card.active {
        border-color: #4285F4;
        background: #e8f0fe;
    }

    /* ── Metric cards ── */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: #1a1a2e !important;
    }
    [data-testid="stMetricLabel"] { font-size: 0.8rem !important; color: #666 !important; }
    [data-testid="metric-container"] {
        background: #f8f9fc;
        border: 1px solid #e4e8f0;
        border-radius: 12px;
        padding: 1rem;
    }

    /* ── Buttons ── */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        padding: 0.55rem 1.5rem;
        transition: all 0.2s;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #4285F4, #1a73e8);
        border: none;
        color: white;
        box-shadow: 0 2px 8px rgba(66,133,244,0.3);
    }
    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 4px 16px rgba(66,133,244,0.4);
        transform: translateY(-1px);
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background: #f0f2f8;
        padding: 4px;
        border-radius: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 0.4rem 1rem;
        font-weight: 500;
        color: #555;
    }
    .stTabs [aria-selected="true"] {
        background: #ffffff;
        color: #1a1a2e;
        box-shadow: 0 1px 6px rgba(0,0,0,0.1);
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    [data-testid="stSidebar"] * { color: rgba(255,255,255,0.85) !important; }
    [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.15) !important; }
    .user-avatar {
        width: 40px; height: 40px; border-radius: 50%;
        border: 2px solid rgba(255,255,255,0.4);
    }

    /* ── Data table ── */
    [data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid #e4e8f0;
    }

    /* ── Alerts ── */
    .stAlert { border-radius: 10px !important; margin: 0.4rem 0 !important; }

    /* ── Upload box ── */
    [data-testid="stFileUploadDropzone"] {
        border-radius: 12px !important;
        border: 2px dashed #c4cce0 !important;
        background: #f8f9fc !important;
    }
    [data-testid="stFileUploadDropzone"]:hover {
        border-color: #4285F4 !important;
        background: #e8f0fe !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Authentication ──
try:
    from auth import require_auth, logout, get_current_user
    _current_user = require_auth()
    if _current_user is None:
        st.stop()
except ImportError:
    _current_user = {"email": "dev@local", "name": "Mode local"}

# ── Header ──
_db_badge = ""
if FINANCES_AVAILABLE and db_available():
    _db_age = db_age_days()
    _db_badge = (
        f'<span class="badge">📊 RNE {_db_age}j</span>'
        if _db_age is not None
        else '<span class="badge">📊 RNE ✓</span>'
    )

st.markdown(
    f"""
    <div class="app-header">
        <h1>🏢 Enrichissement Données Entreprises {_db_badge}</h1>
        <p>Données officielles — API DINUM &amp; RNE / INPI · Connecté&nbsp;: {_current_user.get("name", "")}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# API configuration
USE_API = True
API_BASE_URL = "https://recherche-entreprises.api.gouv.fr"
API_DELAY_SECONDS = float(os.getenv("DINUM_API_DELAY_SECONDS", "0.8"))
API_MAX_RETRIES = 3
DB_AGE_WARNING_DAYS = 90
API_PAGE_SIZE = 25
API_EXTRACTION_LIMIT_MAX = 2000
API_MAX_DELAY_SECONDS = float(os.getenv("DINUM_API_MAX_DELAY_SECONDS", "8"))
API_IMPORT_MAX_COMPANIES = int(os.getenv("DINUM_IMPORT_MAX_COMPANIES", "1500"))

API_SESSION = requests.Session()

CATEGORIE_ENTREPRISE_OPTIONS = ["PME", "ETI", "GE"]
ETAT_ADMIN_OPTIONS = ["A", "C"]
SECTION_ACTIVITE_OPTIONS = list("ABCDEFGHIJKLMNOPQRSTU")
TRANCHE_EFFECTIF_OPTIONS = ["NN", "00", "01", "02", "03", "11", "12", "21", "22", "31", "32", "41", "42", "51", "52", "53"]
DEPARTEMENT_OPTIONS = [f"{i:02d}" for i in range(1, 96)] + ["2A", "2B", "971", "972", "973", "974", "976"]
REGION_OPTIONS = ["01", "02", "03", "04", "06", "11", "24", "27", "28", "32", "44", "52", "53", "75", "76", "84", "93", "94"]
BOOLEAN_FILTER_LABELS = {
    "est_association": "Association",
    "est_entrepreneur_individuel": "Entrepreneur individuel",
    "est_organisme_formation": "Organisme de formation",
    "est_ess": "Économie sociale et solidaire",
    "est_qualiopi": "Qualiopi",
    "est_rge": "RGE",
    "est_bio": "Bio",
    "est_service_public": "Service public",
    "est_societe_mission": "Société à mission",
    "est_collectivite_territoriale": "Collectivité territoriale",
}

# DB age warning
if FINANCES_AVAILABLE and db_available():
    age = db_age_days()
    if age is not None and age > DB_AGE_WARNING_DAYS:
        st.warning(f"⚠️ Base financière datée de {age} jours. Lancez `python update_rne_db.py` pour la mettre à jour.")


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

    params = {"q": search_query, "per_page": 1}
    data = _request_search_api(params=params, timeout=10, query_for_log=query)
    if data and data.get("results") and len(data["results"]) > 0:
        return data["results"][0]
    return None


def _init_api_runtime_state():
    if "api_next_request_ts" not in st.session_state:
        st.session_state["api_next_request_ts"] = 0.0
    if "api_current_delay" not in st.session_state:
        st.session_state["api_current_delay"] = API_DELAY_SECONDS
    if "api_rate_limit_hits" not in st.session_state:
        st.session_state["api_rate_limit_hits"] = 0
    if "api_retry_attempts" not in st.session_state:
        st.session_state["api_retry_attempts"] = 0


def _get_retry_after_seconds(response):
    retry_after = response.headers.get("Retry-After")
    if not retry_after:
        return None
    try:
        return max(0, int(float(retry_after)))
    except ValueError:
        return None


def _wait_for_rate_limit_slot():
    _init_api_runtime_state()
    next_allowed_ts = float(st.session_state.get("api_next_request_ts", 0.0))
    now = time.time()
    wait_seconds = max(0.0, next_allowed_ts - now)
    if wait_seconds > 0:
        time.sleep(wait_seconds)


def _on_api_success():
    _init_api_runtime_state()
    current_delay = float(st.session_state.get("api_current_delay", API_DELAY_SECONDS))
    relaxed_delay = max(API_DELAY_SECONDS, current_delay * 0.95)
    st.session_state["api_current_delay"] = relaxed_delay
    st.session_state["api_next_request_ts"] = time.time() + relaxed_delay


def _on_api_rate_limited(response, attempt):
    _init_api_runtime_state()
    st.session_state["api_rate_limit_hits"] = int(st.session_state.get("api_rate_limit_hits", 0)) + 1
    st.session_state["api_retry_attempts"] = int(st.session_state.get("api_retry_attempts", 0)) + 1

    retry_after = _get_retry_after_seconds(response)
    current_delay = float(st.session_state.get("api_current_delay", API_DELAY_SECONDS))
    exponential_delay = current_delay * (1.7 ** attempt)
    target_delay = retry_after if retry_after is not None else exponential_delay
    new_delay = min(API_MAX_DELAY_SECONDS, max(current_delay, target_delay))

    st.session_state["api_current_delay"] = new_delay
    st.session_state["api_next_request_ts"] = time.time() + new_delay


def _request_search_api(params, timeout=10, query_for_log=""):
    url = f"{API_BASE_URL}/search"
    _init_api_runtime_state()

    for attempt in range(API_MAX_RETRIES):
        try:
            _wait_for_rate_limit_slot()
            response = API_SESSION.get(url, params=params, timeout=timeout)

            if response.status_code == 429:
                _on_api_rate_limited(response, attempt)
                if attempt < API_MAX_RETRIES - 1:
                    continue
                return None

            if response.status_code == 400:
                try:
                    message = response.json().get("erreur", "Paramètres invalides")
                except Exception:
                    message = "Paramètres invalides"
                if query_for_log:
                    st.error(f"❌ Requête invalide DINUM ({query_for_log}) : {message}")
                else:
                    st.error(f"❌ Requête invalide DINUM : {message}")
                return None

            response.raise_for_status()
            _on_api_success()
            return response.json()

        except requests.exceptions.RequestException as e:
            st.session_state["api_retry_attempts"] = int(st.session_state.get("api_retry_attempts", 0)) + 1
            if attempt == API_MAX_RETRIES - 1:
                if query_for_log:
                    st.warning(f"⚠️ API non accessible pour '{query_for_log}': {str(e)}")
                else:
                    st.warning(f"⚠️ API non accessible : {str(e)}")
                return None

    return None


def _parse_multi_values(raw_text):
    values = re.split(r"[,;\n\s]+", (raw_text or "").strip())
    clean_values = [v.strip() for v in values if v and v.strip()]
    dedup = list(dict.fromkeys(clean_values))
    return dedup


def _normalize_naf_code(value):
    if value is None:
        return None

    raw = str(value).strip().upper()
    raw = re.sub(r"[^0-9A-Z.]", "", raw)

    if re.match(r"^\d{2}\.\d{2}[A-Z]$", raw):
        return raw

    compact = raw.replace(".", "")
    if re.match(r"^\d{4}[A-Z]$", compact):
        return f"{compact[:2]}.{compact[2:4]}{compact[4]}"

    return None


def _normalize_naf_codes(values):
    normalized = []
    rejected = []

    for value in values or []:
        naf = _normalize_naf_code(value)
        if naf:
            normalized.append(naf)
        else:
            rejected.append(str(value))

    normalized = list(dict.fromkeys(normalized))
    return normalized, rejected


@st.cache_data(ttl=24 * 3600)
def _load_allowed_naf_codes():
    # 1) Tentative via OpenAPI (quand l'enum est présente)
    try:
        resp = requests.get(f"{API_BASE_URL}/openapi.json", timeout=20)
        resp.raise_for_status()
        spec = resp.json()
        params = (
            spec.get("paths", {})
            .get("/search", {})
            .get("get", {})
            .get("parameters", [])
        )
        for param in params:
            if param.get("name") == "activite_principale":
                allowed = param.get("schema", {}).get("enum", [])
                if allowed:
                    return set(allowed)
    except Exception:
        pass

    # 2) Fallback via message d'erreur API (contient la liste exhaustive)
    try:
        probe = requests.get(
            f"{API_BASE_URL}/search",
            params={"q": "transport", "per_page": 1, "activite_principale": "99.99X"},
            timeout=20,
        )
        if probe.status_code == 400:
            payload = probe.json()
            erreur = str(payload.get("erreur", ""))
            values = re.findall(r"'([0-9]{2}\.[0-9]{2}[A-Z])'", erreur)
            if values:
                return set(values)
    except Exception:
        pass

    return set()


def _resolve_naf_codes_for_api(normalized_codes):
    allowed = _load_allowed_naf_codes()
    if not allowed:
        return normalized_codes, [], {}

    resolved = []
    rejected = []
    remapped = {}

    for code in normalized_codes or []:
        if code in allowed:
            resolved.append(code)
            continue

        prefix = code[:5] if len(code) >= 5 else code
        family = sorted([c for c in allowed if c.startswith(prefix)])
        if family:
            remapped[code] = family
            resolved.extend(family)
        else:
            rejected.append(code)

    resolved = list(dict.fromkeys(resolved))
    return resolved, rejected, remapped


def _build_search_params(query, filters, page=1, per_page=1):
    params = [("q", query.strip()), ("page", page), ("per_page", per_page)]

    multi_fields = [
        "activite_principale",
        "section_activite_principale",
        "tranche_effectif_salarie",
        "categorie_entreprise",
        "etat_administratif",
        "departement",
        "region",
        "nature_juridique",
        "code_postal",
        "code_commune",
    ]
    for field in multi_fields:
        for value in filters.get(field, []):
            params.append((field, str(value).strip()))

    for boolean_field in filters.get("boolean_flags", []):
        params.append((boolean_field, "true"))

    for numeric_field in ["ca_min", "ca_max", "resultat_net_min", "resultat_net_max"]:
        value = filters.get(numeric_field)
        if value is not None and value != "":
            params.append((numeric_field, int(value)))

    return params


def _resolve_effective_query(raw_query, filters):
    query = (raw_query or "").strip()
    if len(query) >= 2:
        return query, "manual"

    activites = filters.get("activite_principale", []) or []
    if activites:
        return "entreprise", "naf"

    sections = filters.get("section_activite_principale", []) or []
    if sections:
        return "entreprise", "section_naf"

    natures = filters.get("nature_juridique", []) or []
    if natures:
        return "entreprise", "nature_juridique"

    departements = filters.get("departement", []) or []
    if departements:
        return "entreprise", "departement"

    regions = filters.get("region", []) or []
    if regions:
        return "entreprise", "region"

    return "entreprise", "fallback"


def _search_api_with_params(params):
    return _request_search_api(params=params, timeout=15)


def count_companies_api(query, filters):
    params = _build_search_params(query, filters, page=1, per_page=1)
    data = _search_api_with_params(params)
    if not data:
        return None

    return {
        "total_results": int(data.get("total_results", 0)),
        "total_pages": int(data.get("total_pages", 0)),
        "per_page": int(data.get("per_page", 1) or 1),
    }


def fetch_companies_api(query, filters, extraction_limit):
    first_params = _build_search_params(query, filters, page=1, per_page=API_PAGE_SIZE)
    first_page = _search_api_with_params(first_params)
    if not first_page:
        return [], 0

    total_results = int(first_page.get("total_results", 0))
    all_results = list(first_page.get("results", []))
    max_to_fetch = min(total_results, extraction_limit)

    if max_to_fetch <= len(all_results):
        return all_results[:max_to_fetch], total_results

    total_pages = int(first_page.get("total_pages", 1) or 1)
    pages_to_fetch = min(total_pages, math.ceil(max_to_fetch / API_PAGE_SIZE))
    progress = st.progress(0.0)

    for page in range(2, pages_to_fetch + 1):
        page_params = _build_search_params(query, filters, page=page, per_page=API_PAGE_SIZE)
        page_data = _search_api_with_params(page_params)
        if not page_data:
            break

        page_results = page_data.get("results", [])
        if not page_results:
            break

        all_results.extend(page_results)
        progress.progress(min(page / pages_to_fetch, 1.0))

        if len(all_results) >= max_to_fetch:
            break

    progress.empty()
    return all_results[:max_to_fetch], total_results


def companies_to_results(companies, use_rne=False):
    results = []
    total = len(companies)
    progress = st.progress(0.0) if total > 1 else None

    for idx, company_data in enumerate(companies, 1):
        siege = company_data.get("siege") or {}
        original_siret = siege.get("siret", company_data.get("siret"))

        rne_data = None
        if use_rne and FINANCES_AVAILABLE:
            siren = company_data.get("siren")
            if siren:
                rne_data = get_finances(siren)

        info = extract_financial_info(company_data, original_siret, rne_data)
        results.append(info)

        if progress:
            progress.progress(idx / total)

    if progress:
        progress.empty()

    return results


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
    
    # Historique financier par année (depuis 2019)
    historical_data = {}
    
    # Priorité aux données RNE si disponibles
    if rne_data and rne_data.get("success"):
        bilans = rne_data.get("bilans", [])
        if bilans:
            # Prendre le bilan le plus récent
            latest_bilan = bilans[0]
            annee_finance = latest_bilan.get("date_cloture", "N/A")
            ca = latest_bilan.get("chiffre_affaires", "N/A")
            resultat_net = latest_bilan.get("resultat_net", "N/A")
            nb_exercices_rne = len(bilans)
            finances_publiees = "Oui"
            source_finances = f"RNE ({nb_exercices_rne} exercice(s))"
            
            # Construire l'historique par année (depuis 2019)
            for bilan in bilans:
                date_cloture = bilan.get("date_cloture", "")
                if date_cloture:
                    annee = date_cloture[:4] if len(date_cloture) >= 4 else ""
                    if annee and annee.isdigit() and int(annee) >= 2019:
                        historical_data[annee] = {
                            "ca": bilan.get("chiffre_affaires"),
                            "resultat_net": bilan.get("resultat_net"),
                            "resultat_exploitation": bilan.get("resultat_exploitation"),
                            "total_actif": bilan.get("total_actif"),
                            "capitaux_propres": bilan.get("capitaux_propres"),
                            "effectif": bilan.get("effectif"),
                            "date_cloture": date_cloture,
                        }
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
    
    # Ajouter les colonnes historiques par année (2019 → année courante)
    import datetime
    current_year = datetime.datetime.now().year
    for year in range(2019, current_year + 1):
        year_str = str(year)
        year_data = historical_data.get(year_str, {})
        info[f"CA {year_str}"] = _format_currency(year_data.get("ca")) if year_data else "N/A"
        info[f"Résultat net {year_str}"] = _format_currency(year_data.get("resultat_net")) if year_data else "N/A"
        info[f"Résultat exploitation {year_str}"] = _format_currency(year_data.get("resultat_exploitation")) if year_data else "N/A"
        info[f"Effectif {year_str}"] = year_data.get("effectif", "N/A") if year_data else "N/A"
    
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

    if total > API_IMPORT_MAX_COMPANIES:
        st.warning(
            f"⚠️ Fichier volumineux ({total} lignes). "
            f"Traitement limité aux {API_IMPORT_MAX_COMPANIES} premières lignes pour éviter les quotas API."
        )
        queries = queries[:API_IMPORT_MAX_COMPANIES]
        total = len(queries)

    _init_api_runtime_state()
    st.session_state["api_rate_limit_hits"] = 0
    st.session_state["api_retry_attempts"] = 0
    request_cache = {}

    if USE_API and total > 1:
        estimated_time = total * max(API_DELAY_SECONDS, float(st.session_state.get("api_current_delay", API_DELAY_SECONDS)))
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

            normalized_key = extract_siren_from_siret(query.strip()) if is_siret(query.strip()) else query.strip().lower()
            if normalized_key in request_cache:
                company_data = request_cache[normalized_key]
            else:
                company_data = search_company_api(query)
                request_cache[normalized_key] = company_data

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

    rate_limit_hits = int(st.session_state.get("api_rate_limit_hits", 0))
    retry_attempts = int(st.session_state.get("api_retry_attempts", 0))
    cache_hits = max(0, total - len(request_cache))

    if cache_hits > 0:
        st.info(f"♻️ Déduplication activée : {cache_hits} appel(s) API évité(s)")

    if rate_limit_hits > 0:
        current_delay = float(st.session_state.get("api_current_delay", API_DELAY_SECONDS))
        st.warning(
            f"⚠️ Quota API atteint {rate_limit_hits} fois (réessais: {retry_attempts}). "
            f"Cadence adaptative appliquée (délai actuel ≈ {current_delay:.2f}s)."
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
    """Display results in a modern card layout."""
    if not results:
        st.info("Aucun résultat.")
        return

    df = pd.DataFrame(results)
    for col in df.columns:
        df[col] = df[col].astype(str)

    verified = sum(1 for r in results if r.get("Vérification SIREN") == "✅ Vérifié")
    not_found = len(results) - verified
    with_finances = sum(1 for r in results if r.get("Données financières publiées") == "Oui")

    # Metric summary row
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📊 Total traité", len(results))
    c2.metric("✅ Trouvées", verified)
    c3.metric("💰 Avec finances", with_finances)
    c4.metric("❌ Non trouvées", not_found)

    # Data table
    st.dataframe(df, use_container_width=True, height=min(420, 60 + len(results) * 35))

    # Download row
    col_a, col_b = st.columns(2)
    with col_a:
        create_download_button(df, "CSV", section_key)
    with col_b:
        create_download_button(df, "XLSX", section_key)



# ── Main UI ──────────────────────────────────────────

# Section 1: Import de données
st.markdown('<div class="section-heading">📥 Import de données</div>', unsafe_allow_html=True)

# Onglets pour choix du mode d'entrée
input_tab1, input_tab2, input_tab3 = st.tabs(["📁 Fichier", "🔎 Recherche directe", "🎯 Filtres DINUM"])

queries_to_process = None

with input_tab1:
    st.caption("CSV ou Excel — colonnes détectées automatiquement (nom, SIRET, SIREN)")
    
    uploaded_file = st.file_uploader(
        "Choisissez un fichier",
        type=["csv", "xlsx", "xls"],
        key="main_file_upload"
    )
    
    if uploaded_file is not None:
        queries_to_process = read_uploaded_file(uploaded_file)
        if queries_to_process:
            st.success(f"✅ {len(queries_to_process)} entrée(s) détectée(s)")

with input_tab2:
    st.caption("Saisissez un nom d'entreprise, un SIREN ou un SIRET")

    direct_query = st.text_input(
        "Entreprise à rechercher",
        placeholder="Ex: Airbus ou 383474814",
        key="direct_query",
    )

    if direct_query and direct_query.strip():
        queries_to_process = [direct_query.strip()]
        st.success("✅ 1 entreprise prête pour enrichissement")

with input_tab3:
    st.caption("Parcours en 2 étapes : comptage puis extraction")

    with st.form("dinum_filters_form"):
        query_filters = st.text_input(
            "Nom / mot-clé de recherche (optionnel)",
            placeholder="Ex: transport, informatique, airbus (laisser vide pour pilotage par filtres)",
            key="filters_query",
        )

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            selected_categories = st.multiselect(
                "Catégories d'entreprise",
                options=CATEGORIE_ENTREPRISE_OPTIONS,
                key="filters_categories",
            )
            selected_etat = st.multiselect(
                "État administratif",
                options=ETAT_ADMIN_OPTIONS,
                format_func=lambda x: "Active" if x == "A" else "Cessée",
                key="filters_etat",
            )
            selected_effectif = st.multiselect(
                "Tranches effectif salarié",
                options=TRANCHE_EFFECTIF_OPTIONS,
                key="filters_effectif",
            )

        with col_f2:
            selected_sections = st.multiselect(
                "Sections activité principale (NAF)",
                options=SECTION_ACTIVITE_OPTIONS,
                key="filters_sections",
            )
            selected_departements = st.multiselect(
                "Départements",
                options=DEPARTEMENT_OPTIONS,
                key="filters_departements",
            )
            selected_regions = st.multiselect(
                "Régions (codes)",
                options=REGION_OPTIONS,
                key="filters_regions",
            )

        st.markdown("**Codes et filtres avancés**")
        ape_input = st.text_area(
            "Codes APE/NAF (multisélection, séparés par virgules ou retours ligne)",
            placeholder="62.01Z, 62.02A",
            height=80,
            key="filters_ape_input",
        )
        nj_input = st.text_area(
            "Natures juridiques (codes, multisélection)",
            placeholder="5710, 5499",
            height=80,
            key="filters_nature_juridique",
        )
        cp_input = st.text_input(
            "Codes postaux (multisélection)",
            placeholder="75001, 69001",
            key="filters_cp",
        )
        commune_input = st.text_input(
            "Codes commune INSEE (multisélection)",
            placeholder="75101, 34172",
            key="filters_commune",
        )

        selected_boolean_labels = st.multiselect(
            "Labels / statuts",
            options=list(BOOLEAN_FILTER_LABELS.keys()),
            format_func=lambda x: BOOLEAN_FILTER_LABELS[x],
            key="filters_boolean",
        )

        st.markdown("**Bornes financières (optionnel)**")
        col_num1, col_num2 = st.columns(2)
        with col_num1:
            ca_min = st.number_input("CA min (€)", min_value=0, step=1000, value=0, key="filters_ca_min")
            rn_min = st.number_input("Résultat net min (€)", step=1000, value=0, key="filters_rn_min")
        with col_num2:
            ca_max = st.number_input("CA max (€)", min_value=0, step=1000, value=0, key="filters_ca_max")
            rn_max = st.number_input("Résultat net max (€)", step=1000, value=0, key="filters_rn_max")

        extraction_limit = st.number_input(
            "Limite d'extraction (protection API/Codespaces)",
            min_value=100,
            max_value=API_EXTRACTION_LIMIT_MAX,
            step=100,
            value=500,
            key="filters_extraction_limit",
        )

        submit_count = st.form_submit_button("1) Compter les entreprises concernées", type="primary")

    if submit_count:
        raw_ape_values = _parse_multi_values(ape_input)
        normalized_ape_values, rejected_ape_values = _normalize_naf_codes(raw_ape_values)
        resolved_ape_values, unresolved_ape_values, remapped_ape_values = _resolve_naf_codes_for_api(normalized_ape_values)

        if rejected_ape_values:
            rejected_preview = ", ".join(rejected_ape_values[:5])
            st.warning(
                "⚠️ Certains codes APE/NAF ont été ignorés car invalides : "
                f"{rejected_preview}"
                + (" ..." if len(rejected_ape_values) > 5 else "")
            )

        if remapped_ape_values:
            examples = []
            for original, mapped_values in list(remapped_ape_values.items())[:3]:
                examples.append(f"{original} → {', '.join(mapped_values[:3])}")
            st.info(
                "ℹ️ Conversion automatique de codes NAF vers les valeurs acceptées par l'API : "
                + " | ".join(examples)
            )

        if unresolved_ape_values:
            unresolved_preview = ", ".join(unresolved_ape_values[:5])
            st.warning(
                "⚠️ Certains codes NAF ne correspondent à aucune valeur API et ont été ignorés : "
                f"{unresolved_preview}"
                + (" ..." if len(unresolved_ape_values) > 5 else "")
            )

        filters_payload = {
            "activite_principale": resolved_ape_values,
            "section_activite_principale": selected_sections,
            "tranche_effectif_salarie": selected_effectif,
            "categorie_entreprise": selected_categories,
            "etat_administratif": selected_etat,
            "departement": selected_departements,
            "region": selected_regions,
            "nature_juridique": _parse_multi_values(nj_input),
            "code_postal": _parse_multi_values(cp_input),
            "code_commune": _parse_multi_values(commune_input),
            "boolean_flags": selected_boolean_labels,
            "ca_min": int(ca_min) if ca_min and ca_min > 0 else None,
            "ca_max": int(ca_max) if ca_max and ca_max > 0 else None,
            "resultat_net_min": int(rn_min) if rn_min and rn_min != 0 else None,
            "resultat_net_max": int(rn_max) if rn_max and rn_max != 0 else None,
        }

        effective_query, query_source = _resolve_effective_query(query_filters, filters_payload)

        if query_source == "naf":
            st.info("ℹ️ Mot-clé absent : comptage piloté par filtres NAF avec requête générique DINUM.")
        elif query_source == "section_naf":
            st.info("ℹ️ Mot-clé absent : comptage piloté par section NAF avec requête générique DINUM.")
        elif query_source == "fallback":
            st.warning("⚠️ Mot-clé absent et aucun filtre textuel fort détecté : utilisation de 'entreprise'. Affinez les filtres si le volume est trop large.")

        with st.spinner("Interrogation DINUM pour le comptage..."):
            count_meta = count_companies_api(effective_query, filters_payload)

        if count_meta:
            st.session_state["dinum_filters_query"] = effective_query
            st.session_state["dinum_filters_query_source"] = query_source
            st.session_state["dinum_filters_payload"] = filters_payload
            st.session_state["dinum_filters_count"] = count_meta["total_results"]
            st.session_state["dinum_filters_limit"] = int(extraction_limit)
            st.session_state.pop("dinum_filters_companies", None)
            st.session_state.pop("dinum_filters_results", None)
            st.success("✅ Comptage terminé")

    if "dinum_filters_count" in st.session_state:
        total_count = st.session_state["dinum_filters_count"]
        extraction_limit = st.session_state.get("dinum_filters_limit", 500)
        effective_query = st.session_state.get("dinum_filters_query", "")
        query_source = st.session_state.get("dinum_filters_query_source", "manual")

        if effective_query:
            query_label = "Mot-clé" if query_source == "manual" else "Requête auto"
            st.caption(f"{query_label} utilisé : {effective_query}")

        c_count1, c_count2 = st.columns(2)
        c_count1.metric("Entreprises correspondant aux filtres", f"{total_count:,}".replace(",", " "))
        c_count2.metric("Extraction max prévue", f"{extraction_limit:,}".replace(",", " "))

        if total_count > extraction_limit:
            st.warning(
                f"⚠️ Volumétrie élevée : {total_count:,} résultats. "
                f"L'extraction sera limitée aux {extraction_limit:,} premiers résultats "
                "pour respecter les capacités API/Codespaces."
                .replace(",", " ")
            )

        if st.button("2) Valider et extraire les données DINUM", type="secondary", use_container_width=True, key="btn_extract_filtered"):
            with st.spinner("Extraction DINUM en cours..."):
                raw_companies, total_found = fetch_companies_api(
                    st.session_state["dinum_filters_query"],
                    st.session_state["dinum_filters_payload"],
                    st.session_state["dinum_filters_limit"],
                )

            if raw_companies:
                st.session_state["dinum_filters_companies"] = raw_companies
                st.session_state["dinum_filters_total_found"] = total_found
                st.session_state["dinum_filters_results"] = companies_to_results(raw_companies, use_rne=False)
                st.success(
                    f"✅ Extraction terminée : {len(raw_companies)} entreprise(s) récupérée(s)"
                )
            else:
                st.warning("Aucune entreprise extraite avec ces filtres.")

    if "dinum_filters_results" in st.session_state and st.session_state["dinum_filters_results"]:
        st.markdown("#### Résultats DINUM extraits")
        display_results(st.session_state["dinum_filters_results"], section_key="dinum_filters")

        can_rne = FINANCES_AVAILABLE and db_available()
        if st.button(
            "3) Enrichir ces résultats avec la base RNE",
            type="secondary",
            use_container_width=True,
            key="btn_rne_after_filters",
            disabled=not can_rne,
        ):
            raw_companies = st.session_state.get("dinum_filters_companies", [])
            if not raw_companies:
                st.warning("Aucune donnée brute disponible pour l'enrichissement RNE.")
            else:
                with st.spinner("Enrichissement RNE en cours..."):
                    st.session_state["dinum_filters_results"] = companies_to_results(raw_companies, use_rne=True)
                st.success("✅ Enrichissement RNE terminé")

# Section 2: Choix de la source de données
st.markdown("---")
st.markdown('<div class="section-heading">⚙️ Source des données</div>', unsafe_allow_html=True)

# Vérifier la disponibilité de Pappers
try:
    from enrichment_pappers import check_api_key, SCRAPING_ENABLED
    PAPPERS_AVAILABLE = check_api_key() or SCRAPING_ENABLED
except ImportError:
    PAPPERS_AVAILABLE = False

# Options disponibles
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🏛️ DINUM", use_container_width=True, help="API officielle de l'État", type="secondary"):
        st.session_state["data_source"] = "dinum"

with col2:
    rne_help = "Base locale RNE/INPI" if FINANCES_AVAILABLE and db_available() else "Base RNE non disponible"
    rne_disabled = not (FINANCES_AVAILABLE and db_available())
    if st.button("📊 RNE", use_container_width=True, help=rne_help, disabled=rne_disabled, type="secondary"):
        st.session_state["data_source"] = "rne"

with col3:
    pappers_help = "RNE + enrichissement Pappers" if PAPPERS_AVAILABLE else "Pappers non configuré"
    pappers_disabled = not PAPPERS_AVAILABLE
    if st.button("💰 RNE + Pappers", use_container_width=True, help=pappers_help, disabled=pappers_disabled, type="secondary"):
        st.session_state["data_source"] = "rne_pappers"

# Afficher la source sélectionnée
if "data_source" in st.session_state:
    source_labels = {
        "dinum": "🏛️ DINUM (API officielle)",
        "rne": "📊 RNE (Base locale)",
        "rne_pappers": "💰 RNE + Pappers (Enrichissement complet)"
    }
    st.info(f"**Source active :** {source_labels.get(st.session_state['data_source'], 'Non sélectionnée')}")
else:
    st.warning("⚠️ Sélectionnez une source de données ci-dessus")

# Section 3: Bouton de recherche (actif seulement si données + source)
st.markdown("---")

if queries_to_process and "data_source" in st.session_state:
    if st.button("🔍 Lancer l'enrichissement", type="primary", use_container_width=True, key="btn_enrich"):
        with st.spinner("Traitement en cours..."):
            # Traiter selon la source sélectionnée
            if st.session_state["data_source"] == "dinum":
                results = process_companies(queries_to_process)
            elif st.session_state["data_source"] == "rne":
                results = process_companies(queries_to_process)  # Utilise déjà RNE automatiquement
            elif st.session_state["data_source"] == "rne_pappers":
                # TODO: Intégrer l'enrichissement Pappers
                st.warning("⚠️ L'enrichissement Pappers sera intégré prochainement")
                results = process_companies(queries_to_process)
            
            st.session_state["results_main"] = results
            st.success("✅ Enrichissement terminé !")
    
    # Afficher les résultats persistés
    if "results_main" in st.session_state and st.session_state["results_main"]:
        display_results(st.session_state["results_main"], section_key="main")
elif not queries_to_process:
    st.info("📤 Importez un fichier ou saisissez des entreprises pour commencer")
elif "data_source" not in st.session_state:
    st.info("⚙️ Sélectionnez une source de données")

# ── Sidebar ──

with st.sidebar:
    # ── User info ──
    _user_name = _current_user.get("name", "Utilisateur")
    _user_email = _current_user.get("email", "")
    _user_pic = _current_user.get("picture", "")

    if _user_pic:
        st.markdown(
            f'<img src="{_user_pic}" class="user-avatar" />', unsafe_allow_html=True
        )
    st.markdown(f"**{_user_name}**")
    if _user_email and _user_email != "dev@local":
        st.caption(_user_email)

    try:
        from auth import logout as _do_logout, _AUTH_ENABLED
        if _AUTH_ENABLED and st.button("🚪 Se déconnecter", use_container_width=True, key="btn_logout"):
            _do_logout()
    except ImportError:
        pass

    st.markdown("---")
    st.markdown("### 📊 Sources de données")

    # DINUM (toujours disponible)
    st.markdown("**🏛️ DINUM**")
    st.caption("✅ API officielle de l'État")
    st.caption("→ Identification & données légales")

    # RNE (base locale)
    st.markdown("**📊 RNE / INPI**")
    if FINANCES_AVAILABLE and db_available():
        st.caption("✅ Base SQLite disponible")
        age = db_age_days()
        if age is not None:
            if age > DB_AGE_WARNING_DAYS:
                st.caption(f"⚠️ Mise à jour : il y a {age} jours")
            else:
                st.caption(f"📅 Mise à jour : il y a {age} jours")
        st.caption("→ Données financières locales")
    else:
        st.caption("❌ Base non disponible")
        st.caption("→ Exécutez `python build_rne_db.py`")

    # Pappers
    st.markdown("**💰 Pappers.fr**")
    try:
        from enrichment_pappers import check_api_key, SCRAPING_ENABLED
        has_api = check_api_key()
        has_scraping = SCRAPING_ENABLED

        if has_api:
            st.caption("✅ API configurée")
            st.caption("→ Enrichissement complet disponible")
        elif has_scraping:
            st.caption("⚠️ Mode scraping activé")
            st.caption("→ Plus lent mais gratuit")
        else:
            st.caption("❌ Non configuré")
            st.caption("→ Ajoutez une clé dans `.env`")
    except ImportError:
        st.caption("❌ Module non disponible")

    st.markdown("---")
    st.markdown("### ⏱️ Cadence API")
    current_delay = (
        float(st.session_state.get("api_current_delay", API_DELAY_SECONDS))
        if "api_current_delay" in st.session_state
        else API_DELAY_SECONDS
    )
    st.caption(f"Délai de base : {API_DELAY_SECONDS:.2f}s")
    st.caption(f"Délai actuel : {current_delay:.2f}s")
    st.caption(f"Limite import : {API_IMPORT_MAX_COMPANIES} lignes")

    st.markdown("---")
    st.caption("⚠️ 10-20 % des entreprises publient leurs comptes")
    st.markdown("[Documentation API](https://recherche-entreprises.api.gouv.fr/)")
