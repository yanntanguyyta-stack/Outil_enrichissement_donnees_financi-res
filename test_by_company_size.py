"""
Test avec des PME pour comprendre la disponibilité des données financières.
"""
import requests
import json
import time

API_BASE_URL = "https://recherche-entreprises.api.gouv.fr"

def search_companies_by_size():
    """Recherche des entreprises de différentes tailles."""
    
    # Test avec des entreprises de différentes catégories
    queries = [
        ("Grandes Entreprises (GE)", "categorie_entreprise:GE", 5),
        ("ETI", "categorie_entreprise:ETI", 5),
        ("PME", "categorie_entreprise:PME", 5),
        ("Sans catégorie", "-categorie_entreprise:[* TO *]", 5),
    ]
    
    results = {}
    
    for category_name, query, per_page in queries:
        print(f"\n{'='*80}")
        print(f"Catégorie: {category_name}")
        print(f"{'='*80}")
        
        try:
            response = requests.get(
                f"{API_BASE_URL}/search",
                params={"q": query, "per_page": per_page},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                companies = data.get("results", [])
                
                with_finance = 0
                without_finance = 0
                
                for company in companies:
                    name = company.get("nom_complet", "N/A")[:40]
                    siren = company.get("siren", "N/A")
                    finances = company.get("finances")
                    cat = company.get("categorie_entreprise", "N/A")
                    
                    if finances and len(finances) > 0:
                        with_finance += 1
                        status = "✅"
                        # Extraire l'année
                        years = list(finances.keys())
                        year_info = f"(année: {', '.join(years)})"
                    else:
                        without_finance += 1
                        status = "❌"
                        year_info = ""
                    
                    print(f"{status} {name:40} | {siren} | Cat: {cat:3} {year_info}")
                
                results[category_name] = {
                    "with": with_finance,
                    "without": without_finance,
                    "total": len(companies)
                }
                
                print(f"\n📊 Résumé {category_name}:")
                print(f"   ✅ Avec finances: {with_finance}/{len(companies)}")
                print(f"   ❌ Sans finances: {without_finance}/{len(companies)}")
                if len(companies) > 0:
                    print(f"   📈 Taux: {(with_finance/len(companies)*100):.1f}%")
                
            time.sleep(0.6)
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
    
    print(f"\n{'='*80}")
    print(f"SYNTHÈSE GLOBALE")
    print(f"{'='*80}")
    for cat, stats in results.items():
        if stats["total"] > 0:
            rate = (stats["with"]/stats["total"]*100)
            print(f"{cat:30} | {stats['with']}/{stats['total']} | {rate:.0f}%")
    
    print(f"\n💡 CONCLUSION:")
    print(f"   Les PME et petites entreprises n'ont généralement PAS")
    print(f"   l'obligation de publier leurs comptes. Seules les:")
    print(f"   - Grandes Entreprises (GE)")
    print(f"   - ETI (Entreprises de Taille Intermédiaire)")
    print(f"   - Sociétés cotées en bourse")
    print(f"   sont tenues de publier leurs données financières.")

if __name__ == "__main__":
    search_companies_by_size()
