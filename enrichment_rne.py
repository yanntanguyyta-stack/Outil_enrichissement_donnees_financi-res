"""
Module d'enrichissement via les données RNE (Registre National des Entreprises)
Utilise les fichiers téléchargés du serveur FTP INPI
"""

import json
import zipfile
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

# Chemins des fichiers
RNE_ZIP_PATH = "/workspaces/TestsMCP/stock_comptes_annuels.zip"
RNE_EXTRACT_DIR = "/workspaces/TestsMCP/rne_data"

# Mapping des codes de liasse vers des libellés lisibles
LIASSE_CODES = {
    # Bilan - Actif
    "AF": "Capital souscrit non appelé",
    "BB": "Total actif immobilisé",
    "BJ": "Total actif",
    "BX": "Stocks et en-cours",
    "BZ": "Créances clients",
    "CB": "Disponibilités",
    
    # Bilan - Passif
    "DL": "Capitaux propres",
    "DN": "Capital social",
    "DT": "Résultat de l'exercice",
    "EB": "Dettes financières",
    "EE": "Dettes fournisseurs",
    "EV": "Total passif",
    
    # Compte de résultat
    "FA": "Chiffre d'affaires",
    "FC": "Production stockée",
    "FL": "Total produits d'exploitation",
    "FP": "Achats consommés",
    "FR": "Charges externes",
    "FT": "Impôts et taxes",
    "FU": "Frais de personnel",
    "FV": "Dotations amortissements",
    "FW": "Autres charges",
    "FX": "Total charges d'exploitation",
    "GC": "Résultat d'exploitation",
    "GE": "Produits financiers",
    "GG": "Charges financières",
    "GW": "Résultat courant",
    "HN": "Résultat net",
    "HY": "Effectif moyen",
}


def is_rne_available() -> bool:
    """Vérifier si les données RNE sont disponibles localement"""
    # Préférer les fichiers extraits, sinon le ZIP
    json_files = list(Path(RNE_EXTRACT_DIR).glob("*.json")) if os.path.exists(RNE_EXTRACT_DIR) else []
    return len(json_files) > 0 or os.path.exists(RNE_ZIP_PATH)


def parse_liasse_value(value: str) -> Optional[int]:
    """
    Parser une valeur de liasse (format: 15 caractères numériques)
    Retourne None si vide ou invalide
    Les valeurs sont en centimes, on les convertit en euros
    """
    if not value or value.strip() == "":
        return None
    
    try:
        # Supprimer les zéros initiaux et parser
        numeric_value = int(value)
        # Les valeurs sont parfois en centimes, parfois en euros
        # On détecte selon la taille
        if numeric_value > 1000000000:  # Plus de 10M€, probablement en centimes
            return numeric_value // 100
        return numeric_value
    except (ValueError, TypeError):
        return None


def extract_financial_data(bilan: Dict) -> Dict[str, Any]:
    """
    Extraire les données financières d'un bilan
    """
    financial_data = {}
    
    # Extraire l'identité
    identite = bilan.get("bilanSaisi", {}).get("bilan", {}).get("identite", {})
    financial_data["date_cloture"] = identite.get("dateClotureExercice", "")
    financial_data["date_depot"] = bilan.get("dateDepot", "")
    financial_data["code_activite"] = identite.get("codeActivite", "")
    financial_data["type_bilan"] = bilan.get("typeBilan", "")
    
    # Extraire les liasses
    pages = bilan.get("bilanSaisi", {}).get("bilan", {}).get("detail", {}).get("pages", [])
    
    liasses = {}
    for page in pages:
        for liasse in page.get("liasses", []):
            code = liasse.get("code", "")
            if code in LIASSE_CODES:
                liasses[code] = {
                    "libelle": LIASSE_CODES[code],
                    "n": parse_liasse_value(liasse.get("m1", "")),
                    "n_moins_1": parse_liasse_value(liasse.get("m2", "")),
                }
    
    financial_data["liasses"] = liasses
    
    # Extraire les principales métriques
    financial_data["chiffre_affaires"] = liasses.get("FA", {}).get("n")
    financial_data["resultat_net"] = liasses.get("HN", {}).get("n")
    financial_data["resultat_exploitation"] = liasses.get("GC", {}).get("n")
    financial_data["total_actif"] = liasses.get("BJ", {}).get("n")
    financial_data["capitaux_propres"] = liasses.get("DL", {}).get("n")
    financial_data["effectif"] = liasses.get("HY", {}).get("n")
    
    return financial_data


