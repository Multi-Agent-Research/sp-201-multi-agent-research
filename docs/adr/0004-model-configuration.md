# ADR-0004: Model ID is configuration, never hardcoded

**Status:** Accepted. The current target is gemini-2.5-flash, which has no announced
shutdown date as of 2026-10-18.
Two corrections to the text below. The retirement date in Context is wrong:
gemini-2.0-flash shutdown is 2026-06-01 per Google's deprecations page
(https://ai.google.dev/gemini-api/docs/deprecations), not March 3, 2026. And the
configuration variable is named SP201_MODEL_ID in this repo, not GEMINI_MODEL.

## Context

The project brief instructs students to use `gemini-1.5-flash` or `gemini-2.0-flash`.
`gemini-2.0-flash` was deprecated and retired on March 3, 2026; `gemini-1.5-flash` is
legacy. Google rotates model IDs and retires them on a rolling basis, and our team
already identified mid-semester model retirement as a project risk.

## Decision

A single `GEMINI_MODEL` value in `.env` is read once into config and used by every
agent. No agent constructor contains a literal model string. Per-agent tier assignment
(Flash vs. Flash-Lite) is a separate config value, not a hardcoded choice.

## Rationale

- Turns a mid-semester model retirement from a code change across four agents into a
  one-line edit plus an `adk eval` re-run.
- The brief's named models are already stale, which demonstrates the risk is real rather
  than theoretical.
- ADK 2.x also supports automatic failover to backup models, which this pattern makes
  straightforward to add.

## Consequences

- Requires verifying the current free-tier model ID before the first run, and recording
  the RPM / TPM / RPD limits in architecture.md section 9.
- Worth flagging to the project owner that the brief's model guidance is out of date.
- Evaluation results are only comparable within a single model; re-run the evalset after
  any model change and note which model produced which numbers.
