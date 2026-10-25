const PUBLIC_EXACT = new Set(["/login", "/access-denied", "/privacy", "/tos", "/manifest.webmanifest", "/favicon.ico"]);

export function isPublicPath(pathname: string): boolean {
  if (pathname.startsWith("/_next")) return true;
  if (pathname.startsWith("/icons/")) return true;
  if (PUBLIC_EXACT.has(pathname)) return true;
  return pathname.startsWith("/auth/");
}
