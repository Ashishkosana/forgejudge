import { cookies } from "next/headers";

export interface SampleTestCase {
  id: string;
  position: number;
  input_data: string;
  expected_output: string;
}

export interface ProblemSummary {
  id: string;
  slug: string;
  title: string;
  difficulty: "easy" | "medium" | "hard";
  time_limit_ms: number;
  memory_limit_mb: number;
}

export interface ProblemDetail extends ProblemSummary {
  description: string;
  sample_test_cases: SampleTestCase[];
}

export interface ProblemList {
  items: ProblemSummary[];
  offset: number;
  limit: number;
  total: number;
}

export interface SubmissionSummary {
  id: string;
  problem_id: string;
  problem: ProblemSummary;
  language: string;
  status: "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED";
  verdict:
    | "NOT_EVALUATED"
    | "ACCEPTED"
    | "WRONG_ANSWER"
    | "RUNTIME_ERROR"
    | "TIME_LIMIT_EXCEEDED"
    | "MEMORY_LIMIT_EXCEEDED";
  queued_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface SubmissionResult {
  id: string;
  test_case_id: string;
  status: SubmissionSummary["verdict"];
  runtime_ms: number | null;
  memory_kb: number | null;
  stdout: string | null;
  stderr: string | null;
}

export interface SubmissionDetail extends SubmissionSummary {
  user_id: string | null;
  source_code: string;
  failure_reason: string | null;
  results: SubmissionResult[];
}

export interface SubmissionList {
  items: SubmissionSummary[];
  offset: number;
  limit: number;
  total: number;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const apiBase = (process.env.API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

export async function apiGet<T>(path: string): Promise<T> {
  let response: Response;
  try {
    const headers = new Headers();
    if (path.startsWith("/submissions")) {
      const accessToken = (await cookies()).get("forgejudge_access")?.value;
      if (!accessToken) throw new ApiError("Sign in to view submissions.", 401);
      headers.set("Authorization", "Bearer " + accessToken);
    }
    response = await fetch(`${apiBase}${path}`, { cache: "no-store", headers });
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError("ForgeJudge API is unavailable.", 503);
  }

  if (!response.ok) {
    throw new ApiError(`ForgeJudge API returned ${response.status}.`, response.status);
  }
  return (await response.json()) as T;
}
