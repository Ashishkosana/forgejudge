import { forwardAuth, readAccessToken, relayError } from "@/lib/auth-bff";

export async function GET(): Promise<Response> {
  const accessToken = await readAccessToken();
  if (!accessToken) {
    return Response.json({ detail: "Not authenticated." }, { status: 401 });
  }
  const upstream = await forwardAuth("/auth/me", undefined, accessToken);
  if (!upstream.ok) return relayError(upstream);
  return new Response(await upstream.text(), {
    status: upstream.status,
    headers: {
      "content-type": upstream.headers.get("content-type") ?? "application/json",
      "Cache-Control": "no-store",
    },
  });
}
