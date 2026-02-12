#!/usr/bin/env python3
"""
Convertir tous les fichiers en cache au format Streaming
Économise ~96% d'espace disque : 5.2 GB → ~200 MB
"""

import json
from pathlib import Path
import sys

sys.path.insert(0, '/workspaces/TestsMCP')
from enrichment_hybrid import extract_key_metrics_only

def convert_cache_to_streaming():
    """Convertir tous les fichiers en cache au format streaming"""
    cache_dir = Path("/workspaces/TestsMCP/rne_cache")
    
    files = sorted(cache_dir.glob("stock_*.json"))
    
    if not files:
        print("❌ Aucun fichier à convertir")
        return
    
    print(f"🔄 Conversion de {len(files)} fichiers au format Streaming...")
    print("="*80)
    
    total_avant = 0
    total_apres = 0
    
    for i, filepath in enumerate(files, 1):
        try:
            # Charger
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            taille_avant = filepath.stat().st_size / (1024 * 1024)
            total_avant += taille_avant
            
            # Vérifier si déjà converti
            if data and 'metrics' in data[0]:
                print(f"⏭️  {i:3}/{len(files)} {filepath.name:20s} - Déjà au format streaming")
                taille_apres = taille_avant
            else:
                # Convertir
                data_streaming = extract_key_metrics_only(data)
                
                # Sauvegarder
                with open(filepath, 'w') as f:
                    json.dump(data_streaming, f)
                
                taille_apres = filepath.stat().st_size / (1024 * 1024)
                reduction = 100 * (1 - taille_apres / taille_avant)
                
                print(f"✅ {i:3}/{len(files)} {filepath.name:20s} - {taille_avant:5.1f} MB → {taille_apres:5.1f} MB ({reduction:4.1f}%)")
            
            total_apres += taille_apres
            
        except Exception as e:
            print(f"❌ {i:3}/{len(files)} {filepath.name:20s} - ERREUR: {e}")
    
    print("="*80)
    print(f"✅ Conversion terminée !")
    print(f"   Taille avant: {total_avant:.1f} MB ({total_avant/1024:.2f} GB)")
    print(f"   Taille après: {total_apres:.1f} MB ({total_apres/1024:.2f} GB)")
    print(f"   Réduction: {100 * (1 - total_apres/total_avant):.1f}%")
    print(f"   💾 Gain: {(total_avant - total_apres)/1024:.2f} GB")

if __name__ == "__main__":
    import time
    start = time.time()
    convert_cache_to_streaming()
    duration = time.time() - start
    print(f"\n⏱️  Durée: {duration:.1f}s")
