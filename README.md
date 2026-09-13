# SP-201: Research & Fact-Checking Pipeline

---

## 1. The Big Picture

**Goal:** Build a pipeline that takes a complex user question, researches it using AI tools, writes a report, and fact-checks that report against the evidence.

**The 4 Agents:**

1.  **Manager:** Breaks the user's question into sub-questions and decides which tools to use.
2.  **Search:** Finds facts using Wikipedia, arXiv, and web search. It saves evidence to a database rather than passing large text around.
3.  **Synthesizer:** Writes a structured draft using the evidence found.
4.  **Fact-Checker:** An LLM-powered agent that reviews the draft to ensure every claim is backed by the evidence.

---

## 2. How It Works

We use a deterministic pipeline (the "Classic" ADK API) to ensure the Manager always stays in control.

1.  **User** submits a question.
2.  **Manager** breaks it down into sub-questions.
3.  **Search** retrieves facts for each sub-question and saves them to a local database (SQLite).
4.  **Synthesizer** writes a report using the database evidence.
5.  **Fact-Checker** reads the report and verifies the claims.
    *   *Constraint:* The system is limited to **1 Revision Cycle** (see budget below).
    *   *If claims are weak:* The Fact-Checker sends feedback, and the Synthesizer revises.
    *   *If claims are strong:* The report is finalized.
6.  **Interface** displays the final verified report.

---

## 3. Key Technical Decisions

### A. We are using the "Classic" API

*   **The Decision:** We are using ADK version 2.9 with the classic `SequentialAgent` and `LoopAgent`.
*   **Why?** The newer "Graph" API has a known bug (Issue #5872) where agents cannot be nested properly. Since our pipeline requires nested steps (a loop inside a sequence), the Classic API is the only stable option right now.

### B. Workers are "Tools," not "Agents" 

*   **The Decision:** The Manager calls the Search and Fact-Check agents as `AgentTools`.
*   **Why?** If we used standard sub-agents, there is a risk the worker agent would take over control and "strand" the workflow (i.e., get stuck and never return to the Manager). By using `AgentTool`, the Manager calls the worker, gets a result, and keeps 100% of the control flow.

### C. Evidence is Stored Externally

*   **The Decision:** We store search results in a local SQLite database. The agents only pass "IDs" around in the session state, not the actual text.
*   **Why?** The AI models have a limited "memory" (context window). Passing large blocks of text between agents would exceed this limit quickly. Storing data in SQLite saves memory, allows the app to run offline, and makes it easier to debug exactly where a fact came from.

### D. Model ID is Configured

*   **The Decision:** The system is configured to use **`gemini-1.5-flash`**.
*   **Why?** The project guidelines specify this (or 2.0-flash) as the approved free-tier model. Since 2.0-flash is retired, 1.5-flash is the correct choice for high capability within the budget constraints.

---

## 4. Constraints & Safety

### A. Budget Management (Strict 1-Cycle Limit)

To stay within the free-tier API limits, the pipeline is strictly limited to **1 Revision Cycle**.

*   **Base Run (4 calls):** Manager + Search + Synthesizer + Fact-Checker.
*   **Revision (2 calls):** If the Fact-Checker finds errors, the Synthesizer and Fact-Checker run *once* more.
*   **Total:** 6 calls.
*   **Reasoning:** A second revision cycle would bring the total to 8+, risking the hard limit of 12 calls per minute/day for the free tier.

### B. MiniCheck Strategy

*   **Decision:** The Fact-Checker must be an actual LLM Agent call, not a local script.
*   **Why:** The project requirements (Milestones 2 & 3) explicitly require "Multi-Agent Orchestration." Using a local verification script would fail the grading criteria for agent-to-agent interaction.

### C. Security

*   **Safety:** We do not trust data from the web. All external text is treated as untrusted data. We use Pydantic schemas to ensure agents only output exactly what we expect, preventing malicious code injection.

---

## 5. Open Decisions (To-Do List)

1.  **Data Storage:** Finalize exactly how very large web pages are handled (Samit to decide), whether to put full text in SQLite or use the ADK artifact service.
