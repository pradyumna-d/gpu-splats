import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowUpFromLine } from "lucide-react";
import { deleteJob, getJobs } from "../services/api";
import type { Job, JobEvent } from "../types/job";
import { useJobEvents } from "../hooks/useJobEvents";
import { JobTable } from "../components/JobTable";
import { ProgressBar } from "../components/ProgressBar";
import { StatusBadge } from "../components/StatusBadge";

export function JobsPage() {
  const { jobId } = useParams();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getJobs().then(setJobs).catch((caught) => setError(caught.message));
  }, []);

  const handleEvent = useCallback((event: JobEvent) => {
    setJobs((current) =>
      current.map((job) =>
        job.job_id === event.job_id
          ? {
              ...job,
              status: event.status,
              progress: event.progress,
              output_available: event.status === "completed" || job.output_available,
              viewer_url: event.viewer_url || job.viewer_url,
              error: event.error || job.error,
              completed_at: event.status === "completed" ? new Date().toISOString() : job.completed_at,
              updated_at: new Date().toISOString()
            }
          : job,
      ),
    );
  }, []);

  const jobIds = useMemo(() => jobs.map((job) => job.job_id), [jobs]);
  useJobEvents(jobIds, handleEvent);

  const selected = jobs.find((job) => job.job_id === jobId);
  const remove = async (id: string) => {
    await deleteJob(id);
    setJobs((current) => current.filter((job) => job.job_id !== id));
  };

  return (
    <main className="page">
      <header className="page-header page-header--row">
        <div>
          <span className="eyebrow">Job history</span>
          <h1>Reconstructions</h1>
        </div>
        <Link className="button" to="/">
          <ArrowUpFromLine size={17} />
          Upload
        </Link>
      </header>
      {error && <div className="inline-error">{error}</div>}
      {selected && (
        <section className="job-detail">
          <div>
            <span className="eyebrow">Active job</span>
            <h2>{selected.input_filename || selected.job_id}</h2>
          </div>
          <StatusBadge status={selected.status} />
          <ProgressBar value={selected.progress} />
          {selected.output_available && (
            <Link className="button button--dark" to={`/viewer/${selected.job_id}`}>
              Open Viewer
            </Link>
          )}
          {selected.error && <div className="inline-error">{selected.error}</div>}
        </section>
      )}
      <JobTable jobs={jobs} activeJobId={jobId} onDelete={remove} />
    </main>
  );
}

