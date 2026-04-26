# 功能一：数学问题解决（Math Problem Solving）设计文档

## 目标

帮助数学研究者面对研究级数学问题时：
1. 快速找到相关已知定理（减少文献检索时间）
2. 获得结构化的证明思路（替代"跟 ChatGPT 瞎聊"）
3. 逐步骤验证证明逻辑（降低错误率）

---

## 用户输入规范

### 必填字段

```json
{
  "problem_id": "user-defined-id",
  "statement": "自然语言数学陈述（支持 LaTeX 公式）",
  "context": "可选：已知条件、变量定义、背景说明",
  "domain_hint": "可选：Ring Theory | Group Theory | Number Theory | ...",
  "mode": "explore | prove | verify"
}
```

### 三种模式

| 模式 | 描述 | 适用场景 |
|------|------|------|
| `explore` | 只做定理检索 + 背景梳理，不尝试完整证明 | 问题刚提出，不知道从哪里入手 |
| `prove` | 完整推理循环（检索 → 分解 → 证明 → 验证） | 有一定想法，希望 AI 协助完成证明 |
| `verify` | 只验证用户提供的证明草稿 | 已有证明，需要检查逻辑漏洞 |

---

## 核心推理流水线（Prove 模式）

```
用户输入
  ↓
[Phase 0] 问题理解
  - 提取关键数学对象（环、群、域、映射等）
  - 识别问题类型（存在性/唯一性/等价/反例等）
  - 用 TheoremSearch 检索直接相关结果
  - 判断：是否已知结果？→ 若是则直接返回引用
  ↓
[Phase 1] 直接证明尝试
  - 调用 direct-proving 技能
  - 用 search-math-results 补充所需引理
  - 若成功 → 输出证明草稿 → 进入验证
  ↓（失败时）
[Phase 2] 子目标分解
  - 调用 propose-subgoal-decomposition-plans
  - 并行探索 2-3 个分解方向
  - 对每个子目标：
      a. search-math-results（找相关引理）
      b. direct-proving（证明子目标）
      c. construct-toy-examples（验证理解）
      d. construct-counterexamples（排除错误方向）
  ↓（仍失败时）
[Phase 3] 失败分析
  - 调用 identify-key-failures
  - 总结：哪个障碍无法克服？需要哪些额外假设？
  - 输出：部分证明 + 关键困难点分析
  ↓
[Phase 4] 验证
  - 将最终证明草稿发送给验证 Agent
  - 验证 Agent 逐步骤检查（Rethlas verification agent）
  - 输出：verdict + repair_hints
  ↓
最终输出
```

---

## 关键组件设计

### A. 检索增强（RAG for Theorems）

**主要检索端点**：TheoremSearch API

```python
# 推荐调用方式
def search_theorems(query: str, domain_hint: str = None) -> list:
    params = {
        "query": query,
        "n_results": 10,
        "types": ["Theorem", "Lemma", "Proposition"],
    }
    if domain_hint:
        # 域提示 → arxiv 标签映射
        tag_map = {
            "Ring Theory": "math.AC",  # 交换代数
            "Group Theory": "math.GR",
            "Number Theory": "math.NT",
            "Algebraic Geometry": "math.AG",
            "Topology": "math.AT",
        }
        if domain_hint in tag_map:
            params["tags"] = [tag_map[domain_hint]]
    return call_api(params)
```

**备用检索**：Web search（通过 Codex CLI 内置工具）

**检索策略**：
1. 先用完整陈述查询（语义相似度最高）
2. 若相似度 < 0.65，改用关键词提取后查询
3. 对返回结果：验证论文中该定理的条件是否与当前问题匹配

### B. 记忆系统（JSONL 工作记忆）

延用 Rethlas 的 JSONL 记忆通道架构：

| 通道 | 内容 | 用途 |
|------|------|------|
| `immediate_conclusions` | 证明过程中推出的中间结论 | 避免重复推导 |
| `subgoals` | 分解的子目标及其状态 | 跟踪证明进度 |
| `toy_examples` | 小例子（验证猜测）| 防止朝错误方向推进 |
| `counterexamples` | 反例（排除错误策略）| 剪枝搜索空间 |
| `failed_paths` | 失败的证明路径 | 防止重复尝试 |
| `events` | 所有操作的日志 | 可追溯性 |

### C. 多模型后端支持

```toml
# config.toml
[model]
provider = "deepseek"  # deepseek | openai | openrouter | gemini
model_id = "deepseek-reasoner"  # = DeepSeek-R1
reasoning_effort = "high"  # low | medium | high

# 通过 OpenAI 兼容接口
[model.deepseek]
base_url = "https://api.deepseek.com"
env_key = "DEEPSEEK_API_KEY"

# 通过 OpenRouter（支持 100+ 模型）
[model.openrouter]
base_url = "https://openrouter.ai/api/v1"
env_key = "OPENROUTER_API_KEY"
```

---

## 输出规范

### 成功输出（verdict: correct）

```json
{
  "problem_id": "...",
  "verdict": "correct",
  "proof": {
    "overview": "一段话总结证明思路",
    "steps": [
      {
        "step_id": 1,
        "claim": "...",
        "justification": "...",
        "references": [
          {
            "title": "论文/定理名",
            "source": "arXiv:2404.01234",
            "link": "https://..."
          }
        ]
      }
    ],
    "key_ideas": ["..."],
    "open_questions": ["残留的未证明子问题（如果有）"]
  },
  "search_results_used": [...],
  "cost_estimate": {
    "model": "deepseek-r1",
    "input_tokens": 5200,
    "output_tokens": 3100,
    "estimated_usd": 0.008
  }
}
```

### 部分失败输出（verdict: partial）

```json
{
  "verdict": "partial",
  "proved_subgoals": ["..."],
  "failed_subgoals": ["..."],
  "key_obstacles": [
    "Obstacle: 需要证明 R 是 Noetherian，但当前假设不足"
  ],
  "suggested_additional_hypotheses": ["..."],
  "repair_hints": ["..."]
}
```

---

## 实现路线图

### Phase 1（MVP，2 周）
- [ ] 复用 Rethlas 的 10 个技能文件（无需修改）
- [ ] 替换检索端点：`leansearch.net` → `theoremsearch.com`
- [ ] 修改 Codex config.toml：支持 DeepSeek-R1（via OPENAI_BASE_URL）
- [ ] 单题端到端测试：FATE-H 级题目（目标：DeepSeek-R1 ≥ 60% 自然语言正确率）

### Phase 2（产品化，4 周）
- [ ] FastAPI 后端：封装整个推理流水线为 REST API
- [ ] Web UI：Markdown 渲染 + 实时流式输出
- [ ] 多模型选择：DeepSeek-R1 / Qwen3 / GPT-5.4（用户配置）

### Phase 3（增强，4 周）
- [ ] 上下文记忆：多轮对话，保留证明历史
- [ ] 探索模式（Explore Mode）：只检索，不证明
- [ ] 协作模式：用户可以插入自己的证明步骤，AI 继续
