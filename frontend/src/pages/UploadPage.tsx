import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { uploadVideo } from "../services/api";
import { UploadDropzone } from "../components/UploadDropzone";

export function UploadPage() {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = async (file: File) => {
    setError(null);
    if (!file.name.toLowerCase().endsWith(".mp4")) {
      setError("Only MP4 videos are supported.");
      return;
    }
    setBusy(true);
    setProgress(0);
    try {
      const response = await uploadVideo(file, setProgress);
      navigate(`/jobs/${response.job_id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="page page--narrow">
      <header className="page-header">
        <span className="eyebrow">Local workstation</span>
        <h1>MP4 to Gaussian Splat</h1>
      </header>
      <UploadDropzone busy={busy} progress={progress} error={error} onUpload={handleUpload} />
    </main>
  );
}

