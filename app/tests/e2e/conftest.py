"""Playwright conftest.py - 端到端测试配置"""
import pytest
from playwright.sync_api import Browser, BrowserContext, Page


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """配置浏览器上下文参数"""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "locale": "zh-CN",
        "timezone_id": "Asia/Shanghai",
    }


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    """配置浏览器启动参数"""
    return {
        **browser_type_launch_args,
        "headless": False,  # 显示浏览器窗口
        "slow_mo": 500,      # 慢速运行，便于观察
    }


@pytest.fixture
def context(browser: Browser):
    """创建浏览器上下文"""
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        locale="zh-CN",
    )
    yield context
    context.close()


@pytest.fixture
def page(context: BrowserContext):
    """创建新页面"""
    page = context.new_page()
    yield page
    page.close()


@pytest.fixture(scope="function")
def app_page(page: Page):
    """
    Navigate to the application and ensure it's fully loaded.

    This fixture:
    1. Navigates to the local dev server
    2. Waits for network idle (all resources loaded)
    3. Verifies the main title is visible (DOM fully rendered)

    Returns:
        Page: Playwright page object ready for testing
    """
    page.goto("http://127.0.0.1:8080/ui/")
    page.wait_for_load_state("networkidle")

    # Verify app is fully loaded by checking for the main title (use specific heading)
    # Use get_by_role to be more specific - the main title is an h1
    page.get_by_role("heading", name="vibe_proving").wait_for(state="visible", timeout=10000)

    return page


@pytest.fixture(scope="function")
def mock_api_responses(page: Page):
    """
    Setup network mocking to prevent expensive API calls during tests.
    This fixture intercepts all backend API calls and returns mock responses.

    CRITICAL: This prevents actual OpenAI/DeepSeek API calls, saving costs and
    ensuring test determinism.
    """

    def setup_mocks():
        # Mock /learn endpoint (Learning Mode SSE streaming)
        def handle_learn(route):
            # Simulate realistic SSE streaming with multiple chunks
            sse_response = """data: {"chunk": "## Background\\n\\n"}
data: {"chunk": "The Pythagorean theorem is one of the most famous theorems in mathematics.\\n\\n"}
data: {"status": "generating_prerequisites", "step": "prereq"}
data: {"chunk": "## Prerequisites\\n\\n"}
data: {"chunk": "- Understanding of right triangles\\n- Basic algebra\\n\\n"}
data: {"status": "generating_proof", "step": "proof"}
data: {"chunk": "## Complete Proof\\n\\n"}
data: {"chunk": "Consider a right triangle with legs $a$ and $b$, and hypotenuse $c$. Then $a^2 + b^2 = c^2$.\\n\\n"}
data: {"status": "generating_examples", "step": "examples"}
data: {"chunk": "## Examples\\n\\n"}
data: {"chunk": "1. Triangle with sides 3, 4, 5: $3^2 + 4^2 = 9 + 16 = 25 = 5^2$\\n"}
data: {"status": "done", "step": "done"}
data: [DONE]
"""
            route.fulfill(
                status=200,
                headers={
                    "Content-Type": "text/event-stream",
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",
                },
                body=sse_response
            )

        # Mock /search endpoint (Search Mode SSE streaming)
        def handle_search(route):
            sse_response = """data: {"chunk": "## Search Results\\n\\n"}
data: {"chunk": "Found 2 matching theorems:\\n\\n"}
data: {"chunk": "### Pythagorean Theorem\\n"}
data: {"chunk": "In a right triangle with legs $a$, $b$ and hypotenuse $c$, we have $a^2 + b^2 = c^2$\\n\\n"}
data: {"chunk": "**Similarity**: 95%\\n\\n"}
data: {"chunk": "### Fermat's Last Theorem\\n"}
data: {"chunk": "For $n > 2$, there are no positive integers satisfying $a^n + b^n = c^n$\\n\\n"}
data: {"chunk": "**Similarity**: 68%\\n\\n"}
data: {"status": "done", "step": "done"}
data: [DONE]
"""
            route.fulfill(
                status=200,
                headers={"Content-Type": "text/event-stream"},
                body=sse_response
            )

        page.route("**/learn", handle_learn)
        page.route("**/search", handle_search)

    setup_mocks()
    return page
