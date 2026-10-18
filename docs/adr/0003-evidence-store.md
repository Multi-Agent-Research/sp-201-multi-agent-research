# ADR-0003: Store evidence externally; session state carries IDs only

**Status:** Accepted

## Context

The Search Agent accumulates a growing body of retrieved evidence, potentially many
results per query, each with long snippets and source metadata. Every downstream agent
needs access to it. The obvious place to put it is `session.state`, since that is ADK's
built-in coordination mechanism.

## Decision

Evidence bodies live in an external store (SQLite, keyed by stable evidence IDs).
`session.state` carries only `evidence_index` (a list of IDs) plus short spans where an
agent needs inline context.

## Rationale

- ADK documentation explicitly warns that session state is not optimized for large
  amounts of data and is text-oriented.
- Evidence grows unboundedly with query complexity; state does not degrade gracefully
  under that.
- An external store is inspectable and diffable, which matters for the demo and for
  debugging why a claim was or wasn't supported.
- Caching evidence on disk enables an offline demo mode if search sources block us on
  presentation day.

## Consequences

- One extra component to build and maintain. Small; SQLite needs no server.
- Agents must resolve IDs to content through a helper rather than reading state
  directly. This is a deliberate constraint: it keeps context windows small, which
  matters on the free tier.
- Evidence outlives the session, which is what makes reproducible evaluation runs
  possible.
- Samit owns the final schema (week of 10/04). Whether very large page bodies go in
  SQLite or ADK's artifact service is README open item 7, to settle with him.
