"""
Extraire et analyser un fichier JSON exemple du RNE
"""

import zipfile
import json
import os

def extract_and_analyze_first_json():
    """Extraire le premier fichier JSON et l'analyser"""
    zip_path = "/workspaces/TestsMCP/stock_comptes_annuels.zip"
    extract_dir = "/workspaces/TestsMCP/rne_data"
    
    print("="*80)
    print("📦 EXTRACTION ET ANALYSE D'UN FICHIER JSON EXEMPLE")
    print("="*80)
    
    # Créer le dossier d'extraction
    os.makedirs(extract_dir, exist_ok=True)
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Extraire le premier fichier JSON
            json_files = [f for f in zip_ref.namelist() if f.endswith('.json')]
            
            if not json_files:
                print("❌ Aucun fichier JSON trouvé")
                return
            
            first_json = json_files[0]
            print(f"\n📄 Extraction de: {first_json}")
            
            zip_ref.extract(first_json, extract_dir)
            extracted_path = os.path.join(extract_dir, first_json)
            
            file_size = os.path.getsize(extracted_path)
            print(f"✅ Fichier extrait: {file_size:,} octets ({file_size / (1024**2):.2f} MB)")
            
            # Lire et analyser le fichier
            print(f"\n🔍 Analyse du contenu...")
            print("-" * 80)
            
            with open(extracted_path, 'r', encoding='utf-8') as f:
                # Lire les premières lignes
                lines = []
                for i, line in enumerate(f):
                    if i >= 5:  # Lire seulement les 5 premières lignes
                        break
                    lines.append(line.strip())
                
                print(f"\n📝 Premières lignes du fichier:\n")
                
                # Essayer de parser chaque ligne comme JSON
                for i, line in enumerate(lines, 1):
                    if line:
                        print(f"\nLigne {i}:")
                        print("-" * 40)
                        try:
                            obj = json.loads(line)
                            print(json.dumps(obj, indent=2, ensure_ascii=False)[:2000])
                            
                            if i == 1:
                                # Afficher la structure des clés
                                print("\n📋 Structure des clés:")
                                print("-" * 40)
                                
                                def print_structure(data, indent=0):
                                    """Afficher la structure récursivement"""
                                    prefix = "  " * indent
                                    if isinstance(data, dict):
                                        for key, value in data.items():
                                            value_type = type(value).__name__
                                            if isinstance(value, (dict, list)) and value:
                                                print(f"{prefix}📁 {key}: {value_type}")
                                                if isinstance(value, dict):
                                                    print_structure(value, indent + 1)
                                                elif isinstance(value, list) and len(value) > 0:
                                                    print(f"{prefix}  └─ [0]: {type(value[0]).__name__}")
                                                    if isinstance(value[0], dict):
                                                        print_structure(value[0], indent + 2)
                                            else:
                                                sample = str(value)[:50] if value else "None"
                                                print(f"{prefix}📄 {key}: {value_type} = {sample}")
                                    elif isinstance(data, list):
                                        for i, item in enumerate(data[:2]):
                                            print(f"{prefix}[{i}]: {type(item).__name__}")
                                            if isinstance(item, dict):
                                                print_structure(item, indent + 1)
                                
                                print_structure(obj)
                            
                        except json.JSONDecodeError as e:
                            print(f"❌ Erreur JSON: {str(e)}")
                            print(f"Contenu brut: {line[:200]}")
                
                # Compter le nombre total de lignes
                f.seek(0)
                total_lines = sum(1 for _ in f)
                print(f"\n📊 Statistiques:")
                print(f"   Total de lignes: {total_lines:,}")
                print(f"   Chaque ligne = 1 entreprise avec ses comptes annuels")
            
            print("-" * 80)
            print(f"\n✅ Analyse terminée")
            
    except Exception as e:
        print(f"\n❌ Erreur: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("="*80)

if __name__ == "__main__":
    extract_and_analyze_first_json()
