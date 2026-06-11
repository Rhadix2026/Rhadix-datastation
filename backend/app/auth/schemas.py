from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from app.models.auth_models import UserRole


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    role: UserRole
    tenant_id: str
    tenant_name: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str
