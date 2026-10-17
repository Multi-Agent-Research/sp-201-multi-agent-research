"""Session-state keys shared by the agents and tools.

Temporary home until Samit's schemas.py is in the repo. The README says
state keys are imported from there, so these move into schemas.py then and
this file goes away.

Only short values go into state: the question, the sub-questions, evidence
IDs and the draft. Source text stays in SQLite (req. 3.3.3).

Sub-questions and evidence IDs each get their own key instead of one shared
list. Gemini often makes several Search calls in one turn, ADK runs them in
parallel, and parallel writes to one list key would overwrite each other.
"""

USER_QUESTION = "user_question"
DRAFT_REPORT = "draft_report"
# Written by the Fact-Checker once it exists; read by the EscalationChecker.
FACT_CHECK = "fact_check"

_SUB_QUESTION_PREFIX = "sub_question_"
_EVIDENCE_PREFIX = "evidence_"


def sub_question_key(number: int) -> str:
    return f"{_SUB_QUESTION_PREFIX}{number:02d}"


def evidence_key(evidence_id: str) -> str:
    return f"{_EVIDENCE_PREFIX}{evidence_id}"


def sub_questions(state: dict) -> list[str]:
    """The sub-questions the Manager searched, in the order it asked them."""
    keys = sorted(k for k in state if k.startswith(_SUB_QUESTION_PREFIX))
    return [state[k] for k in keys]


def evidence_ids(state: dict) -> list[str]:
    """Every evidence ID Search stored during this run."""
    return sorted(k[len(_EVIDENCE_PREFIX) :] for k in state if k.startswith(_EVIDENCE_PREFIX))
