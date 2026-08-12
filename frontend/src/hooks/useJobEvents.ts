import { useEffect } from "react";
import type { JobEvent } from "../types/job";

export function useJobEvents(
  jobIds: string[],
  onEvent: (event: JobEvent) => void,
  onError?: (jobId: string) => void,
) {
  useEffect(() => {
    const uniqueIds = Array.from(new Set(jobIds)).filter(Boolean);
    const sources = uniqueIds.map((jobId) => {
      const source = new EventSource(`/api/jobs/${jobId}/events`);
      const handle = (message: MessageEvent) => onEvent(JSON.parse(message.data));
      source.addEventListener("status", handle);
      source.addEventListener("completed", handle);
      source.addEventListener("failed", handle);
      source.onerror = () => onError?.(jobId);
      return source;
    });
    return () => sources.forEach((source) => source.close());
  }, [jobIds.join("|"), onEvent, onError]);
}

