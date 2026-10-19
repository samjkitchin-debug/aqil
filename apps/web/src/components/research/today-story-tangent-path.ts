export const TODAY_STORY_QUERY_KEY = "from";
export const TODAY_STORY_QUERY_VALUE = "today";

export function researchStoryHrefFromToday(): string {
  const params = new URLSearchParams({
    [TODAY_STORY_QUERY_KEY]: TODAY_STORY_QUERY_VALUE,
  });
  return `/research?${params.toString()}`;
}

export function shouldShowReturnToToday(
  searchParams: Record<string, string | string[] | undefined>,
): boolean {
  const raw = searchParams[TODAY_STORY_QUERY_KEY];
  const value = Array.isArray(raw) ? raw[0] : raw;
  return value === TODAY_STORY_QUERY_VALUE;
}
