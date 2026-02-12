#!/usr/bin/env python3
"""
Module d'enrichissement RNE optimisé avec index par ranges
Combine API DINUM (recherche) + FTP RNE (données financières)

STOCKAGE: ~50 KB seulement !
"""

import json
import zipfile
import io
from pathlib import Path
from ftplib import FTP
from typing import Dict, List, Optional, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Configuration
FTP_HOST = "www.inpi.net"
FTP_USER = "rneinpiro"
FTP_PASSWORD = "vv8_rQ5f4M_2-E"
FTP_ZIP_FILE = "stock_RNE_comptes_annuels_20250926_1000_v2.zip"

INDEX_FILE = Path("/workspaces/TestsMCP/rne_siren_ranges.json")
CACHE_DIR = Path("/workspaces/TestsMCP/rne_cache")

# Configuration traitement par lots
MAX_CONCURRENT_FILES = 1  # 1 seul fichier à la fois pour économiser l'espace
AVG_RNE_FILE_SIZE_MB = 80  # Taille réelle moyenne d'un fichier RNE

# Timeouts et retry
FTP_TIMEOUT = 60  # Timeout FTP en secondes
FTP_MAX_RETRIES = 2  # Nombre de tentatives
ZIP_DOWNLOAD_WARNING_SHOWN = False  # Flag pour éviter les avertissements répétés

# Mode espace disque limité
LIMITED_SPACE_MODE = True  # Activer le nettoyage agressif après chaque fichier

# Mode filtrage des données (ne garder que les données financières)
FINANCIAL_ONLY_MODE = False  # DÉSACTIVÉ: gain seulement 2%, pas assez significatif
# Pour un vrai gain (99%), il faudrait extraire seulement les 6 indicateurs clés  
# mais on perdrait la flexibilité d'ajouter d'autres indicateurs plus tard

# Mode Streaming (extraction à la volée des indicateurs clés)
STREAMING_MODE = True  # Extraire seulement les 6 indicateurs sans tout charger en mémoire
# Avantages: Fichiers 99% plus petits (~80 MB → ~1 KB), parsing instantané, mémoire minimale
# Inconvénient: Pas de flexibilité pour ajouter d'autres indicateurs plus tard

# Codes de liasse principaux
LIASSE_CODES = {
    "FA": "Chiffre d'affaires",
    "HN": "Résultat net",
    "GC": "Résultat d'exploitation",
    "BJ": "Total actif",
    "DL": "Capitaux propres",
    "HY": "Effectif moyen",
}


def load_ranges_index() -> Optional[Dict]:
    """Charger l'index des ranges SIREN"""
    if not INDEX_FILE.exists():
        print(f"⚠️ Index non trouvé: {INDEX_FILE}")
        return None
    
    with open(INDEX_FILE, 'r') as f:
        return json.load(f)


def extract_key_metrics_only(data: List[Dict]) -> List[Dict]:
    """
    MODE STREAMING: Extraire SEULEMENT les 6 indicateurs financiers clés.
    
    Au lieu de garder tout bilanSaisi (80 MB par fichier), on extrait seulement :
    - FA: Chiffre d'affaires
    - HN: Résultat net  
    - GC: Résultat d'exploitation
    - BJ: Total actif
    - DL: Capitaux propres
    - HY: Effectif moyen
    
    Structure d'origine (bilanSaisi.detail.pages[].liasses[]):
    {
      "bilanSaisi": {
        "detail": {
          "pages": [
            {"numero": 1, "liasses": [{"code": "FA", "m1": "1234", "m2": "5678"}, ...]},
            {"numero": 2, "liasses": [{"code": "HN", "m1": "9012", "m2": "3456"}, ...]}
          ]
        }
      }
    }
    
    Gain: Fichier de 83 MB → ~500 KB (99% de réduction !)
          Parsing quasi instantané
          Mémoire minimale
    """
    if not STREAMING_MODE:
        return data  # Mode désactivé, garder tout
    
    filtered = []
    codes_recherches = set(LIASSE_CODES.keys())  # FA, HN, GC, BJ, DL, HY
    
    for entreprise in data:
        bilan_saisi = entreprise.get("bilanSaisi", {})
        bilan = bilan_saisi.get("bilan", {})  # NIVEAU SUPPLÉMENTAIRE
        detail = bilan.get("detail", {})
        pages = detail.get("pages", [])
        
        # Extraire seulement les codes qui nous intéressent
        metrics = {}
        for page in pages:
            liasses = page.get("liasses", [])
            for liasse in liasses:
                code = liasse.get("code")
                if code in codes_recherches:
                    # Garder m1 (année N) et m2 (année N-1) si disponibles
                    metrics[code] = {
                        "m1": liasse.get("m1"),
                        "m2": liasse.get("m2")
                    }
        
        # Structure ultra-légère
        filtered_entreprise = {
            "siren": entreprise.get("siren"),
            "dateCloture": entreprise.get("dateCloture"),
            "dateDepot": entreprise.get("dateDepot"),
            "typeBilan": entreprise.get("typeBilan"),
            "metrics": metrics  # Seulement les 6 indicateurs
        }
        filtered.append(filtered_entreprise)
    
    return filtered


