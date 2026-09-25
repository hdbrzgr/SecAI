export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export type User = {
  id: string;
  email: string;
  name: string | null;
  is_superuser: boolean;
  mfa_enabled: boolean;
};

export type LoginResult = { mfa_required: boolean; user: User | null };

function errorMessage(detail: unknown): string {
  if (typeof detail === "string") return detail;
  // FastAPI validation errors: [{ msg: "..." }, ...]
  if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
  return "Something went wrong";
}

export async function api<T>(path: string, init: { method?: string; body?: unknown } = {}) {
  const res = await fetch(`/api${path}`, {
    method: init.method ?? (init.body === undefined ? "GET" : "POST"),
    credentials: "same-origin",
    headers: init.body === undefined ? undefined : { "Content-Type": "application/json" },
    body: init.body === undefined ? undefined : JSON.stringify(init.body),
  });
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(res.status, errorMessage(data.detail));
  return data as T;
}

export type Severity = "critical" | "high" | "medium" | "low" | "info";
export type ScanStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";
export type VerificationMethod = "dns_txt" | "well_known_file" | "meta_tag";
export type Grade = "A" | "B" | "C" | "D" | "F";

export type ToolRun = {
  name: string;
  status: "ok" | "skipped" | "failed" | "blocked";
  findings?: number;
  reason?: string;
  seconds?: number;
};

export type AiVerdict = "likely_real" | "needs_review" | "likely_false_positive";

export type FindingAi = {
  verdict: AiVerdict;
  severity: Severity;
  explanation: string;
  impact: string;
  fix_steps: string[];
  code_example: { language: string; code: string } | null;
};

export type ScanAi = {
  status: "ok" | "skipped" | "declined" | "incomplete" | "failed";
  reason: string | null;
  executive_summary: string | null;
  top_priorities: string[];
  model: string | null;
};

export type ScanSummary = {
  score?: number;
  grade?: Grade;
  counts?: Partial<Record<Severity, number>>;
  tools?: ToolRun[];
  seconds?: number;
  ai?: ScanAi | null;
};

export type ScanBrief = {
  id: string;
  status: ScanStatus;
  progress: number;
  current_step: string | null;
  summary: ScanSummary;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type Finding = {
  id: string;
  tool: string;
  rule_id: string;
  title: string;
  severity: Severity;
  cwe: string | null;
  location: { url?: string; param?: string };
  evidence: string | null;
  description: string | null;
  recommendation: string | null;
  references: string[];
  fingerprint: string;
  ai: FindingAi | null;
};

export type Scan = ScanBrief & {
  target_id: string | null;
  target_url: string | null;
  error: string | null;
  findings: Finding[];
};

export type Target = {
  id: string;
  url: string;
  hostname: string;
  verification_token: string;
  verification_method: VerificationMethod | null;
  verified_at: string | null;
  verification_expired: boolean;
  created_at: string;
  last_scan: ScanBrief | null;
};

export function formatDate(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}
