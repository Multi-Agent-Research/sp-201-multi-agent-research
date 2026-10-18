# ADR-0005: Bounded revision loop; unsupported claims are flagged, not dropped

**Status:** SUPERSEDED IN PART by the SRS and SDD 3.6 (Sept 20, 2026). ADR-0007 pending.
Three things below did not survive: the loop ordering (Fact-Checker first is NOT the
approved design; the Synthesizer runs first inside the loop); the "one targeted
re-search" for an unsupportable claim (3.5.5 bars the Fact-Checker from retrieving,
3.4.4 bars the Synthesizer, and 3.6.3 bars any worker from invoking Search, so no
component can perform it); and exit condition 3, "no improvement between iterations"
(`should_escalate` is pass-only). What survives: the bounded loop with
`max_iterations` = 2, and flagging rather than silently dropping an unsupportable claim.

## Context

The Fact-Checker and Synthesizer form a generator-critic loop. Unbounded, it can spin:
each revision is a model call, and a claim with no supporting evidence will never become
supported no matter how many times it is rewritten. Free-tier quota and demo runtime both
punish this.

We also need a policy for what happens to a claim the evidence cannot support.

## Decision

> SUPERSEDED: the ordering in this paragraph was reversed by SDD 3.6. The approved
> order is Synthesizer, Fact-Checker, EscalationChecker. See README, "Why the
> Synthesizer is inside the loop".

`LoopAgent` with `max_iterations` set (2 to start), Fact-Checker ordered **first** so it
can exit before a wasted revision when the draft already passes. Exit conditions:

1. All atomic claims are supported: set `EventActions(escalate=True)` and exit.
2. `max_iterations` is reached: finalize.
3. No improvement between iterations: stop.

For an unsupportable claim: one targeted re-search, then flag as `[unverified]` in the
output. Never silently drop, and never let the Synthesizer defend a claim with no
evidence behind it.

## Rationale

- Forgetting `max_iterations` is the most commonly cited `LoopAgent` failure.
- Checker-first ordering saves a model call on every draft that already passes.
- Silent dropping hides the system's failure mode from the reader, which defeats the
  purpose of a fact-checking pipeline. Visible flags are both more honest and a better
  demo, since they show the checker working.
- Letting the Synthesizer argue for an unsupported claim reintroduces exactly the
  hallucination the architecture exists to catch.

## Consequences

- Some outputs ship with `[unverified]` markers. This is intended behavior, not a defect,
  and should be stated in the final report and the demo narration.
- The verdicts table becomes part of the user-facing output, not just internal state.
- `max_iterations` should be tuned against measured per-query call counts once the
  skeleton runs. How unsupported claims are *presented* to the reader is settled by
  requirements 3.6.5 and 3.6.7.
