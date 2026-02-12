#!/usr/bin/env python3
"""
Créer un index des SIRENs disponibles dans les données RNE
Cet index permet de trouver rapidement dans quel fichier se trouve un SIREN
"""

import json
import os
from pathlib import Path
from collections import defaultdict

RNE_DATA_DIR = "/workspaces/TestsMCP/rne_data"
INDEX_FILE = "/workspaces/TestsMCP/rne_data/siren_index.json"

def create_siren_index():
    """
    Créer un index mappant chaque SIREN vers le fichier qui le contient
    Format: {"SIREN": "nom_fichier.json"}
    """
    
    rne_dir = Path(RNE_DATA_DIR)
    if not rne_dir.exists():
        print("❌ Répertoire rne_data non trouvé")
        return
    
    json_files = list(rne_dir.glob("*.json"))
    if "siren_index.json" in [f.name for f in json_files]:
        json_files = [f for f in json_files if f.name != "siren_index.json"]
    
    print(f"📊 Indexation de {len(json_files)} fichiers...")
    
    siren_index = {}
    stats = {
        "total_files": len(json_files),
        "total_companies": 0,
        "total_bilans": 0,
        "files_processed": 0
    }
    
    for i, json_file in enumerate(json_files, 1):
        if i % 50 == 0:
            print(f"   Progression: {i}/{len(json_files)} fichiers...")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Grouper par SIREN
                companies_in_file = defaultdict(int)
                for bilan in data:
                    siren = bilan.get("siren")
                    if siren:
                        companies_in_file[siren] += 1
                        stats["total_bilans"] += 1
                
                # Ajouter à l'index
                for siren, count in companies_in_file.items():
                    if siren not in siren_index:
                        siren_index[siren] = {
                            "file": json_file.name,
                            "bilans_count": count
                        }
                        stats["total_companies"] += 1
                    else:
                        # Si le SIREN existe déjà, cumuler les bilans
                        siren_index[siren]["bilans_count"] += count
                
                stats["files_processed"] += 1
        
        except Exception as e:
            print(f"   ⚠️  Erreur avec {json_file.name}: {e}")
            continue
    
    # Sauvegarder l'index
    print(f"\n💾 Sauvegarde de l'index...")
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            "index": siren_index,
            "stats": stats,
            "created_at": str(Path(json_files[0]).stat().st_mtime) if json_files else None
        }, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Index créé avec succès !")
    print(f"\n📈 Statistiques:")
    print(f"   - Fichiers traités: {stats['files_processed']}")
    print(f"   - Entreprises uniques: {stats['total_companies']:,}")
    print(f"   - Bilans totaux: {stats['total_bilans']:,}")
    print(f"   - Index sauvegardé: {INDEX_FILE}")
    
    # Afficher quelques exemples
    print(f"\n🔍 Exemples de SIRENs disponibles:")
    for i, (siren, info) in enumerate(list(siren_index.items())[:10]):
        print(f"   - {siren}: {info['bilans_count']} bilan(s) dans {info['file']}")
    
    return siren_index, stats

def load_siren_index():
    """Charger l'index existant"""
    if not os.path.exists(INDEX_FILE):
        return None
    
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data.get("index"), data.get("stats")

def search_siren_fast(siren: str):
    """Recherche rapide d'un SIREN dans l'index"""
    index, stats = load_siren_index()
    
    if not index:
        print("❌ Index non trouvé. Lancez d'abord la création de l'index.")
        return None
    
    siren = str(siren).zfill(9)
    
    if siren in index:
        info = index[siren]
        print(f"✅ SIREN {siren} trouvé !")
        print(f"   Fichier: {info['file']}")
        print(f"   Nombre de bilans: {info['bilans_count']}")
        return info
    else:
        print(f"❌ SIREN {siren} non trouvé dans l'index")
        print(f"   (Index contient {len(index):,} entreprises)")
        return None

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Mode recherche
        siren = sys.argv[1]
        search_siren_fast(siren)
    else:
        # Mode création d'index
        create_siren_index()
