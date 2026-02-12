#!/usr/bin/env python3
"""
Test du filtrage des données RNE - ne garder que les données financières
"""

import json
import sys
from pathlib import Path

def analyze_file_structure(filepath: Path):
    """Analyser la structure d'un fichier RNE"""
    print(f"\n{'='*80}")
    print(f"📊 Analyse de {filepath.name}")
    print('='*80)
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    print(f"\n📈 Statistiques générales:")
    print(f"  Nombre d'entreprises: {len(data)}")
    print(f"  Taille du fichier: {filepath.stat().st_size / 1024 / 1024:.1f} MB")
    
    if not data:
        print("  ⚠️  Fichier vide")
        return
    
    # Analyser la première entreprise
    first = data[0]
    print(f"\n🔍 Structure d'une entreprise:")
    print(f"  Clés présentes: {list(first.keys())}")
    
    # Vérifier si filtré ou non
    has_unnecessary_data = any(k in first for k in ['denomination', 'id', 'updatedAt', 'deleted'])
    
    if has_unnecessary_data:
        print(f"\n  ⚠️  FICHIER NON FILTRÉ - Contient des données inutiles:")
        for key in ['denomination', 'id', 'confidentiality', 'updatedAt', 'deleted', 'numChrono']:
            if key in first:
                print(f"      - {key}")
    else:
        print(f"\n  ✅ FICHIER FILTRÉ - Ne contient que les données essentielles")
    
    # Analyser les données financières
    if 'bilanSaisi' in first:
        bilan = first['bilanSaisi']
        if isinstance(bilan, dict):
            print(f"\n💰 Données financières (bilanSaisi):")
            print(f"  Clés: {list(bilan.keys())[:10]}")
    
    # Calculer le gain potentiel de filtrage
    if has_unnecessary_data:
        # Simuler le filtrage
        filtered_data = []
        for entreprise in data:
            filtered_data.append({
                "siren": entreprise.get("siren"),
                "dateCloture": entreprise.get("dateCloture"),
                "dateDepot": entreprise.get("dateDepot"),
                "bilanSaisi": entreprise.get("bilanSaisi"),
                "typeBilan": entreprise.get("typeBilan"),
            })
        
        original_json = json.dumps(data)
        filtered_json = json.dumps(filtered_data)
        
        original_size = len(original_json) / (1024 * 1024)
        filtered_size = len(filtered_json) / (1024 * 1024)
        reduction = 100 * (1 - filtered_size / original_size)
        
        print(f"\n📊 Gain potentiel du filtrage:")
        print(f"  Taille actuelle (non filtré): {original_size:.1f} MB")
        print(f"  Taille après filtrage: {filtered_size:.1f} MB")
        print(f"  Réduction: {reduction:.0f}%")
        print(f"  💾 Gain d'espace: {original_size - filtered_size:.1f} MB par fichier")


if __name__ == "__main__":
    cache_dir = Path("/workspaces/TestsMCP/rne_cache")
    
    if not cache_dir.exists() or not list(cache_dir.glob("*.json")):
        print("❌ Aucun fichier RNE trouvé dans le cache")
        sys.exit(1)
    
    # Analyser les 3 premiers fichiers
    files = sorted(cache_dir.glob("stock_*.json"))[:3]
    
    total_original = 0
    total_filtered = 0
    
    for filepath in files:
        analyze_file_structure(filepath)
    
    print(f"\n{'='*80}")
    print("✅ Analyse terminée")
    print('='*80)
