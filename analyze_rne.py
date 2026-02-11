"""
Script pour monitorer le téléchargement et analyser les données RNE
"""

import os
import time
import zipfile
import json
from datetime import datetime

def check_download_progress():
    """Vérifier la progression du téléchargement"""
    file_path = "/workspaces/TestsMCP/stock_comptes_annuels.zip"
    log_path = "/workspaces/TestsMCP/download_progress.log"
    target_size = 3663124363  # 3,6 GB
    
    print("="*80)
    print("📊 PROGRESSION DU TÉLÉCHARGEMENT")
    print("="*80)
    
    if os.path.exists(file_path):
        current_size = os.path.getsize(file_path)
        progress = (current_size / target_size) * 100
        
        print(f"\n📥 Fichier: stock_comptes_annuels.zip")
        print(f"   Téléchargé: {current_size:,} octets ({current_size / (1024**3):.2f} GB)")
        print(f"   Total attendu: {target_size:,} octets ({target_size / (1024**3):.2f} GB)")
        print(f"   Progression: {progress:.1f}%")
        print(f"   {'█' * int(progress / 2)}{' ' * (50 - int(progress / 2))} {progress:.1f}%")
        
        if progress >= 100:
            print(f"\n✅ Téléchargement terminé!")
            return True
        else:
            print(f"\n⏳ Téléchargement en cours...")
            return False
    else:
        print("\n⚠️  Le fichier n'existe pas encore")
        return False
    
    print("="*80)

def analyze_rne_structure():
    """Analyser la structure des données RNE une fois téléchargées"""
    file_path = "/workspaces/TestsMCP/stock_comptes_annuels.zip"
    
    print("\n" + "="*80)
    print("📦 ANALYSE DE LA STRUCTURE DES DONNÉES RNE")
    print("="*80)
    
    if not os.path.exists(file_path):
        print("\n❌ Le fichier n'existe pas encore. Attendez la fin du téléchargement.")
        return
    
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            files = zip_ref.filelist
            print(f"\n✅ Archive ouverte avec succès")
            print(f"   Nombre total de fichiers: {len(files)}")
            
            # Analyser les noms de fichiers
            print(f"\n📄 Premiers fichiers dans l'archive:")
            print("-" * 80)
            
            for i, file_info in enumerate(files[:10]):
                size_mb = file_info.file_size / (1024 * 1024)
                print(f"   {file_info.filename:<40} {size_mb:>10.2f} MB")
            
            if len(files) > 10:
                print(f"   ... et {len(files) - 10} autres fichiers")
            
            print("-" * 80)
            
            # Extraire et analyser un fichier JSON exemple
            json_files = [f for f in files if f.filename.endswith('.json')]
            
            if json_files:
                print(f"\n📊 Fichiers JSON trouvés: {len(json_files)}")
                
                # Analyser le premier fichier JSON
                first_json = json_files[0]
                print(f"\n🔍 Analyse du fichier: {first_json.filename}")
                print("-" * 80)
                
                with zip_ref.open(first_json.filename) as json_file:
                    # Lire les premières lignes pour comprendre la structure
                    content = json_file.read(10000).decode('utf-8', errors='replace')
                    
                    # Essayer de parser comme JSON
                    try:
                        # Le fichier pourrait contenir plusieurs objets JSON (JSONL)
                        lines = content.strip().split('\n')
                        
                        print(f"   Premières lignes du fichier:\n")
                        for i, line in enumerate(lines[:3]):
                            if line.strip():
                                try:
                                    obj = json.loads(line)
                                    print(f"   Ligne {i+1} (JSON):")
                                    print(f"   {json.dumps(obj, indent=2, ensure_ascii=False)[:500]}")
                                    print()
                                    
                                    # Afficher la structure
                                    print(f"   📋 Structure des données:")
                                    for key in obj.keys():
                                        value_type = type(obj[key]).__name__
                                        print(f"      - {key}: {value_type}")
                                    
                                    break
                                except json.JSONDecodeError:
                                    pass
                    except Exception as e:
                        print(f"   ⚠️  Format non-standard: {str(e)}")
                        print(f"   Contenu brut:\n{content[:500]}")
                
                print("-" * 80)
            else:
                print("\n⚠️  Aucun fichier JSON trouvé dans l'archive")
        
        print("\n✅ Analyse terminée")
        
    except zipfile.BadZipFile:
        print("\n❌ Le fichier ZIP est corrompu ou incomplet")
    except Exception as e:
        print(f"\n❌ Erreur lors de l'analyse: {str(e)}")
    
    print("="*80)

if __name__ == "__main__":
    # Vérifier la progression
    is_complete = check_download_progress()
    
    # Si le téléchargement est terminé, analyser
    if is_complete:
        analyze_rne_structure()
    else:
        print("\n💡 Relancez ce script plus tard pour analyser les données")
        print("   ou utilisez: watch -n 10 python3 analyze_rne.py")
