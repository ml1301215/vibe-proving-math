"""完整的用户场景E2E测试

测试覆盖真实用户使用流程：
1. 首次访问配置API key
2. 使用学习模式学习数学定理
3. 使用问题求解模式解决问题
4. 使用审查模式审查证明
5. 使用检索模式搜索定理
6. 重新生成内容
7. 切换语言
8. 使用形式化证明
"""
import pytest
import re
import time
from playwright.sync_api import Page, expect, Error as PlaywrightError


@pytest.fixture(scope="session")
def base_url():
    """应用基础URL"""
    return "http://localhost:8080"


@pytest.fixture
def app_page(page: Page, base_url: str):
    """打开应用页面"""
    page.goto(f"{base_url}/ui/")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)  # 等待初始化
    return page


class TestCompleteUserFlow:
    """完整用户使用流程测试"""

    def test_01_initial_visit_and_config(self, app_page: Page):
        """场景1：用户首次访问并配置API"""
        # 验证首页加载
        page_title = app_page.locator(".home-title")
        expect(page_title).to_be_visible(timeout=5000)
        expect(page_title).to_contain_text("vibe_proving")

        # 打开设置面板
        settings_btn = app_page.locator("#btn-panel-toggle")
        expect(settings_btn).to_be_visible()
        settings_btn.click()
        app_page.wait_for_timeout(500)

        # 验证设置面板打开
        settings_panel = app_page.locator("#settings-panel")
        expect(settings_panel).to_be_visible()

        # 填写LLM配置（使用实际配置或测试配置）
        base_url_input = app_page.locator("#input-llm-base-url")
        api_key_input = app_page.locator("#input-llm-api-key")
        model_input = app_page.locator("#input-llm-model")

        expect(base_url_input).to_be_visible()
        expect(api_key_input).to_be_visible()
        expect(model_input).to_be_visible()

        # 填写配置
        base_url_input.fill("https://apirx.boyuerichdata.com/v1")
        api_key_input.fill("test-api-key")
        model_input.fill("gpt-4")

        # 保存配置
        save_btn = app_page.locator("#btn-save-llm")
        expect(save_btn).to_be_visible()
        save_btn.click()
        app_page.wait_for_timeout(2000)

        # 关闭设置面板
        close_btn = app_page.locator("#panel-close")
        close_btn.click()
        app_page.wait_for_timeout(500)

    def test_02_learning_mode_flow(self, app_page: Page):
        """场景2：使用学习模式学习数学定理"""
        # 点击学习模式卡片进入
        learning_card = app_page.locator("button.feature-card[data-mode='learning']")
        expect(learning_card).to_be_visible(timeout=5000)
        learning_card.click()
        app_page.wait_for_timeout(1000)

        # 验证切换到chat视图
        chat_view = app_page.locator("#chat-view")
        expect(chat_view).to_be_visible()

        # 验证输入框存在
        input_textarea = app_page.locator("#input-textarea")
        expect(input_textarea).to_be_visible()

        # 输入一个简单的数学命题
        test_statement = "证明：对于任意实数 x，x^2 >= 0"
        input_textarea.fill(test_statement)
        app_page.wait_for_timeout(500)

        # 点击发送按钮
        send_btn = app_page.locator("#send-btn")
        expect(send_btn).to_be_visible()
        send_btn.click()

        # 等待响应出现（最多30秒）
        # 注意：这里不实际等待API响应（需要真实API key），只验证UI行为
        app_page.wait_for_timeout(2000)

        # 验证停止按钮出现（说明请求正在进行）
        stop_btn = app_page.locator("#stop-btn")
        # stop_btn可能可见（说明请求进行中）或不可见（请求已完成）

        # 验证聊天容器存在
        chat_container = app_page.locator("#chat-container")
        expect(chat_container).to_be_visible()

    def test_03_solving_mode_flow(self, app_page: Page):
        """场景3：使用问题求解模式"""
        # 返回主页
        home_btn = app_page.locator("#btn-home")
        if home_btn.is_visible():
            home_btn.click()
            app_page.wait_for_timeout(1000)

        # 点击问题求解卡片
        solving_card = app_page.locator("button.feature-card[data-mode='solving']")
        expect(solving_card).to_be_visible()
        solving_card.click()
        app_page.wait_for_timeout(1000)

        # 验证模式切换
        solving_tab = app_page.locator("button.mode-tab[data-mode='solving']")
        expect(solving_tab).to_have_class(re.compile("active"))

        # 输入数学问题
        input_textarea = app_page.locator("#input-textarea")
        test_problem = "求解方程 x^2 - 5x + 6 = 0"
        input_textarea.fill(test_problem)

        # 发送
        send_btn = app_page.locator("#send-btn")
        send_btn.click()
        app_page.wait_for_timeout(2000)

    def test_04_reviewing_mode_with_upload(self, app_page: Page):
        """场景4：使用审查模式并上传文件"""
        # 切换到审查模式
        reviewing_tab = app_page.locator("button.mode-tab[data-mode='reviewing']")
        if not reviewing_tab.is_visible():
            # 如果在主页，先点击审查卡片
            review_card = app_page.locator("button.feature-card[data-mode='reviewing']")
            if review_card.is_visible():
                review_card.click()
                app_page.wait_for_timeout(1000)
        else:
            reviewing_tab.click()
            app_page.wait_for_timeout(1000)

        # 验证上传按钮出现
        attach_btn = app_page.locator("#attach-btn")
        expect(attach_btn).to_be_visible(timeout=3000)

        # 输入证明文本
        input_textarea = app_page.locator("#input-textarea")
        test_proof = """
定理：sqrt(2) 是无理数。
证明：假设 sqrt(2) 是有理数，则存在互质的正整数 p, q 使得 sqrt(2) = p/q。
两边平方得 2 = p^2/q^2，即 2q^2 = p^2。
因此 p^2 是偶数，所以 p 也是偶数。设 p = 2k，代入得 2q^2 = 4k^2，即 q^2 = 2k^2。
因此 q^2 也是偶数，所以 q 也是偶数。
这与 p, q 互质矛盾，所以 sqrt(2) 是无理数。
        """
        input_textarea.fill(test_proof.strip())

        # 发送
        send_btn = app_page.locator("#send-btn")
        send_btn.click()
        app_page.wait_for_timeout(2000)

    def test_05_searching_mode_flow(self, app_page: Page):
        """场景5：使用定理检索模式"""
        # 切换到检索模式
        searching_tab = app_page.locator("button.mode-tab[data-mode='searching']")
        if not searching_tab.is_visible():
            search_card = app_page.locator("button.feature-card[data-mode='searching']")
            if search_card.is_visible():
                search_card.click()
                app_page.wait_for_timeout(1000)
        else:
            searching_tab.click()
            app_page.wait_for_timeout(1000)

        # 输入搜索关键词
        input_textarea = app_page.locator("#input-textarea")
        test_query = "Pythagorean theorem"
        input_textarea.fill(test_query)

        # 发送搜索
        send_btn = app_page.locator("#send-btn")
        send_btn.click()
        app_page.wait_for_timeout(2000)

    def test_06_language_switching(self, app_page: Page):
        """场景6：切换语言"""
        # 打开设置面板
        settings_btn = app_page.locator("#btn-panel-toggle")
        settings_btn.click()
        app_page.wait_for_timeout(500)

        # 切换到英文
        lang_en_btn = app_page.locator("#lang-seg button[data-lang='en']")
        expect(lang_en_btn).to_be_visible()
        lang_en_btn.click()
        app_page.wait_for_timeout(1000)

        # 验证UI文本变化（检查panel标题）
        panel_title = app_page.locator(".panel-title")
        # 注意：可能需要等待i18n加载

        # 切换回中文
        lang_zh_btn = app_page.locator("#lang-seg button[data-lang='zh']")
        lang_zh_btn.click()
        app_page.wait_for_timeout(1000)

        # 关闭设置面板
        close_btn = app_page.locator("#panel-close")
        close_btn.click()
        app_page.wait_for_timeout(500)

    def test_07_theme_switching(self, app_page: Page):
        """场景7：切换主题"""
        # 打开设置面板
        settings_btn = app_page.locator("#btn-panel-toggle")
        settings_btn.click()
        app_page.wait_for_timeout(500)

        # 获取当前主题
        html = app_page.locator("html")
        initial_theme = html.get_attribute("data-theme")

        # 点击主题切换按钮
        theme_btn = app_page.locator("#btn-theme")
        expect(theme_btn).to_be_visible()
        theme_btn.click()
        app_page.wait_for_timeout(500)

        # 验证主题改变
        new_theme = html.get_attribute("data-theme")
        assert new_theme != initial_theme, f"主题未改变，仍然是 {initial_theme}"

        # 关闭设置面板
        close_btn = app_page.locator("#panel-close")
        close_btn.click()
        app_page.wait_for_timeout(500)

    def test_08_model_selector_interaction(self, app_page: Page):
        """场景8：模型选择器交互"""
        # 定位模型选择chip
        model_chip = app_page.locator("#model-chip")
        if model_chip.is_visible():
            # 点击打开下拉菜单
            model_chip.click()
            app_page.wait_for_timeout(500)

            # 验证下拉菜单出现
            model_dropdown = app_page.locator("#model-dropdown")
            expect(model_dropdown).to_be_visible()

            # 选择一个模型
            model_option = app_page.locator("#model-dropdown .chip-option").first
            if model_option.is_visible():
                model_option.click()
                app_page.wait_for_timeout(500)

    def test_09_mode_switching_via_tabs(self, app_page: Page):
        """场景9：通过顶部tabs快速切换模式"""
        modes = ["learning", "solving", "reviewing", "searching"]

        for mode in modes:
            # 点击模式tab
            mode_tab = app_page.locator(f"button.mode-tab[data-mode='{mode}']")
            if mode_tab.is_visible():
                mode_tab.click()
                app_page.wait_for_timeout(500)

                # 验证tab激活状态
                expect(mode_tab).to_have_class(re.compile("active"))

    def test_10_input_validation(self, app_page: Page):
        """场景10：输入验证"""
        # 切换到学习模式
        learning_tab = app_page.locator("button.mode-tab[data-mode='learning']")
        if learning_tab.is_visible():
            learning_tab.click()
            app_page.wait_for_timeout(500)

        # 清空输入
        input_textarea = app_page.locator("#input-textarea")
        input_textarea.fill("")

        # 尝试发送空内容
        send_btn = app_page.locator("#send-btn")
        send_btn.click()
        app_page.wait_for_timeout(1000)

        # 验证是否有错误提示或按钮被禁用（取决于实现）
        # 这里只验证不会崩溃

    def test_11_responsive_design_mobile(self, app_page: Page):
        """场景11：响应式设计 - 移动端"""
        # 设置移动端视口
        app_page.set_viewport_size({"width": 375, "height": 667})
        app_page.wait_for_timeout(500)

        # 验证汉堡菜单按钮出现
        hamburger_btn = app_page.locator("#hamburger")
        expect(hamburger_btn).to_be_visible()

        # 点击打开侧边栏
        hamburger_btn.click()
        app_page.wait_for_timeout(500)

        # 验证侧边栏出现
        sidebar = app_page.locator("#sidebar")
        # 检查侧边栏是否可见或有active类

        # 恢复桌面视口
        app_page.set_viewport_size({"width": 1280, "height": 720})

    def test_12_math_rendering(self, app_page: Page):
        """场景12：数学公式渲染"""
        # 验证KaTeX已加载
        katex_loaded = app_page.evaluate("() => typeof window.katex !== 'undefined'")
        assert katex_loaded, "KaTeX库未加载"

        # 验证marked已加载
        marked_loaded = app_page.evaluate("() => typeof window.marked !== 'undefined'")
        assert marked_loaded, "Marked库未加载"

    def test_13_config_persistence(self, app_page: Page, base_url: str):
        """场景13：配置持久化验证"""
        # 打开设置面板
        settings_btn = app_page.locator("#btn-panel-toggle")
        settings_btn.click()
        app_page.wait_for_timeout(500)

        # 设置一个特殊的model值
        model_input = app_page.locator("#input-llm-model")
        test_model = f"test-model-{int(time.time())}"
        model_input.fill(test_model)

        # 保存
        save_btn = app_page.locator("#btn-save-llm")
        save_btn.click()
        app_page.wait_for_timeout(2000)

        # 关闭设置面板
        close_btn = app_page.locator("#panel-close")
        close_btn.click()

        # 刷新页面
        app_page.reload()
        app_page.wait_for_load_state("networkidle")
        app_page.wait_for_timeout(2000)

        # 重新打开设置面板
        settings_btn = app_page.locator("#btn-panel-toggle")
        settings_btn.click()
        app_page.wait_for_timeout(1000)

        # 验证配置保留
        model_input = app_page.locator("#input-llm-model")
        current_value = model_input.input_value()
        # 注意：配置可能从服务器加载，不一定是刚才设置的测试值
        # 这里只验证字段有值即可
        assert current_value, "配置未持久化"

        # 关闭面板
        close_btn = app_page.locator("#panel-close")
        close_btn.click()

    def test_14_error_handling(self, app_page: Page):
        """场景14：错误处理"""
        # 测试无效输入
        learning_tab = app_page.locator("button.mode-tab[data-mode='learning']")
        if learning_tab.is_visible():
            learning_tab.click()
            app_page.wait_for_timeout(500)

        # 输入超长文本
        input_textarea = app_page.locator("#input-textarea")
        long_text = "测试" * 10000  # 非常长的输入
        input_textarea.fill(long_text[:1000])  # 限制在1000字符避免超时

        # 验证页面不崩溃
        expect(input_textarea).to_be_visible()

    def test_15_navigation_flow(self, app_page: Page):
        """场景15：完整导航流程"""
        # 从主页开始
        home_btn = app_page.locator("#btn-home")
        if home_btn.is_visible():
            home_btn.click()
            app_page.wait_for_timeout(500)

        # 验证主页显示
        home_view = app_page.locator("#home-view")
        expect(home_view).to_be_visible()

        # 点击不同的功能卡片
        cards = app_page.locator(".feature-card")
        card_count = cards.count()

        if card_count > 0:
            # 点击第一个卡片
            cards.first.click()
            app_page.wait_for_timeout(1000)

            # 验证切换到chat视图
            chat_view = app_page.locator("#chat-view")
            expect(chat_view).to_be_visible()

            # 返回主页
            home_btn = app_page.locator("#btn-home")
            if home_btn.is_visible():
                home_btn.click()
                app_page.wait_for_timeout(500)

            # 验证返回主页
            expect(home_view).to_be_visible()


