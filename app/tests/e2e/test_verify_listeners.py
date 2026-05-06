"""验证事件监听器绑定"""
import pytest
from playwright.sync_api import Page


def test_verify_event_listeners(app_page: Page):
    """验证卡片的事件监听器是否被绑定"""

    # 检查 feature-card 元素
    feature_cards = app_page.locator(".feature-card")
    card_count = feature_cards.count()
    print(f"\n[DEBUG] Found {card_count} feature-card elements")

    if card_count == 0:
        print("[ERROR] No .feature-card elements found!")
        print("[DEBUG] Let's check if cards have different classes...")

        # 检查是否有其他卡片类名
        all_cards = app_page.locator("[class*='card']")
        print(f"[DEBUG] Found {all_cards.count()} elements with 'card' in class")

        for i in range(min(all_cards.count(), 6)):
            card = all_cards.nth(i)
            classes = card.get_attribute("class")
            data_mode = card.get_attribute("data-mode")
            data_action = card.get_attribute("data-action")
            text = card.text_content()[:50] if card.is_visible() else "(hidden)"
            print(f"  Card {i}: class='{classes}', data-mode='{data_mode}', data-action='{data_action}'")
            print(f"           text='{text}'")

    # 检查Learning卡片的data-mode属性
    learning_containers = app_page.locator("*:has-text('Learning Mode')").filter(has_text="Step-by-step")
    print(f"\n[DEBUG] Found {learning_containers.count()} containers with 'Learning Mode' text")

    if learning_containers.count() > 0:
        container = learning_containers.first
        tag_name = container.evaluate("el => el.tagName")
        classes = container.get_attribute("class")
        data_mode = container.get_attribute("data-mode")
        data_action = container.get_attribute("data-action")

        print(f"[DEBUG] Learning Mode container:")
        print(f"  Tag: {tag_name}")
        print(f"  Classes: {classes}")
        print(f"  data-mode: {data_mode}")
        print(f"  data-action: {data_action}")

        # 检查是否有事件监听器
        has_click_listener = container.evaluate("""el => {
            const events = getEventListeners ? getEventListeners(el) : null;
            return events && events.click ? events.click.length : 'N/A (getEventListeners not available)';
        }""")
        print(f"  Click listeners: {has_click_listener}")

    # 检查 switchMode 函数是否存在
    switch_mode_exists = app_page.evaluate("() => typeof switchMode !== 'undefined'")
    print(f"\n[DEBUG] switchMode function exists: {switch_mode_exists}")

    # 检查 AppState 是否存在
    app_state_exists = app_page.evaluate("() => typeof AppState !== 'undefined'")
    print(f"[DEBUG] AppState exists: {app_state_exists}")

    if app_state_exists:
        current_view = app_page.evaluate("() => AppState.view")
        current_mode = app_page.evaluate("() => AppState.mode")
        print(f"[DEBUG] Current AppState.view: {current_view}")
        print(f"[DEBUG] Current AppState.mode: {current_mode}")

    # 截图
    app_page.screenshot(path="debug_event_listeners.png")
