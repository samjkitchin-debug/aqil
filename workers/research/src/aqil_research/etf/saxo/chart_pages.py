"""Plan the next Chart V3 page. This module does not call Saxo or store a bar.

A count of 1200 is one window. It is not the full history. The latest sample
may still be the open session. A chart close is not a last trade.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ChartWindow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: int
    count: int
    earliest: str | None
    latest: str | None
    first_sample_time: str | None
    data_version: int | None = None


class PagePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: str | None
    time: str | None
    reached_first_sample: bool
    older_page_refused: bool
    latest_may_be_open: bool
    note: str


def plan_older_page(window: ChartWindow, *, today: str) -> PagePlan:
    """Decide whether Mode=UpTo can ask for samples before this window.

    ``today`` is the session date being read, YYYY-MM-DD. The latest bar on
    that date is not treated as a completed close.
    """

    latest_day = (window.latest or "")[:10]
    open_session = bool(latest_day) and latest_day == today
    if window.status != 200:
        return PagePlan(
            mode=None,
            time=None,
            reached_first_sample=False,
            older_page_refused=True,
            latest_may_be_open=open_session,
            note=f"The chart request returned HTTP {window.status}. No older page was requested.",
        )
    if window.count <= 0 or not window.earliest:
        return PagePlan(
            mode=None,
            time=None,
            reached_first_sample=False,
            older_page_refused=True,
            latest_may_be_open=open_session,
            note="The chart page contained no samples. No older page was requested.",
        )
    if window.first_sample_time and window.earliest <= window.first_sample_time:
        return PagePlan(
            mode=None,
            time=None,
            reached_first_sample=True,
            older_page_refused=False,
            latest_may_be_open=open_session,
            note=(
                "The earliest sample matches ChartInfo.FirstSampleTime. "
                "No older page was refused. This is not a cited inception."
            ),
        )
    return PagePlan(
        mode="UpTo",
        time=window.earliest,
        reached_first_sample=False,
        older_page_refused=False,
        latest_may_be_open=open_session,
        note=(
            "Another page uses Mode=UpTo at the earliest sample. "
            "1200 bars is not the full history."
        ),
    )
