import Link from "next/link";

import { apiGet, type ProblemList } from "@/lib/api";

export const metadata = { title: "Problems | ForgeJudge" };

export default async function ProblemsPage() {
  let problems: ProblemList | null = null;
  let unavailable = false;
  try {
    problems = await apiGet<ProblemList>("/problems?limit=100");
  } catch {
    unavailable = true;
  }

  return (
    <main className="page-shell">
      <div className="page-heading">
        <div>
          <div className="eyebrow">Problem set / {String(problems?.total ?? 0).padStart(2, "0")}</div>
          <h1 className="page-title">Problems</h1>
        </div>
        <p className="page-deck">Small problems, real systems. Choose a challenge to inspect its input contract and submit a solution.</p>
      </div>
      {unavailable ? (
        <div className="empty-state" role="status">Problem service is unavailable. Check API readiness and try again.</div>
      ) : problems?.items.length ? (
        <div className="problem-table" role="table" aria-label="Published coding problems">
          <div className="problem-row problem-header" role="row">
            <span role="columnheader">Problem</span><span role="columnheader">Difficulty</span><span role="columnheader">Limits</span><span aria-hidden="true" />
          </div>
          {problems.items.map((problem, index) => (
            <Link className="problem-row" href={`/problems/${problem.id}`} key={problem.id} role="row">
              <span className="problem-name"><span className="row-number">{String(index + 1).padStart(2, "0")}</span>{problem.title}</span>
              <span><span className={`difficulty difficulty-${problem.difficulty}`}>{problem.difficulty}</span></span>
              <span className="limit-copy">{problem.time_limit_ms} ms <span>/</span> {problem.memory_limit_mb} MB</span>
              <span className="row-arrow" aria-hidden="true">↗</span>
            </Link>
          ))}
        </div>
      ) : (
        <div className="empty-state" role="status">No published problems yet.</div>
      )}
    </main>
  );
}
