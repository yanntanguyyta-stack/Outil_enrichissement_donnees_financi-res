#!/usr/bin/env python3
"""
Créer un index ultra-léger des ranges de SIRENs par fichier
Taille de l'index: ~50 KB au lieu de 50 MB !
"""

import zipfile
import json
from pathlib import Path
from datetime import datetime

ZIP_PATH = "/workspaces/TestsMCP/stock_comptes_annuels.zip"
INDEX_FILE = "/workspaces/TestsMCP/rne_siren_ranges.json"

print("="*80)
print("📊 Création d'un INDEX ULTRA-LÉGER par ranges de SIRENs")
print("="*80)
print()

with zipfile.ZipFile(ZIP_PATH, 'r') as zf:
    json_files = sorted([f for f in zf.namelist() if f.endswith('.json')])
    print(f"🔍 Analyse de {len(json_files)} fichiers...\n")
    
    ranges = []
    stats = {
        'total_files': len(json_files),
        'total_companies': 0,
        'total_bilans': 0,
        'created_at': datetime.now().isoformat()
    }
    
    for i, json_file in enumerate(json_files, 1):
        if i % 50 == 0:
            print(f"   Progression: {i}/{len(json_files)} ({i*100/len(json_files):.1f}%)")
        
        try:
            with zf.open(json_file) as f:
                data = json.loads(f.read().decode('utf-8'))
                
                sirens = sorted([b.get('siren') for b in data if b.get('siren')])
                unique_sirens = sorted(set(sirens))
                
                if unique_sirens:
                    ranges.append({
                        'file': json_file,
                        'siren_min': unique_sirens[0],
                        'siren_max': unique_sirens[-1],
                        'companies': len(unique_sirens),
                        'bilans': len(sirens)
                    })
                    
                    stats['total_companies'] += len(unique_sirens)
                    stats['total_bilans'] += len(sirens)
        
        except Exception as e:
            print(f"   ⚠️  Erreur {json_file}: {e}")
    
    print()
    print("💾 Sauvegarde de l'index...")
    
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            'ranges': ranges,
            'stats': stats,
            'format_version': '2.0-ranges'
        }, f, ensure_ascii=False, indent=2)
    
    index_size = Path(INDEX_FILE).stat().st_size
    
    print(f"\n✅ Index créé avec succès !")
    print(f"\n📈 Statistiques:")
    print(f"   - Fichiers indexés: {len(ranges)}")
    print(f"   - Entreprises uniques: {stats['total_companies']:,}")
    print(f"   - Bilans totaux: {stats['total_bilans']:,}")
    print(f"   - Taille de l'index: {index_size / 1024:.1f} KB")
    print(f"   - Fichier: {INDEX_FILE}")
    
    print(f"\n💡 Réduction:")
    estimated_full_index = stats['total_companies'] * 50  # ~50 bytes par SIREN
    reduction_factor = estimated_full_index / index_size
    print(f"   - Index complet estimé: {estimated_full_index / 1024**2:.1f} MB")
    print(f"   - Index ranges: {index_size / 1024:.1f} KB")
    print(f"   - Facteur de réduction: {reduction_factor:.0f}x")
    
    # Exemples
    print(f"\n🔍 Exemples de ranges:")
    for r in ranges[:5]:
        print(f"   {r['file']}: {r['siren_min']} → {r['siren_max']} ({r['companies']} entreprises)")

print("\n✨ Vous pouvez maintenant:")
print("   1. Supprimer le ZIP de 3,5 GB")
print("   2. Utiliser l'API DINUM + cet index pour enrichir à la demande")
print("   3. Committer l'index léger (~50 KB) dans Git")
