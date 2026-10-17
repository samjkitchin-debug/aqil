import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

import { isAllowlisted, parseAuthorisedUserIds } from "@/lib/auth/allowlist";
import { isPublicPath } from "@/lib/auth/paths";
import { safeNextPath } from "@/lib/auth/safe-next";

const PRIVATE_CACHE = "private, no-store, max-age=0";

function copyCookies(from: NextResponse, to: NextResponse) {
  from.cookies.getAll().forEach((cookie) => {
    to.cookies.set(cookie);
  });
}

function redirectTo(request: NextRequest, session: NextResponse, pathname: string, search: string) {
  const url = request.nextUrl.clone();
  url.pathname = pathname;
  url.search = search;
  const redirect = NextResponse.redirect(url);
  copyCookies(session, redirect);
  redirect.headers.set("Cache-Control", PRIVATE_CACHE);
  return redirect;
}

export async function proxy(request: NextRequest) {
  let session = NextResponse.next({ request });
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !anon) {
    if (isPublicPath(request.nextUrl.pathname)) return session;
    return redirectTo(request, session, "/login", "?error=unavailable");
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

  const { data, error } = await supabase.auth.getUser();
  const pathname = request.nextUrl.pathname;

  if (isPublicPath(pathname)) {
    session.headers.set("Cache-Control", PRIVATE_CACHE);
    return session;
  }

  if (error || !data.user) {
    const message = (error?.message ?? "").toLowerCase();
    const transport =
      error?.name === "AuthRetryableFetchError" ||
      message.includes("fetch") ||
      message.includes("network");
    const reason = transport ? "unavailable" : "signed_out";
    const next = safeNextPath(`${pathname}${request.nextUrl.search}`);
    return redirectTo(request, session, "/login", `?error=${reason}&next=${encodeURIComponent(next)}`);
  }

  const allowlist = parseAuthorisedUserIds(process.env.AQIL_AUTHORISED_USER_IDS);
  let permitted = isAllowlisted(data.user.id, allowlist);
  if (!permitted) {
    const grant = await supabase
      .from("access_grants")
      .select("role")
      .eq("user_id", data.user.id)
      .maybeSingle();
    if (grant.error) {
      const missing =
        grant.error.code === "42P01" ||
        grant.error.code === "PGRST205" ||
        grant.error.message.toLowerCase().includes("access_grants");
      if (!missing) {
        return redirectTo(request, session, "/login", "?error=unavailable");
      }
    } else if (grant.data?.role === "founder") {
      permitted = true;
    }
  }

  if (!permitted) {
    return redirectTo(request, session, "/access-denied", "");
  }

  session.headers.set("Cache-Control", PRIVATE_CACHE);
  return session;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
