"""
FactLoom Fact Extraction Engine
Implements Agent 1 (Extractor) with deterministic grounding verification and bbox matching.
Supports chunked table and prose extraction for multi-column disclosures.
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional, Tuple

from backend.extract.schema import FactCandidate, ExtractionResponse
from backend.extract.prompts.extraction_prompt import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT_TEMPLATE
from backend.extract.client import GroqClient
from backend.ingest.parser import ParsedPage

logger = logging.getLogger(__name__)

class FactExtractor:
    def __init__(self, client: Optional[GroqClient] = None):
        self.client = client or GroqClient()

    def extract_from_page(
        self,
        page: ParsedPage,
        doc_filename: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract grounded fact candidates from a single parsed page.
        Enforces deterministic quote_span verification before returning any candidate.
        """
        page_text = page.full_text
        if not page_text or len(page_text.strip()) < 15:
            logger.info(f"Page {page.page_number} has insufficient text for extraction.")
            return []

        contexts_to_extract: List[str] = []

        # Check for structured tables
        has_large_table = False
        if page.table_blocks:
            for idx, tab in enumerate(page.table_blocks):
                header = tab.get("header", [])
                rows = [r for r in tab.get("rows", []) if any(cell.strip() for cell in r)]
                if len(rows) > 8:
                    has_large_table = True
                    # Split rows into chunks of 10 rows with header
                    chunk_size = 10
                    for r_start in range(0, len(rows), chunk_size):
                        r_slice = rows[r_start:r_start + chunk_size]
                        t_lines = [" | ".join(header)] + [" | ".join(r) for r in r_slice]
                        t_str = "\n".join(t_lines)
                        part_info = f"Page {page.page_number} - Table {idx+1} (Rows {r_start+1}-{r_start+len(r_slice)}):\n\n{t_str}"
                        if doc_filename:
                            part_info = f"Document: {doc_filename}\n" + part_info
                        contexts_to_extract.append(part_info)

        if not has_large_table:
            # Standard single page context
            context_parts = [f"Page Number: {page.page_number}"]
            if doc_filename:
                context_parts.append(f"Document: {doc_filename}")
            context_parts.append("\nText Content:\n" + page_text)

            if page.table_blocks:
                context_parts.append("\nStructured Tables Detected:")
                for idx, tab in enumerate(page.table_blocks):
                    header_str = " | ".join(tab.get("header", []))
                    rows_str = "\n".join([" | ".join(row) for row in tab.get("rows", [])])
                    context_parts.append(f"--- Table {idx+1} ---\n{header_str}\n{rows_str}")

            contexts_to_extract.append("\n".join(context_parts))

        all_raw_candidates: List[FactCandidate] = []
        for prompt_content in contexts_to_extract:
            messages = [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": EXTRACTION_USER_PROMPT_TEMPLATE.format(page_content=prompt_content)}
            ]

            raw_resp = self.client.chat_completion(
                messages,
                model_role="extractor",
                temperature=0.0,
                reasoning_effort="low"
            )

            try:
                extraction = ExtractionResponse.model_validate(raw_resp)
                all_raw_candidates.extend(extraction.candidates)
            except Exception as e:
                logger.warning(f"Failed to validate extraction schema: {e}. Raw response: {raw_resp}")

        # Deterministic Grounding & Deduplication
        verified_records: List[Dict[str, Any]] = []
        seen_keys = set()

        for cand in all_raw_candidates:
            is_valid_grounding, normalized_quote = self._verify_grounding(cand.quote_span, page_text)
            if not is_valid_grounding:
                logger.warning(
                    f"Grounding check failed for claim '{cand.claim_text}': "
                    f"quote_span {repr(cand.quote_span)} not found in page {page.page_number}. Dropping candidate."
                )
                continue

            # Deduplication key across chunks
            val_clean = cand.value.strip()
            metric_clean = cand.metric_mention.strip().lower()
            period_clean = (cand.period_mention or "").strip().lower()
            dedup_key = (metric_clean, val_clean, period_clean)
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            # Resolve bounding box
            resolved_bbox = self._locate_bbox_for_quote(cand.quote_span, page.text_blocks)

            verified_records.append({
                "entity_mention": cand.entity_mention.strip(),
                "metric_mention": cand.metric_mention.strip(),
                "value": val_clean,
                "unit": cand.unit.strip() if cand.unit else None,
                "period_mention": cand.period_mention.strip() if cand.period_mention else None,
                "scope_mention": cand.scope_mention.strip() if cand.scope_mention else None,
                "definition_mention": cand.definition_mention.strip() if cand.definition_mention else None,
                "claim_text": cand.claim_text.strip(),
                "quote_span": normalized_quote or cand.quote_span.strip(),
                "confidence": cand.confidence,
                "page_number": page.page_number,
                "bbox": resolved_bbox
            })

        return verified_records

    def _verify_grounding(self, quote_span: str, page_text: str) -> Tuple[bool, Optional[str]]:
        """
        Deterministic verification: quote_span must be an exact substring of page_text.
        Handles escaped newlines, pipe delimiters, and whitespace normalization.
        """
        if not quote_span:
            return False, None

        quote_clean = quote_span.strip()
        # Unescape literal \n or \r if present from JSON encoding
        quote_clean = quote_clean.replace("\\n", "\n").replace("\\r", "\r")

        # 1. Exact literal substring check
        if quote_clean in page_text:
            return True, quote_clean

        # 2. Pipe-separated table cell quotes (e.g. 'Metric | Value')
        if "|" in quote_clean:
            parts = [p.strip() for p in quote_clean.split("|") if p.strip()]
            if parts and all(p in page_text for p in parts):
                return True, " ".join(parts)

        # 3. Whitespace normalization check
        normalized_page = " ".join(page_text.split())
        normalized_quote = " ".join(quote_clean.split())
        if normalized_quote in normalized_page:
            pattern = re.escape(normalized_quote).replace(r"\ ", r"\s+")
            match = re.search(pattern, page_text)
            if match:
                return True, match.group(0)
            return True, normalized_quote

        return False, None

    def _locate_bbox_for_quote(
        self,
        quote_span: str,
        text_blocks: List[Dict[str, Any]]
    ) -> Optional[List[float]]:
        """Find the bounding box of the block containing or best overlapping the quote span."""
        quote_clean = " ".join(quote_span.split()).lower()
        best_block = None
        best_overlap = 0

        for block in text_blocks:
            block_text = " ".join(block.get("text", "").split()).lower()
            if quote_clean in block_text:
                return block.get("bbox")

            # Keyword overlap fallback
            quote_words = set(re.findall(r"\w+", quote_clean))
            block_words = set(re.findall(r"\w+", block_text))
            overlap = len(quote_words.intersection(block_words))
            if overlap > best_overlap:
                best_overlap = overlap
                best_block = block

        if best_block and best_overlap >= max(2, len(quote_clean.split()) // 2):
            return best_block.get("bbox")

        return None
