# TheoremSearch API vs matlas.ai 检索质量报告

## 测试方法

- 查询集：8 道 FATE-X/H 级研究级代数问题（自然语言问题陈述）
- TheoremSearch：使用官方 REST API（`https://api.theoremsearch.com/search`）
- matlas.ai：**无公开 API**，只有 Web UI，无法集成到 Agent 流程

---

## TheoremSearch API 基础功能测试结果

### FATE-X 题目检索结果（Top-1 相似度 + 命中质量）

| 查询 | Top-1 相似度 | 命中质量 | 评价 |
|------|------|------|------|
| UFD 两个素元 → PID | 0.704 | 部分（找到 PID/UFD 等价条件，不完全匹配） | 一般 |
| 有限群 L maximal simple → ≤2 个 minimal normal 子群 | 0.701 | 弱（群论相关结果） | 弱 |
| 有限群阶 p(p+1) 无正规 Sylow → p+1 是 2 的幂 | 0.701 | 弱（Sylow 定理相关） | 弱 |
| R[X,Y]/(X²+Y²+1) 是 PID | 0.740 | **强**（商环 PID 定理，几乎直接命中） | 好 |
| Z[(1+√-19)/2] 是 PID | 0.660 | 差（返回一般整数环结果） | 差 |
| B\A 对乘法封闭 → A 整闭 | 0.769 | 中等（整闭相关命题） | 一般 |
| C[x₁,...,xₙ]/(∑xᵢ²) 是 UFD（n≥5） | **0.797** | **优秀**（几乎直接找到该定理） | 优秀 |
| F₄(t) 在 F₄(t⁴+t) 上 Galois | 0.683 | 弱（未直接命中） | 弱 |

### 高级过滤功能测试

**按学科过滤（math.AC 交换代数 + Theorem 类型）**：
- 查询 "integrally closed domain polynomial ring"
- 命中 math.AC 文章中的整闭相关定理，分数 0.746/0.737
- 过滤功能有效，提升了精准度

**按年份过滤（2010-2025）**：
- UFD/PID 相关结果，Top 分数 0.771（2024 年论文）
- 年份过滤有助于找到最新结果

**按来源过滤（Stacks Project）**：
- 可准确召回 Stacks Project 中的同调代数结果
- 延迟：10 秒（较慢，但结果高质量）

---

## Graph API 测试

**接口**：`GET /graph?external_id={arxiv_id}`

**测试结果**（论文 1705.01033 "Completely integrally closed Prufer v-multiplication domains"）：
- 成功返回：46 个 statements，33 个 dependencies
- **问题**：statements 的 body 字段为空（只有 `statement_id`, `kind`, `ref`），与文档描述不符
- dependencies 字段存在但没有跨论文引用（`interpaper` 为空）
- **结论**：Graph API 功能设计上很有价值（论文内部依赖图），但当前实现**不完整**，body 字段缺失导致无法直接用于论文审查

---

## 关键对比：TheoremSearch vs matlas.ai vs leansearch.net

| 指标 | TheoremSearch (theoremsearch.com) | matlas.ai | leansearch.net (Rethlas 使用) |
|------|------|------|------|
| 公开 API | **有**，REST API | **无**，只有 Web UI | 有（Rethlas 已集成） |
| 检索覆盖 | arXiv + Stacks Project + 更多 | 未知（无 API 测试） | arXiv 数学论文 |
| 返回格式 | similarity, slogan, theorem_type, paper | - | title, theorem, arxiv_id |
| 过滤参数 | 标签/年份/来源/类型 | Web 界面手动 | 无 |
| 响应延迟 | ~5s/条（基础），~10s（Stacks） | 未测（无 API） | 未测 |
| 图谱 API | 有（但实现不完整） | 未知 | 无 |
| 集成难度 | **低**（HTTP POST JSON） | 不可集成 | 已集成（Rethlas） |

---

## Rethlas 检索升级方案

Rethlas 当前使用 `leansearch.net/thm/search`（旧版 Matlas），响应格式：
```json
[{"title": "...", "theorem": "...", "arxiv_id": "...", "theorem_id": "..."}]
```

TheoremSearch 响应格式：
```json
{"theorems": [{"similarity": 0.79, "slogan": "...", "theorem_type": "Theorem", "paper": {...}, "link": "..."}]}
```

**升级步骤**：
1. 在 `mcp/server.py` 中将 `THEOREM_SEARCH_URL` 改为 `https://api.theoremsearch.com/search`
2. 修改 `search_arxiv_theorems()` 的请求参数（`task` 字段不需要，改为标准参数）
3. 修改返回格式适配新字段（`slogan` → `theorem`，`link` → URL）
4. 可选：添加 `tags`/`year_range`/`sources` 参数传入，提升召回精度

---

## 结论

**TheoremSearch 推荐作为主要检索基础设施**：
- 唯一有公开 API 的高质量数学定理检索服务
- 过滤功能丰富，适合论文审查中的精准检索
- 对"某具体结构的某性质"类问题（如环的代数性质）效果好
- 对极特殊的数值定理和竞赛式群论题效果较弱

**matlas.ai**：检索质量主观上优秀（Web UI 体验好），但无 API，短期内不可集成。可关注是否开放 API。
