/**
 * Typed client for the Scotch backend API.
 * All frontend↔backend traffic goes through this module.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiRequest<T>(
  method: string,
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      signal,
      headers: {
        Accept: "application/json",
        ...(body !== undefined && { "Content-Type": "application/json" }),
      },
      ...(body !== undefined && { body: JSON.stringify(body) }),
      cache: "no-store",
    });
  } catch {
    throw new ApiError(`Backend unreachable at ${API_BASE_URL}`);
  }
  if (!response.ok) {
    throw new ApiError(
      `${method} ${path} failed with ${response.status}`,
      response.status,
    );
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

function apiGet<T>(path: string, init?: { signal?: AbortSignal }): Promise<T> {
  return apiRequest<T>("GET", path, undefined, init?.signal);
}

export interface HealthResponse {
  app: string;
  status: string;
  version: string;
}

export function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return apiGet<HealthResponse>("/health", { signal });
}

export function getSampleProject(
  signal?: AbortSignal,
): Promise<import("@/features/project/types").ArchitectureProject> {
  return apiGet("/projects/sample", { signal });
}

// ── Project storage (Phase 4) ──────────────────────────────────────

type ArchitectureProject = import("@/features/project/types").ArchitectureProject;

/** Persistence envelope around the universal model (mirrors backend StoredProject). */
export interface StoredProject {
  id: string;
  name: string;
  prompt?: string | null;
  created_at: string;
  updated_at: string;
  project?: ArchitectureProject | null;
}

/** Listing row for dashboards (mirrors backend ProjectSummary). */
export interface ProjectSummary {
  id: string;
  name: string;
  prompt?: string | null;
  created_at: string;
  updated_at: string;
  room_count: number;
  site_label?: string | null;
}

export function listProjects(signal?: AbortSignal): Promise<ProjectSummary[]> {
  return apiGet("/projects", { signal });
}

export function createProject(body: {
  name: string;
  prompt?: string;
}): Promise<StoredProject> {
  return apiRequest("POST", "/projects", body);
}

export function getProject(
  projectId: string,
  signal?: AbortSignal,
): Promise<StoredProject> {
  return apiGet(`/projects/${projectId}`, { signal });
}

export function updateProject(
  projectId: string,
  body: {
    name?: string;
    prompt?: string;
    project?: ArchitectureProject;
  },
): Promise<StoredProject> {
  return apiRequest("PATCH", `/projects/${projectId}`, body);
}

export function deleteProject(projectId: string): Promise<void> {
  return apiRequest("DELETE", `/projects/${projectId}`);
}
