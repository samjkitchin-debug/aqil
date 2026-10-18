import { parseSaxoTokenResponse, saxoEndpoints, type SaxoEnvironment, type SaxoTokens } from "./sim-guard.ts";

type FetchLike = (input: string, init: { method: string; headers: Record<string, string>; body: string }) => Promise<{
  ok: boolean;
  status: number;
  json: () => Promise<unknown>;
}>;

export async function requestSaxoToken(
  input: {
    grant: "authorization_code" | "refresh_token";
    environment?: SaxoEnvironment;
    code?: string;
    refreshToken?: string;
    appKey: string;
    appSecret: string;
    redirectUri: string;
  },
  fetchImpl: FetchLike,
): Promise<{ ok: true; tokens: SaxoTokens } | { ok: false; status: number }> {
  const body = new URLSearchParams({ grant_type: input.grant, redirect_uri: input.redirectUri });
  if (input.grant === "authorization_code") {
    if (!input.code) return { ok: false, status: 0 };
    body.set("code", input.code);
  } else {
    if (!input.refreshToken) return { ok: false, status: 0 };
    body.set("refresh_token", input.refreshToken);
  }
  const basic = Buffer.from(`${input.appKey}:${input.appSecret}`, "utf8").toString("base64");
  let response: { ok: boolean; status: number; json: () => Promise<unknown> };
  try {
    response = await fetchImpl(saxoEndpoints(input.environment ?? "simulation").tokenUrl, {
      method: "POST",
      headers: {
        authorization: `Basic ${basic}`,
        "content-type": "application/x-www-form-urlencoded",
      },
      body: body.toString(),
    });
  } catch {
    return { ok: false, status: 0 };
  }
  if (!response.ok) return { ok: false, status: response.status };
  try {
    const tokens = parseSaxoTokenResponse(await response.json());
    if (!tokens) return { ok: false, status: response.status };
    return { ok: true, tokens };
  } catch {
    return { ok: false, status: response.status };
  }
}
