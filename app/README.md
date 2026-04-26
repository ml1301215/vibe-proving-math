# app/ — 后端与前端实现

`vibe_proving` 的后端服务、单页前端、技能层、测试与配置示例都集中在本目录。完整的产品介绍、架构图与对外文档请见仓库根目录：

- [`README.md`](../README.md) — 一键启动、API 概览、能力一览
- [`PRODUCT_INTRO.md`](../PRODUCT_INTRO.md) — 模式细节、流程图与路线图
- [`CLAUDE.md`](../CLAUDE.md) — 开发者协作指南（含 LaTeX 输出与 SSE 约定）

## 子目录速览

```text
app/
├── api/server.py            FastAPI 路由 / SSE / 静态托管
├── core/                    config / llm / theorem_search / memory / text_sanitize
├── modes/                   learning · research · formalization
├── skills/                  search_theorems · direct_proving · verify_sequential 等
├── ui/                      原生 HTML/CSS/JS（在 /ui/ 静态托管）
├── tests/                   pytest（`-m "not slow"` 为快速回归）
├── config.example.toml      复制为 `config.toml` 后填写密钥
├── .env.example             可选 `.env` 覆盖（`VP_CONFIG_PATH` 等）
├── pytest.ini               注册 `slow` marker
└── requirements.txt
```

## 本地运行

```bash
cd app
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix:    source .venv/bin/activate
pip install -r requirements.txt
cp config.example.toml config.toml
# 编辑 config.toml：至少填写 [llm].api_key
python -m uvicorn api.server:app --host 127.0.0.1 --port 8080
```

启动后访问 `http://127.0.0.1:8080/ui/`、`http://127.0.0.1:8080/docs`、`http://127.0.0.1:8080/health`。

## 运行测试

```bash
cd app
python -m pytest tests -m "not slow"
```

调用真实 LLM / TheoremSearch / OCR 或本地 8080 服务的测试已统一标记为 `slow` 或在依赖缺失时自动 `pytest.skip`，因此干净环境下默认回归不会失败。完整集成回归请使用 `-m slow`，并提前在 `config.toml` 中配置好相关密钥。

## 配置约定

- 默认配置文件：`app/config.toml`（已被 `.gitignore` 忽略，请勿提交）。
- 通过 `VP_CONFIG_PATH` 环境变量可指向任意 TOML。
- 当配置文件缺失时，`core/config.py` 会抛出带复制示例命令的 `FileNotFoundError`。
