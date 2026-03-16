export interface MediaAsset {
  id: number;
  kind: "image" | "video";
  original_filename: string;
  mime_type: string;
  width: number | null;
  height: number | null;
  duration_seconds: number | null;
  crop_x: number | null;
  crop_y: number | null;
  crop_w: number | null;
  crop_h: number | null;
  thumbnail_url: string | null;
  processed_url: string | null;
  original_url: string;
  created_at: string;
}

export interface MediaListResponse {
  items: MediaAsset[];
  total: number;
}

export interface Profile {
  id: number;
  name: string;
  mode: "static" | "gallery" | "video";
  config_json: string;
  created_at: string;
  updated_at: string;
  last_used_at: string | null;
}

export interface ProfileListResponse {
  items: Profile[];
  total: number;
}
