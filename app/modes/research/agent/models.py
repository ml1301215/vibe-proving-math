from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from modes.research.parser import TheoremProofPair
from modes.research.reviewer import StructuredDocument


@dataclass
class ReferenceMarker:
    raw_text: str
    normalized_key: str
    page_num: int
    block_id: str = ""
    span_start: int = -1
    span_end: int = -1


@dataclass
class AlignedCitation:
    key: str
    callout: str
    title: str = ""
    doi: str = ""
    xml_id: str = ""
    page_num: int = 0
    block_id: str = ""
    alignment_score: float = 0.0


@dataclass
class ParsedBlock:
    block_id: str
    page_num: int
    text: str
    block_type: str = "text"
    heading_level: int = 0
    confidence: float = 1.0
    parser_source: str = "pipeline"
    citations: list[ReferenceMarker] = field(default_factory=list)


@dataclass
class ParsedPage:
    page_num: int
    text: str
    parser_source: str = "pipeline"
    confidence: float = 1.0
    blocks: list[ParsedBlock] = field(default_factory=list)
    headers: list[str] = field(default_factory=list)
    footers: list[str] = field(default_factory=list)
    references: list[ReferenceMarker] = field(default_factory=list)


@dataclass
class AgentSection:
    unit_id: int
    section_title: str
    section_path: str
    page_start: int
    page_end: int
    raw_text: str
    parser_source: str = "pipeline"
    quality_score: float = 1.0
    low_confidence: bool = False
    context_before: str = ""
    context_after: str = ""
    local_definitions: list[str] = field(default_factory=list)
    local_citations: list[str] = field(default_factory=list)


@dataclass
class AgentClaim:
    claim_id: int
    pair: TheoremProofPair
    section_id: int
    claim_kind: str = "core_result"
    parser_source: str = "pipeline"
    quality_score: float = 1.0
    review_confidence: float = 0.0
    retry_count: int = 0
    uncertain: bool = False


@dataclass
class AgentStepResult:
    step: str
    status: str
    details: dict = field(default_factory=dict)


@dataclass
class AgentReviewContext:
    source: str
    pdf_bytes: bytes
    page_texts: list[str]
    structured_document: StructuredDocument
    sections: list[AgentSection]
    parsed_pages: list[ParsedPage] = field(default_factory=list)
    aligned_citations: list[AlignedCitation] = field(default_factory=list)
    parser_source: str = "pipeline"
    quality_score: float = 1.0
    low_confidence_pages: list[int] = field(default_factory=list)
    fallback_pages: list[int] = field(default_factory=list)
    citation_map: dict[str, dict] = field(default_factory=dict)
    parser_details: dict = field(default_factory=dict)
    step_results: list[AgentStepResult] = field(default_factory=list)

    def with_step(self, step: str, status: str, **details) -> None:
        self.step_results.append(AgentStepResult(step=step, status=status, details=details))


@dataclass
class AgentRunResult:
    claims: list[AgentClaim]
    retries: int = 0
    uncertain_claims: int = 0
    claims_classified: int = 0
    fallback_pages: int = 0
    parser_source: str = "pipeline"
    quality_score: float = 1.0
    citation_map_size: int = 0
    extra_stats: dict = field(default_factory=dict)
