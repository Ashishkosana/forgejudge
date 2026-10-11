"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { csrfHeaders } from "@/lib/csrf-client";

interface AuthFormProps {
  mode: "login" | "register";
}

export default function AuthForm({ mode }: AuthFormProps) {
  const router = useRouter();
  const registering = mode === "register";
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    const form = new FormData(event.currentTarget);
    const payload = {
      email: String(form.get("email") ?? ""),
      password: String(form.get("password") ?? ""),
      ...(registering ? { display_name: String(form.get("display_name") ?? "") } : {}),
    };
    try {
      const response = await fetch(`/api/auth/${mode}`, {
        method: "POST",
        headers: { "content-type": "application/json", ...(await csrfHeaders()) },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const result = (await response.json()) as { detail?: string };
        throw new Error(result.detail ?? "Authentication failed.");
      }
      router.push("/problems");
      router.refresh();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Authentication failed.");
      setBusy(false);
    }
  }

  return (
    <main className="page-shell">
      <section className="auth-card">
        <div className="eyebrow">{registering ? "Create your account" : "Welcome back"}</div>
        <h1 className="page-title">{registering ? "Join ForgeJudge" : "Sign in"}</h1>
        <form className="auth-form" onSubmit={submit}>
          {registering && (
            <label>
              Display name
              <input name="display_name" autoComplete="name" maxLength={120} required />
            </label>
          )}
          <label>
            Email
            <input
              name="email"
              type="email"
              autoComplete="email"
              maxLength={320}
              required
            />
          </label>
          <label>
            Password
            <input
              name="password"
              type="password"
              autoComplete={registering ? "new-password" : "current-password"}
              minLength={registering ? 12 : 1}
              maxLength={128}
              required
            />
          </label>
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="primary-button" type="submit" disabled={busy}>
            {busy ? "Please wait…" : registering ? "Create account" : "Sign in"}
          </button>
        </form>
        <p className="form-note">
          {registering ? (
            <>Already registered? <Link href="/login">Sign in</Link>.</>
          ) : (
            <>New to ForgeJudge? <Link href="/register">Create an account</Link>.</>
          )}
        </p>
      </section>
    </main>
  );
}
