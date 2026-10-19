import { StatusLine } from "@/components/ui/status-line";

import { ResearchStoryDepthPanel } from "@/components/research/research-story-depth-panel";
import { getSyntheticResearchStory } from "@/lib/research/story";

export function ResearchStoryView() {
  const story = getSyntheticResearchStory();

  return (
    <>
      <StatusLine tone="limitation">{story.label}</StatusLine>
      <ResearchStoryDepthPanel story={story} />
    </>
  );
}
