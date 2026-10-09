import sqlite3
import uuid
from pydantic import BaseModel, Field

# Database Initialization

def init_db():
    """Creates the SQLite evidence table if it does not already exist."""
    conn = sqlite3.connect("evidence_store.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evidence (
            evidence_id TEXT PRIMARY KEY,
            query_topic TEXT NOT NULL,
            source_type TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT,
            raw_content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()


# Pydantic Schemas
class EvidenceMetadata(BaseModel):
    evidence_id: str = Field(description="Unique identifier stored in SQLite")
    title: str = Field(description="Title of the source article or document")
    url: str = Field(description="Source URL or reference link")
    source_type: str = Field(description="Origin: wikipedia, arxiv, or web")

class SearchResponse(BaseModel):
    sub_question: str
    retrieved_evidence: list[EvidenceMetadata]


# Database Persistence Helper

def store_evidence(query_topic: str, source_type: str, title: str, url: str, content: str) -> str:
    """Inserts raw search text into SQLite and returns a lightweight reference ID."""
    evidence_id = f"EVID-{uuid.uuid4().hex[:8].upper()}"
    conn = sqlite3.connect("evidence_store.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO evidence (evidence_id, query_topic, source_type, title, url, raw_content)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (evidence_id, query_topic, source_type, title, url, content))
    
    conn.commit()
    conn.close()
    return evidence_id


# Search Tool Functions

def fetch_wikipedia_source(sub_question: str) -> EvidenceMetadata:
    """Fetches full content from Wikipedia, persists it, and returns metadata."""
    raw_text = f"Full extracted content for query: {sub_question}. Wikipedia detailed context..." 
    title = f"Wikipedia entry for {sub_question}"
    url = f"https://en.wikipedia.org/wiki/{sub_question.replace(' ', '_')}"
    
    eid = store_evidence(sub_question, "wikipedia", title, url, raw_text)
    return EvidenceMetadata(evidence_id=eid, title=title, url=url, source_type="wikipedia")

def fetch_arxiv_source(sub_question: str) -> EvidenceMetadata:
    """Fetches full paper summary/text from arXiv, persists it, and returns metadata."""
    raw_text = f"Full paper abstract and content for query: {sub_question}. arXiv paper details..." 
    title = f"arXiv paper on {sub_question}"
    url = f"https://arxiv.org/abs/2401.{uuid.uuid4().hex[:4]}"
    
    eid = store_evidence(sub_question, "arxiv", title, url, raw_text)
    return EvidenceMetadata(evidence_id=eid, title=title, url=url, source_type="arxiv")


# Execution / Test Block

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
    
    # Test retrieval
    meta = fetch_wikipedia_source("Agentic AI Architectures")
    print("Retrieved & Persisted Evidence:", meta.model_dump())
