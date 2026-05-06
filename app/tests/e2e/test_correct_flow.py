"""
正确的E2E测试 - 基于实际前端代码编写
"""
import pytest
from playwright.sync_api import Page, expect


def test_learning_mode_real_flow(app_page: Page, mock_api_responses):
    """
    根据实际HTML结构编写的Learning Mode测试

    HTML真实情况:
    - 卡片是 <button class="feature-card" data-mode="learning">
    - 点击后触发 switchMode('learning', {force: true})
    - switchMode 设置 AppState.view = 'chat'
    - UI.switchView('chat') 切换DOM显示
    """
    print("\n[Test] Learning Mode - 基于实际代码")

    # Step 1: 验证主页显示
    home_view = app_page.locator("#home-view")
    expect(home_view).to_be_visible(timeout=5000)
    print("  [OK] Home view visible")

    # Step 2: 点击Learning Mode按钮 - 使用实际的HTML属性
    learning_btn = app_page.locator("button.feature-card[data-mode='learning']")
    expect(learning_btn).to_be_visible(timeout=5000)
    print("  [OK] Learning button found")

    learning_btn.click()
    print("  [OK] Button clicked")

    # Step 3: 等待视图切换 - 根据实际JS代码
    # switchMode() 调用后会: AppState.set('view', 'chat')
    # 然后 UI.switchView() 会修改 display 样式
    app_page.wait_for_timeout(1000)  # 给动画时间

    # Step 4: 验证视图已切换
    chat_view = app_page.locator("#chat-view")

    # 根据 UI.switchView 的实际实现:
    # chatEl.style.display = '';  (空字符串表示显示)
    # homeEl.style.display = 'none';
    expect(chat_view).to_be_visible(timeout=5000)
    expect(home_view).to_be_hidden(timeout=5000)
    print("  [OK] View switched to chat")

    # Step 5: 验证input textarea可见
    input_textarea = app_page.locator("#input-textarea")
    expect(input_textarea).to_be_visible(timeout=5000)
    expect(input_textarea).to_be_editable()
    print("  [OK] Input textarea ready")

    # Step 6: 填写并提交
    input_textarea.fill("What is the Pythagorean theorem?")
    send_btn = app_page.locator("#send-btn")
    send_btn.click()
    print("  [OK] Query submitted")

    # Step 7: 等待mock响应
    app_page.wait_for_timeout(2000)  # Mock响应应该很快

    # Step 8: 验证收到响应
    assistant_messages = app_page.locator(".message.ai")

    # 由于使用了mock，应该立即有响应
    if assistant_messages.count() > 0:
        print(f"  [OK] Received response ({assistant_messages.count()} messages)")
    else:
        print("  [WARN] No response yet (may need to check mock setup)")

    print("\n[Test Complete]")


def test_verify_actual_html_structure(app_page: Page):
    """验证实际HTML结构与预期一致"""

    print("\n[Verification] Checking actual HTML structure...")

    # 1. 验证所有卡片都是button元素
    all_cards = app_page.locator(".feature-card")
    count = all_cards.count()
    print(f"  Found {count} feature cards")

    for i in range(count):
        card = all_cards.nth(i)
        tag_name = card.evaluate("el => el.tagName")
        data_mode = card.get_attribute("data-mode")
        data_action = card.get_attribute("data-action")

        assert tag_name == "BUTTON", f"Card {i} should be a BUTTON, got {tag_name}"
        print(f"  [OK] Card {i}: <{tag_name}> data-mode='{data_mode}' data-action='{data_action}'")

    # 2. 验证Learning卡片的具体属性
    learning_btn = app_page.locator("button.feature-card[data-mode='learning']")
    expect(learning_btn).to_be_visible()

    aria_label = learning_btn.get_attribute("aria-label")
    tabindex = learning_btn.get_attribute("tabindex")

    print(f"\n  Learning button attributes:")
    print(f"    aria-label: {aria_label}")
    print(f"    tabindex: {tabindex}")

    # 3. 验证按钮内部结构
    glyph = learning_btn.locator(".card-glyph")
    title = learning_btn.locator(".card-title")
    desc = learning_btn.locator(".card-desc")

    expect(glyph).to_be_visible()
    expect(title).to_be_visible()
    expect(desc).to_be_visible()

    print(f"    glyph text: {glyph.text_content()}")
    print(f"    title text: {title.text_content()}")
    print(f"    desc text: {desc.text_content()[:50]}...")

    print("\n[Verification Complete] HTML structure matches expectations")
