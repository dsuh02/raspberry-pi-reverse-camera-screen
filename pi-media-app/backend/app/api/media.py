from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from app.config import ALLOWED_IMAGE_TYPES, MAX_IMAGE_SIZE_MB, UPLOAD_DIR_ORIGINALS
from app.db import get_session
from app.models import MediaAsset
from app.schemas import CropRequest, MediaAssetResponse, MediaListResponse
from app.services.image_service import (
    generate_cropped_display_image,
    generate_thumbnail,
    get_image_dimensions,
)
from app.services.storage_service import (
    delete_media_files,
    generate_storage_filename,
    get_absolute_path,
    save_upload,
)

router = APIRouter(prefix="/api/media", tags=["media"])


def _asset_to_response(asset: MediaAsset) -> MediaAssetResponse:
    """Convert a DB model to an API response with computed URLs."""
    return MediaAssetResponse(
        id=asset.id,
        kind=asset.kind,
        original_filename=asset.original_filename,
        mime_type=asset.mime_type,
        width=asset.width,
        height=asset.height,
        duration_seconds=asset.duration_seconds,
        crop_x=asset.crop_x,
        crop_y=asset.crop_y,
        crop_w=asset.crop_w,
        crop_h=asset.crop_h,
        thumbnail_url=(
            f"/api/media/files/{asset.thumbnail_path}"
            if asset.thumbnail_path
            else None
        ),
        processed_url=(
            f"/api/media/files/{asset.processed_path}"
            if asset.processed_path
            else None
        ),
        original_url=f"/api/media/files/{asset.original_path}",
        created_at=asset.created_at,
    )


@router.post("/images", response_model=MediaAssetResponse, status_code=201)
async def upload_image(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    # Validate content type
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(400, f"Unsupported image type: {file.content_type}")

    # Read file content
    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise HTTPException(400, f"File exceeds {MAX_IMAGE_SIZE_MB}MB limit")

    # Save original
    storage_name = generate_storage_filename(file.filename or "upload.jpg")
    original_rel = save_upload(content, storage_name, UPLOAD_DIR_ORIGINALS)

    # Get dimensions
    abs_path = get_absolute_path(original_rel)
    width, height = get_image_dimensions(abs_path)

    # Generate thumbnail
    thumb_rel = generate_thumbnail(original_rel, storage_name)

    # Create DB record
    asset = MediaAsset(
        kind="image",
        original_filename=file.filename or "upload.jpg",
        original_path=original_rel,
        thumbnail_path=thumb_rel,
        mime_type=file.content_type,
        width=width,
        height=height,
    )
    session.add(asset)
    session.commit()
    session.refresh(asset)

    return _asset_to_response(asset)


@router.get("", response_model=MediaListResponse)
def list_media(
    kind: str | None = None,
    session: Session = Depends(get_session),
):
    statement = select(MediaAsset).order_by(MediaAsset.created_at.desc())
    if kind:
        statement = statement.where(MediaAsset.kind == kind)
    assets = session.exec(statement).all()
    return MediaListResponse(
        items=[_asset_to_response(a) for a in assets],
        total=len(assets),
    )


@router.get("/{media_id}", response_model=MediaAssetResponse)
def get_media(media_id: int, session: Session = Depends(get_session)):
    asset = session.get(MediaAsset, media_id)
    if not asset:
        raise HTTPException(404, "Media asset not found")
    return _asset_to_response(asset)


@router.delete("/{media_id}", status_code=204)
def delete_media(media_id: int, session: Session = Depends(get_session)):
    asset = session.get(MediaAsset, media_id)
    if not asset:
        raise HTTPException(404, "Media asset not found")
    delete_media_files(
        asset.original_path, asset.processed_path, asset.thumbnail_path
    )
    session.delete(asset)
    session.commit()


@router.post("/{media_id}/crop", response_model=MediaAssetResponse)
def crop_image(
    media_id: int,
    crop: CropRequest,
    session: Session = Depends(get_session),
):
    asset = session.get(MediaAsset, media_id)
    if not asset:
        raise HTTPException(404, "Media asset not found")
    if asset.kind != "image":
        raise HTTPException(400, "Can only crop images")

    # Generate the cropped display image
    storage_name = asset.original_path.split("/")[-1]
    processed_rel = generate_cropped_display_image(
        asset.original_path, storage_name, crop.x, crop.y, crop.w, crop.h
    )

    # Update the asset record
    asset.crop_x = crop.x
    asset.crop_y = crop.y
    asset.crop_w = crop.w
    asset.crop_h = crop.h
    asset.processed_path = processed_rel
    session.add(asset)
    session.commit()
    session.refresh(asset)

    return _asset_to_response(asset)


@router.get("/files/{file_path:path}")
def serve_file(file_path: str):
    """Serve uploaded files. Path is relative to DATA_DIR."""
    abs_path = get_absolute_path(file_path)
    if not abs_path.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(abs_path)