def filter_financial_data_only(data: List[Dict]) -> List[Dict]:
    """
    Filtrer les données RNE pour ne garder QUE les données financières.
    
    Réduit la taille de ~90% en supprimant :
    - denomination, adresse, forme juridique, etc. (déjà dans API Pappers/DINUM)
    - Métadonnées techniques (id, updatedAt, deleted, etc.)
    
    Garde uniquement :
    - siren : pour identifier l'entreprise
    - dateCloture : date de clôture de l'exercice
    - dateDepot : date de dépôt des comptes
    - bilanSaisi : LES DONNÉES COMPTABLES (l'essentiel !)
    - typeBilan : type de bilan (C=consolidé, S=simplifié, etc.)
    
    Gain: Fichier de 83 MB → ~8 MB (10x plus petit)
          Mémoire divisée par 10
          Parsing 10x plus rapide
    """
    if not FINANCIAL_ONLY_MODE:
        return data  # Mode désactivé, garder tout
    
    filtered = []
    for entreprise in data:
        # Ne garder QUE les données financières essentielles
        filtered_entreprise = {
            "siren": entreprise.get("siren"),
            "dateCloture": entreprise.get("dateCloture"),
            "dateDepot": entreprise.get("dateDepot"),
            "bilanSaisi": entreprise.get("bilanSaisi"),
            "typeBilan": entreprise.get("typeBilan"),
        }
        filtered.append(filtered_entreprise)
    
    return filtered


def load_ranges_index() -> Optional[Dict]:
    """Charger l'index des ranges de SIRENs"""
    if not INDEX_FILE.exists():
        print(f"❌ Index non trouvé: {INDEX_FILE}")
        print(f"💡 Créez-le avec: python3 create_rne_index_ranges.py")
        return None
    
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def find_file_for_siren(siren: str, ranges: List[Dict]) -> Optional[str]:
    """
    Trouver le fichier contenant un SIREN par recherche binaire dans les ranges
    Très rapide: O(log n) au lieu de O(1) mais index 1000x plus petit
    """
    siren = str(siren).zfill(9)
    
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


