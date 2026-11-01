import os
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel, Field

from evidence_store import EvidenceStore, DEFAULT_DB_PATH
from schemas import EvidenceRecord, SourceType

# Timestamp helper matching EvidenceStore format
def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

# Pydantic Schemas for Search Agent Output

class EvidenceMetadata(BaseModel):
    evidence_id: int = Field(description="Unique integer identifier stored in SQLite EvidenceStore")
    title: str = Field(description="Title of the source article or document")
    url: str = Field(description="Source URL or reference link")
    source_type: str = Field(description="Origin: wikipedia, arxiv, or web")

class SearchResponse(BaseModel):
    sub_question_id: int
    sub_question: str
    retrieved_evidence: list[EvidenceMetadata]

# Database Persistence Helper using Samit's EvidenceStore

def store_evidence(question_id: int, sub_question_id: int, source_type: str, title: str, url: str, content: str) -> int:
    """Inserts raw search text into SQLite using Samit's EvidenceStore.add_evidence and returns an integer ID."""
    store = EvidenceStore()
    
    record = EvidenceRecord(
        sub_question_id=sub_question_id,
        source_url=url,
        source_title=title,
        published_date="",
        passage=content,
        retrieved_at=utc_now(),
        source_type=SourceType(source_type)
    )
    
    return store.add_evidence(question_id, record)

# Search Tool Functions
# ---------------------------------------------------------------------------
WIKIPEDIA_USER_AGENT = (
    "SP201-multi-agent-research/0.1 "
    "(KSU CS 4850 senior project; https://github.com/Multi-Agent-Research/sp-201-multi-agent-research)"
)
ARXIV_TIMEOUT_SECONDS = 30

def fetch_wikipedia_source(question_id: int, sub_question_id: int, sub_question: str) -> EvidenceMetadata:
    """Performs a 2-step Wikipedia search to locate the relevant page and extract text."""
    try:
        import wikipedia
        wikipedia.set_user_agent(WIKIPEDIA_USER_AGENT)
        search_results = wikipedia.search(sub_question)
        if search_results:
            page_title = search_results[0]
            page = wikipedia.page(page_title, auto_suggest=False)
            title = page.title
            url = page.url
            raw_text = page.content[:3000]
        else:
            title = f"No Wikipedia page found for {sub_question}"
            url = ""
            raw_text = "No content retrieved."
    except Exception as e:
        title = f"Wikipedia search: {sub_question}"
        url = f"https://en.wikipedia.org/wiki/Special:Search?search={sub_question.replace(' ', '+')}"
        raw_text = f"[Wikipedia API Error/Fallback: {str(e)}]"

    eid = store_evidence(question_id, sub_question_id, "wikipedia", title, url, raw_text)
    return EvidenceMetadata(evidence_id=eid, title=title, url=url, source_type="wikipedia")

def fetch_arxiv_source(question_id: int, sub_question_id: int, sub_question: str) -> EvidenceMetadata:
    """Queries arXiv API for academic papers related to the sub-question."""
    try:
        query_url = f"http://export.arxiv.org/api/query?search_query=all:{sub_question.replace(' ', '+')}&start=0&max_results=1"
        response = urllib.request.urlopen(query_url, timeout=ARXIV_TIMEOUT_SECONDS)
        xml_data = response.read()
        
        root = ET.fromstring(xml_data)
        ns = {'arxiv': 'http://www.w3.org/2005/Atom'}
        entry = root.find('arxiv:entry', ns)
        
        if entry is not None:
            title = entry.find('arxiv:title', ns).text.strip().replace('\n', ' ')
            url = entry.find('arxiv:id', ns).text.strip()
            raw_text = entry.find('arxiv:summary', ns).text.strip().replace('\n', ' ')
        else:
            title = f"No arXiv paper found for {sub_question}"
            url = ""
            raw_text = "No paper content found."
    except Exception as e:
        title = f"arXiv query: {sub_question}"
        url = "https://arxiv.org"
        raw_text = f"[arXiv API Error/Fallback: {str(e)}]"

    eid = store_evidence(question_id, sub_question_id, "arxiv", title, url, raw_text)
    return EvidenceMetadata(evidence_id=eid, title=title, url=url, source_type="arxiv")

def fetch_web_source(question_id: int, sub_question_id: int, sub_question: str) -> EvidenceMetadata:
    """Performs a web search via DuckDuckGo search wrapper."""
    try:
        from duckduckgo_search import DDGS
        results = list(DDGS().text(sub_question, max_results=1))
        if results:
            title = results[0].get('title', f"Web search for {sub_question}")
            url = results[0].get('href', '')
            raw_text = results[0].get('body', '')
        else:
            title = f"Web result for {sub_question}"
            url = ""
            raw_text = "No web search results."
    except Exception as e:
        title = f"Web Search for {sub_question}"
        url = ""
        raw_text = f"[Web Search Error/Fallback: {str(e)}]"

    eid = store_evidence(question_id, sub_question_id, "web", title, url, raw_text)
    return EvidenceMetadata(evidence_id=eid, title=title, url=url, source_type="web")


# Execution / Test Block

if __name__ == "__main__":
    store = EvidenceStore()
    q_id = store.add_question("Test Research Question")
    # Simulate adding a sub-question plan mapping (plan_number 1)
    # Usually handled by add_sub_questions, but for quick standalone test:
    with store.connect() as conn:
        cursor = conn.execute(
            "INSERT INTO sub_question (question_id, plan_number, text) VALUES (?, ?, ?)",
            (q_id, 1, "Agentic AI Architectures")
        )
        
    print(f"Database initialized at: {store.db_path}")
    
    meta = fetch_wikipedia_source(question_id=q_id, sub_question_id=1, sub_question="Agentic AI Architectures")
    print("Retrieved & Persisted Evidence:", meta.model_dump())
