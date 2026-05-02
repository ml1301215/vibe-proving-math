![vibe_proving](assets/banner.svg)

<p align="center">
面向学生和研究者的 AI 驱动数学研究助手
</p>

<p align="center">
<a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License"></a>
<a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python"></a>
</p>

<p align="center">
中文 | <a href="README.md">English</a>
</p>

---

## 概述

**vibe_proving** 是面向数学领域学生和研究者的 AI 平台。结合语言模型与定理检索，提供学习、求解、审查、检索等交互式工作流。

### 核心能力

- **学习模式** — 生成包含前置知识、证明、例子和扩展的结构化讲解
- **求解模式** — 自动证明生成，包含引用验证和置信度评分
- **审查模式** — 对数学写作（LaTeX/PDF/图片）进行结构化分析
- **检索模式** — 在 900 万+ 定理中进行语义搜索

### 视频演示

<table>
<tr>
<td width="50%">

**学习模式**  
![学习模式演示](https://github.com/user-attachments/assets/588b3f73-7b4f-4040-acd2-d7243c10b3dc)

</td>
<td width="50%">

**问题求解**  
![问题求解演示](https://github.com/user-attachments/assets/ff33ef0e-b330-4d79-bb06-3a0c4cd9f920)

</td>
</tr>
<tr>
<td width="50%">

**证明审查**  
![证明审查演示](https://github.com/user-attachments/assets/186e9541-b64f-419f-9682-94298e61d189)

</td>
<td width="50%">

**文献检索**  
![文献检索演示](https://github.com/user-attachments/assets/ce5e17b3-e9e9-45ce-a038-c2b6b672d440)

</td>
</tr>
</table>

![界面](assets/screenshot.png)

---

## 主要特性

### 1. 交互式学习

将数学陈述转化为全面的学习资源：
- 背景与动机
- 前置知识与定义
- 逐步证明演示
- 具体例子与反例
- 扩展与相关主题

目标难度级别：本科或研究生。

### 2. 智能求解

生成–验证–修订流水线：
- 定理数据库直接检索
- 带推理步骤的证明生成
- 独立验证
- 通过 [TheoremSearch](https://www.theoremsearch.com) 进行引用检查
- 反例测试
- 置信度评分，明确不确定性

### 3. 证明审查

自动化分析：
- **逻辑一致性**：检测缺失步骤、循环论证
- **引用准确性**：验证引用定理
- **符号一致性**：跟踪变量作用域

支持格式：文本、LaTeX、图片（通过视觉模型）、PDF（通过 OCR）。

### 4. 定理发现

语义搜索：
- 来自 arXiv、Stacks Project 等专业数据库的 900 万+ 定理
- 自然语言查询
- 相似度排序
- 论文直链

### 5. 形式化

自然语言到 Lean 4 的转换：
- 关键词提取和 Mathlib 检索
- 蓝图规划
- 带自动修复的代码生成

---

## 安装

```bash
git clone https://github.com/ml1301215/vibe-proving-math.git
cd vibe-proving-math/app
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn api.server:app --host 127.0.0.1 --port 8080
```

**在浏览器中打开 `http://127.0.0.1:8080/ui/`。**

点击右上角的**设置图标（⚙️）**进行配置：
- LLM API（Base URL、API Key、Model）
- Nanonets OCR（用于 PDF 审查）

无需编辑配置文件 — 所有设置可通过 Web 界面管理。

---

## 架构

```
┌────────────────────────────────────────────────┐
│              Web 界面                          │
│      (原生 JS + KaTeX + SSE 流式)              │
└───────────────────┬────────────────────────────┘
                    │
       ┌────────────▼────────────┐
       │   FastAPI 服务器        │
       │   (Python 3.10+)        │
       └────────────┬────────────┘
                    │
    ┌───────────────┼───────────────┐
    │               │               │
┌───▼────┐   ┌─────▼──────┐   ┌───▼────┐
│学习流水│   │  求解流水  │   │审查流水│
│  线    │   │    线      │   │  线    │
└───┬────┘   └─────┬──────┘   └───┬────┘
    │              │              │
    └──────────────┼──────────────┘
                   │
    ┌──────────────┼──────────────┐
    │              │              │
┌───▼──────┐  ┌───▼────────┐  ┌─▼────────┐
│ LLM 核心 │  │  定理检索  │  │ Nanonets │
│ (OpenAI  │  │ (引用验证) │  │   OCR    │
│   API)   │  │            │  │  (PDF)   │
└──────────┘  └────────────┘  └──────────┘
```

**关键组件**：

- **前端**：单页应用，Markdown + KaTeX 渲染
- **后端**：FastAPI，支持 Server-Sent Events 渐进式流式输出
- **LLM 集成**：OpenAI 兼容接口（DeepSeek、Gemini、OpenAI 等）
- **引用验证**：TheoremSearch API 集成
- **PDF 处理**：Nanonets OCR 保留公式的提取

---

## API 参考

完整文档见 `/docs`。核心端点：

| 端点 | 方法 | 用途 |
|----------|--------|---------|
| `/learn` | POST | 生成结构化讲解 |
| `/learn/section` | POST | 重新生成特定章节 |
| `/solve` | POST | 带验证的证明生成 |
| `/solve_latex` | POST | 从证明蓝图生成 LaTeX |
| `/review` | POST | 文本/图片证明审查 |
| `/review_stream` | POST | 流式证明审查 |
| `/review_pdf_stream` | POST | PDF 上传与分析 |
| `/formalize` | POST | 自然语言 → Lean 4 |
| `/search` | GET | 定理语义搜索 |
| `/config/llm` | POST | 运行时 LLM 配置 |
| `/config/nanonets` | POST | 运行时 OCR 配置 |

**示例**（求解模式）：

```bash
curl -X POST http://127.0.0.1:8080/solve \
  -H "Content-Type: application/json" \
  -d '{
    "statement": "证明：对所有素数 p > 2，p 是奇数"
  }'
```

---

## 使用场景

### 学生

- **概念探索**：输入陌生定理获取前置知识分解
- **证明理解**：逐步演示包含推理注释
- **考试准备**：生成练习题和详细解答

### 研究者

- **文献综述**：定理数据库的语义搜索
- **证明起草**：生成包含引用建议的初始草稿
- **稿件审查**：提交前的自动一致性检查

---

## 贡献

欢迎数学社区的贡献：

- **错误报告**：[GitHub Issues](https://github.com/ml1301215/vibe-proving-math/issues)
- **功能请求**：描述使用场景和预期行为
- **代码贡献**：遵循 [CLAUDE.md](CLAUDE.md) 中的规范
- **文档**：改进示例、修正错误、翻译内容

---

## 致谢

- [TheoremSearch](https://www.theoremsearch.com) — 语义定理数据库
- [Aletheia](https://arxiv.org/abs/2602.10177) — 生成–验证–修订架构
- [Rethlas](https://github.com/frenzymath/Rethlas) — 基于生成和验证代理的自然语言推理系统
- [LATRACE](https://github.com/zxxz1000/LATRACE) — 长期记忆系统
- [Nanonets OCR](https://nanonets.com) — 公式感知的 PDF 提取
- [Harmonic Aristotle](https://aristotle.harmonic.fun) — Lean 4 形式化引擎
- [Research Math Assistant](https://github.com/ml1301215/research-math-assistant) — 社区资源

---

## 许可证

[MIT License](LICENSE)

---

## 联系方式

**QQ 交流群**：1093249787  
**GitHub Issues**：[github.com/ml1301215/vibe-proving-math/issues](https://github.com/ml1301215/vibe-proving-math/issues)
