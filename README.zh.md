![vibe_proving](assets/banner.svg)

<p align="center">
结合语言模型与形式化验证的数学推理系统
</p>

<p align="center">
<a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License"></a>
<a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python"></a>
</p>

<p align="center">
中文 | <a href="README.md">English</a>
</p>

---

## 功能

- **学习模式** — 分层讲解，包含前置知识与例子
- **求解模式** — 证明生成，引用验证，反例检测
- **审查模式** — 数学写作的结构化分析（PDF/LaTeX/图片）
- **检索模式** — 900 万+ 定理的语义检索
- **形式化** — 自然语言到 Lean 4 的转换

![界面](assets/screenshot.png)

---

## 安装

```bash
git clone https://github.com/ml1301215/vibe-proving-math.git
cd vibe-proving-math/app
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp config.example.toml config.toml
# 编辑 config.toml：设置 [llm].api_key
python -m uvicorn api.server:app --host 127.0.0.1 --port 8080
```

访问 `http://127.0.0.1:8080/ui/` 或 `http://127.0.0.1:8080/docs` 查看 API 文档。

**LLM 配置**：支持任何 OpenAI 兼容端点。

| 提供商 | Base URL | 密钥 |
|----------|----------|-----|
| DeepSeek | `https://api.deepseek.com/v1` | [platform.deepseek.com](https://platform.deepseek.com/api_keys) |
| Gemini | `https://generativelanguage.googleapis.com/v1beta/openai` | [aistudio.google.com](https://aistudio.google.com/apikey) |
| OpenAI | `https://api.openai.com/v1` | [platform.openai.com](https://platform.openai.com/api-keys) |

也可通过 Web UI 配置。

---

## 架构

```
Web UI / API 客户端
         │
    ┌────▼────────────────────────────────┐
    │         FastAPI 服务器              │
    │  /learn  /solve  /review  /search   │
    └────┬────────────────────────────────┘
         │
    ┌────▼────┬────────┬─────────┬────────┐
    │学习模式 │求解模式│ 审查    │形式化  │
    └────┬────┴────┬───┴────┬────┴────┬───┘
         │         │        │         │
    ┌────▼─────────▼────────▼─────────▼───┐
    │  LLM 核心  │  定理检索  │  OCR     │
    └────────────┴─────────────┴──────────┘
```

**质量控制**：引用验证、逐步检查、反例生成、LaTeX 清洗降低幻觉风险。

---

## API 参考

完整文档见 `/docs`。核心端点：

| 端点 | 功能 |
|----------|---------|
| `/learn` | 生成结构化讲解 |
| `/solve` | 证明生成与验证 |
| `/review_stream` | 流式证明审查 |
| `/review_pdf_stream` | PDF 上传与分析 |
| `/formalize` | 自然语言 → Lean 4 |
| `/search` | 定理检索 |

**示例**：

```bash
curl -X POST http://127.0.0.1:8080/solve \
  -H "Content-Type: application/json" \
  -d '{"statement": "证明：对所有素数 p > 2，p 是奇数"}'
```

返回带置信度评分和已验证引用的结构化证明。

---

## 测试

```bash
cd app
pytest tests -m "not slow"  # 快速回归测试
pytest tests                # 完整测试（需要 API 密钥）
```

---

## 技术细节

- **流式输出**：Server-Sent Events 实现渐进式更新
- **引用检查**：TheoremSearch 集成防止虚假引用
- **独立验证**：证明步骤的独立验证
- **形式化**：多阶段 Lean 生成与自动修复
- **LaTeX 处理**：前端渲染的自动清洗

架构细节见 [PRODUCT_INTRO.md](PRODUCT_INTRO.md)。

---

## 贡献

- 问题反馈：[GitHub Issues](https://github.com/ml1301215/vibe-proving-math/issues)
- 开发规范：参见 [CLAUDE.md](CLAUDE.md)
- 欢迎提交 Pull Request

---

## 致谢

- [TheoremSearch](https://www.theoremsearch.com) — 引用验证
- [Aletheia](https://arxiv.org/abs/2602.10177) — 生成–验证–修订架构
- [LATRACE](https://github.com/zxxz1000/LATRACE) — 记忆系统
- [Rethlas](https://github.com/frenzymath/Rethlas) — 架构启发

---

## 许可证

[MIT](LICENSE)
