from __future__ import annotations

from collections import defaultdict
import tempfile
from pathlib import Path
from typing import Optional


def extract_docling_page_texts(pdf_bytes: bytes) -> Optional[list[str]]:
    try:
        from docling.document_converter import DocumentConverter
    except Exception:
        return None

    tmp_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = Path(tmp.name)

        converter = DocumentConverter()
        result = converter.convert(str(tmp_path))
        document = getattr(result, "document", result)

        page_map = getattr(document, "pages", None)
        if isinstance(page_map, dict) and page_map:
            dump = document.model_dump()
            texts_by_page: dict[int, list[str]] = defaultdict(list)
            for item in dump.get("texts", []):
                text = (item.get("text") or "").strip()
                if not text:
                    continue
                prov = item.get("prov") or []
                page_no = None
                for prov_item in prov:
                    if isinstance(prov_item, dict) and prov_item.get("page_no") is not None:
                        page_no = int(prov_item["page_no"])
                        break
                if page_no is None:
                    page_no = 1
                texts_by_page[page_no].append(text)

            if texts_by_page:
                page_texts = []
                for page_no in sorted(page_map.keys()):
                    joined = "\n\n".join(texts_by_page.get(int(page_no), []))
                    page_texts.append(joined.strip())
                if any(text.strip() for text in page_texts):
                    return page_texts

        if hasattr(document, "export_to_markdown"):
            markdown = document.export_to_markdown()
            if markdown.strip():
                return [markdown]
    finally:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
    return None
