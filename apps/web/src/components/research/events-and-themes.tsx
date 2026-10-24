import Link from "next/link";

import { loadMacroIntelligence } from "@/lib/research/load-macro-events";
import {
  presentMacroIntelligence,
  type PresentedIntelligence,
} from "@/lib/research/present-macro-events";

type Variant = "today" | "compact" | "evidence";

export async function EventsAndThemesSection({ variant }: { variant: Variant }) {
  const loaded = await loadMacroIntelligence();
  if (loaded.status === "unavailable") {
    return <p className="research-body">{loaded.reason}</p>;
  }
  const events = loaded.status === "ok" ? loaded.events : [];
  const themes = loaded.status === "ok" ? loaded.themes : [];
  const view = presentMacroIntelligence(events, themes, variant, new Date());
  return <EventsAndThemesView view={view} variant={variant} />;
}

export function EventsAndThemesView({
  view,
  variant,
}: {
  view: PresentedIntelligence;
  variant: Variant;
}) {
  return (
    <section aria-labelledby={`${variant}-events-heading`} data-testid={`events-${variant}`}>
      <h2 id={`${variant}-events-heading`} className="research-section-title">
        {view.title}
      </h2>
      <p className="research-meta">{view.awareness}</p>
      {view.empty ? <p className="research-body">{view.empty}</p> : null}
      {view.events.map((event) => (
        <article key={event.eventKey} className="research-banner">
          {variant === "today" && event.reason ? (
            <p className="research-body">{event.reason}</p>
          ) : (
            <p className="research-body">{event.summary}</p>
          )}
          {variant !== "today" ? (
            <p className="research-meta">
              {event.epistemicClass}. {event.claimScope}.
            </p>
          ) : null}
          <p className="research-meta">
            Event date {event.eventDate}. Dates stated: {event.datesStated}. Published{" "}
            {event.publishedDate}.
          </p>
          <p className="research-meta">
            Source:{" "}
            {event.sourceUrl ? (
              <a href={event.sourceUrl} rel="noopener noreferrer" target="_blank">
                {event.sourceLabel}
              </a>
            ) : (
              event.sourceLabel
            )}
          </p>
          {variant === "evidence" && event.primaryTitle ? (
            <p className="research-body">Primary source: {event.primaryTitle}.</p>
          ) : null}
          {variant === "evidence" ? (
            <p className="research-meta">
              {event.later.length > 0
                ? `Later evidence: ${event.later.join("; ")}.`
                : "No later evidence is stored."}
            </p>
          ) : null}
          {variant === "evidence" && event.conflicting.length > 0 ? (
            <p className="research-body">Conflicting evidence: {event.conflicting.join("; ")}.</p>
          ) : null}
          {event.channels.length > 0 ? (
            <p className="research-meta">
              {event.channels.map((channel) => (
                <Link key={channel.sourceId} href={channel.href} prefetch={false}>
                  {channel.label}
                </Link>
              ))}
            </p>
          ) : null}
        </article>
      ))}
      {view.themes.map((theme) => (
        <article key={theme.assessmentId} className="research-banner">
          {theme.supersededLine ? <p className="research-meta">{theme.supersededLine}</p> : null}
          <h3 className="research-section-title">What the filing establishes</h3>
          <p className="research-body">{theme.establishes}</p>
          <h3 className="research-section-title">What the filing does not establish</h3>
          {theme.doesNot.map((line) => (
            <p key={line} className="research-body">
              {line}
            </p>
          ))}
          {theme.dimensions.map((dimension) => (
            <div key={dimension.label}>
              <h3 className="research-section-title">{dimension.label}</h3>
              <p className="research-body">{dimension.statusLine}</p>
              <p className="research-meta">{dimension.measureLine}</p>
              <p className="research-body">{dimension.explanation}</p>
              {dimension.amountLine ? (
                <p className="research-meta">{dimension.amountLine}</p>
              ) : null}
            </div>
          ))}
        </article>
      ))}
    </section>
  );
}
