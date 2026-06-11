from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health():
    """Liveness probe voor Docker/CI."""
    return {"status": "ok"}
