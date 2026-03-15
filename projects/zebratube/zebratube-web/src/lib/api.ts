// src/lib/api.ts — typed API client for zebratube-api

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";

// ── generic fetch ─────────────────────────────────────────────────────────────

async function req<T>(
  method: string,
  path: string,
  body?: unknown,
  headers?: Record<string, string>,
): Promise<T> {
  const token = localStorage.getItem("zt_token");
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      ...(body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, detail.detail ?? res.statusText);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

const get  = <T>(path: string)               => req<T>("GET",    path);
const post = <T>(path: string, body: unknown) => req<T>("POST",   path, body);
const del  = <T>(path: string)               => req<T>("DELETE", path);

// ── types ─────────────────────────────────────────────────────────────────────

export interface Project {
  id: string;
  slug: string;
  title: string;
  description: string | null;
  project_type: string;
  source_url: string | null;
  is_public: boolean;
  created_at: string;
  version_count: number;
  latest_version_id: string | null;
  corpus_stats: CorpusStats | null;
}

export interface CorpusStats {
  entities: number;
  events: number;
  claims: number;
  ambiguities: number;
  themes: number;
  source_documents: number;
}

export interface ProjectVersion {
  id: string;
  project_id: string;
  version_number: number;
  crawl_timestamp: string;
  source_commit: string | null;
  model_name: string | null;
  corpus_stats: CorpusStats | null;
  task_count: number;
  is_active: boolean;
}

export interface Task {
  id: string;
  project_id: string;
  project_version_id: string;
  projection_type: string;
  label: string;
  difficulty: "simple" | "standard" | "complex";
  output_format: string;
  duration_estimate_s: number | null;
  assembly_weight: number;
  status: "open" | "claimed" | "submitted" | "in_review" | "accepted" | "saturated";
  submission_count: number;
  accepted_count: number;
  current_bounty: number;
  scarcity: number;
  style_hint: string | null;
  output_spec: Record<string, string> | null;
  graph_nodes: string[] | null;
  depends_on: string[] | null;
  created_at: string;
}

export interface Claim {
  id: string;
  user_id: string;
  task_id: string;
  status: string;
  claimed_at: string;
  expires_at: string;
}

export interface Submission {
  id: string;
  task_id: string;
  user_id: string;
  claim_id: string;
  status: string;
  branch_label: string | null;
  preview_url: string | null;
  thumbnail_url: string | null;
  media_metadata: Record<string, unknown> | null;
  notes: string | null;
  submitted_at: string;
}

export interface User {
  id: string;
  username: string;
  role: string;
  point_balance: number;
  person_graph_public: boolean;
  created_at: string;
}

export interface UserProfile extends User {
  specialisations: string[];
  contributions: Record<string, number>;
  person_graph: Record<string, unknown> | null;
}

export interface SearchResult {
  type: string;
  id: string;
  label: string;
  project_id: string | null;
  score: number;
  source_docs: string[];
}

// ── projects ──────────────────────────────────────────────────────────────────

export const projects = {
  list: (params?: { project_type?: string; limit?: number; offset?: number }) =>
    get<Project[]>(`/projects?${new URLSearchParams(params as Record<string,string> ?? {})}`),

  get: (slug: string) =>
    get<Project>(`/projects/${slug}`),

  versions: (slug: string) =>
    get<ProjectVersion[]>(`/projects/${slug}/versions`),

  graph: (slug: string, versionId: string) =>
    get<Record<string, unknown>>(`/projects/${slug}/versions/${versionId}/graph`),

  wiki: (slug: string, style = "science") =>
    get<Record<string, unknown>>(`/projects/${slug}/wiki?style=${style}`),

  diff: (slug: string, versionId: string, compareTo?: string) =>
    get<Record<string, unknown>>(
      `/projects/${slug}/versions/${versionId}/diff${compareTo ? `?compare_to=${compareTo}` : ""}`
    ),

  ingest: (slug: string, body: { source_path?: string; source_url?: string; model?: string }) =>
    post<{ status: string }>(`/projects/${slug}/ingest`, body),
};

// ── tasks ─────────────────────────────────────────────────────────────────────

export const tasks = {
  list: (params?: {
    project_id?: string;
    projection_type?: string;
    difficulty?: string;
    status?: string;
    min_bounty?: number;
    sort_by?: string;
    limit?: number;
    offset?: number;
  }) => get<Task[]>(`/tasks?${new URLSearchParams(params as Record<string,string> ?? {})}`),

  bottlenecks: (limit = 10) =>
    get<Task[]>(`/tasks/bottlenecks?limit=${limit}`),

  get: (taskId: string) =>
    get<Task>(`/tasks/${taskId}`),

  submissions: (taskId: string) =>
    get<Submission[]>(`/tasks/${taskId}/submissions`),

  bounty: (taskId: string) =>
    get<{ bounty: number; breakdown: Record<string, number> }>(`/tasks/${taskId}/bounty`),

  bundleUrl: (taskId: string) =>
    `${BASE}/tasks/${taskId}/bundle`,
};

// ── claims ────────────────────────────────────────────────────────────────────

export const claims = {
  create: (taskId: string) =>
    post<Claim>("/claims", { task_id: taskId }),

  withdraw: (claimId: string) =>
    del<void>(`/claims/${claimId}`),

  mine: () =>
    get<Claim[]>("/claims/mine"),
};

// ── submissions ───────────────────────────────────────────────────────────────

export const submissions = {
  upload: (form: FormData) =>
    req<Submission>("POST", "/submissions", form),

  get: (id: string) =>
    get<Submission>(`/submissions/${id}`),

  forTask: (taskId: string) =>
    get<Submission[]>(`/submissions/task/${taskId}`),
};

// ── reviews ───────────────────────────────────────────────────────────────────

export const reviews = {
  create: (submissionId: string, verdict: string, notes?: string) =>
    post<unknown>("/reviews", { submission_id: submissionId, verdict, notes }),

  forSubmission: (submissionId: string) =>
    get<unknown[]>(`/reviews/submission/${submissionId}`),
};

// ── assemblies ────────────────────────────────────────────────────────────────

export const assemblies = {
  create: (body: {
    project_version_id: string;
    title?: string;
    segments: Array<{
      task_id: string;
      submission_id?: string;
      position: number;
      is_canonical?: boolean;
    }>;
  }) => post<unknown>("/assemblies", body),

  get: (id: string) =>
    get<unknown>(`/assemblies/${id}`),

  render: (id: string) =>
    post<void>(`/assemblies/${id}/render`, {}),
};

// ── users ─────────────────────────────────────────────────────────────────────

export const users = {
  register: (username: string, email: string, password: string) =>
    post<User>("/users/register", { username, email, password }),

  me: () => get<UserProfile>("/users/me"),

  get: (username: string) =>
    get<UserProfile>(`/users/${username}`),

  ledger: (username: string) =>
    get<unknown[]>(`/users/${username}/ledger`),
};

// ── search ────────────────────────────────────────────────────────────────────

export const search = {
  query: (q: string, mode = "full", projectId?: string, limit = 10) =>
    get<SearchResult[]>(
      `/search?q=${encodeURIComponent(q)}&mode=${mode}&limit=${limit}` +
      (projectId ? `&project_id=${projectId}` : "")
    ),
};
