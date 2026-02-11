#!/usr/bin/env python3
"""Script simple pour créer l'index RNE"""

import json
import zipfile
from collections import defaultdict
from datetime import datetime

ZIP_PATH = "/workspaces/TestsMCP/stock_comptes_annuels.zip"
INDEX_PATH = "/workspaces/TestsMCP/rne_siren_index.json"

print("="*80)
print("📦 Création de l'index RNE")
print("="*80)
print(f"\nFichier ZIP: {ZIP_PATH}")

# Ouvrir le ZIP
with zipfile.ZipFile(ZIP_PATH, 'r') as zf:
    json_files = [f for f in zf.namelist() if f.endswith('.json')]
    print(f"Fichiers JSON trouvés: {len(json_files)}\n")
    
    index = {}
    total_bilans = 0
    
    for i, json_file in enumerate(json_files, 1):
        if i % 50 == 0:
            pct = (i / len(json_files)) * 100
            print(f"Progression: {i}/{len(json_files)} ({pct:.1f}%) - {len(index):,} entreprises, {total_bilans:,} bilans")
        
        try:
            with zf.open(json_file) as f:
                data = json.loads(f.read().decode('utf-8'))
                
                for bilan in data:
                    siren = bilan.get('siren')
                    if siren:
                        if siren not in index:
                            index[siren] = {'file': json_file, 'count': 0}
                        index[siren]['count'] += 1
                        total_bilans += 1
        except Exception as e:
            print(f"   Erreur {json_file}: {e}")

# Sauvegarder
print(f"\n💾 Sauvegarde de l'index...")
with open(INDEX_PATH, 'w', encoding='utf-8') as f:
    json.dump({
        'index': index,
        'stats': {
            'total_files': len(json_files),
            'total_companies': len(index),
            'total_bilans': total_bilans,
            'created_at': datetime.now().isoformat()
        }
    }, f, ensure_ascii=False, indent=2)

print(f"\n✅ Index créé !")
print(f"   Entreprises: {len(index):,}")
print(f"   Bilans: {total_bilans:,}")
print(f"   Fichier: {INDEX_PATH}")
