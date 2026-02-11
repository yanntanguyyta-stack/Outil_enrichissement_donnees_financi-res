"""
Test de connexion FTP/FTPS au RNE (Registre National des Entreprises) - INPI
Pour explorer les données financières disponibles
"""

from ftplib import FTP, FTP_TLS
from datetime import datetime
import ssl

# Configuration FTP RNE
FTP_HOST = "www.inpi.net"
FTP_USER = "rneinpiro"
FTP_PASSWORD = "vv8_rQ5f4M_2-E"

def test_ftp_connection():
    """Test de connexion FTP standard"""
    print(f"🔗 Tentative de connexion FTP standard...")
    print(f"   Hôte: {FTP_HOST}")
    print(f"   Utilisateur: {FTP_USER}\n")
    
    try:
        # Connexion FTP standard
        ftp = FTP(timeout=10)
        ftp.connect(FTP_HOST, 21)
        print(f"✅ Connexion TCP établie au serveur FTP\n")
        
        # Authentification
        response = ftp.login(FTP_USER, FTP_PASSWORD)
        print(f"✅ Authentification réussie: {response}\n")
        
        # Message de bienvenue
        print(f"📢 Message du serveur: {ftp.getwelcome()}\n")
        
        # Répertoire courant
        current_dir = ftp.pwd()
        print(f"📁 Répertoire courant: {current_dir}\n")
        
        # Lister les fichiers
        print("📂 Contenu du répertoire racine:")
        print("-" * 80)
        
        files_list = []
        ftp.retrlines('LIST', files_list.append)
        
        for item in files_list:
            print(f"   {item}")
        
        print("-" * 80)
        print(f"\n✅ Total: {len(files_list)} éléments trouvés\n")
        
        # Essayer d'obtenir la liste des répertoires de manière structurée
        try:
            print("\n📂 Liste des répertoires et fichiers (format détaillé):")
            print("-" * 80)
            items = ftp.nlst()
            for item in items:
                try:
                    # Essayer de changer de répertoire pour voir si c'est un dossier
                    current = ftp.pwd()
                    try:
                        ftp.cwd(item)
                        print(f"📁 {item}/ [DOSSIER]")
                        
                        # Lister le contenu
                        sub_items = ftp.nlst()
                        print(f"   └─ Contient {len(sub_items)} éléments")
                        if sub_items:
                            preview = ', '.join(sub_items[:5])
                            print(f"   └─ Exemples: {preview}")
                            if len(sub_items) > 5:
                                print(f"      ... et {len(sub_items) - 5} autres")
                        
                        ftp.cwd(current)
                    except:
                        print(f"📄 {item} [FICHIER]")
                except Exception as e:
                    print(f"❓ {item} [Type inconnu: {str(e)}]")
            
            print("-" * 80)
        except Exception as e:
            print(f"\n⚠️  Impossible d'obtenir la liste détaillée: {str(e)}")
        
        ftp.quit()
        return True
        
    except Exception as e:
        print(f"❌ Erreur de connexion FTP: {str(e)}")
        return False

def test_ftps_connection():
    """Test de connexion FTPS (FTP over TLS)"""
    print(f"\n🔗 Tentative de connexion FTPS (FTP sécurisé)...")
    print(f"   Hôte: {FTP_HOST}")
    print(f"   Utilisateur: {FTP_USER}\n")
    
    try:
        # Connexion FTPS
        ftps = FTP_TLS(timeout=10)
        ftps.connect(FTP_HOST, 21)
        print(f"✅ Connexion TCP établie au serveur FTPS\n")
        
        # Authentification
        response = ftps.login(FTP_USER, FTP_PASSWORD)
        print(f"✅ Authentification réussie: {response}\n")
        
        # Activer la protection des données
        ftps.prot_p()
        print(f"✅ Canal de données sécurisé activé\n")
        
        # Message de bienvenue
        print(f"📢 Message du serveur: {ftps.getwelcome()}\n")
        
        # Répertoire courant
        current_dir = ftps.pwd()
        print(f"📁 Répertoire courant: {current_dir}\n")
        
        # Lister les fichiers
        print("📂 Contenu du répertoire racine:")
        print("-" * 80)
        
        files_list = []
        ftps.retrlines('LIST', files_list.append)
        
        for item in files_list:
            print(f"   {item}")
        
        print("-" * 80)
        print(f"\n✅ Total: {len(files_list)} éléments trouvés\n")
        
        ftps.quit()
        return True
        
    except Exception as e:
        print(f"❌ Erreur de connexion FTPS: {str(e)}")
        return False

if __name__ == "__main__":
    print("="*80)
    print("🏛️  TEST DE CONNEXION FTP - REGISTRE NATIONAL DES ENTREPRISES (RNE/INPI)")
    print("="*80)
    print()
    
    # Essayer d'abord FTP standard
    print("📝 Note: L'URL fournie (ftp://...) suggère un serveur FTP classique\n")
    
    success_ftp = test_ftp_connection()
    
    # Si FTP ne fonctionne pas, essayer FTPS
    if not success_ftp:
        print("\n" + "="*80)
        success_ftps = test_ftps_connection()
        
        if not success_ftps:
            print("\n❌ Impossible de se connecter avec FTP ou FTPS")
            print("   Vérifiez vos identifiants et la connexion réseau")
    else:
        print("\n💡 Connexion FTP établie avec succès!")
        print("   Vous pouvez maintenant explorer les données disponibles.")
        print("   Les données du RNE incluent généralement:")
        print("   - Comptes annuels (bilans, comptes de résultat)")
        print("   - Données d'identification des entreprises")
        print("   - Actes et statuts")
        print("   - Données des dirigeants")
