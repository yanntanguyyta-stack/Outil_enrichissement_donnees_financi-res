"""
Authentication module — Google OAuth2 + Google Groups authorization.

Flow:
  1. User clicks "Se connecter avec Google" → redirected to Google consent screen.
  2. Google redirects back with ?code=... in the URL.
  3. We exchange the code for tokens, fetch user info.
  4. We check the user email against:
       a. ALLOWED_EMAILS env var (comma-separated direct whitelist), OR
       b. ALLOWED_GOOGLE_GROUPS env var (requires GOOGLE_SERVICE_ACCOUNT_JSON).
  5. If authorized, store user in st.session_state["auth_user"].

Configuration (via .env or Streamlit secrets):
  GOOGLE_CLIENT_ID        — OAuth2 client ID
  GOOGLE_CLIENT_SECRET    — OAuth2 client secret
  OAUTH_REDIRECT_URI      — e.g. https://yourapp.streamlit.app
  ALLOWED_EMAILS          — "alice@corp.com,bob@corp.com" (optional)
  ALLOWED_GOOGLE_GROUPS   — "group1@corp.com,group2@corp.com" (optional)
  GOOGLE_SERVICE_ACCOUNT_JSON — path to service-account JSON or inline JSON (optional)
  AUTH_SECRET_KEY         — secret for signing JWT session tokens
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

def _cfg(key: str, default: str = "") -> str:
    """Read from Streamlit secrets first, then from environment variables."""
    try:
        # Streamlit secrets are available only inside a running Streamlit context.
        return st.secrets.get(key, os.getenv(key, default))
    except Exception:
        return os.getenv(key, default)


GOOGLE_CLIENT_ID: str = _cfg("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET: str = _cfg("GOOGLE_CLIENT_SECRET")
OAUTH_REDIRECT_URI: str = _cfg("OAUTH_REDIRECT_URI", "http://localhost:8501")
AUTH_SECRET_KEY: str = _cfg("AUTH_SECRET_KEY", "REMPLACEZ-PAR-UNE-CHAINE-ALEATOIRE-DE-32-CARACTERES-MINIMUM")

ALLOWED_EMAILS: List[str] = [
    e.strip().lower()
    for e in _cfg("ALLOWED_EMAILS").split(",")
    if e.strip()
]
ALLOWED_GOOGLE_GROUPS: List[str] = [
    g.strip().lower()
    for g in _cfg("ALLOWED_GOOGLE_GROUPS").split(",")
    if g.strip()
]
GOOGLE_SERVICE_ACCOUNT_JSON: str = _cfg("GOOGLE_SERVICE_ACCOUNT_JSON")

# Google OAuth2 endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

# Session keys
_SESSION_USER_KEY = "auth_user"
_SESSION_TOKEN_KEY = "auth_token"
SESSION_DURATION_SECONDS = 8 * 3600  # 8 hours — long enough for a full workday

# ---------------------------------------------------------------------------
# HMAC-based session token (no external JWT library required)
# ---------------------------------------------------------------------------


def _sign_payload(payload: Dict[str, Any]) -> str:
    """Create a compact signed token: base64(payload_json).signature."""
    import base64

    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    sig = hmac.new(
        AUTH_SECRET_KEY.encode(), body.encode(), hashlib.sha256
    ).hexdigest()
    return f"{body}.{sig}"


def _verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a signed token. Returns payload or None."""
    import base64

    try:
        parts = token.rsplit(".", 1)
        if len(parts) != 2:
            return None
        body, sig = parts
        expected_sig = hmac.new(
            AUTH_SECRET_KEY.encode(), body.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        payload = json.loads(base64.urlsafe_b64decode(body + "==").decode())
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Google OAuth2 helpers
# ---------------------------------------------------------------------------


def get_oauth_login_url() -> str:
    """Build the Google OAuth2 authorization URL."""
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def exchange_code_for_user_info(code: str) -> Optional[Dict[str, Any]]:
    """Exchange OAuth2 authorization code for user info dict."""
    try:
        token_resp = requests.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": OAUTH_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        token_resp.raise_for_status()
        tokens = token_resp.json()

        user_resp = requests.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            timeout=10,
        )
        user_resp.raise_for_status()
        return user_resp.json()
    except requests.RequestException as exc:
        logger.error("OAuth2 token exchange failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Authorization — email whitelist + Google Groups
# ---------------------------------------------------------------------------


def is_authorized(email: str) -> bool:
    """Return True if the email is in the allowed whitelist or a configured group."""
    email_lower = email.lower()

    # If no restrictions configured → allow everyone who successfully authenticated
    if not ALLOWED_EMAILS and not ALLOWED_GOOGLE_GROUPS:
        return True

    # Direct email whitelist check
    if ALLOWED_EMAILS and email_lower in ALLOWED_EMAILS:
        return True

    # Google Groups membership check
    if ALLOWED_GOOGLE_GROUPS:
        for group in ALLOWED_GOOGLE_GROUPS:
            if _is_member_of_google_group(email_lower, group):
                return True

    return False


def _is_member_of_google_group(email: str, group_email: str) -> bool:
    """
    Check if *email* is a member of *group_email* using the Google Directory API.

    Requires GOOGLE_SERVICE_ACCOUNT_JSON with domain-wide delegation enabled
    and the scope https://www.googleapis.com/auth/admin.directory.group.member.readonly.
    """
    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        logger.warning(
            "GOOGLE_SERVICE_ACCOUNT_JSON not set; cannot verify group membership for %s",
            group_email,
        )
        return False

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build  # type: ignore

        # GOOGLE_SERVICE_ACCOUNT_JSON may be a file path or inline JSON string
        if GOOGLE_SERVICE_ACCOUNT_JSON.strip().startswith("{"):
            service_account_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        else:
            with open(GOOGLE_SERVICE_ACCOUNT_JSON) as fh:
                service_account_info = json.load(fh)

        scopes = ["https://www.googleapis.com/auth/admin.directory.group.member.readonly"]
        # Domain-wide delegation requires impersonating an admin account
        admin_email = _cfg("GOOGLE_ADMIN_EMAIL")
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info, scopes=scopes
        )
        if admin_email:
            credentials = credentials.with_subject(admin_email)

        service = build("admin", "directory_v1", credentials=credentials, cache_discovery=False)
        result = (
            service.members()
            .hasMember(groupKey=group_email, memberKey=email)
            .execute()
        )
        return bool(result.get("isMember", False))
    except Exception as exc:
        logger.warning("Google Groups check failed for %s in %s: %s", email, group_email, exc)
        return False