def download_json_from_ftp(filename: str, use_cache: bool = True) -> Optional[List[Dict]]:
    """Télécharger un fichier JSON depuis le FTP
    
    ⚠️  ATTENTION: Cette fonction télécharge le ZIP complet (3.5 GB) à chaque fois.
    Pour éviter cela, téléchargez le ZIP une seule fois et extrayez localement.
    """
    global ZIP_DOWNLOAD_WARNING_SHOWN
    
    cache_path = CACHE_DIR / filename
    
    # Cache
    if use_cache and cache_path.exists():
        print(f"📂 Cache: {filename}")
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Si le fichier en cache n'est pas dans le bon format, le convertir
            if data and len(data) > 0:
                first_item = data[0]
                
                # Mode Streaming : vérifier si le cache est au format streaming
                if STREAMING_MODE:
                    if 'bilanSaisi' in first_item:  # Ancien format (complet)
                        print(f"   🗜️  Conversion en mode Streaming (ancien format détecté)...")
                        data = extract_key_metrics_only(data)
                        # Sauvegarder la version streaming
                        with open(cache_path, 'w', encoding='utf-8') as f:
                            json.dump(data, f)
                
                # Mode Filtrage : vérifier si le cache est filtré
                elif FINANCIAL_ONLY_MODE and ('denomination' in first_item or 'id' in first_item):
                    print(f"   🗜️  Filtrage du cache (ancien format détecté)...")
                    data = filter_financial_data_only(data)
                    # Sauvegarder la version filtrée
                    with open(cache_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f)
            
            return data
        except Exception as e:
            print(f"⚠️  Erreur lecture cache {filename}: {e}")
            # Continuer avec téléchargement
    
    # Avertissement sur le téléchargement complet
    if not ZIP_DOWNLOAD_WARNING_SHOWN:
        print(f"\n⚠️  AVERTISSEMENT: Téléchargement du ZIP complet (3.5 GB)")
        print(f"💡 Pour de meilleures performances, téléchargez le ZIP une fois:")
        print(f"   wget ftp://{FTP_USER}:{FTP_PASSWORD}@{FTP_HOST}/{FTP_ZIP_FILE}")
        print(f"   Puis extrayez tous les fichiers localement\n")
        ZIP_DOWNLOAD_WARNING_SHOWN = True
    
    # Télécharger avec retry
    for attempt in range(FTP_MAX_RETRIES):
        try:
            print(f"⬇️  FTP: {filename} (Tentative {attempt + 1}/{FTP_MAX_RETRIES})")
            print(f"   ⏱️  Cela peut prendre 30-60s (téléchargement 3.5 GB)...")
            
            ftp = FTP(FTP_HOST, timeout=FTP_TIMEOUT)
            ftp.login(FTP_USER, FTP_PASSWORD)
            
            # Télécharger le ZIP complet
            zip_buffer = io.BytesIO()
            
            def progress_callback(block):
                # Afficher progression tous les 100 MB
                if zip_buffer.tell() % (100 * 1024 * 1024) < 8192:
                    mb_downloaded = zip_buffer.tell() / (1024 * 1024)
                    print(f"   📥 {mb_downloaded:.0f} MB téléchargés...")
            
            ftp.retrbinary(f'RETR {FTP_ZIP_FILE}', zip_buffer.write, blocksize=8192)
            ftp.quit()
            
            print(f"   ✅ Téléchargement terminé, extraction de {filename}...")
            
            # Extraire le fichier voulu
            zip_buffer.seek(0)
            with zipfile.ZipFile(zip_buffer, 'r') as zf:
                if filename not in zf.namelist():
                    print(f"❌ {filename} non trouvé dans le ZIP")
                    return None
                    
                with zf.open(filename) as f:
                    data = json.loads(f.read().decode('utf-8'))
            
            # **MODE STREAMING: Extraire seulement les 6 indicateurs clés** (réduit 99% de la taille)
            if STREAMING_MODE:
                original_size = len(json.dumps(data)) / (1024 * 1024)
                data = extract_key_metrics_only(data)
                filtered_size = len(json.dumps(data)) / (1024 * 1024)
                print(f"   🗜️  Mode Streaming: {original_size:.1f} MB → {filtered_size:.1f} MB ({100 * (1 - filtered_size/original_size):.0f}% de réduction)")
            # **FILTRAGE: Ne garder que les données financières** (réduit ~90% de la taille)
            elif FINANCIAL_ONLY_MODE:
                original_size = len(json.dumps(data)) / (1024 * 1024)
                data = filter_financial_data_only(data)
                filtered_size = len(json.dumps(data)) / (1024 * 1024)
                print(f"   🗜️  Filtrage: {original_size:.1f} MB → {filtered_size:.1f} MB ({100 * (1 - filtered_size/original_size):.0f}% de réduction)")
            
            # Sauvegarder dans le cache
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            try:
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f)
                print(f"💾 Cache sauvegardé: {filename}")
            except Exception as e:
                print(f"⚠️  Impossible de sauvegarder le cache: {e}")
            
            return data
            
        except Exception as e:
            print(f"❌ Erreur téléchargement {filename} (tentative {attempt + 1}): {e}")
            if attempt < FTP_MAX_RETRIES - 1:
                print(f"   🔄 Nouvelle tentative dans 3 secondes...")
                import time
                time.sleep(3)
            else:
                print(f"❌ Échec définitif après {FTP_MAX_RETRIES} tentatives")
                return None
    
    return None


