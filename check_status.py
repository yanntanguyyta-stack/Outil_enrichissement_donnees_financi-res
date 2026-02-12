#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path

cache = Path('/workspaces/TestsMCP/rne_cache')
files = list(cache.glob('stock_*.json'))

print("="*80)
print("📊 ÉTAT DU SYSTÈME")
print("="*80)

# Cache
print(f"\n📁 Cache RNE:")
print(f"  Nombre de fichiers: {len(files)}")

if files:
    sizes = [f.stat().st_size / (1024*1024) for f in files]
    total = sum(sizes)
    print(f"  Taille totale: {total:.1f} MB ({total/1024:.2f} GB)")
    print(f"  Taille moyenne: {sum(sizes)/len(sizes):.1f} MB/fichier")
    
    # Vérifier quelques fichiers
    f1 = cache / 'stock_000001.json'
    f520 = cache / 'stock_000520.json'
    
    if f1.exists():
        s1 = f1.stat().st_size / (1024*1024)
        print(f"  stock_000001.json: {s1:.1f} MB {'(converti ✅)' if s1 < 10 else '(non converti ⚠️)'}")
    
    if f520.exists():
        s520 = f520.stat().st_size / (1024*1024)
        print(f"  stock_000520.json: {s520:.1f} MB {'(converti ✅)' if s520 < 10 else '(non converti ⚠️)'}")

# Espace disque
print(f"\n💾 Espace disque:")
result = subprocess.run(['df', '-h', '/workspaces'], capture_output=True, text=True)
for line in result.stdout.split('\n'):
    if '/workspaces' in line:
        parts = line.split()
        print(f"  Total: {parts[1]}")  
        print(f"  Utilisé: {parts[2]} ({parts[4]})")
        print(f"  Disponible: {parts[3]}")

# Streamlit
print(f"\n🚀 Streamlit:")
result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
streamlit_running = any('streamlit run' in line for line in result.stdout.split('\n'))
print(f"  État: {'✅ Actif' if streamlit_running else '❌ Arrêté'}")

# Processus de conversion
conversion_running = any('convert_cache_streaming' in line for line in result.stdout.split('\n'))
print(f"\n🔄 Conversion streaming:")
print(f"  État: {'✅ En cours' if conversion_running else '✅ Terminée (ou pas lancée)'}")

print("\n" + "="*80)
