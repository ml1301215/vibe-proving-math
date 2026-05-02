# Developer Guide

Project conventions for contributors and AI assistants.

## Project Structure

```
app/
  api/server.py          HTTP endpoints and SSE protocol
  core/                  Configuration, LLM, theorem search, memory, text sanitization
  modes/                 learning / research / formalization
  skills/                Reusable capabilities (proof, verification, retrieval)
  ui/                    Single-page frontend (HTML/CSS/JS with ?v= cache busting)
  tests/                 pytest suite (-m "not slow" for fast regression)
```

## Development Workflow

### Dependencies
- Python: Use virtual environment
- Frontend: CDN-loaded libraries (KaTeX, marked); **no npm build chain**
- New dependencies require justification in PR and update to `requirements.txt`

### Editing Rules

1. **Frontend cache busting**: After editing `app/ui/app.js`, increment `?v=` version in `app/ui/index.html`
2. **Backend changes**: Restart uvicorn for changes to `app/api/server.py` or `app/modes/`
3. **Comments**: Only explain non-obvious "why", not "what"

### LaTeX Sanitization (Required)

All user-facing strings pass through `app/core/text_sanitize.py`:
- Preserve `$...$` and `$$...$$` for KaTeX
- Strip `\label`, `\cite`, `\ref`, `\textbf`, `\begin...\end` and other non-display sequences
- New API fields must include sanitization with test coverage

### Streaming Output

Long tasks use Server-Sent Events with comment frames: `<!--vp-status:...-->`, `<!--vp-result:...-->`, `<!--vp-final:...-->`. Frontend parses via `fetch` + `ReadableStream`.

## Testing

```bash
cd app
python -m pytest tests -m "not slow"
```

Tests marked `slow` require external API keys (LLM, TheoremSearch, OCR).

## Running the Server

```bash
cd app
python -m uvicorn api.server:app --host 127.0.0.1 --port 8080
```

Access: `http://127.0.0.1:8080/ui/`, `http://127.0.0.1:8080/docs`, `http://127.0.0.1:8080/health`

## Communication (For AI Assistants)

- Use **Simplified Chinese** when communicating with users
- Execute operations directly without preamble
