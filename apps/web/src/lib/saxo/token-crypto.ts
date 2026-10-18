import { createCipheriv, createDecipheriv, randomBytes } from "node:crypto";

export function saxoEncryptionKey(encoded: string | undefined): Buffer | null {
  if (!encoded) return null;
  const trimmed = encoded.trim();
  const key = /^[0-9a-fA-F]{64}$/.test(trimmed) ? Buffer.from(trimmed, "hex") : Buffer.from(trimmed, "base64");
  return key.length === 32 ? key : null;
}

/** AES-256-GCM. The result contains no key material. */
export function encryptJson(value: unknown, key: Buffer): string {
  const nonce = randomBytes(12);
  const cipher = createCipheriv("aes-256-gcm", key, nonce);
  const ciphertext = Buffer.concat([
    cipher.update(Buffer.from(JSON.stringify(value), "utf8")),
    cipher.final(),
    cipher.getAuthTag(),
  ]);
  return `v1.${nonce.toString("base64url")}.${ciphertext.toString("base64url")}`;
}

export function decryptJson(payload: string, key: Buffer): unknown | null {
  const [version, noncePart, bodyPart] = payload.split(".");
  if (version !== "v1" || !noncePart || !bodyPart) return null;
  try {
    const nonce = Buffer.from(noncePart, "base64url");
    const body = Buffer.from(bodyPart, "base64url");
    if (nonce.length !== 12 || body.length < 16) return null;
    const tag = body.subarray(body.length - 16);
    const ciphertext = body.subarray(0, body.length - 16);
    const decipher = createDecipheriv("aes-256-gcm", key, nonce);
    decipher.setAuthTag(tag);
    const plain = Buffer.concat([decipher.update(ciphertext), decipher.final()]).toString("utf8");
    return JSON.parse(plain) as unknown;
  } catch {
    return null;
  }
}
