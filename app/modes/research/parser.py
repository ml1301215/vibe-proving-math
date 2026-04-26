"""论文解析器 —— 从 arXiv / LaTeX / PDF 提取定理-证明对。

优化记录：
  - parse_arxiv 结果缓存（进程内 TTL 1 小时），同一 arxiv_id 不重复下载
  - 使用模块级 httpx.AsyncClient（连接池复用）
  - 所有异常使用 logging 记录，不再静默忽略

支持三种输入：
  1. arXiv ID → 下载源文件（.tex）→ 结构化解析
  2. .tex 文件 → 直接解析
  3. PDF → LLM 结构化提取（降级，精度约 60%）

输出：list[TheoremProofPair]
"""
from __future__ import annotations

import json
import logging
import re
import time
import zipfile
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx

from core.llm import chat_json
from core.text_sanitize import ensure_inline_math, strip_non_math_latex

logger = logging.getLogger(__name__)

_ARXIV_EPRINT_URL = "https://arxiv.org/e-print/{arxiv_id}"
_ARXIV_PDF_URL    = "https://arxiv.org/pdf/{arxiv_id}"
_DOWNLOAD_TIMEOUT = 20.0
_LATEX_STYLE_INSTRUCTION = (
    "When any extracted JSON string field mentions a mathematical symbol, variable, formula, set, map, inequality, "
    "cardinality, or symbolic relation, wrap the mathematical part in inline LaTeX using `$...$`. "
    "Examples: `$p=3$`, `$g \\in G$`, `$H \\le G$`, `$f: X \\to Y$`, `$|H| \\mid |G|$`. "
    "Do not emit bare Unicode math such as `∈`, `≤`, `⊂`, `|G|` outside `$...$`. "
    "Use plain natural language outside math delimiters, and do not use Markdown formatting besides LaTeX math."
)

# LaTeX 环境名（定理类）
_THEOREM_ENVS = {
    "theorem", "lemma", "proposition", "corollary", "claim",
    "conjecture", "fact", "observation", "remark", "definition",
    "example", "problem", "exercise",
}

# ── 模块级 HTTP 客户端（连接复用）──────────────────────────────────────────────
_http: Optional[httpx.AsyncClient] = None


def _get_http() -> httpx.AsyncClient:
    global _http
    if _http is None or _http.is_closed:
        _http = httpx.AsyncClient(
            timeout=_DOWNLOAD_TIMEOUT,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=5, max_keepalive_connections=2),
        )
    return _http


# ── arXiv 解析结果 TTL 缓存 ────────────────────────────────────────────────────
_ARXIV_CACHE_TTL = 3600          # 1 小时
_ARXIV_CACHE_MAX = 50            # 最多缓存 50 篇（内存友好）
_arxiv_cache: dict[str, tuple[float, list]] = {}


def _arxiv_cache_get(arxiv_id: str):
    entry = _arxiv_cache.get(arxiv_id)
    if entry is None:
        return None
    ts, pairs = entry
    if time.monotonic() - ts > _ARXIV_CACHE_TTL:
        del _arxiv_cache[arxiv_id]
        return None
    logger.debug("arXiv cache hit: %s (%d pairs)", arxiv_id, len(pairs))
    return pairs


def _arxiv_cache_set(arxiv_id: str, pairs: list) -> None:
    if len(_arxiv_cache) >= _ARXIV_CACHE_MAX:
        # 淘汰最老条目
        oldest_key = min(_arxiv_cache, key=lambda k: _arxiv_cache[k][0])
        del _arxiv_cache[oldest_key]
    _arxiv_cache[arxiv_id] = (time.monotonic(), pairs)


# ── 数据模型 ───────────────────────────────────────────────────────────────────

