# ADR-0006: Wikipedia and academic APIs primary; DuckDuckGo fallback only

**Status:** Accepted

## Context

The project brief suggests free scrapers or free search APIs, naming Wikipedia and
DuckDuckGo. Our team identified "search sources going down or blocking automated access"
as a project risk. We have no budget for paid search APIs.

## Decision

Primary sources, each wrapped as a `FunctionTool`:

| Source | Key | Notes |
|---|---|---|
| Wikipedia API | none | General knowledge; clean citable snippets |
| arXiv API | none | Preprints; abstracts + metadata |
| Semantic Scholar | free key recommended | 100 req / 5 min unauthenticated; 1 req/sec with key |
| Crossref | none | DOI metadata |

Fallback: DuckDuckGo via `ddgs`, best-effort only, with retry and backoff. A
circuit-breaker fails over to the next source on error.

## Rationale

- There is no official DuckDuckGo web-search API; the Python libraries are unofficial and
  suffer 202 rate-limiting and bot-blocking. Building the pipeline's primary retrieval
  path on it would make the demo fragile.
- Wikipedia and the academic APIs are free, key-optional or free-key, ToS-clean for
  academic use, and return snippets suitable for evidence grounding, which is what the
  Fact-Checker needs.
- Multiple independent sources are themselves the mitigation for the "source goes down"
  risk. A single point of failure in retrieval fails the whole pipeline.
- Brave dropped its free tier in February 2026; Tavily and Serper are credit-limited.
  Neither is a dependable base for a semester-long project.

## Consequences

- Coverage of very recent events is weaker than a general web search would give. The
  20-query evaluation set should reflect what these sources can actually support, with
  recency-sensitive queries included deliberately to expose the limit rather than by
  accident.
- Each source needs its own `FunctionTool` and its own response normalization into the
  common evidence record shape (architecture.md section 8).
- ADK's built-in `google_search` tool may be usable on the free tier; treat as unverified
  and keep these tools as the dependable base regardless.