# ---------------------------------------------------------------------------
# Streamlit session management
# ---------------------------------------------------------------------------


def get_current_user() -> Optional[Dict[str, Any]]:
    """Return the authenticated user dict, or None if not logged in."""
    token = st.session_state.get(_SESSION_TOKEN_KEY)
    if not token:
        return None
    payload = _verify_token(token)
    if not payload:
        st.session_state.pop(_SESSION_TOKEN_KEY, None)
        st.session_state.pop(_SESSION_USER_KEY, None)
        return None
    return payload.get("user")


def _store_user(user: Dict[str, Any]) -> None:
    """Sign and store the user in session state."""
    payload = {"user": user, "exp": time.time() + SESSION_DURATION_SECONDS}
    token = _sign_payload(payload)
    st.session_state[_SESSION_TOKEN_KEY] = token
    st.session_state[_SESSION_USER_KEY] = user


def logout() -> None:
    """Clear authentication state."""
    st.session_state.pop(_SESSION_TOKEN_KEY, None)
    st.session_state.pop(_SESSION_USER_KEY, None)
    st.rerun()


# ---------------------------------------------------------------------------
# OAuth callback handler (call once per page load)
# ---------------------------------------------------------------------------


def handle_oauth_callback() -> None:
    """Process the OAuth2 callback (?code=...) if present in the URL."""
    # st.query_params is the new API (Streamlit ≥ 1.30); fall back gracefully
    try:
        params = st.query_params
        code = params.get("code")
    except Exception:
        code = None

    if not code:
        return

    # Clear the code from the URL to avoid re-processing on reload
    try:
        st.query_params.clear()
    except Exception:
        pass

    with st.spinner("Vérification de votre compte Google…"):
        user_info = exchange_code_for_user_info(code)

    if not user_info:
        st.error("❌ Échec de l'authentification Google. Veuillez réessayer.")
        return

    email = user_info.get("email", "")
    if not email:
        st.error("❌ Impossible de récupérer votre adresse e-mail depuis Google.")
        return

    if not is_authorized(email):
        st.error(
            f"🚫 Accès refusé. Le compte **{email}** n'est pas autorisé à accéder à cette application. "
            "Contactez votre administrateur pour être ajouté au groupe autorisé."
        )
        return

    user = {
        "email": email,
        "name": user_info.get("name", email),
        "picture": user_info.get("picture", ""),
        "given_name": user_info.get("given_name", ""),
    }
    _store_user(user)
    st.rerun()


# ---------------------------------------------------------------------------
# Public authentication gate
# ---------------------------------------------------------------------------

_AUTH_ENABLED = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)


def require_auth() -> Optional[Dict[str, Any]]:
    """
    Enforce authentication. Returns the current user dict if authenticated,
    otherwise renders the login page and returns None.

    Usage in app.py::

        from auth import require_auth
        user = require_auth()
        if user is None:
            st.stop()
        # rest of the app...
    """
    if not _AUTH_ENABLED:
        # Auth not configured → open access (dev mode)
        return {"email": "dev@local", "name": "Développeur (mode local)", "picture": ""}

    handle_oauth_callback()

    user = get_current_user()
    if user:
        return user

    # Render login page
    _render_login_page()
    return None


def _render_login_page() -> None:
    """Render a clean login / landing page."""
    st.markdown(
        """
        <style>
        .login-container {
            max-width: 480px;
            margin: 6rem auto;
            padding: 2.5rem;
            background: #ffffff;
            border-radius: 16px;
            box-shadow: 0 4px 32px rgba(0,0,0,0.10);
            text-align: center;
        }
        .login-logo { font-size: 3rem; margin-bottom: 0.5rem; }
        .login-title { font-size: 1.5rem; font-weight: 700; color: #1a1a2e; margin-bottom: 0.3rem; }
        .login-subtitle { font-size: 0.95rem; color: #666; margin-bottom: 2rem; }
        .google-btn {
            display: inline-block;
            background: #4285F4;
            color: white !important;
            padding: 0.75rem 2rem;
            border-radius: 8px;
            font-weight: 600;
            font-size: 1rem;
            text-decoration: none !important;
            transition: background 0.2s;
            cursor: pointer;
        }
        .google-btn:hover { background: #3367d6; }
        .login-note { font-size: 0.8rem; color: #999; margin-top: 1.5rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    login_url = get_oauth_login_url()

    st.markdown(
        f"""
        <div class="login-container">
            <div class="login-logo">🏢</div>
            <div class="login-title">Enrichissement Données Entreprises</div>
            <div class="login-subtitle">
                Accès réservé aux membres des équipes autorisées.<br>
                Connectez-vous avec votre compte Google professionnel.
            </div>
            <a class="google-btn" href="{login_url}" target="_self">
                🔐 &nbsp; Se connecter avec Google
            </a>
            <div class="login-note">
                Vos données ne sont pas stockées. La session expire après 8 heures.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
