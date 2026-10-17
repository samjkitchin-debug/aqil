import { resolveAccess } from "@/lib/auth/access";
import { signOut } from "@/lib/auth/actions";

export async function SignOutControl() {
  const access = await resolveAccess();
  if (access.status !== "authorised" && access.status !== "unauthorised") return null;
  return (
    <form action={signOut}>
      <button type="submit" className="text-sm text-muted underline">
        Sign out
      </button>
    </form>
  );
}
