![vibe_proving](assets/banner.svg)

<p align="center">
Mathematical reasoning system with language models and formal verification.
</p>

<p align="center">
<a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License"></a>
<a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python"></a>
</p>

<p align="center">
<a href="README.zh.md">中文</a> | English
</p>

---

## Capabilities

- **Learning** — Layered explanations with prerequisites and examples
- **Solving** — Proof generation with citation verification and counterexample detection
- **Review** — Structured analysis of mathematical writing (PDF/LaTeX/images)
- **Search** — Semantic retrieval across 9M+ theorems
- **Formalization** — Natural language to Lean 4 translation

![Interface](assets/screenshot.png)

---

## Installation

```bash
git clone https://github.com/ml1301215/vibe-proving-math.git
cd vibe-proving-math/app
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp config.example.toml config.toml
# Edit config.toml: set [llm].api_key
python -m uvicorn api.server:app --host 127.0.0.1 --port 8080
```

Open `http://127.0.0.1:8080/ui/` or `http://127.0.0.1:8080/docs` for API documentation.

**LLM Configuration**: Supports any OpenAI-compatible endpoint.

| Provider | Base URL | Key |
|----------|----------|-----|
| DeepSeek | `https://api.deepseek.com/v1` | [platform.deepseek.com](https://platform.deepseek.com/api_keys) |
| Gemini | `https://generativelanguage.googleapis.com/v1beta/openai` | [aistudio.google.com](https://aistudio.google.com/apikey) |
| OpenAI | `https://api.openai.com/v1` | [platform.openai.com](https://platform.openai.com/api-keys) |

Configuration via web UI is also supported.

---

## Architecture

```
Web UI / API Clients
         │
    ┌────▼────────────────────────────────┐
    │         FastAPI Server              │
    │  /learn  /solve  /review  /search   │
    └────┬────────────────────────────────┘
         │
    ┌────▼────┬────────┬─────────┬────────┐
    │Learning │Solving │ Review  │Formal. │
    └────┬────┴────┬───┴────┬────┴────┬───┘
         │         │        │         │
    ┌────▼─────────▼────────▼─────────▼───┐
    │  LLM Core  │  TheoremSearch  │  OCR  │
    └────────────┴─────────────────┴───────┘
```

**Quality Control**: Citation verification, step-by-step validation, counterexample generation, and LaTeX sanitization reduce hallucination.

---

## API Reference

Complete documentation at `/docs`. Core endpoints:

| Endpoint | Purpose |
|----------|---------|
| `/learn` | Generate structured explanations |
| `/solve` | Proof generation with verification |
| `/review_stream` | Streaming proof review |
| `/review_pdf_stream` | PDF upload and analysis |
| `/formalize` | Natural language → Lean 4 |
| `/search` | Theorem retrieval |

**Example**:

```bash
curl -X POST http://127.0.0.1:8080/solve \
  -H "Content-Type: application/json" \
  -d '{"statement": "Prove: For all primes p > 2, p is odd"}'
```

Returns structured proof with confidence score and verified citations.

---

## Testing

```bash
cd app
pytest tests -m "not slow"  # Fast regression
pytest tests                # Full suite (requires API keys)
```

---

## Technical Details

- **Streaming**: Server-Sent Events for progressive updates
- **Citation Checking**: TheoremSearch integration prevents hallucinated references
- **Verification**: Independent proof validation
- **Formalization**: Multi-stage Lean generation with automated repair
- **LaTeX Handling**: Automatic sanitization for frontend rendering

See [PRODUCT_INTRO.md](PRODUCT_INTRO.md) for architecture details.

---

## Contributing

- Issues and requests: [GitHub Issues](https://github.com/ml1301215/vibe-proving-math/issues)
- Development: Follow [CLAUDE.md](CLAUDE.md) conventions
- Pull requests welcome

---

## Acknowledgments

- [TheoremSearch](https://www.theoremsearch.com) — Citation verification
- [Aletheia](https://arxiv.org/abs/2602.10177) — Generator–Verifier–Reviser
- [LATRACE](https://github.com/zxxz1000/LATRACE) — Memory system
- [Rethlas](https://github.com/frenzymath/Rethlas) — Architecture inspiration

---

## License

[MIT](LICENSE)
