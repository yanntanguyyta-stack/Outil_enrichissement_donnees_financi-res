#!/usr/bin/env python3
"""
Script pour extraire les fichiers RNE localement et éviter les téléchargements FTP répétés.

Ce script extrait uniquement les fichiers nécessaires du ZIP (au lieu de tout extraire).
Recommandé pour un usage intensif avec beaucoup d'entreprises.
"""

import zipfile
from pathlib import Path
import json
import sys


def extract_rne_files_from_zip(zip_path: Path, cache_dir: Path, file_list: list = None):
    """
    Extraire des fichiers spécifiques du ZIP RNE vers le cache.
    
    Args:
        zip_path: Chemin vers le ZIP RNE
        cache_dir: Répertoire de cache où extraire
        file_list: Liste de fichiers à extraire (None = tous)
    """
    if not zip_path.exists():
        print(f"❌ ZIP non trouvé: {zip_path}")
        print(f"\n💡 Téléchargez-le avec:")
        print(f"wget ftp://rneinpiro:vv8_rQ5f4M_2-E@www.inpi.net/stock_RNE_comptes_annuels_20250926_1000_v2.zip")
        return
    
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*80}")
    print(f"📦 EXTRACTION FICHIERS RNE")
    print(f"{'='*80}")
    print(f"📁 Source: {zip_path}")
    print(f"📂 Destination: {cache_dir}")
    print(f"{'='*80}\n")
    
    with zipfile.ZipFile(zip_path, 'r') as zf:
        available_files = zf.namelist()
        
        if file_list is None:
            # Extraire tous les fichiers JSON
            file_list = [f for f in available_files if f.endswith('.json')]
        
        total = len(file_list)
        extracted = 0
        skipped = 0
        errors = 0
        
        for i, filename in enumerate(file_list, 1):
            target_path = cache_dir / filename
            
            # Skip si déjà extrait
            if target_path.exists():
                if i % 100 == 0:
                    print(f"⏩ [{i}/{total}] Déjà extrait: {filename}")
                skipped += 1
                continue
            
            try:
                # Extraire
                with zf.open(filename) as source:
                    data = json.load(source)
                
                # Sauvegarder
                with open(target_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f)
                
                extracted += 1
                
                # Progression
                if i % 50 == 0 or i == total:
                    print(f"✅ [{i}/{total}] {filename} ({len(data)} entrées)")
                
            except Exception as e:
                errors += 1
                print(f"❌ [{i}/{total}] Erreur {filename}: {e}")
    
    print(f"\n{'='*80}")
    print(f"📊 RÉSUMÉ")
    print(f"{'='*80}")
    print(f"✅ Extraits: {extracted}")
    print(f"⏩ Ignorés (déjà présents): {skipped}")
    print(f"❌ Erreurs: {errors}")
    print(f"📦 Total: {total}")
    print(f"{'='*80}\n")


def extract_specific_files(zip_path: Path, cache_dir: Path, sirens: list):
    """
    Extraire uniquement les fichiers nécessaires pour une liste de SIRENs.
    
    Args:
        zip_path: Chemin vers le ZIP RNE
        cache_dir: Répertoire de cache
        sirens: Liste de SIRENs
    """
    from enrichment_hybrid import group_sirens_by_rne_file
    
    print(f"\n🔍 Identification des fichiers nécessaires pour {len(sirens)} SIREN(s)...")
    
    grouped = group_sirens_by_rne_file(sirens)
    files_needed = list(grouped.keys())
    
    print(f"📦 {len(files_needed)} fichier(s) nécessaire(s)\n")
    
    extract_rne_files_from_zip(zip_path, cache_dir, files_needed)


def main():
    """Interface en ligne de commande"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Extraire les fichiers RNE localement pour éviter les téléchargements FTP répétés"
    )
    
    parser.add_argument(
        '--zip',
        type=str,
        default='/workspaces/TestsMCP/stock_comptes_annuels.zip',
        help='Chemin vers le ZIP RNE'
    )
    
    parser.add_argument(
        '--cache',
        type=str,
        default='/workspaces/TestsMCP/rne_cache',
        help='Répertoire de cache de destination'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Extraire tous les fichiers (1380 fichiers, peut prendre du temps)'
    )
    
    parser.add_argument(
        '--files',
        nargs='+',
        help='Liste de fichiers spécifiques à extraire (ex: stock_000001.json stock_000002.json)'
    )
    
    parser.add_argument(
        '--sirens',
        nargs='+',
        help='Extraire uniquement les fichiers nécessaires pour ces SIRENs'
    )
    
    args = parser.parse_args()
    
    zip_path = Path(args.zip)
    cache_dir = Path(args.cache)
    
    if args.sirens:
        # Extraire pour SIRENs spécifiques
        extract_specific_files(zip_path, cache_dir, args.sirens)
    elif args.all:
        # Extraire tout
        response = input(f"\n⚠️  Êtes-vous sûr de vouloir extraire TOUS les fichiers (1380 fichiers, ~2-3 GB) ? (o/N): ")
        if response.lower() == 'o':
            extract_rne_files_from_zip(zip_path, cache_dir)
        else:
            print("❌ Extraction annulée")
    elif args.files:
        # Extraire fichiers spécifiques
        extract_rne_files_from_zip(zip_path, cache_dir, args.files)
    else:
        # Mode interactif
        print("\n" + "="*80)
        print("📦 EXTRACTION FICHIERS RNE - MODE INTERACTIF")
        print("="*80)
        print("\nOptions:")
        print("  1. Extraire des fichiers spécifiques (recommandé)")
        print("  2. Extraire pour des SIRENs donnés")
        print("  3. Extraire TOUS les fichiers (1380 fichiers, ~2-3 GB)")
        print("  4. Quitter")
        
        choice = input("\nVotre choix (1-4): ").strip()
        
        if choice == '1':
            files = input("Fichiers à extraire (séparés par des espaces): ").strip().split()
            if files:
                extract_rne_files_from_zip(zip_path, cache_dir, files)
        elif choice == '2':
            sirens = input("SIRENs (séparés par des espaces): ").strip().split()
            if sirens:
                extract_specific_files(zip_path, cache_dir, sirens)
        elif choice == '3':
            response = input("\n⚠️  Confirmer extraction complète ? (o/N): ")
            if response.lower() == 'o':
                extract_rne_files_from_zip(zip_path, cache_dir)
        else:
            print("Au revoir!")


if __name__ == "__main__":
    # Exemples d'utilisation
    if len(sys.argv) == 1:
        print("\n📖 EXEMPLES D'UTILISATION:\n")
        print("# Extraire pour des SIRENs spécifiques (recommandé)")
        print("python3 extract_rne_files.py --sirens 552100554 005880596 775665019")
        print()
        print("# Extraire des fichiers spécifiques")
        print("python3 extract_rne_files.py --files stock_000001.json stock_000498.json")
        print()
        print("# Extraire tout (attention: 1380 fichiers)")
        print("python3 extract_rne_files.py --all")
        print()
        print("# Mode interactif")
        print("python3 extract_rne_files.py")
        print()
    
    main()
