import { useCallback, useEffect, useState } from "react";
import { listMedia } from "../api/media";
import type { MediaAsset } from "../types";
import MediaCard from "../components/MediaCard";

export default function MediaLibrary() {
  const [assets, setAssets] = useState<MediaAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMedia = useCallback(async () => {
    try {
      const data = await listMedia();
      setAssets(data.items);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMedia();
  }, [fetchMedia]);

  if (loading) return <div className="loading">Loading...</div>;

  return (
    <div className="page">
      <h1 className="page-title">Media Library</h1>

      {error && <div className="error">{error}</div>}

      {assets.length === 0 ? (
        <div className="empty-state">
          <p>No media yet</p>
          <p style={{ fontSize: "0.85rem", marginTop: 8 }}>
            Upload your first image to get started
          </p>
        </div>
      ) : (
        <div className="media-grid">
          {assets.map((asset) => (
            <MediaCard key={asset.id} asset={asset} onDeleted={fetchMedia} />
          ))}
        </div>
      )}
    </div>
  );
}
