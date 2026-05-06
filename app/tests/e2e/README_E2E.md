# Robust E2E Testing with Playwright

## 框架选择

**选择**: `pytest-playwright` (Python)
- 与您的FastAPI后端技术栈完美对齐
- 强大的fixture系统用于共享配置
- 优秀的异步支持,适合SSE测试

## 安装

```bash
# 1. 安装pytest-playwright
pip install pytest-playwright

# 2. 安装浏览器驱动
python -m playwright install chromium

# 3. 可选：安装所有浏览器
python -m playwright install
```

## 测试文件结构

```
app/tests/e2e/
├── conftest.py              # 共享fixtures和配置
│   ├── app_page            # 自动导航到应用并验证加载
│   └── mock_api_responses  # 模拟API响应,避免真实调用
├── test_e2e_robust.py       # 主测试套件
│   ├── TestSettingsConfiguration     # 设置面板测试
│   ├── TestLearningModeFlow         # Learning模式E2E
│   ├── TestSearchModeFlow           # Search模式E2E
│   └── TestRobustWaitingStrategies  # 最佳实践文档
└── README_E2E.md            # 本文件
```

## 运行测试

### 基本运行

```bash
# 启动后端服务器（另一个终端）
cd app
python -m uvicorn api.server:app --host 127.0.0.1 --port 8080

# 运行所有E2E测试
pytest tests/e2e/test_e2e_robust.py -v -s
```

### 指定测试类或方法

```bash
# 只测试Learning Mode
pytest tests/e2e/test_e2e_robust.py::TestLearningModeFlow -v -s

# 只测试单个方法
pytest tests/e2e/test_e2e_robust.py::TestLearningModeFlow::test_learning_mode_complete_flow_with_mock -v -s
```

### 可视化调试

```bash
# Headed模式：显示浏览器窗口
pytest tests/e2e/test_e2e_robust.py --headed -v -s

# 慢动作模式：每步操作延迟1秒
pytest tests/e2e/test_e2e_robust.py --headed --slowmo 1000 -v -s

# 录制视频
pytest tests/e2e/test_e2e_robust.py --video on
```

### 多浏览器测试

```bash
# Chromium（默认）
pytest tests/e2e/test_e2e_robust.py --browser chromium -v -s

# Firefox
pytest tests/e2e/test_e2e_robust.py --browser firefox -v -s

# WebKit（Safari引擎）
pytest tests/e2e/test_e2e_robust.py --browser webkit -v -s
```

### 生成报告

```bash
# 安装pytest-html
pip install pytest-html

# 生成HTML报告
pytest tests/e2e/test_e2e_robust.py --html=e2e_report.html --self-contained-html
```

## 核心设计原则

### 1. ✅ 智能等待 - NO 硬编码超时

**❌ 错误做法（脆弱）**:
```python
send_btn.click()
page.wait_for_timeout(15000)  # 硬编码15秒,太脆弱!
```

**✅ 正确做法（健壮）**:
```python
send_btn.click()

# 策略1：监控Stop按钮生命周期
stop_btn = page.locator("#stop-btn")
expect(stop_btn).to_be_visible(timeout=5000)   # 确认流开始
expect(stop_btn).to_be_hidden(timeout=60000)   # 确认流结束

# 策略2：监控Send按钮状态
expect(send_btn).to_be_enabled(timeout=60000)  # 重新启用表示完成

# 策略3：验证内容存在
assistant_msg = page.locator(".message.assistant").last
expect(assistant_msg).to_be_visible()
```

**为什么这样做？**
- **适应性强**: 快速响应几秒,慢速响应几十秒,都能正确处理
- **提前失败**: 如果真的卡住,在timeout时立即报错
- **语义明确**: 代码表达"等待完成",而非"等待N秒"

### 2. ✅ 弹性定位器 - 优先用户可见属性

**❌ 脆弱选择器**:
```python
# CSS路径：DOM变化就失效
page.locator("div.main > div:nth-child(3) > button")

# 依赖实现细节：重构代码就失效
page.locator(".css-xyz123")
```

**✅ 健壮选择器**:
```python
# 优先级1：语义化role + 文本
page.get_by_role("button", name="Learning Mode")
page.get_by_role("button").filter(has_text="Learning Mode")

# 优先级2：稳定的ID/data属性
page.locator("#send-btn")
page.locator("[data-mode='learning']")

# 优先级3：占位符文本
page.get_by_placeholder("Enter a statement")
```

### 3. ✅ 网络模拟 - 避免真实API调用

**为什么需要模拟？**
- 💰 **节省成本**: OpenAI/DeepSeek API按token计费,每次测试几美元
- ⚡ **提高速度**: 模拟响应<100ms,真实API可能10-30秒
- 🎯 **确定性**: 模拟返回固定结果,真实API可能每次不同
- 🔒 **独立性**: 测试不依赖外部服务可用性

