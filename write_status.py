#!/usr/bin/env python3
import os
from pathlib import Path

cache = Path('/workspaces/TestsMCP/rne_cache')
files = sorted(cache.glob('stock_*.json'))

with open('/tmp/status.txt', 'w') as f:
    f.write("="*80 + "\n")
    f.write("📊 ÉTAT DU SYSTÈME\n")
    f.write("="*80 + "\n\n")
    
    # Cache
    f.write(f"📁 Cache RNE:\n")
    f.write(f"  Nombre de fichiers: {len(files)}\n")
    
    if files:
        sizes = [f.stat().st_size / (1024*1024) for f in files]
        total = sum(sizes)
        f.write(f"  Taille totale: {total:.1f} MB ({total/1024:.2f} GB)\n")
        f.write(f"  Taille moyenne: {sum(sizes)/len(sizes):.1f} MB/fichier\n\n")
        
        # Vérifier premiers et derniers fichiers
        f.write(f"  Premier fichier: {files[0].name} - {files[0].stat().st_size/(1024*1024):.1f} MB\n")
        f.write(f"  Dernier fichier: {files[-1].name} - {files[-1].stat().st_size/(1024*1024):.1f} MB\n\n")
        
        # Compter convertis vs non convertis
        converted = sum(1 for s in sizes if s < 10)
        f.write(f"  📊 Statut conversion:\n")
        f.write(f"    Convertis (<10 MB): {converted} fichiers\n")
        f.write(f"    Non convertis (>10 MB): {len(files)-converted} fichiers\n\n")
    
    # Espace disque
    disk = os.statvfs('/workspaces')
    total_gb = (disk.f_blocks * disk.f_frsize) / (1024**3)
    used_gb = ((disk.f_blocks - disk.f_bavail) * disk.f_frsize) / (1024**3)
    avail_gb = (disk.f_bavail * disk.f_frsize) / (1024**3)
    pct = (used_gb / total_gb) * 100
    
    f.write(f"💾 Espace disque (/workspaces):\n")
    f.write(f"  Total: {total_gb:.1f} GB\n")
    f.write(f"  Utilisé: {used_gb:.1f} GB ({pct:.0f}%)\n")
    f.write(f"  Disponible: {avail_gb:.1f} GB\n\n")
    
    # Streamlit
    import subprocess
    result = subprocess.run(['pgrep', '-f', 'streamlit'], capture_output=True)
    streamlit_running = len(result.stdout) > 0
    f.write(f"🚀 Streamlit: {'✅ Actif' if streamlit_running else '❌ Arrêté'}\n\n")
    
    # Processus conversion
    result = subprocess.run(['pgrep', '-f', 'convert_cache'], capture_output=True)
    conversion_running = len(result.stdout) > 0
    f.write(f"🔄 Conversion: {'⏳ En cours' if conversion_running else '✅ Terminée'}\n\n")
    
    f.write("="*80 + "\n")

print("Statut écrit dans /tmp/status.txt")