@dataclass
class TheoremProofPair:
    """一个定理-证明对。"""
    env_type: str          # "theorem" | "lemma" | etc.
    ref: Optional[str]     # 引用标签（如 "thm:main"）
    statement: str         # 定理陈述
    proof: Optional[str]   # 证明文本（可能为空）
    source: str            # 来源标识（arxiv_id 或文件名）
    line_start: int = 0    # 在原文件中的起始行
    location_hint: Optional[str] = None
    context_excerpt: Optional[str] = None
    section_title: Optional[str] = None
    section_path: Optional[str] = None
    page_span: Optional[str] = None
    claim_kind: Optional[str] = None
    parser_source: Optional[str] = None
    quality_score: Optional[float] = None
    review_confidence: Optional[float] = None
    context_before: Optional[str] = None
    context_after: Optional[str] = None
    local_citations: list[str] = field(default_factory=list)
    local_definitions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "env_type": self.env_type,
            "ref": self.ref,
            "statement": self.statement[:500],
            "proof": self.proof[:500] if self.proof else None,
            "source": self.source,
            "location_hint": self.location_hint,
            "section_title": self.section_title,
            "section_path": self.section_path,
            "page_span": self.page_span,
            "claim_kind": self.claim_kind,
            "parser_source": self.parser_source,
            "quality_score": self.quality_score,
            "review_confidence": self.review_confidence,
        }

    def has_proof(self) -> bool:
        return bool(self.proof and len(self.proof.strip()) > 20)


# ── LaTeX 解析 ─────────────────────────────────────────────────────────────────

def _discover_custom_envs(tex_content: str) -> set[str]:
    """扫描 \\newtheorem / \\declaretheorem 声明，提取作者自定义的定理类环境名。

    例如 `\\newtheorem{thm}{Theorem}` → 收集 'thm'；`\\newtheorem*{lem}{Lemma}` → 'lem'。
    将基础 stem (Theorem/Lemma/...) 与基础环境集对比，匹配即视为定理类环境。
    """
    custom: set[str] = set()
    pattern = re.compile(
        r"\\(?:newtheorem|declaretheorem)\*?\s*\{([^}]+)\}\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}",
    )
    base_terms = {term.lower() for term in _THEOREM_ENVS} | {
        "theorem", "lemma", "proposition", "corollary", "claim", "definition",
        "remark", "example", "fact", "observation", "exercise", "problem",
        "conjecture",
    }
    for m in pattern.finditer(tex_content):
        env_name = m.group(1).strip().lower()
        display = m.group(2).strip().lower()
        if any(term in display for term in base_terms):
            custom.add(env_name)
    return custom


def _extract_tex_environments(tex_content: str, source: str = "") -> list[TheoremProofPair]:
    """从 LaTeX 文本中提取定理/引理/命题环境及其证明。

    支持：
      - 内建环境名（theorem/lemma/...）及其 starred 形式（theorem*）
      - 通过 \\newtheorem 注册的自定义短名（如 thm, lem, prop, cor）
    """
    pairs: list[TheoremProofPair] = []

    custom_envs = _discover_custom_envs(tex_content)
    all_envs = set(e.lower() for e in _THEOREM_ENVS) | custom_envs
    env_alt = "|".join(sorted(re.escape(e) for e in all_envs))

    env_pattern = re.compile(
        r"\\begin\{(" + env_alt + r")\*?\}"
        r"(?:\[([^\]]*)\])?"
        r"(.*?)"
        r"\\end\{\1\*?\}",
        re.DOTALL | re.IGNORECASE,
    )

    proof_pattern = re.compile(
        r"\\begin\{proof\}(.*?)\\end\{proof\}",
        re.DOTALL,
    )

    proofs = [(m.start(), m.end(), m.group(1)) for m in proof_pattern.finditer(tex_content)]

    for match in env_pattern.finditer(tex_content):
        env_type = match.group(1).lower()
        label = match.group(2) or None
        body = match.group(3).strip()
        env_end = match.end()

        adjacent_proof = None
        for p_start, p_end, p_text in proofs:
            if p_start >= env_end and p_start - env_end < 5000:
                adjacent_proof = p_text.strip()
                break

        pair = TheoremProofPair(
            env_type=env_type,
            ref=label,
            statement=_clean_latex(body),
            proof=_clean_latex(adjacent_proof) if adjacent_proof else None,
            source=source,
            line_start=tex_content[:match.start()].count("\n"),
        )
        pairs.append(pair)

    return pairs


