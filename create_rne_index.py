#!/usr/bin/env python3
"""
Script pour créer un index léger des données RNE
Cet index permet de retrouver rapidement dans quel fichier se trouve un SIREN
sans avoir à stocker tout le contenu localement
"""

from ftplib import FTP
import json
import zipfile
import io
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Configuration FTP
FTP_HOST = "www.inpi.net"
FTP_USER = "rneinpiro"
FTP_PASSWORD = "vv8_rQ5f4M_2-E"
FTP_ZIP_FILE = "stock_RNE_comptes_annuels_20250926_1000_v2.zip"

# Chemins locaux
INDEX_FILE = Path("/workspaces/TestsMCP/rne_siren_index.json")
TMP_ZIP = Path("/workspaces/TestsMCP/stock_comptes_annuels.zip")


def create_index_from_local_zip(zip_path: Path):
    """
    Créer l'index depuis un ZIP local (déjà téléchargé)
    Plus rapide si le ZIP est déjà disponible
    """
    print(f"📦 Création de l'index depuis le ZIP local...")
    print(f"   Fichier: {zip_path}")
    print(f"   Taille: {zip_path.stat().st_size / 1024**3:.2f} GB")
    print()
    
    index = {}
    stats = {
        'total_files': 0,
        'total_companies': 0,
        'total_bilans': 0,
        'created_at': datetime.now().isoformat(),
        'source': 'local_zip'
    }
    
    with zipfile.ZipFile(zip_path, 'r') as zf:
        json_files = [f for f in zf.namelist() if f.endswith('.json')]
        stats['total_files'] = len(json_files)
        
        print(f"🔍 Analyse de {len(json_files)} fichiers JSON...")
        print()
        
        for i, json_file in enumerate(json_files, 1):
            if i % 50 == 0:
                pct = (i / len(json_files)) * 100
                print(f"   Progression: {i}/{len(json_files)} ({pct:.1f}%) - {stats['total_companies']:,} entreprises")
            
            try:
                with zf.open(json_file) as f:
                    content = f.read().decode('utf-8')
                    data = json.loads(content)
                    
                    for bilan in data:
                        siren = bilan.get('siren')
                        if siren:
                            if siren not in index:
                                index[siren] = {
                                    'file': json_file,
                                    'count': 0
                                }
                                stats['total_companies'] += 1
                            index[siren]['count'] += 1
                            stats['total_bilans'] += 1
            
            except Exception as e:
                print(f"   ⚠️  Erreur avec {json_file}: {e}")
                continue
        
        print()
        print(f"✅ Analyse terminée !")
    
    # Sauvegarder l'index
    print(f"\n💾 Sauvegarde de l'index...")
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            'index': index,
            'stats': stats,
            'format_version': '1.0'
        }, f, ensure_ascii=False, indent=2)
    
    index_size = INDEX_FILE.stat().st_size / 1024**2
    
    print(f"✅ Index créé avec succès !")
    print(f"\n📈 Statistiques:")
    print(f"   - Fichiers JSON: {stats['total_files']}")
    print(f"   - Entreprises uniques: {stats['total_companies']:,}")
    print(f"   - Bilans totaux: {stats['total_bilans']:,}")
    print(f"   - Taille de l'index: {index_size:.2f} MB")
    print(f"   - Fichier sauvegardé: {INDEX_FILE}")
    
    print(f"\n💡 Vous pouvez maintenant:")
    print(f"   1. Supprimer le ZIP de {zip_path.stat().st_size / 1024**3:.2f} GB")
    print(f"   2. Utiliser enrichment_rne_ondemand.py pour enrichir à la demande")
    
    return index, stats


