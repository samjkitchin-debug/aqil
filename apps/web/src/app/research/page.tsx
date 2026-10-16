import { AppShell } from "@/components/app-shell";
import { PlaceholderPanel } from "@/components/placeholder-panel";

export default function ResearchPage() {
  return (
    <AppShell title="Research">
      <PlaceholderPanel
        heading="Research"
        body="The Python research worker will publish reproducible analyses here. No automated recommendations are shown during initialisation."
      />
    </AppShell>
  );
}
