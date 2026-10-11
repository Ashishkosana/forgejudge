'use client';

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

interface SubmissionFormProps {
  problemId: string;
}

interface CreatedSubmission {
  id: string;
}

export default function SubmissionForm({ problemId }: SubmissionFormProps) {
  const router = useRouter();
  const [sourceCode, setSourceCode] = useState("# Read input from stdin and write output to stdout\n");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const response = await fetch("/api/submissions", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ problem_id: problemId, language: "python", source_code: sourceCode }),
      });
      if (!response.ok) {
        const result = (await response.json()) as { detail?: string | { message?: string } };
        const detail = result.detail;
        throw new Error(
          typeof detail === "string" ? detail : detail?.message ?? "Submission could not be queued.",
        );
      }
      const submission = (await response.json()) as CreatedSubmission;
      router.push(`/submissions/${submission.id}`);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Submission could not be queued.");
      setIsSubmitting(false);
    }
  }

  return (
    <form className="submit-form" onSubmit={handleSubmit}>
      <div className="editor-heading">
        <label htmlFor="source-code">Python 3</label>
        <span>{sourceCode.length.toLocaleString()} / 100,000</span>
      </div>
      <textarea
        id="source-code"
        name="source_code"
        value={sourceCode}
        onChange={(event) => setSourceCode(event.target.value)}
        maxLength={100_000}
        spellCheck={false}
        required
        aria-describedby={error ? "submission-error" : undefined}
      />
      {error && (
        <p className="form-error" id="submission-error" role="alert">
          {error}
        </p>
      )}
      <button className="primary-button" type="submit" disabled={isSubmitting || !sourceCode.trim()}>
        {isSubmitting ? "Queueing…" : "Submit solution"}
      </button>
      <p className="form-note">Submissions are queued. User code is not executed in this phase.</p>
    </form>
  );
}
