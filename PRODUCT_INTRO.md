# Product Overview

`vibe_proving` is a mathematical reasoning system designed around five modes: learning, solving, reviewing, searching, and formalizing. It combines language models with external verification mechanisms to reduce hallucination in mathematical contexts.

## Architecture

The system implements a pipeline where generation is followed by independent verification:

1. **Generator** — Produces initial proofs or explanations
2. **Verifier** — Evaluates steps without access to generator's reasoning chain
3. **Reviser** — Incorporates feedback to repair errors
4. **Citation Checker** — Queries TheoremSearch for theorem verification
5. **Counterexample Engine** — Attempts to falsify claims before accepting them

This architecture is informed by [Aletheia](https://arxiv.org/abs/2602.10177) and related work on reducing confirmation bias in automated reasoning.

## Modes

### Learning Mode
Generates structured mathematical explanations:
- Prerequisites (definitions, background theorems)
- Proof outline with annotations
- Worked examples
- Extensions and related results

Target audience: Students and researchers encountering unfamiliar material.

### Solving Mode
Proof generation pipeline:
1. Direct retrieval (check if problem already solved)
2. Proof generation with step-by-step verification
3. Citation checking via TheoremSearch
4. Counterexample testing (for conjectures)
5. Confidence scoring and verdict (`proved`, `counterexample`, `partial`, `no_confident_solution`)

Returns structured output with references, obstacles, and failed paths.

### Review Mode
Structured analysis of mathematical writing:
- Logic gap detection (missing steps, circular reasoning)
- Citation accuracy (theorem existence and relevance)
- Symbol consistency (variable scope, assumption tracking)

Supports text, LaTeX, images (via multimodal models), and PDF (via OCR).

### Search Mode
Semantic search over 9M+ theorems from arXiv, Stacks Project, and other sources via [TheoremSearch](https://www.theoremsearch.com).

### Formalization Mode (Beta)
Natural language → Lean 4 translation:
1. Keyword extraction from natural language statement
2. Mathlib retrieval for relevant definitions and lemmas
3. Blueprint planning (proof structure)
4. Code generation
5. Verification (local or remote)
6. Iterative repair based on compiler errors

Currently experimental; requires further benchmarking.

## Technical Stack

- **Backend**: FastAPI with Server-Sent Events for streaming
- **Frontend**: Vanilla HTML/CSS/JS (no build toolchain)
- **LLM Integration**: OpenAI-compatible interface (supports DeepSeek, Gemini, OpenAI, etc.)
- **Citation Verification**: TheoremSearch API
- **PDF Parsing**: Nanonets OCR (primary), with fallback options
- **Formal Verification**: Lean 4 + Mathlib via remote verifier

## Quality Control

Multiple layers prevent common failure modes:
- **Citation hallucination**: External theorem database lookup
- **Logical errors**: Independent verification step
- **False claims**: Counterexample generation
- **LaTeX issues**: Automatic sanitization of control sequences
- **Confidence reporting**: System refuses to answer when uncertain

## Deployment

Configuration via `config.toml` (copy from `config.example.toml`). Minimum requirement: LLM API key. Optional services (TheoremSearch, OCR, memory system) enhance functionality but are not required for basic operation.

```bash
cd app
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config.example.toml config.toml
# Edit config.toml: set [llm].api_key
python -m uvicorn api.server:app --host 127.0.0.1 --port 8080
```

## Testing

```bash
pytest tests -m "not slow"  # Fast regression
pytest tests                # Full suite (requires API keys)
```

Test coverage includes:
- Configuration parsing
- LLM client integration
- All five modes (learning, solving, reviewing, searching, formalizing)
- Citation verification
- LaTeX sanitization
- Error handling

## Current Status

| Module | Status | Notes |
|--------|--------|-------|
| Learning | Stable | Streaming explanations with memory integration |
| Solving | Stable | GVR pipeline with citation checking |
| Review | Stable | Quality depends on OCR/parsing backend |
| Search | Stable | Direct TheoremSearch integration |
| Formalization | Beta | Requires expanded benchmark evaluation |

## Design Constraints

1. **Verification over trust**: Never accept model outputs without external checks when verification is available
2. **Transparency**: Return confidence scores and failed paths, not just final answers
3. **Academic rigor**: Optimize for correctness over speed
4. **Local-first**: Minimize cloud dependencies where feasible
5. **Open integration**: Standard interfaces (OpenAI API, REST) over proprietary formats

## Comparison with Alternatives

**vs. General LLM Chatbots**: Adds citation checking, proof verification, and structured workflows

**vs. Wolfram Alpha**: Handles abstract proofs beyond symbolic computation

**vs. Lean Prover**: Provides natural language interface and automated formalization

**vs. arXiv**: Offers semantic search and structured proof analysis

## Future Directions

- Expand Lean formalization benchmark
- Improve PDF parsing reliability
- Add collaborative features (team projects, shared knowledge bases)
- Integrate additional theorem databases
- Support for proof assistants beyond Lean (Coq, Isabelle)

## References

- [TheoremSearch](https://www.theoremsearch.com) — Theorem database
- [Aletheia](https://arxiv.org/abs/2602.10177) — Generator–Verifier–Reviser architecture
- [LATRACE](https://github.com/zxxz1000/LATRACE) — Memory system
- [Lean 4](https://lean-lang.org) — Proof assistant
- [Mathlib](https://leanprover-community.github.io) — Lean mathematics library
