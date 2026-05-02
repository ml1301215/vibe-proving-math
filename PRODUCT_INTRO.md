# Product Overview

`vibe_proving` is an AI platform for students and researchers in mathematics. It integrates language models with theorem retrieval to support interactive workflows across learning, problem-solving, proof review, and knowledge discovery.

## Design Philosophy

Unlike general-purpose AI assistants, vibe_proving prioritizes mathematical correctness through external verification:

1. **Citation Verification** — Language model outputs are cross-checked against theorem databases
2. **Independent Validation** — Proof steps are verified without access to generator reasoning
3. **Counterexample Generation** — Active falsification attempts before accepting claims
4. **Confidence Reporting** — Transparent uncertainty assessment with explicit confidence scores
5. **Theorem Retrieval** — Semantic search across 9M+ indexed theorems from mathematical literature

This architecture reduces hallucination risk in mathematical contexts where accuracy is critical.

## Core Capabilities

### Learning Mode

Generates structured mathematical explanations:
- **Prerequisites**: Background definitions and required theorems
- **Proof Walkthrough**: Step-by-step reasoning with annotations
- **Examples**: Concrete instances and counterexamples
- **Extensions**: Related results and generalizations

Target difficulty levels: undergraduate or graduate.

### Solving Mode

Proof generation pipeline with verification:
1. **Direct Retrieval**: Check if problem already solved in theorem databases
2. **Proof Generation**: Create initial draft with reasoning steps
3. **Independent Verification**: Validate logic without generator bias
4. **Citation Checking**: Verify theorem references via TheoremSearch
5. **Counterexample Testing**: Attempt to falsify claims before accepting
6. **Confidence Scoring**: Transparent assessment with explicit uncertainty

Output includes structured proof, verified citations, failed paths, and reasoning obstacles.

### Review Mode

Structured analysis of mathematical writing:
- **Logic Consistency**: Detect missing steps, circular reasoning, unjustified leaps
- **Citation Accuracy**: Verify referenced theorems exist and are correctly stated
- **Symbol Consistency**: Track variable scope and assumption dependencies

Supported formats: text, LaTeX, images (via vision models), PDF (via OCR).

### Search Mode

Semantic theorem retrieval:
- 9M+ theorems indexed from arXiv, Stacks Project, and specialized databases
- Natural language queries without formula syntax requirements
- Similarity scoring and ranking
- Direct links to original papers

### Formalization

Natural language → Lean 4 translation:
1. Keyword extraction from natural language statement
2. Mathlib retrieval for relevant definitions and lemmas
3. Blueprint planning (proof structure)
4. Code generation
5. Verification (local or remote)
6. Iterative repair based on compiler errors

## Technical Architecture

```
Web Interface (HTML/CSS/JS + KaTeX)
         │
    FastAPI Server
         │
  ┌──────┴──────┬──────────┬─────────┐
  │             │          │         │
Learning    Solving    Review    Search
Pipeline    Pipeline   Pipeline  Pipeline
  │             │          │         │
  └─────────────┴──────────┴─────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
 LLM Core   TheoremSearch  Nanonets
(OpenAI)    (Citation)      (OCR)
```

### Components

1. **External Citation Database**: TheoremSearch API prevents hallucinated references
2. **Independent Verification**: Proof validator operates without generator context
3. **Counterexample Engine**: Active falsification before claiming truth
4. **LaTeX Sanitization**: Automatic cleaning for frontend rendering
5. **Confidence Thresholds**: System refuses to answer when uncertain

## Technical Stack

- **Backend**: FastAPI with Server-Sent Events for progressive streaming
- **Frontend**: Vanilla HTML/CSS/JS (no build toolchain)
- **LLM Integration**: OpenAI-compatible interface (model-agnostic)
- **Theorem Database**: TheoremSearch API
- **PDF Processing**: Nanonets OCR for formula-preserving extraction
- **Formalization**: Harmonic Aristotle for Lean 4

## Deployment

Configuration via `config.toml` or web interface (recommended):

```toml
[llm]
base_url = "https://api.deepseek.com/v1"
api_key = "your-key"
model = "deepseek-chat"

[theorem_search]
base_url = "https://api.theoremsearch.com"

[nanonets]
api_key = "your-key"  # Optional, for PDF review
```

Minimum requirement: LLM API key. Optional services enhance functionality but are not required for core operations.

## Design Constraints

1. **Verification Over Trust**: Never accept model outputs without external checks when verification is available
2. **Transparency**: Return confidence scores and failed paths, not just final answers
3. **Academic Rigor**: Optimize for correctness over speed
4. **Local-First**: Minimize cloud dependencies where feasible
5. **Open Integration**: Standard interfaces (OpenAI API, REST) over proprietary formats

## Comparison

**vs. General LLM Chatbots**: Adds citation checking, proof verification, and structured workflows

**vs. Wolfram Alpha**: Handles abstract proofs beyond symbolic computation

**vs. arXiv**: Offers semantic search and structured proof analysis

**vs. Lean Prover**: Provides natural language interface without formal syntax requirements

## Future Development

- Expand theorem database coverage
- Improve PDF parsing reliability
- Add collaborative features (team projects, shared knowledge bases)
- Support for additional proof assistants

## References

- [TheoremSearch](https://www.theoremsearch.com) — Theorem database and citation verification
- [Aletheia](https://arxiv.org/abs/2602.10177) — Generator–Verifier–Reviser architecture
- [LATRACE](https://github.com/zxxz1000/LATRACE) — Long-term memory system
- [Nanonets](https://nanonets.com) — Formula-aware PDF extraction
- [Harmonic Aristotle](https://aristotle.harmonic.fun) — Lean 4 formalization
- [Research Math Assistant](https://github.com/ml1301215/research-math-assistant) — Community resources
