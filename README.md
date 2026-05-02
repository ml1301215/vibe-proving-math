![vibe_proving](assets/banner.svg)

<p align="center">
A mathematical reasoning system combining language models with formal verification.
</p>

<p align="center">
<a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License"></a>
<a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python"></a>
</p>

---

## Overview

`vibe_proving` implements five modes of mathematical assistance:

- **Learning** — Generate layered explanations with prerequisites, proofs, and examples
- **Solving** — Generator–Verifier–Reviser pipeline with citation checking and counterexample detection
- **Review** — Structured analysis of proofs and papers (PDF/LaTeX/images) for logic gaps and citation accuracy
- **Search** — Semantic retrieval across 9M+ theorems from arXiv, Stacks Project, and other sources
- **Formalization** — Natural language to Lean 4 translation with automated verification and repair

![Interface](assets/screenshot.png)

---

## Installation

```bash
git clone https://github.com/ml1301215/vibe-proving-math.git
cd vibe-proving-math/app
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp config.example.toml config.toml
# Edit config.toml: set [llm].api_key at minimum
python -m uvicorn api.server:app --host 127.0.0.1 --port 8080
```

Visit `http://127.0.0.1:8080/ui/` for the web interface, or `http://127.0.0.1:8080/docs` for API documentation.

**LLM Configuration**: The system accepts any OpenAI-compatible endpoint. Recommended providers:

| Provider | Base URL | Key |
|----------|----------|-----|
| DeepSeek | `https://api.deepseek.com/v1` | [platform.deepseek.com](https://platform.deepseek.com/api_keys) |
| Gemini | `https://generativelanguage.googleapis.com/v1beta/openai` | [aistudio.google.com](https://aistudio.google.com/apikey) |
| OpenAI | `https://api.openai.com/v1` | [platform.openai.com](https://platform.openai.com/api-keys) |

Alternatively, configure via the web UI settings panel after startup.

---

## Architecture

```
┌─────────────┐
│   Web UI    │────┐
└─────────────┘    │
┌─────────────┐    │    ┌──────────────────────────────────────┐
│ API Clients │────┼───→│         FastAPI Server               │
└─────────────┘    │    │  /learn  /solve  /review  /formalize │
                   │    └──────────────────────────────────────┘
                   │                     │
                   │         ┌───────────┼───────────┬─────────┐
                   │         ▼           ▼           ▼         ▼
                   │    ┌────────┐  ┌────────┐  ┌────────┐  ┌──────────┐
                   │    │Learning│  │Solving │  │ Review │  │Formaliz. │
                   │    └────────┘  └────────┘  └────────┘  └──────────┘
                   │         │           │           │           │
                   │         └───────────┴───────────┴───────────┘
                   │                     │
                   │         ┌───────────┼──────────────┬──────────────┐
                   │         ▼           ▼              ▼              ▼
                   │    ┌────────┐  ┌──────────┐  ┌─────────┐  ┌──────────┐
                   └───→│  LLM   │  │ Theorem  │  │   OCR   │  │   Lean   │
                        │  Core  │  │  Search  │  │  (PDF)  │  │ Verifier │
                        └────────┘  └──────────┘  └─────────┘  └──────────┘
```

**Quality Control**: Citation verification via TheoremSearch, step-by-step proof checking, counterexample generation, and LaTeX sanitization prevent common failure modes.

---

## API Reference

Complete documentation at `/docs`. Core endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/learn` | POST | Generate structured explanations (background, prerequisites, proof, examples, extensions) |
| `/solve` | POST | Proof generation with verification, citation checking, and confidence scoring |
| `/review_stream` | POST | Streaming proof review (text/LaTeX/images) |
| `/review_pdf_stream` | POST | PDF upload and structured analysis |
| `/formalize` | POST | Natural language → Lean 4 with iterative repair |
| `/search` | GET | Theorem retrieval by semantic similarity |
| `/health` | GET | Service status and dependency checks |
| `/config/llm` | POST | Runtime LLM configuration updates |

**Example** (Solving mode):

```bash
curl -X POST http://127.0.0.1:8080/solve \
  -H "Content-Type: application/json" \
  -d '{"statement": "Prove: There are infinitely many primes"}'
```

Returns structured proof with confidence score, verified citations, and potential obstacles.

---

## Testing

```bash
cd app
python -m pytest tests -m "not slow"  # Fast regression tests
python -m pytest tests                # Full suite (requires API keys)
```

Tests cover configuration parsing, LLM integration, all five modes, citation verification, and output sanitization.

---

## Technical Notes

- **Streaming**: Server-Sent Events for long-running tasks with progressive status updates
- **Citation Checking**: TheoremSearch integration prevents hallucinated references
- **Verification**: Independent proof validation reduces confirmation bias
- **Formalization**: Multi-stage Lean generation (keyword extraction → Mathlib retrieval → blueprint planning → code generation → verification → repair)
- **LaTeX Handling**: Automatic sanitization preserves math environments while removing unsupported control sequences

Full design documentation in [PRODUCT_INTRO.md](PRODUCT_INTRO.md).

---

## Contributing

- Bug reports and feature requests: [GitHub Issues](https://github.com/ml1301215/vibe-proving-math/issues)
- Code contributions: Follow conventions in [CLAUDE.md](CLAUDE.md)
- Documentation improvements welcome

**Development Guidelines**:
- Python code follows PEP 8
- Frontend changes to `app.js` require incrementing `?v=` in `index.html`
- LaTeX output must pass through `text_sanitize.py`
- New endpoints require test coverage

---

## Acknowledgments

- [TheoremSearch](https://www.theoremsearch.com) — Citation verification
- [Aletheia](https://arxiv.org/abs/2602.10177) — Generator–Verifier–Reviser architecture
- [LATRACE](https://github.com/zxxz1000/LATRACE) — Memory system
- [Lean 4](https://lean-lang.org) & [Mathlib](https://leanprover-community.github.io) — Formal verification

---

## License

[MIT](LICENSE)

---

## Contact

**Project**: [github.com/ml1301215/vibe-proving-math](https://github.com/ml1301215/vibe-proving-math)  
**Issues**: [GitHub Issues](https://github.com/ml1301215/vibe-proving-math/issues)
