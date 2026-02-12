#!/usr/bin/env python3
"""
Test du Mode Streaming - Extraction des 6 indicateurs clés uniquement
"""

import json
import sys
from pathlib import Path

# Importer la fonction depuis enrichment_hybrid
sys.path.insert(0, '/workspaces/TestsMCP')
from enrichment_hybrid import extract_key_metrics_only, LIASSE_CODES

def test_streaming_extraction():
    """Tester l'extraction en mode streaming"""
    print("=" * 80)
    print("🧪 TEST MODE STREAMING")
    print("=" * 80)
    
    cache_dir = Path("/workspaces/TestsMCP/rne_cache")
    test_file = cache_dir / "stock_000001.json"
    
    if not test_file.exists():
        print("❌ Fichier de test non trouvé:", test_file)
        return
    
    # Charger le fichier complet
    print(f"\n📂 Chargement de {test_file.name}...")
    with open(test_file, 'r') as f:
        data_complete = json.load(f)
    
    print(f"  Nombre d'entreprises: {len(data_complete)}")
    
    # Calculer taille avant
    json_complete = json.dumps(data_complete)
    taille_complete = len(json_complete) / (1024 * 1024)
    print(f"  Taille complète: {taille_complete:.1f} MB")
    
    # Extraire en mode streaming
    print(f"\n🗜️  Extraction des 6 indicateurs clés...")
    data_streaming = extract_key_metrics_only(data_complete)
    
    # Calculer taille après
    json_streaming = json.dumps(data_streaming)
    taille_streaming = len(json_streaming) / (1024 * 1024)
    reduction = 100 * (1 - taille_streaming / taille_complete)
    
    print(f"  Taille streaming: {taille_streaming:.2f} MB")
    print(f"  Réduction: {reduction:.1f}%")
    print(f"  💾 Gain: {taille_complete - taille_streaming:.1f} MB")
    
    # Analyser le résultat
    print(f"\n📊 Analyse du résultat:")
    print(f"  Nombre d'entreprises: {len(data_streaming)}")
    
    # Afficher un exemple
    if data_streaming:
        exemple = data_streaming[0]
        print(f"\n🔍 Exemple (première entreprise):")
        print(f"  SIREN: {exemple.get('siren')}")
        print(f"  Date clôture: {exemple.get('dateCloture')}")
        print(f"  Date dépôt: {exemple.get('dateDepot')}")
        print(f"  Type bilan: {exemple.get('typeBilan')}")
        print(f"  Métriques extraites:")
        
        metrics = exemple.get('metrics', {})
        if metrics:
            for code, values in metrics.items():
                nom = LIASSE_CODES.get(code, "Inconnu")
                m1 = values.get('m1') if isinstance(values, dict) else values
                print(f"    - {code} ({nom}): {m1}")
        else:
            print(f"    ⚠️  Aucune métrique trouvée pour cette entreprise")
    
    # Compter les entreprises avec des données
    avec_donnees = sum(1 for e in data_streaming if e.get('metrics'))
    print(f"\n📈 Statistiques:")
    print(f"  Entreprises avec données financières: {avec_donnees}/{len(data_streaming)} ({100*avec_donnees/len(data_streaming):.1f}%)")
    
    # Sauvegarder un exemple
    output_file = cache_dir / "exemple_streaming.json"
    with open(output_file, 'w') as f:
        json.dump(data_streaming[:10], f, indent=2)  # Seulement les 10 premières
    
    print(f"\n✅ Exemple sauvegardé dans: {output_file}")
    print(f"   Taille: {output_file.stat().st_size / 1024:.1f} KB (vs {taille_complete * 1024 / len(data_complete) * 10:.1f} KB en format complet)")

if __name__ == "__main__":
    test_streaming_extraction()
    print("\n" + "=" * 80)
    print("✅ Test terminé")
    print("=" * 80)
