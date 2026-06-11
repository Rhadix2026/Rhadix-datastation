"""dependencies.py — auth/authorisatie dependencies."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
from app.database import get_db
from app.models.auth_models import User, UserRole

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Niet geauthenticeerd",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = decode_access_token(credentials.credentials)
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
    return user


def require_role(*roles: UserRole):
    allowed = set(roles)

    def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Onvoldoende rechten")
        return current_user

    return _check
