import { forwardAuth, isSameOrigin, writeSession } from "@/lib/auth-bff";

export async function POST(request: Request): Promise<Response> {
  if (!isSameOrigin(request)) {
    return Response.json({ detail: "Cross-origin request rejected." }, { status: 403 });
  }
  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return Response.json({ detail: "Request body must be valid JSON." }, { status: 400 });
  }
  return writeSession(
    await forwardAuth("/auth/login", payload, undefined, "POST", request.headers.get("x-forwarded-for") ?? undefined),
  );
}
