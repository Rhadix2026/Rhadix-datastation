"""auth/router.py — login, profiel, wachtwoord wijzigen."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.schemas import LoginRequest, PasswordChangeRequest, TokenResponse, UserResponse
from app.auth.security import create_access_token, hash_password, validate_password_strength, verify_password
from app.database import get_db
from app.models.auth_models import User

router = APIRouter(tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower().strip(), User.is_active == True).first()
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Onjuist e-mailadres of wachtwoord")
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    token = create_access_token({
        "sub": str(user.id), "role": user.role.value,
        "tenant_id": str(user.tenant_id), "email": user.email,
    })
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user.id), email=current_user.email, full_name=current_user.full_name,
        role=current_user.role, tenant_id=str(current_user.tenant_id),
        tenant_name=current_user.tenant.name,
    )


@router.patch("/me/password", status_code=204)
def change_password(body: PasswordChangeRequest, current_user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if not current_user.password_hash or not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(400, "Huidig wachtwoord is onjuist")
    try:
        validate_password_strength(body.new_password)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    current_user.password_hash = hash_password(body.new_password)
    db.commit()
