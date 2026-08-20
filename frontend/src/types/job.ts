export type JobStatus =
  | "queued"
  | "extracting_frames"
  | "running_colmap"
  | "preparing_dataset"
  | "training"
  | "exporting"
  | "completed"
  | "failed";

export interface Job {
  job_id: string;
  status: JobStatus;
  progress: number;
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
  output_available: boolean;
  input_filename?: string | null;
  viewer_url?: string | null;
  error?: string | null;
}

export interface JobEvent {
  job_id: string;
  status: JobStatus;
  progress: number;
  viewer_url?: string;
  error?: string;
}

