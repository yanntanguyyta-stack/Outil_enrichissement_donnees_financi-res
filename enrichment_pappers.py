"""
Module d'enrichissement des données d'entreprises via l'API Pappers.fr
Récupère l'historique financier complet et données supplémentaires

Deux modes disponibles:
1. API (recommandé) - Nécessite clé API
2. Scraping (fallback) - Gratuit mais plus lent et fragile
"""

import os
import time
import random
import requests
import pandas as pd
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import re

# Charger les variables d'environnement
load_dotenv()

# Configuration
PAPPERS_API_KEY = os.getenv('PAPPERS_API_KEY', '')
PAPPERS_DELAY = float(os.getenv('PAPPERS_DELAY_SECONDS', '0.5'))
PAPPERS_BASE_URL = "https://api.pappers.fr/v2"
PAPPERS_WEB_URL = "https://www.pappers.fr/entreprise"
PAPPERS_MAX_RETRIES = 3

# Configuration scraping
SCRAPING_MIN_DELAY = float(os.getenv('SCRAPING_MIN_DELAY', '2.0'))
SCRAPING_MAX_DELAY = float(os.getenv('SCRAPING_MAX_DELAY', '5.0'))
SCRAPING_ENABLED = os.getenv('SCRAPING_ENABLED', 'true').lower() == 'true'

# User agents pour rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
]


def check_api_key() -> bool:
    """Vérifie si la clé API Pappers est configurée"""
    return bool(PAPPERS_API_KEY and PAPPERS_API_KEY != 'votre_cle_api_ici')


def get_random_delay() -> float:
    """Génère un délai aléatoire pour le scraping"""
    return random.uniform(SCRAPING_MIN_DELAY, SCRAPING_MAX_DELAY)


def get_random_headers() -> Dict[str, str]:
    """Génère des headers HTTP aléatoires pour éviter la détection"""
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
    }


def get_company_data_pappers(siren: str) -> Optional[Dict[str, Any]]:
    """
    Récupère les données complètes d'une entreprise via l'API Pappers
    
    Args:
        siren: Numéro SIREN de l'entreprise (9 chiffres)
        
    Returns:
        Dictionnaire avec les données de l'entreprise ou None en cas d'erreur
    """
    if not check_api_key():
        return None
    
    # Nettoyer le SIREN
    siren = str(siren).strip().replace(' ', '')[:9]
    if not siren.isdigit() or len(siren) != 9:
        return None
    
    url = f"{PAPPERS_BASE_URL}/entreprise"
    params = {
        'api_token': PAPPERS_API_KEY,
        'siren': siren,
        'format_publications_bodacc': 'true'
    }
    
    for attempt in range(PAPPERS_MAX_RETRIES):
        try:
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                # Rate limit - attendre plus longtemps
                wait_time = PAPPERS_DELAY * (2 ** attempt)
                time.sleep(wait_time)
                continue
            elif response.status_code == 404:
                # Entreprise non trouvée
                return None
            else:
                # Autre erreur
                if attempt < PAPPERS_MAX_RETRIES - 1:
                    time.sleep(PAPPERS_DELAY)
                    continue
                return None
                
        except requests.exceptions.RequestException:
            if attempt < PAPPERS_MAX_RETRIES - 1:
                time.sleep(PAPPERS_DELAY)
                continue
            return None
    
    return None


def scrape_company_data_pappers(siren: str) -> Optional[Dict[str, Any]]:
    """
    Récupère les données d'une entreprise par scraping web de Pappers.fr
    Fallback gratuit quand l'API n'est pas disponible
    
    Args:
        siren: Numéro SIREN de l'entreprise (9 chiffres)
        
    Returns:
        Dictionnaire avec les données financières ou None en cas d'erreur
    """
    if not SCRAPING_ENABLED:
        return None
    
    # Nettoyer le SIREN
    siren = str(siren).strip().replace(' ', '')[:9]
    if not siren.isdigit() or len(siren) != 9:
        return None
    
    # URL de la page entreprise
    url = f"{PAPPERS_WEB_URL}/{siren}"
    
    for attempt in range(PAPPERS_MAX_RETRIES):
        try:
            # Délai aléatoire avant la requête
            if attempt > 0:
                time.sleep(get_random_delay())
            
            # Requête HTTP avec headers aléatoires
            headers = get_random_headers()
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                # Parser le HTML
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extraire les données financières
                finances = []
                
                # Chercher la section des finances
                # Pappers.fr structure: tables avec class="financials" ou similaire
                finance_sections = soup.find_all(['table', 'div'], class_=re.compile(r'financ|bilan|compte', re.I))
                
                for section in finance_sections:
                    # Extraire les lignes de données
                    rows = section.find_all('tr')
                    
                    current_year_data = {}
                    current_year = None
                    
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 2:
                            label = cells[0].get_text(strip=True).lower()
                            value_text = cells[1].get_text(strip=True)
                            
                            # Détecter l'année
                            year_match = re.search(r'20\d{2}', value_text)
                            if year_match:
                                current_year = year_match.group()
                            
                            # Extraire les valeurs numériques
                            value_match = re.search(r'([\d\s]+)', value_text.replace(' ', ''))
                            if value_match:
                                try:
                                    value = int(value_match.group(1).replace(' ', ''))
                                    
                                    # Identifier le type de donnée
                                    if 'chiffre' in label or 'ca' in label:
                                        current_year_data['ca'] = value
                                    elif 'résultat' in label and 'net' in label:
                                        current_year_data['resultat_net'] = value
                                    elif 'effectif' in label:
                                        current_year_data['effectif'] = value
                                except ValueError:
                                    continue
                    
                    if current_year and current_year_data:
                        finances.append({
                            'date_cloture_exercice': f'{current_year}-12-31',
                            **current_year_data
                        })
                
                # Alternative: chercher les données dans le JSON embarqué
                scripts = soup.find_all('script', type='application/ld+json')
                for script in scripts:
                    try:
                        import json
                        data = json.loads(script.string)
                        if isinstance(data, dict) and 'finances' in data:
                            return {'finances': data['finances']}
                    except:
                        continue
                
                if finances:
                    return {'finances': finances}
                else:
                    return None
                    
            elif response.status_code == 404:
                return None
            elif response.status_code == 429:
                # Rate limit - attendre plus longtemps
                wait_time = get_random_delay() * (2 ** attempt)
                time.sleep(wait_time)
                continue
            else:
                if attempt < PAPPERS_MAX_RETRIES - 1:
                    time.sleep(get_random_delay())
                    continue
                return None
                
        except requests.exceptions.RequestException:
            if attempt < PAPPERS_MAX_RETRIES - 1:
                time.sleep(get_random_delay())
                continue
            return None
    
    return None


