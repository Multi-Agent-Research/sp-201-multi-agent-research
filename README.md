# SP-201 Multi-Agent Research and Fact-Checking Pipeline

CS 4850 Senior Project, Section 01, Fall 2026, Kennesaw State University.
Advisor: Professor Sharon Perry.

Four language-model agents, orchestrated with the Google Agent Development Kit
(ADK), take one research question, gather source material, draft a cited
report, and check every claim in that report against the evidence it cites.
The pipeline runs on a Gemini Flash model through the Google AI Studio free
tier.

## Components

| Component | What it does | Owner |
|---|---|---|
| Manager | Splits the question into sub-questions and picks sources for each | Jackson |
| Search | Retrieves from Wikipedia, arXiv and web search; writes passages to SQLite | Raul |
| Synthesizer | Drafts a structured report from stored evidence only | Samit |
| Fact-Checker | Judges each claim against the evidence it cites | Jackson |
| EscalationChecker | Ends the revision loop when the Fact-Checker passes the draft | Raul |
| Interface | Takes the question; shows the report, flagged claims and support score | Samit (web), Vansh (CLI) |

The first four are LLM agents. The EscalationChecker makes no model call and
no judgment of its own; it reads the Fact-Checker's pass/fail result and
escalates on a pass. The Interface displays what the pipeline produced and
verifies nothing itself.

## How a run works

1. The user submits one question.
2. The Manager splits it into at most three sub-questions (req. 3.1.6).
3. The Manager calls Search once per sub-question, as an `AgentTool`
   (SDD 5.1). Search handles one sub-question at a time (req. 3.2.1).
4. Search writes each passage to SQLite and returns record IDs. Full source
   text never goes into session state (req. 3.3.3).
5. The revision loop runs, up to two iterations:
   1. The Synthesizer drafts, or on the second pass revises, using only
      stored evidence.
   2. The Fact-Checker checks every claim and returns pass or fail.
   3. The EscalationChecker ends the loop on a pass.
6. The Interface shows the report with citations, flagged claims and a
   support score.

In ADK terms:

```
SequentialAgent
  Manager                        # holds AgentTool(Search)
  LoopAgent (max_iterations=2)
    Synthesizer                  # first in the loop, not before it
    Fact-Checker
    EscalationChecker            # control only, no model call
```

Every iteration ends with a verification, so there is no path through the
system that returns a report the Fact-Checker has not checked (req. 3.6.4).
Two iterations means exactly one revision (req. 3.6.2).

### Why the Synthesizer is inside the loop

This is the part of the design most likely to get "fixed" by someone who has
not read the reasoning, so it gets its own section.

The obvious layout is Synthesizer before the loop, with the loop running
Fact-Checker then Synthesizer. That works when the draft passes. When it fails
twice, the loop ends right after a revision that no Fact-Checker has looked
at, and that unverified draft is what the user gets. Req. 3.6.4 forbids that.
Putting the Synthesizer first means every iteration ends on a check, and a
run that exhausts the limit still returns a verified draft with its failing
claims marked (req. 3.6.5). It is also one call cheaper on the worst path.

One thing to know before building the loop: ADR-0005 (Sept 13) says
"Fact-Checker ordered first". The SDD (Sept 20) reversed that and the ADR was
never updated. Follow SDD 3.6 and SDD Appendix A, not ADR-0005, until ADR-0007
is written. See open item 8.

## Design decisions

Each has an ADR in `docs/adr/` unless noted. The ADR is the record; this
table is a summary. Reversing one of these needs a new ADR, not a quiet
refactor.

