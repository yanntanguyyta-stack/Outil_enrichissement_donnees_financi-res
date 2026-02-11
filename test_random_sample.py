"""
Test simple pour comprendre la disponibilité des données financières
en recherchant des entreprises aléatoires.
"""
import requests
import json
import time

API_BASE_URL = "https://recherche-entreprises.api.gouv.fr"

def test_random_companies():
    """Teste plusieurs entreprises de recherche générale."""
    
    print("="*80)
    print("TEST : Échantillon aléatoire d'entreprises")
    print("="*80 + "\n")
    
    # Recherche générale pour avoir un échantillon varié
    try:
        response = requests.get(
            f"{API_BASE_URL}/search",
            params={"q": "France", "per_page": 20},  # 20 entreprises diverses
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            companies = data.get("results", [])
            
            with_finance = 0
            without_finance = 0
            
            stats_by_category = {}
            
            for company in companies:
                name = company.get("nom_complet", "N/A")[:40]
                siren = company.get("siren", "N/A")
                finances = company.get("finances")
                cat = company.get("categorie_entreprise") or "Non classé"
                effectif = company.get("tranche_effectif_salarie", "N/A")
                
                # Statistiques par catégorie
                if cat not in stats_by_category:
                    stats_by_category[cat] = {"with": 0, "without": 0}
                
                has_finance = bool(finances and len(finances) > 0)
                
                if has_finance:
                    with_finance += 1
                    stats_by_category[cat]["with"] += 1
                    status = "✅"
                    years = list(finances.keys())
                    ca = finances[years[0]].get("ca", "N/A")
                    year_info = f"Année: {years[0]}, CA: {ca:,}" if isinstance(ca, int) else "N/A"
                else:
                    without_finance += 1
                    stats_by_category[cat]["without"] += 1
                    status = "❌"
                    year_info = "Pas de données"
                
                print(f"{status} {name:40} | Cat: {cat:5} | Effectif: {effectif:3} | {year_info}")
            
            print(f"\n{'='*80}")
            print(f"RÉSUMÉ GLOBAL")
            print(f"{'='*80}")
            print(f"Total entreprises testées: {len(companies)}")
            print(f"✅ Avec données financières: {with_finance} ({(with_finance/len(companies)*100):.1f}%)")
            print(f"❌ Sans données financières: {without_finance} ({(without_finance/len(companies)*100):.1f}%)")
            
            print(f"\n{'='*80}")
            print(f"DÉTAIL PAR CATÉGORIE")
            print(f"{'='*80}")
            for cat, stats in sorted(stats_by_category.items()):
                total = stats["with"] + stats["without"]
                rate = (stats["with"]/total*100) if total > 0 else 0
                print(f"{cat:15} | Total: {total:2} | ✅ {stats['with']:2} | ❌ {stats['without']:2} | Taux: {rate:5.1f}%")
            
            print(f"\n{'='*80}")
            print(f"💡 EXPLICATIONS")
            print(f"{'='*80}")
            print(f"""
📌 Obligation de publication des comptes en France :

✅ OBLIGÉES de publier :
   • Grandes Entreprises (GE) : > 5000 salariés OU CA > 1,5 Mrd€ OU bilan > 2 Mrd€
   • ETI : entre 250 et 5000 salariés
   • Sociétés cotées en bourse
   • Sociétés de plus de 50 salariés (simplifiés)

❌ NON OBLIGÉES :
   • PME de moins de 50 salariés
   • Micro-entreprises
   • Associations (sauf certaines)
   • Professions libérales
   
➡️ Résultat : Sur 100 entreprises françaises aléatoires, seulement 
   10-20% environ publient leurs données financières dans l'API publique.
            """)
            
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    test_random_companies()
