"""Tests for the auth module."""
import json
import os
import time
from unittest.mock import MagicMock, patch

import pytest


# Patch streamlit before importing auth
import sys
mock_st = MagicMock()
mock_st.secrets = {}
mock_st.session_state = {}
sys.modules['streamlit'] = mock_st


import auth  # noqa: E402 — must come after mock


class TestTokenSigning:
    """Test HMAC-based session token signing and verification."""

    def test_sign_and_verify_valid_token(self):
        payload = {"user": {"email": "test@test.com"}, "exp": time.time() + 3600}
        token = auth._sign_payload(payload)
        result = auth._verify_token(token)
        assert result is not None
        assert result["user"]["email"] == "test@test.com"

    def test_expired_token_is_rejected(self):
        payload = {"user": {"email": "test@test.com"}, "exp": time.time() - 1}
        token = auth._sign_payload(payload)
        result = auth._verify_token(token)
        assert result is None

    def test_tampered_token_is_rejected(self):
        payload = {"user": {"email": "test@test.com"}, "exp": time.time() + 3600}
        token = auth._sign_payload(payload)
        # Tamper with the token by changing a character
        tampered = token[:-5] + "XXXXX"
        result = auth._verify_token(tampered)
        assert result is None

    def test_malformed_token_is_rejected(self):
        assert auth._verify_token("notavalidtoken") is None
        assert auth._verify_token("") is None


class TestAuthorization:
    """Test email/group authorization logic."""

    def test_no_restrictions_allows_everyone(self):
        with patch.object(auth, 'ALLOWED_EMAILS', []):
            with patch.object(auth, 'ALLOWED_GOOGLE_GROUPS', []):
                assert auth.is_authorized("anyone@example.com") is True

    def test_email_whitelist_allows_listed_email(self):
        with patch.object(auth, 'ALLOWED_EMAILS', ["alice@corp.com"]):
            with patch.object(auth, 'ALLOWED_GOOGLE_GROUPS', []):
                assert auth.is_authorized("alice@corp.com") is True

    def test_email_whitelist_blocks_unlisted_email(self):
        with patch.object(auth, 'ALLOWED_EMAILS', ["alice@corp.com"]):
            with patch.object(auth, 'ALLOWED_GOOGLE_GROUPS', []):
                assert auth.is_authorized("eve@corp.com") is False

    def test_email_check_is_case_insensitive(self):
        with patch.object(auth, 'ALLOWED_EMAILS', ["alice@corp.com"]):
            with patch.object(auth, 'ALLOWED_GOOGLE_GROUPS', []):
                assert auth.is_authorized("ALICE@CORP.COM") is True

    def test_group_membership_grants_access(self):
        with patch.object(auth, 'ALLOWED_EMAILS', []):
            with patch.object(auth, 'ALLOWED_GOOGLE_GROUPS', ["team@corp.com"]):
                with patch.object(auth, '_is_member_of_google_group', return_value=True):
                    assert auth.is_authorized("member@corp.com") is True

    def test_group_non_membership_denies_access(self):
        with patch.object(auth, 'ALLOWED_EMAILS', []):
            with patch.object(auth, 'ALLOWED_GOOGLE_GROUPS', ["team@corp.com"]):
                with patch.object(auth, '_is_member_of_google_group', return_value=False):
                    assert auth.is_authorized("outsider@corp.com") is False


class TestGoogleGroupCheckWithoutServiceAccount:
    """Test that group check fails gracefully when no service account is configured."""

    def test_returns_false_without_service_account(self):
        with patch.object(auth, 'GOOGLE_SERVICE_ACCOUNT_JSON', ''):
            result = auth._is_member_of_google_group("user@corp.com", "group@corp.com")
            assert result is False


class TestOAuthLoginUrl:
    """Test that the login URL is correctly constructed."""

    def test_login_url_contains_client_id(self):
        with patch.object(auth, 'GOOGLE_CLIENT_ID', 'my-client-id'):
            url = auth.get_oauth_login_url()
            assert 'my-client-id' in url
            # Verify the URL starts with the expected Google auth endpoint
            assert url.startswith('https://accounts.google.com/')
            assert 'openid' in url


class TestSessionManagement:
    """Test session state management."""

    def test_store_and_retrieve_user(self):
        user = {"email": "user@test.com", "name": "Test User"}
        mock_st.session_state = {}
        auth._store_user(user)
        retrieved = auth.get_current_user()
        assert retrieved is not None
        assert retrieved["email"] == "user@test.com"

    def test_get_current_user_returns_none_without_session(self):
        mock_st.session_state = {}
        result = auth.get_current_user()
        assert result is None
