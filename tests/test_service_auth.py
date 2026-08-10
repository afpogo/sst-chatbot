from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.service_auth import ClientCredentialTokenProvider
from app.service_auth import JwksServiceTokenVerifier
from app.service_auth import ServiceCredentialError


def test_jwks_verifier_enforces_audience_scope_and_caller() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    public_jwk.update({"kid": "test-key", "alg": "RS256", "use": "sig"})

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            body = json.dumps({"keys": [public_jwk]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    verifier = JwksServiceTokenVerifier(
        jwks_url=f"http://127.0.0.1:{server.server_port}/jwks",
        issuer="sst-auth",
        audience="sst-chatbot",
        scope="chat:process",
        caller="sst-bend",
    )

    def token(**overrides):
        claims = {
            "iss": "sst-auth",
            "aud": "sst-chatbot",
            "sub": "sst-bend",
            "client_id": "sst-bend",
            "token_use": "service",
            "scope": "chat:process",
            "iat": int(time.time()),
            "exp": int(time.time()) + 60,
        }
        claims.update(overrides)
        return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "test-key"})

    try:
        assert verifier.verify(token())["sub"] == "sst-bend"
        with pytest.raises(ServiceCredentialError):
            verifier.verify(token(scope="session:introspect"))
        with pytest.raises(ServiceCredentialError):
            verifier.verify(token(aud="sst-api"))
        with pytest.raises(ServiceCredentialError):
            verifier.verify(token(sub="other", client_id="other"))
    finally:
        server.shutdown()


def test_client_credentials_are_cached_per_exact_grant() -> None:
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            length = int(self.headers["Content-Length"])
            body = json.loads(self.rfile.read(length))
            calls.append(body)
            response = json.dumps({"access_token": f"token-{len(calls)}", "expires_in": 60}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

        def log_message(self, *_args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    provider = ClientCredentialTokenProvider(
        token_url=f"http://127.0.0.1:{server.server_port}/token",
        client_id="sst-chatbot",
        client_secret="secret",
    )
    try:
        assert provider.get_token("sst-api", "agent-handoff:submit") == "token-1"
        assert provider.get_token("sst-api", "agent-handoff:submit") == "token-1"
        assert provider.get_token("other", "agent-handoff:submit") == "token-2"
    finally:
        server.shutdown()
    assert len(calls) == 2
