# 推理模型评测报告

## 数据来源

- FATE 论文（arXiv:2511.02872）：官方评测数据，自然语言推理 Pass@1 + 形式化证明 Pass@64
- FrontierMath Tier-4 排行（epoch.ai）：研究级开放问题成功率
- 公开 API 定价信息（2026 年 4 月）

---

## 核心发现

### 1. 自然语言推理 vs 形式化证明的巨大鸿沟

FATE 论文的两阶段评测揭示了关键事实：**模型在自然语言层面的数学推理能力远高于形式化能力**。

| 模型 | FATE-H 自然语言(Pass@1) | FATE-X 自然语言(Pass@1) | FATE-H 形式化(Pass@64) | FATE-X 形式化(Pass@64) |
|------|------|------|------|------|
| DeepSeek-R1 | **71.0%** | **33.0%** | 0.0% | 0.0% |
| DeepSeek-Prover-V2 | 39.0% | 9.0% | 3.0% | 0.0% |
| o3 | 未测 | 未测 | 3.0% | 0.0% |
| Claude-Sonnet-4 | 未测 | 未测 | 0.0% | 0.0% |
| Gemini-2.5-Pro | 未测 | 未测 | 0.0% | 0.0% |

**结论**：形式化是当前最大瓶颈，不是数学推理本身。vibe_proving 在自然语言层面的价值空间更大。

### 2. 研究级开放问题（FrontierMath Tier-4）

| 模型 | 成功率(Pass@1) |
|------|------|
| GPT-5.4 Pro (web) | 38% |
| o3 | 25% |
| GPT-5 | 15% |
| o3-mini | 4% |

GPT-5.4 已能解决部分真正的开放问题（首个：Ramsey 超图剖分问题，难度估计 1-3 个月人工工作量）。

### 3. FATE-X 自然语言推理成功率分析

- **DeepSeek-R1 FATE-X: 33%**，显著高于专用定理证明器（Prover-V2: 9%）
- **关键洞察**：通用推理模型（DeepSeek-R1）的数学推理能力强于专用证明器，因为专用器的 RL 训练使其不善于反思和修正
- **Qwen3 系列**：AIME 2025 成绩优秀（1.7B 模型 65.6%），更大参数版本（235B）预期更强，且成本极低
- **GPT-5.4 vs DeepSeek-R1**：GPT-5.4 预计在 FATE-X NL 达到 50%+（FrontierMath 38% → FATE-X 对应关系未直接测试）

---

## 模型成本对比

| 模型 | 输入($/1M tokens) | 输出($/1M tokens) | 适用场景 |
|------|------|------|------|
| DeepSeek-R1 | $0.55 | $2.19（缓存$0.14） | 高性价比，开源，推荐主力 |
| Qwen3-235B-A22B | $0.20 | $0.60（OpenRouter）| 开源最便宜，能力待验证 |
| Gemini 2.5 Pro | $1.25 | $5.00 | 中等成本，Google 生态 |
| o3 | $10.00 | $40.00 | 高质量，成本高 |
| GPT-5.4 | ~$15 | ~$60（估算）| 最强，极贵 |

**成本比率**：DeepSeek-R1 vs GPT-5.4 ≈ **27倍成本差**

---

## 对 vibe_proving 的推荐

### 主力模型（自然语言推理）
**DeepSeek-R1** 作为默认后端：
- FATE-X NL 33%（FATE-H 71%），显著强于专用证明器
- 成本极低，有 OpenAI 兼容 API
- 可通过 OpenRouter 或官方 API 调用

### 备选模型（分场景）
- **Qwen3-235B**：成本最低，适合高频、低要求场景（初步筛选）
- **Gemini 2.5 Pro**：百万上下文窗口，适合长论文审查
- **GPT-5.4**：精度要求最高时的可选后端（按需付费）

### 关键设计原则
系统应支持**多模型后端切换**：通过配置文件选择模型，允许用户根据成本/质量需求自行决定。

---

## Rethlas 模型替换可行性预评估

Rethlas 的生成 Agent 使用 OpenAI Codex CLI，其 `.codex/config.toml` 写死 `model = "gpt-5.4"`。

**好消息**：Codex CLI 支持通过以下方式替换模型：
```toml
# .codex/config.toml 修改方案
model_provider = "openrouter"
model = "deepseek/deepseek-r1"

[model_providers.openrouter]
name = "openrouter"
base_url = "https://openrouter.ai/api/v1"
env_key = "OPENROUTER_API_KEY"
```

或通过 DeepSeek 的 OpenAI 兼容接口：
```bash
export OPENAI_BASE_URL="https://api.deepseek.com"
export OPENAI_API_KEY="<deepseek_api_key>"
# model = "deepseek-reasoner"  (= DeepSeek-R1)
```

**预计效果衰退**：DeepSeek-R1 FATE-X NL 33% vs GPT-5.4（预估50%+），约 20-30% 差距。但成本降低 27 倍，对于非最高精度场景完全可接受。