def get_company_data_unified(siren: str, prefer_api: bool = True) -> Optional[Dict[str, Any]]:
    """  
    Récupère les données d'entreprise avec fallback automatique API → Scraping
    
    Args:
        siren: Numéro SIREN de l'entreprise
        prefer_api: Si True, essaye l'API d'abord puis scraping. Si False, scraping uniquement.
        
    Returns:
        Dictionnaire avec les données ou None
    """
    # Tentative 1: API (si clé disponible et préférée)
    if prefer_api and check_api_key():
        data = get_company_data_pappers(siren)
        if data:
            return data
    
    # Tentative 2: Scraping (si activé)
    if SCRAPING_ENABLED:
        data = scrape_company_data_pappers(siren)
        if data:
            return data
    
    return None


def extract_financial_history(pappers_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extrait l'historique financier complet depuis les données Pappers
    
    Returns:
        Liste de dictionnaires avec année, CA, résultat net, effectif, etc.
    """
    history = []
    
    if not pappers_data or 'finances' not in pappers_data:
        return history
    
    for finance in pappers_data.get('finances', []):
        year_data = {
            'annee': finance.get('date_cloture_exercice', '')[:4],
            'ca': finance.get('chiffre_affaires'),
            'resultat_net': finance.get('resultat'),
            'effectif': finance.get('effectif'),
            'resultat_exploitation': finance.get('resultat_exploitation'),
            'excedent_brut_exploitation': finance.get('excedent_brut_exploitation'),
            'capacite_autofinancement': finance.get('capacite_autofinancement'),
            'fonds_roulement': finance.get('fonds_roulement'),
            'dette_financiere': finance.get('dette_financiere'),
            'marge_brute': finance.get('marge_brute'),
            'duree_exercice_mois': finance.get('duree_exercice')
        }
        history.append(year_data)
    
    # Trier par année décroissante
    history.sort(key=lambda x: x.get('annee', ''), reverse=True)
    return history


def format_financial_data(history: List[Dict[str, Any]], prefix: str = '') -> Dict[str, str]:
    """
    Formate les données financières pour l'export Excel
    Crée des colonnes distinctes pour chaque année
    
    Args:
        history: Liste des données financières par année
        prefix: Préfixe pour les noms de colonnes (ex: 'Pappers_')
        
    Returns:
        Dictionnaire avec colonnes formatées
    """
    formatted = {}
    
    for i, year_data in enumerate(history[:10]):  # Max 10 années
        year = year_data.get('annee', f'N-{i}')
        
        # Chiffre d'affaires
        ca = year_data.get('ca')
        formatted[f'{prefix}CA_{year}'] = _format_currency(ca) if ca else ''
        
        # Résultat net
        resultat = year_data.get('resultat_net')
        formatted[f'{prefix}Resultat_{year}'] = _format_currency(resultat) if resultat else ''
        
        # Effectif
        effectif = year_data.get('effectif')
        formatted[f'{prefix}Effectif_{year}'] = str(effectif) if effectif else ''
    
    # Statistiques sur l'historique
    if history:
        formatted[f'{prefix}Annees_Disponibles'] = len(history)
        formatted[f'{prefix}Derniere_Annee'] = history[0].get('annee', '')
    else:
        formatted[f'{prefix}Annees_Disponibles'] = 0
        formatted[f'{prefix}Derniere_Annee'] = ''
    
    return formatted


def _format_currency(value: Optional[float]) -> str:
    """Formate une valeur monétaire en euros"""
    if value is None:
        return ""
    try:
        return f"{int(value):,} €".replace(',', ' ')
    except (ValueError, TypeError):
        return ""


def enrich_with_pappers(df: pd.DataFrame, siren_column: str = 'SIREN') -> pd.DataFrame:
    """
    Enrichit un DataFrame avec les données financières de Pappers
    
    Args:
        df: DataFrame contenant au minimum une colonne SIREN
        siren_column: Nom de la colonne contenant les SIREN
        
    Returns:
        DataFrame enrichi avec les données Pappers
    """
    if not check_api_key():
        raise ValueError(
            "❌ Clé API Pappers non configurée.\n"
            "Créez un fichier .env avec PAPPERS_API_KEY=votre_clé\n"
            "Obtenez une clé sur: https://www.pappers.fr/api"
        )
    
    if siren_column not in df.columns:
        raise ValueError(f"Colonne '{siren_column}' introuvable dans le DataFrame")
    
    # Préparer la liste d'enrichissement
    enriched_data = []
    total = len(df)
    
    print(f"\n🔍 Enrichissement Pappers.fr de {total} entreprises...")
    print(f"⏱️  Délai entre requêtes: {PAPPERS_DELAY}s")
    
    start_time = time.time()
    
    for idx, row in df.iterrows():
        siren = str(row.get(siren_column, '')).strip()
        
        if not siren or siren == 'nan':
            enriched_data.append({})
            continue
        
        # Appel API Pappers avec fallback scraping
        pappers_data = get_company_data_unified(siren, prefer_api=True)
        
        if pappers_data:
            # Extraire l'historique financier
            history = extract_financial_history(pappers_data)
            formatted = format_financial_data(history, prefix='Pappers_')
            enriched_data.append(formatted)
            
            # Afficher progression
            if (idx + 1) % 10 == 0 or (idx + 1) == total:
                elapsed = time.time() - start_time
                rate = (idx + 1) / elapsed if elapsed > 0 else 0
                remaining = (total - idx - 1) / rate if rate > 0 else 0
                print(f"  ✓ {idx + 1}/{total} - {len(history)} années trouvées pour {siren} - "
                      f"Temps restant: ~{int(remaining)}s")
        else:
            enriched_data.append({})
        
        # Respecter le rate limit
        if idx < total - 1:
            # Si on utilise le scraping, délai aléatoire
            if not check_api_key() or pappers_data is None:
                delay = get_random_delay()
            else:
                delay = PAPPERS_DELAY
            time.sleep(delay)
    
    # Créer DataFrame avec les nouvelles colonnes
    enriched_df = pd.DataFrame(enriched_data)
    
    # Fusionner avec le DataFrame original
    result_df = pd.concat([df.reset_index(drop=True), enriched_df], axis=1)
    
    # Statistiques
    has_pappers_data = enriched_df.get('Pappers_Annees_Disponibles', pd.Series([0])) > 0
    success_count = has_pappers_data.sum()
    success_rate = (success_count / total * 100) if total > 0 else 0
    
    elapsed = time.time() - start_time
    print(f"\n✅ Enrichissement terminé en {int(elapsed)}s")
    print(f"📊 Données Pappers trouvées: {success_count}/{total} ({success_rate:.1f}%)")
    
    return result_df


def main():
    """Fonction de test du module"""
    has_api = check_api_key()
    
    if not has_api and not SCRAPING_ENABLED:
        print("❌ Ni API ni scraping configurés")
        print("Créez un fichier .env avec:")
        print("PAPPERS_API_KEY=votre_clé_ici")
        print("ou")
        print("SCRAPING_ENABLED=true")
        return
    
    if has_api:
        print("✅ Mode: API Pappers (avec fallback scraping)")
    else:
        print("⚠️  Mode: Scraping uniquement (API non configurée)")
        print(f"📊 Délais aléatoires: {SCRAPING_MIN_DELAY}s - {SCRAPING_MAX_DELAY}s")
    
    # Test avec quelques SIREN
    test_sirens = [
        '449162163',  # CISCO SYSTEMS CAPITAL FRANCE
        '552100554',  # CARREFOUR
        '542065479'   # ORANGE
    ]
    
    print("🧪 Test du module d'enrichissement Pappers\n")
    
    for siren in test_sirens:
        print(f"\n📊 Test SIREN: {siren}")
        data = get_company_data_unified(siren)
        
        if data:
            history = extract_financial_history(data)
            print(f"  ✓ {len(history)} années de données financières")
            
            if history:
                latest = history[0]
                print(f"  📅 Dernière année: {latest.get('annee')}")
                if latest.get('ca'):
                    print(f"  💰 CA: {_format_currency(latest.get('ca'))}")
                if latest.get('resultat_net'):
                    print(f"  📈 Résultat: {_format_currency(latest.get('resultat_net'))}")
        else:
            print("  ❌ Données non trouvées")
        
        time.sleep(PAPPERS_DELAY)


if __name__ == '__main__':
    main()
