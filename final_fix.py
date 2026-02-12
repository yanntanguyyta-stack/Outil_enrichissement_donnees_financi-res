#!/usr/bin/env python3
from pathlib import Path
import subprocess, os

cache = Path('/workspaces/TestsMCP/rne_cache')
files = sorted(cache.glob('stock_*.json'))

# Supprimer fichiers > 84
for f in files:
    num = int(f.stem.replace('stock_', ''))
    if num > 84:
        f.unlink()

# État final
files = sorted(cache.glob('stock_*.json'))
print(f"{len(files)} fichiers")

# Disque
d = os.statvfs('/workspaces')
used_pct = 100 * (d.f_blocks - d.f_bavail) / d.f_blocks
print(f"{used_pct:.0f}% disque")

# Streamlit
subprocess.run(['pkill', '-9', 'streamlit'], capture_output=True)
subprocess.run([
    'nohup', 'streamlit', 'run', '/workspaces/TestsMCP/app.py',
    '--server.headless=true', '--server.port=8501'
], stdout=open('/tmp/streamlit.log', 'w'), stderr=subprocess.STDOUT)
print("Streamlit relancé")
print("http://localhost:8501")
