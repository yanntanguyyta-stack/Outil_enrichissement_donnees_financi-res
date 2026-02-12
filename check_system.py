#!/usr/bin/env python3
import os
from pathlib import Path

cache = Path('/workspaces/TestsMCP/rne_cache')
files = list(cache.glob('stock_*.json'))
size_bytes = sum(f.stat().st_size for f in files)
size_gb = size_bytes / (1024**3)

disk = os.statvfs('/workspaces')
total_gb = disk.f_blocks * disk.f_frsize / (1024**3)
used_gb = (disk.f_blocks - disk.f_bavail) * disk.f_frsize / (1024**3)
avail_gb = disk.f_bavail * disk.f_frsize / (1024**3)

with open('/workspaces/TestsMCP/SYSTEM_STATUS.txt', 'w') as f:
    f.write(f"Fichiers RNE: {len(files)}\n")
    f.write(f"Taille cache: {size_gb:.2f} GB\n")
    f.write(f"Disque utilisé: {used_gb:.1f}/{total_gb:.1f} GB ({100*used_gb/total_gb:.0f}%)\n")
    f.write(f"Disque dispo: {avail_gb:.1f} GB\n")

print(f"✅ {len(files)} fichiers | {size_gb:.2f} GB | {100*used_gb/total_gb:.0f}% disque")
