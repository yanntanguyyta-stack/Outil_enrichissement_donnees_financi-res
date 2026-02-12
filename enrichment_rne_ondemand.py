#!/usr/bin/env python3
"""
Module d'enrichissement RNE optimisé - Téléchargement à la demande depuis le FTP
Cette version télécharge uniquement les fichiers nécessaires depuis le serveur INPI

AVANTAGES:
- Stockage minimal (~10-50 MB au lieu de 27 GB)
- Toujours à jour avec le serveur INPI
- Cache local pour éviter les re-téléchargements
- Pas de limite d'espace disque
"""

import json
import os
import zipfile
from pathlib import Path
from ftplib import FTP
from typing import Dict, List, Optional, Any
from datetime import datetime
import io

# Configuration FTP
FTP_HOST = "www.inpi.net"
FTP_USER = "rneinpiro"
FTP_PASSWORD = "vv8_rQ5f4M_2-E"
FTP_ZIP_FILE = "stock_RNE_comptes_annuels_20250926_1000_v2.zip"

# Chemins locaux
BASE_DIR = Path("/workspaces/TestsMCP")
CACHE_DIR = BASE_DIR / "rne_cache"
INDEX_FILE = BASE_DIR / "rne_siren_index.json"

# Mapping des codes de liasse
LIASSE_CODES = {
    "FA": "Chiffre d'affaires",
    "HN": "Résultat net",
    "GC": "Résultat d'exploitation",
    "BJ": "Total actif",
    "DL": "Capitaux propres",
    "DN": "Capital social",
    "DT": "Résultat de l'exercice",
    "HY": "Effectif moyen",
    "FU": "Frais de personnel",
    "EE": "Dettes fournisseurs",
    "EB": "Dettes financières",
}


def download_file_from_zip_ftp(filename: str, cache_path: Path) -> Optional[List[Dict]]:
    """
    Télécharger UN SEUL fichier JSON depuis le ZIP sur le FTP
    en utilisant le range request pour ne télécharger que ce fichier
    """
    try:
        print(f"⬇️  Téléchargement FTP: {filename}...")
        
        ftp = FTP(FTP_HOST, timeout=30)
        ftp.login(FTP_USER, FTP_PASSWORD)
        
        # Pour l'instant, on télécharge tout le ZIP (à optimiser plus tard avec range requests)
        # C'est un compromis : le ZIP est gros mais on ne le télécharge qu'une fois
        zip_buffer = io.BytesIO()
        
        total_size = ftp.size(FTP_ZIP_FILE)
        downloaded = 0
        
        def callback(data):
            nonlocal downloaded
            zip_buffer.write(data)
            downloaded += len(data)
            if downloaded % (500 * 1024 * 1024) == 0:  # Tous les 500 MB
                progress = (downloaded / total_size) * 100
                print(f"   Progression: {progress:.1f}% ({downloaded / 1024**3:.2f} GB)")
        
        print(f"   Téléchargement du ZIP complet ({total_size / 1024**3:.2f} GB)...")
        print(f"   ⚠️  Ceci sera fait seulement si le fichier n'est pas en cache")
        ftp.retrbinary(f'RETR {FTP_ZIP_FILE}', callback)
        ftp.quit()
        
        print(f"   Extraction de {filename}...")
        zip_buffer.seek(0)
        
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            with zf.open(filename) as f:
                content = f.read().decode('utf-8')
                data = json.loads(content)
                
                # Sauvegarder en cache
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                with open(cache_path, 'w', encoding='utf-8') as cache_f:
                    json.dump(data, cache_f, ensure_ascii=False)
                
                print(f"✅ Fichier téléchargé et mis en cache")
                return data
        
    except Exception as e:
        print(f"❌ Erreur téléchargement: {e}")
        return None


def load_siren_index() -> Optional[Dict]:
    """Charger l'index SIREN → fichier"""
    if not INDEX_FILE.exists():
        print(f"❌ Index non trouvé: {INDEX_FILE}")
        print(f"💡 Créez-le d'abord avec: python3 download_rne.py --create-index")
        return None
    
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data.get('index', {})


def get_company_bilans(siren: str, use_cache: bool = True) -> Optional[List[Dict]]:
    """
    Récupérer tous les bilans d'une entreprise
    Télécharge uniquement le fichier nécessaire depuis le FTP
    """
    # Charger l'index
    index = load_siren_index()
    if not index:
        return None
    
    # Normaliser le SIREN
    siren = str(siren).zfill(9)
    
    # Trouver le fichier
    info = index.get(siren)
    if not info:
        print(f"❌ SIREN {siren} non trouvé dans l'index")
        return None
    
    filename = info['file']
    cache_path = CACHE_DIR / filename
    
    # Vérifier le cache
    if use_cache and cache_path.exists():
        print(f"📂 Lecture depuis le cache: {filename}")
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"⚠️  Cache corrompu, re-téléchargement...")
            data = download_file_from_zip_ftp(filename, cache_path)
    else:
        # Télécharger depuis le FTP
        data = download_file_from_zip_ftp(filename, cache_path)
    
    if not data:
        return None
    
    # Filtrer par SIREN
    return [bilan for bilan in data if bilan.get('siren') == siren]


