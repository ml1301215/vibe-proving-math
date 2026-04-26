# Rethlas 框架适配与模型替换方案

## 当前 Rethlas 依赖分析

### 硬依赖（必须解决）

| 组件 | 当前实现 | 问题 |
|------|------|------|
| 生成 Agent 运行时 | OpenAI Codex CLI（`@openai/codex`）| 封装了 OpenAI 的 agentic 运行框架 |
| 默认模型 | GPT-5.4，reasoning_effort=xhigh | 成本极高（约 $15/1M input） |
| 验证 Agent 运行时 | 同 Codex CLI | 同上 |
| 定理检索端点 | `leansearch.net/thm/search`（旧 Matlas）| 返回格式与 TheoremSearch 不同 |

### 可配置依赖（容易替换）

| 组件 | 当前实现 | 替换方案 |
|------|------|------|
| 模型 ID | `gpt-5.4` in config.toml | `CODEX_MODEL` 环境变量 or 编辑 config.toml |
| 检索 URL | `THEOREM_SEARCH_URL` 常量 | 直接修改 mcp/server.py 第 21 行 |
| 超时 | `CODEX_TIMEOUT_SECONDS` | 环境变量 |

---

## Codex CLI 的模型替换可行性

**关键发现**：Codex CLI（v0.121+）支持 OpenRouter 和自定义 base_url。

### 方案一：DeepSeek-R1（官方 API，最直接）

```bash
# 环境变量设置
export OPENAI_BASE_URL="https://api.deepseek.com"
export OPENAI_API_KEY="<deepseek_api_key>"

# config.toml 修改（不需要改 model_provider，直接用 openai 兼容接口）
# model = "deepseek-reasoner"  ← DeepSeek-R1 的 API 名称
```

DeepSeek 提供 OpenAI 兼容接口，Codex CLI 支持 `OPENAI_BASE_URL` 环境变量。

### 方案二：OpenRouter（最灵活，100+ 模型）

```toml
# .codex/config.toml
model_provider = "openrouter"
model = "deepseek/deepseek-r1"

[model_providers.openrouter]
name = "openrouter"
base_url = "https://openrouter.ai/api/v1"
env_key = "OPENROUTER_API_KEY"
```

可随时切换为：
- `qwen/qwen3-235b-a22b` (成本最低)
- `google/gemini-2.5-pro` (超长上下文)
- `openai/gpt-5.4` (最强)

### 方案三：Codex CLI 替代（长期）

若 Codex CLI 限制太多，可用以下框架替代：
- **Claude Code**（Archon 使用）：与 Anthropic Claude 集成，支持多 Agent
- **直接 API**：自行实现 Agent 循环（FastAPI + asyncio + 工具调用）

---

## 实际修改清单

### 修改 1：模型配置（5 分钟）

```toml
# Rethlas/agents/generation/.codex/config.toml
# 原：model = "gpt-5.4"
# 改为（选择其一）：

# 选项 A: DeepSeek-R1 via DeepSeek 官方
model = "deepseek-reasoner"

# 选项 B: 通过 OpenRouter
model_provider = "openrouter"
model = "deepseek/deepseek-r1"

[model_providers.openrouter]
name = "openrouter"
base_url = "https://openrouter.ai/api/v1"
env_key = "OPENROUTER_API_KEY"
```

同样修改 `agents/subgoal-prover.toml`：
```toml
# 原：model = "gpt-5.4"
model = "deepseek-reasoner"
```

修改验证 Agent：
```bash
# 环境变量
export CODEX_MODEL="deepseek-reasoner"
export OPENAI_BASE_URL="https://api.deepseek.com"
```

### 修改 2：检索端点升级（30 分钟）

文件：`Rethlas/agents/generation/mcp/server.py`

```python
# 原
THEOREM_SEARCH_URL = "https://leansearch.net/thm/search"

# 改
THEOREM_SEARCH_URL = "https://api.theoremsearch.com/search"
```

同时修改 `search_arxiv_theorems()` 函数适配新 API：

```python
def search_arxiv_theorems(query, num_results=10, domain_tag=None):
    payload = {
        "query": query,
        "n_results": num_results,
        "types": ["Theorem", "Lemma", "Proposition"],
    }
    if domain_tag:
        payload["tags"] = [domain_tag]
    
    response = requests.post(THEOREM_SEARCH_URL, json=payload, timeout=30)
    data = response.json()
    
    # 适配新格式
    normalized = []
    for item in data.get("theorems", []):
        normalized.append({
            "title": item.get("slogan", ""),
            "theorem": item.get("slogan", ""),  # 旧字段兼容
            "arxiv_id": item.get("paper", {}).get("external_id", ""),
            "theorem_id": str(item.get("theorem_id", "")),
            "similarity": item.get("similarity", 0),
            "link": item.get("link", ""),
            "source": item.get("paper", {}).get("source", ""),
        })
    return {"query": query, "count": len(normalized), "results": normalized}
```

---

## 效果衰退预测

基于 FATE 基准数据和已知信息：

| 对比 | DeepSeek-R1 | GPT-5.4 | 差距 |
|------|------|------|------|
| FATE-H 自然语言推理 | 71% | 预估 85%+ | ~20% |
| FATE-X 自然语言推理 | 33% | 预估 50%+ | ~20% |
| FrontierMath Tier-4 | 未测 | 38% | 未知 |
| 成本（同任务）| $0.02-0.1 | $1-5 | **27-50x** |

**结论**：DeepSeek-R1 在精度上有约 20% 差距，但成本降低 27-50 倍。对于 vibe_proving 的场景（辅助工具，不要求完美），这是合理的权衡。

---

## 推荐部署配置

### 开发/测试（最低成本）
```toml
model = "qwen/qwen3-235b-a22b"  # via OpenRouter, $0.20/1M input
# 用于快速迭代和功能测试
```

### 生产（平衡配置）
```toml
model = "deepseek/deepseek-r1"  # $0.55/1M input，FATE-X NL 33%
# 适合大多数研究级问题
```

### 高精度（按需）
```toml
model = "openai/gpt-5.4"  # ~$15/1M input，最强
# 用于最重要的问题或用户明确要求时
```

---

## 潜在风险

1. **Codex CLI 的 OpenRouter 集成稳定性**：目前是社区贡献功能，可能有 bug
2. **推理努力（reasoning_effort）**：Codex CLI 的 `xhigh` 设置在 DeepSeek 接口是否生效未知
3. **工具调用兼容性**：Codex CLI 的工具调用格式（MCP）在不同模型下是否一致待测试
4. **DeepSeek-R1 的 Agentic 能力**：DeepSeek-R1 在多轮 Agent 任务（vs 单次问答）的稳定性未经大规模验证

**建议**：先在单道 FATE-H 题目上测试完整流水线，再决定是否批量替换。
