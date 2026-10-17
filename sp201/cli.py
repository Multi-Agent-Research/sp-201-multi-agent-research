"""Command-line interface. From the repo root:

    python -m sp201 "your question"
    python -m sp201 --verbose "your question"   # also show each agent step

Prints the sub-questions, the report, its sources, any citation that points
at evidence this run did not store, and how many model calls the run used.
The call count is the measurement req. 3.9.5 asks for.
"""

import argparse
import asyncio
import re
import socket
import sys
import warnings

import wikipedia
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.runners import InMemoryRunner
from google.genai import errors as genai_errors
from google.genai import types

import search_agent
from sp201 import state
from sp201.agents import build_pipeline
from sp201.config import ConfigError, Settings, load_settings
from sp201.tools import load_evidence_rows

APP_NAME = "sp201"
USER_ID = "cli"
CITATION = re.compile(r"\[(EVID-[0-9A-F]{8})\]")
WIKIPEDIA_USER_AGENT = (
    "SP201-multi-agent-research/0.1 "
    "(KSU CS 4850 senior project; https://github.com/Multi-Agent-Research/sp-201-multi-agent-research)"
)


class ModelCallCounter(BasePlugin):
    """Counts every model request, including the ones Search makes inside AgentTool."""

    def __init__(self) -> None:
        super().__init__(name="model_call_counter")
        self.calls = 0

    async def before_model_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> None:
        self.calls += 1


def _show_event(event) -> None:
    if not event.content or not event.content.parts:
        return
    for part in event.content.parts:
        if part.function_call:
            args = dict(part.function_call.args or {})
            print(f"  [{event.author}] calls {part.function_call.name}({args})")
        elif part.function_response:
            print(f"  [{event.author}] {part.function_response.name} returned")
        elif part.text and not part.thought:
            print(f"  [{event.author}] {part.text.strip()[:200]}")


async def run_question(
    question: str, settings: Settings, verbose: bool = False, model: BaseLlm | None = None
) -> tuple[dict, int]:
    """Runs one question through the pipeline. Returns the final session state and the model call count.

    model defaults to Gemini; tests pass a fake one.
    """
    search_agent.init_db()
    counter = ModelCallCounter()
    runner = InMemoryRunner(agent=build_pipeline(settings, model), app_name=APP_NAME, plugins=[counter])
    try:
        session = await runner.session_service.create_session(
            app_name=APP_NAME, user_id=USER_ID, state={state.USER_QUESTION: question}
        )
        message = types.Content(role="user", parts=[types.Part(text=question)])
        async for event in runner.run_async(user_id=USER_ID, session_id=session.id, new_message=message):
            if verbose:
                _show_event(event)
        final = await runner.session_service.get_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=session.id
        )
    finally:
        await runner.close()
    return final.state, counter.calls


def print_result(final_state: dict, calls: int) -> None:
    subs = state.sub_questions(final_state)
    stored = {row[0]: row for row in load_evidence_rows(state.evidence_ids(final_state))}
    report = final_state.get(state.DRAFT_REPORT) or "(no report was produced)"
    cited = list(dict.fromkeys(CITATION.findall(report)))

    print(f"\nSub-questions searched ({len(subs)}):")
    for i, sub in enumerate(subs, 1):
        print(f"  {i}. {sub}")
    print("\nReport:\n")
    print(report.strip())
    print("\nSources cited:")
    for eid in cited:
        if eid in stored:
            _, source_type, title, url, _ = stored[eid]
            print(f"  [{eid}] {title} ({source_type}) {url}")
    unknown = [eid for eid in cited if eid not in stored]
    if unknown:
        print(f"\nWARNING: cited but not stored this run: {', '.join(unknown)}")
    print(f"\nEvidence stored: {len(stored)}, cited: {len(cited) - len(unknown)}. Model calls: {calls}.")
    print("Note: the Fact-Checker is not built yet, so this report has not been verified (req. 3.6.4).")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m sp201", description="Run one research question through the SP-201 pipeline."
    )
    parser.add_argument("question", help="the research question, in quotes")
    parser.add_argument("--verbose", action="store_true", help="show each agent step as it happens")
    args = parser.parse_args(argv)

    try:
        settings = load_settings()
    except ConfigError as err:
        print(f"Configuration problem: {err}", file=sys.stderr)
        return 2

    # ADK 2.9.2 announces an experimental feature it turns on by itself; not ours.
    warnings.filterwarnings("ignore", message=r"\[EXPERIMENTAL\]", category=UserWarning)

    # Two stopgaps for search_agent.py, to move into that file:
    # 1. Its HTTP calls have no timeout, so one slow source could hang the run.
    socket.setdefaulttimeout(30)
    # 2. Wikimedia answers 429 "too many requests" to the wikipedia package's
    #    default User-Agent, which every user of that library shares. A
    #    descriptive one is what Wikimedia's API rules ask for, and it works.
    wikipedia.set_user_agent(WIKIPEDIA_USER_AGENT)

    print(f"Question: {args.question}\nModel: {settings.model_id}")
    try:
        final_state, calls = asyncio.run(run_question(args.question, settings, args.verbose))
    except genai_errors.APIError as err:
        print(f"\nGemini returned an error: {err}", file=sys.stderr)
        if getattr(err, "code", None) == 429:
            print(
                "That is the free-tier rate limit. Wait a minute and rerun; if it persists, "
                "the daily cap is used up until midnight Pacific.",
                file=sys.stderr,
            )
        return 1
    print_result(final_state, calls)
    return 0
