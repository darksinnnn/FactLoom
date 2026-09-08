"""
FactLoom Query Service
Top-level orchestration for question answering:
1. Parse & canonicalize question mentions
2. Retrieve candidate facts, observations, and relationships
3. Synthesize answer with ambiguity abstention
4. Validate 100% citation resolution
"""

import logging
from typing import Optional, Dict, Any

from backend.query.parser import QueryParser, ParsedQuery
from backend.query.retriever import KnowledgeRetriever, RetrievalResult
from backend.query.citation_validator import CitationValidator
from backend.query.synthesizer import AnswerSynthesizer, QueryAnswerResponse

logger = logging.getLogger(__name__)

class QueryService:
    def __init__(
        self,
        db_path: Optional[str] = None,
        query_parser: Optional[QueryParser] = None,
        retriever: Optional[KnowledgeRetriever] = None,
        validator: Optional[CitationValidator] = None,
        synthesizer: Optional[AnswerSynthesizer] = None
    ):
        self.db_path = db_path
        self.parser = query_parser or QueryParser()
        self.retriever = retriever or KnowledgeRetriever(db_path=self.db_path)
        self.validator = validator or CitationValidator(db_path=self.db_path)
        self.synthesizer = synthesizer or AnswerSynthesizer(citation_validator=self.validator)

    def ask(self, question: str) -> QueryAnswerResponse:
        """
        Execute end-to-end question answering pipeline:
        parse -> retrieve -> synthesize -> validate citations.
        """
        logger.info(f"[QUERY] Processing question: '{question}'")
        parsed = self.parser.parse_question(question)
        logger.info(f"[QUERY] Parsed: Entity='{parsed.canonical_entity}', Metric='{parsed.canonical_metric}', Period='{parsed.period_mention}'")

        retrieval = self.retriever.retrieve(parsed)
        logger.info(f"[QUERY] Retrieved {retrieval.total_facts} facts, {retrieval.total_observations} observations, {len(retrieval.relationships)} relationships")

        answer_response = self.synthesizer.answer_query(parsed, retrieval)
        logger.info(f"[QUERY] Answered (ambiguous={answer_response.is_ambiguous}, citations={len(answer_response.citations)})")

        return answer_response
