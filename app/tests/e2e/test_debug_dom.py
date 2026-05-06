"""Debug test to inspect actual DOM structure"""
import pytest
from playwright.sync_api import Page


def test_debug_after_clicking_learning_card(app_page: Page):
    """调试：点击Learning卡片后的状态"""

    # 点击前截图
    app_page.screenshot(path="debug_before_click.png")
    print("\n[DEBUG] Before click screenshot saved")

    # 点击Learning Mode卡片
    learning_card = app_page.locator(".feature-card, [class*='card']").filter(has_text="Learning Mode").first
    if learning_card.count() == 0:
        learning_card = app_page.locator("*:has-text('Learning Mode')").filter(has_text="Step-by-step").first

    print(f"[DEBUG] Learning card visible: {learning_card.is_visible()}")
    learning_card.click()
    print("[DEBUG] Clicked learning card")

    # 等待一段时间让动画完成
    app_page.wait_for_timeout(2000)

    # 点击后截图
    app_page.screenshot(path="debug_after_click.png")
    print("[DEBUG] After click screenshot saved")

    # 检查 input textarea
    input_textarea = app_page.locator("#input-textarea")
    print(f"\n[DEBUG] Input textarea count: {input_textarea.count()}")

    if input_textarea.count() > 0:
        print(f"[DEBUG] Input visible: {input_textarea.is_visible()}")
        print(f"[DEBUG] Input hidden: {input_textarea.is_hidden()}")
        print(f"[DEBUG] Input editable: {input_textarea.is_editable()}")

        # 获取样式信息
        display = input_textarea.evaluate("el => window.getComputedStyle(el).display")
        visibility = input_textarea.evaluate("el => window.getComputedStyle(el).visibility")
        opacity = input_textarea.evaluate("el => window.getComputedStyle(el).opacity")

        print(f"[DEBUG] Computed styles:")
        print(f"  display: {display}")
        print(f"  visibility: {visibility}")
        print(f"  opacity: {opacity}")

    # 检查当前视图
    home_view = app_page.locator("#home-view")
    chat_view = app_page.locator("#chat-view")

    print(f"\n[DEBUG] home-view visible: {home_view.is_visible() if home_view.count() > 0 else 'not found'}")
    print(f"[DEBUG] chat-view visible: {chat_view.is_visible() if chat_view.count() > 0 else 'not found'}")

    # 检查 body 的 data-view 属性
    body_view = app_page.evaluate("() => document.body.getAttribute('data-view')")
    print(f"[DEBUG] body data-view: {body_view}")

    # 列出所有 visible 的主要容器
    all_containers = app_page.locator("div[id*='view'], div[class*='view']")
    print(f"\n[DEBUG] Found {all_containers.count()} view containers")
    for i in range(min(all_containers.count(), 5)):
        cont = all_containers.nth(i)
        cont_id = cont.get_attribute("id")
        cont_class = cont.get_attribute("class")
        is_visible = cont.is_visible()
        print(f"  Container {i}: id='{cont_id}', class='{cont_class}', visible={is_visible}")

