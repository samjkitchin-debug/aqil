import { AppShell } from "@/components/app-shell";
import { PlaceholderPanel } from "@/components/placeholder-panel";

export default function ExplorePage() {
  return (
    <AppShell title="Explore">
      <PlaceholderPanel
        heading="Explore"
        body="Browse investment themes, regions and asset classes once the research catalogue is connected."
      />
    </AppShell>
  );
}
