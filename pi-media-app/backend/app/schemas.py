from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MediaAssetResponse(BaseModel):
    id: int
    kind: str
    original_filename: str
    mime_type: str
    width: Optional[int]
    height: Optional[int]
    duration_seconds: Optional[float]
    crop_x: Optional[int]
    crop_y: Optional[int]
    crop_w: Optional[int]
    crop_h: Optional[int]
    thumbnail_url: Optional[str]
    processed_url: Optional[str]
    original_url: str
    created_at: datetime


class MediaListResponse(BaseModel):
    items: list[MediaAssetResponse]
    total: int


class CropRequest(BaseModel):
    x: int
    y: int
    w: int
    h: int
