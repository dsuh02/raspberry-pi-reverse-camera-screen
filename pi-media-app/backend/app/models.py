from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class MediaAsset(SQLModel, table=True):
    __tablename__ = "media_assets"

    id: Optional[int] = Field(default=None, primary_key=True)
    kind: str  # "image" | "video"
    original_filename: str
    original_path: str  # relative to DATA_DIR
    processed_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    mime_type: str
    width: Optional[int] = None
    height: Optional[int] = None
    duration_seconds: Optional[float] = None

    # Crop region (set via crop endpoint)
    crop_x: Optional[int] = None
    crop_y: Optional[int] = None
    crop_w: Optional[int] = None
    crop_h: Optional[int] = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    profile_links: list["ProfileMedia"] = Relationship(
        back_populates="media_asset"
    )


class Profile(SQLModel, table=True):
    __tablename__ = "profiles"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    mode: str  # "static" | "gallery" | "video"
    config_json: str = Field(default="{}")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_used_at: Optional[datetime] = None

    media_links: list["ProfileMedia"] = Relationship(
        back_populates="profile"
    )


class ProfileMedia(SQLModel, table=True):
    __tablename__ = "profile_media"

    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="profiles.id")
    media_asset_id: int = Field(foreign_key="media_assets.id")
    sort_order: int = 0

    profile: Optional[Profile] = Relationship(back_populates="media_links")
    media_asset: Optional[MediaAsset] = Relationship(
        back_populates="profile_links"
    )


class AppState(SQLModel, table=True):
    __tablename__ = "app_state"

    key: str = Field(primary_key=True)
    value_json: str = Field(default="{}")
