import Link from "next/link";

import { apiGet, type SubmissionList } from "@/lib/api";

export const metadata = { title: "Submissions | ForgeJudge" };

export default async function SubmissionsPage() {
  let submissions: SubmissionList | null = null;
  let unavailable = false;
  try {
    submissions = await apiGet<SubmissionList>("/submissions?limit=100");
  } catch {
    unavailable = true;
  }

  return (
    <main className="page-shell">
      <div className="page-heading">
        <div>
          <div className="eyebrow">Queue history / {String(submissions?.total ?? 0).padStart(2, "0")}</div>
          <h1 className="page-title">Submissions</h1>
        </div>
        <p className="page-deck">Follow each job from durable queue entry through worker processing and its current verdict.</p>
      </div>
      {unavailable ? (
        <div className="empty-state" role="status">Submission service is unavailable. Check API readiness and try again.</div>
      ) : submissions?.items.length ? (
        <div className="submission-table" role="table" aria-label="Recent submissions">
          <div className="submission-row submission-header" role="row">
            <span role="columnheader">Problem</span><span role="columnheader">Status</span><span role="columnheader">Verdict</span><span role="columnheader">Queued</span>
          </div>
          {submissions.items.map((submission) => (
            <Link className="submission-row" href={`/submissions/${submission.id}`} key={submission.id} role="row">
              <span><strong>{submission.problem.title}</strong><small>{submission.language} · {submission.id.slice(0, 8)}</small></span>
              <span><span className={`status-pill status-${submission.status.toLowerCase()}`}>{submission.status}</span></span>
              <span className="verdict-copy">{submission.verdict.replaceAll("_", " ")}</span>
              <time dateTime={submission.queued_at}>{new Date(submission.queued_at).toLocaleString()}</time>
            </Link>
          ))}
        </div>
      ) : (
        <div className="empty-state" role="status">No submissions yet. Start from a problem detail page.</div>
      )}
    </main>
  );
}
