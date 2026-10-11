import {
  clearSession,
  forwardAuth,
  isSameOrigin,
  readAccessToken,
  relayError,
} from "@/lib/auth-bff";

export async function POST(request: Request): Promise<Response> {
  if (!isSameOrigin(request)) {
    return Response.json({ detail: "Cross-origin request rejected." }, { status: 403 });
  }
  const accessToken = await readAccessToken();
  if (!accessToken) {
    await clearSession();
    return Response.json({ detail: "Not authenticated." }, { status: 401 });
  }
  const upstream = await forwardAuth("/auth/logout-all", undefined, accessToken, "POST");
  if (!upstream.ok) return relayError(upstream);
  await clearSession();
  return new Response(null, { status: 204 });
}
