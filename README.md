<div align="center">

![vibe_proving](assets/banner.jpg)

# 𝒱𝒾𝒷ℯ 𝒫𝓇ℴ𝓋𝒾𝓃ℊ

<p>
AI-driven mathematical research assistant for students and researchers
</p>

<p>
<a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License"></a>
<a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python"></a>
</p>

<p>
<a href="README.zh.md">中文</a> | English
</p>

</div>

---

## Overview

**vibe_proving** is an AI platform designed for students and researchers in mathematics. It combines language models with theorem retrieval to provide interactive workflows for learning, problem-solving, proof review, and knowledge discovery.

### Core Capabilities

<div align="center">
<img src="assets/screenshot_en.png" alt="Interface" style="border-radius: 12px; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12); border: 1px solid rgba(255, 255, 255, 0.18);" width="90%">
</div>

<br>

- **Learning Mode** — Generate structured explanations with prerequisites, proofs, examples, and extensions
- **Solving Mode** — Automated proof generation with citation verification and confidence scoring
- **Review Mode** — Structured analysis of mathematical writing (LaTeX/PDF/images)
- **Search Mode** — Semantic search across 9M+ theorems from arXiv and mathematical databases

### Video Demonstrations

<table>
<tr>
<td width="50%" align="center">

**Learning Mode**  
[![▶️ Learning Mode](assets/screenshot_en.png)](https://github.com/user-attachments/assets/ff33ef0e-b330-4d79-bb06-3a0c4cd9f920)  
*Click to play video*

</td>
<td width="50%" align="center">

**Problem Solving**  
[![▶️ Problem Solving](assets/screenshot_en.png)](https://github.com/user-attachments/assets/ce5e17b3-e9e9-45ce-a038-c2b6b672d440)  
*Click to play video*

</td>
</tr>
<tr>
<td width="50%" align="center">

**Proof Review**  
[![▶️ Proof Review](assets/screenshot_en.png)](https://github.com/user-attachments/assets/eec047a3-c791-4938-a4fc-5e322ccfb2da)  
*Click to play video*

</td>
<td width="50%" align="center">

**Literature Search**  
[![▶️ Literature Search](assets/screenshot_en.png)](https://github.com/user-attachments/assets/588b3f73-7b4f-4040-acd2-d7243c10b3dc)  
*Click to play video*

</td>
</tr>
<tr>
<td width="50%" align="center">

**Formalization**  
[![▶️ Formalization](assets/screenshot_en.png)](https://github.com/user-attachments/assets/3dd05428-e023-4903-bb6b-0cc2e7dad42c)  
*Click to play video*

</td>
<td width="50%">

</td>
</tr>
</table>

---

## Key Features

### 1. Interactive Learning

Transform mathematical statements into comprehensive learning resources:
- Background context and motivation
- Prerequisite knowledge with definitions
- Step-by-step proof walkthrough
- Concrete examples and counterexamples
- Extensions and related topics

Target difficulty levels: undergraduate or graduate.

### 2. Intelligent Problem Solving

Generator–Verifier–Reviser pipeline:
- Direct retrieval from theorem databases
- Proof generation with reasoning steps
- Independent verification
- Citation checking via [TheoremSearch](https://www.theoremsearch.com)
- Counterexample testing
- Confidence scoring with explicit uncertainty

### 3. Proof Review

Automated analysis:
- **Logic Consistency**: Detect missing steps, circular reasoning
- **Citation Accuracy**: Verify referenced theorems
- **Symbol Consistency**: Track variable scope

Supported formats: Text, LaTeX, images (via vision models), PDF (via OCR).

### 4. Theorem Discovery

Semantic search:
- 9M+ theorems from arXiv, Stacks Project, and specialized databases
- Natural language queries
- Similarity ranking
- Direct links to papers

### 5. Formalization

Powered by [Harmonic Aristotle](https://aristotle.harmonic.fun):
- Submit natural language mathematical statements
- Automatic translation to Lean 4 code
- Integrated with Mathlib theorem database
- Real-time compilation and verification

---

## Installation

**Requirements:** Python 3.11+ or Docker

### Option 1: Docker (Recommended)

**Fastest way to get started:**

```bash
git clone https://github.com/ml1301215/vibe-proving-math.git
cd vibe-proving-math

# Linux/macOS
chmod +x docker-start.sh
./docker-start.sh

# Windows
docker-start.bat
```

**Manual Docker setup:**

```bash
# 1. Clone repository
git clone https://github.com/ml1301215/vibe-proving-math.git
cd vibe-proving-math

# 2. Create config file
cp app/config.example.toml app/config.toml
# Edit app/config.toml and add your LLM API key

# 3. Start with Docker Compose
docker-compose up -d

# 4. Check status
docker-compose ps
docker-compose logs -f
```

**Access:** `http://localhost:8080/ui/`

**Stop service:** `docker-compose down`

### Option 2: Local Python Installation

#### Linux / macOS

```bash
git clone https://github.com/ml1301215/vibe-proving-math.git
cd vibe-proving-math/app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.example.toml config.toml
# Edit config.toml and add your API keys
python -m uvicorn api.server:app --host 127.0.0.1 --port 8080
```

#### Windows (PowerShell)

```powershell
git clone https://github.com/ml1301215/vibe-proving-math.git
cd vibe-proving-math\app
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy config.example.toml config.toml
# Edit config.toml and add your API keys
python -m uvicorn api.server:app --host 127.0.0.1 --port 8080
```

#### Windows (Command Prompt)

```cmd
git clone https://github.com/ml1301215/vibe-proving-math.git
cd vibe-proving-math\app
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
copy config.example.toml config.toml
REM Edit config.toml and add your API keys
python -m uvicorn api.server:app --host 127.0.0.1 --port 8080
```

### Configuration

**Access:** `http://127.0.0.1:8080/ui/` or `http://localhost:8080/ui/`

**First-time setup:**
1. Click the settings icon (⚙️) in the top-right corner
2. Configure LLM API:
   - Base URL (e.g., `https://api.deepseek.com/v1`)
   - API Key
   - Model name (e.g., `deepseek-chat`)
3. (Optional) Configure Nanonets OCR for PDF review
4. Click "Save"

**All settings are persisted** — your configuration will be saved and remain after page refresh.

---

## Architecture

Bilingual stack overview (Mermaid; renders on GitHub). Chinese headings mirror: [README.zh.md — 架构](README.zh.md#架构).

### Stack overview (English)

```mermaid
mindmap
    root((vibe_proving))
        Frontend
            HTML5
            CSS3
                Responsive layout
                Theme toggle
                Motion / transitions
            JavaScript ES6+
                AppState
                SSE client
                Event handling
            CDN deps
                KaTeX
                marked.js Markdown
        Backend
            Python 3.11+
            FastAPI
                Async I/O
                SSE
                OpenAPI docs
            Uvicorn
                ASGI server
            Core libs
                TOML config
                HTTP client
        External services
            LLM API
                DeepSeek v4 Pro
                Gemini 3.1 Pro
                Custom endpoints
            Theorem Search
            Nanonets OCR
            Aristotle Lean 4
        DevOps
            Deployment
                Docker optional
                Nginx reverse proxy
```

### 技术栈（中文）

```mermaid
mindmap
    root((vibe_proving))
        前端
            HTML5
            CSS3
                响应式布局
                主题切换
                动画效果
            JavaScript ES6+
                状态管理 AppState
                SSE客户端
                事件处理
            CDN依赖
                KaTeX 数学渲染
                marked.js Markdown
        后端
            Python 3.11+
            FastAPI
                异步处理
                SSE支持
                自动文档
            Uvicorn
                ASGI服务器
            核心库
                TOML配置
                HTTP客户端
        外部服务
            LLM API
                DeepSeek v4 Pro
                Gemini 3.1 Pro
                自定义端点
            Theorem Search
            Nanonets OCR
            Aristotle Lean4
        开发工具
            部署
                Docker可选
                Nginx反向代理
```

**Key Components**:

- **Frontend**: Single-page app with real-time streaming and KaTeX rendering
- **Backend**: FastAPI with SSE support for progressive responses
- **LLM Integration**: OpenAI-compatible interface (DeepSeek, Gemini, OpenAI)
- **Theorem Retrieval**: TheoremSearch API for citation verification
- **Formalization**: Harmonic Aristotle for Lean 4 code generation
- **PDF Processing**: Nanonets OCR for formula-preserving extraction

---

## Contributing

We welcome contributions from the mathematical community:

- **Bug Reports**: [GitHub Issues](https://github.com/ml1301215/vibe-proving-math/issues)
- **Code Contributions**: See [CONTRIBUTING.md](CONTRIBUTING.md)

---

## Acknowledgments

- [TheoremSearch](https://www.theoremsearch.com) — Semantic theorem retrieval
- [Harmonic Aristotle](https://aristotle.harmonic.fun) — Automated formalization
- [Research Math Assistant](https://github.com/ml1301215/research-math-assistant) — Mathematical research assistant
- [Rethlas](https://github.com/frenzymath/Rethlas) — Natural language reasoning system
- [Aletheia](https://arxiv.org/abs/2602.10177) — Generator–Verifier–Reviser architecture
- [LATRACE](https://github.com/zxxz1000/LATRACE) — Long-term memory system
- [Nanonets OCR](https://nanonets.com) — Formula-aware PDF extraction

---

## License

[MIT License](LICENSE)

---

## Contact

**QQ Group**: 1093249787  
**GitHub Issues**: [github.com/ml1301215/vibe-proving-math/issues](https://github.com/ml1301215/vibe-proving-math/issues)
