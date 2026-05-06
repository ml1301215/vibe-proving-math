"""调试消息渲染问题"""
import pytest
from playwright.sync_api import Page, expect


def test_debug_message_rendering(app_page: Page):
    """详细调试为什么assistant消息没有显示"""

    print("\n[DEBUG] Testing message rendering flow")
    print("=" * 60)

    # Step 1: 切换到Learning Mode
    learning_btn = app_page.locator("button.feature-card[data-mode='learning']")
    learning_btn.click()
    app_page.wait_for_timeout(1000)
    print("[Step 1] Switched to Learning Mode")

    # Step 2: 监听网络请求
    requests = []
    responses = []

    def handle_request(request):
        if '/learn' in request.url or '/api' in request.url:
            requests.append({
                'url': request.url,
                'method': request.method,
            })
            print(f"  [Network] Request: {request.method} {request.url}")

    def handle_response(response):
        if '/learn' in response.url or '/api' in response.url:
            responses.append({
                'url': response.url,
                'status': response.status,
            })
            print(f"  [Network] Response: {response.status} {response.url}")

    app_page.on("request", handle_request)
    app_page.on("response", handle_response)

    # Step 3: 提交查询
    input_textarea = app_page.locator("#input-textarea")
    input_textarea.fill("勾股定理")

    send_btn = app_page.locator("#send-btn")
    send_btn.click()
    print("\n[Step 2] Query submitted")

    # Step 4: 等待响应完成
    app_page.wait_for_timeout(3000)
    try:
        expect(send_btn).to_be_enabled(timeout=60000)
        print("[Step 3] Send button re-enabled")
    except:
        print("[Step 3] [WARN] Send button still disabled")

    # Step 5: 检查所有消息元素
    print("\n[DEBUG] Checking all message-related elements:")

    # 检查各种可能的消息选择器
    selectors = [
        ".message",
        ".message.ai",
        ".message.user",
        "#messages-container .message",
        "[class*='message']",
        ".chat-messages .message",
        "#chat-messages .message",
    ]

    for selector in selectors:
        elements = app_page.locator(selector)
        count = elements.count()
        print(f"  Selector '{selector}': {count} elements")

        if count > 0:
            for i in range(min(count, 3)):
                el = elements.nth(i)
                classes = el.get_attribute("class")
                visible = el.is_visible()
                text = el.text_content()[:100] if visible else "(hidden)"
                print(f"    [{i}] class='{classes}', visible={visible}")
                print(f"        text: {text}")

    # Step 6: 检查messages容器
    print("\n[DEBUG] Checking message containers:")
    containers = [
        "#messages-container",
        "#chat-messages",
        ".chat-messages",
        ".messages",
    ]

    for container_id in containers:
        container = app_page.locator(container_id)
        if container.count() > 0:
            visible = container.first.is_visible()
            html = container.first.inner_html()[:200] if visible else "(hidden)"
            print(f"  Container '{container_id}': visible={visible}")
            print(f"    innerHTML: {html}...")

    # Step 7: 检查JavaScript状态
    print("\n[DEBUG] Checking JavaScript state:")
    js_state = app_page.evaluate("""() => {
        return {
            appState: typeof AppState !== 'undefined' ? {
                view: AppState.view,
                mode: AppState.mode,
                generating: AppState.generating,
            } : null,
            hasMessages: typeof window.messages !== 'undefined' ? window.messages.length : 'N/A',
            hasUI: typeof UI !== 'undefined',
        };
    }""")

    print(f"  AppState: {js_state.get('appState')}")
    print(f"  Messages array length: {js_state.get('hasMessages')}")
    print(f"  UI object exists: {js_state.get('hasUI')}")

    # Step 8: 检查是否有错误
    print("\n[DEBUG] Checking for errors:")
    error_selectors = [
        ".error",
        ".error-message",
        "[class*='error']",
        ".section-error",
    ]

    for selector in error_selectors:
        errors = app_page.locator(selector)
        if errors.count() > 0:
            print(f"  Found {errors.count()} error elements with '{selector}'")
            for i in range(min(errors.count(), 2)):
                text = errors.nth(i).text_content()[:150]
                print(f"    Error {i}: {text}")

    # Step 9: 打印网络请求汇总
    print("\n[DEBUG] Network summary:")
    print(f"  Total requests: {len(requests)}")
    print(f"  Total responses: {len(responses)}")

    # Step 10: 截图
    app_page.screenshot(path="debug_rendering.png", full_page=True)
    print("\n[DEBUG] Screenshot saved to debug_rendering.png")

    print("\n" + "=" * 60)
