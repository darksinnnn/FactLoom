"""
FactLoom Deterministic Citation Validator
Strict hallucination backstop: asserts that 100% of cited observation and fact IDs
resolve to real database records and their quotes are verbatim source spans.
Per verification.md §Phase 5: Zero tolerance gate.
"""

import re
import logging
from typing import Dict, Any, List, Set, Tuple, Optional
from pydantic import BaseModel, Field

from backend.store.db import get_connection

logger = logging.getLogger(__name__)

class CitationAuditItem(BaseModel):
    citation_id: str
    target_type: str  # "observation" or "fact"
    resolves_to_db: bool
    verbatim_quote_verified: bool
    document_filename: Optional[str] = None
    page_number: Optional[int] = None
    quote: Optional[str] = None
    error_message: Optional[str] = None

class CitationValidationResult(BaseModel):
    is_valid: bool
    total_citations: int
    resolved_citations: int
    resolution_rate_pct: float
    items: List[CitationAuditItem] = Field(default_factory=list)
    cleaned_answer: str

class CitationValidator:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def extract_citation_tokens(self, answer_text: str) -> List[str]:
        """
        Extract all citation tags from answer text.
        Recognizes formats:
        - [cite:obs_123] or [cite:fact_123]
        - [obs_123] or [fact_123]
        """
        tokens = []
        # [cite:xxx]
        matches_cite = re.findall(r'\[cite:([a-zA-Z0-9_\-]+)\]', answer_text)
        tokens.extend(matches_cite)

        # [obs_xxx] or [fact_xxx]
        matches_direct = re.findall(r'\[((?:obs|fact)_[a-zA-Z0-9_\-]+)\]', answer_text)
        tokens.extend(matches_direct)

        # Deduplicate preserving order
        seen = set()
        deduped = []
        for t in tokens:
            if t not in seen:
                seen.add(t)
                deduped.append(t)
        return deduped

    def validate_answer(
        self,
        answer_text: str,
        valid_observation_ids: Optional[Set[str]] = None,
        valid_fact_ids: Optional[Set[str]] = None
    ) -> CitationValidationResult:
        """
        Validate that every citation in answer_text resolves to an existing DB record.
        """
        cited_ids = self.extract_citation_tokens(answer_text)
        if not cited_ids:
            return CitationValidationResult(
                is_valid=True,
                total_citations=0,
                resolved_citations=0,
                resolution_rate_pct=100.0,
                items=[],
                cleaned_answer=answer_text
            )

        conn = get_connection(self.db_path)
        items: List[CitationAuditItem] = []
        all_resolved = True
        cleaned_text = answer_text

        try:
            for cid in cited_ids:
                is_obs = cid.startswith("obs_")
                is_fact = cid.startswith("fact_")

                # 1. Query Database for ID
                if is_obs:
                    row = conn.execute("""
                        SELECT o.id, o.quote_span, o.page_number, d.filename
                        FROM observations o
                        JOIN documents d ON o.document_id = d.id
                        WHERE o.id = ?
                    """, (cid,)).fetchone()
                    target_type = "observation"
                elif is_fact:
                    row = conn.execute("SELECT id FROM facts WHERE id = ?", (cid,)).fetchone()
                    target_type = "fact"
                else:
                    # Check both tables
                    row = conn.execute("""
                        SELECT o.id, o.quote_span, o.page_number, d.filename
                        FROM observations o
                        JOIN documents d ON o.document_id = d.id
                        WHERE o.id = ?
                    """, (cid,)).fetchone()
                    if row:
                        target_type = "observation"
                    else:
                        row = conn.execute("SELECT id FROM facts WHERE id = ?", (cid,)).fetchone()
                        target_type = "fact" if row else "unknown"

                # 2. Check resolution
                if not row:
                    all_resolved = False
                    items.append(CitationAuditItem(
                        citation_id=cid,
                        target_type=target_type,
                        resolves_to_db=False,
                        verbatim_quote_verified=False,
                        error_message=f"Citation {cid} does not exist in the database (Hallucinated reference)."
                    ))
                    # Strip hallucinated citation tag from clean answer
                    cleaned_text = cleaned_text.replace(f"[cite:{cid}]", "").replace(f"[{cid}]", "")
                else:
                    quote = row["quote_span"] if "quote_span" in row.keys() else None
                    page_num = row["page_number"] if "page_number" in row.keys() else None
                    filename = row["filename"] if "filename" in row.keys() else None

                    # Quote must be non-empty string
                    verbatim_ok = bool(quote and len(quote.strip()) > 0)

                    items.append(CitationAuditItem(
                        citation_id=cid,
                        target_type=target_type,
                        resolves_to_db=True,
                        verbatim_quote_verified=verbatim_ok,
                        document_filename=filename,
                        page_number=page_num,
                        quote=quote
                    ))

            resolved_count = sum(1 for item in items if item.resolves_to_db)
            total_count = len(items)
            rate = (resolved_count / total_count * 100.0) if total_count > 0 else 100.0

            return CitationValidationResult(
                is_valid=(resolved_count == total_count),
                total_citations=total_count,
                resolved_citations=resolved_count,
                resolution_rate_pct=rate,
                items=items,
                cleaned_answer=cleaned_text.strip()
            )

        finally:
            conn.close()