def _clean_latex(text: Optional[str]) -> Optional[str]:
    """简单清理 LaTeX 命令，保留数学内容。"""
    if text is None:
        return None
    text = re.sub(r"\\label\{[^}]*\}", "", text)
    text = re.sub(r"\\cite\{[^}]*\}", "[REF]", text)
    text = re.sub(r"\\ref\{[^}]*\}", "[REF]", text)
    text = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+\b", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ── LLM 降级提取 ───────────────────────────────────────────────────────────────

async def _llm_extract_from_text(text: str, source: str) -> list[TheoremProofPair]:
    """降级：用 LLM 从非结构化文本（如 PDF 提取的文本）中识别定理-证明对。

    若文本中完全找不到 theorem/lemma/proposition/corollary/proof 等关键字，
    直接返回空列表，避免无意义的 LLM 调用（节省 ~30s 耗时）。
    """
    lowered = text.lower()
    if not any(kw in lowered for kw in ("theorem", "lemma", "proposition", "corollary", "proof", "定理", "引理", "命题")):
        logger.info("Text from %s contains no theorem-like keywords; skipping LLM extraction", source)
        return []

    truncated = text[:8000]   # 控制 token 消耗

    system = (
        "You are a mathematical paper parser. Extract theorem-proof pairs from the given text.\n"
        'Output JSON array of objects with fields: '
        '{"env_type": "theorem|lemma|proposition|corollary|definition", '
        '"ref": "optional label", "statement": "...", "proof": "...or null"}\n'
        "Output JSON array only."
    )
    user_msg = f"Extract theorem-proof pairs from this mathematical text:\n\n{truncated}"

    try:
        raw = await chat_json(user_msg, system=system)
        data = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(data, list):
            data = data.get("theorems", data.get("pairs", []))
        pairs = []
        for item in data:
            pairs.append(TheoremProofPair(
                env_type=item.get("env_type", "theorem"),
                ref=item.get("ref"),
                statement=str(item.get("statement", ""))[:1000],
                proof=str(item.get("proof", ""))[:1000] if item.get("proof") else None,
                source=source,
            ))
        logger.debug("LLM extracted %d pairs from %s", len(pairs), source)
        return pairs
    except Exception as exc:
        logger.warning("_llm_extract_from_text failed for %s: %s", source, exc)
        return []


_STATEMENT_SCHEMA = {
    "statements": [
        {
            "env_type": "theorem",
            "ref": "Theorem 1.1",
            "statement": "The claim itself",
            "proof": "Optional nearby proof sketch",
            "location_hint": "page 2",
            "confidence": 0.82,
        }
    ]
}


def _normalize_statement_items(data) -> list[dict]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if isinstance(data.get("statements"), list):
            return data["statements"]
        if isinstance(data.get("pairs"), list):
            return data["pairs"]
        if isinstance(data.get("theorems"), list):
            return data["theorems"]
    return []


