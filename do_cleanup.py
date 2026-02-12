#!/usr/bin/env python3
import os, subprocess
from pathlib import Path

# 1. Arrêter processus
subprocess.run(['pkill', '-9', '-f', 'extract'], capture_output=True)
subprocess.run(['pkill', '-9', '-f', 'convert'], capture_output=True)

# 2. Nettoyer cache
cache = Path('/workspaces/TestsMCP/rne_cache')
files = list(cache.glob('stock_*.json'))
to_del = [f for f in files if int(f.stem.replace('stock_', '')) > 84]
freed = sum(f.stat().st_size for f in to_del) / 1e9
for f in to_del: f.unlink()

# 3. État final
remain = list(cache.glob('stock_*.json'))
size = sum(f.stat().st_size for f in remain) / 1e9
sample = remain[0].stat().st_size / 1e6 if remain else 0

# 4. Disque
d = os.statvfs('/workspaces')
total = d.f_blocks * d.f_frsize / 1e9
used = (d.f_blocks - d.f_bavail) * d.f_frsize / 1e9
avail = d.f_bavail * d.f_frsize / 1e9

# 5. Écrire résumé
Path('/tmp/status.md').write_text(f"""## ✅ Nettoyage terminé

- **Fichiers supprimés:** {len(to_del)}
- **Espace libéré:** {freed:.1f} GB
- **Fichiers restants:** {len(remain)}
- **Taille du cache:** {size:.1f} GB
- **Taille/fichier:** {sample:.1f} MB ({('✅ Streaming' if sample < 10 else '❌ Complet')})

### 💾 Disque
- Total: {total:.0f} GB
- Utilisé: {used:.0f} GB ({100*used/total:.0f}%)
- Disponible: {avail:.0f} GB
""")

print("Statut écrit dans /tmp/status.md")
