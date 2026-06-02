# vibe-proving

A FastAPI web application for mathematical problem-solving and proof assistance. Paper: [arXiv:2602.13695](https://arxiv.org/abs/2602.13695).

The core of the system is a Generator–Verifier–Reviser loop for proof search: the generator produces a candidate proof, the verifier cross-checks citations against TheoremSearch (9M+ theorems indexed from arXiv and Stacks Project), and the reviser patches gaps before returning a confidence-scored result. All modes stream output over SSE.

## Modes

| Mode | What it does |
|------|-------------|
| Solving | GVR loop: generate → verify citations → revise → confidence score |
| Learning | Explanation with prerequisites, proof, examples, extensions at undergraduate or graduate level |
| Review | Checks logic consistency, citation accuracy, symbol scope; accepts LaTeX/PDF/image |
| Search | Semantic search over 9M+ theorem database |
| Formalization | Lean 4 code generation via Harmonic Aristotle with Mathlib verification |

## Architecture

```
app/
├── api/server.py           # FastAPI entry point, SSE endpoints
├── core/
│   ├── llm.py              # OpenAI-compatible client (DeepSeek / Gemini / OpenAI)
│   ├── theorem_search.py   # TheoremSearch API for citation checks
│   ├── config.py           # TOML config loader
│   ├── user_store.py       # SQLite auth: sessions, per-user quotas
│   └── memory.py           # Conversation state
├── modes/
│   ├── research/           # GVR solving pipeline
│   │   ├── solver.py       # Generator stage
│   │   ├── reviewer.py     # Verifier stage
│   │   └── agent/          # Reviser + orchestration
│   ├── learning/           # Explanation pipeline
│   └── formalization/      # Lean 4 pipeline via Aristotle
└── skills/                 # Shared tool definitions
```

## Requirements

Python 3.11+ or Docker. An OpenAI-compatible LLM API key is required.

## Setup

### Docker

```bash
git clone https://github.com/ml1301215/vibe-proving-math.git
cd vibe-proving-math
cp app/config.example.toml app/config.toml
# Edit config.toml: set superuser_password and llm.api_key
docker compose up -d
```

Access at `http://localhost:8080/ui/`.

### Local

```bash
git clone https://github.com/ml1301215/vibe-proving-math.git
cd vibe-proving-math
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp app/config.example.toml app/config.toml
# Edit config.toml
cd app && python -m uvicorn api.server:app --host 127.0.0.1 --port 8080
```

## Configuration

Minimal `config.toml`:

```toml
[auth]
superuser_password = "your-password"

[llm]
base_url = "https://api.deepseek.com/v1"
api_key  = "sk-..."
model    = "deepseek-chat"
```

Optional: `[nanonets]` for PDF OCR, `[aristotle]` for Lean 4 formalization, `[mineru]` for MinerU extraction.

The superuser manages API settings from the settings panel. Registered users get a configurable default quota (default: 50 requests).

## Author

Lve Meng — [ml130@mail.ustc.edu.cn](mailto:ml130@mail.ustc.edu.cn)

## License

MIT
