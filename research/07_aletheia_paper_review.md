# Aletheia 论文精读：《Towards Autonomous Mathematics Research》

> arXiv:2602.10177 | Google DeepMind | 提交：2026 年 2 月 10 日，最终版 v3：2026 年 3 月 6 日
> 作者：Tony Feng, Trieu H. Trinh, Garrett Bingham 等（Google DeepMind）+ 多位数学家
> GitHub（全部 prompts + 输出）：https://github.com/google-deepmind/superhuman/tree/main/aletheia

---

## 一、Aletheia 的架构

### 三子 Agent 循环（Generator → Verifier → Reviser）

```
用户提问
  ↓
Generator（生成器）
  ├── 基于 Gemini Deep Think（Jan 2026 版）
  ├── 调用工具：Google Search + Web Browsing + Python
  └── 输出：候选证明草稿
  ↓
Verifier（验证器）
  ├── 独立于 Generator 运行
  ├── 解耦 intermediate thinking tokens，避免被 Generator 的推理链误导
  └── 判断：证明是否正确
  ↓（若不正确）
Reviser（修订器）
  ├── 接收 Verifier 的反馈
  └── 修正 Generator 的输出
  ↓
循环至 Verifier 批准 或 达到最大尝试次数
  ↓
最终输出（或"No solution found"）
```

**关键设计洞察（论文 §2.2）**：

> 把推理模型的最终输出与其中间思维链（intermediate thinking tokens）解耦，然后加上精心设计的 prompt scaffolding，可以让模型识别出它在生成时忽略的错误。

原因猜想：训练过程激励模型"猜测或虚张声势"；扩展的思维链可能成为支持错误结论的"误导性上下文"。

---

## 二、关键能力数据

### 测试集 1：IMO-ProofBench Advanced（30 道奥赛级题目）

| 模型 | 准确率 |
|------|------|
| Gemini Deep Think（IMO Gold 版，Jul 2025） | ~65% |
| Gemini Deep Think（Jan 2026 版，更高计算量）| ~80%+ |
| **Aletheia（同底座模型）** | **93%**（整体）/ **96%**（有输出题目的条件准确率）|
| **Aletheia（Feb 2026 Gemini 3 底座）** | **95%**（SOTA）|

Aletheia 的关键优势：以**相同或更少**的计算量超越 Deep Think。

### 测试集 2：FutureMath Basic（PhD 课程练习题）

- Aletheia 仅解答 < 60% 的题（主动拒绝回答是关键特性）
- 有输出题目的条件准确率：**82%**

### 测试集 3：FirstProof（10 道真实研究级 Lemma）

| 系统 | 解决题数（正确）|
|------|------|
| GPT-5.2 Pro（公开版）| 2（P9, P10 "开箱即用"）|
| **Aletheia（best-of-2）** | **6**（P2, P5, P7, P8, P9, P10）|
| OpenAI 内部模型（有人工引导）| 5（P2 证错，P4,5,6,9,10 正确）|
| Cursor 研究人员 | P6（自主）|

**注意**：Aletheia 和 OpenAI 在 P7 都正确（P7 是一个此前开放的数学问题）。

### 测试集 4：Erdős 问题（700 道开放问题）

| 分类 | 数量 |
|------|------|
| 生成候选答案 | 212 |
| 技术上正确（宽松解释）| 63（31.5%）|
| **有意义正确**（符合 Erdős 原意）| **13（6.5%）**|
| 真正自主解决（4 道）| Erdős-652, 654, 1040, 1051 |

**关键结论（论文 §5.2）**：成功率 6.5%，大部分失败是由于误解题意（找到技术上正确但数学上平凡的解释）。

---

## 三、工具使用的关键作用（§2.3）

**没有 Google Search 时**：模型频繁幻觉引用（伪造论文标题和作者）。

**训练 tool use 后**：引用幻觉大幅减少，但出现更隐蔽的幻觉：
- 论文存在，但引用结论不准确
- 例：Galambos 1976 年的论文存在，但其中"经典结果"实际找不到

**Python 工具**：效果有限，仅边际改进（Gemini 本身数学计算能力已较强）。

---

## 四、自主数学研究的里程碑

### Milestone A：特征权（Eigenweights）——完全自主生成的论文 [Feng2026]

**背景**：Feng-Yun-Zhang 的算术 Hirzebruch 比例原理研究中，需要计算某些"特征权"结构常数（eigenweights），作者们无法用封闭形式确定所有特征权。

**Aletheia 的贡献**：
- 完全自主，无任何人工干预
- 使用了 FYZ 作者**不熟悉的另一领域技术**（代数组合学）
- 解决了 FYZ 遗留的若干开放问题
- 人工评审后，作者**将其放入正式论文**（替换了原来的证明）

**自主程度**：Level A（完全自主），Significance Level 2（可发表）。

### Milestone B：多元独立多项式下界——人机协作 [LeeSeo2026]

**协作模式（论文 §3.2）反转了通常的范式**：
- 通常：人提大方向，AI 解决细节子问题
- 本次：**AI（Aletheia）提出大方向和核心思路**（如引入"对偶集"和对数凸性），人类数学家完成严格执行

### Milestone C：Erdős 问题——半自主评估

4 道真正自主解决的 Erdős 开放问题（Erdős-652, 654, 1040, 1051）。
其中 Erdős-1051 的解进一步被 AI+人合作推广为正式论文 [BKKKZ]。

---

## 五、AI 弱点的坦诚讨论（§5.3）

论文对 AI 的弱点非常诚实：

