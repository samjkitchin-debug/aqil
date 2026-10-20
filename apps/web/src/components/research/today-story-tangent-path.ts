export const DEV_STORY_PATH = "/dev/story";

export function researchStoryHrefFromToday(): string {
  return DEV_STORY_PATH;
}

/** Legacy query param — story now lives on /dev/story. */
export function shouldShowReturnToToday(
  _searchParams: Record<string, string | string[] | undefined>,
): boolean {
  return false;
}
