import { redirect } from "next/navigation";

import { resolveAccess } from "@/lib/auth/access";

type Props = {
  nextPath: string;
  children: React.ReactNode;
};

export async function PrivatePage({ nextPath, children }: Props) {
  const access = await resolveAccess();
  if (access.status === "signed_out" || access.status === "terminal_invalid_session") {
    const reason = access.status === "terminal_invalid_session" ? "session_ended" : "signed_out";
    redirect(`/login?error=${reason}&next=${encodeURIComponent(nextPath)}`);
  }
  if (access.status === "temporarily_unavailable") {
    return (
      <p className="research-body" data-testid="auth-unavailable">
        Aqil could not verify your session. Private research and portfolio data are not shown, and
        your session has not been cleared.
      </p>
    );
  }
  return children;
}
