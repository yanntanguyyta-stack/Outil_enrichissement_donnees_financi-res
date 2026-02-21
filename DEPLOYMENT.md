# Guide de déploiement

Ce document décrit comment déployer l'application **Enrichissement Données Entreprises** en production, avec authentification Google OAuth2.

---

## Architecture d'authentification

```
Utilisateur
    │
    ▼
Page de connexion (auth.py)
    │  "Se connecter avec Google"
    ▼
Google OAuth2 ──► Consent screen
    │  code=...
    ▼
auth.py — échange le code, récupère l'email
    │
    ├── Vérifie ALLOWED_EMAILS (whitelist directe)
    └── Vérifie ALLOWED_GOOGLE_GROUPS (Directory API)
            │
            ▼
        Accès accordé → session HMAC token (8h)
```

---

## Option 1 — Streamlit Community Cloud (recommandé)

**Avantages** : gratuit, WebSocket natif, déploiement en 2 clics.

### Étapes

1. Poussez ce dépôt sur GitHub.
2. Rendez-vous sur [share.streamlit.io](https://share.streamlit.io) et liez votre dépôt.
3. Dans **Settings → Secrets**, copiez le contenu de `.streamlit/secrets.toml.example` et remplissez vos valeurs.
4. Dans la [console Google Cloud](https://console.cloud.google.com/apis/credentials) :
   - Créez un projet → activez l'API « Google Identity »
   - Créez des identifiants OAuth 2.0 (Application Web)
   - Ajoutez l'URI de redirection : `https://<votre-app>.streamlit.app`
5. Déployez. 🎉

---

## Option 2 — Railway / Render

Ces plateformes supportent les serveurs Python persistants (WebSocket inclus).

### Étapes communes

1. Créez un compte sur [railway.app](https://railway.app) ou [render.com](https://render.com).
2. Liez votre dépôt GitHub.
3. Configurez les variables d'environnement (voir `.env.example`).
4. La commande de démarrage est lue depuis le `Procfile` :
   ```
   web: streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
   ```
5. Mettez à jour `OAUTH_REDIRECT_URI` avec l'URL publique fournie par la plateforme.

---

## Option 3 — Docker (auto-hébergé ou Cloud Run)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
```

```bash
docker build -t enrichissement-app .
docker run -p 8501:8501 \
  -e GOOGLE_CLIENT_ID=... \
  -e GOOGLE_CLIENT_SECRET=... \
  -e OAUTH_REDIRECT_URI=https://votre-domaine.com \
  -e AUTH_SECRET_KEY=... \
  -e ALLOWED_GOOGLE_GROUPS=equipe@corp.com \
  enrichissement-app
```

---

## Option 4 — Vercel (expérimental)

> ⚠️ **Note** : Streamlit utilise WebSockets, que Vercel ne supporte pas nativement dans son runtime serverless. Le fichier `vercel.json` fourni est un point de départ, mais un déploiement complet nécessitera des adaptations (ex. : utiliser Vercel Edge Functions ou un serveur proxy).
>
> **Recommandation** : utilisez l'Option 1 (Streamlit Cloud) ou l'Option 2 (Railway/Render) pour un déploiement sans friction.

---

## Configuration de l'authentification

### 1. Créer les identifiants OAuth2 Google

1. Allez sur [console.cloud.google.com](https://console.cloud.google.com).
2. Créez un projet ou sélectionnez un projet existant.
3. Menu **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client IDs**.
4. Type : **Web application**.
5. Ajoutez les URIs de redirection autorisées :
   - Développement : `http://localhost:8501`
   - Production : `https://<votre-app>.streamlit.app` (ou votre domaine)
6. Notez le **Client ID** et le **Client Secret**.

### 2. Configurer les Google Groups (optionnel)

Pour autoriser l'accès aux membres d'un Google Group :

1. Dans la console Google, activez l'API **Admin SDK Directory API**.
2. Créez un **Compte de service** (Service Account) :
   - Menu **IAM & Admin → Service Accounts → Create**.
   - Téléchargez le fichier JSON de clé.
3. Activez la **délégation à l'échelle du domaine** (Domain-Wide Delegation) :
   - Dans les détails du compte de service, cliquez sur **Edit → Show advanced settings**.
   - Activez la délégation, notez le Client ID numérique.
4. Dans [admin.google.com](https://admin.google.com) → **Security → API Controls → Domain-wide delegation** :
   - Ajoutez le Client ID numérique du compte de service.
   - Scope : `https://www.googleapis.com/auth/admin.directory.group.member.readonly`
5. Renseignez dans les secrets :
   - `GOOGLE_SERVICE_ACCOUNT_JSON` : contenu du fichier JSON (ou chemin)
   - `GOOGLE_ADMIN_EMAIL` : email d'un admin Google Workspace
   - `ALLOWED_GOOGLE_GROUPS` : `mongroupe@monentreprise.com`

### 3. Variables d'environnement requises

| Variable | Description | Exemple |
|----------|-------------|---------|
| `GOOGLE_CLIENT_ID` | OAuth2 Client ID | `123456789.apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | OAuth2 Client Secret | `GOCSPX-...` |
| `OAUTH_REDIRECT_URI` | URL de redirection après login | `https://app.streamlit.app` |
| `AUTH_SECRET_KEY` | Clé secrète pour les tokens de session | `<chaîne longue aléatoire>` |
| `ALLOWED_EMAILS` | Liste blanche d'emails (optionnel) | `alice@corp.com,bob@corp.com` |
| `ALLOWED_GOOGLE_GROUPS` | Groupes Google autorisés (optionnel) | `equipe@corp.com` |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | JSON du compte de service (si groupes) | `{"type":"service_account",...}` |
| `GOOGLE_ADMIN_EMAIL` | Admin pour l'impersonnification | `admin@corp.com` |

---

## Base de données RNE

La base SQLite `rne_finances.db` doit être présente dans le répertoire de l'application.

- **Streamlit Cloud** : uploadez-la via le dépôt Git (si < 100 MB) ou depuis un service de stockage externe.
- **Railway/Render** : montez un volume persistant ou utilisez la version compressée `.db.xz` fournie.
- **Mise à jour** : exécutez `python update_rne_db.py` trimestriellement.

---

## Checklist avant déploiement

- [ ] `GOOGLE_CLIENT_ID` et `GOOGLE_CLIENT_SECRET` configurés
- [ ] `OAUTH_REDIRECT_URI` correspond à l'URL de déploiement
- [ ] `AUTH_SECRET_KEY` est une chaîne aléatoire forte (≥ 32 caractères)
- [ ] `ALLOWED_EMAILS` ou `ALLOWED_GOOGLE_GROUPS` configurés (sinon accès ouvert à tous)
- [ ] `rne_finances.db` disponible (ou `.db.xz` pour décompression automatique)
- [ ] `.env` ou secrets de plateforme remplis (jamais commités en Git)
