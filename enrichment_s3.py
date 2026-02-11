#!/usr/bin/env python3
"""
Exemple d'implémentation avec stockage distant (Amazon S3)
Alternative à la solution FTP gratuite

COÛT: ~$0,50-5/mois selon utilisation
"""

import json
import boto3
from typing import Dict, List, Optional
from pathlib import Path

# Configuration S3
S3_BUCKET = "mon-bucket-rne"  # À personnaliser
S3_PREFIX = "rne_data/"
INDEX_LOCAL = Path("/workspaces/TestsMCP/rne_siren_ranges.json")
CACHE_DIR = Path("/workspaces/TestsMCP/rne_cache")


class RNEStorageS3:
    """Gestionnaire de stockage RNE sur S3"""
    
    def __init__(self, bucket_name: str = S3_BUCKET):
        self.bucket = bucket_name
        self.s3_client = boto3.client('s3')
        self.index = self._load_index()
    
    def _load_index(self) -> Dict:
        """Charger l'index local (50 KB seulement)"""
        if not INDEX_LOCAL.exists():
            raise FileNotFoundError(f"Index non trouvé: {INDEX_LOCAL}")
        
        with open(INDEX_LOCAL, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def find_file_for_siren(self, siren: str) -> Optional[str]:
        """Trouver le fichier contenant un SIREN"""
        siren = str(siren).zfill(9)
        ranges = self.index['ranges']
        
        # Recherche binaire
        left, right = 0, len(ranges) - 1
        
        while left <= right:
            mid = (left + right) // 2
            r = ranges[mid]
            
            if r['siren_min'] <= siren <= r['siren_max']:
                return r['file']
            elif siren < r['siren_min']:
                right = mid - 1
            else:
                left = mid + 1
        
        return None
    
    def download_from_s3(self, filename: str, use_cache: bool = True) -> Optional[List[Dict]]:
        """Télécharger un fichier depuis S3"""
        cache_path = CACHE_DIR / filename
        
        # Cache
        if use_cache and cache_path.exists():
            print(f"📂 Cache: {filename}")
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # Télécharger depuis S3
        print(f"⬇️  S3: {filename} (~2-3 secondes)")
        
        try:
            s3_key = f"{S3_PREFIX}{filename}"
            
            # Télécharger
            response = self.s3_client.get_object(Bucket=self.bucket, Key=s3_key)
            data = json.loads(response['Body'].read().decode('utf-8'))
            
            # Mettre en cache
            if use_cache:
                CACHE_DIR.mkdir(exist_ok=True)
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False)
            
            return data
        
        except Exception as e:
            print(f"❌ Erreur S3: {e}")
            return None
    
    def get_company_bilans(self, siren: str) -> Optional[List[Dict]]:
        """Récupérer les bilans d'une entreprise depuis S3"""
        # Trouver le fichier
        filename = self.find_file_for_siren(siren)
        if not filename:
            return None
        
        # Télécharger
        data = self.download_from_s3(filename)
        if not data:
            return None
        
        # Filtrer par SIREN
        siren = str(siren).zfill(9)
        return [b for b in data if b.get('siren') == siren]


def upload_to_s3_once():
    """
    Script à exécuter UNE FOIS pour uploader les données vers S3
    
    Prérequis:
    - AWS CLI configuré (aws configure)
    - Extraction du ZIP : unzip stock_comptes_annuels.zip
    """
    import zipfile
    import os
    
    print("📤 Upload des fichiers RNE vers S3...")
    print(f"   Bucket: {S3_BUCKET}")
    print(f"   Cela va coûter ~$0,08/mois de stockage")
    print()
    
    # Extraire le ZIP
    zip_path = "/workspaces/TestsMCP/stock_comptes_annuels.zip"
    extract_dir = "/tmp/rne_extracted"
    
    if not os.path.exists(extract_dir):
        print(f"📦 Extraction du ZIP...")
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)
    
    # Upload vers S3
    s3 = boto3.client('s3')
    json_files = [f for f in os.listdir(extract_dir) if f.endswith('.json')]
    
    print(f"⬆️  Upload de {len(json_files)} fichiers vers S3...")
    
    for i, filename in enumerate(json_files, 1):
        if i % 50 == 0:
            print(f"   Progression: {i}/{len(json_files)} ({i*100/len(json_files):.1f}%)")
        
        local_path = os.path.join(extract_dir, filename)
        s3_key = f"{S3_PREFIX}{filename}"
        
        s3.upload_file(local_path, S3_BUCKET, s3_key)
    
    print(f"\n✅ Upload terminé !")
    print(f"   Bucket: s3://{S3_BUCKET}/{S3_PREFIX}")
    print(f"   Fichiers: {len(json_files)}")
    
    # Nettoyer
    print(f"\n🧹 Nettoyage local...")
    import shutil
    shutil.rmtree(extract_dir)
    
    print(f"✅ Vous pouvez maintenant utiliser RNEStorageS3()")


def enrich_with_s3(siren: str, max_bilans: int = 10) -> Dict:
    """Enrichir depuis S3"""
    storage = RNEStorageS3()
    
    bilans = storage.get_company_bilans(siren)
    if not bilans:
        return {
            "success": False,
            "error": f"Aucun bilan pour {siren}",
            "siren": siren
        }
    
    # Trier et limiter
    bilans.sort(key=lambda x: x.get("dateCloture", ""), reverse=True)
    bilans = bilans[:max_bilans]
    
    return {
        "success": True,
        "siren": siren,
        "denomination": bilans[0].get("denomination", ""),
        "nb_bilans": len(bilans),
        "bilans": bilans,
        "source": "Amazon S3"
    }


if __name__ == "__main__":
    print("="*80)
    print("☁️  STOCKAGE DISTANT - AMAZON S3")
    print("="*80)
    print("\n💰 Coût: ~$0,50-5/mois selon utilisation")
    print("⚡ Avantage: Très rapide, scalable")
    print("\n📝 Setup:")
    print("   1. aws configure")
    print("   2. python3 -c 'from enrichment_s3 import upload_to_s3_once; upload_to_s3_once()'")
    print("   3. Utiliser enrich_with_s3()")
    print()
    
    # Vérifier si configuré
    try:
        storage = RNEStorageS3()
        print("✅ S3 prêt à l'emploi")
    except Exception as e:
        print(f"⚠️  S3 non configuré: {e}")
        print("\nPour tester sans S3, utilisez enrichment_hybrid.py (gratuit)")
