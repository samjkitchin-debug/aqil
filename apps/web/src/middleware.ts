import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const FOUNDER_COOKIE = "aqil_founder_insight";
const FOUNDER_HEADER = "x-aqil-founder-insight";

export function middleware(request: NextRequest) {
  const token = process.env.AQIL_FOUNDER_INSIGHT_TOKEN?.trim();
  if (
    process.env.AQIL_ALLOW_FOUNDER_INSIGHT_HEADER !== "true" ||
    !token ||
    request.headers.get(FOUNDER_HEADER) !== token
  ) {
    return NextResponse.next();
  }

  const response = NextResponse.next();
  response.cookies.set(FOUNDER_COOKIE, token, {
    path: "/",
    httpOnly: true,
    sameSite: "lax",
    secure: false,
  });
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
