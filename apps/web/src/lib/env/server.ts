import "server-only";

/**
 * Server-only secrets and configuration. Never import this module from client components.
 */

export function getServiceRoleKey(): string | undefined {
  return process.env.SUPABASE_SERVICE_ROLE_KEY;
}

export function requireServiceRoleKey(): string {
  const value = getServiceRoleKey();
  if (!value) {
    throw new Error(
      "Missing SUPABASE_SERVICE_ROLE_KEY. Set it only in server-side environment files.",
    );
  }
  return value;
}
