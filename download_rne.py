"""
Script pour télécharger et explorer les fichiers du RNE
"""

from ftplib import FTP
import os

# Configuration FTP RNE
FTP_HOST = "www.inpi.net"
FTP_USER = "rneinpiro"
FTP_PASSWORD = "vv8_rQ5f4M_2-E"

def download_file(ftp, remote_filename, local_filename):
    """Télécharger un fichier depuis le FTP"""
    print(f"📥 Téléchargement de {remote_filename}...")
    
    with open(local_filename, 'wb') as local_file:
        ftp.retrbinary(f'RETR {remote_filename}', local_file.write)
    
    size = os.path.getsize(local_filename)
    print(f"✅ Téléchargé: {local_filename} ({size:,} octets)")

def download_readme():
    """Télécharger et afficher le fichier readme.txt"""
    print("="*80)
    print("📖 TÉLÉCHARGEMENT ET LECTURE DU README")
    print("="*80)
    print()
    
    try:
        ftp = FTP(timeout=30)
        ftp.connect(FTP_HOST, 21)
        ftp.login(FTP_USER, FTP_PASSWORD)
        
        # Télécharger le readme
        local_readme = "/workspaces/TestsMCP/rne_readme.txt"
        download_file(ftp, "readme.txt", local_readme)
        
        # Afficher le contenu
        print("\n" + "="*80)
        print("📄 CONTENU DU README:")
        print("="*80)
        
        with open(local_readme, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            print(content)
        
        print("="*80)
        
        ftp.quit()
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        return False

def download_comptes_annuels_sample():
    """Télécharger un échantillon du fichier des comptes annuels (premiers Mo)"""
    print("\n" + "="*80)
    print("📥 TÉLÉCHARGEMENT D'UN ÉCHANTILLON DES COMPTES ANNUELS")
    print("="*80)
    print()
    
    try:
        ftp = FTP(timeout=30)
        ftp.connect(FTP_HOST, 21)
        ftp.login(FTP_USER, FTP_PASSWORD)
        
        remote_file = "stock_RNE_comptes_annuels_20250926_1000_v2.zip"
        local_file = "/workspaces/TestsMCP/comptes_annuels_sample.zip"
        
        print(f"⚠️  Attention: Le fichier complet fait 3,6 GB")
        print(f"   Nous téléchargeons seulement les premiers 100 MB pour analyse...")
        
        # Télécharger seulement les premiers 100 MB pour test
        sample_size = 100 * 1024 * 1024  # 100 MB
        bytes_downloaded = 0
        
        with open(local_file, 'wb') as f:
            def callback(data):
                nonlocal bytes_downloaded
                if bytes_downloaded < sample_size:
                    to_write = min(len(data), sample_size - bytes_downloaded)
                    f.write(data[:to_write])
                    bytes_downloaded += to_write
                    if bytes_downloaded >= sample_size:
                        raise Exception("Sample size reached")
            
            try:
                ftp.retrbinary(f'RETR {remote_file}', callback)
            except Exception as e:
                if "Sample size reached" not in str(e):
                    raise
        
        size = os.path.getsize(local_file)
        print(f"✅ Échantillon téléchargé: {local_file} ({size:,} octets)")
        
        # Essayer de lister le contenu du ZIP
        import zipfile
        try:
            with zipfile.ZipFile(local_file, 'r') as zip_ref:
                print("\n📦 Contenu de l'archive (aperçu):")
                print("-" * 80)
                for info in zip_ref.filelist[:20]:  # Premiers 20 fichiers
                    print(f"   {info.filename} ({info.file_size:,} octets)")
                
                if len(zip_ref.filelist) > 20:
                    print(f"   ... et {len(zip_ref.filelist) - 20} autres fichiers")
                
                print("-" * 80)
        except zipfile.BadZipFile:
            print("⚠️  L'échantillon est trop petit pour lire la structure du ZIP")
            print("   Il faudra télécharger plus de données pour analyser le contenu")
        
        ftp.quit()
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        return False

if __name__ == "__main__":
    # Télécharger et lire le README
    download_readme()
    
    # Télécharger un échantillon
    download_comptes_annuels_sample()
