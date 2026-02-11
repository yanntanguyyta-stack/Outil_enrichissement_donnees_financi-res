"""
Test pour comprendre pourquoi les données financières ne sont pas récupérées.
"""
import requests
import json
import time

API_BASE_URL = "https://recherche-entreprises.api.gouv.fr"

# Liste d'entreprises de test variées
test_companies = {
    "Airbus": "383474814",
    "Total Energies": "542051180", 
    "Orange": "380129866",
    "Renault": "441639465",
    "LVMH": "775670417",
    "Carrefour": "652014051",
    "BNP Paribas": "662042449",
    "Société Générale": "552120222",
}

def test_financial_data():
    """Test la récupération des données financières."""
    print("="*80)
    print("TEST DE RÉCUPÉRATION DES DONNÉES FINANCIÈRES")
    print("="*80 + "\n")
    
    with_finance = 0
    without_finance = 0
    
    for name, siren in test_companies.items():
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
                    
                    # Vérifier les finances
                    finances = result.get("finances")
                    
                    print(f"\n{'─'*80}")
                    print(f"🏢 {name} (SIREN: {siren})")
                    print(f"{'─'*80}")
                    
                    if finances:
                        print(f"✅ DONNÉES FINANCIÈRES DISPONIBLES")
                        print(f"   Structure: {type(finances)}")
                        print(f"   Contenu: {json.dumps(finances, indent=2, ensure_ascii=False)}")
                        with_finance += 1
                    else:
                        print(f"❌ PAS DE DONNÉES FINANCIÈRES")
                        print(f"   Valeur: {finances}")
                        without_finance += 1
                    
                    # Afficher d'autres infos utiles
                    cat = result.get("categorie_entreprise", "N/A")
                    effectif = result.get("tranche_effectif_salarie", "N/A")
                    print(f"   Catégorie: {cat}")
                    print(f"   Effectif: {effectif}")
                    print(f"   Date création: {result.get('date_creation', 'N/A')}")
                    
            time.sleep(0.6)  # Rate limiting
            
        except Exception as e:
            print(f"❌ Erreur pour {name}: {e}")
    
    print(f"\n{'='*80}")
    print(f"RÉSUMÉ")
    print(f"{'='*80}")
    print(f"✅ Avec données financières: {with_finance}/{len(test_companies)}")
    print(f"❌ Sans données financières: {without_finance}/{len(test_companies)}")
    print(f"📊 Taux de disponibilité: {(with_finance/len(test_companies)*100):.1f}%")
    print(f"\n💡 EXPLICATION:")
    print(f"   Les données financières (CA, résultat net) ne sont disponibles")
    print(f"   QUE pour les entreprises qui les déclarent publiquement.")
    print(f"   Beaucoup d'entreprises, notamment les PME, n'ont pas")
    print(f"   l'obligation de publier leurs comptes.")

if __name__ == "__main__":
    test_financial_data()
