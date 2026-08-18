"""dependencies.py — auth/authorisatie dependencies."""
from __future__ import annotations

import os
import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token, decode_central_token, token_alg, CENTRAL_PUBLIC_KEY
from app.database import get_db
from app.models.auth_models import User, UserRole, Tenant

_bearer = HTTPBearer(auto_error=False)


_ROLE_MAP = {
    "RHADIX_ADMIN":   UserRole.PLATFORM_ADMIN,
    "PLATFORM_ADMIN": UserRole.PLATFORM_ADMIN,
    "ORG_ADMIN":      UserRole.ORG_ADMIN,
    "ORG_USER":       UserRole.ORG_USER,
}


def _provision_from_claims(claims: dict, db: Session) -> User:
    """JIT-provisioning: maak/synchroniseer een lokale user uit de centrale claims."""
    import re as _re
    email = (claims.get("email") or "").lower().strip()
    if not email:
        raise ValueError("centraal token mist email")
    role  = _ROLE_MAP.get(claims.get("role"), UserRole.ORG_USER)
    name  = claims.get("name")
    tname = claims.get("tenant_name") or "SureSync"
    slug  = _re.sub(r"[^a-z0-9]+", "-", tname.lower()).strip("-") or "suresync"

    tenant = db.query(Tenant).filter(Tenant.slug == slug).first()
    if not tenant:
        tenant = Tenant(slug=slug, name=tname, is_active=True)
        db.add(tenant); db.flush()

    user = db.query(User).filter(User.email == email).first()
    changed = False
    if not user:
        user = User(email=email, full_name=name, role=role, tenant_id=tenant.id,
                    is_active=True, password_hash=None)
        db.add(user); changed = True
    else:
        if user.role != role:        user.role = role; changed = True
        if name and user.full_name != name: user.full_name = name; changed = True
    if changed:
        db.commit(); db.refresh(user)
    # Branding uit het centrale token als transient meegeven aan /auth/me (niet opgeslagen).
    user._branding = claims.get("branding")
    # Autorisatie-context uit het centrale token, transient (niet opgeslagen):
    # de apps-claim is de enige bron voor menselijke applicatietoegang.
    user._token_source = "central"
    user._apps = claims.get("apps")
    user._token_typ = claims.get("typ")
    user._token_scope = claims.get("scope")
    return user


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials if credentials else request.cookies.get(os.getenv("SSO_COOKIE_NAME", "rhadix_sso"))
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Niet geauthenticeerd",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        if CENTRAL_PUBLIC_KEY and token_alg(token) == "RS256":
            return _provision_from_claims(decode_central_token(token), db)
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("geen sub")
        user_uuid = uuid.UUID(str(user_id))
    except (JWTError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Ongeldig of verlopen token",
                            headers={"WWW-Authenticate": "Bearer"})

    user = db.query(User).filter(User.id == user_uuid, User.is_active == True).first()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Gebruiker niet gevonden of gedeactiveerd")
    # Lokaal (HS256) token: draagt geen centrale apps-claim.
    user._token_source = "lokaal"
    user._apps = None
    user._token_typ = payload.get("typ")
    user._token_scope = payload.get("scope")
    return user


def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Als get_current_user, maar geeft None zonder token i.p.v. 401.

    Nodig voor de app-autorisatiecontrole: die moet publieke en server-to-server
    routes ongemoeid laten (die komen zonder token binnen) en alleen ingrijpen
    wanneer er wél een token is meegestuurd.
    """
    heeft_token = bool(credentials) or bool(
        request.cookies.get(os.getenv("SSO_COOKIE_NAME", "rhadix_sso")))
    if not heeft_token:
        return None
    return get_current_user(request, credentials, db)


def require_role(*roles: UserRole):
    allowed = set(roles)

    def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Onvoldoende rechten")
        return current_user

    return _check
