"""security.py — JWT + bcrypt + wachtwoordsterkte."""
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-insecure-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_SPECIAL = r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]"


def validate_password_strength(password: str) -> None:
    """Minimaal 12 tekens, hoofd-/kleine letter, cijfer en speciaal teken."""
    errors = []
    if len(password) < 12:           errors.append("minimaal 12 tekens")
    if not re.search(r"[A-Z]", password): errors.append("minimaal 1 hoofdletter")
    if not re.search(r"[a-z]", password): errors.append("minimaal 1 kleine letter")
    if not re.search(r"[0-9]", password): errors.append("minimaal 1 cijfer")
    if not re.search(_SPECIAL, password): errors.append("minimaal 1 speciaal teken")
    if errors:
        raise ValueError("Wachtwoord voldoet niet: " + ", ".join(errors) + ".")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


# ── Centrale identiteit (SureSync ID) — accepteer RS256-tokens via publieke sleutel ──
CENTRAL_PUBLIC_KEY = os.getenv("CENTRAL_JWT_PUBLIC_KEY")
CENTRAL_ISSUER     = os.getenv("CENTRAL_JWT_ISSUER", "suresync-id")


def token_alg(token: str) -> str:
    try:
        return jwt.get_unverified_header(token).get("alg", ALGORITHM)
    except Exception:
        return ALGORITHM


def decode_central_token(token: str) -> dict:
    if not CENTRAL_PUBLIC_KEY:
        raise JWTError("central public key not configured")
    claims = jwt.decode(token, CENTRAL_PUBLIC_KEY, algorithms=["RS256"], options={"verify_aud": False})
    if claims.get("iss") != CENTRAL_ISSUER:
        raise JWTError("issuer mismatch")
    return claims
