from fastapi import APIRouter

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


@router.get("")
def list_profiles():
    return {"items": [], "total": 0}
