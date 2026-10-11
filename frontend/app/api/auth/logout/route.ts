import {
  clearSession,
  forwardAuth,
  hasValidCsrfProof,
  readRefreshToken,
} from "@/lib/auth-bff";

export async function POST(request: Request): Promise<Response> {
  if (!(await hasValidCsrfProof(request))) {
    return Response.json({ detail: "Invalid CSRF proof." }, { status: 403 });
  }
  const refreshToken = await readRefreshToken();
  let upstream: Response | undefined;
  if (refreshToken) {
    upstream = await forwardAuth("/auth/logout", { refresh_token: refreshToken });
  }
  await clearSession();
  if (upstream && !upstream.ok) return upstream;
  return new Response(null, { status: 204 });
}
