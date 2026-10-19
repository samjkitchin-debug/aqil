import Link from "next/link";

import { StatusLine } from "@/components/ui/status-line";
import { SYNTHETIC_STORY_BANNER } from "@/lib/research/story";

import { researchStoryHrefFromToday } from "@/components/research/today-story-tangent-path";

export { shouldShowReturnToToday } from "@/components/research/today-story-tangent-path";

export function TodaySyntheticStoryTangentLink() {
  return (
    <div className="mt-[var(--space-4)]" data-testid="today-synthetic-story-tangent">
      <StatusLine tone="limitation">{SYNTHETIC_STORY_BANNER}</StatusLine>
      <p className="research-meta">
        <Link href={researchStoryHrefFromToday()} data-testid="today-synthetic-story-link">
          Open the layered synthetic story
        </Link>
      </p>
    </div>
  );
}

export function ReturnToTodayFromStoryLink() {
  return (
    <p className="research-meta mb-[var(--space-4)]" data-testid="return-to-today-link">
      <Link href="/">Back to Today</Link>
    </p>
  );
}
