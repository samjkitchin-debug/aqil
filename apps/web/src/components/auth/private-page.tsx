import { redirect } from "next/navigation";

import { resolveAccess } from "@/lib/auth/access";

type Props = {
  nextPath: string;
  children: React.ReactNode;
};

export async function PrivatePage({ nextPath, children }: Props) {
  const access = await resolveAccess();
  if (access.status === "signed_out") {
    redirect(`/login?next=${encodeURIComponent(nextPath)}`);
  }
  if (access.status === "unauthorised") {
    redirect("/access-denied");
  }
  if (access.status === "unavailable") {
    return (
      <p className="research-body" data-testid="auth-unavailable">
        Aqil could not verify your session. Private research and portfolio data are not shown when
        authentication is unavailable.
      </p>
    );
  }
  return children;
}
