import { ArrowLeft } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { SplatViewer } from "../viewer/SplatViewer";

export function ViewerPage() {
  const { jobId } = useParams();
  if (!jobId) return null;

  return (
    <main className="viewer-page">
      <header className="viewer-header">
        <Link className="icon-button" to={`/jobs/${jobId}`} title="Back to job">
          <ArrowLeft size={18} />
        </Link>
        <div>
          <span className="eyebrow">Viewer</span>
          <h1>{jobId}</h1>
        </div>
      </header>
      <SplatViewer jobId={jobId} />
    </main>
  );
}

