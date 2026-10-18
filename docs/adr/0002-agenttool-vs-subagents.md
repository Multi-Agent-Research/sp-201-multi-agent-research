# ADR-0002: Expose workers to the Manager via AgentTool, not sub_agents

**Status:** Accepted

## Context

ADK offers two ways for a Manager agent to reach a worker agent:

1. **`sub_agents`**: the Manager's LLM decides to hand off via `transfer_to_agent`.
   Control moves to the child and does not automatically return.
2. **`AgentTool`**: the worker is wrapped as a callable tool. The Manager invokes it,
   receives a result, and retains control.

Our Manager must decompose a question, dispatch search work, and then continue
orchestrating. It cannot afford to lose control mid-run.

## Decision

Wrap the Search Agent in `AgentTool`. Use deterministic workflow agents
(`SequentialAgent`, `LoopAgent`) for the fixed pipeline stages. Do not use `sub_agents`
transfer anywhere in this design.

## Rationale

- Transfer semantics are wrong for a Manager-Worker pattern: practitioners document a
  "stickiness" failure where a sub-agent never transfers back and the workflow strands.
- Our pipeline shape is known and fixed. Spending a model call on LLM routing buys
  nothing and costs free-tier quota.
- Deterministic composition is materially easier to debug and to demo reproducibly.

## Consequences

- Workers run in isolation and return structured values; they do not see or extend the
  Manager's conversation. Anything a worker needs must be passed explicitly or read from
  session state.
- Routing behavior is predictable, which makes trajectory-based evaluation meaningful
  (`tool_trajectory_avg_score` has a fixed expected sequence to compare against).
- The `description` field on each worker still matters, because the Manager's LLM
  reads it when deciding to call the tool. Raul owns these strings (see section 5
  of architecture.md).
