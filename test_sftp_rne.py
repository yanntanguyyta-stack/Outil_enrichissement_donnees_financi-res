"""
Test de connexion SFTP au RNE (Registre National des Entreprises) - INPI
Pour explorer les données financières disponibles
"""

import paramiko
import os
import stat
from datetime import datetime

# Configuration SFTP RNE
SFTP_HOST = "www.inpi.net"
SFTP_USER = "rneinpiro"
SFTP_PASSWORD = "vv8_rQ5f4M_2-E"
SFTP_PORT = 22

def test_connection():
    """Test de connexion au serveur SFTP RNE"""
    print(f"🔗 Tentative de connexion au serveur SFTP RNE...")
    print(f"   Hôte: {SFTP_HOST}")
    print(f"   Utilisateur: {SFTP_USER}")
    print(f"   Port: {SFTP_PORT}\n")
    
    transport = None
    sftp = None
    
    try:
        # Créer un transport SSH
        transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
        transport.connect(username=SFTP_USER, password=SFTP_PASSWORD)
        
        # Ouvrir une session SFTP
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        print("✅ Connexion réussie au serveur SFTP RNE!\n")
        
        # Afficher le répertoire courant
        current_dir = sftp.getcwd() or "/"
        print(f"📁 Répertoire courant: {current_dir}\n")
        
        # Lister les fichiers et dossiers
        print("📂 Contenu du répertoire racine:")
        print("-" * 80)
        
        items = sftp.listdir()
        for item in items:
            try:
                # Obtenir les informations sur l'élément
                attrs = sftp.stat(item)
                size = attrs.st_size
                mtime = datetime.fromtimestamp(attrs.st_mtime)
                
                # Déterminer si c'est un fichier ou un dossier
                is_dir = stat.S_ISDIR(attrs.st_mode)
                
                if is_dir:
                    print(f"📁 {item:40} [DOSSIER] - Modifié: {mtime.strftime('%Y-%m-%d %H:%M')}")
                    
                    # Explorer le contenu des dossiers
                    try:
                        sub_items = sftp.listdir(item)
                        print(f"   └─ Contient {len(sub_items)} éléments")
                        
                        # Afficher quelques éléments du sous-dossier
                        if sub_items:
                            preview = ', '.join(sub_items[:3])
                            print(f"   └─ Exemples: {preview}")
                            if len(sub_items) > 3:
                                print(f"      ... et {len(sub_items) - 3} autres")
                        
                    except Exception as e:
                        print(f"   └─ Erreur d'accès: {str(e)}")
                else:
                    size_mb = size / (1024 * 1024)
                    print(f"📄 {item:40} {size_mb:>10.2f} MB - Modifié: {mtime.strftime('%Y-%m-%d %H:%M')}")
                    
            except Exception as e:
                print(f"❌ {item:40} [Erreur: {str(e)}]")
        
        print("-" * 80)
        print(f"\n✅ Exploration terminée. Total: {len(items)} éléments\n")
        
        return True, sftp, transport
        
    except Exception as e:
        print(f"❌ Erreur de connexion: {str(e)}")
        if sftp:
            sftp.close()
        if transport:
            transport.close()
        return False, None, None

def explore_directory(sftp, path="/"):
    """Explorer un répertoire spécifique de manière récursive"""
    print(f"\n📂 Exploration de: {path}")
    print("-" * 80)
    
    try:
        items = sftp.listdir(path)
        
        for item in items:
            try:
                item_path = f"{path}/{item}".replace("//", "/")
                attrs = sftp.stat(item_path)
                is_dir = stat.S_ISDIR(attrs.st_mode)
                
                if is_dir:
                    print(f"📁 {item}/")
                else:
                    size_mb = attrs.st_size / (1024 * 1024)
                    print(f"📄 {item} ({size_mb:.2f} MB)")
            except Exception as e:
                print(f"❌ {item}: {str(e)}")
        
        print("-" * 80)
        
    except Exception as e:
        print(f"❌ Erreur d'exploration: {str(e)}")

if __name__ == "__main__":
    print("="*80)
    print("🏛️  TEST DE CONNEXION SFTP - REGISTRE NATIONAL DES ENTREPRISES (RNE/INPI)")
    print("="*80)
    print()
    
    success, sftp_connection, transport = test_connection()
    
    if success and sftp_connection:
        print("\n💡 Connexion établie avec succès!")
        print("   Vous pouvez maintenant explorer les données disponibles.")
        print("   Les données du RNE incluent généralement:")
        print("   - Comptes annuels (bilans, comptes de résultat)")
        print("   - Données d'identification des entreprises")
        print("   - Actes et statuts")
        print("   - Données des dirigeants")
        
        # Nettoyage
        sftp_connection.close()
        if transport:
            transport.close()
    else:
        print("\n❌ Impossible de se connecter au serveur SFTP RNE")
        print("   Vérifiez vos identifiants et la connexion réseau")
