#!/usr/bin/env python3
"""
Script d'extraction automatique de tous les fichiers RNE (sans confirmation)
"""

from pathlib import Path
import sys

# Ajouter le chemin pour importer extract_rne_files
sys.path.insert(0, '/workspaces/TestsMCP')

from extract_rne_files import extract_rne_files_from_zip

def main():
    zip_path = Path('/workspaces/TestsMCP/stock_comptes_annuels.zip')
    cache_dir = Path('/workspaces/TestsMCP/rne_cache')
    
    print("\n" + "="*80)
    print("🚀 EXTRACTION AUTOMATIQUE DE TOUS LES FICHIERS RNE")
    print("="*80)
    print(f"📦 ZIP: {zip_path}")
    print(f"📂 Cache: {cache_dir}")
    print(f"📊 Fichiers à extraire: ~1380")
    print(f"💾 Espace nécessaire: ~2-3 GB")
    print(f"⏱️  Temps estimé: 10-15 minutes")
    print("="*80 + "\n")
    
    # Extraction sans confirmation
    extract_rne_files_from_zip(zip_path, cache_dir, file_list=None)
    
    print("\n✅ Extraction terminée!")
    print("🎯 L'application peut maintenant fonctionner sans erreur 502\n")

if __name__ == "__main__":
    main()
