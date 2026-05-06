"""调试测试 - 验证基本功能"""
import pytest
from playwright.sync_api import Page, expect


@pytest.fixture
def app_page(page: Page):
    """打开应用"""
    page.goto("http://localhost:8080/ui/")
    page.wait_for_load_state("networkidle")
    return page


def test_debug_basic_navigation(app_page: Page):
    """调试：验证从主页到聊天视图的基本切换"""

    # 1. 验证在主页
    print("\n=== Step 1: 验证主页 ===")
    home_view = app_page.locator("#home-view")
    expect(home_view).to_be_visible()
    print(f"home-view display: {home_view.evaluate('el => getComputedStyle(el).display')}")

    # 2. 找到learning卡片
    print("\n=== Step 2: 找到learning卡片 ===")
    learning_card = app_page.locator("button.feature-card[data-mode='learning']")
    expect(learning_card).to_be_visible()
    print("Found learning card")

    # 3. 点击卡片
    print("\n=== Step 3: 点击learning卡片 ===")
    learning_card.click()

    # 4. 等待一段时间
    app_page.wait_for_timeout(2000)

    # 5. 检查视图状态
    print("\n=== Step 4: 检查视图状态 ===")
    chat_view = app_page.locator("#chat-view")
    print(f"chat-view exists: {chat_view.count() > 0}")
    if chat_view.count() > 0:
        print(f"chat-view display: {chat_view.evaluate('el => getComputedStyle(el).display')}")
        print(f"chat-view visibility: {chat_view.evaluate('el => getComputedStyle(el).visibility')}")
        print(f"chat-view opacity: {chat_view.evaluate('el => getComputedStyle(el).opacity')}")

    print(f"home-view display: {home_view.evaluate('el => getComputedStyle(el).display')}")

    # 6. 测试发送消息
    print("\n=== Step 5: 测试发送消息 ===")
    input_textarea = app_page.locator("#input-textarea")
    expect(input_textarea).to_be_visible()
    input_textarea.fill("什么是勾股定理")

    send_btn = app_page.locator("#send-btn")
    expect(send_btn).to_be_visible()
    send_btn.click()

    # 7. 等待响应
    print("\n=== Step 6: 等待AI响应 ===")
    app_page.wait_for_timeout(60000)  # 等待60秒

    # 8. 检查是否有消息
    user_messages = app_page.locator(".message.user")
    assistant_messages = app_page.locator(".message.ai")

    print(f"User messages count: {user_messages.count()}")
    print(f"Assistant messages count: {assistant_messages.count()}")

    if user_messages.count() > 0:
        print("User message found")
    if assistant_messages.count() > 0:
        print("Assistant message found")
        last_content = assistant_messages.last.locator(".message-content").text_content()
        print(f"Assistant response length: {len(last_content)}")
    else:
        print("No assistant message found")
        # 检查是否有错误消息
        error_toast = app_page.locator(".toast-error")
        if error_toast.count() > 0:
            print(f"Error toast found: {error_toast.first.text_content()}")

    # 9. 截图
    app_page.screenshot(path="debug_after_send.png")
    print("\n=== Screenshot saved: debug_after_send.png ===")

    # 10. 检查网络请求
    print("\n=== Step 7: 检查控制台错误 ===")
    # Playwright会自动捕获控制台消息，如果有的话
