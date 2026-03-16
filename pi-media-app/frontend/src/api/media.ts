import { apiFetch } from "./client";
import type { MediaAsset, MediaListResponse } from "../types";

export async function uploadImage(file: File): Promise<MediaAsset> {
  const form = new FormData();
  form.append("file", file);
  return apiFetch<MediaAsset>("/api/media/images", {
    method: "POST",
    body: form,
  });
}

export async function listMedia(kind?: string): Promise<MediaListResponse> {
  const params = kind ? `?kind=${kind}` : "";
  return apiFetch<MediaListResponse>(`/api/media${params}`);
}

export async function getMedia(id: number): Promise<MediaAsset> {
  return apiFetch<MediaAsset>(`/api/media/${id}`);
}

export async function deleteMedia(id: number): Promise<void> {
  return apiFetch<void>(`/api/media/${id}`, { method: "DELETE" });
}
