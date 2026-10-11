import { cookies } from "next/headers";

const apiBase = (process.env.API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
const accessCookie = "forgejudge_access";
const refreshCookie = "forgejudge_refresh";

export interface AuthUser {
  id: string;
  email: string;
  display_name: string;
  role: "user" | "admin";
}

interface AuthTokenResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user: AuthUser;
}

export function isSameOrigin(request: Request): boolean {
  const origin = request.headers.get("origin");
  return origin !== null && origin === new URL(request.url).origin;
}

export async function forwardAuth(
  path: string,
  payload?: unknown,
  accessToken?: string,
  method: "GET" | "POST" = payload === undefined ? "GET" : "POST",
  forwardedFor?: string,
): Promise<Response> {
  const sharedSecret = process.env.FORGEJUDGE_BFF_SHARED_SECRET;
  if (!sharedSecret || sharedSecret.length < 32) {
    return Response.json({ detail: "Authentication is not configured." }, { status: 503 });
  }

  const headers = new Headers({ "X-ForgeJudge-BFF-Secret": sharedSecret });
  if (payload !== undefined) headers.set("content-type", "application/json");
  if (accessToken) headers.set("Authorization", "Bearer " + accessToken);
  if (forwardedFor) headers.set("X-Forwarded-For", forwardedFor);

  try {
    return await fetch(`${apiBase}${path}`, {
      method,
      headers,
      body: payload === undefined ? undefined : JSON.stringify(payload),
      cache: "no-store",
    });
  } catch {
    return Response.json({ detail: "Authentication service is unavailable." }, { status: 503 });
  }
}

export async function writeSession(upstream: Response): Promise<Response> {
  if (!upstream.ok) return relayError(upstream);

  let result: AuthTokenResponse;
  try {
    result = (await upstream.json()) as AuthTokenResponse;
  } catch {
    return Response.json(
      { detail: "Authentication service returned an invalid response." },
      { status: 502 },
    );
  }
  if (
    typeof result.access_token !== "string" ||
    typeof result.refresh_token !== "string" ||
    typeof result.expires_in !== "number" ||
    !result.user
  ) {
    return Response.json(
      { detail: "Authentication service returned an invalid response." },
      { status: 502 },
    );
  }

  const cookieStore = await cookies();
  const secure = process.env.NODE_ENV === "production";
  cookieStore.set(accessCookie, result.access_token, {
    httpOnly: true,
    secure,
    sameSite: "lax",
    path: "/",
    maxAge: result.expires_in,
  });
  cookieStore.set(refreshCookie, result.refresh_token, {
    httpOnly: true,
    secure,
    sameSite: "lax",
    path: "/api/auth",
    maxAge: 30 * 24 * 60 * 60,
  });

  return Response.json(
    { user: result.user, expires_in: result.expires_in },
    { headers: { "Cache-Control": "no-store" } },
  );
}

export async function clearSession(): Promise<void> {
  const cookieStore = await cookies();
  for (const name of [accessCookie, refreshCookie]) {
    cookieStore.set(name, "", {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: name === refreshCookie ? "/api/auth" : "/",
      maxAge: 0,
    });
  }
}

export async function readAccessToken(): Promise<string | undefined> {
  return (await cookies()).get(accessCookie)?.value;
}

export async function readRefreshToken(): Promise<string | undefined> {
  return (await cookies()).get(refreshCookie)?.value;
}

export async function relayError(upstream: Response): Promise<Response> {
  let body: unknown = { detail: "Authentication request failed." };
  try {
    body = await upstream.json();
  } catch {
    if (upstream.status >= 500) {
      body = { detail: "Authentication service is unavailable." };
    }
  }
  return Response.json(body, {
    status: upstream.status,
    headers: { "Cache-Control": "no-store" },
  });
}
