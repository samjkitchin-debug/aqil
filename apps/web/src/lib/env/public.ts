/**
 * Browser-safe configuration only. Never import server secrets here.
 */

export type PublicEnvKey =
  | "NEXT_PUBLIC_SUPABASE_URL"
  | "NEXT_PUBLIC_SUPABASE_ANON_KEY"
  | "NEXT_PUBLIC_APP_URL";

export function getPublicEnv(name: PublicEnvKey): string | undefined {
  return process.env[name];
}

export function requirePublicEnv(name: PublicEnvKey): string {
  const value = getPublicEnv(name);
  if (!value) {
    throw new Error(
      `Missing public environment variable: ${name}. Copy apps/web/.env.example to apps/web/.env.local.`,
    );
  }
  return value;
}

export function isSupabaseConfigured(): boolean {
  return Boolean(
    getPublicEnv("NEXT_PUBLIC_SUPABASE_URL") &&
      getPublicEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY"),
  );
}
