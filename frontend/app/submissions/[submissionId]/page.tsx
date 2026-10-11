import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { ApiError, apiGet, type SubmissionDetail } from "@/lib/api";

export default async function SubmissionDetailPage({
  params,
}: {
  params: Promise<{ submissionId: string }>;
}) {
  const { submissionId } = await params;
  let submission: SubmissionDetail;
  try {
    submission = await apiGet<SubmissionDetail>(`/submissions/${submissionId}`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    if (error instanceof ApiError && error.status === 401) {
      redirect(`/login?next=%2Fsubmissions%2F${submissionId}`);
    }
    throw error;
  }

  return (
    <main className="page-shell">
      <Link className="back-link" href="/submissions">← All submissions</Link>
      <div className="page-heading detail-heading">
        <div>
          <div className="eyebrow">Submission / {submission.id.slice(0, 8)}</div>
          <h1 className="page-title">{submission.problem.title}</h1>
          <div className="problem-meta">
            <span className={`status-pill status-${submission.status.toLowerCase()}`}>{submission.status}</span>
            <span>{submission.verdict.replaceAll("_", " ")}</span>
            <span>{submission.language}</span>
          </div>
        </div>
        <Link className="text-link" href={`/problems/${submission.problem_id}`}>Open problem ↗</Link>
      </div>
      {submission.failure_reason && <div className="form-error">{submission.failure_reason}</div>}
      <section className="result-section" aria-labelledby="results-title">
        <div className="section-heading"><h2 id="results-title">Test cases</h2><span>{submission.results.length} recorded</span></div>
        {submission.results.length ? (
          <div className="result-table" role="table" aria-label="Per-test-case results">
            <div className="result-row result-header" role="row"><span role="columnheader">Case</span><span role="columnheader">Status</span><span role="columnheader">Runtime</span><span role="columnheader">Memory</span></div>
            {submission.results.map((result, index) => (
              <div className="result-row" role="row" key={result.id}>
                <span>Case {String(index + 1).padStart(2, "0")}</span>
                <span>{result.status.replaceAll("_", " ")}</span>
                <span>{result.runtime_ms === null ? "—" : `${result.runtime_ms.toFixed(2)} ms`}</span>
                <span>{result.memory_kb === null ? "—" : `${result.memory_kb} KB`}</span>
              </div>
            ))}
          </div>
        ) : <div className="empty-state">The worker has not recorded test cases yet.</div>}
      </section>
      <section className="source-section" aria-labelledby="source-title">
        <div className="section-heading"><h2 id="source-title">Source code</h2><span>Python 3</span></div>
        <pre className="source-code"><code>{submission.source_code}</code></pre>
      </section>
    </main>
  );
}
