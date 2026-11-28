"""IAP の JWT の検証を、手元で作った鍵で確かめる。"""

import time

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from google.auth import crypt, jwt

from job_posting_agent.auth import IAP_HEADER, IAP_ISSUER, Authenticator, AuthError, IapVerifier
from job_posting_agent.config import Settings

pytestmark = pytest.mark.anyio

AUDIENCE = "/projects/123/locations/asia-northeast1/services/job-posting-agent"


class StaticVerifier(IapVerifier):
    def __init__(self, certs: dict[str, str]) -> None:
        super().__init__(AUDIENCE)
        self._static = certs

    async def _get_certs(self) -> dict[str, str]:
        return self._static


@pytest.fixture
def keypair() -> tuple[crypt.ES256Signer, dict[str, str]]:
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    public = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    signer = crypt.ES256Signer.from_string(pem, key_id="k1")
    return signer, {"k1": public.decode()}


def token(signer: crypt.ES256Signer, **overrides: object) -> str:
    now = int(time.time())
    claims = {
        "iss": IAP_ISSUER,
        "aud": AUDIENCE,
        "email": "Alice@Example.com",
        "sub": "accounts.google.com:1",
        "iat": now,
        "exp": now + 300,
        **overrides,
    }
    return jwt.encode(signer, claims).decode()


async def test_valid_token_gives_lowercase_email(keypair) -> None:  # type: ignore[no-untyped-def]
    signer, certs = keypair
    auth = Authenticator(Settings(auth_mode="iap"), StaticVerifier(certs))
    assert await auth.user_id({IAP_HEADER: token(signer)}) == "alice@example.com"


@pytest.mark.parametrize(
    "overrides",
    [
        {"aud": "/projects/999/other"},
        {"iss": "https://evil.example"},
        {"email": None},
        {"exp": 1, "iat": 0},
    ],
)
async def test_invalid_tokens_are_rejected(keypair, overrides) -> None:  # type: ignore[no-untyped-def]
    signer, certs = keypair
    auth = Authenticator(Settings(auth_mode="iap"), StaticVerifier(certs))
    with pytest.raises(AuthError):
        await auth.user_id({IAP_HEADER: token(signer, **overrides)})


async def test_token_signed_by_other_key_is_rejected(keypair) -> None:  # type: ignore[no-untyped-def]
    _, certs = keypair
    other = ec.generate_private_key(ec.SECP256R1()).private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    forged = token(crypt.ES256Signer.from_string(other, key_id="k1"))
    auth = Authenticator(Settings(auth_mode="iap"), StaticVerifier(certs))
    with pytest.raises(AuthError):
        await auth.user_id({IAP_HEADER: forged})


async def test_missing_header_and_spoofed_email_header_are_rejected(keypair) -> None:  # type: ignore[no-untyped-def]
    _, certs = keypair
    auth = Authenticator(Settings(auth_mode="iap"), StaticVerifier(certs))
    with pytest.raises(AuthError):
        await auth.user_id({"x-goog-authenticated-user-email": "accounts.google.com:bob@x.com"})


def test_iap_mode_requires_audience() -> None:
    with pytest.raises(RuntimeError):
        Authenticator(Settings(auth_mode="iap", iap_audience=None))


async def test_local_mode_uses_local_user() -> None:
    auth = Authenticator(Settings(auth_mode="local", local_user="me@example.com"))
    assert await auth.user_id({}) == "me@example.com"
