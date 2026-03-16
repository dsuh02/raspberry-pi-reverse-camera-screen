import os
from pathlib import Path

# Base data directory - override with PI_MEDIA_DATA_DIR env var
DATA_DIR = Path(
    os.getenv(
        "PI_MEDIA_DATA_DIR",
        str(Path(__file__).resolve().parent.parent.parent / "data"),
    )
)

DB_PATH = DATA_DIR / "app.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

UPLOAD_DIR_ORIGINALS = DATA_DIR / "uploads" / "originals"
UPLOAD_DIR_PROCESSED = DATA_DIR / "uploads" / "processed"
UPLOAD_DIR_THUMBNAILS = DATA_DIR / "uploads" / "thumbnails"
UPLOAD_DIR_VIDEOS_NORMALIZED = DATA_DIR / "uploads" / "videos_normalized"

# Display target
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480

# Thumbnail dimensions (maintains 5:3)
THUMB_MAX_WIDTH = 320
THUMB_MAX_HEIGHT = 192

# Allowed MIME types
ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}
ALLOWED_VIDEO_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/webm",
    "video/x-msvideo",
}

# Upload size limits
MAX_IMAGE_SIZE_MB = 50
MAX_VIDEO_SIZE_MB = 500
