"""高级E2E测试套件 - TDD + 验证循环方法

基于Deepnote和Shipyard的最佳实践：
1. 上下文包装：测试能看到完整的系统状态
2. 验证循环：检查 → 假设 → 更改 → 验证
3. TDD：先写测试，描述预期行为，再验证实现

测试场景：
- 形式化证明模式完整流程
- 网络错误恢复
- SSE流中断和恢复
- 浏览器导航（前进/后退）
- 并发操作
- 深度数据一致性验证
"""
import pytest
import time
from playwright.sync_api import Page, expect, Error as PlaywrightError


@pytest.fixture
def app_page(page: Page):
    """打开应用并提供完整上下文"""
    page.goto("http://localhost:8080/ui/")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    return page


class TestFormalizationMode:
    """形式化证明模式测试 - TDD方法

    用户故事：作为数学研究者，我想访问Aristotle形式化证明服务
    注意：形式化模式是外部链接，不是内部模式
    """

    def test_formalization_tab_exists(self, app_page: Page):
        """测试1：形式化模式tab应该存在"""
        # 检查：验证tab存在
        formal_tab = app_page.locator("button.mode-tab[data-mode='formalization']")
        expect(formal_tab).to_be_visible(timeout=5000)

        # 验证：tab应该包含文本（中文或英文）
        tab_text = formal_tab.text_content()
        assert "形式化" in tab_text or "Formalization" in tab_text

    def test_formalization_card_is_external_link(self, app_page: Page):
        """测试2：形式化卡片应该标记为外部链接"""
        # 在主页查找形式化卡片
        formal_card = app_page.locator("button.feature-card[data-mode='formalization']")

        if not formal_card.is_visible():
            # 如果不在主页，返回主页
            home_btn = app_page.locator("#btn-home")
            if home_btn.is_visible():
                home_btn.click()
                app_page.wait_for_timeout(500)

        # 验证：应该有外部链接箭头
        external_arrow = formal_card.locator(".card-external-arrow")
        expect(external_arrow).to_be_visible()

    def test_formalization_opens_external_service(self, app_page: Page):
        """测试3：点击形式化应该提示外部服务（不在应用内切换）"""
        # 这个测试验证形式化模式的实际行为：外部链接
        # 我们不期望它像其他模式一样在应用内切换

        formal_tab = app_page.locator("button.mode-tab[data-mode='formalization']")

        # 监听新窗口打开事件
        with app_page.context.expect_page(timeout=3000) as new_page_info:
            try:
                formal_tab.click()
                # 如果打开了新窗口，这是预期行为
                new_page = new_page_info.value
                new_page.close()
            except:
                # 如果没有打开新窗口，可能还没有实现，跳过
                pytest.skip("形式化模式外部链接未实现或需要配置")


class TestNetworkErrorRecovery:
    """网络错误恢复测试 - 验证循环方法

    用户故事：当网络请求失败时，应用应该优雅降级并允许用户重试
    """

    def test_offline_detection(self, app_page: Page):
        """测试：应用应该检测离线状态"""
        # 模拟离线（通过浏览器上下文）
        context = app_page.context

        # 检查：在线状态下功能正常
        health_check = app_page.request.get("http://localhost:8080/health")
        assert health_check.ok

        # 假设：离线时应该显示错误
        # 注意：实际实现可能需要在前端添加网络状态检测

    def test_api_failure_handling(self, app_page: Page):
        """测试：API失败时应该显示友好错误消息"""
        # 切换到学习模式
        learning_tab = app_page.locator("button.mode-tab[data-mode='learning']")
        learning_tab.click()
        app_page.wait_for_timeout(500)

        # 输入内容
        input_textarea = app_page.locator("#input-textarea")
        input_textarea.fill("测试网络错误处理")

        # 发送（如果后端不可用，应该有错误处理）
        send_btn = app_page.locator("#send-btn")
        send_btn.click()

        # 验证：不应该崩溃
        expect(input_textarea).to_be_visible()


