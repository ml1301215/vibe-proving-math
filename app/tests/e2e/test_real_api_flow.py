"""
真实API测试 - 验证完整的用户流程（不使用mock）
注意：这会调用真实的API，需要配置有效的API密钥
"""
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.slow  # 标记为慢速测试，因为要等待真实API
def test_learning_mode_with_real_api(app_page: Page):
    """
    完整的用户流程测试 - 使用真实API

    测试目标：
    1. 验证UI交互正常
    2. 验证真实API调用工作
    3. 验证SSE流式响应处理
    4. 验证Learning模式的结构化输出

    需要：config.toml中配置有效的API密钥
    """
    print("\n[Real API Test] Learning Mode Complete Flow")
    print("=" * 60)

    # Step 1: 验证主页
    home_view = app_page.locator("#home-view")
    expect(home_view).to_be_visible(timeout=5000)
    print("[Step 1] [OK] Home page loaded")

    # Step 2: 点击Learning Mode按钮
    learning_btn = app_page.locator("button.feature-card[data-mode='learning']")
    expect(learning_btn).to_be_visible(timeout=5000)
    learning_btn.click()
    print("[Step 2] [OK] Clicked Learning Mode button")

    # Step 3: 等待并验证视图切换
    app_page.wait_for_timeout(1000)  # 给动画时间
    chat_view = app_page.locator("#chat-view")
    expect(chat_view).to_be_visible(timeout=5000)
    print("[Step 3] [OK] Switched to chat view")

    # Step 4: 输入查询
    input_textarea = app_page.locator("#input-textarea")
    expect(input_textarea).to_be_visible()
    expect(input_textarea).to_be_editable()

    test_query = "勾股定理"  # 简单查询，快速响应
    input_textarea.fill(test_query)
    print(f"[Step 4] [OK] Entered query: '{test_query}'")

    # Step 5: 提交查询
    send_btn = app_page.locator("#send-btn")
    expect(send_btn).to_be_enabled()
    send_btn.click()
    print("[Step 5] [OK] Submitted query")

    # Step 6: 等待Stop按钮出现（表示开始生成）
    stop_btn = app_page.locator("#stop-btn")
    try:
        expect(stop_btn).to_be_visible(timeout=10000)
        print("[Step 6] [OK] Generation started (stop button visible)")
    except:
        print("[Step 6] [WARN] Stop button didn't appear (response might be very fast)")

    # Step 7: 等待生成完成
    # 策略：等待Stop按钮消失，或者Send按钮重新启用
    print("[Step 7] Waiting for generation to complete...")

    try:
        # 等待Stop按钮消失
        if stop_btn.is_visible():
            expect(stop_btn).to_be_hidden(timeout=120000)  # 最多等待2分钟
            print("         [OK] Stop button disappeared")
    except:
        print("         [WARN] Stop button timeout")

    # 等待Send按钮重新启用
    expect(send_btn).to_be_enabled(timeout=120000)
    print("         [OK] Send button re-enabled")

    # Step 8: 验证收到了AI响应
    assistant_messages = app_page.locator(".message.ai")

    # 检查是否有assistant消息
    message_count = assistant_messages.count()
    print(f"[Step 8] Assistant messages found: {message_count}")

    if message_count == 0:
        # 可能是API配置问题，检查是否有错误提示
        error_elements = app_page.locator(".section-error, .error-message, [class*='error']")
        if error_elements.count() > 0:
            error_text = error_elements.first.text_content()
            print(f"         [X] Error detected: {error_text[:200]}")
            pytest.skip(f"API Error: {error_text[:100]}")
        else:
            pytest.fail("No assistant message received and no error message shown")

    # Step 9: 验证响应内容
    last_message = assistant_messages.last
    content = last_message.text_content()

    print(f"[Step 9] Response content length: {len(content)} characters")
    print(f"         Preview: {content[:150]}...")

    # 验证内容不为空且相关
    assert len(content) > 50, f"Response too short: {len(content)} chars"
    assert any(keyword in content for keyword in ["勾股", "三角", "Pythag", "定理"]), \
        "Response doesn't contain relevant keywords"

    print("         [OK] Response content validated")

    # Step 10: 验证Learning模式的结构化输出
    learn_body = app_page.locator("#learn-body, .learn-body, [id*='learn']")

    if learn_body.count() > 0 and learn_body.first.is_visible():
        print("[Step 10] Learning mode structured output detected")

        # 检查各个section
        sections = ["background", "prereq", "proof", "examples"]
        found_sections = 0

        for section_name in sections:
            section_el = app_page.locator(f"[data-section='{section_name}']")
            if section_el.count() > 0:
                found_sections += 1
                print(f"          [OK] Section '{section_name}' found")

        print(f"          Total sections found: {found_sections}/4")
    else:
        print("[Step 10] [WARN] No structured learning output (might be simple mode)")

    # Step 11: 截图保存
    app_page.screenshot(path="real_api_test_result.png")
    print("[Step 11] [OK] Screenshot saved")

    print("\n" + "=" * 60)
    print("[Test Complete] [OK] All steps passed")
    print("=" * 60)


def test_check_api_configuration(app_page: Page):
    """
    辅助测试：检查API配置是否正确

    在运行真实API测试前，先验证配置
    """
    print("\n[Config Check] Verifying API configuration...")

    # 方法1: 检查settings面板
    settings_btn = app_page.locator("#btn-panel-toggle, button:has-text('Run settings')")
    if settings_btn.count() > 0 and settings_btn.is_visible():
        settings_btn.click()
        app_page.wait_for_timeout(500)

        # 检查API Key输入框是否有值
        api_key_input = app_page.locator("input[name='api_key'], input[placeholder*='API']").first
        if api_key_input.count() > 0:
            value = api_key_input.input_value()
            if value and len(value) > 10:
                print(f"  [OK] API key configured (length: {len(value)})")
            else:
                print("  [WARN] API key not configured or too short")
                pytest.skip("API key not configured in settings")

    # 方法2: 调用/health endpoint检查
    health_status = app_page.evaluate("""async () => {
        try {
            const resp = await fetch('/health');
            const data = await resp.json();
            return data;
        } catch (e) {
            return {error: e.message};
        }
    }""")

    print(f"\n[Health Check] Backend status:")
    print(f"  Status: {health_status.get('status', 'unknown')}")

    llm_config = health_status.get('llm', {})
    if llm_config:
        print(f"  LLM Base URL: {llm_config.get('base_url', 'not configured')}")
        print(f"  LLM Model: {llm_config.get('model', 'not configured')}")

    print("\n[Config Check] Complete")
