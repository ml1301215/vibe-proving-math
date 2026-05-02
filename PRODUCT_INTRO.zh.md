# 产品概述

`vibe_proving` 是围绕五种模式设计的数学推理系统：学习、求解、审查、检索、形式化。结合语言模型与外部验证机制，降低数学场景中的幻觉风险。

## 架构

系统实现生成后独立验证的流水线：

1. **生成器** — 产生初始证明或解释
2. **验证器** — 在不访问生成器推理链的情况下评估步骤
3. **修订器** — 整合反馈以修复错误
4. **引用检查** — 查询 TheoremSearch 进行定理验证
5. **反例引擎** — 在接受声明前尝试证伪

该架构参考了 [Aletheia](https://arxiv.org/abs/2602.10177) 及降低自动推理中确认偏差的相关工作。

## 模式

### 学习模式
生成结构化数学讲解：
- 前置知识（定义、背景定理）
- 带注释的证明大纲
- 具体例子
- 扩展与相关结果

目标用户：遇到陌生材料的学生和研究者。

### 求解模式
证明生成流水线：
1. 直接检索（检查问题是否已解决）
2. 带逐步验证的证明生成
3. 通过 TheoremSearch 进行引用检查
4. 反例测试（针对猜想）
5. 置信度评分和判定（`proved`、`counterexample`、`partial`、`no_confident_solution`）

返回包含引用、障碍和失败路径的结构化输出。

### 审查模式
数学写作的结构化分析：
- 逻辑缺口检测（缺失步骤、循环论证）
- 引用准确性（定理存在性和相关性）
- 符号一致性（变量作用域、假设跟踪）

支持文本、LaTeX、图片（通过多模态模型）和 PDF（通过 OCR）。

### 检索模式
通过 [TheoremSearch](https://www.theoremsearch.com) 对来自 arXiv、Stacks Project 等来源的 900 万+ 定理进行语义搜索。

### 形式化模式（Beta）
自然语言 → Lean 4 转换：
1. 从自然语言陈述中提取关键词
2. Mathlib 检索相关定义和引理
3. 蓝图规划（证明结构）
4. 代码生成
5. 验证（本地或远程）
6. 基于编译器错误的迭代修复

目前处于实验阶段，需要进一步基准测试。

## 技术栈

- **后端**：FastAPI，支持 Server-Sent Events 流式输出
- **前端**：原生 HTML/CSS/JS（无构建工具链）
- **LLM 集成**：OpenAI 兼容接口（支持 DeepSeek、Gemini、OpenAI 等）
- **引用验证**：TheoremSearch API
- **PDF 解析**：Nanonets OCR（主要），带降级选项
- **形式化验证**：通过远程验证器使用 Lean 4 + Mathlib

## 质量控制

多层机制防止常见失败模式：
- **引用幻觉**：外部定理数据库查找
- **逻辑错误**：独立验证步骤
- **虚假声明**：反例生成
- **LaTeX 问题**：控制序列的自动清洗
- **置信度报告**：系统在不确定时拒绝回答

## 部署

通过 `config.toml` 配置（从 `config.example.toml` 复制）。最低要求：LLM API 密钥。可选服务（TheoremSearch、OCR、记忆系统）增强功能但非基本操作所必需。

```bash
cd app
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config.example.toml config.toml
# 编辑 config.toml：设置 [llm].api_key
python -m uvicorn api.server:app --host 127.0.0.1 --port 8080
```

## 测试

```bash
pytest tests -m "not slow"  # 快速回归
pytest tests                # 完整套件（需要 API 密钥）
```

测试覆盖：
- 配置解析
- LLM 客户端集成
- 所有五种模式
- 引用验证
- LaTeX 清洗
- 错误处理

## 当前状态

| 模块 | 状态 | 说明 |
|--------|--------|-------|
| 学习 | 稳定 | 带记忆集成的流式讲解 |
| 求解 | 稳定 | 带引用检查的 GVR 流水线 |
| 审查 | 稳定 | 质量取决于 OCR/解析后端 |
| 检索 | 稳定 | 直接 TheoremSearch 集成 |
| 形式化 | Beta | 需要扩展基准评估 |

## 设计约束

1. **验证优于信任**：在验证可用时，从不无检查地接受模型输出
2. **透明性**：返回置信度评分和失败路径，而非仅最终答案
3. **学术严谨**：优化正确性而非速度
4. **本地优先**：在可行的情况下最小化云依赖
5. **开放集成**：标准接口（OpenAI API、REST）而非专有格式

## 与替代方案的比较

**vs. 通用 LLM 聊天机器人**：增加引用检查、证明验证和结构化工作流

**vs. Wolfram Alpha**：处理超越符号计算的抽象证明

**vs. Lean 证明器**：提供自然语言接口和自动形式化

**vs. arXiv**：提供语义搜索和结构化证明分析

## 未来方向

- 扩展 Lean 形式化基准
- 提高 PDF 解析可靠性
- 添加协作功能（团队项目、共享知识库）
- 集成额外定理数据库
- 支持 Lean 之外的证明助手（Coq、Isabelle）

## 参考文献

- [TheoremSearch](https://www.theoremsearch.com) — 定理数据库
- [Aletheia](https://arxiv.org/abs/2602.10177) — 生成–验证–修订架构
- [LATRACE](https://github.com/zxxz1000/LATRACE) — 记忆系统
- [Rethlas](https://github.com/frenzymath/Rethlas) — 架构启发
