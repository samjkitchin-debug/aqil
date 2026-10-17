import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

import { isAllowlisted, parseAuthorisedUserIds } from "@/lib/auth/allowlist";
import { isPublicPath } from "@/lib/auth/paths";
import { safeNextPath } from "@/lib/auth/safe-next";
import {
  classifyAuthFailure,
  hasAuthSessionCookie,
  isPrefetchRequest,
  shouldContactAuthServer,
} from "@/lib/auth/session-policy";

function copyCookies(from: NextResponse, to: NextResponse) {
  from.cookies.getAll().forEach((cookie) => {
    to.cookies.set(cookie);
  });
}

function clearLocalAuthCookies(request: NextRequest, response: NextResponse) {
  for (const cookie of request.cookies.getAll()) {
    if (cookie.name.startsWith("sb-") && cookie.name.includes("-auth-token")) {
      response.cookies.set(cookie.name, "", { path: "/", maxAge: 0 });
    }
  }
}

function redirectTo(request: NextRequest, session: NextResponse, pathname: string, search: string) {
  const url = request.nextUrl.clone();
  url.pathname = pathname;
  url.search = search;
  const redirect = NextResponse.redirect(url);
  copyCookies(session, redirect);
  return redirect;
}

export async function proxy(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  const isPublic = isPublicPath(pathname);

  if (isPrefetchRequest(request.headers) && !isPublic) {
    return new NextResponse(null, { status: 204 });
  }

  let session = NextResponse.next({ request });
  if (!shouldContactAuthServer(isPublic)) {
    return session;
  }

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  const next = safeNextPath(`${pathname}${request.nextUrl.search}`);
  if (!url || !anon) {
    return redirectTo(request, session, "/login", `?error=unavailable&next=${encodeURIComponent(next)}`);
  }
  if (!hasAuthSessionCookie(request.cookies.getAll().map((cookie) => cookie.name))) {
    return redirectTo(request, session, "/login", `?error=signed_out&next=${encodeURIComponent(next)}`);
  }

  const supabase = createServerClient(url, anon, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
        session = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) => {
          session.cookies.set(name, value, options);
        });
      },
    },
  });

  // getUser() calls the Auth user endpoint. The installed SDK refreshes the
  // access token only when it is inside the expiry margin, then setAll copies
  // those cookies onto this request for the server render. This is not a second
  // refresh by itself, and it does not publish an identity header.
  const { data, error } = await supabase.auth.getUser();
  if (error || !data.user) {
    const status = classifyAuthFailure(error);
    const reason =
      status === "temporarily_unavailable"
        ? "unavailable"
        : status === "terminal_invalid_session"
          ? "session_ended"
          : "signed_out";
    const redirect = redirectTo(request, session, "/login", `?error=${reason}&next=${encodeURIComponent(next)}`);
    if (status === "terminal_invalid_session") {
      clearLocalAuthCookies(request, redirect);
    }
    return redirect;
  }

  const allowlist = parseAuthorisedUserIds(process.env.AQIL_AUTHORISED_USER_IDS);
  let permitted = isAllowlisted(data.user.id, allowlist);
  if (!permitted) {
    const grant = await supabase.from("access_grants").select("role").eq("user_id", data.user.id).maybeSingle();
    if (grant.error) {
      const missing =
        grant.error.code === "42P01" ||
        grant.error.code === "PGRST205" ||
        grant.error.message.toLowerCase().includes("access_grants");
      if (!missing) {
        return redirectTo(request, session, "/login", `?error=unavailable&next=${encodeURIComponent(next)}`);
      }
    } else if (grant.data?.role === "founder") {
      permitted = true;
    }
  }

  if (!permitted) {
    return redirectTo(request, session, "/access-denied", "");
  }

  return session;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
