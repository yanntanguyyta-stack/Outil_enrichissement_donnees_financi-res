#!/usr/bin/env python3
"""Nettoyage rapide du cache RNE"""
import os
from pathlib import Path

cache_dir = Path('/workspaces/TestsMCP/rne_cache')
files = sorted(cache_dir.glob('stock_*.json'))

# Identifier fichiers à supprimer
to_delete = []
for f in files:
    num_str = f.stem.replace('stock_', '')
    try:
        if int(num_str) > 84:
            to_delete.append(f)
    except:
        pass

# Supprimer
deleted_size = 0
for f in to_delete:
    deleted_size += f.stat().st_size
    f.unlink()

# Rapport
remaining = list(cache_dir.glob('stock_*.json'))
final_size = sum(f.stat().st_size for f in remaining) / (1024**3)

with open('/tmp/cleanup_result.txt', 'w') as out:
    out.write(f"Fichiers supprimés: {len(to_delete)}\n")
    out.write(f"Espace libéré: {deleted_size/(1024**3):.2f} GB\n")
    out.write(f"Fichiers restants: {len(remaining)}\n")
    out.write(f"Taille finale: {final_size:.2f} GB\n")
    
    if remaining:
        sample_size = remaining[0].stat().st_size / (1024**2)
        out.write(f"Taille d'un fichier: {sample_size:.1f} MB\n")
        out.write(f"Format: {'Streaming' if sample_size < 10 else 'Complet'}\n")

print("OK")
