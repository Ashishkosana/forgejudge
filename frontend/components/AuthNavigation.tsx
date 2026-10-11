"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import type { AuthUser } from "@/lib/auth-bff";

export default function AuthNavigation() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    let active = true;
    void fetch("/api/auth/me", { cache: "no-store" }).then(async (response) => {
      if (response.ok) {
        if (active) setUser((await response.json()) as AuthUser);
        return;
      }
      if (response.status !== 401) {
        if (active) setUnavailable(true);
        return;
      }
      const refreshed = await fetch("/api/auth/session", { method: "POST" });
      if (refreshed.ok && active) {
        const result = (await refreshed.json()) as { user: AuthUser };
        setUser(result.user);
      }
    }).catch(() => {
      if (active) setUnavailable(true);
    });
    return () => {
      active = false;
    };
  }, []);

  async function logout() {
    try {
      const response = await fetch("/api/auth/logout", { method: "POST" });
      if (!response.ok) {
        setUnavailable(true);
        return;
      }
      setUser(null);
      router.push("/login");
      router.refresh();
    } catch {
      setUnavailable(true);
    }
  }

  return (
    <div className="auth-navigation">
      {user ? (
        <>
          <span className="auth-greeting">{user.display_name}</span>
          <button className="nav-button" type="button" onClick={() => void logout()}>
            Sign out
          </button>
        </>
      ) : (
        <>
          {unavailable && <span role="status">Auth unavailable</span>}
          <Link href="/login">Sign in</Link>
          <Link href="/register">Create account</Link>
        </>
      )}
    </div>
  );
}
