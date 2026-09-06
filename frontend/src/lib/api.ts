import type { Report } from "./types";

export class ApiError extends Error {}

export async function analyzeDocument(file: File): Promise<Report> {
  const body = new FormData();
  body.append("file", file, file.name);

  let res: Response;
  try {
    res = await fetch("/api/analyze", { method: "POST", body });
  } catch {
    throw new ApiError(
      "Could not reach the Authentix service. Is it running on port 8000? (python server.py)"
    );
  }

  const text = await res.text();
  let data: unknown;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    throw new ApiError(`Unexpected response from the server (HTTP ${res.status}).`);
  }

  if (!res.ok) {
    const detail =
      (data as { detail?: string })?.detail ?? `Analysis failed (HTTP ${res.status}).`;
    throw new ApiError(detail);
  }
  return data as Report;
}

export async function health(): Promise<boolean> {
  try {
    const r = await fetch("/api/health");
    return r.ok;
  } catch {
    return false;
  }
}
