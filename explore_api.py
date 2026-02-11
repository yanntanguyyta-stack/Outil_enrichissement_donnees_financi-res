"""
Script d'exploration de l'API Recherche d'Entreprises pour identifier 
toutes les données disponibles, y compris l'historique financier.
"""
import requests
import json
import time

API_BASE_URL = "https://recherche-entreprises.api.gouv.fr"

def explore_company_data(siren):
    """Explore toutes les données disponibles pour un SIREN."""
    print(f"\n{'='*80}")
    print(f"Exploration des données pour SIREN: {siren}")
    print(f"{'='*80}\n")
    
    # 1. Recherche de base
    print("1️⃣ Recherche de base (/search)")
    print("-" * 80)
    try:
        response = requests.get(
            f"{API_BASE_URL}/search",
            params={"q": siren, "per_page": 1},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("results"):
                result = data["results"][0]
                print(json.dumps(result, indent=2, ensure_ascii=False))
                print(f"\n✅ Clés disponibles: {list(result.keys())}")
        else:
            print(f"❌ Erreur: {response.status_code}")
        time.sleep(0.5)
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    # 2. Recherche unitaire (endpoint détaillé)
    print(f"\n2️⃣ Recherche unitaire (/{siren})")
    print("-" * 80)
    try:
        response = requests.get(
            f"{API_BASE_URL}/{siren}",
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            print(json.dumps(data, indent=2, ensure_ascii=False))
            print(f"\n✅ Clés disponibles: {list(data.keys())}")
        else:
            print(f"❌ Erreur: {response.status_code} - {response.text[:200]}")
        time.sleep(0.5)
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    # 3. Vérifier si l'API offre des endpoints supplémentaires
    print(f"\n3️⃣ Tentative d'accès aux données financières historiques")
    print("-" * 80)
    endpoints_to_test = [
        f"/{siren}/finances",
        f"/{siren}/bilans",
        f"/{siren}/history",
        f"/{siren}/documents",
    ]
    
    for endpoint in endpoints_to_test:
        try:
            response = requests.get(f"{API_BASE_URL}{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {endpoint} - DISPONIBLE!")
                print(json.dumps(response.json(), indent=2, ensure_ascii=False)[:500])
            elif response.status_code == 404:
                print(f"❌ {endpoint} - Non disponible (404)")
            else:
                print(f"⚠️  {endpoint} - Status: {response.status_code}")
            time.sleep(0.5)
        except Exception as e:
            print(f"❌ {endpoint} - Erreur: {e}")

def test_multiple_companies():
    """Test avec plusieurs entreprises connues."""
    test_companies = {
        "Airbus": "383474814",
        "Total Energies": "542051180",
        "Orange": "380129866",
    }
    
    for name, siren in test_companies.items():
        print(f"\n\n{'#'*80}")
        print(f"# Test: {name}")
        print(f"{'#'*80}")
        explore_company_data(siren)
        time.sleep(1)  # Respecter le rate limiting

def check_api_documentation():
    """Vérifier la documentation de l'API."""
    print("\n" + "="*80)
    print("Documentation de l'API")
    print("="*80 + "\n")
    
    doc_endpoints = [
        "",
        "/docs",
        "/swagger",
        "/openapi.json",
        "/api-docs",
    ]
    
    for endpoint in doc_endpoints:
        try:
            url = f"{API_BASE_URL}{endpoint}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ Documentation trouvée: {url}")
                content_type = response.headers.get('content-type', '')
                if 'json' in content_type:
                    print(json.dumps(response.json(), indent=2)[:1000])
                else:
                    print(response.text[:1000])
        except Exception as e:
            pass
        time.sleep(0.3)

if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║  Exploration de l'API Recherche d'Entreprises                           ║
    ║  Objectif: Identifier toutes les données disponibles                    ║
    ╚══════════════════════════════════════════════════════════════════════════╝
    """)
    
    # 1. Vérifier la documentation
    check_api_documentation()
    
    # 2. Explorer les données d'une entreprise
    explore_company_data("383474814")  # Airbus
    
    # Décommenter pour tester plusieurs entreprises :
    # test_multiple_companies()
    
    print("\n" + "="*80)
    print("CONCLUSION")
    print("="*80)
    print("""
    L'API recherche-entreprises.api.gouv.fr fournit principalement:
    - Données d'identification (SIREN, SIRET, nom, adresse...)
    - Données légales (forme juridique, état administratif...)
    - Données de structure (nombre d'établissements, effectifs...)
    
    Pour l'historique financier détaillé sur plusieurs années, il faudrait
    explorer d'autres APIs comme:
    - entreprise.data.gouv.fr (API Entreprise - nécessite authentification)
    - pappers.fr API (service tiers)
    - infogreffe.fr (registre du commerce)
    """)
