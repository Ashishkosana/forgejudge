import {
  clearSession,
  forwardAuth,
  isSameOrigin,
  readRefreshToken,
  writeSession,
} from "@/lib/auth-bff";

export async function POST(request: Request): Promise<Response> {
  if (!isSameOrigin(request)) {
    return Response.json({ detail: "Cross-origin request rejected." }, { status: 403 });
  }
  const refreshToken = await readRefreshToken();
  if (!refreshToken) {
    await clearSession();
    return Response.json({ detail: "Not authenticated." }, { status: 401 });
  }
  const result = await writeSession(
    await forwardAuth("/auth/refresh", { refresh_token: refreshToken }),
  );
  if (result.status === 401) await clearSession();
  return result;
}
