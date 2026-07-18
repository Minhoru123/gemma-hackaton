# Backlog

Deferred items David asked to be reminded about. Neither is being fixed yet —
pick these up in a future session.

## 1. Watchdog over-triggers on opposing merits arguments

Observed 2026-07-18 while re-ingesting `State Defendants Motion to Dismiss.pdf`:
the fault scanner flagged two of the State's ordinary merits arguments
("Plaintiff's First Claim fails to state a claim…") as lawyer-error faults, one
miscategorized as `discovery-failure`. These landed on the ask-your-attorney
list as noise.

The watchdog (`app/case_events.py`, `faults` in `_PROMPT`) should flag
*procedural* failures (missed deadlines, waiver, non-appearance, unanswered
discovery, sanctions) — not an opposing brief's legal-merits contentions.

Fix ideas, in rough order of preference:
- Tighten the fault prompt: require a *procedural* failure that already
  happened; explicitly exclude merits arguments ("fails to state a claim",
  "does not violate", sufficiency-of-pleading language).
- Only run fault detection on court-issued documents (order/notice); treat
  accusations inside opposing briefs as adversarial intelligence, not faults.
- Add a deterministic merits-phrase filter on returned quotes as a backstop.

## 2. Stale presumptive deadlines from old filings

Observed 2026-07-18: the same MTD (filed 2025-04-12) generated a presumptive
"File opposition" obligation due 2025-04-26 — displayed as OVERDUE more than a
year later, even though that briefing is long complete. Any historical filing
uploaded for record purposes will produce this noise.

Relevant code: `app/deadlines.py` (`apply`), `app/obligations.py` (`warnings`).

Fix ideas:
- Skip (or create as already-satisfied/"historical") deadline triggers when
  `filed_date` is older than a configurable window (e.g. 30 days) — likely a
  `config.py` setting like `DEADLINE_TRIGGER_MAX_AGE_DAYS`.
- Or surface a distinct "historical" urgency instead of "overdue" so old
  uploads don't look like emergencies.
- Or have the upload response ask the user whether the triggered obligation is
  still live.

Until fixed: click "Done" on stale warnings in the UI.
