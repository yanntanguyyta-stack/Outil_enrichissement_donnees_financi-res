#!/usr/bin/env python3
"""
Test du traitement par lots optimisé pour l'enrichissement RNE
"""

from enrichment_hybrid import (
    group_sirens_by_rne_file,
    process_batch,
    enrich_batch_parallel
)

def test_grouping():
    """Test du regroupement par fichier RNE"""
    print("\n" + "="*80)
    print("🧪 TEST 1: Regroupement par fichier RNE")
    print("="*80)
    
    # SIRENs de test (différents fichiers RNE)
    test_sirens = [
        "552100554",  # EDF
        "005880596",  # Dans stock_000001.json
        "775665019",  # Dans un autre fichier
        "123456789",  # Exemple
        "987654321",  # Exemple
    ]
    
    grouped = group_sirens_by_rne_file(test_sirens)
    
    print(f"\n📊 {len(test_sirens)} SIRENs → {len(grouped)} fichier(s) RNE\n")
    
    for filename, sirens in grouped.items():
        print(f"   📄 {filename}")
        print(f"      └─ {len(sirens)} SIREN(s): {', '.join(sirens)}")
    
    return grouped


def test_single_batch():
    """Test du traitement d'un seul lot"""
    print("\n" + "="*80)
    print("🧪 TEST 2: Traitement d'un lot unique")
    print("="*80)
    
    # Tester avec un SIREN connu
    test_sirens = ["552100554"]  # EDF
    
    grouped = group_sirens_by_rne_file(test_sirens)
    
    if not grouped:
        print("❌ Aucun fichier trouvé")
        return
    
    # Traiter le premier fichier
    filename, sirens = list(grouped.items())[0]
    results = process_batch(filename, sirens, max_bilans=3, cleanup=False)
    
    print(f"\n📋 Résultats:")
    for siren, data in results.items():
        if data.get('success'):
            print(f"   ✅ {siren}: {data.get('nb_bilans')} bilan(s) - {data.get('denomination', 'N/A')}")
        else:
            print(f"   ❌ {siren}: {data.get('error', 'Erreur')}")
    
    return results


def test_parallel_batch():
    """Test du traitement parallèle"""
    print("\n" + "="*80)
    print("🧪 TEST 3: Traitement parallèle optimisé")
    print("="*80)
    
    # SIRENs de test (multiple fichiers)
    test_sirens = [
        "552100554",  # EDF
        "005880596",  # Autre entreprise
        "775665019",  # Encore une autre
    ]
    
    print(f"\n📊 Test avec {len(test_sirens)} entreprises")
    
    results = enrich_batch_parallel(
        test_sirens,
        max_bilans=3,
        max_workers=2  # 2 fichiers en parallèle pour le test
    )
    
    print(f"\n📋 Résultats finaux:")
    for siren, data in results.items():
        if data.get('success'):
            bilans = data.get('bilans', [])
            if bilans:
                latest = bilans[0]
                print(f"   ✅ {siren}: {data.get('denomination', 'N/A')}")
                print(f"      └─ CA: {latest.get('chiffre_affaires', 'N/A')}")
                print(f"      └─ Date: {latest.get('date_cloture', 'N/A')}")
        else:
            print(f"   ❌ {siren}: {data.get('error', 'Erreur')}")
    
    return results


def test_large_volume():
    """Simulation d'un gros volume"""
    print("\n" + "="*80)
    print("🧪 TEST 4: Simulation gros volume (sans téléchargement)")
    print("="*80)
    
    # Créer une liste de SIRENs de test
    # En pratique, on aurait récupéré ces SIRENs de l'API DINUM
    test_sirens = [
        "552100554",
        "005880596",
        "775665019",
        "123456789",
        "987654321",
        "111222333",
        "444555666",
        "777888999",
    ] * 10  # 80 SIRENs au total
    
    print(f"\n📊 Simulation avec {len(test_sirens)} entreprises")
    
    # Grouper pour voir la répartition
    grouped = group_sirens_by_rne_file(test_sirens)
    
    print(f"\n📦 Répartition:")
    print(f"   📄 Fichiers RNE différents: {len(grouped)}")
    
    sizes = [len(sirens) for sirens in grouped.values()]
    print(f"   📊 Taille moyenne par lot: {sum(sizes)/len(sizes):.1f} entreprises")
    print(f"   📊 Plus gros lot: {max(sizes)} entreprises")
    print(f"   📊 Plus petit lot: {min(sizes)} entreprises")
    
    # Estimation du temps
    avg_download_time = 7  # secondes par fichier
    with_parallel = len(grouped) * avg_download_time / 3  # 3 workers
    without_parallel = len(grouped) * avg_download_time
    
    print(f"\n⏱️  Estimation temps:")
    print(f"   Séquentiel: ~{int(without_parallel)}s")
    print(f"   Parallèle (3 workers): ~{int(with_parallel)}s")
    print(f"   Gain: {int((1 - with_parallel/without_parallel) * 100)}%")
    
    return grouped


if __name__ == "__main__":
    print("\n" + "="*80)
    print("🧪 SUITE DE TESTS - TRAITEMENT PAR LOTS OPTIMISÉ")
    print("="*80)
    
    try:
        # Test 1: Regroupement
        test_grouping()
        
        # Test 2: Lot unique (nécessite connexion FTP)
        print("\n\n⚠️  Tests 2-3 nécessitent une connexion FTP active")
        response = input("Continuer avec les tests FTP ? (o/N): ")
        
        if response.lower() == 'o':
            test_single_batch()
            test_parallel_batch()
        
        # Test 4: Simulation (sans FTP)
        test_large_volume()
        
        print("\n" + "="*80)
        print("✅ TOUS LES TESTS TERMINÉS")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Erreur lors des tests: {e}")
        import traceback
        traceback.print_exc()