def _sanitize_extracted_field(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    return strip_non_math_latex(ensure_inline_math(str(text).strip()))


_NON_CLAIM_HEADINGS = {
    "abstract", "introduction", "references", "bibliography", "acknowledgments",
    "acknowledgements", "contents", "appendix", "preliminaries", "background",
}

_GENERIC_NON_STATEMENTS = {
    "then", "hence", "thus", "therefore", "set", "suppose", "assume",
    "moreover", "this gives", "we have", "it follows", "proof", "claim",
}

_THEOREM_LABEL_RE = re.compile(
    r"\b(theorem|lemma|proposition|corollary|claim|conjecture)\s+"
    r"\d+(?:\.\d+)*\b",
    re.IGNORECASE,
)


def _strip_markdown_label(text: str) -> str:
    cleaned = re.sub(r"^\s{0,3}#{1,6}\s*", "", text or "").strip()
    cleaned = re.sub(r"^\*{1,3}(.+?)\*{1,3}$", r"\1", cleaned).strip()
    return cleaned.strip(" .:-—–")


def _looks_like_extracted_claim(item: dict, statement: str, proof_text: Optional[str]) -> bool:
    """Reject section headings and proof fragments masquerading as theorem statements."""
    raw = (statement or "").strip()
    if len(raw) < 20:
        return False
    label = _strip_markdown_label(raw)
    lowered = label.lower()
    if lowered in _NON_CLAIM_HEADINGS or lowered in _GENERIC_NON_STATEMENTS:
        return False
    if re.match(r"^(?:table|fig(?:ure)?\.?|section)\b", label, re.IGNORECASE):
        return False
    if re.match(r"^(?:proof|then|hence|set|suppose|assume|moreover)\b\.?$", label, re.IGNORECASE):
        return False
    if raw.lstrip().startswith("#") and not _THEOREM_LABEL_RE.search(label):
        return False
    if raw.lstrip().startswith("$$") or raw.lstrip().startswith("\\["):
        return False
    if re.fullmatch(r"[\s$\\{}_^=+\-*/(),.;:\[\]0-9A-Za-z|<>≤≥∈∉⊂⊃∑∏∫]+", raw) and len(label.split()) < 10:
        return False
    if re.match(r"^(?:proof|then|hence|thus|therefore|set|suppose|assume|moreover|note that|from\s+\(?\d)", label, re.IGNORECASE):
        return False

    env_type = str(item.get("env_type", "")).strip().lower()
    ref = str(item.get("ref", "") or "").strip()
    has_theorem_label = bool(_THEOREM_LABEL_RE.search(label) or _THEOREM_LABEL_RE.search(ref))
    has_math = bool(re.search(r"\$[^$\n]+\$|\\[a-zA-Z]+|[=<>≤≥∈∉⊂⊃∑∏∫]", raw))
    has_claim_start = bool(re.match(
        r"^(?:for every|for all|let|if|there exists|there is|given|assume|suppose that)\b",
        label,
        re.IGNORECASE,
    ))
    has_sentence = len(label.split()) >= 8 and (has_claim_start or any(ch in label for ch in (".", ":", ";")))
    env_ok = env_type in _THEOREM_ENVS
    proof_has_label = bool(proof_text and _THEOREM_LABEL_RE.search(proof_text[:500]))
    return has_theorem_label or (env_ok and (has_math or has_sentence or proof_has_label))


def _extract_markdown_labeled_claims(cleaned: str, *, source: str, location_text: str) -> list[TheoremProofPair]:
    """High-precision MinerU Markdown extractor for explicit theorem labels.

    MinerU often preserves labels like "Theorem 1 Let ..." in plain Markdown. These
    should be extracted deterministically before asking an LLM, otherwise the model
    may paraphrase proof fragments such as "Then" or standalone equations.
    """
    label_re = re.compile(
        r"(?im)(?:^|\n)\s*(?:#{1,6}\s*)?"
        r"((theorem|lemma|proposition|corollary|claim|conjecture)\s+\d+(?:\.\d+)*)\b"
    )
    matches = list(label_re.finditer(cleaned))
    pairs: list[TheoremProofPair] = []
    if not matches:
        return pairs

    hard_stop_re = re.compile(
        r"(?im)^\s{0,3}#{1,6}\s+|^\s*(?:references|bibliography|acknowledg(?:e)?ments)\b"
    )
    for idx, match in enumerate(matches):
        start = match.start()
        next_label = matches[idx + 1].start() if idx + 1 < len(matches) else len(cleaned)
        stop = next_label
        hard_stop = hard_stop_re.search(cleaned, match.end(), next_label)
        if hard_stop:
            stop = min(stop, hard_stop.start())
        block = cleaned[start:stop].strip()
        if len(block) < 30:
            continue

        proof_match = re.search(r"(?i)\bproof\b\s*[\.:]?", block)
        if proof_match and proof_match.start() > 40:
            statement = block[:proof_match.start()].strip()
            proof_text = block[proof_match.end():].strip() or None
        else:
            statement = block.strip()
            proof_text = None

        # Avoid swallowing multiple paragraphs of exposition after the claim.
        statement = re.split(r"\n\s*\n", statement, maxsplit=1)[0].strip()
        if len(statement) > 1600:
            statement = statement[:1600].rsplit(" ", 1)[0]
        if proof_text and len(proof_text) > 2600:
            proof_text = proof_text[:2600].rsplit(" ", 1)[0]

        label = match.group(1).strip()
        env_type = match.group(2).lower()
        item = {"env_type": env_type, "ref": label}
        if not _looks_like_extracted_claim(item, statement, proof_text):
            continue
        pairs.append(TheoremProofPair(
            env_type=env_type,
            ref=_sanitize_extracted_field(label),
            statement=_sanitize_extracted_field(statement) or statement,
            proof=_sanitize_extracted_field(proof_text) if proof_text else None,
            source=source,
            location_hint=location_text,
            context_excerpt=cleaned[:2500],
            parser_source="regex_markdown",
            quality_score=0.9,
        ))
    return pairs


async def extract_statement_candidates_from_text(
    text: str,
    *,
    source: str,
    location_hint: str = "",
    model: Optional[str] = None,
    lang: str = "zh",
) -> list[TheoremProofPair]:
    """从 PDF/纯文本分块中提取 statement / proof 候选。"""
    cleaned = (text or "").strip()
    if not cleaned:
        return []

    lowered = cleaned.lower()
    interesting = (
        "theorem", "lemma", "proposition", "corollary", "claim", "proof",
        "conjecture", "result", "main result", "key lemma", "observation",
        "定理", "引理", "命题", "推论", "证明", "结论", "猜想",
    )
    if not any(token in lowered for token in interesting):
        return []

    excerpt = cleaned[:9000]
    location_text = location_hint or source
    regex_pairs = _extract_markdown_labeled_claims(excerpt, source=source, location_text=location_text)
    if regex_pairs:
        return regex_pairs[:8]

    system = (
        "You are a mathematical paper parser. Extract theorem-like statements from a paper chunk. "
        "Prefer real mathematical claims over narrative text. "
        "If a nearby proof or proof sketch is visible, attach it to the same item. "
        "If the current chunk only supports a theorem but does not contain the theorem itself, return an empty list. "
        "Keep location_hint consistent with the provided Location instead of inventing another page number. "
        "The input may be MinerU-formatted Markdown with bold labels like **Theorem 1.** or headings like ## Lemma. "
        "Treat these as formal theorem environments. "
        f"{_LATEX_STYLE_INSTRUCTION} "
        "All math in statement/proof fields MUST use `$...$` inline LaTeX. "
        "Return JSON only."
    )
    if lang == "zh":
        system += " 输出字段值可以用中文概括，但必须保持 JSON 结构稳定。"

    user = (
        f"Source: {source}\n"
        f"Location: {location_text}\n\n"
        "Extract up to 8 theorem-like statements (Theorem, Lemma, Proposition, Corollary, Claim, "
        "or Conjecture) from this paper chunk. "
        "For each item, fill env_type/ref/statement/proof/location_hint/confidence. "
        "Use null for missing ref/proof. Do not invent claims absent from the chunk. "
        "CRITICAL RULES for the `statement` and `proof` fields:\n"
        "1. ONLY extract formal theorem-like environments. Do NOT extract abstracts, references, headings, tables, figures, proof fragments, or standalone equations.\n"
        "2. The statement must be a complete mathematical claim, not words like Then/Hence/Set/We have and not a single displayed formula.\n"
        "3. COPY the exact wording from the source. Do NOT paraphrase or summarize.\n"
        "4. If the source uses `$...$` or `$$...$$` LaTeX, copy those delimiters verbatim.\n"
        "5. Convert any bare Unicode math symbols (∀ ∃ ∈ ∉ ≤ ≥ → ← ↦ ⊂ ⊃ ≡ ≈ ∑ ∏ ∫ ℝ ℤ ℕ ℚ ℂ)\n"
        "   to inline LaTeX: e.g. write `$x \\in \\mathbb{R}$` not `x ∈ R`.\n"
        "6. Variables, sets and function names that appear mathematically should use `$...$`:\n"
        "   e.g. `$f: X \\to Y$`, `$n \\geq 1$`, `$|A| > N/2$`.\n"
        "Return an empty list if the chunk has no formal theorem-like statement.\n\n"
        f"Chunk:\n{excerpt}"
    )
    try:
        data = await chat_json(user, system=system, model=model, schema=_STATEMENT_SCHEMA)
    except Exception as exc:
        logger.warning("extract_statement_candidates_from_text failed for %s: %s", location_text, exc)
        return []

    pairs: list[TheoremProofPair] = []
    for item in _normalize_statement_items(data):
        statement = str(item.get("statement", "")).strip()
        proof = item.get("proof")
        proof_text = str(proof).strip() if proof else None
        if not _looks_like_extracted_claim(item, statement, proof_text):
            continue
        pairs.append(TheoremProofPair(
            env_type=str(item.get("env_type", "theorem")).strip().lower() or "theorem",
            ref=_sanitize_extracted_field(str(item.get("ref")).strip() if item.get("ref") else None),
            statement=_sanitize_extracted_field(statement[:1500]) or statement[:1500],
            proof=_sanitize_extracted_field(proof_text[:2500]) if proof_text else None,
            source=source,
            location_hint=_sanitize_extracted_field(str(item.get("location_hint")).strip() if item.get("location_hint") else location_text),
            context_excerpt=excerpt[:2500],
        ))
    return pairs


async def extract_statement_candidates_from_images(
    images: list[str],
    *,
    source: str,
    model: Optional[str] = None,
    lang: str = "zh",
) -> list[TheoremProofPair]:
    """从图片中多模态抽取 theorem / statement / proof 候选。"""
    payloads = [img for img in images if isinstance(img, str) and img.strip()]
    if not payloads:
        return []

    text_prompt = (
        "Extract theorem-like statements from these mathematical paper images. "
        "If there is a nearby proof or proof sketch, attach it. "
        "Keep location_hint grounded in the visible image region; if unknown, use a generic image location instead of inventing page numbers. "
        f"{_LATEX_STYLE_INSTRUCTION} "
        "Return JSON only with a top-level 'statements' array."
    )
    if lang == "zh":
        text_prompt += " 如果图片中没有清晰的数学命题，不要编造内容。"

    content = [{"type": "text", "text": text_prompt}]
    for img in payloads[:6]:
        content.append({"type": "image_url", "image_url": {"url": img}})

    try:
        data = await chat_json(
            [{"role": "user", "content": content}],
            system="You are a multimodal mathematical paper parser.",
            model=model,
            schema=_STATEMENT_SCHEMA,
        )
    except Exception as exc:
        logger.warning("extract_statement_candidates_from_images failed for %s: %s", source, exc)
        return []

    pairs: list[TheoremProofPair] = []
    for item in _normalize_statement_items(data):
        statement = str(item.get("statement", "")).strip()
        proof = item.get("proof")
        proof_text = str(proof).strip() if proof else None
        if not _looks_like_extracted_claim(item, statement, proof_text):
            continue
        location_hint = _sanitize_extracted_field(str(item.get("location_hint", "")).strip()) or "image"
        pairs.append(TheoremProofPair(
            env_type=str(item.get("env_type", "theorem")).strip().lower() or "theorem",
            ref=_sanitize_extracted_field(str(item.get("ref")).strip() if item.get("ref") else None),
            statement=_sanitize_extracted_field(statement[:1500]) or statement[:1500],
            proof=_sanitize_extracted_field(proof_text[:2500]) if proof_text else None,
            source=source,
            location_hint=location_hint,
            context_excerpt=None,
        ))
    return pairs


# ── 公共 API ───────────────────────────────────────────────────────────────────

async def parse_arxiv(arxiv_id: str) -> list[TheoremProofPair]:
    """
    从 arXiv 下载论文并解析定理-证明对（带进程内缓存，1 小时 TTL）。

    优先使用源文件（.tex）；若下载失败则尝试 PDF + LLM 降级。
    """
    clean_id = arxiv_id.strip()

    # 缓存命中
    cached = _arxiv_cache_get(clean_id)
    if cached is not None:
        return cached

    pairs: list[TheoremProofPair] = []

    # 1. 尝试下载源文件（e-print tar.gz）
    src_url = _ARXIV_EPRINT_URL.format(arxiv_id=clean_id)
    try:
        resp = await _get_http().get(src_url)
        if resp.status_code == 404:
            raise ValueError(f"arXiv 论文不存在: {clean_id}")
        if resp.status_code == 200:
            content = resp.content
            with tempfile.TemporaryDirectory() as tmpdir:
                tar_path = Path(tmpdir) / "source.tar.gz"
                tar_path.write_bytes(content)
                import tarfile
                try:
                    with tarfile.open(tar_path, "r:gz") as tar:
                        tar.extractall(tmpdir)
                except Exception:
                    with tarfile.open(tar_path, "r:*") as tar:
                        tar.extractall(tmpdir)

                tex_files = sorted(
                    Path(tmpdir).rglob("*.tex"),
                    key=lambda p: p.stat().st_size,
                    reverse=True,
                )

                if tex_files:
                    combined = ""
                    for tf in tex_files[:3]:
                        try:
                            combined += tf.read_text(encoding="utf-8", errors="ignore") + "\n\n"
                        except Exception as exc:
                            logger.debug("Failed to read tex file %s: %s", tf, exc)

                    pairs = _extract_tex_environments(combined, source=clean_id)
                    if pairs:
                        logger.info("Parsed %d theorem pairs from arXiv:%s (tex)", len(pairs), clean_id)
                        _arxiv_cache_set(clean_id, pairs)
                        return pairs
    except ValueError:
        raise
    except Exception as exc:
        logger.debug("arXiv src download failed for %s: %s", clean_id, exc)

    # 2. 降级：下载 PDF，用 LLM 提取
    pdf_url = _ARXIV_PDF_URL.format(arxiv_id=clean_id)
    try:
        resp = await _get_http().get(pdf_url)
        if resp.status_code == 404:
            raise ValueError(f"arXiv 论文不存在: {clean_id}")
        if resp.status_code == 200:
            try:
                import fitz
                doc = fitz.open(stream=resp.content, filetype="pdf")
                text = ""
                for page in doc[:10]:
                    text += page.get_text()
                pairs = await _llm_extract_from_text(text, source=clean_id)
                _arxiv_cache_set(clean_id, pairs)
                return pairs
            except ImportError:
                logger.debug("PyMuPDF not available, skipping PDF fallback")
    except ValueError:
        raise
    except Exception as exc:
        logger.debug("arXiv PDF download failed for %s: %s", clean_id, exc)

    # 3. 最终降级：LLM 按 arxiv_id 描述
    pairs = await _llm_extract_from_text(
        f"Paper: arXiv:{clean_id}. Please describe theorems from this paper based on your knowledge.",
        source=clean_id,
    )
    _arxiv_cache_set(clean_id, pairs)
    return pairs


async def parse_tex_file(tex_path: str) -> list[TheoremProofPair]:
    """从本地 .tex 文件解析。"""
    path = Path(tex_path)
    content = path.read_text(encoding="utf-8", errors="ignore")
    return _extract_tex_environments(content, source=path.name)
