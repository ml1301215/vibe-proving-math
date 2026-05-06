"""调试JavaScript执行流程"""
import pytest
from playwright.sync_api import Page


def test_debug_javascript_execution(app_page: Page):
    """追踪卡片点击后的JavaScript执行"""

    # 添加JavaScript监听器来追踪执行
    app_page.evaluate("""() => {
        window._debugLog = [];
        const originalSwitchMode = window.switchMode;
        window.switchMode = function(...args) {
            window._debugLog.push(['switchMode called', args]);
            return originalSwitchMode.apply(this, args);
        };

        const originalSet = AppState.set;
        AppState.set = function(key, value) {
            window._debugLog.push(['AppState.set', key, value]);
            return originalSet.call(this, key, value);
        };

        const originalSwitchView = UI.switchView;
        UI.switchView = function(view) {
            window._debugLog.push(['UI.switchView', view]);
            const homeEl = document.getElementById('home-view');
            const chatEl = document.getElementById('chat-view');
            window._debugLog.push(['Elements exist', homeEl != null, chatEl != null]);
            return originalSwitchView.call(this, view);
        };
    }""")

    print("\n[DEBUG] JavaScript监听器已设置")

    # 点击Learning Mode卡片
    learning_card = app_page.locator(".feature-card, [class*='card']").filter(has_text="Learning Mode").first
    learning_card.click()

    # 等待一点时间让JavaScript执行
    app_page.wait_for_timeout(2000)

    # 获取调试日志
    debug_log = app_page.evaluate("() => window._debugLog")

    print("\n[DEBUG] JavaScript执行日志:")
    for entry in debug_log:
        print(f"  {entry}")

    # 检查最终状态
    print("\n[DEBUG] 最终状态:")
    app_state_view = app_page.evaluate("() => AppState.view")
    app_state_mode = app_page.evaluate("() => AppState.mode")
    home_display = app_page.evaluate("() => document.getElementById('home-view').style.display")
    chat_display = app_page.evaluate("() => document.getElementById('chat-view').style.display")

    print(f"  AppState.view: {app_state_view}")
    print(f"  AppState.mode: {app_state_mode}")
    print(f"  home-view display: '{home_display}'")
    print(f"  chat-view display: '{chat_display}'")

    # 截图
    app_page.screenshot(path="debug_js_trace.png")
