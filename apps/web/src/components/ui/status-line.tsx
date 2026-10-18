import type { ReactNode } from "react";

export type StatusTone = "meta" | "limitation" | "simulation";

type StatusLineProps = {
  tone: StatusTone;
  children: ReactNode;
};

/**
 * Three tones only.
 * meta: dated facts and sources.
 * limitation: unavailable, stale, estimated, unverified or demonstration.
 * simulation: this block is not the investor's live wealth. Do not wrap a mixed portfolio in it.
 */
export function StatusLine({ tone, children }: StatusLineProps) {
  return <p className={`aq-status aq-status--${tone}`}>{children}</p>;
}