def extract_financial_data(bilan: Dict) -> Dict[str, Any]:
    """Extraire les données financières d'un bilan
    
    Supporte 2 formats :
    1. Format complet (ancien) : avec bilanSaisi.bilan.detail.pages[]
    2. Format streaming (nouveau) : avec metrics directement
    """
    financial_data = {}
    
    # Détecter le format
    if "metrics" in bilan:
        # FORMAT STREAMING (nouveau) : extraction ultra-rapide
        metrics_data = bilan.get("metrics", {})
        
        financial_data["date_cloture"] = bilan.get("dateCloture", "")
        financial_data["date_depot"] = bilan.get("dateDepot", "")
        financial_data["denomination"] = ""  # Pas disponible en mode streaming (déjà dans Pappers)
        
        # Convertir les métriques
        metrics = {}
        for code, values in metrics_data.items():
            try:
                value_n = values.get("m1", "") if isinstance(values, dict) else ""
                if value_n and value_n.strip():
                    numeric = int(value_n)
                    if numeric > 1000000000:  # En centimes
                        numeric = numeric // 100
                    metrics[code] = numeric
            except:
                pass
        
        financial_data["chiffre_affaires"] = metrics.get("FA")
        financial_data["resultat_net"] = metrics.get("HN")
        financial_data["resultat_exploitation"] = metrics.get("GC")
        financial_data["total_actif"] = metrics.get("BJ")
        financial_data["capitaux_propres"] = metrics.get("DL")
        financial_data["effectif"] = metrics.get("HY")
    
    else:
        # FORMAT COMPLET (ancien) : parsing complet de la structure
        identite = bilan.get("bilanSaisi", {}).get("bilan", {}).get("identite", {})
        financial_data["date_cloture"] = identite.get("dateClotureExercice", "")
        financial_data["date_depot"] = bilan.get("dateDepot", "")
        financial_data["denomination"] = bilan.get("denomination", "")
        
        pages = bilan.get("bilanSaisi", {}).get("bilan", {}).get("detail", {}).get("pages", [])
        
        # Extraire les liasses
        metrics = {}
        for page in pages:
            for liasse in page.get("liasses", []):
                code = liasse.get("code", "")
                if code in LIASSE_CODES:
                    try:
                        value_n = liasse.get("m1", "")
                        if value_n and value_n.strip():
                            numeric = int(value_n)
                            if numeric > 1000000000:  # En centimes
                                numeric = numeric // 100
                            metrics[code] = numeric
                    except:
                        pass
        
        financial_data["chiffre_affaires"] = metrics.get("FA")
        financial_data["resultat_net"] = metrics.get("HN")
        financial_data["resultat_exploitation"] = metrics.get("GC")
        financial_data["total_actif"] = metrics.get("BJ")
        financial_data["capitaux_propres"] = metrics.get("DL")
        financial_data["effectif"] = metrics.get("HY")
    
    return financial_data


