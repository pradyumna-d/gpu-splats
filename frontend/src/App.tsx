import { Link, Route, Routes } from "react-router-dom";
import { Box, ListChecks, Upload } from "lucide-react";
import { JobsPage } from "./pages/JobsPage";
import { UploadPage } from "./pages/UploadPage";
import { ViewerPage } from "./pages/ViewerPage";

export function App() {
  return (
    <div className="app">
      <nav className="topbar">
        <Link className="brand" to="/">
          <Box size={19} />
          Gaussian Splats
        </Link>
        <div className="nav-actions">
          <Link to="/" title="Upload">
            <Upload size={18} />
          </Link>
          <Link to="/jobs" title="Jobs">
            <ListChecks size={18} />
          </Link>
        </div>
      </nav>
      <Routes>
        <Route path="/" element={<UploadPage />} />
        <Route path="/jobs" element={<JobsPage />} />
        <Route path="/jobs/:jobId" element={<JobsPage />} />
        <Route path="/viewer/:jobId" element={<ViewerPage />} />
      </Routes>
    </div>
  );
}

