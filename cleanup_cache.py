#!/usr/bin/env python3
"""
Script de nettoyage et optimisation du cache RNE  
"""
import os
import subprocess
from pathlib import Path

cache_dir = Path('/workspaces/TestsMCP/rne_cache')
log_lines = []

def log(msg):
    """Ajouter un message au log"""
    log_lines.append(msg)
    print(msg)

log("="*80)
log("🧹 NETTOYAGE ET OPTIMISATION")
log("="*80)

# 1. Arrêter les processus
print("\n1️⃣ Arrêt des processus en cours...")
subprocess.run(['pkill', '-9', '-f', 'extract'], capture_output=True)
subprocess.run(['pkill', '-9', '-f', 'convert_cache'], capture_output=True)
print("   ✅ Processus arrêtés")

# 2. Lister tous les fichiers
files = sorted(cache_dir.glob('stock_*.json'))
print(f"\n2️⃣ Analyse du cache...")
print(f"   Total de fichiers trouvés: {len(files)}")

# 3. Identifier les fichiers à supprimer (> 084)
to_keep = []
to_delete = []

for f in files:
    # Extraire le numéro du fichier (ex: stock_000085.json -> 85)
    name = f.stem  # stock_000085
    num_str = name.replace('stock_', '')  # 000085
    try:
        num = int(num_str)
        if num <= 84:
            to_keep.append(f)
        else:
            to_delete.append(f)
    except ValueError:
        print(f"   ⚠️ Fichier ignoré: {f.name}")

print(f"   Fichiers à garder (≤ 084): {len(to_keep)}")
print(f"   Fichiers à supprimer (> 084): {len(to_delete)}")

# 4. Calculer l'espace avant suppression
total_size_before = sum(f.stat().st_size for f in files) / (1024**3)
delete_size = sum(f.stat().st_size for f in to_delete) / (1024**3)

print(f"\n3️⃣ Espace disque...")
print(f"   Taille actuelle du cache: {total_size_before:.2f} GB")
print(f"   Espace à libérer: {delete_size:.2f} GB")

# 5. Supprimer les fichiers
if to_delete:
    print(f"\n4️⃣ Suppression de {len(to_delete)} fichiers...")
    for i, f in enumerate(to_delete, 1):
        f.unlink()
        if i % 50 == 0:
            print(f"   Supprimés: {i}/{len(to_delete)}")
    print(f"   ✅ {len(to_delete)} fichiers supprimés")

# 6. Vérifier les fichiers restants
remaining = sorted(cache_dir.glob('stock_*.json'))
total_size_after = sum(f.stat().st_size for f in remaining) / (1024**3)

print(f"\n5️⃣ État final...")
print(f"   Fichiers restants: {len(remaining)}")
print(f"   Taille finale: {total_size_after:.2f} GB")
print(f"   Espace libéré: {delete_size:.2f} GB")

# 7. Vérifier si les fichiers sont au format streaming
if remaining:
    sample = remaining[0]
    size_mb = sample.stat().st_size / (1024**2)
    is_streaming = size_mb < 10
    
    print(f"\n6️⃣ Format des fichiers...")
    print(f"   Exemple: {sample.name} = {size_mb:.1f} MB")
    print(f"   Format: {'✅ Streaming (optimisé)' if is_streaming else '❌ Complet (non optimisé)'}")
    
    if not is_streaming:
        print(f"\n   ⚠️  Les fichiers ne sont pas au format streaming!")
        print(f"   💡 Pour les convertir, lancez:")
        print(f"      python3 /workspaces/TestsMCP/convert_cache_streaming.py")

# 8. Espace disque global
disk = os.statvfs('/workspaces')
total_gb = (disk.f_blocks * disk.f_frsize) / (1024**3)
used_gb = ((disk.f_blocks - disk.f_bavail) * disk.f_frsize) / (1024**3)
avail_gb = (disk.f_bavail * disk.f_frsize) / (1024**3)
pct = (used_gb / total_gb) * 100

print(f"\n7️⃣ Espace disque global (/workspaces)...")
print(f"   Total: {total_gb:.1f} GB")
print(f"   Utilisé: {used_gb:.1f} GB ({pct:.0f}%)")
print(f"   Disponible: {avail_gb:.1f} GB")

print("\n" + "="*80)
print("✅ NETTOYAGE TERMINÉ")
print("="*80)

log_file.flush()
log_file.close()

# Maintenant afficher le log
with open('/tmp/cleanup.log', 'r') as f:
    print(f.read(), file=sys.__stdout__)
