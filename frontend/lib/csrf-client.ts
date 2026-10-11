export async function csrfHeaders(): Promise<Record<string, string>> {
  const response = await fetch("/api/auth/csrf", { cache: "no-store" });
  if (!response.ok) throw new Error("Unable to prepare a secure request.");
  const result = (await response.json()) as { csrf_token?: string };
  if (!result.csrf_token) throw new Error("Unable to prepare a secure request.");
  return { "X-ForgeJudge-CSRF": result.csrf_token };
}
