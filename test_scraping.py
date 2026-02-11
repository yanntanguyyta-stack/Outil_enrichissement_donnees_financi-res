"""
Test du module de scraping Pappers.fr
Teste le scraping avec délais aléatoires
"""

import os
import time
from dotenv import load_dotenv

# Forcer le mode scraping pour les tests
os.environ['SCRAPING_ENABLED'] = 'true'
os.environ['SCRAPING_MIN_DELAY'] = '1.0'  # Délais réduits pour les tests
os.environ['SCRAPING_MAX_DELAY'] = '2.0'

# Charger après avoir défini les variables
load_dotenv()

from enrichment_pappers import (
    scrape_company_data_pappers,
    get_company_data_unified,
    extract_financial_history,
    _format_currency,
    SCRAPING_MIN_DELAY,
    SCRAPING_MAX_DELAY
)

def test_scraping():
    """Test le scraping de données Pappers"""
    
    print("🧪 Test du module de scraping Pappers.fr")
    print(f"⏱️  Délais aléatoires configurés: {SCRAPING_MIN_DELAY}s - {SCRAPING_MAX_DELAY}s\n")
    
    # SIREN de test (grandes entreprises avec données publiques)
    test_companies = [
        ('449162163', 'CISCO SYSTEMS CAPITAL FRANCE'),
        ('552100554', 'CARREFOUR'),
        ('542065479', 'ORANGE')
    ]
    
    results = []
    start_time = time.time()
    
    for siren, name in test_companies:
        print(f"\n{'='*60}")
        print(f"🏢 Test: {name} (SIREN: {siren})")
        print(f"{'='*60}")
        
        company_start = time.time()
        
        # Test du scraping
        print("🔍 Scraping en cours...")
        data = scrape_company_data_pappers(siren)
        
        company_elapsed = time.time() - company_start
        
        if data:
            print(f"✅ Données récupérées en {company_elapsed:.2f}s")
            
            # Extraire les finances
            history = extract_financial_history(data)
            
            if history:
                print(f"📊 {len(history)} années de données financières trouvées")
                
                # Afficher les 3 dernières années
                for i, year_data in enumerate(history[:3]):
                    year = year_data.get('annee', 'N/A')
                    ca = year_data.get('ca')
                    resultat = year_data.get('resultat_net')
                    effectif = year_data.get('effectif')
                    
                    print(f"\n  📅 Année {year}:")
                    if ca:
                        print(f"    💰 CA: {_format_currency(ca)}")
                    if resultat:
                        print(f"    📈 Résultat net: {_format_currency(resultat)}")
                    if effectif:
                        print(f"    👥 Effectif: {effectif}")
                
                results.append({
                    'siren': siren,
                    'name': name,
                    'success': True,
                    'years': len(history),
                    'time': company_elapsed
                })
            else:
                print("⚠️  Aucune donnée financière extraite")
                results.append({
                    'siren': siren,
                    'name': name,
                    'success': False,
                    'years': 0,
                    'time': company_elapsed
                })
        else:
            print(f"❌ Échec du scraping après {company_elapsed:.2f}s")
            results.append({
                'siren': siren,
                'name': name,
                'success': False,
                'years': 0,
                'time': company_elapsed
            })
    
    # Statistiques globales
    total_elapsed = time.time() - start_time
    success_count = sum(1 for r in results if r['success'])
    total_years = sum(r['years'] for r in results)
    avg_time = total_elapsed / len(test_companies)
    
    print(f"\n\n{'='*60}")
    print("📊 STATISTIQUES GLOBALES")
    print(f"{'='*60}")
    print(f"✅ Succès: {success_count}/{len(test_companies)} ({success_count/len(test_companies)*100:.1f}%)")
    print(f"📅 Total années récupérées: {total_years}")
    print(f"⏱️  Temps total: {total_elapsed:.2f}s")
    print(f"⏱️  Temps moyen par entreprise: {avg_time:.2f}s")
    
    if success_count > 0:
        avg_years = total_years / success_count
        print(f"📈 Moyenne années par succès: {avg_years:.1f}")
    
    print(f"\n{'='*60}")
    print("⚠️  NOTE IMPORTANTE:")
    print("Le scraping peut être instable selon la structure HTML de Pappers.")
    print("Si les résultats sont incomplets, préférez l'API officielle.")
    print(f"{'='*60}\n")
    
    return results


def test_unified_mode():
    """Test le mode unifié (API + Scraping fallback)"""
    
    print("\n\n🔄 Test du mode unifié (API → Scraping fallback)")
    print("="*60)
    
    siren = '449162163'
    
    # Test avec préférence API (qui tombera sur scraping si pas de clé)
    print(f"\n📡 Tentative avec get_company_data_unified('{siren}')")
    
    start = time.time()
    data = get_company_data_unified(siren, prefer_api=True)
    elapsed = time.time() - start
    
    if data:
        history = extract_financial_history(data)
        print(f"✅ Données récupérées en {elapsed:.2f}s")
        print(f"📊 {len(history)} années disponibles")
        
        if history:
            latest = history[0]
            print(f"\n📅 Dernière année: {latest.get('annee')}")
            if latest.get('ca'):
                print(f"💰 CA: {_format_currency(latest.get('ca'))}")
            if latest.get('resultat_net'):
                print(f"📈 Résultat: {_format_currency(latest.get('resultat_net'))}")
    else:
        print(f"❌ Échec après {elapsed:.2f}s")


if __name__ == '__main__':
    print("""
╔══════════════════════════════════════════════════════════╗
║          TEST MODULE SCRAPING PAPPERS.FR                 ║
║                                                          ║
║  ⚠️  ATTENTION:                                          ║
║  - Délais aléatoires entre chaque requête               ║
║  - Le scraping peut être bloqué par Pappers             ║
║  - Structure HTML peut changer sans préavis             ║
║  - Pour usage intensif, préférez l'API officielle       ║
╚══════════════════════════════════════════════════════════╝
""")
    
    input("Appuyez sur Entrée pour lancer les tests...")
    
    # Test du scraping
    results = test_scraping()
    
    # Test du mode unifié
    test_unified_mode()
    
    print("\n✅ Tests terminés !")
