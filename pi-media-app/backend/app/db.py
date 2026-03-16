from sqlmodel import SQLModel, Session, create_engine

from app.config import (
    DATABASE_URL,
    DATA_DIR,
    UPLOAD_DIR_ORIGINALS,
    UPLOAD_DIR_PROCESSED,
    UPLOAD_DIR_THUMBNAILS,
    UPLOAD_DIR_VIDEOS_NORMALIZED,
)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_db():
    """Create data directories and database tables."""
    for d in [
        DATA_DIR,
        UPLOAD_DIR_ORIGINALS,
        UPLOAD_DIR_PROCESSED,
        UPLOAD_DIR_THUMBNAILS,
        UPLOAD_DIR_VIDEOS_NORMALIZED,
    ]:
        d.mkdir(parents=True, exist_ok=True)

    import app.models  # noqa: F401 — ensure models are registered

    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency that yields a database session."""
    with Session(engine) as session:
        yield session
