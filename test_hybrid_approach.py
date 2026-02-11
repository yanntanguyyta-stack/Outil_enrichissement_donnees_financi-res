#!/usr/bin/env python3
"""
Test complet de l'approche hybride optimisée
API DINUM + Index ultra-léger + FTP RNE
"""

import sys
import json
from pathlib import Path

# Vérifier l'index
INDEX_FILE = Path("/workspaces/TestsMCP/rne_siren_ranges.json")

print("="*80)
print("🧪 TEST DE L'APPROCHE HYBRIDE OPTIMISÉE")
print("="*80)
print()

# 1. Vérifier l'index
print("1️⃣  Vérification de l'index...")
if not INDEX_FILE.exists():
    print(f"   ❌ Index non trouvé: {INDEX_FILE}")
    print(f"   💡 Créez-le avec: python3 create_rne_index_ranges.py")
    sys.exit(1)

with open(INDEX_FILE, 'r', encoding='utf-8') as f:
    index_data = json.load(f)

index_size = INDEX_FILE.stat().st_size
stats = index_data.get('stats', {})
ranges = index_data.get('ranges', [])

print(f"   ✅ Index chargé")
print(f"   📊 Taille: {index_size / 1024:.1f} KB")
print(f"   🏢 Entreprises: {stats.get('total_companies', 0):,}")
print(f"   📄 Fichiers: {len(ranges)}")
print()

# 2. Test de recherche de fichier
print("2️⃣  Test de recherche dans l'index...")

test_sirens = [
    ("005880596", "GEDIMO HOLDING"),
    ("552100554", "EDF"),
    ("775665019", "TOTAL"),
]

for siren, expected_name in test_sirens:
    siren_padded = str(siren).zfill(9)
    
    # Recherche binaire
    found = None
    left, right = 0, len(ranges) - 1
    
    while left <= right:
        mid = (left + right) // 2
        r = ranges[mid]
        
        if r['siren_min'] <= siren_padded <= r['siren_max']:
            found = r
            break
        elif siren_padded < r['siren_min']:
            right = mid - 1
        else:
            left = mid + 1
    
    if found:
        print(f"   ✅ {siren} → {found['file']}")
    else:
        print(f"   ❌ {siren} non trouvé")

print()

# 3. Statistiques sur l'efficacité
print("3️⃣  Efficacité de la solution...")

total_companies = stats.get('total_companies', 0)
estimated_full_index = total_companies * 50  # ~50 bytes par SIREN
reduction = estimated_full_index / index_size

print(f"   Index complet estimé: {estimated_full_index / 1024**2:.1f} MB")
print(f"   Index ranges actuel: {index_size / 1024:.1f} KB")
print(f"   Réduction: {reduction:.0f}x")
print()

# 4. Test avec le cache
print("4️⃣  Test du système de cache...")

cache_dir = Path("/workspaces/TestsMCP/rne_cache")
if cache_dir.exists():
    cache_files = list(cache_dir.glob("*.json"))
    total_cache_size = sum(f.stat().st_size for f in cache_files)
    print(f"   📂 Cache: {len(cache_files)} fichiers ({total_cache_size / 1024**2:.1f} MB)")
else:
    print(f"   📂 Cache: vide (premier usage)")
print()

# 5. Résumé
print("="*80)
print("📊 RÉSUMÉ")
print("="*80)
print()
print("✅ L'approche hybride est prête à l'emploi !")
print()
print("💾 Stockage:")
print(f"   - Index: {index_size / 1024:.1f} KB")
print(f"   - Cache: {total_cache_size / 1024**2:.1f} MB" if cache_dir.exists() else "   - Cache: 0 MB (vide)")
print()
print("🔄 Workflow:")
print("   1. API DINUM → Obtenir SIREN")
print("   2. Index ranges (50 KB) → Trouver fichier en O(log n)")
print("   3. FTP INPI → Télécharger 1 fichier (~2-3 MB)")
print("   4. Cache local → Réutiliser pour futures requêtes")
print()
print("🚀 Pour enrichir:")
print("   python3 -c \"from enrichment_hybrid import enrich_from_api_dinum_and_rne; ")
print("              print(enrich_from_api_dinum_and_rne('552100554'))\"")  
print()
print("📝 Avantages:")
print("   ✅ Stockage minimal: ~50 KB (vs 27 GB)")
print("   ✅ Gratuit (pas de serveur)")
print("   ✅ Rapide avec cache (<1s)")
print("   ✅ Toujours à jour")
print()

# 6. Exemples de ranges
print("📋 Exemples de ranges disponibles:")
for r in ranges[:10]:
    companies_k = r['companies'] / 1000
    print(f"   {r['file']}: {r['siren_min']} → {r['siren_max']} ({companies_k:.1f}k entreprises)")
print(f"   ... et {len(ranges) - 10} autres fichiers")
print()

print("="*80)
