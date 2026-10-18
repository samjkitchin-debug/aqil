/** Same-origin relative path only. Rejects open redirects. */
export function safeNextPath(value: string | null | undefined): string {
  if (!value) return "/";
  if (!value.startsWith("/")) return "/";
  if (value.startsWith("//") || value.startsWith("/\\")) return "/";
  if (value.includes("\\") || value.includes("://") || value.includes("\0")) return "/";
  if (value.startsWith("/login") || value.startsWith("/auth/")) return "/";
  return value;
}