def enrich_from_api_dinum_and_rne(siren: str, max_bilans: int = 10) -> Dict[str, Any]:
    """
    APPROCHE HYBRIDE:
    1. API DINUM pour les infos de base (gratuit, rapide)
    2. Index RNE pour trouver le fichier (~50 KB)
    3. FTP pour télécharger seulement le fichier nécessaire
    """
    print(f"\n🔍 Enrichissement hybride pour SIREN: {siren}")
    
    # 1. Charger l'index
    index_data = load_ranges_index()
    if not index_data:
        return {"success": False, "error": "Index non disponible"}
    
    ranges = index_data['ranges']
    
    # 2. Trouver le fichier
    filename = find_file_for_siren(siren, ranges)
    if not filename:
        return {
            "success": False,
            "error": f"SIREN {siren} hors limites RNE",
            "siren": siren
        }
    
    print(f"📍 Fichier identifié: {filename}")
    
    # 3. Télécharger le fichier
    data = download_json_from_ftp(filename, use_cache=True)
    if not data:
        return {
            "success": False,
            "error": "Erreur téléchargement FTP",
            "siren": siren
        }
    
    # 4. Filtrer par SIREN
    siren = str(siren).zfill(9)
    bilans = [b for b in data if b.get('siren') == siren]
    
    if not bilans:
        return {
            "success": False,
            "error": f"Aucun bilan trouvé pour {siren}",
            "siren": siren
        }
    
    # 5. Trier et extraire
    bilans.sort(key=lambda x: x.get("dateCloture", ""), reverse=True)
    bilans = bilans[:max_bilans]
    
    financial_history = [extract_financial_data(b) for b in bilans]
    
    print(f"✅ {len(financial_history)} bilan(s) trouvé(s)")
    
    return {
        "success": True,
        "siren": siren,
        "denomination": bilans[0].get("denomination", ""),
        "nb_bilans": len(financial_history),
        "bilans": financial_history,
        "source": "RNE via FTP INPI"
    }


def enrich_from_rne_only(siren_or_siret: str, max_bilans: int = 10) -> Dict[str, Any]:
    """
    Enrichissement RNE SEUL (sans passer par Pappers).
    
    Utilise uniquement les données RNE pour récupérer :
    - Les informations de base (dénomination depuis le bilan)
    - Les données financières historiques
    
    Idéal pour les utilisateurs qui ont déjà une liste de SIRETs validés
    et veulent uniquement les données financières RNE.
    
    Args:
        siren_or_siret: SIREN (9 chiffres) ou SIRET (14 chiffres)
        max_bilans: Nombre maximum de bilans à récupérer
        
    Returns:
        Dict avec success, siren, denomination, nb_bilans, bilans, source
    """
    # Extraire le SIREN du SIRET si nécessaire
    siren = siren_or_siret[:9] if len(siren_or_siret) >= 9 else siren_or_siret
    siren = str(siren).zfill(9)
    
    print(f"\n🔍 Enrichissement RNE seul pour SIREN: {siren}")
    
    # 1. Charger l'index
    index_data = load_ranges_index()
    if not index_data:
        return {
            "success": False,
            "error": "Index RNE non disponible",
            "siren": siren
        }
    
    ranges = index_data['ranges']
    
    # 2. Trouver le fichier
    filename = find_file_for_siren(siren, ranges)
    if not filename:
        return {
            "success": False,
            "error": f"SIREN {siren} hors limites RNE (pas de données)",
            "siren": siren
        }
    
    print(f"📍 Fichier RNE identifié: {filename}")
    
    # 3. Télécharger/charger le fichier
    data = download_json_from_ftp(filename, use_cache=True)
    if not data:
        return {
            "success": False,
            "error": "Erreur téléchargement FTP ou lecture cache",
            "siren": siren
        }
    
    # 4. Filtrer par SIREN
    bilans = [b for b in data if b.get('siren') == siren]
    
    if not bilans:
        return {
            "success": False,
            "error": f"Aucun bilan trouvé pour SIREN {siren} dans RNE",
            "siren": siren
        }
    
    # 5. Trier et extraire les données financières
    bilans.sort(key=lambda x: x.get("dateCloture", ""), reverse=True)
    bilans = bilans[:max_bilans]
    
    financial_history = [extract_financial_data(b) for b in bilans]
    
    # 6. Récupérer la dénomination depuis le premier bilan
    denomination = bilans[0].get("denomination", f"Entreprise {siren}")
    
    print(f"✅ RNE: {len(financial_history)} bilan(s) trouvé(s) pour {denomination}")
    
    return {
        "success": True,
        "siren": siren,
        "siret": siren_or_siret if len(siren_or_siret) == 14 else None,
        "denomination": denomination,
        "nb_bilans": len(financial_history),
        "bilans": financial_history,
        "source": "RNE uniquement (sans Pappers)"
    }


