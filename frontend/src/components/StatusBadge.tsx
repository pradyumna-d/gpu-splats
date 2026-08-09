import type { JobStatus } from "../types/job";

const labels: Record<JobStatus, string> = {
  queued: "Queued",
  extracting_frames: "Extracting",
  running_colmap: "COLMAP",
  preparing_dataset: "Dataset",
  training: "Training",
  exporting: "Exporting",
  completed: "Completed",
  failed: "Failed"
};

export function StatusBadge({ status }: { status: JobStatus }) {
  return <span className={`status status--${status}`}>{labels[status]}</span>;
}

