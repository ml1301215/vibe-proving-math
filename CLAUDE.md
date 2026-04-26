# vibe_proving · 开发者协作指南

面向人类与 AI 助手的项目约定。修改本文件后无需重启服务即可生效。

## 1. 项目定位

`vibe_proving` 是面向数学场景的 AI 系统：学习讲解、研究求解、论文/证明审查、定理检索与 Lean 形式化（Beta）。

- 后端：FastAPI（`app/api/server.py`）+ uvicorn，默认 `127.0.0.1:8080`
- 前端：原生 HTML/CSS/JS（`app/ui/`），由后端在 `/ui/` 静态托管
- 配置：`app/config.example.toml` 复制为 `app/config.toml`，或通过环境变量 `VP_CONFIG_PATH` 指定路径
- UI：`http://127.0.0.1:8080/ui/` · 健康检查：`/health` · OpenAPI：`/docs`

## 2. 目录约定

```
app/
  api/server.py      HTTP 端点与 SSE 协议
  core/              配置、LLM、定理检索、记忆、文本清洗等
  modes/             learning / research / formalization
  skills/            可复用技能（证明、验证、检索等）
  ui/                单页前端（index.html 中 app.js 带 ?v= 防缓存）
  tests/             pytest；`-m "not slow"` 为快速回归
```

## 3. 工作约定

### 3.1 依赖

- Python：使用虚拟环境；新增依赖前请在 PR 中说明理由并更新 `app/requirements.txt`
- 前端：CDN 引入 KaTeX / marked 等，**不引入 npm 构建链**

### 3.2 编辑规则

- 修改 `app/ui/app.js` 后，**必须**将 `app/ui/index.html` 里 `<script src="app.js?v=fNN">` 的版本号递增，避免浏览器缓存旧脚本
- 修改 `app/api/server.py` 或 `app/modes/` 后需**重启 uvicorn** 才生效
- 避免无意义的注释；仅在解释「为什么」时添加注释

### 3.3 LaTeX 输出规范（强约束）

面向用户的字符串须经过 `app/core/text_sanitize.py`（如 `strip_non_math_latex`、`sanitize_dict`）：

- 保留 `$...$` / `$$...$$` 数学块供前端 KaTeX 渲染
- 剥离 `\label`、`\cite`、`\ref`、`\textbf`、`\begin...\end` 等非展示控制序列
- 新增 API 字段同样纳入清洗，并补充测试断言

### 3.4 流式输出规范

长任务使用 SSE；后端可嵌入注释帧：`<!--vp-status:...-->`、`<!--vp-result:...-->`、`<!--vp-final:...-->`；前端用 `fetch` + `ReadableStream` 解析。

## 4. 测试

```bash
cd app
python -m pytest tests -m "not slow"
```

标记为 `slow` 的测试可能调用真实 LLM、TheoremSearch、OCR 等，需在本地配置密钥后按需运行。

## 5. 常用命令

```bash
cd app
python -m uvicorn api.server:app --host 127.0.0.1 --port 8080
```

浏览器打开 `http://127.0.0.1:8080/ui/`。

## 6. 沟通（面向 AI 助手）

- 与用户交流使用**简体中文**
- 直接执行必要操作，避免空洞铺垫
