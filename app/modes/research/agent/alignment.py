from __future__ import annotations

import re
from difflib import SequenceMatcher

from modes.research.agent.models import AlignedCitation, ParsedBlock, ParsedPage, ReferenceMarker

_CITATION_PATTERN = re.compile(
    r"(\[[0-9,\-\s]+\]|\([A-Z][A-Za-z]+(?:\s+et\s+al\.)?,?\s+\d{4}[a-z]?\)|(?:Theorem|Lemma|Proposition|Corollary)\s+\d+(?:\.\d+)*)"
)


def normalize_reference_key(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").strip().lower())


def build_parsed_pages_from_texts(
    page_texts: list[str],
    *,
    parser_source: str,
    page_confidences: dict[int, float] | None = None,
) -> list[ParsedPage]:
    parsed_pages: list[ParsedPage] = []
    for idx, raw_text in enumerate(page_texts, start=1):
        text = (raw_text or "").strip()
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()] or ([text] if text else [])
        blocks: list[ParsedBlock] = []
        markers: list[ReferenceMarker] = []
        headers: list[str] = []
        footers: list[str] = []

        if paragraphs:
            if len(paragraphs[0]) <= 80:
                headers.append(paragraphs[0])
            if len(paragraphs[-1]) <= 40 and len(paragraphs) > 1:
                footers.append(paragraphs[-1])

        for block_idx, para in enumerate(paragraphs, start=1):
            block_id = f"p{idx}-b{block_idx}"
            block_markers: list[ReferenceMarker] = []
            for match in _CITATION_PATTERN.finditer(para):
                marker = ReferenceMarker(
                    raw_text=match.group(1),
                    normalized_key=normalize_reference_key(match.group(1)),
                    page_num=idx,
                    block_id=block_id,
                    span_start=match.start(),
                    span_end=match.end(),
                )
                markers.append(marker)
                block_markers.append(marker)
            blocks.append(ParsedBlock(
                block_id=block_id,
                page_num=idx,
                text=para,
                parser_source=parser_source,
                confidence=float((page_confidences or {}).get(idx, 1.0)),
                citations=block_markers,
            ))

        parsed_pages.append(ParsedPage(
            page_num=idx,
            text=text,
            parser_source=parser_source,
            confidence=float((page_confidences or {}).get(idx, 1.0)),
            blocks=blocks,
            headers=headers,
            footers=footers,
            references=markers,
        ))
    return parsed_pages


def align_grobid_citations(parsed_pages: list[ParsedPage], citation_map: dict[str, dict]) -> list[AlignedCitation]:
    aligned: list[AlignedCitation] = []
    if not parsed_pages or not citation_map:
        return aligned

    flattened_markers = [marker for page in parsed_pages for marker in page.references]
    for key, payload in citation_map.items():
        callout = str(payload.get("callout") or key or "").strip()
        normalized = normalize_reference_key(callout or key)
        best_marker = None
        best_score = 0.0
        for marker in flattened_markers:
            if marker.normalized_key == normalized:
                best_marker = marker
                best_score = 1.0
                break
            score = SequenceMatcher(None, marker.normalized_key, normalized).ratio()
            if score > best_score:
                best_score = score
                best_marker = marker
        aligned.append(AlignedCitation(
            key=normalized or normalize_reference_key(str(key)),
            callout=callout,
            title=str(payload.get("title") or ""),
            doi=str(payload.get("doi") or ""),
            xml_id=str(payload.get("xml_id") or ""),
            page_num=best_marker.page_num if best_marker else 0,
            block_id=best_marker.block_id if best_marker else "",
            alignment_score=round(best_score, 3),
        ))
    return aligned
