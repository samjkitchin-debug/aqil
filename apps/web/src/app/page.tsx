import { AppShell } from "@/components/app-shell";
import { PlaceholderPanel } from "@/components/placeholder-panel";

export default function TodayPage() {
  return (
    <AppShell title="Today">
      <PlaceholderPanel
        heading="Today"
        body="Your daily briefing will summarise verified macro context and portfolio-relevant themes. This screen is a layout placeholder."
      />
    </AppShell>
  );
}
