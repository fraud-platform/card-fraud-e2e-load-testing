"""
Authentication module supporting multiple AUTH_MODE options.

Supports:
- none: No authentication (anonymous access)
- auth0: Auth0 Client Credentials flow
- local: Locally signed tokens (dev-only)

This module also maintains backward compatibility with the original Auth0TokenGenerator.
"""

import os
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx
from jose import jwt

# =============================================================================
# Legacy Auth0TokenGenerator (Backward Compatibility)
# =============================================================================


class Auth0TokenGenerator:
    """Generates Auth0 JWT tokens for load testing."""

    def __init__(
        self,
        domain: str,
        audience: str,
        client_id: str,
        client_secret: str,
        issuer: str | None = None,
    ):
        self.domain = domain
        self.audience = audience
        self.client_id = client_id
        self.client_secret = client_secret
        self.issuer = issuer or f"https://{domain}/"

        self._token: str | None = None
        self._token_expires: float = 0

    def get_token(self, force_refresh: bool = False) -> str:
        """Get a valid JWT token."""
        if not force_refresh and self._token and time.time() < self._token_expires - 60:
            return self._token

        token_url = f"https://{self.domain}/oauth/token"

        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "audience": self.audience,
            "grant_type": "client_credentials",
        }

        with httpx.Client(timeout=10.0) as client:
            response = client.post(token_url, json=payload)
            response.raise_for_status()

            data = response.json()
            self._token = data["access_token"]
            self._token_expires = time.time() + data["expires_in"]

        return self._token

    def get_test_token(self, roles: list[str] | None = None) -> str:
        """Generate a test token locally (for testing without Auth0)."""
        now = int(time.time())

        payload = {
            "iss": self.issuer,
            "aud": self.audience,
            "sub": "load-test-user",
            "iat": now,
            "exp": now + 3600,
            "azp": self.client_id,
            "roles": roles or ["read", "write"],
        }

        return jwt.encode(
            payload,
            self.client_secret,
            algorithm="HS256",
        )


# Singleton for legacy API
_token_generator: Auth0TokenGenerator | None = None


def get_token(domain: str, audience: str, client_id: str, client_secret: str) -> str:
    """Get token using singleton generator (legacy API)."""
    global _token_generator

    if _token_generator is None:
        _token_generator = Auth0TokenGenerator(domain, audience, client_id, client_secret)

    return _token_generator.get_token()


# =============================================================================
# New AUTH_MODE Implementation
# =============================================================================


@dataclass
class AuthConfig:
    """Authentication configuration."""

    mode: str  # none, auth0, local
    auth0_domain: str | None = None
    auth0_audience: str | None = None
    auth0_client_id: str | None = None
    auth0_client_secret: str | None = None
    local_signing_key: str | None = None


class TokenCache:
    """Caches JWT tokens to avoid rate limiting."""

    def __init__(self):
        self._tokens: dict[str, tuple] = {}  # key: (token, expiry)

    def get(self, key: str) -> str | None:
        """Get cached token if not expired."""
        if key in self._tokens:
            token, expiry = self._tokens[key]
            if time.time() < expiry - 60:  # 1 min buffer
                return token
        return None

    def set(self, key: str, token: str, expires_in: int):
        """Cache a token with expiry."""
        expiry = time.time() + expires_in
        self._tokens[key] = (token, expiry)


# Global token cache (shared across all users)
token_cache = TokenCache()


def get_auth_config() -> AuthConfig:
    """Load auth configuration from environment."""
    return AuthConfig(
        mode=os.getenv("AUTH_MODE", "none"),
        auth0_domain=os.getenv("AUTH0_DOMAIN"),
        auth0_audience=os.getenv("AUTH0_AUDIENCE"),
        auth0_client_id=os.getenv("AUTH0_CLIENT_ID"),
        auth0_client_secret=os.getenv("AUTH0_CLIENT_SECRET"),
        local_signing_key=os.getenv("LOCAL_SIGNING_KEY"),
    )


def get_auth_headers(config: AuthConfig = None) -> dict[str, str]:
    """
    Get authentication headers based on AUTH_MODE.

    Returns dict with Authorization header if needed.
    """
    if config is None:
        config = get_auth_config()

    if config.mode == "none":
        return {}

    if config.mode == "auth0":
        token = _get_auth0_token(config)
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    if config.mode == "local":
        token = _get_local_token(config)
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    return {}


def _get_auth0_token(config: AuthConfig) -> str | None:
    """Get Auth0 token using Client Credentials flow."""
    cache_key = f"auth0:{config.auth0_client_id}:{config.auth0_audience}"

    # Check cache
    cached = token_cache.get(cache_key)
    if cached:
        return cached

    # Validate config
    if not all([config.auth0_domain, config.auth0_client_id, config.auth0_client_secret]):
        print("Warning: Missing Auth0 configuration")
        return None

    try:
        token_url = f"https://{config.auth0_domain}/oauth/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": config.auth0_client_id,
            "client_secret": config.auth0_client_secret,
            "audience": config.auth0_audience,
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(token_url, json=payload)
            response.raise_for_status()
            data = response.json()

        token = data.get("access_token")
        expires_in = data.get("expires_in", 3600)

        if token:
            token_cache.set(cache_key, token, expires_in)
            print(f"Auth0 token obtained, expires in {expires_in}s")
            return token

    except Exception as e:
        print(f"Error obtaining Auth0 token: {e}")

    return None


def _get_local_token(config: AuthConfig) -> str | None:
    """Generate a locally signed JWT token (dev-only)."""
    cache_key = "local:dev-token"

    # Check cache (local tokens are short-lived)
    cached = token_cache.get(cache_key)
    if cached:
        return cached

    try:
        # Create a simple payload
        now = datetime.now(UTC)
        payload = {
            "sub": f"load-test-{uuid.uuid4().hex[:8]}",
            "iss": "load-test-local",
            "aud": config.auth0_audience or "local-api",
            "iat": now,
            "exp": now + timedelta(hours=1),
            "scope": "read:transactions write:transactions evaluate:rules",
        }

        # Sign with local key (HS256 for simplicity)
        signing_key = config.local_signing_key or "dev-secret-key-do-not-use-in-production"
        token = jwt.encode(payload, signing_key, algorithm="HS256")

        token_cache.set(cache_key, token, 3600)
        return token

    except Exception as e:
        print(f"Error generating local token: {e}")
        return None


def validate_auth_setup() -> bool:
    """
    Validate that authentication is properly configured.

    Returns True if auth is ready, False otherwise.
    """
    config = get_auth_config()

    if config.mode == "none":
        print("Auth mode: none (anonymous)")
        return True

    if config.mode == "auth0":
        missing = []
        if not config.auth0_domain:
            missing.append("AUTH0_DOMAIN")
        if not config.auth0_client_id:
            missing.append("AUTH0_CLIENT_ID")
        if not config.auth0_client_secret:
            missing.append("AUTH0_CLIENT_SECRET")

        if missing:
            print(f"Auth0 configuration incomplete. Missing: {', '.join(missing)}")
            return False

        # Test token acquisition
        token = _get_auth0_token(config)
        if token:
            print("Auth0 configuration validated successfully")
            return True
        return False

    if config.mode == "local":
        print("Auth mode: local (development only)")
        return True

    print(f"Unknown auth mode: {config.mode}")
    return False
