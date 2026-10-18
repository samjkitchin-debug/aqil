import { signOut } from "@/lib/auth/actions";

export function SignOutControl() {
  return (
    <form action={signOut} className="aq-header-account">
      <button type="submit" className="aq-header-action">
        Sign out
      </button>
    </form>
  );
}
