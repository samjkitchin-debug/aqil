import { redirect } from "next/navigation";

import { resolveAccess } from "@/lib/auth/access";

export default async function AccessDeniedPage() {
  const access = await resolveAccess();
  if (access.status === "authenticated_authorised") {
    redirect("/");
  }
  const reason =
    access.status === "terminal_invalid_session"
      ? "session_ended"
      : access.status === "temporarily_unavailable"
        ? "unavailable"
        : "signed_out";
  redirect(`/login?error=${reason}`);
}