**conftest.py中的mock_api_responses fixture**:
```python
@pytest.fixture(scope="function")
def mock_api_responses(page: Page):
    def handle_learn(route):
        # 模拟SSE流式响应
        sse_response = """data: {"chunk": "## Background\\n\\n"}
data: {"chunk": "The Pythagorean theorem..."}
...
data: [DONE]
"""
        route.fulfill(status=200, body=sse_response)
    
    page.route("**/learn", handle_learn)
    return page
```

**使用方式**:
```python
def test_learning_mode(app_page: Page, mock_api_responses):
    # mock_api_responses fixture自动拦截/learn请求
    # 不会调用真实API!
    ...
```

### 4. ✅ KaTeX感知 - 处理数学渲染

KaTeX将LaTeX转换为HTML,生成特殊的DOM结构:

```html
<!-- 输入: $a^2 + b^2 = c^2$ -->
<!-- KaTeX输出: -->
<span class="katex">
  <span class="katex-html">
    <span class="mord mathnormal">a</span>
    <span class="msupsub">
      <span class="mord">2</span>
    </span>
    ...
  </span>
</span>
```

**验证策略**:
```python
# 不要断言精确HTML（会因KaTeX版本变化）
# ❌ assert content == "<span class='katex'>...</span>"

# 而是验证KaTeX类的存在
# ✅
katex_elements = page.locator(".katex")
expect(katex_elements.first).to_be_visible()
assert katex_elements.count() > 0  # 至少有1个数学表达式
```

## SSE流式传输等待逻辑详解

Server-Sent Events (SSE)是单向流式协议,后端持续推送数据块,前端逐步渲染。

### SSE流的生命周期

```
用户点击Send → 开始流式传输 → 数据块陆续到达 → 流结束
     ↓                 ↓                ↓            ↓
Send按钮禁用     Stop按钮出现      内容逐步渲染   Stop按钮消失
                                                  Send按钮重新启用
```

### 我们的等待策略

`wait_for_sse_completion()`函数实现三层防护:

```python
def wait_for_sse_completion(page: Page, timeout_ms: int = 60000):
    stop_btn = page.locator("#stop-btn")
    send_btn = page.locator("#send-btn")
    
    # 第1层：Stop按钮监控（最可靠）
    if stop_btn.is_visible(timeout=1000):
        print("Stop按钮可见,等待消失...")
        expect(stop_btn).to_be_hidden(timeout=timeout_ms)
        # 当stop按钮消失时,流一定已经结束
    
    # 第2层：Send按钮状态（兜底保障）
    expect(send_btn).to_be_enabled(timeout=timeout_ms)
    # 即使stop按钮逻辑失败,send按钮重新启用也能确认完成
    
    # 第3层：内容验证（最终确认）
    assistant_msg = page.locator(".message.assistant").last
    expect(assistant_msg).to_be_visible(timeout=5000)
    # 确保至少有一条AI消息渲染完成
```

**为什么需要三层？**
- **第1层**可能失败：快速响应时stop按钮可能不出现
- **第2层**可能不够：按钮启用≠DOM完全更新
- **第3层**作确认：真正验证内容已渲染

## 测试覆盖矩阵

| 功能模块 | 测试场景 | 状态 |
|---------|---------|------|
| **Settings** | 打开设置面板 | ✅ |
| **Settings** | 配置LLM API密钥 | ✅ |
| **Settings** | 保存配置到localStorage | ✅ |
| **Learning** | 从主页导航 | ✅ |
| **Learning** | 提交查询 | ✅ |
| **Learning** | 接收结构化响应 | ✅ |
| **Learning** | 验证4个section | ✅ |
| **Learning** | KaTeX渲染验证 | ✅ |
| **Search** | 提交搜索查询 | ✅ |
| **Search** | 接收定理列表 | ✅ |
| **Search** | 验证相似度分数 | ✅ |
| **Solving** | 复杂证明生成 | 🚧 待添加 |
| **Reviewing** | PDF上传审查 | 🚧 待添加 |
| **多模式** | 模式间切换 | 🚧 待添加 |

## 扩展测试套件

### 添加新的测试

```python
class TestSolvingModeFlow:
    def test_solve_complex_problem(self, app_page: Page, mock_api_responses):
        """测试Solving模式的研究级别证明"""
        
        # 1. 在conftest.py添加mock
        # page.route("**/solve", handle_solve)
        
        # 2. 导航到Solving模式
        solving_card = app_page.get_by_role("button").filter(has_text="Problem Solving")
        solving_card.click()
        
        # 3. 提交复杂问题
        input_textarea = app_page.locator("#input-textarea")
        input_textarea.fill("Prove: For any positive integer n, ...")
        
        # 4. 使用智能等待
        send_btn = app_page.locator("#send-btn")
        send_btn.click()
        wait_for_sse_completion(app_page)
        
        # 5. 验证结果
        # Solving模式特有的UI元素
        blueprint = app_page.locator(".proof-blueprint")
        expect(blueprint).to_be_visible()
```

### 添加新的mock响应