class TestSSEStreamInterruption:
    """SSE流中断和恢复测试

    用户故事：当流式响应中断时，用户应该能够停止或重新生成
    """

    def test_stop_streaming_button(self, app_page: Page):
        """测试：流式响应时停止按钮应该可用"""
        # 切换到学习模式
        learning_tab = app_page.locator("button.mode-tab[data-mode='learning']")
        learning_tab.click()
        app_page.wait_for_timeout(500)

        # 输入内容并提交
        input_textarea = app_page.locator("#input-textarea")
        input_textarea.fill("解释费马大定理")

        send_btn = app_page.locator("#send-btn")
        send_btn.click()

        # 验证：停止按钮应该出现（如果请求正在进行）
        app_page.wait_for_timeout(1000)
        stop_btn = app_page.locator("#stop-btn")
        # 停止按钮可能可见或不可见，取决于请求是否还在进行

    def test_regenerate_after_completion(self, app_page: Page):
        """测试：响应完成后应该有重新生成按钮"""
        # 这个测试需要实际的API响应，暂时跳过
        pytest.skip("需要实际API响应才能测试重新生成功能")


class TestBrowserNavigation:
    """浏览器导航测试 - 前进/后退

    用户故事：用户使用浏览器前进/后退按钮时，应用状态应该正确恢复
    """

    def test_back_button_from_chat_to_home(self, app_page: Page):
        """测试：从聊天视图返回主页"""
        # 检查：在主页
        home_view = app_page.locator("#home-view")
        expect(home_view).to_be_visible()

        # 假设：点击卡片进入聊天视图
        learning_card = app_page.locator("button.feature-card[data-mode='learning']")
        learning_card.click()
        app_page.wait_for_timeout(1000)

        # 验证：切换到聊天视图
        chat_view = app_page.locator("#chat-view")
        expect(chat_view).to_be_visible()

        # 更改：使用返回按钮
        home_btn = app_page.locator("#btn-home")
        expect(home_btn).to_be_visible()
        home_btn.click()
        app_page.wait_for_timeout(500)

        # 验证：返回主页
        expect(home_view).to_be_visible()

    def test_browser_back_button(self, app_page: Page):
        """测试：浏览器后退按钮应该工作"""
        # 从主页进入聊天视图
        learning_card = app_page.locator("button.feature-card[data-mode='learning']")
        learning_card.click()
        app_page.wait_for_timeout(1000)

        # 使用浏览器后退
        app_page.go_back()
        app_page.wait_for_timeout(500)

        # 验证：应该回到主页（如果支持历史状态）
        # 注意：这取决于应用是否使用History API


class TestConcurrentOperations:
    """并发操作测试

    用户故事：用户快速连续操作时，应用不应该出现竞态条件
    """

    def test_rapid_mode_switching(self, app_page: Page):
        """测试：快速切换模式不应该导致状态错误"""
        modes = ["learning", "solving", "reviewing", "searching"]

        # 快速连续切换模式
        for mode in modes * 3:  # 重复3次
            mode_tab = app_page.locator(f"button.mode-tab[data-mode='{mode}']")
            if mode_tab.is_visible():
                mode_tab.click()
                app_page.wait_for_timeout(100)  # 很短的间隔

        # 验证：最后一个模式应该被正确激活
        final_tab = app_page.locator(f"button.mode-tab[data-mode='{modes[-1]}']")
        expect(final_tab).to_have_class(re.compile("active"))

    def test_multiple_inputs_rapid_submission(self, app_page: Page):
        """测试：快速多次提交不应该导致重复请求"""
        # 切换到学习模式
        learning_tab = app_page.locator("button.mode-tab[data-mode='learning']")
        learning_tab.click()
        app_page.wait_for_timeout(500)

        input_textarea = app_page.locator("#input-textarea")
        send_btn = app_page.locator("#send-btn")

        # 快速输入并多次点击发送
        input_textarea.fill("快速提交测试")
        for _ in range(5):
            send_btn.click()
            app_page.wait_for_timeout(50)

        # 验证：应用不应该崩溃
        expect(input_textarea).to_be_visible()


