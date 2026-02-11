"""
Script de test pour vérifier le rate limiting de l'application.

Ce script simule des requêtes multiples pour vérifier que le délai
entre les requêtes est bien respecté.
"""
import time
import requests

API_BASE_URL = "https://recherche-entreprises.api.gouv.fr"
API_DELAY_SECONDS = 0.5  # Marge de sécurité de 50% (2 req/sec vs 4.17 max)

# Liste de test avec quelques entreprises françaises
test_companies = [
    "Airbus",
    "Total Energies",
    "Orange",
    "Renault",
    "LVMH"
]

def test_rate_limiting():
    """Test le rate limiting avec plusieurs requêtes."""
    print(f"🧪 Test du rate limiting avec {len(test_companies)} requêtes")
    print(f"⏱️  Délai configuré : {API_DELAY_SECONDS}s par requête")
    print(f"📊 Limite API : ~250 req/min (4.17 req/sec)")
    print(f"✅ Notre limite : {1/API_DELAY_SECONDS:.2f} req/sec (marge de sécurité de 50% incluse)\n")
    
    start_time = time.time()
    
    for i, company in enumerate(test_companies, 1):
        request_start = time.time()
        
        try:
            # Respecter le délai
            if i > 1:
                time.sleep(API_DELAY_SECONDS)
            
            # Faire la requête
            url = f"{API_BASE_URL}/search"
            params = {"q": company, "per_page": 1}
            response = requests.get(url, params=params, timeout=10)
            
            request_time = time.time() - request_start
            
            if response.status_code == 200:
                data = response.json()
                results_count = len(data.get("results", []))
                print(f"✅ {i}/{len(test_companies)} - {company}: "
                      f"{results_count} résultat(s) - {request_time:.2f}s")
            else:
                print(f"⚠️  {i}/{len(test_companies)} - {company}: "
                      f"Status {response.status_code} - {request_time:.2f}s")
                
        except Exception as e:
            request_time = time.time() - request_start
            print(f"❌ {i}/{len(test_companies)} - {company}: "
                  f"Erreur - {str(e)[:50]} - {request_time:.2f}s")
    
    total_time = time.time() - start_time
    avg_time = total_time / len(test_companies)
    
    print(f"\n📈 Résultats:")
    print(f"   Temps total : {total_time:.2f}s")
    print(f"   Temps moyen par requête : {avg_time:.2f}s")
    print(f"   Débit effectif : {len(test_companies)/total_time:.2f} req/sec")
    print(f"   Débit limite API : 4.17 req/sec")
    print(f"   Marge de sécurité : {(1 - (len(test_companies)/total_time)/4.17)*100:.1f}%")

if __name__ == "__main__":
    test_rate_limiting()
