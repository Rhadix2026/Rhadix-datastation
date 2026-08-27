"""Stap 1b — Datastation accepteert het centrale SureSync ID-token (RS256)."""
from jose import jwt as _jwt
import app.auth.security as security
from app.auth.dependencies import _ROLE_MAP
from app.models.auth_models import UserRole
from tests._testkeys import PRIV, PUB


def _central(claims):
    return _jwt.encode({**claims, "iss": "suresync-id"}, PRIV, algorithm="RS256")


def test_centraal_token_verifieren(monkeypatch):
    monkeypatch.setattr(security, "CENTRAL_PUBLIC_KEY", PUB)
    claims = security.decode_central_token(_central({"sub": "u1", "email": "a@b.nl", "role": "ORG_ADMIN"}))
    assert claims["email"] == "a@b.nl"


def test_verkeerde_issuer_geweigerd(monkeypatch):
    monkeypatch.setattr(security, "CENTRAL_PUBLIC_KEY", PUB)
    import pytest
    from jose import JWTError
    bad = _jwt.encode({"sub": "u1", "iss": "x"}, PRIV, algorithm="RS256")
    with pytest.raises(JWTError):
        security.decode_central_token(bad)


def test_rol_mapping():
    assert _ROLE_MAP["RHADIX_ADMIN"] == UserRole.PLATFORM_ADMIN
    assert _ROLE_MAP["ORG_USER"] == UserRole.ORG_USER
