"""org.py — ORG_ADMIN: gebruikers binnen de eigen organisatie beheren."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.auth.security import hash_password, validate_password_strength
from app.database import get_db
from app.models.auth_models import User, UserRole

router = APIRouter(tags=["org"])
_org_admin = require_role(UserRole.ORG_ADMIN, UserRole.PLATFORM_ADMIN)


def _parse_uuid(val: str, label="ID") -> uuid.UUID:
    try:
        return uuid.UUID(str(val))
    except (ValueError, AttributeError):
        raise HTTPException(400, f"Ongeldig {label}: {val!r}")


def _user_dict(u: User) -> dict:
    return {"id": str(u.id), "email": u.email, "full_name": u.full_name,
            "role": u.role.value, "is_active": u.is_active,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None}


class CreateUserRequest(BaseModel):
    email: str
    full_name: Optional[str] = None
    password: str
    role: str = "ORG_USER"          # ORG_USER of ORG_ADMIN


class ResetPasswordRequest(BaseModel):
    new_password: str


@router.get("/users")
def list_users(db: Session = Depends(get_db), current: User = Depends(_org_admin)):
    users = db.query(User).filter(User.tenant_id == current.tenant_id).order_by(User.created_at).all()
    return [_user_dict(u) for u in users]


@router.post("/users", status_code=201)
def create_user(body: CreateUserRequest, db: Session = Depends(get_db), current: User = Depends(_org_admin)):
    email = body.email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(400, f"E-mailadres '{body.email}' is al in gebruik")
    try:
        validate_password_strength(body.password)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    try:
        role = UserRole(body.role)
    except ValueError:
        raise HTTPException(422, f"Ongeldige rol: {body.role!r}")
    if role == UserRole.PLATFORM_ADMIN:
        raise HTTPException(403, "Platform-beheerdersrol kan niet worden toegewezen")

    user = User(id=uuid.uuid4(), tenant_id=current.tenant_id, email=email,
                full_name=body.full_name, password_hash=hash_password(body.password),
                role=role, is_active=True)
    db.add(user); db.commit(); db.refresh(user)
    return _user_dict(user)


@router.patch("/users/{user_id}/deactivate")
def toggle_active(user_id: str, db: Session = Depends(get_db), current: User = Depends(_org_admin)):
    uid = _parse_uuid(user_id, "user_id")
    user = db.query(User).filter(User.id == uid, User.tenant_id == current.tenant_id).first()
    if not user:
        raise HTTPException(404, "Gebruiker niet gevonden in uw organisatie")
    if user.id == current.id:
        raise HTTPException(400, "U kunt uw eigen account niet deactiveren")
    user.is_active = not user.is_active
    db.commit()
    return {"id": str(user.id), "is_active": user.is_active}


@router.post("/users/{user_id}/reset-password", status_code=204)
def reset_password(user_id: str, body: ResetPasswordRequest, db: Session = Depends(get_db),
                   current: User = Depends(_org_admin)):
    uid = _parse_uuid(user_id, "user_id")
    user = db.query(User).filter(User.id == uid, User.tenant_id == current.tenant_id).first()
    if not user:
        raise HTTPException(404, "Gebruiker niet gevonden in uw organisatie")
    try:
        validate_password_strength(body.new_password)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    user.password_hash = hash_password(body.new_password)
    db.commit()


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: str, db: Session = Depends(get_db), current: User = Depends(_org_admin)):
    uid = _parse_uuid(user_id, "user_id")
    user = db.query(User).filter(User.id == uid, User.tenant_id == current.tenant_id).first()
    if not user:
        raise HTTPException(404, "Gebruiker niet gevonden in uw organisatie")
    if user.id == current.id:
        raise HTTPException(400, "U kunt uw eigen account niet verwijderen")
    db.delete(user); db.commit()
