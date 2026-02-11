"""
Test spécifique pour le SIREN 449162163 et debug de l'extraction des données.
"""
import requests
import json

API_BASE_URL = "https://recherche-entreprises.api.gouv.fr"

def test_specific_siren(siren):
    """Test un SIREN spécifique et affiche toute la structure."""
    print(f"="*80)
    print(f"TEST DEBUG pour SIREN: {siren}")
    print(f"="*80 + "\n")
    
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
                
                print(f"✅ Entreprise trouvée: {result.get('nom_complet', 'N/A')}\n")
                
                # Afficher la structure finances
                print("="*80)
                print("STRUCTURE DES DONNÉES FINANCIÈRES")
                print("="*80)
                
                finances = result.get("finances")
                print(f"Type de 'finances': {type(finances)}")
                print(f"Valeur de 'finances': {finances}")
                print(f"Bool de 'finances': {bool(finances)}")
                
                if finances:
                    print(f"\nClés dans finances: {list(finances.keys())}")
                    for year, data in finances.items():
                        print(f"\n  Année {year}:")
                        print(f"    Type: {type(data)}")
                        print(f"    Contenu: {json.dumps(data, indent=6)}")
                
                # Test de l'extraction comme dans le code
                print("\n" + "="*80)
                print("TEST D'EXTRACTION (comme dans le code)")
                print("="*80)
                
                finances = result.get("finances") or {}
                print(f"1. finances après get: {finances}")
                print(f"2. Type: {type(finances)}")
                print(f"3. Bool: {bool(finances)}")
                print(f"4. Len: {len(finances) if finances else 0}")
                
                if finances:
                    latest_year = max(finances.keys()) if finances else None
                    print(f"5. Latest year: {latest_year}")
                    
                    if latest_year:
                        year_data = finances[latest_year]
                        ca = year_data.get("ca", "N/A")
                        resultat_net = year_data.get("resultat_net", "N/A")
                        print(f"6. CA: {ca}")
                        print(f"7. Résultat net: {resultat_net}")
                else:
                    print("❌ finances est vide ou False!")
                
                # Afficher toutes les clés disponibles
                print("\n" + "="*80)
                print("TOUTES LES CLÉS DISPONIBLES")
                print("="*80)
                print(json.dumps(list(result.keys()), indent=2))
                
        else:
            print(f"❌ Erreur API: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Test avec le SIREN fourni par l'utilisateur
    test_specific_siren("449162163")
    
    print("\n\n" + "="*80)
    print("Test avec Airbus (référence)")
    print("="*80)
    test_specific_siren("383474814")
