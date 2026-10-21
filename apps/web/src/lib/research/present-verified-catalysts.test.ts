import assert from "node:assert/strict";
import test from "node:test";

import { upcomingCatalysts, type VerifiedCatalyst } from "./present-verified-catalysts.ts";

const now = new Date("2026-10-22T00:00:00Z");

const event: VerifiedCatalyst = {
  eventId: "event:verified:bls:ics:employment",
  title: "Employment Situation",
  scheduledAt: "2026-11-06T13:30:00.000Z",
  timezone: "America/New_York",
  status: "scheduled",
  sourceId: "bls_ics_schedule",
  sourceLocator: "https://www.bls.gov/schedule/news_release/bls.ics",
  lastVerifiedAt: "2026-10-22T04:00:00.000Z",
  datePrecision: "confirmed",
};

test("a confirmed future release is listed in Eastern Time", () => {
  const view = upcomingCatalysts([event], now);
  assert.equal(view.listed.length, 1);
  assert.equal(view.listed[0]?.providerLabel, "U.S. Bureau of Labor Statistics");
  assert.match(view.listed[0]?.scheduleLabel ?? "", /6 Nov 2026, 08:30 Eastern Time/);
  assert.match(view.listed[0]?.verifiedLabel ?? "", /22 Oct 2026, 04:00 UTC/);
});

test("an unconfirmed or past entry is not listed", () => {
  const view = upcomingCatalysts(
    [
      { ...event, datePrecision: "estimated" },
      { ...event, eventId: "past", scheduledAt: "2026-10-01T13:30:00.000Z" },
    ],
    now,
  );
  assert.equal(view.listed.length, 0);
});
