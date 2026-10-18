import { signOut } from "@/lib/auth/actions";

export function SignOutControl() {
  return (
    <form action={signOut}>
      <button type="submit" className="text-sm text-muted underline">
        Sign out
      </button>
    </form>
  );
}