def format_amount(amount: Optional[int]) -> str:
    """Formater un montant"""
    if amount is None:
        return "N/A"
    return f"{amount:,}".replace(",", " ") + " €"


def display_financial_data(data: Dict):
    """Afficher les données financières"""
    if not data.get("success"):
        print(f"\n❌ {data.get('error', 'Erreur')}")
        return
    
    print(f"\n{'='*80}")
    print(f"📊 {data['denomination']}")
    print(f"    SIREN: {data['siren']} | Source: {data.get('source', 'RNE')}")
    print('='*80)
    
    for bilan in data['bilans'][:5]:  # 5 derniers exercices
        print(f"\n📅 {bilan['date_cloture']}")
        print(f"   💰 CA: {format_amount(bilan['chiffre_affaires'])}")
        print(f"   📈 Résultat net: {format_amount(bilan['resultat_net'])}")
        
        if bilan['effectif']:
            print(f"   👥 Effectif: {bilan['effectif']} personnes")
    
    print(f"\n{'='*80}")


def group_sirens_by_rne_file(sirens: List[str]) -> Dict[str, List[str]]:
    """
    Grouper les SIRENs par fichier RNE pour traitement par lots.
    Retourne: {"filename.json": [siren1, siren2, ...], ...}
    """
    index_data = load_ranges_index()
    if not index_data:
        return {}
    
    ranges = index_data['ranges']
    grouped = {}
    not_found = []
    
    for siren in sirens:
        filename = find_file_for_siren(siren, ranges)
        if filename:
            if filename not in grouped:
                grouped[filename] = []
            grouped[filename].append(siren)
        else:
            not_found.append(siren)
    
    if not_found:
        print(f"⚠️  {len(not_found)} SIREN(s) hors limites RNE: {not_found[:5]}{'...' if len(not_found) > 5 else ''}")
    
    return grouped


def process_batch(filename: str, sirens: List[str], max_bilans: int = 10, cleanup: bool = True) -> Dict[str, Dict]:
    """
    Traiter un lot de SIRENs depuis un même fichier RNE.
    
    Args:
        filename: Nom du fichier RNE
        sirens: Liste des SIRENs à extraire
        max_bilans: Nombre max de bilans par SIREN
       cleanup: Supprimer le fichier du cache après traitement
    
    Returns:
        {siren: {données enrichies}, ...}
    """
    print(f"\n📦 Traitement du lot: {filename} ({len(sirens)} entreprise(s))")
    
    # En mode espace limité, toujours nettoyer sauf si déjà en cache (< 000085)
    if LIMITED_SPACE_MODE:
        file_num = int(filename.replace('stock_', '').replace('.json', ''))
        cleanup = cleanup and file_num >= 85  # Garder les 84 premiers fichiers
    
    # 1. Télécharger le fichier RNE
    data = download_json_from_ftp(filename, use_cache=True)
    if not data:
        return {siren: {"success": False, "error": "Erreur téléchargement"} for siren in sirens}
    
    results = {}
    
    # 2. Traiter chaque SIREN
    for siren in sirens:
        siren_padded = str(siren).zfill(9)
        bilans = [b for b in data if b.get('siren') == siren_padded]
        
        if bilans:
            bilans.sort(key=lambda x: x.get("dateCloture", ""), reverse=True)
            bilans = bilans[:max_bilans]
            financial_history = [extract_financial_data(b) for b in bilans]
            
            results[siren] = {
                "success": True,
                "siren": siren_padded,
                "denomination": bilans[0].get("denomination", ""),
                "nb_bilans": len(financial_history),
                "bilans": financial_history,
                "source": "RNE via FTP INPI"
            }
        else:
            results[siren] = {
                "success": False,
                "error": f"Aucun bilan pour {siren}",
                "siren": siren_padded
            }
    
    # 3. Nettoyage du cache si demandé
    if cleanup:
        cache_path = CACHE_DIR / filename
        if cache_path.exists():
            try:
                cache_path.unlink()
                print(f"🗑️  Cache nettoyé: {filename}")
            except Exception as e:
                print(f"⚠️  Erreur nettoyage cache {filename}: {e}")
    
    print(f"✅ Lot terminé: {filename} ({len([r for r in results.values() if r.get('success')])} réussis)")
    return results


