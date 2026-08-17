import type { Job } from "../types/job";

export const API_BASE = "";

export async function getJobs(): Promise<Job[]> {
  const response = await fetch(`${API_BASE}/api/jobs`);
  if (!response.ok) throw new Error("Unable to load jobs");
  return response.json();
}

export async function getJob(jobId: string): Promise<Job> {
  const response = await fetch(`${API_BASE}/api/jobs/${jobId}`);
  if (!response.ok) throw new Error("Unable to load job");
  return response.json();
}

export async function deleteJob(jobId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/jobs/${jobId}`, { method: "DELETE" });
  if (!response.ok) throw new Error("Unable to delete job");
}

export function uploadVideo(
  file: File,
  onProgress: (progress: number) => void,
): Promise<{ job_id: string }> {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.append("video", file);

    const request = new XMLHttpRequest();
    request.open("POST", `${API_BASE}/api/upload`);
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
    };
    request.onload = () => {
      if (request.status >= 200 && request.status < 300) {
        resolve(JSON.parse(request.responseText));
      } else {
        try {
          reject(new Error(JSON.parse(request.responseText).detail || "Upload failed"));
        } catch {
          reject(new Error("Upload failed"));
        }
      }
    };
    request.onerror = () => reject(new Error("Upload failed"));
    request.send(form);
  });
}

export function outputUrl(jobId: string, fileName = "scene.splat"): string {
  return `${API_BASE}/api/outputs/${jobId}/${fileName}`;
}

export interface SceneBounds {
  min: [number, number, number];
  max: [number, number, number];
  center: [number, number, number];
  size: [number, number, number];
}

export interface OutputMetadata {
  scene_file?: string;
  scene?: string;
  bounds?: SceneBounds;
}

export function sceneUrlFromMetadata(jobId: string, metadata?: OutputMetadata): string {
  if (metadata?.scene_file) return outputUrl(jobId, metadata.scene_file);
  if (metadata?.scene) return outputUrl(jobId, metadata.scene.split("/").pop() || "scene.splat");
  return outputUrl(jobId);
}

export async function getOutputMetadata(jobId: string): Promise<OutputMetadata | null> {
  try {
    const response = await fetch(outputUrl(jobId, "metadata.json"));
    if (!response.ok) return null;
    return (await response.json()) as OutputMetadata;
  } catch {
    return null;
  }
}

export async function getSceneUrl(jobId: string): Promise<string> {
  return sceneUrlFromMetadata(jobId, (await getOutputMetadata(jobId)) ?? undefined);
}
