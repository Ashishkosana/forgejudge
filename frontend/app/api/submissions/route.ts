const apiBase = (process.env.API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

export async function POST(request: Request): Promise<Response> {
  const contentLength = Number(request.headers.get("content-length") ?? 0);
  if (contentLength > 150_000) {
    return Response.json({ detail: "Submission payload is too large." }, { status: 413 });
  }

  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return Response.json({ detail: "Request body must be valid JSON." }, { status: 400 });
  }

  try {
    const upstream = await fetch(`${apiBase}/submissions`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
    });
    const body = await upstream.text();
    return new Response(body, {
      status: upstream.status,
      headers: { "content-type": upstream.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return Response.json({ detail: "Submission API is unavailable." }, { status: 503 });
  }
}
