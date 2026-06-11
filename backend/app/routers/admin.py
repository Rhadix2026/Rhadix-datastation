"""admin.py — PLATFORM_ADMIN: organisaties en gebruikers beheren."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.auth.security import hash_password
from app.database import get_db
from app.models.auth_models import Tenant, User, UserRole

router = APIRouter(tags=["admin"])
_platform = require_role(UserRole.PLATFORM_ADMIN)


def _parse_uuid(val: str, label="ID") -> uuid.UUID:
    try:
        return uuid.UUID(str(val))
    except (ValueError, AttributeError):
        raise HTTPException(400, f"Ongeldig {label}: {val!r}")


def _user_dict(u: User) -> dict:
    return {"id": str(u.id), "email": u.email, "full_name": u.full_name,
            "role": u.role.value, "is_active": u.is_active,
            "tenant_id": str(u.tenant_id),
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None}


# ── Organisaties ──────────────────────────────────────────────────────────────
class CreateTenantRequest(BaseModel):
    name: str
    slug: str
    admin_email: str
    admin_full_name: Optional[str] = None
    admin_password: str


@router.get("/tenants")
def list_tenants(db: Session = Depends(get_db), _: User = Depends(_platform)):
    out = []
    for t in db.query(Tenant).order_by(Tenant.created_at).all():
        n = db.query(User).filter(User.tenant_id == t.id).count()
        out.append({"id": str(t.id), "slug": t.slug, "name": t.name,
                    "is_active": t.is_active, "user_count": n})
    return out


@router.post("/tenants", status_code=201)
def create_tenant(body: CreateTenantRequest, db: Session = Depends(get_db), _: User = Depends(_platform)):
    slug = body.slug.lower().strip()
    if db.query(Tenant).filter(Tenant.slug == slug).first():
        raise HTTPException(400, f"Slug '{slug}' bestaat al")
    email = body.admin_email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(400, f"E-mailadres '{email}' is al in gebruik")
    if len(body.admin_password) < 12:
        raise HTTPException(422, "Wachtwoord moet minimaal 12 tekens bevatten")

    tenant = Tenant(id=uuid.uuid4(), slug=slug, name=body.name, is_active=True)
    db.add(tenant); db.flush()
    admin = User(id=uuid.uuid4(), tenant_id=tenant.id, email=email,
                 full_name=body.admin_full_name, password_hash=hash_password(body.admin_password),
                 role=UserRole.ORG_ADMIN, is_active=True)
    db.add(admin); db.commit()
    return {"id": str(tenant.id), "slug": tenant.slug, "name": tenant.name,
            "admin": _user_dict(admin)}


@router.get("/tenants/{tenant_id}/users")
def list_tenant_users(tenant_id: str, db: Session = Depends(get_db), _: User = Depends(_platform)):
    tid = _parse_uuid(tenant_id, "tenant_id")
    users = db.query(User).filter(User.tenant_id == tid).order_by(User.created_at).all()
    return [_user_dict(u) for u in users]


@router.get("/users")
def list_all_users(db: Session = Depends(get_db), _: User = Depends(_platform)):
    return [_user_dict(u) for u in db.query(User).order_by(User.created_at).all()]


@router.get("/stats")
def platform_stats(db: Session = Depends(get_db), _: User = Depends(_platform)):
    return {
        "tenants": db.query(Tenant).count(),
        "users": db.query(User).count(),
        "active_users": db.query(User).filter(User.is_active == True).count(),
    }
