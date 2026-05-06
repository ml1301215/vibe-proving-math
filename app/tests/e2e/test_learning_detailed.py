"""详细调试测试 - 查看Learning模式的实际DOM结构"""
import pytest
from playwright.sync_api import Page, expect


@pytest.fixture
def app_page(page: Page):
    """打开应用"""
    page.goto("http://localhost:8080/ui/")
    page.wait_for_load_state("networkidle")
    return page


def test_learning_mode_detailed(app_page: Page):
    """详细测试Learning模式 - 查看实际DOM和输出"""

    print("\n=== 1. 访问主页 ===")
    home_view = app_page.locator("#home-view")
    expect(home_view).to_be_visible()

    print("\n=== 2. 点击Learning卡片 ===")
    learning_card = app_page.locator("button.feature-card[data-mode='learning']")
    learning_card.click()
    app_page.wait_for_timeout(1500)

    print("\n=== 3. 验证聊天视图 ===")
    chat_view = app_page.locator("#chat-view")
    expect(chat_view).to_be_visible()

    print("\n=== 4. 输入并发送消息 ===")
    input_textarea = app_page.locator("#input-textarea")
    input_textarea.fill("什么是勾股定理")

    send_btn = app_page.locator("#send-btn")
    send_btn.click()

    print("\n=== 5. 等待AI完整生成（90秒）===")
    app_page.wait_for_timeout(90000)

    print("\n=== 6. 截图保存 ===")
    app_page.screenshot(path="learning_test_result.png")

    print("\n=== 7. 分析DOM结构 ===")

    # 检查所有可能的消息容器
    chat_container = app_page.locator("#chat-container")
    print(f"Chat container visible: {chat_container.is_visible()}")
    print(f"Chat container HTML length: {len(chat_container.inner_html())}")

    # 检查用户消息
    user_messages = app_page.locator(".message.user")
    print(f"User messages count: {user_messages.count()}")

    # 检查assistant消息
    assistant_messages = app_page.locator(".message.ai")
    print(f"Assistant messages count: {assistant_messages.count()}")

    # 检查learning-specific的结构
    learn_body = app_page.locator("#learn-body")
    if learn_body.count() > 0:
        print(f"learn-body found: visible={learn_body.is_visible()}")
        print(f"learn-body content length: {len(learn_body.inner_html())}")

        # 检查各个section
        sections = ["background", "prereq", "proof", "examples"]
        for section in sections:
            section_el = app_page.locator(f"[data-section='{section}']")
            if section_el.count() > 0:
                status_class = section_el.get_attribute("class")
                print(f"  Section {section}: exists, classes={status_class}")

                # 检查section内容
                section_body = section_el.locator(".accordion-body")
                if section_body.count() > 0:
                    content = section_body.text_content()
                    print(f"    Content length: {len(content)}, preview: {content[:100]}...")

    # 检查是否有错误
    error_sections = app_page.locator(".section-error")
    print(f"\nError sections: {error_sections.count()}")
    if error_sections.count() > 0:
        for i in range(error_sections.count()):
            error_text = error_sections.nth(i).text_content()
            print(f"  Error {i}: {error_text[:200]}")

    # 最终断言
    print("\n=== 8. 最终验证 ===")
    if learn_body.count() > 0:
        content_length = len(learn_body.inner_html())
        print(f"Total learning content: {content_length} characters")
        assert content_length > 500, f"Learning content too short: {content_length} chars"
        print("✅ Test PASSED: Learning mode generated sufficient content")
    else:
        assert False, "No learn-body element found - Learning mode structure not recognized"
