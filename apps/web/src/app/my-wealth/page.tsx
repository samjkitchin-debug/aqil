import { AppShell } from "@/components/app-shell";
import { PlaceholderPanel } from "@/components/placeholder-panel";

export default function MyWealthPage() {
  return (
    <AppShell title="My wealth">
      <PlaceholderPanel
        heading="My wealth"
        body="Goals, holdings and progress tracking will appear here after secure account and data integrations are configured."
      />
    </AppShell>
  );
}