1. **倾向于找"最容易解释"的理解**（specification gaming）：当题意有歧义时，AI 倾向于选择更容易证明的解释，哪怕这不是数学家的本意
2. **幻觉仍是主要失败模式**：即使有 Internet search，仍会伪造或误引合法文献
3. **成功率低**：Erdős 问题上"有意义正确"率只有 6.5%
4. **结果偏短、偏初等**：当前自主结果比人类论文简短得多，缺乏真正的"创造力"
5. **主动拒绝回答**：Aletheia 对 60%+ 的 PhD 级题目和 40% 的 FirstProof 题目输出"No Output"——这被认为是**正面特性**（节省人类核验时间）

---

## 六、"自主数学等级"分类框架（§6.1，对 vibe_proving 有直接借鉴价值）

论文提出了类似 SAE 自动驾驶等级的**自主数学等级**分类：

**自主程度轴（Axis 1）**：

| 等级 | 描述 |
|------|------|
| H | 主要由人完成，AI 做辅助（文献搜索、常规证明）|
| C | 人机实质性协作，双方均有核心贡献 |
| A | AI 全自主，无实质性人工干预 |

**数学意义轴（Axis 2）**：

| 等级 | 描述 |
|------|------|
| 0 | 可忽略新颖性（奥赛级、博士练习题）|
| 1 | 轻微新颖性（新结果，但不达发表标准）|
| 2 | 可发表研究（在正规期刊可发表，覆盖范围很广）|
| 3 | 重大进展（顶级数学期刊：Annals, Inventiones 等）|
| 4 | 历史性突破（费马大定理级别）|

**当前 Aletheia 成果定位**：Feng2026 = A2，Erdős-1051 = A1，多数 Erdős 题 = A0。

---

## 七、对 vibe_proving 的启示与差异化分析

### 7.1 架构层面的直接借鉴

| Aletheia 组件 | vibe_proving 对应 |
|------|------|
| Generator（生成器）| Rethlas 生成 Agent（直接复用）|
| **Verifier（自然语言验证器）** | **Rethlas 验证 Agent（关键组件，需重点测试误判率）** |
| Reviser（修订器）| 可由生成 Agent 的 `identify-key-failures` 技能覆盖 |
| Google Search + Web | Codex CLI 内置 web search + TheoremSearch API |

**关键洞察**：Aletheia 的验证器是整个架构的核心，而 Rethlas 已经有一个完整的验证 Agent。这证明了 vibe_proving 方向的正确性。

### 7.2 vibe_proving 的差异化机会

| 维度 | Aletheia | vibe_proving |
|------|------|------|
| 可用性 | **不可用**（Google 内部工具，无公开入口）| **目标：开源可用** |
| 底座模型 | Gemini Deep Think（专有，极贵）| DeepSeek-R1 / Qwen3（开源，便宜 27-50x）|
| 目标场景 | 自主发现新定理（研究最前沿）| 辅助日常研究（文献验证、论文审查）|
| 工具集成 | Google Search | TheoremSearch API（定理级检索，更精准）|
| 数学领域 | 广泛（所有领域）| 初期聚焦代数/数论（TheoremSearch 覆盖好）|
| 主动拒绝功能 | 有（关键特性）| **应该明确实现**（避免产生低置信度的错误答案）|

### 7.3 必须从 Aletheia 论文学到的重要教训

1. **验证器解耦至关重要**：不要让 Generator 的 thinking tokens 影响 Verifier，必须分开独立运行
2. **主动拒绝回答**是正面特性，不是缺点：应该明确告诉用户"这道题超出了当前能力范围"
3. **工具使用必须专门训练**：只给模型 Internet access 是不够的，需要精心设计 tool-use 提示
4. **引用幻觉是主要风险**：TheoremSearch 的作用不仅是找定理，更是**防止模型幻觉引用**——需要强制要求模型用 TheoremSearch 验证所有引用
5. **成功率低是常态**：不要追求"总是能解决"，而是追求"解决时一定是对的"（高 precision，低 recall）

### 7.4 新增功能建议（基于 Aletheia 论文）

**建议增加"引用幻觉检查"子功能**（属于论文审查功能的一部分）：
- 提取证明中所有"由 [某文] 的某定理"式的引用
- 强制用 TheoremSearch 验证每一个引用
- 对无法找到的引用：标记为"潜在幻觉"，提示用户手动核实

这直接对应 Aletheia 论文中描述的核心问题（即使是 Gemini Deep Think 这样的顶级模型，也会在引用上产生幻觉）。

---

## 八、Cursor 团队的贡献（意外发现）

论文 §4.2 提到：
> "Cursor researchers (Zhang and Lin) exhibited an autonomously generated solution to Problem 6; our understanding is that experts regard it to be correct."

FirstProof 的 10 道研究级数学问题，Cursor 的研究员用自主系统解决了 Problem 6——这说明即使不依赖 Gemini Deep Think，工程化的 AI Agent 也有机会在研究级数学问题上取得突破。

---

## 九、总结

Aletheia 论文是目前 AI 辅助数学研究领域最重要的参考文献：
- 验证了"自然语言 + 三 Agent 循环（生成-验证-修订）"架构的有效性
- 证明了在研究级数学上 AI 已经可以产出可发表的结果（Level A2）
- 坦诚披露了 AI 的核心弱点（幻觉、specification gaming、成功率低）
- 提供了"自主数学等级"框架，有助于 vibe_proving 定义自身产品能力边界

vibe_proving 的定位：不是做第二个 Aletheia（没有 Gemini Deep Think），而是做**"面向普通数学研究者的 Aletheia 开源平替"**——以 DeepSeek-R1 为底座，TheoremSearch 为检索，Rethlas 为推理框架，以更低成本、更好的可及性，覆盖大多数日常研究辅助场景（而非顶级研究突破）。
