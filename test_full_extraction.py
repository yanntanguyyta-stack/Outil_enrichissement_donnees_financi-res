"""
Test complet de la chaîne d'extraction avec le code de l'app.
"""
import sys
sys.path.insert(0, '/workspaces/TestsMCP')

import requests
import re

API_BASE_URL = "https://recherche-entreprises.api.gouv.fr"
API_DELAY_SECONDS = 0.5

def _format_etat(etat):
    """Format the administrative state."""
    if etat == "A":
        return "Active"
    if etat == "C":
        return "Cessée"
    return etat

def _format_currency(value):
    """Format a numeric value as currency."""
    print(f"  DEBUG _format_currency - Input: {value}, Type: {type(value)}")
    if isinstance(value, (int, float)) and value != "N/A":
        result = f"{value:,.0f} €"
        print(f"  DEBUG _format_currency - Output: {result}")
        return result
    print(f"  DEBUG _format_currency - Pas de formatage, retour: {value}")
    return value

def extract_financial_info(company_data, original_siret=None):
    """Extract comprehensive information from company data."""
    
    print("\n" + "="*80)
    print("DEBUG: Extraction des informations")
    print("="*80)
    
    # Base structures
    finances = company_data.get("finances") or {}
    print(f"finances: {finances}")
    
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
    
    print(f"\n1. finances dict: {finances}")
    print(f"2. bool(finances): {bool(finances)}")
    
    if finances:
        print("3. finances est truthy, extraction...")
        # L'API retourne un dict avec l'année comme clé: {"2024": {"ca": ..., "resultat_net": ...}}
        latest_year = max(finances.keys()) if finances else None
        print(f"4. latest_year: {latest_year}")
        
        if latest_year:
            annee_finance = latest_year
            year_data = finances[latest_year]
            print(f"5. year_data: {year_data}")
            
            ca = year_data.get("ca", "N/A")
            resultat_net = year_data.get("resultat_net", "N/A")
            
            print(f"6. ca (avant format): {ca}, type: {type(ca)}")
            print(f"7. resultat_net (avant format): {resultat_net}, type: {type(resultat_net)}")
    else:
        print("3. finances est falsy, pas d'extraction")
    
    # Dirigeants - formater la liste
    dirigeants_str = "N/A"
    if dirigeants:
        dir_list = []
        for d in dirigeants[:5]:
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
    
    # Certifications
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
    
    print(f"\n8. Avant _format_currency:")
    print(f"   ca = {ca}")
    print(f"   resultat_net = {resultat_net}")
    
    ca_formatted = _format_currency(ca)
    resultat_net_formatted = _format_currency(resultat_net)
    
    print(f"\n9. Après _format_currency:")
    print(f"   ca_formatted = {ca_formatted}")
    print(f"   resultat_net_formatted = {resultat_net_formatted}")
    
    info = {
        # Identification
        "SIRET": siret,
        "SIREN": siren,
        "Vérification SIREN": siren_verifie,
        "Nom": company_data.get("nom_complet", company_data.get("nom_raison_sociale", "N/A")),
        
        # Finances
        "Année finances": annee_finance,
        "Chiffre d'affaires (CA)": ca_formatted,
        "Résultat net": resultat_net_formatted,
    }
    
    print(f"\n10. Info dict (extrait):")
    print(f"   Année finances: {info['Année finances']}")
    ca_key = "Chiffre d'affaires (CA)"
    print(f"   CA: {info[ca_key]}")
    print(f"   Résultat net: {info['Résultat net']}")
    
    return info

def test_extraction(siren):
    """Test l'extraction complète."""
    print(f"\n{'#'*80}")
    print(f"# TEST EXTRACTION POUR SIREN: {siren}")
    print(f"{'#'*80}")
    
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
                info = extract_financial_info(result)
                
                print(f"\n{'='*80}")
                print(f"RÉSULTAT FINAL")
                print(f"{'='*80}")
                for key, value in info.items():
                    print(f"{key:30}: {value}")
                    
                return info
        else:
            print(f"❌ Erreur API: {response.status_code}")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Test avec le SIREN problématique
    test_extraction("449162163")
    
    # Test avec Airbus
    print("\n\n")
    test_extraction("383474814")