在`conftest.py`的`mock_api_responses` fixture中:

```python
def setup_mocks():
    # 现有的/learn和/search mock...
    
    # 添加新的/solve mock
    def handle_solve(route):
        sse_response = """data: {"status": "searching", "step": "search"}
data: {"status": "generating_proof", "step": "proof"}
data: {"chunk": "## Proof Blueprint\\n\\n"}
data: {"chunk": "Step 1: Establish base case..."}
...
data: [DONE]
"""
        route.fulfill(status=200, body=sse_response)
    
    page.route("**/solve", handle_solve)
```

## 调试技巧

### 1. 暂停执行并手动探索

```python
def test_debug_learning(app_page: Page):
    learning_card = app_page.get_by_role("button").filter(has_text="Learning Mode")
    learning_card.click()
    
    # 暂停！打开Playwright Inspector
    page.pause()
    
    # 在Inspector中可以：
    # - 手动操作页面
    # - 在控制台测试选择器
    # - 查看DOM结构
```

### 2. 截图保存状态

```python
# 在关键步骤保存截图
app_page.screenshot(path="before_submit.png")
send_btn.click()
wait_for_sse_completion(app_page)
app_page.screenshot(path="after_completion.png")
```

### 3. 监控网络请求

```python
# 打印所有请求
app_page.on("request", lambda req: print(f"→ {req.method} {req.url}"))

# 打印所有响应
app_page.on("response", lambda resp: print(f"← {resp.status} {resp.url}"))
```

### 4. Console日志捕获

```python
# 捕获浏览器console.log
app_page.on("console", lambda msg: print(f"[Browser Console] {msg.text}"))
```

## 持续集成（CI）配置

### GitHub Actions示例

```yaml
# .github/workflows/e2e-tests.yml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          python -m playwright install --with-deps chromium
      
      - name: Start backend
        run: |
          cd app
          python -m uvicorn api.server:app --host 127.0.0.1 --port 8080 &
          sleep 5  # 等待服务器启动
      
      - name: Run E2E tests
        run: |
          pytest tests/e2e/test_e2e_robust.py -v --html=e2e_report.html
      
      - name: Upload test report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: e2e-report
          path: e2e_report.html
```

## 性能基准

基于mock响应的典型测试执行时间:

| 测试 | 执行时间 | 说明 |
|-----|---------|------|
| `test_open_settings_panel` | ~2s | DOM操作 |
| `test_configure_llm_api_keys` | ~3s | 表单填写+localStorage验证 |
| `test_learning_mode_complete_flow_with_mock` | ~5s | 完整流程+SSE等待 |
| `test_search_mode_returns_results` | ~4s | 搜索+结果验证 |
| **总计（全套）** | **~15s** | 远快于真实API（>2分钟）|

## 常见问题

### Q: 为什么测试有时超时失败？

**A**: 检查以下几点:
1. 后端服务器是否正在运行？`curl http://127.0.0.1:8080/health`
2. 模拟是否正确设置？在测试中使用`mock_api_responses` fixture
3. 选择器是否仍然有效？运行`pytest --headed -s`查看

### Q: 如何测试真实API（不用mock）？

**A**: 创建单独的测试文件:

```python
# test_e2e_real_api.py
@pytest.mark.integration  # 标记为集成测试
def test_learning_real_api(app_page: Page):
    # 注意：不使用mock_api_responses fixture!
    learning_card = app_page.get_by_role("button").filter(has_text="Learning Mode")
    learning_card.click()
    # ... 其余代码相同
    wait_for_sse_completion(app_page, timeout_ms=120000)  # 真实API需要更长时间
```

运行真实API测试:
```bash
pytest tests/e2e/test_e2e_real_api.py -m integration -v -s
```

### Q: 测试在CI中失败,但本地通过？

**A**: 常见原因:
1. **时序问题**: CI环境可能更慢,增加timeout
2. **浏览器差异**: 指定具体浏览器`--browser chromium`
3. **依赖缺失**: 确保`playwright install --with-deps`安装系统依赖

## 最佳实践总结

✅ **DO**:
- 使用语义化选择器（role, text, placeholder）
- 等待具体的DOM状态变化,不用硬编码超时
- Mock外部API避免费用和不确定性
- 为每个测试写清晰的文档字符串
- 使用fixtures共享设置逻辑

❌ **DON'T**:
- 不要使用脆弱的CSS路径选择器
- 不要使用`wait_for_timeout()`等待异步操作
- 不要在CI中调用真实付费API
- 不要在一个测试中测试多个功能
- 不要忽略失败的断言

## 进一步学习

- [Playwright官方文档](https://playwright.dev/python/)
- [pytest-playwright GitHub](https://github.com/microsoft/playwright-pytest)
- [Best Practices for E2E Testing](https://martinfowler.com/articles/practical-test-pyramid.html)

---

**创建时间**: 2026-05-04  
**作者**: Expert QA Automation Engineer  
**框架**: pytest-playwright (Python)
