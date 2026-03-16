from pathlib import Path

import pillow_heif
from PIL import Image

from app.config import (
    DATA_DIR,
    DISPLAY_HEIGHT,
    DISPLAY_WIDTH,
    THUMB_MAX_HEIGHT,
    THUMB_MAX_WIDTH,
    UPLOAD_DIR_PROCESSED,
    UPLOAD_DIR_THUMBNAILS,
)
from app.services.storage_service import get_absolute_path

# Register HEIF/HEIC opener with Pillow
pillow_heif.register_heif_opener()


def get_image_dimensions(file_path: Path) -> tuple[int, int]:
    """Return (width, height) of an image file."""
    with Image.open(file_path) as img:
        return img.size


def generate_thumbnail(original_relative_path: str, storage_filename: str) -> str:
    """Generate a thumbnail. Returns path relative to DATA_DIR.

    Thumbnail maintains aspect ratio, fits within THUMB_MAX dimensions.
    Always saved as JPEG.
    """
    src = get_absolute_path(original_relative_path)
    thumb_filename = Path(storage_filename).stem + "_thumb.jpg"
    dest = UPLOAD_DIR_THUMBNAILS / thumb_filename

    with Image.open(src) as img:
        img = img.convert("RGB")
        img.thumbnail(
            (THUMB_MAX_WIDTH, THUMB_MAX_HEIGHT), Image.Resampling.LANCZOS
        )
        img.save(dest, "JPEG", quality=80)

    return str(dest.relative_to(DATA_DIR))


def generate_cropped_display_image(
    original_relative_path: str,
    storage_filename: str,
    crop_x: int,
    crop_y: int,
    crop_w: int,
    crop_h: int,
) -> str:
    """Crop the original image and resize to 800x480.

    Returns path relative to DATA_DIR.
    """
    src = get_absolute_path(original_relative_path)
    proc_filename = Path(storage_filename).stem + "_display.jpg"
    dest = UPLOAD_DIR_PROCESSED / proc_filename

    with Image.open(src) as img:
        img = img.convert("RGB")
        cropped = img.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h))
        resized = cropped.resize(
            (DISPLAY_WIDTH, DISPLAY_HEIGHT), Image.Resampling.LANCZOS
        )
        resized.save(dest, "JPEG", quality=90)

    return str(dest.relative_to(DATA_DIR))