def cleanup_after_indexing():
    """Nettoyer les fichiers volumineux après création de l'index"""
    print(f"\n🧹 NETTOYAGE DES FICHIERS VOLUMINEUX")
    print("="*80)
    
    files_to_delete = []
    total_size = 0
    
    # ZIP
    if TMP_ZIP.exists():
        size = TMP_ZIP.stat().st_size
        files_to_delete.append(('ZIP', TMP_ZIP, size))
        total_size += size
    
    # Répertoire rne_data
    rne_data_dir = Path("/workspaces/TestsMCP/rne_data")
    if rne_data_dir.exists():
        size = sum(f.stat().st_size for f in rne_data_dir.glob("**/*") if f.is_file())
        if size > 0:
            files_to_delete.append(('rne_data/', rne_data_dir, size))
            total_size += size
    
    if not files_to_delete:
        print("✅ Aucun fichier volumineux à supprimer")
        return
    
    print(f"\nFichiers à supprimer:")
    for name, path, size in files_to_delete:
        print(f"   - {name}: {size / 1024**3:.2f} GB")
    
    print(f"\n💾 Espace libéré: {total_size / 1024**3:.2f} GB")
    
    response = input(f"\n⚠️  Voulez-vous supprimer ces fichiers ? (o/N): ")
    if response.lower() in ['o', 'oui', 'y', 'yes']:
        for name, path, size in files_to_delete:
            try:
                if path.is_dir():
                    import shutil
                    shutil.rmtree(path)
                    print(f"   ✅ Supprimé: {name}")
                else:
                    path.unlink()
                    print(f"   ✅ Supprimé: {name}")
            except Exception as e:
                print(f"   ❌ Erreur: {e}")
        
        print(f"\n✅ Nettoyage terminé !")
        print(f"💾 {total_size / 1024**3:.2f} GB libérés")
    else:
        print("⏭️  Nettoyage annulé")


def verify_index():
    """Vérifier l'index existant"""
    if not INDEX_FILE.exists():
        print(f"❌ Index non trouvé: {INDEX_FILE}")
        return False
    
    try:
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        index = data.get('index', {})
        stats = data.get('stats', {})
        
        print(f"✅ Index trouvé et valide")
        print(f"\n📊 Informations:")
        print(f"   - Taille: {INDEX_FILE.stat().st_size / 1024**2:.2f} MB")
        print(f"   - Entreprises: {len(index):,}")
        print(f"   - Bilans totaux: {stats.get('total_bilans', 0):,}")
        print(f"   - Créé le: {stats.get('created_at', 'N/A')}")
        
        # Afficher quelques exemples
        print(f"\n🔍 Exemples de SIRENs disponibles:")
        for i, (siren, info) in enumerate(list(index.items())[:5]):
            print(f"   - {siren}: {info['count']} bilan(s) dans {info['file']}")
        
        return True
    
    except Exception as e:
        print(f"❌ Erreur lecture index: {e}")
        return False


def main():
    """Menu principal"""
    print("="*80)
    print("🏛️  GESTIONNAIRE D'INDEX RNE")
    print("="*80)
    print()
    
    # Vérifier si l'index existe
    if INDEX_FILE.exists():
        print("📋 Index existant détecté")
        verify_index()
        print()
    else:
        print("⚠️  Aucun index trouvé")
        print()
    
    # Options
    print("Options disponibles:")
    print("  1. Créer/Recréer l'index depuis le ZIP local")
    print("  2. Vérifier l'index existant")
    print("  3. Nettoyer les fichiers volumineux")
    print("  4. Quitter")
    print()
    
    choice = input("Votre choix (1-4): ").strip()
    
    if choice == '1':
        if not TMP_ZIP.exists():
            print(f"\n❌ ZIP non trouvé: {TMP_ZIP}")
            print(f"💡 Téléchargez-le d'abord avec le FTP")
            return
        
        create_index_from_local_zip(TMP_ZIP)
        
        # Proposer le nettoyage
        cleanup_after_indexing()
    
    elif choice == '2':
        verify_index()
    
    elif choice == '3':
        cleanup_after_indexing()
    
    elif choice == '4':
        print("👋 Au revoir !")
    
    else:
        print("❌ Choix invalide")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--verify':
            verify_index()
        elif sys.argv[1] == '--create':
            if TMP_ZIP.exists():
                create_index_from_local_zip(TMP_ZIP)
                cleanup_after_indexing()
            else:
                print(f"❌ ZIP non trouvé: {TMP_ZIP}")
        elif sys.argv[1] == '--cleanup':
            cleanup_after_indexing()
        else:
            print("Options: --verify, --create, --cleanup")
    else:
        main()
