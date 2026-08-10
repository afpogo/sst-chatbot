from __future__ import annotations

import base64
import json
import os
import threading
import time
import urllib.request
from dataclasses import dataclass
from typing import Any

import jwt


class ServiceCredentialError(RuntimeError):
    """A service credential could not be obtained or validated."""


def _scopes(claims: dict[str, Any]) -> set[str]:
    value = claims.get("scope", "")
    if isinstance(value, list):
        return {str(item) for item in value}
    return set(str(value).split())


class JwksServiceTokenVerifier:
    def __init__(self, *, jwks_url: str, issuer: str, audience: str, scope: str, caller: str) -> None:
        self._keys = jwt.PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=300)
        self.issuer = issuer
        self.audience = audience
        self.scope = scope
        self.caller = caller

    @classmethod
    def from_env(cls) -> "JwksServiceTokenVerifier":
        return cls(
            jwks_url=os.getenv("AUTH_JWKS_URL", "http://fuentes:4000/.well-known/jwks.json"),
            issuer=os.getenv("AUTH_JWT_ISSUER", "sst-auth"),
            audience=os.getenv("CHAT_SERVICE_AUDIENCE", "sst-chatbot"),
            scope="chat:process",
            caller=os.getenv("M2M_SST_BEND_CLIENT_ID", "sst-bend"),
        )

    def verify(self, token: str) -> dict[str, Any]:
        try:
            key = self._keys.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                key.key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["exp", "iat", "iss", "aud", "sub", "token_use"]},
            )
        except jwt.PyJWTError as exc:
            raise ServiceCredentialError("invalid service token") from exc
        if claims.get("token_use") != "service":
            raise ServiceCredentialError("token_use must be service")
        if claims.get("sub") != self.caller or claims.get("client_id") != self.caller:
            raise ServiceCredentialError("service caller is not allowed")
        if self.scope not in _scopes(claims):
            raise ServiceCredentialError("required service scope is missing")
        return claims


@dataclass(frozen=True)
class _CachedToken:
    value: str
    expires_at: float


class ClientCredentialTokenProvider:
    def __init__(self, *, token_url: str, client_id: str, client_secret: str, timeout: float = 5.0) -> None:
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout
        self._cache: dict[tuple[str, str], _CachedToken] = {}
        self._lock = threading.Lock()

    @classmethod
    def chatbot_from_env(cls) -> "ClientCredentialTokenProvider":
        return cls(
            token_url=os.getenv("AUTH_SERVICE_TOKEN_URL", "http://fuentes:4000/api/auth/internal/oauth/token"),
            client_id=os.getenv("M2M_SST_CHATBOT_CLIENT_ID", "sst-chatbot"),
            client_secret=os.getenv("M2M_SST_CHATBOT_CLIENT_SECRET", ""),
        )

    def get_token(self, audience: str, scope: str) -> str:
        cache_key = (audience, scope)
        now = time.time()
        with self._lock:
            cached = self._cache.get(cache_key)
            if cached and cached.expires_at - 15 > now:
                return cached.value
            if not self.client_secret:
                raise ServiceCredentialError("service client secret is not configured")
            basic = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
            body = json.dumps({"grant_type": "client_credentials", "audience": audience, "scope": scope}).encode()
            request = urllib.request.Request(
                self.token_url,
                data=body,
                headers={"Authorization": f"Basic {basic}", "Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    result = json.load(response)
            except Exception as exc:
                raise ServiceCredentialError("service token request failed") from exc
            token = result.get("access_token")
            expires_in = int(result.get("expires_in", 300))
            if not isinstance(token, str) or not token:
                raise ServiceCredentialError("service token response is invalid")
            self._cache[cache_key] = _CachedToken(token, now + expires_in)
            return token
