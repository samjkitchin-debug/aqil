import "server-only";

/**
 * Hosted Saxo tokens are read with the service role only after assertVaultOwner.
 * Authenticated and anon roles have no grant on saxo_token_vault.
 * The local file vault in sim-session.ts remains the default. This module does not replace it.
 */
export {
  assertVaultOwner,
  createMemoryVaultStore,
  openTokens,
  rotateHostedTokens,
  sealTokens,
  VaultOwnerError,
} from "./hosted-rotation.ts";
export type { VaultRow, VaultStore, VaultStatus } from "./hosted-rotation.ts";
