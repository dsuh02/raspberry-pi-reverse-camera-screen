import uuid
from pathlib import Path

from app.config import DATA_DIR


def generate_storage_filename(original_filename: str) -> str:
    """Generate a unique filename preserving the original extension."""
    ext = Path(original_filename).suffix.lower()
    return f"{uuid.uuid4().hex}{ext}"


def save_upload(content: bytes, filename: str, subdir: Path) -> str:
    """Save raw bytes to the given subdirectory.

    Returns path relative to DATA_DIR.
    """
    dest = subdir / filename
    dest.write_bytes(content)
    return str(dest.relative_to(DATA_DIR))


def get_absolute_path(relative_path: str) -> Path:
    """Convert a DB-stored relative path to an absolute filesystem path."""
    return DATA_DIR / relative_path


def delete_media_files(
    original_path: str | None,
    processed_path: str | None,
    thumbnail_path: str | None,
) -> None:
    """Delete all files associated with a media asset."""
    for rel_path in [original_path, processed_path, thumbnail_path]:
        if rel_path:
            abs_path = get_absolute_path(rel_path)
            if abs_path.exists():
                abs_path.unlink()