def search_company_in_file(json_file_path: str, siren: str) -> List[Dict]:
    """
    Rechercher une entreprise dans un fichier JSON
    Retourne la liste de tous ses bilans
    """
    bilans = []
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            # Le fichier contient une seule ligne avec un array
            content = f.read()
            companies_data = json.loads(content)
            
            # Filtrer par SIREN
            for bilan in companies_data:
                if bilan.get("siren") == siren:
                    bilans.append(bilan)
    
    except Exception as e:
        print(f"❌ Erreur lors de la lecture de {json_file_path}: {str(e)}")
    
    return bilans


def enrich_with_rne(siren: str, max_results: int = 10) -> Dict[str, Any]:
    """
    Enrichir les données d'une entreprise avec les comptes annuels du RNE
    
    Args:
        siren: Numéro SIREN de l'entreprise (9 chiffres)
        max_results: Nombre maximum de bilans à retourner (par défaut 10, pour les 10 dernières années)
    
    Returns:
        Dict contenant les données enrichies
    """
    if not is_rne_available():
        return {
            "success": False,
            "error": "Données RNE non disponibles. Téléchargez d'abord le fichier via FTP.",
            "siren": siren
        }
    
    # Normaliser le SIREN (9 chiffres)
    siren = str(siren).zfill(9)
    
    all_bilans = []
    
    try:
        # Vérifier si les fichiers JSON sont extraits localement
        json_files_local = list(Path(RNE_EXTRACT_DIR).glob("*.json")) if os.path.exists(RNE_EXTRACT_DIR) else []
        
        if json_files_local:
            # MÉTHODE 1: Utiliser les fichiers JSON extraits (RAPIDE)
            print(f"🔍 Recherche du SIREN {siren} dans {len(json_files_local)} fichiers locaux...")
            
            for i, json_file_path in enumerate(json_files_local):
                # Afficher progression tous les 100 fichiers
                if (i + 1) % 100 == 0:
                    print(f"   Progression: {i+1}/{len(json_files_local)} fichiers analysés...")
                
                try:
                    with open(json_file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        companies_data = json.loads(content)
                        
                        # Filtrer par SIREN
                        for bilan in companies_data:
                            if bilan.get("siren") == siren:
                                all_bilans.append(bilan)
                
                except Exception as e:
                    # Continuer même si un fichier est corrompu
                    continue
                
                # Arrêter si on a trouvé assez de bilans
                if len(all_bilans) >= max_results:
                    break
        
        else:
            # MÉTHODE 2 (FALLBACK): Lire depuis le ZIP (LENT)
            print(f"⚠️  Fichiers non extraits, lecture depuis le ZIP...")
            print(f"💡 Astuce: Lancez 'python3 setup_rne_data.py' pour extraire les données et accélérer les recherches")
            
            with zipfile.ZipFile(RNE_ZIP_PATH, 'r') as zip_ref:
                json_files = [f for f in zip_ref.namelist() if f.endswith('.json')]
                
                print(f"🔍 Recherche du SIREN {siren} dans {len(json_files)} fichiers...")
                
                for i, json_file in enumerate(json_files):
                    # Afficher progression tous les 100 fichiers
                    if (i + 1) % 100 == 0:
                        print(f"   Progression: {i+1}/{len(json_files)} fichiers analysés...")
                    
                    # Lire le fichier directement depuis le ZIP
                    with zip_ref.open(json_file) as f:
                        try:
                            content = f.read().decode('utf-8')
                            companies_data = json.loads(content)
                            
                            # Filtrer par SIREN
                            for bilan in companies_data:
                                if bilan.get("siren") == siren:
                                    all_bilans.append(bilan)
                        
                        except Exception as e:
                            # Continuer même si un fichier est corrompu
                            continue
                    
                    # Arrêter si on a trouvé assez de bilans
                    if len(all_bilans) >= max_results:
                        break
        
        if not all_bilans:
            return {
                "success": False,
                "error": f"Aucun compte annuel trouvé pour le SIREN {siren}",
                "siren": siren
            }
        
        # Trier par date de clôture décroissante (plus récent d'abord)
        all_bilans.sort(key=lambda x: x.get("dateCloture", ""), reverse=True)
        
        # Limiter au nombre demandé
        all_bilans = all_bilans[:max_results]
        
        # Extraire les données financières
        financial_history = []
        for bilan in all_bilans:
            financial_data = extract_financial_data(bilan)
            financial_history.append(financial_data)
        
        print(f"✅ Trouvé {len(financial_history)} compte(s) annuel(s) pour {siren}")
        
        return {
            "success": True,
            "siren": siren,
            "denomination": all_bilans[0].get("denomination", ""),
            "nb_bilans": len(financial_history),
            "bilans": financial_history
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Erreur lors de l'enrichissement RNE: {str(e)}",
            "siren": siren
        }


def format_amount(amount: Optional[int]) -> str:
    """Formater un montant en euros"""
    if amount is None:
        return "N/A"
    return f"{amount:,}".replace(",", " ") + " €"


def display_rne_data(rne_data: Dict) -> None:
    """
    Afficher les données RNE de manière lisible
    """
    if not rne_data.get("success"):
        print(f"❌ {rne_data.get('error', 'Erreur inconnue')}")
        return
    
    print("\n" + "="*80)
    print(f"📊 COMPTES ANNUELS RNE - {rne_data['denomination']}")
    print(f"    SIREN: {rne_data['siren']}")
    print("="*80)
    
    for i, bilan in enumerate(rne_data["bilans"], 1):
        print(f"\n📅 Exercice clos le {bilan['date_cloture']} (déposé le {bilan['date_depot']})")
        print("-" * 80)
        
        print(f"   💰 Chiffre d'affaires:    {format_amount(bilan['chiffre_affaires'])}")
        print(f"   📈 Résultat net:          {format_amount(bilan['resultat_net'])}")
        print(f"   ⚙️  Résultat exploitation: {format_amount(bilan['resultat_exploitation'])}")
        print(f"   💼 Total actif:           {format_amount(bilan['total_actif'])}")
        print(f"   💎 Capitaux propres:      {format_amount(bilan['capitaux_propres'])}")
        
        if bilan['effectif']:
            print(f"   👥 Effectif moyen:        {bilan['effectif']} personnes")
    
    print("\n" + "="*80)


# Test de fonctionnalité
if __name__ == "__main__":
    print("="*80)
    print("🏛️  MODULE D'ENRICHISSEMENT RNE")
    print("="*80)
    print()
    
    # Vérifier disponibilité
    if is_rne_available():
        print("✅ Données RNE disponibles")
        print(f"   Fichier: {RNE_ZIP_PATH}")
        print(f"   Taille: {os.path.getsize(RNE_ZIP_PATH) / (1024**3):.2f} GB")
    else:
        print("❌ Données RNE non disponibles")
        print("   Téléchargez d'abord le fichier via: python3 download_rne.py")
        exit(1)
    
    # Test avec un SIREN exemple (si disponible dans les données)
    test_siren = "005880596"  # GEDIMO HOLDING (vu dans l'exemple)
    
    print(f"\n🧪 Test avec le SIREN: {test_siren}")
    print("-" * 80)
    
    rne_data = enrich_with_rne(test_siren, max_results=5)
    display_rne_data(rne_data)
