# ADR-0001: Use the classic ADK agent API, not the 2.x graph Workflow API

**Status:** Accepted. The pinned version has not yet been verified against an
install (README open item 6).

## Context

ADK 2.0 (GA May 2026) introduced a graph-based Workflow Runtime in which `BaseAgent`
subclasses `BaseNode`. `SequentialAgent`, `LoopAgent`, and `ParallelAgent` are marked
deprecated in favor of graph Workflows, but the official migration guide states they
continue to work and that no immediate action is required. No removal date has been
announced.

Our pipeline needs a nested structure: a top-level sequence containing a revision loop.

## Decision

Build on the classic API: `SequentialAgent`, `LoopAgent`, and `AgentTool`. Pin
`google-adk~=2.9` in `requirements.txt`.

## Rationale

- `google/adk-python` issue #5872 confirms a `Workflow` is a `BaseNode`, not a
  `BaseAgent`, so it cannot be nested as a sub-agent. Our design requires exactly that
  nesting. The issue was closed without a linked fix and there is no committed ETA.
- The "Workflow as Tool" workaround (2.4.0+) changes invocation semantics from a
  deterministic pipeline step to an LLM-decided tool call, which is not what we want for
  a fixed research sequence.
- Deprecation is warning-only, and the 15-week project ends well inside any plausible
  removal window. Pinning the version removes the risk entirely.
- Google's own `adk-samples` deep-research agent is built on the classic API in exactly
  this shape.

## Consequences

- One-time deprecation warnings appear in logs. Acceptable; documented here so reviewers
  aren't surprised.
- We do not get graph-native features (durable orchestration, pause/resume HITL). None
  are required by the project scope.
- If the project later needs those features, revisit once #5872's composition gap is
  resolved. That would be a new ADR superseding this one.
- If an install check shows 2.9.x misbehaves, the fallback is pinning the
  1.x line (1.39.1, Aug 2026, still maintained). That would supersede this ADR.
