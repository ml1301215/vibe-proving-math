<div align="center">

![vibe proving](assets/banner.jpg)

# 𝒱𝒾𝒷ℯ 𝒫𝓇ℴ𝓋𝒾𝓃ℊ

<p>
面向学生和研究者的 AI 驱动数学研究助手
</p>

<p>
<a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License"></a>
<a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python"></a>
</p>

<p>
中文 | <a href="README.md">English</a>
</p>

</div>

---

## 概述

**vibe proving** 是面向数学领域学生和研究者的 AI 平台。结合语言模型与定理检索，提供学习、求解、审查、检索等交互式工作流。

### 核心能力

<div align="center">
<img src="assets/screenshot.png" alt="界面" style="border-radius: 12px; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12); border: 1px solid rgba(255, 255, 255, 0.18);" width="90%">
</div>

<br>

- **学习模式** — 生成包含前置知识、证明、例子和扩展的结构化讲解
- **求解模式** — 自动证明生成，包含引用验证和置信度评分
- **审查模式** — 对数学写作（LaTeX/PDF/图片）进行结构化分析
- **检索模式** — 在 900 万+ 定理中进行语义搜索

### 视频演示

<table>
<tr>
<td width="50%" align="center">

**学习模式**  
[![▶️ 学习模式](assets/screenshot.png)](https://github.com/user-attachments/assets/ff33ef0e-b330-4d79-bb06-3a0c4cd9f920)  
*点击播放视频*

</td>
<td width="50%" align="center">

**问题求解**  
[![▶️ 问题求解](assets/screenshot.png)](https://github.com/user-attachments/assets/ce5e17b3-e9e9-45ce-a038-c2b6b672d440)  
*点击播放视频*

</td>
</tr>
<tr>
<td width="50%" align="center">

**证明审查**  
[![▶️ 证明审查](assets/screenshot.png)](https://github.com/user-attachments/assets/eec047a3-c791-4938-a4fc-5e322ccfb2da)  
*点击播放视频*

</td>
<td width="50%" align="center">

**文献检索**  
[![▶️ 文献检索](assets/screenshot.png)](https://github.com/user-attachments/assets/588b3f73-7b4f-4040-acd2-d7243c10b3dc)  
*点击播放视频*

</td>
</tr>
<tr>
<td width="50%" align="center">

**自动形式化**  
[![▶️ 自动形式化](assets/screenshot.png)](https://github.com/user-attachments/assets/3dd05428-e023-4903-bb6b-0cc2e7dad42c)  
*点击播放视频*

</td>
<td width="50%">

</td>
</tr>
</table>

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

基于 [Harmonic Aristotle](https://aristotle.harmonic.fun)：
- 提交自然语言数学陈述
- 自动转换为 Lean 4 代码
- 集成 Mathlib 定理数据库
- 实时编译和验证

---

## 安装

**要求：** Python 3.11 或更高版本

### Docker（推荐）

```bash
git clone https://github.com/ml1301215/vibe-proving-math.git
cd vibe-proving-math

# Linux/macOS
chmod +x docker-start.sh
./docker-start.sh

# Windows
docker-start.bat
```

手动 Docker 启动：

```bash
git clone https://github.com/ml1301215/vibe-proving-math.git
cd vibe-proving-math

cp app/config.example.toml app/config.toml
# 编辑 app/config.toml：
#   - 设置 [auth].superuser_password
#   - 填写 [llm] 的 API endpoint/key/model

docker compose up -d
docker compose ps
docker compose logs -f
```

停止服务：

```bash
docker compose down
```

### 本地 Python 安装

#### Linux / macOS

```bash
git clone https://github.com/ml1301215/vibe-proving-math.git
cd vibe-proving-math
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp app/config.example.toml app/config.toml
# 编辑 app/config.toml，设置超级账户密码和 API 密钥
cd app
python -m uvicorn api.server:app --host 127.0.0.1 --port 8080
```

#### Windows (PowerShell)

```powershell
git clone https://github.com/ml1301215/vibe-proving-math.git
cd vibe-proving-math
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy app\config.example.toml app\config.toml
# 编辑 app\config.toml，设置超级账户密码和 API 密钥
cd app
python -m uvicorn api.server:app --host 127.0.0.1 --port 8080
```

#### Windows (命令提示符)

```cmd
git clone https://github.com/ml1301215/vibe-proving-math.git
cd vibe-proving-math
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
copy app\config.example.toml app\config.toml
REM 编辑 app\config.toml，设置超级账户密码和 API 密钥
cd app
python -m uvicorn api.server:app --host 127.0.0.1 --port 8080
```

**在浏览器中打开 `http://127.0.0.1:8080/ui/`。**

配置从 `app/config.toml` 读取。首次部署至少需要设置：

```toml
[auth]
superuser_username = "dev_user"
superuser_password = "change-this-password"
session_days = 30
default_quota = 50
allow_register = true

[llm]
base_url = "https://api.deepseek.com/v1"
api_key = "your-api-key"
model = "deepseek-chat"
```

用户系统说明：
- 超级账户可在右侧设置面板修改 API 配置。
- 普通注册用户可以使用服务，但看不到也不能修改 API Key/Base URL。
- 登录状态保存在 HTTP-only cookie 中，有效期由 `[auth].session_days` 控制。

可选服务：
- `[nanonets]` 用于 PDF 审查 OCR。
- `[mineru]` 使用 MinerU Agent Lightweight Extract API，无需 token。
- `[aristotle]` 用于 Harmonic Aristotle 形式化。

---

## 架构

```mermaid
mindmap
    root((vibe proving))
        前端
            HTML5
            CSS3
                响应式布局
                主题切换
                动画效果
            JavaScript ES6+
                状态管理 AppState
                SSE客户端
                事件处理
            CDN依赖
                KaTeX 数学渲染
                marked.js Markdown
        后端
            Python 3.11+
            FastAPI
                异步处理
                SSE支持
                自动文档
            Uvicorn
                ASGI服务器
            核心库
                TOML配置
                HTTP客户端
        外部服务
            LLM API
                DeepSeek v4 Pro
                Gemini 3.1 Pro
                自定义端点
            Theorem Search
            Nanonets OCR
            Aristotle Lean4
        开发工具
            部署
                Docker可选
                Nginx反向代理
```

**关键组件**：

- **前端**：单页应用，实时流式输出和 KaTeX 渲染
- **后端**：FastAPI，支持 SSE 渐进式响应
- **LLM 集成**：OpenAI 兼容接口（DeepSeek、Gemini、OpenAI）
- **定理检索**：TheoremSearch API 用于引用验证
- **形式化**：Harmonic Aristotle 生成 Lean 4 代码
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

## 贡献

欢迎数学社区的贡献：

- **错误报告**：[GitHub Issues](https://github.com/ml1301215/vibe-proving-math/issues)
- **代码贡献**：请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 致谢

- [TheoremSearch](https://www.theoremsearch.com) — 语义定理检索
- [Harmonic Aristotle](https://aristotle.harmonic.fun) — 自动形式化
- [Research Math Assistant](https://github.com/ml1301215/research-math-assistant) — 数学科研助手
- [Rethlas](https://github.com/frenzymath/Rethlas) — 自然语言推理系统
- [Aletheia](https://arxiv.org/abs/2602.10177) — 生成–验证–修订架构
- [LATRACE](https://github.com/zxxz1000/LATRACE) — 长期记忆系统
- [Nanonets OCR](https://nanonets.com) — 公式感知的 PDF 提取

---

## 许可证

[MIT License](LICENSE)

---

## 联系方式

**QQ 交流群**：1093249787  
**GitHub Issues**：[github.com/ml1301215/vibe-proving-math/issues](https://github.com/ml1301215/vibe-proving-math/issues)
