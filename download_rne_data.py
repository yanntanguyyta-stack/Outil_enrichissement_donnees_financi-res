#!/usr/bin/env python3
"""
Script pour télécharger les dernières données RNE depuis le serveur FTP INPI
À exécuter périodiquement pour rafraîchir les données
"""

from ftplib import FTP
import os
from datetime import datetime

# Identifiants FTP RNE
FTP_HOST = "www.inpi.net"
FTP_USER = "rneinpiro"
FTP_PASSWORD = "vv8_rQ5f4M_2-E"

# Fichiers cibles
TARGET_FILE = "stock_RNE_comptes_annuels_20250926_1000_v2.zip"
LOCAL_PATH = "/workspaces/TestsMCP/stock_comptes_annuels.zip"

def download_rne_data():
    """Télécharge le fichier ZIP des comptes annuels depuis le FTP INPI"""
    
    print(f"🌐 Connexion au serveur FTP INPI...")
    print(f"   Hôte: {FTP_HOST}")
    print(f"   Utilisateur: {FTP_USER}")
    
    try:
        # Connexion FTP
        ftp = FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASSWORD)
        print("✅ Connexion établie !")
        
        # Lister les fichiers pour trouver le plus récent
        print("\n📋 Fichiers disponibles:")
        files = []
        ftp.retrlines('LIST', files.append)
        
        # Trouver les fichiers de comptes annuels
        comptes_files = [f for f in files if 'comptes_annuels' in f]
        for file_info in comptes_files:
            print(f"   {file_info}")
        
        # Vérifier si le fichier local existe déjà
        if os.path.exists(LOCAL_PATH):
            local_size = os.path.getsize(LOCAL_PATH)
            local_date = datetime.fromtimestamp(os.path.getmtime(LOCAL_PATH))
            print(f"\n📦 Fichier local existant:")
            print(f"   Taille: {local_size / 1024**3:.2f} GB")
            print(f"   Date: {local_date.strftime('%Y-%m-%d %H:%M:%S')}")
            
            response = input("\n❓ Voulez-vous re-télécharger ? (o/N): ")
            if response.lower() not in ['o', 'oui', 'y', 'yes']:
                print("⏭️  Téléchargement annulé")
                ftp.quit()
                return
        
        # Téléchargement
        print(f"\n⬇️  Téléchargement de {TARGET_FILE}...")
        print("   (Cela peut prendre plusieurs minutes...)")
        
        # Télécharger avec progression
        file_size = ftp.size(TARGET_FILE)
        downloaded = 0
        
        def callback(data):
            nonlocal downloaded
            downloaded += len(data)
            progress = (downloaded / file_size) * 100
            if downloaded % (50 * 1024 * 1024) == 0:  # Tous les 50 MB
                print(f"   Progression: {progress:.1f}% ({downloaded / 1024**3:.2f} GB)")
            file_handle.write(data)
        
        with open(LOCAL_PATH, 'wb') as file_handle:
            ftp.retrbinary(f'RETR {TARGET_FILE}', callback)
        
        print(f"\n✅ Téléchargement terminé !")
        print(f"   Fichier sauvegardé: {LOCAL_PATH}")
        print(f"   Taille: {os.path.getsize(LOCAL_PATH) / 1024**3:.2f} GB")
        
        ftp.quit()
        
        # Proposer d'extraire directement
        print("\n💡 Astuce: Lancez maintenant setup_rne_data.py pour extraire les données")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        raise

if __name__ == "__main__":
    download_rne_data()
