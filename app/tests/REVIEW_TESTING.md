# 证明审查功能测试说明

## 功能描述

证明审查功能用于：
- **上传数学论文 PDF**（或粘贴证明文本）
- **逐步审查逻辑漏洞**（gap、critical_error）
- **核查引用的定理**（通过 TheoremSearch）
- **检测符号一致性**（与证明完备性）

## 测试覆盖

### 1. 文本粘贴审查 (`/review_stream`)

**支持格式**：
- 纯文本证明
- LaTeX 片段（含 `\begin{theorem}` 等环境）
- Markdown 格式

**测试用例**：
- `test_review_text_basic`: 基础文本审查
- `test_review_text_with_options`: 使用审查选项（logic/citations/symbols）
- `test_review_text_latex_theorem_env`: LaTeX 定理环境解析
- `test_review_detects_logical_gaps`: 检测逻辑漏洞
- `test_review_citation_checking`: 引用核查功能

### 2. PDF 上传审查 (`/review_pdf_stream`)

**PDF 主路径（2025 重构）**：Nanonets 异步 OCR → Markdown → 按 `#` / `##` 大章节切分 →
`chat_json`（默认模型 `gemini-3.1-pro`，可由表单 `model` 覆盖）逐章结构化输出。
需提供 `NANONETS_API_KEY`（或表单 `nanonets_api_key` / `config.toml` `[nanonets].api_key`）。
解析失败时 SSE 最终帧含 `parse_failed: true`，**不会**降级到 MinerU / PyMuPDF / agent。

**支持格式**：
- `.pdf` - PDF 论文
- `.tex` - LaTeX 源文件
- `.txt` - 纯文本
- `.md` / `.mmd` - Markdown 文档

**测试用例**：
- `test_review_pdf_txt_file`: 上传 TXT 文件
- `test_review_pdf_latex_file`: 上传 LaTeX 文件
- `test_review_pdf_unsupported_format`: 不支持的文件格式

### 3. 审查选项

**可选参数**（`ReviewRequest`）：
- `check_logic: bool` - 是否审查逻辑漏洞（默认 true）
- `check_citations: bool` - 是否核查定理引用（默认 true）
- `check_symbols: bool` - 是否检查符号一致性（默认 true）

### 4. 边界条件

**测试用例**：
- `test_review_empty_text`: 空文本 → 422
- `test_review_text_too_long`: 超长文本 (>50000) → 422
- `test_review_pdf_unsupported_format`: 不支持格式 → 415

### 5. 输出格式验证

**必需字段**：
```json
{
  "overall_verdict": "Correct" | "Partial" | "Incorrect",
  "stats": {
    "theorems_checked": int,
    "citations_checked": int,
    "issues_found": int
  },
  "issues": [
    {
      "location": str,
      "issue_type": "gap" | "critical_error" | "citation_not_found",
      "description": str,
      "fix_suggestion": str,
      "confidence": float
    }
  ]
}
```

## 运行测试

```bash
# 快速测试（不依赖服务器）
python -m pytest app/tests/test_review_comprehensive.py::test_review_empty_text -v

# 完整测试（需要启动服务器）
python -m pytest app/tests/test_review_comprehensive.py -v -m slow

# 所有审查相关测试
python -m pytest app/tests -k review -v
```

## SSE 流式输出

审查接口使用 Server-Sent Events (SSE) 流式下发结果：

1. **status 帧**：阶段进度
   - `parse`: 解析输入文本
   - `review`: 开始审查
   - `theorem`: 审查单个定理
   - `done`: 完成

2. **result 帧**：单个定理审查结果（增量）
   ```json
   {"result": {"kind": "theorem", "index": 1, "data": {...}}}
   ```

3. **final 帧**：最终汇总
   ```json
   {"final": {"overall_verdict": "...", "stats": {...}, "issues": [...]}}
   ```

4. **done 哨兵**：`[DONE]`

## 已知限制

- 单次请求最大 50000 字符（PDF 自动分块）
- 最多审查前 5 个定理（可调整 `max_theorems`）
- TheoremSearch 引用核查需要外部服务（可降级）
- 大文件 PDF 可能超时（分块处理缓解）
