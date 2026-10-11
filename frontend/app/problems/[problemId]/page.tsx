import Link from "next/link";
import { notFound } from "next/navigation";

import SubmissionForm from "@/components/SubmissionForm";
import { ApiError, apiGet, type ProblemDetail } from "@/lib/api";

export default async function ProblemDetailPage({
  params,
}: {
  params: Promise<{ problemId: string }>;
}) {
  const { problemId } = await params;
  let problem: ProblemDetail;
  try {
    problem = await apiGet<ProblemDetail>(`/problems/${problemId}`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }

  return (
    <main className="page-shell">
      <Link className="back-link" href="/problems">← All problems</Link>
      <div className="detail-heading">
        <div>
          <div className="eyebrow">{problem.slug}</div>
          <h1 className="page-title">{problem.title}</h1>
          <div className="problem-meta">
            <span className={`difficulty difficulty-${problem.difficulty}`}>{problem.difficulty}</span>
            <span>{problem.time_limit_ms} ms</span>
            <span>{problem.memory_limit_mb} MB</span>
          </div>
        </div>
      </div>
      <div className="challenge-grid">
        <section className="statement" aria-labelledby="statement-title">
          <h2 id="statement-title">Problem</h2>
          <p>{problem.description}</p>
          {problem.sample_test_cases.map((testCase, index) => (
            <div className="sample-case" key={testCase.id}>
              <h3>Example {index + 1}</h3>
              <div className="sample-columns">
                <div><span>Input</span><pre>{testCase.input_data}</pre></div>
                <div><span>Output</span><pre>{testCase.expected_output}</pre></div>
              </div>
            </div>
          ))}
        </section>
        <aside className="submission-column" aria-label="Submit a solution">
          <SubmissionForm problemId={problem.id} />
        </aside>
      </div>
    </main>
  );
}
