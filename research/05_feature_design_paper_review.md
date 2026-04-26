# 功能二：数学论文审查验证（Math Paper Review）设计文档

## 目标

帮助数学研究者：
1. **投稿前自查**：发现证明中的逻辑跳跃、未证明的断言
2. **审稿辅助**：快速定位证明漏洞，生成具体反馈
3. **论文阅读验证**：验证引用定理是否存在、条件是否匹配

---

## 输入规范

### 支持格式

| 格式 | 解析方式 | 限制 |
|------|------|------|
| LaTeX 源文件（.tex） | plasTeX + 正则抽取 | 最完整，推荐 |
| arXiv ID | 自动下载 .tar.gz 源文件 | 需要网络访问 |
| PDF 文件 | PyMuPDF 文本提取 + LLM 结构化 | 精度较低（丢失结构）|

### 输入参数

```json
{
  "source": {
    "type": "arxiv_id | latex_file | pdf_file",
    "content": "arXiv:2404.01234 | /path/to/paper.tex | /path/to/paper.pdf"
  },
  "scope": {
    "mode": "full | section | theorem",
    "target": "可选：指定章节名或定理编号"
  },
  "focus": ["proof_logic", "citation_check", "gap_detection"]
}
```

---

## 核心审查流水线

```
输入（LaTeX/PDF/arXiv ID）
  ↓
[Phase 1] 论文解析
  ├── LaTeX: plasTeX 解析 → 抽取所有 theorem/lemma/proposition/proof 环境
  ├── PDF: PyMuPDF 提取文本 → LLM 重构结构
  └── 输出：定理列表（每条：类型、编号、陈述、证明文本、引用列表）
  ↓
[Phase 2] 证明分段
  - 将每个证明切分为独立的逻辑步骤（每步：一个论断 + 其理由）
  - 识别引用：外部引用（引用编号 → TheoremSearch）、内部引用（前文定理）
  - 标记逻辑跳跃候选：步骤间缺乏理由的论断
  ↓
[Phase 3] 逐步骤验证（Rethlas 验证技能）
  对每个证明步骤：
  ├── verify-sequential-statements：检查该步骤是否逻辑上可从前提推出
  ├── check-referenced-statements：验证引用的定理是否存在且条件匹配
  └── 记录：passed | failed | uncertain（逻辑跳跃或无法验证）
  ↓
[Phase 4] 外部引用验证（TheoremSearch）
  对每个外部引用：
  ├── 提取引用描述（"由 Theorem 3.2 in [Smith2020]，…"）
  ├── 用 TheoremSearch 查询该结果是否存在
  ├── 检查引用条件是否满足（当前论文的假设是否蕴含引用定理的前提）
  └── 报告：verified | not_found | condition_mismatch
  ↓
[Phase 5] 反例搜索（针对 uncertain 步骤）
  - 对标记为 uncertain 的步骤，尝试构造反例
  - 调用 construct-counterexamples 技能
  - 若找到反例：该步骤为错误；否则：标记为 likely_correct（人工复核）
  ↓
[Phase 6] 审查报告生成
  ├── 汇总所有问题（按严重程度排序）
  ├── 每个问题：位置 + 类型 + 具体描述 + 修复建议
  └── 整体评分：Correct | Minor Issues | Major Issues | Incorrect
```

---

## 关键组件设计

### A. LaTeX 解析器

**方案**：plasTeX + 自定义 theorem 抽取

```python
# 抽取所有定理环境
THEOREM_ENVS = [
    'theorem', 'lemma', 'proposition', 'corollary',
    'claim', 'remark', 'definition', 'example', 'proof'
]

def extract_theorems_from_latex(latex_path: str) -> list[dict]:
    """
    使用 plasTeX 解析 LaTeX 文件，提取所有定理/证明环境。
    返回结构化的定理列表。
    """
    # 工程复杂度评估：
    # - 标准 theorem 环境：容易
    # - 嵌套环境（proof inside proof）：中等
    # - 自定义 \newtheorem：需要额外处理
    # - 复杂数学公式：plasTeX 会保留 LaTeX 源码
```

**备选方案**（更稳健）：LLM 提取
```
arXiv LaTeX 源 → 按节（\section）切分 → GPT-4o-mini 提取每节的定理/证明
```
优点：处理自定义宏、非标准格式；缺点：成本较高（1 篇 20 页论文约 $0.05-0.2）

### B. 引用解析

