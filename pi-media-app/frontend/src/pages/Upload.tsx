import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { uploadImage } from "../api/media";

export default function Upload() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedName, setSelectedName] = useState<string | null>(null);

  async function handleFile(file: File) {
    setError(null);
    setSelectedName(file.name);
    setUploading(true);
    try {
      await uploadImage(file);
      navigate("/media");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setUploading(false);
    }
  }

  function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  }

  return (
    <div className="page">
      <h1 className="page-title">Upload</h1>

      {error && <div className="error">{error}</div>}

      <div className="upload-area">
        <div
          className="upload-dropzone"
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={onDrop}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={onFileChange}
          />
          {uploading ? (
            <p>Uploading {selectedName}...</p>
          ) : (
            <>
              <p style={{ fontSize: "2rem", marginBottom: 8 }}>+</p>
              <p>Tap to select an image</p>
              <p style={{ fontSize: "0.8rem", marginTop: 4 }}>
                JPG, PNG, HEIC, WebP
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
