#!/usr/bin/env python3
"""
Test du module d'enrichissement RNE avec les données locales
"""

import sys
sys.path.append('/workspaces/TestsMCP')

from enrichment_rne import enrich_with_rne, display_rne_data
import json

def test_multiple_sirens():
    """Tester l'enrichissement avec plusieurs SIRENs"""
    
    print("="*80)
    print("🧪 TEST D'ENRICHISSEMENT RNE AVEC DONNÉES LOCALES")
    print("="*80)
    print()
    
    # Liste de SIRENs de test - des grandes entreprises françaises connues
    test_sirens = [
        ("005880596", "GEDIMO HOLDING"),
        ("552100554", "EDF"),
        ("542051180", "ORANGE"),
        ("552032534", "AIRBUS"),
        ("775665019", "TOTAL"),
    ]
    
    results = []
    
    for siren, expected_name in test_sirens:
        print(f"\n{'='*80}")
        print(f"🔍 Test avec SIREN: {siren} (attendu: {expected_name})")
        print('='*80)
        
        # Enrichir avec RNE
        rne_data = enrich_with_rne(siren, max_results=3)
        
        if rne_data["success"]:
            print(f"\n✅ Succès pour {siren}")
            print(f"   Dénomination: {rne_data['denomination']}")
            print(f"   Nombre de bilans: {rne_data['nb_bilans']}")
            
            # Afficher le dernier bilan
            if rne_data['bilans']:
                last_bilan = rne_data['bilans'][0]
                print(f"\n   📊 Dernier exercice ({last_bilan['date_cloture']}):")
                if last_bilan['chiffre_affaires']:
                    print(f"      CA: {last_bilan['chiffre_affaires']:,} €".replace(',', ' '))
                if last_bilan['resultat_net']:
                    print(f"      Résultat net: {last_bilan['resultat_net']:,} €".replace(',', ' '))
                if last_bilan['effectif']:
                    print(f"      Effectif: {last_bilan['effectif']} personnes")
            
            results.append({
                "siren": siren,
                "found": True,
                "name": rne_data['denomination'],
                "nb_bilans": rne_data['nb_bilans']
            })
        else:
            print(f"\n⚠️  Pas de données pour {siren}")
            print(f"   Raison: {rne_data.get('error', 'Inconnue')}")
            results.append({
                "siren": siren,
                "found": False,
                "error": rne_data.get('error', 'Inconnue')
            })
    
    # Résumé
    print(f"\n\n{'='*80}")
    print("📈 RÉSUMÉ DES TESTS")
    print('='*80)
    
    found_count = sum(1 for r in results if r.get('found'))
    total_count = len(results)
    
    print(f"\n   ✅ Trouvés: {found_count}/{total_count}")
    print(f"   ❌ Non trouvés: {total_count - found_count}/{total_count}")
    
    if found_count > 0:
        print(f"\n   💡 Les données RNE locales sont fonctionnelles !")
        print(f"   📁 {found_count} entreprise(s) trouvée(s) dans les fichiers extraits")
    
    # Détails
    print(f"\n   Détails:")
    for result in results:
        if result.get('found'):
            print(f"      ✅ {result['siren']}: {result['name']} ({result['nb_bilans']} bilans)")
        else:
            print(f"      ❌ {result['siren']}: Non trouvé")
    
    print(f"\n{'='*80}")
    
    return results

def check_extraction_status():
    """Vérifier l'état de l'extraction"""
    import os
    from pathlib import Path
    
    rne_dir = Path("/workspaces/TestsMCP/rne_data")
    if not rne_dir.exists():
        print("⚠️  Le répertoire rne_data n'existe pas encore")
        return 0
    
    json_files = list(rne_dir.glob("*.json"))
    total_expected = 1380
    
    print(f"\n📊 État de l'extraction:")
    print(f"   Fichiers extraits: {len(json_files)}/{total_expected}")
    print(f"   Progression: {len(json_files)*100/total_expected:.1f}%")
    
    if len(json_files) < total_expected:
        print(f"   ⏳ Extraction en cours... (lancez 'python3 setup_rne_data.py' si nécessaire)")
    else:
        print(f"   ✅ Extraction complète !")
    
    return len(json_files)

if __name__ == "__main__":
    # Vérifier l'état de l'extraction
    nb_files = check_extraction_status()
    
    if nb_files == 0:
        print("\n❌ Aucun fichier extrait. Lancez d'abord: python3 setup_rne_data.py")
        sys.exit(1)
    
    # Lancer les tests
    print(f"\n🚀 Lancement des tests avec {nb_files} fichiers disponibles...\n")
    test_multiple_sirens()