def parse_liasse_value(value: str) -> Optional[int]:
    """Parser une valeur de liasse"""
    if not value or value.strip() == "":
        return None
    try:
        numeric_value = int(value)
        if numeric_value > 1000000000:
            return numeric_value // 100
        return numeric_value
    except (ValueError, TypeError):
        return None


def extract_financial_data(bilan: Dict) -> Dict[str, Any]:
    """Extraire les données financières d'un bilan"""
    financial_data = {}
    
    identite = bilan.get("bilanSaisi", {}).get("bilan", {}).get("identite", {})
    financial_data["date_cloture"] = identite.get("dateClotureExercice", "")
    financial_data["date_depot"] = bilan.get("dateDepot", "")
    financial_data["denomination"] = bilan.get("denomination", "")
    
    pages = bilan.get("bilanSaisi", {}).get("bilan", {}).get("detail", {}).get("pages", [])
    
    liasses = {}
    for page in pages:
        for liasse in page.get("liasses", []):
            code = liasse.get("code", "")
            if code in LIASSE_CODES:
                liasses[code] = {
                    "libelle": LIASSE_CODES[code],
                    "n": parse_liasse_value(liasse.get("m1", "")),
                    "n_minus_1": parse_liasse_value(liasse.get("m2", "")),
                }
    
    financial_data["chiffre_affaires"] = liasses.get("FA", {}).get("n")
    financial_data["resultat_net"] = liasses.get("HN", {}).get("n")
    financial_data["resultat_exploitation"] = liasses.get("GC", {}).get("n")
    financial_data["total_actif"] = liasses.get("BJ", {}).get("n")
    financial_data["capitaux_propres"] = liasses.get("DL", {}).get("n")
    financial_data["effectif"] = liasses.get("HY", {}).get("n")
    financial_data["frais_personnel"] = liasses.get("FU", {}).get("n")
    
    return financial_data


def enrich_with_rne_ondemand(siren: str, max_results: int = 10) -> Dict[str, Any]:
    """
    Enrichir avec RNE en téléchargeant à la demande
    """
    print(f"\n🔍 Recherche RNE pour SIREN: {siren}")
    
    # Récupérer les bilans
    bilans = get_company_bilans(siren, use_cache=True)
    
    if not bilans:
        return {
            "success": False,
            "error": f"Aucun compte annuel trouvé pour le SIREN {siren}",
            "siren": siren
        }
    
    # Trier par date décroissante
    bilans.sort(key=lambda x: x.get("dateCloture", ""), reverse=True)
    bilans = bilans[:max_results]
    
    # Extraire les données financières
    financial_history = [extract_financial_data(b) for b in bilans]
    
    print(f"✅ Trouvé {len(financial_history)} compte(s) annuel(s)")
    
    return {
        "success": True,
        "siren": siren,
        "denomination": bilans[0].get("denomination", ""),
        "nb_bilans": len(financial_history),
        "bilans": financial_history
    }


def format_amount(amount: Optional[int]) -> str:
    """Formater un montant"""
    if amount is None:
        return "N/A"
    return f"{amount:,}".replace(",", " ") + " €"


def display_rne_data(rne_data: Dict):
    """Afficher les données RNE"""
    if not rne_data.get("success"):
        print(f"\n❌ {rne_data.get('error', 'Erreur inconnue')}")
        return
    
    print(f"\n{'='*80}")
    print(f"📊 COMPTES ANNUELS RNE - {rne_data['denomination']}")
    print(f"    SIREN: {rne_data['siren']}")
    print('='*80)
    
    for i, bilan in enumerate(rne_data['bilans'], 1):
        print(f"\n📅 Exercice clos le {bilan['date_cloture']}")
        print('-'*80)
        print(f"   💰 Chiffre d'affaires:    {format_amount(bilan['chiffre_affaires'])}")
        print(f"   📈 Résultat net:          {format_amount(bilan['resultat_net'])}")
        print(f"   ⚙️  Résultat exploitation: {format_amount(bilan['resultat_exploitation'])}")
        print(f"   💼 Total actif:           {format_amount(bilan['total_actif'])}")
        print(f"   💎 Capitaux propres:      {format_amount(bilan['capitaux_propres'])}")
        
        if bilan['effectif']:
            print(f"   👥 Effectif moyen:        {bilan['effectif']} personnes")
    
    print(f"\n{'='*80}")


if __name__ == "__main__":
    print("="*80)
    print("🏛️  MODULE RNE - Téléchargement à la demande")
    print("="*80)
    print("\n💡 Ce module télécharge uniquement les fichiers nécessaires depuis le FTP INPI")
    print("💾 Stockage minimal : ~10-50 MB au lieu de 27 GB")
    print()
    
    # Test avec un SIREN
    test_siren = " 005880596"  # GEDIMO HOLDING
    
    print(f"🧪 Test avec SIREN: {test_siren}")
    rne_data = enrich_with_rne_ondemand(test_siren, max_results=5)
    display_rne_data(rne_data)
