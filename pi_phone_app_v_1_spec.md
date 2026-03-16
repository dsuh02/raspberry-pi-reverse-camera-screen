# Pi Phone App v1 Spec

## Goal
Build the phone/admin app first as a standalone web app for the Raspberry Pi. This app handles media upload, crop selection, media library management, profile creation/editing/deletion, and profile activation. The Pi-local touchscreen app will be built separately later as a much thinner profile-switching UI.

## Scope locked for v1
- Separate phone/admin app only
- Upload images and videos to the Pi
- Support Apple-origin image/video formats during upload and normalization
- Crop preview for images before display use
- Save uploaded media to the Pi
- Create/edit/delete profiles
- Three profile modes only:
  - Static: one image
  - Gallery: ordered list of images + interval seconds
  - Video: one video
- Activate one profile at a time

## Not in v1
- Pi-local settings UI
- Mixed image+video gallery playlists
- User accounts/auth
- Cloud sync
- Advanced transitions/effects
- Per-profile image crop variants
- Audio controls beyond simple mute support later

## Recommended stack
### Backend
- FastAPI
- Uvicorn
- SQLite
- SQLAlchemy or SQLModel
- python-multipart for uploads

### Media processing
- Pillow
- pillow-heif for HEIC/HEIF support
- FFmpeg/ffprobe for video probe + normalization + poster thumbnails

### Frontend
- React + Vite
- Mobile-first responsive UI
- Cropper UI component with locked 800x480 aspect ratio

## Why this split
The phone app needs richer workflows: uploads, crop preview, profile editing, media selection, ordering, and activation. That complexity is much better in a dedicated responsive web app. The future Pi-local app can stay intentionally small and only switch/select saved profiles.

## Display target assumptions
Primary display target for media assets is 800x480.
Target aspect ratio: 5:3.
All image crop selection should use a fixed 5:3 crop frame.

## App sections
### 1. Dashboard
- Show current active profile
- Quick activate existing profile
- Quick jump to uploads / profiles

### 2. Upload page
Two separate actions:
- Upload Image
- Upload Video

#### Image upload flow
1. Select file
2. Backend stores temporary original
3. Frontend loads preview
4. User sets crop region with fixed 5:3 frame
5. Save crop
6. Backend generates:
   - original asset
   - thumbnail
   - processed display asset
7. Asset appears in media library

#### Video upload flow
1. Select file
2. Backend stores original
3. Backend probes metadata
4. Backend normalizes to a standard playback format
5. Backend generates thumbnail/poster
6. Asset appears in media library

## Media library
Grid/list showing:
- thumbnail/poster
- filename
- type
- dimensions
- duration for video
- created date

Actions:
- view
- delete
- re-crop image
- use in new profile

## Profiles
Each profile is a saved configuration.

### Static profile
- name
- one selected image

### Gallery profile
- name
- ordered selected images
- interval seconds

### Video profile
- name
- one selected video

### Profile actions
- create
- edit
- delete
- duplicate
- activate

## Backend data model
### media_assets
- id
- kind (`image` | `video`)
- original_filename
- original_path
- processed_path
- thumbnail_path
- mime_type
- width
- height
- duration_seconds nullable
- crop_x nullable
- crop_y nullable
- crop_w nullable
- crop_h nullable
- created_at

### profiles
- id
- name
- mode (`static` | `gallery` | `video`)
- config_json
- created_at
- updated_at
- last_used_at nullable

### profile_media
- id
- profile_id
- media_asset_id
- sort_order

### app_state
- key
- value_json

Initial `app_state` keys:
- `active_profile_id`
- `gallery_runtime_state`

## Filesystem layout
```text
/opt/pi-media-app/
  backend/
  frontend/
  data/
    app.db
    uploads/
      originals/
      processed/
      thumbnails/
      videos_normalized/
```

## API endpoints
### Media
- `POST /api/media/images`
- `POST /api/media/videos`
- `GET /api/media`
- `GET /api/media/{id}`
- `DELETE /api/media/{id}`
- `POST /api/media/{id}/crop`

### Profiles
- `GET /api/profiles`
- `POST /api/profiles`
- `GET /api/profiles/{id}`
- `PUT /api/profiles/{id}`
- `DELETE /api/profiles/{id}`
- `POST /api/profiles/{id}/activate`

### State
- `GET /api/state`
- `PUT /api/state`

## Frontend routes
- `/` dashboard
- `/upload` upload page
- `/media` media library
- `/profiles` profile list
- `/profiles/new`
- `/profiles/:id/edit`

## Core UX details
### Upload buttons
Keep the image and video upload buttons separate exactly as requested.

### Crop UI
- Locked 5:3 crop ratio
- Show live preview of final framing
- Save once per image asset
- Re-crop available later from library

### Gallery ordering
- Explicit reorder controls
- Show interval field in seconds
- Preview final sequence order

## Video normalization recommendation
Normalize all uploaded videos at ingest instead of trying to directly play every source format. This is the cleanest way to support MOV/iPhone-origin files and keep later Pi playback predictable.

## Build order
### Phase 1
- Backend skeleton
- DB schema
- file storage service
- image upload endpoint
- basic image library listing

### Phase 2
- crop UI
- crop save endpoint
- processed image generation

### Phase 3
- video upload endpoint
- ffprobe metadata
- ffmpeg normalization
- poster generation

### Phase 4
- profiles CRUD
- gallery ordering
- activate profile endpoint

### Phase 5
- polish mobile UX
- prep contract for separate Pi-local app

## Suggested repo structure
```text
pi-media-app/
  backend/
    app/
      main.py
      db.py
      models.py
      schemas.py
      api/
        media.py
        profiles.py
        state.py
      services/
        image_service.py
        video_service.py
        storage_service.py
    requirements.txt
  frontend/
    src/
      pages/
      components/
      api/
      types/
    package.json
```

## Next implementation target
Start by building the backend and the phone frontend for:
1. image upload
2. image crop preview
3. image library
4. static profile create/edit/activate

That gives the smallest functional slice while establishing the patterns the other modes will reuse.

