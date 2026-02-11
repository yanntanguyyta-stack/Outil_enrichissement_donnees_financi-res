#!/usr/bin/env python3
"""
Script pour extraire et organiser les données RNE dans le repo
À exécuter après chaque téléchargement du ZIP de l'INPI
"""

import zipfile
import os
import json
from pathlib import Path

# Chemins
ZIP_PATH = "/workspaces/TestsMCP/stock_comptes_annuels.zip"
EXTRACT_DIR = "/workspaces/TestsMCP/rne_data"

def setup_rne_data():
    """Extrait les fichiers JSON du ZIP dans le répertoire local"""
    
    # Créer le répertoire si nécessaire
    os.makedirs(EXTRACT_DIR, exist_ok=True)
    
    print(f"📦 Extraction des données RNE depuis {ZIP_PATH}")
    print(f"📁 Destination: {EXTRACT_DIR}")
    
    with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
        # Lister les fichiers JSON
        json_files = [f for f in zip_ref.namelist() if f.endswith('.json')]
        print(f"📊 {len(json_files)} fichiers JSON trouvés")
        
        # Extraire tous les fichiers JSON
        for i, json_file in enumerate(json_files, 1):
            if i % 100 == 0:
                print(f"   Extraction: {i}/{len(json_files)} fichiers...")
            zip_ref.extract(json_file, EXTRACT_DIR)
        
        # Extraire aussi le readme si présent
        if 'readme.txt' in zip_ref.namelist():
            zip_ref.extract('readme.txt', EXTRACT_DIR)
    
    print("✅ Extraction terminée !")
    
    # Statistiques
    json_files_extracted = list(Path(EXTRACT_DIR).glob("*.json"))
    total_size = sum(f.stat().st_size for f in json_files_extracted)
    
    print(f"\n📈 Statistiques:")
    print(f"   - Fichiers JSON: {len(json_files_extracted)}")
    print(f"   - Taille totale: {total_size / 1024**3:.2f} GB")
    
    # Compter le nombre total d'entreprises
    total_companies = 0
    print("\n🔍 Analyse des données...")
    for json_file in json_files_extracted[:5]:  # Échantillon
        with open(json_file, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                total_companies += len(data)
            except:
                pass
    
    avg_per_file = total_companies / min(5, len(json_files_extracted))
    estimated_total = int(avg_per_file * len(json_files_extracted))
    
    print(f"   - Comptes annuels estimés: ~{estimated_total:,}")
    print(f"\n✨ Les données RNE sont maintenant disponibles localement!")

if __name__ == "__main__":
    setup_rne_data()
