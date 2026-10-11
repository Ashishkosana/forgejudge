import { forwardAuth, hasValidCsrfProof, writeSession } from "@/lib/auth-bff";

export async function POST(request: Request): Promise<Response> {
  if (!(await hasValidCsrfProof(request))) {
    return Response.json({ detail: "Invalid CSRF proof." }, { status: 403 });
  }
  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return Response.json({ detail: "Request body must be valid JSON." }, { status: 400 });
  }
  return writeSession(
    await forwardAuth("/auth/register", payload, undefined, "POST", request.headers.get("x-forwarded-for") ?? undefined),
  );
}
