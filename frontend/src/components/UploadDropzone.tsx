import { Upload, XCircle } from "lucide-react";
import { useRef, useState } from "react";
import { ProgressBar } from "./ProgressBar";

interface UploadDropzoneProps {
  busy: boolean;
  progress: number;
  error: string | null;
  onUpload: (file: File) => void;
}

export function UploadDropzone({ busy, progress, error, onUpload }: UploadDropzoneProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [over, setOver] = useState(false);

  const acceptFile = (file?: File) => {
    if (file) onUpload(file);
  };

  return (
    <section
      className={`dropzone ${over ? "dropzone--over" : ""}`}
      onDragOver={(event) => {
        event.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(event) => {
        event.preventDefault();
        setOver(false);
        acceptFile(event.dataTransfer.files[0]);
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept="video/mp4"
        hidden
        onChange={(event) => acceptFile(event.target.files?.[0])}
      />
      <button className="dropzone__button" disabled={busy} onClick={() => inputRef.current?.click()}>
        <Upload size={18} />
        Select MP4
      </button>
      <div className="dropzone__text">
        <strong>{busy ? "Uploading video" : "Drop an MP4 video"}</strong>
        <span>{busy ? `${progress}%` : "Local processing starts after validation"}</span>
      </div>
      {busy && <ProgressBar value={progress} />}
      {error && (
        <div className="inline-error">
          <XCircle size={16} />
          {error}
        </div>
      )}
    </section>
  );
}

