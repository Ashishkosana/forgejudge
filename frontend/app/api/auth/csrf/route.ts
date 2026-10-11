import { issueCsrfToken } from "@/lib/auth-bff";

export async function GET(): Promise<Response> {
  const csrfToken = await issueCsrfToken();
  return Response.json(
    { csrf_token: csrfToken },
    { headers: { "Cache-Control": "no-store" } },
  );
}
