# vibe_proving 调研成果汇总

## 调研报告索引

| 文件 | 内容 | 状态 |
|------|------|------|
| [01_reasoning_models.md](01_reasoning_models.md) | 推理模型评测（FATE 基准数据 + 成本对比） | ✅ 完成 |
| [02_theorem_search_quality.md](02_theorem_search_quality.md) | TheoremSearch API 实测 + 高级功能测试 | ✅ 完成 |
| [03_competitor_analysis.md](03_competitor_analysis.md) | 竞品分析（Aletheia/Elicit/Wolfram 等） | ✅ 完成 |
| [04_feature_design_problem_solving.md](04_feature_design_problem_solving.md) | 功能一：数学问题解决，完整设计文档 | ✅ 完成 |
| [05_feature_design_paper_review.md](05_feature_design_paper_review.md) | 功能二：数学论文审查验证，完整设计文档 | ✅ 完成 |
| [06_rethlas_adaptation.md](06_rethlas_adaptation.md) | Rethlas 模型替换方案（GPT-5.4 → DeepSeek-R1）| ✅ 完成 |
| [07_aletheia_paper_review.md](07_aletheia_paper_review.md) | Aletheia 论文精读（arXiv:2602.10177）| ✅ 完成 |

---

## 核心结论（决策摘要）

### 1. 选哪个推理模型？

**立刻可用（开发阶段）**：DeepSeek-R1
- FATE-X 自然语言推理 33%（FATE-H 71%），远强于任何专用形式化证明器
- 成本：$0.55/1M 输入，$2.19/1M 输出
- 比 GPT-5.4 便宜 **27 倍**
- 通过 `OPENAI_BASE_URL=https://api.deepseek.com` 可无缝替换 Rethlas 的 GPT-5.4

**备用（高精度要求）**：GPT-5.4
- FrontierMath 研究级问题 38% 通过率（DeepSeek-R1 未测）
- 适合用户明确要求最高精度时的按需调用

**最低成本（批量处理）**：Qwen3-235B via OpenRouter
- $0.20/1M 输入，仍有强数学推理能力

### 2. 用哪个定理检索？

**唯一可集成的选择**：TheoremSearch API（`api.theoremsearch.com`）
- matlas.ai 无公开 API，不可集成
- 对"具体代数结构性质"类问题效果好（similarity 0.74-0.80）
- 支持按学科/年份/来源过滤，适合精准检索
- **需要将 Rethlas 的 `leansearch.net/thm/search` 替换**（适配工作约 30 分钟）

### 3. 竞争格局怎么看？

- **Aletheia（Google DeepMind）** 技术最强，但**不可用**，是 vibe_proving 的技术可行性验证而非威胁
- **Elicit/Semantic Scholar** 是文献管理工具，定位不同，无直接竞争
- **Wolfram Alpha** 是符号计算工具，不做抽象证明推理
- **空白地带**：研究级数学推理 + 开源 + 产品可用性，这是 vibe_proving 的机会窗口

### 4. Rethlas 能改造吗？

**能，修改量极小**：
1. 改 `.codex/config.toml`（2 行）：替换模型为 DeepSeek-R1
2. 改 `mcp/server.py`（约 20 行）：替换检索端点为 TheoremSearch
3. 无需修改任何技能文件（10 个技能可直接复用）

**风险点**：Codex CLI 的 OpenRouter 集成稳定性、多 Agent 任务下 DeepSeek-R1 的 agentic 能力待验证。

---

## 下一步行动（优先级排序）

### 立即可做（1-2 天）

**Action 1：Rethlas 检索端点替换 + 模型替换**
```bash
# 目标文件
Rethlas/agents/generation/mcp/server.py  # 修改 THEOREM_SEARCH_URL
Rethlas/agents/generation/.codex/config.toml  # 修改 model
Rethlas/agents/generation/.codex/agents/subgoal-prover.toml  # 修改 model
```

**Action 2：单题端到端测试**
- 选 1 道 FATE-H 题目（例：Problem 4: R[X,Y]/(X²+Y²+1) 是 PID）
- 用改造后的 Rethlas（DeepSeek-R1 + TheoremSearch）跑完整证明流水线
- 记录：成功/失败、推理时间、Token 消耗

### 本周内（3-5 天）

**Action 3：Rethlas 验证 Agent 误判率测试**
- 准备 10-15 个已知正确的 FATE-H 自然语言证明
- 启动验证 Agent 服务（`uvicorn api.server:app --port 8091`）
- 发送 POST `/verify` 请求，统计 `verdict: wrong` 的误判率
- 目标：误判率 < 20%（即 80%+ 正确证明被判为 correct）

**Action 4：TheoremSearch 论文审查场景测试**
- 取一篇真实 arXiv 代数论文（如 1705.01033）
- 手动提取几个外部引用，用 TheoremSearch 验证
- 评估：引用验证成功率是否 > 60%？

### 本月内（2-4 周）

**Action 5：论文解析 MVP**
- 用 plasTeX 解析 1 篇代数论文（标准格式）
- 抽取 theorem/lemma/proof 环境
- 对接 Rethlas 验证 Agent

**Action 6：FastAPI 包装层**
- 将两个功能封装为 REST API
- `POST /solve` → 数学问题解决
- `POST /review` → 论文审查

---

## 待解答的关键问题

1. **Rethlas 验证 Agent 误判率**：正确证明被判为 wrong 的概率是否可接受？（需实测）
2. **DeepSeek-R1 agentic 稳定性**：多轮 Agent 任务（子目标分解 → 并行证明）是否比 GPT-5.4 更容易出轨？
3. **TheoremSearch Graph API**：body 字段为何为空？是否有文档说明？（需联系 API 维护者）
4. **论文解析成本**：一篇 20 页代数论文，完整审查需要多少 Token？成本是否可接受？
