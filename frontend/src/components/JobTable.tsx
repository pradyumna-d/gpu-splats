import { Eye, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";
import type { Job } from "../types/job";
import { ProgressBar } from "./ProgressBar";
import { StatusBadge } from "./StatusBadge";

interface JobTableProps {
  jobs: Job[];
  activeJobId?: string;
  onDelete: (jobId: string) => void;
}

export function JobTable({ jobs, activeJobId, onDelete }: JobTableProps) {
  if (jobs.length === 0) {
    return <div className="empty-state">No jobs yet.</div>;
  }

  return (
    <div className="table-shell">
      <table>
        <thead>
          <tr>
            <th>Video</th>
            <th>Status</th>
            <th>Progress</th>
            <th>Created</th>
            <th>Completed</th>
            <th aria-label="Actions" />
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.job_id} className={job.job_id === activeJobId ? "row--active" : undefined}>
              <td>
                <Link to={`/jobs/${job.job_id}`} className="job-link">
                  {job.input_filename || job.job_id}
                </Link>
                {job.error && <span className="job-error">{job.error}</span>}
              </td>
              <td>
                <StatusBadge status={job.status} />
              </td>
              <td>
                <div className="progress-cell">
                  <ProgressBar value={job.progress} />
                  <span>{job.progress}%</span>
                </div>
              </td>
              <td>{formatDate(job.created_at)}</td>
              <td>{job.completed_at ? formatDate(job.completed_at) : "-"}</td>
              <td>
                <div className="actions">
                  <Link
                    className={`icon-button ${!job.output_available ? "icon-button--disabled" : ""}`}
                    to={job.output_available ? `/viewer/${job.job_id}` : `/jobs/${job.job_id}`}
                    title="Open viewer"
                    aria-disabled={!job.output_available}
                  >
                    <Eye size={17} />
                  </Link>
                  <button className="icon-button" onClick={() => onDelete(job.job_id)} title="Delete job">
                    <Trash2 size={17} />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

