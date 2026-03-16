import { useState } from "react";
import type { MediaAsset } from "../types";
import { deleteMedia } from "../api/media";

interface Props {
  asset: MediaAsset;
  onDeleted: () => void;
}

export default function MediaCard({ asset, onDeleted }: Props) {
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const imgSrc = asset.thumbnail_url || asset.original_url;

  async function handleDelete() {
    setDeleting(true);
    try {
      await deleteMedia(asset.id);
      onDeleted();
    } catch (e) {
      alert("Failed to delete: " + (e as Error).message);
    } finally {
      setDeleting(false);
      setConfirming(false);
    }
  }

  return (
    <>
      <div className="media-card">
        <img className="media-card-img" src={imgSrc} alt={asset.original_filename} />
        <div className="media-card-info">
          <div className="media-card-name" title={asset.original_filename}>
            {asset.original_filename}
          </div>
          <div className="media-card-meta">
            {asset.width && asset.height ? `${asset.width}x${asset.height}` : asset.kind}
          </div>
        </div>
        <div className="media-card-actions">
          <button
            className="btn btn-danger btn-sm"
            onClick={() => setConfirming(true)}
          >
            Delete
          </button>
        </div>
      </div>

      {confirming && (
        <div className="confirm-overlay" onClick={() => setConfirming(false)}>
          <div className="confirm-box" onClick={(e) => e.stopPropagation()}>
            <p>Delete &ldquo;{asset.original_filename}&rdquo;?</p>
            <div className="confirm-actions">
              <button
                className="btn btn-outline btn-sm"
                onClick={() => setConfirming(false)}
              >
                Cancel
              </button>
              <button
                className="btn btn-danger btn-sm"
                onClick={handleDelete}
                disabled={deleting}
              >
                {deleting ? "Deleting..." : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
