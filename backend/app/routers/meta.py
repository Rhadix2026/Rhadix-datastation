import os

from fastapi import APIRouter

router = APIRouter()


@router.get("/meta")
def meta():
    """Applicatie-metadata voor de frontend-shell (omgeving, versie, features)."""
    return {
        "name": "Rhadix Datastation",
        "edition": "KIK-V",
        "version": "0.1.0",
        "environment": os.getenv("KIK_ENV", "development"),
        "modules": [
            {"key": "datastation", "label": "Datastation", "status": "available"},
        ],
    }