**步骤**：
1. 正则匹配常见引用模式：`\cite{...}`、`\ref{...}`、"by Lemma X.Y in [Author]"
2. 构建引用映射：bibtex 条目 → 论文标题/作者/年份
3. 对每个外部引用：构造自然语言查询 → TheoremSearch

**TheoremSearch 查询策略**（论文审查场景）：
```python
# 示例：验证引用 "by Theorem 3.1 of [Eisenbud95], R is Cohen-Macaulay"
query = "Cohen-Macaulay ring characterization Eisenbud"
# 配合年份过滤
params = {"query": query, "year_range": [1990, 2000], "types": ["Theorem"]}
```

**图谱 API 补充**：
- `GET /graph?external_id={arxiv_id}`：获取引用论文内部的定理依赖图（当 API 完整实现后）
- `GET /paper-links`：追踪定理被引用网络

### C. 逐步骤验证（Rethlas 技能直接复用）

**verify-sequential-statements 技能**（已有，直接用）：
- 输入：陈述列表（每条带引用依据）
- 检查：每条是否可从前提 + 引用定理逻辑推出
- 输出：passed/failed/uncertain + 具体问题描述

**check-referenced-statements 技能**（已有，直接用）：
- 输入：一个声称引用某定理的步骤
- 动作：用 TheoremSearch 验证该定理是否存在 + 条件是否匹配
- 输出：verified/not_found/condition_mismatch

### D. 工程复杂度评估（关键风险）

| 场景 | 复杂度 | 说明 |
|------|------|------|
| 标准 theorem 环境 + 简单证明 | **低** | plasTeX 可直接解析 |
| 自定义 `\newtheorem` 宏 | **中** | 需要读 .sty 文件，额外处理 |
| 嵌套 proof 环境 | **中** | plasTeX 支持，但需要递归遍历 |
| 大量数学公式（无文字） | **中** | 公式作为推理步骤，LLM 需要理解 |
| 多文件项目（`\input`、`\include`）| **中-高** | 需要解析 `\input` 链 |
| 纯 PDF（无 LaTeX 源）| **高** | 结构丢失，精度大幅下降（约 60%） |

**推荐路线**：
- **MVP**：只支持 LaTeX 源文件 + arXiv ID（有源文件的论文）
- **后期**：添加 PDF 支持（使用 LLM 结构化提取）

---

## 输出规范：审查报告

```json
{
  "paper": {
    "title": "...",
    "source": "arXiv:...",
    "scope": "full"
  },
  "overall_verdict": "Minor Issues",
  "theorems_reviewed": 12,
  "issues_found": [
    {
      "issue_id": 1,
      "severity": "major | minor | uncertain",
      "type": "logic_gap | citation_error | unverified_claim | circular_reasoning",
      "location": {
        "theorem": "Lemma 3.2",
        "proof_step": 4,
        "text_excerpt": "由于 R 是 Noetherian，..."
      },
      "description": "该步骤声称 R 是 Noetherian，但这在假设中未给出，也未在之前证明。",
      "repair_hint": "需要明确添加 'R 是 Noetherian' 作为定理假设，或在此处证明该性质。",
      "confidence": 0.87
    }
  ],
  "citation_checks": [
    {
      "reference": "[Atiyah-MacDonald 1969, Proposition 5.15]",
      "claimed_statement": "局部化保持整闭性质",
      "search_result": "verified",
      "similarity_score": 0.82,
      "link": "https://..."
    }
  ],
  "cost_estimate": {
    "model": "deepseek-r1",
    "paper_pages": 20,
    "input_tokens": 45000,
    "output_tokens": 8000,
    "estimated_usd": 0.12
  }
}
```

---

## 实现路线图

### Phase 1（MVP，3 周）
- [ ] arXiv 源文件下载 + plasTeX 解析（抽取 theorem/proof 环境）
- [ ] 接入 Rethlas 验证 Agent（verify-sequential-statements）
- [ ] TheoremSearch 引用验证（check-referenced-statements + TheoremSearch API）
- [ ] 基础报告生成（Markdown 格式）
- [ ] 测试：用一篇真实 arXiv 代数论文（约 10-20 页）端到端跑通

### Phase 2（增强，4 周）
- [ ] 自定义宏处理（读取 .sty/.cls 文件）
- [ ] 反例搜索（construct-counterexamples 技能）
- [ ] 交互式界面：点击问题跳转到论文对应位置
- [ ] 批量模式：一次审查论文的多个定理

### Phase 3（PDF 支持，4 周）
- [ ] PyMuPDF 文本提取 + LLM 结构化（回退方案）
- [ ] 精度评估：LaTeX vs PDF 解析的审查质量对比