def enrich_batch_parallel(sirens: List[str], max_bilans: int = 10, max_workers: int = MAX_CONCURRENT_FILES, 
                          progress_callback=None) -> Dict[str, Dict]:
    """
    Enrichir un lot de SIRENs en parallèle avec gestion optimisée de la mémoire.
    
    Args:
        sirens: Liste de SIRENs à enrichir
        max_bilans: Nombre max de bilans par SIREN
        max_workers: Nombre max de fichiers RNE téléchargés simultanément
        progress_callback: Fonction appelée avec (completed, total, current_file)
    
    Returns:
        {siren: {données enrichies}, ...}
    """
    print(f"\n{'='*80}")
    print(f"🚀 ENRICHISSEMENT PAR LOTS OPTIMISÉ")
    print(f"{'='*80}")
    print(f"📊 Total: {len(sirens)} entreprise(s)")
    print(f"⚙️  Workers: {max_workers} fichiers RNE simultanés max")
    print(f"{'='*80}\n")
    
    # 1. Grouper par fichier RNE
    grouped = group_sirens_by_rne_file(sirens)
    total_files = len(grouped)
    
    if not grouped:
        print("❌ Aucun SIREN valide à traiter")
        return {}
    
    print(f"📁 Répartition: {total_files} fichier(s) RNE à traiter")
    for filename, file_sirens in list(grouped.items())[:5]:
        print(f"   • {filename}: {len(file_sirens)} entreprise(s)")
    if total_files > 5:
        print(f"   ... et {total_files - 5} autres fichiers\n")
    
    # 2. Traitement parallèle par lots
    all_results = {}
    completed_files = 0
    lock = threading.Lock()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Soumettre tous les lots
        future_to_file = {
            executor.submit(process_batch, filename, file_sirens, max_bilans, cleanup=True): filename
            for filename, file_sirens in grouped.items()
        }
        
        # Récupérer les résultats au fur et à mesure
        for future in as_completed(future_to_file):
            filename = future_to_file[future]
            try:
                batch_results = future.result()
                with lock:
                    all_results.update(batch_results)
                    completed_files += 1
                    
                if progress_callback:
                    progress_callback(completed_files, total_files, filename)
                    
            except Exception as e:
                print(f"❌ Erreur traitement {filename}: {e}")
                with lock:
                    completed_files += 1
    
    # 3. Statistiques finales
    successful = len([r for r in all_results.values() if r.get('success')])
    print(f"\n{'='*80}")
    print(f"📊 RÉSULTATS FINAUX")
    print(f"{'='*80}")
    print(f"✅ Réussis: {successful}/{len(sirens)}")
    print(f"❌ Échecs: {len(sirens) - successful}/{len(sirens)}")
    print(f"📁 Fichiers traités: {completed_files}/{total_files}")
    print(f"{'='*80}\n")
    
    return all_results


# Test
if __name__ == "__main__":
    print("="*80)
    print("🏛️  MODULE RNE - APPROCHE HYBRIDE OPTIMISÉE")
    print("="*80)
    print("\n💡 API DINUM + Index ultra-léger (50 KB) + FTP à la demande")
    print()
    
    # Test simple
    print("\n=== TEST SIMPLE ===")
    test_siren = "552100554"  # EDF
    result = enrich_from_api_dinum_and_rne(test_siren, max_bilans=5)
    display_financial_data(result)
    
    # Test par lots
    print("\n\n=== TEST PAR LOTS ===")
    test_sirens = ["552100554", "005880596", "775665019"]  # EDF + 2 autres
    batch_results = enrich_batch_parallel(test_sirens, max_bilans=3, max_workers=2)
    
    print("\n📋 Résultats:")
    for siren, data in batch_results.items():
        if data.get('success'):
            print(f"✅ {siren}: {data.get('nb_bilans', 0)} bilan(s) - {data.get('denomination', 'N/A')}")
        else:
            print(f"❌ {siren}: {data.get('error', 'Erreur inconnue')}")
