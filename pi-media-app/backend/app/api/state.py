from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db import get_session
from app.models import AppState

router = APIRouter(prefix="/api/state", tags=["state"])


@router.get("")
def get_state(session: Session = Depends(get_session)):
    results = session.exec(select(AppState)).all()
    return {row.key: row.value_json for row in results}