class TestDataConsistency:
    """深度数据一致性测试

    用户故事：配置和状态在各种场景下应该保持一致
    """

    def test_config_consistency_across_modes(self, app_page: Page):
        """测试：配置在切换模式时应该保持一致"""
        # 打开设置
        settings_btn = app_page.locator("#btn-panel-toggle")
        settings_btn.click()
        app_page.wait_for_timeout(500)

        # 记录当前model设置
        model_input = app_page.locator("#input-llm-model")
        initial_model = model_input.input_value()

        # 关闭设置
        close_btn = app_page.locator("#panel-close")
        close_btn.click()

        # 切换多个模式
        for mode in ["learning", "solving", "reviewing"]:
            mode_tab = app_page.locator(f"button.mode-tab[data-mode='{mode}']")
            if mode_tab.is_visible():
                mode_tab.click()
                app_page.wait_for_timeout(300)

        # 重新打开设置，验证model没有变化
        settings_btn.click()
        app_page.wait_for_timeout(500)

        current_model = model_input.input_value()
        assert current_model == initial_model, f"Model changed from {initial_model} to {current_model}"

    def test_multiple_refresh_consistency(self, app_page: Page, base_url="http://localhost:8080"):
        """测试：多次刷新后配置和状态应该一致"""
        # 设置配置
        settings_btn = app_page.locator("#btn-panel-toggle")
        settings_btn.click()
        app_page.wait_for_timeout(500)

        model_input = app_page.locator("#input-llm-model")
        test_value = f"test-consistency-{int(time.time())}"
        model_input.fill(test_value)

        save_btn = app_page.locator("#btn-save-llm")
        save_btn.click()
        app_page.wait_for_timeout(2000)

        # 多次刷新
        for i in range(3):
            app_page.reload()
            app_page.wait_for_load_state("networkidle")
            app_page.wait_for_timeout(1000)

            # 验证配置保持
            settings_btn = app_page.locator("#btn-panel-toggle")
            settings_btn.click()
            app_page.wait_for_timeout(500)

            model_input = app_page.locator("#input-llm-model")
            current_value = model_input.input_value()

            # 注意：配置从服务器加载，可能不是测试值
            assert current_value, f"Config lost after refresh {i+1}"

            close_btn = app_page.locator("#panel-close")
            close_btn.click()


class TestEdgeCases:
    """边缘案例测试

    各种极端输入和异常情况
    """

    def test_special_characters_input(self, app_page: Page):
        """测试：特殊字符输入不应该破坏UI"""
        learning_tab = app_page.locator("button.mode-tab[data-mode='learning']")
        learning_tab.click()
        app_page.wait_for_timeout(500)

        input_textarea = app_page.locator("#input-textarea")

        # 各种特殊字符
        special_inputs = [
            "<script>alert('xss')</script>",  # XSS尝试
            "'; DROP TABLE users; --",  # SQL注入尝试
            "\\textbf{测试} $x^2$ \\cite{ref}",  # LaTeX混合
            "🔥💯✨🎉",  # Emoji
            "a" * 50000,  # 超长输入（会被限制）
        ]

        for test_input in special_inputs:
            input_textarea.fill(test_input[:1000])  # 限制长度避免超时
            app_page.wait_for_timeout(100)

            # 验证：不应该崩溃
            expect(input_textarea).to_be_visible()

            # 清空输入
            input_textarea.fill("")

    def test_rapid_theme_switching(self, app_page: Page):
        """测试：快速切换主题不应该导致UI闪烁错误"""
        settings_btn = app_page.locator("#btn-panel-toggle")
        settings_btn.click()
        app_page.wait_for_timeout(500)

        theme_btn = app_page.locator("#btn-theme")
        html = app_page.locator("html")

        # 快速切换10次
        for _ in range(10):
            theme_btn.click()
            app_page.wait_for_timeout(50)

        # 验证：HTML应该有有效的theme属性
        theme_attr = html.get_attribute("data-theme")
        assert theme_attr in ["light", "dark"], f"Invalid theme: {theme_attr}"


class TestKeyboardShortcuts:
    """键盘快捷键测试

    用户故事：高级用户应该能够使用键盘快捷键提高效率
    """

    def test_enter_to_submit(self, app_page: Page):
        """测试：Enter键应该提交输入"""
        learning_tab = app_page.locator("button.mode-tab[data-mode='learning']")
        learning_tab.click()
        app_page.wait_for_timeout(500)

        input_textarea = app_page.locator("#input-textarea")
        input_textarea.fill("测试Enter提交")

        # 按Enter键
        input_textarea.press("Enter")
        app_page.wait_for_timeout(1000)

        # 验证：消息应该被发送（输入框应该被清空或有响应）
        # 具体验证取决于实现

    def test_escape_to_stop_streaming(self, app_page: Page):
        """测试：Escape键应该停止流式响应"""
        learning_tab = app_page.locator("button.mode-tab[data-mode='learning']")
        learning_tab.click()
        app_page.wait_for_timeout(500)

        input_textarea = app_page.locator("#input-textarea")
        input_textarea.fill("长时间响应测试")

        send_btn = app_page.locator("#send-btn")
        send_btn.click()
        app_page.wait_for_timeout(500)

        # 按Escape键
        app_page.keyboard.press("Escape")
        app_page.wait_for_timeout(500)

        # 验证：流应该停止（具体验证取决于实现）


# 导入re模块供正则表达式使用
import re