| Decision | Reason | Recorded in |
|---|---|---|
| Classic ADK API (`SequentialAgent`, `LoopAgent`) at a pinned version | The graph API cannot nest a loop inside a sequence (adk-python #5872) | ADR-0001 |
| Workers exposed as `AgentTool`, not sub-agents | Control returns to the Manager after every call instead of the worker keeping it | ADR-0002 |
| Evidence stored in SQLite and passed between agents by integer ID | Keeps full text out of the context window and keeps every claim traceable to the retrieval that produced it | ADR-0003 |
| Model ID read from the environment, never written at a call site (req. 3.11.1) | Models get retired; re-pointing should not need a code change | ADR-0004 |
| One revision cycle, then stop; unsupported claims are flagged, not dropped | Bounded call count per question | ADR-0005 |
| Wikipedia and academic APIs primary, web search as fallback | Free web-search libraries are unofficial and get rate-limited or blocked | ADR-0006 |
| Fact-Checker is an LLM agent; hosted model by default, local entailment classifier held in reserve | Keeps the option of moving the most call-hungry step off the daily cap (open item 3) | SRS 3.5.1, SDD 3.4 (no ADR) |
| Synthesizer runs first inside the revision loop | See the section above | SDD 3.6 (no ADR, open item 8) |

On the model ID: both models named in the project brief have been retired
(`gemini-1.5-flash` on 2025-09-29, `gemini-2.0-flash` on 2026-06-01). The
current target is `gemini-2.5-flash`. Do not copy a model string out of the
brief into code.

## Constraints

### Call budget

The project runs entirely on the free tier, which enforces three separate caps
per Google Cloud project: requests per minute, input tokens per minute, and
requests per day. The daily cap resets at midnight Pacific.

A question with three sub-questions is estimated at 12 to 14 model calls. The
earlier estimate of 6 assumed one call per agent and missed that Search runs
once per sub-question, that an agent calling a tool spends at least two calls
(one to request, one to read the result), and that each `AgentTool` return
costs the Manager another call. Treat 12 to 14 as an estimate until the
evaluation harness measures it (req. 3.9.5).

Two limits follow from this: at most 3 sub-questions per question
(req. 3.1.6) and at most 1 revision per question (req. 3.6.2).

A 20-query evaluation run is roughly 250 calls, so the daily cap is the one
that bites, not the per-minute cap. The run may need to be split across two
days.

The live free-tier figures have not been confirmed. Google no longer publishes
fixed numbers. Someone needs to read them from the AI Studio rate-limit page
and record them with the date before the first evaluation run (open item 2).

### Security

Retrieved web content is the main untrusted input. There are two separate
risks with two separate mitigations, and neither covers the other.

Prompt injection: instructions hidden in a retrieved passage that try to
redirect an agent. Retrieved text is treated as data, never as instruction.
Every passage is wrapped in explicit delimiters and marked untrusted (3.7.3),
it is supplied through the data channel only and never the system instruction
(3.7.4), and a guardrail callback inspects tool output before it reaches a
model (3.7.5). These measures reduce the risk; they do not eliminate it
(3.7.6).

Improper output handling: a malformed value propagating into a later stage.
Every agent output is validated against a Pydantic schema before the next
stage uses it, so bad output fails closed (3.7.2). Schema validation
constrains the form of an output. It is not a defense against prompt
injection, and nothing in the code or docs should claim it is.

Credentials come from the environment and are never committed (3.7.7). On the
free tier, prompts and responses may be used by Google to improve its
products, so no confidential or personal data goes into evaluation queries
(3.7.8).

## Setup

Python 3.10 or later.

```
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Configuration is read from the environment. Copy `.env.example` to `.env`
(git ignores `.env`) and fill in `GOOGLE_API_KEY`. The other three come
prefilled with their defaults:

- `GOOGLE_API_KEY`: Google AI Studio API key.
- `SP201_MODEL_ID`: Gemini model ID. Currently `gemini-2.5-flash`
  (req. 3.11.1).
- `SP201_MAX_SUB_QUESTIONS`: cap on sub-questions per question. Default 3,
  ceiling 5 (req. 3.1.6).
- `SP201_MAX_REVISIONS`: cap on revision cycles per question. Default 1
  (req. 3.6.2).

## Open items

Tracked here until the repo has issues set up. Items 1 to 3 are also in SRS
Appendix B.

| # | Item | Owner | Status |
|---|---|---|---|
| 1 | What "partially supported" requires of the Synthesizer | Team | Closed. The Synthesizer softens the claim using the Fact-Checker's restatement (req. 3.6.6). |
| 2 | Live free-tier rate limits | Team | Open. Read from AI Studio and record with the date before the first evaluation run. |
| 3 | Whether the Fact-Checker delegates entailment to a local classifier (req. 3.5.1) | Team | Open. Decide on measured call counts (req. 3.9.5), not preference. |
| 4 | Value of `PASS_ALLOWS_PARTIAL` in `schemas.py` | Team | Open. Currently `False`; not formally agreed. |
| 5 | What `AgentTool(Search)` returns per call and who assembles `SearchResults` | Jackson, Raul | Open. Settle before Manager and Search are integrated. Per-sub-question dispatch itself is settled (3.2.1, SDD 5.1). |
| 6 | Pinned `google-adk` version missing from the SDD dependency table | Jackson | Open. `requirements.txt` says `2.9.2`; install, run `pip show google-adk`, record what resolves. |
| 7 | Very large pages: full text in SQLite or the ADK artifact service | Samit | Open. Not in SRS Appendix B. |
| 8 | ADR-0005 contradicts the SDD on loop ordering | Jackson | Open. Write ADR-0007 and mark ADR-0005 superseded on that point. Needed before the loop is built (week ending 11/01). |
| 9 | Environment setup | Jackson | Open. Setup section, `.env.example` and the install are done; VM setup remains. |

On item 3: the hosted model is the default because it is simpler to demo and
keeps the pipeline uniform. The per-claim entailment check is the most
call-hungry part of verification, so a local classifier is kept as an option
if the daily cap becomes a problem. Delegating that check to a `FunctionTool`
does not change the multi-agent character of the system; the orchestrating
component is still an LLM agent, which is what SRS 2.3 and req. 3.5.1 ask for.

## Conventions

- Source control is the shared GitHub organization, not a personal account.
- `requirements.txt` pins `google-adk`. Do not float the version.
- No credentials in the repository (3.7.7). Use environment variables, keep
  `.env.example` free of secrets, keep `.env` in `.gitignore`.
- Put requirement numbers in commit messages, docstrings and test names. A
  test for 3.6.6 should turn up when you search for `3.6.6`.
- Import session-state keys from `schemas.py`. Do not type `"manager_plan"`
  at a call site.
- One numbered ADR per decision in `docs/adr/`. Reversing a decision means a
  new ADR, plus a status-line note on the old one (`Superseded by ADR-NNNN`)
  so nobody reads a reversed decision as current.

## Documents

| Document | Status |
|---|---|
| SRS (Sept 20, 2026). Authoritative for requirements. | Submitted. Not in the repo yet. |
| SDD (Sept 20, 2026). Authoritative for design. | Submitted. Not in the repo yet. |
| `schemas.py`. Authoritative for the agent I/O contract (Samit, Oct 11). | Not in the repo yet |
| `docs/adr/0001` to `0006`. One decision each, with the rejected alternative. | In the repo. ADR-0005 is marked superseded on loop ordering; see open item 8. |

If this file disagrees with the SRS, SDD or `schemas.py`, they are right and
this file needs fixing.