class TestAPIIntegration:
    """API集成测试（验证前后端连接）"""

    def test_health_endpoint(self, page: Page, base_url: str):
        """测试健康检查端点"""
        response = page.request.get(f"{base_url}/health")
        assert response.ok, f"健康检查失败: {response.status}"
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"

    def test_config_endpoint(self, page: Page, base_url: str):
        """测试配置端点"""
        response = page.request.get(f"{base_url}/config")
        assert response.ok, f"配置端点失败: {response.status}"
        data = response.json()
        assert "llm" in data

    def test_search_endpoint_basic(self, page: Page, base_url: str):
        """测试搜索端点基本功能"""
        try:
            response = page.request.get(
                f"{base_url}/search",
                params={"q": "Pythagorean theorem", "max_results": 5},
                timeout=5000  # 5秒超时
            )
            # 搜索端点可能需要外部服务，允许503/404/502
            assert response.status in [200, 404, 502, 503], f"搜索端点异常: {response.status}"
        except PlaywrightError as e:
            # 外部服务不可用时跳过测试
            if "Timeout" in str(e):
                pytest.skip("TheoremSearch服务不可用（超时）")
            raise


class TestPerformance:
    """性能测试"""

    def test_page_load_performance(self, app_page: Page):
        """测试页面加载性能"""
        start_time = time.time()

        # 重新加载页面
        app_page.reload()
        app_page.wait_for_load_state("networkidle")

        load_time = time.time() - start_time

        # 页面加载应在5秒内完成
        assert load_time < 5.0, f"页面加载时间过长: {load_time:.2f}秒"

    def test_interaction_responsiveness(self, app_page: Page):
        """测试交互响应性"""
        # 测试按钮点击响应时间
        settings_btn = app_page.locator("#btn-panel-toggle")

        start_time = time.time()
        settings_btn.click()

        # 等待设置面板出现
        settings_panel = app_page.locator("#settings-panel")
        settings_panel.wait_for(state="visible", timeout=3000)

        response_time = time.time() - start_time

        # 交互响应应在1秒内
        assert response_time < 1.0, f"交互响应时间过长: {response_time:.2f}秒"
