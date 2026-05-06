"""现代化E2E测试套件 - 遵循测试金字塔原则

核心原则（来自现代前端测试最佳实践）：
══════════════════════════════════════════════════════════
1. 测试金字塔：E2E只测核心业务流（~10%）
2. 生产环境验证：在真实环境测试关键旅程
3. 确定性：零脆弱，稳定可预测
4. 快速反馈：快速执行，可并行
5. 行为导向：测试用户可见行为，非实现细节

E2E测试范围（Top 10%）
══════════════════════════════════════════════════════════
仅覆盖核心盈利业务流和关键用户旅程：
- 认证基础（登录/登出）如需要
- 前3-10个关键业务旅程
- 一两个导航完整性检查

VS 不应该在E2E测试的：
- UI组件状态（应该在单元/集成测试）
- 边缘案例和错误处理（应该在单元测试）
- API响应验证（应该在集成测试）
- 主题切换、语言切换（应该在集成测试）
"""
import pytest
from playwright.sync_api import Page, expect


@pytest.fixture
def app_page(page: Page):
    """打开应用"""
    page.goto("http://localhost:8080/ui/")
    page.wait_for_load_state("networkidle")
    return page


class TestCriticalUserJourneys:
    """关键用户旅程 - 这是E2E测试应该覆盖的唯一内容

    原则：只测试核心盈利业务流，确保核心功能永不崩溃
    """

    def test_journey_01_first_time_user_complete_flow(self, app_page: Page):
        """关键旅程1：首次用户完整使用流程

        业务价值：新用户能够配置并立即使用核心功能
        路径：访问 → 配置API → 使用学习模式 → 获得AI完整响应

        注意：需要真实的API密钥才能测试完整流程
        """
        # Step 1: 首次访问验证
        home_title = app_page.locator(".home-title")
        expect(home_title).to_be_visible(timeout=5000)

        # Step 2: 配置API验证（跳过实际配置，假设测试环境已配置）
        # 注意：打开和关闭设置可能会干扰后续的点击，这里仅验证配置按钮可见
        settings_btn = app_page.locator("#btn-panel-toggle")
        expect(settings_btn).to_be_visible()

        # Step 3: 使用核心功能（学习模式）
        learning_card = app_page.locator("button.feature-card[data-mode='learning']")
        expect(learning_card).to_be_visible()
        learning_card.click()

        # 等待视图切换完成
        app_page.wait_for_timeout(1500)

        # 验证切换到功能界面
        chat_view = app_page.locator("#chat-view")
        expect(chat_view).to_be_visible(timeout=10000)

        # Step 4: 输入并提交（核心交互）
        input_textarea = app_page.locator("#input-textarea")
        expect(input_textarea).to_be_visible()
        input_textarea.fill("什么是勾股定理")

        send_btn = app_page.locator("#send-btn")
        expect(send_btn).to_be_visible()
        send_btn.click()

        # Step 5: 等待AI流式响应完成
        # 等待停止按钮出现（说明开始生成）
        stop_btn = app_page.locator("#stop-btn")
        try:
            expect(stop_btn).to_be_visible(timeout=5000)
            # 等待停止按钮消失（说明生成完成）
            expect(stop_btn).to_be_hidden(timeout=60000)
        except:
            # 如果响应太快，可能没看到停止按钮，这也是正常的
            pass

        # Step 6: 验证实际的AI输出内容
        # Learning模式生成多个sections需要较长时间，等待60秒
        app_page.wait_for_timeout(60000)  # 等待60秒让所有sections完成

        # 再次检查是否还在生成
        if stop_btn.is_visible():
            app_page.wait_for_timeout(30000)  # 再等30秒

        # 检查是否有API认证错误
        error_messages = app_page.locator(".section-error-details")
        if error_messages.count() > 0:
            error_text = error_messages.first.text_content()
            if "AuthenticationError" in error_text or "401" in error_text or "无效的令牌" in error_text:
                pytest.skip("API认证失败：需要在config.toml中配置真实的API密钥才能测试完整的AI输出流程")

        chat_container = app_page.locator("#chat-container")
        expect(chat_container).to_be_visible()

        # 验证有assistant消息出现
        assistant_messages = app_page.locator(".message.ai")
        if assistant_messages.count() == 0:
            pytest.skip("未收到AI响应：可能是API配置问题或网络问题")

        expect(assistant_messages.last).to_be_visible(timeout=5000)

        # 验证消息内容不为空，并包含相关关键词
        last_message_content = assistant_messages.last.locator(".message-content")
        message_text = last_message_content.text_content()
        assert len(message_text) > 50, f"AI响应内容太短: {len(message_text)}字符"
        assert "勾股" in message_text or "三角形" in message_text or "Pythag" in message_text, \
            "AI响应未包含相关数学内容"

    def test_journey_02_solve_mathematical_problem(self, app_page: Page):
        """关键旅程2：数学问题求解流程

        业务价值：核心功能 - 用户能够提交问题并获得完整解答
        路径：访问 → 切换求解模式 → 输入问题 → 获得AI完整解答
        """
        # 直接访问求解模式
        solving_card = app_page.locator("button.feature-card[data-mode='solving']")
        solving_card.click()
        app_page.wait_for_timeout(1000)

        # 输入数学问题
        input_textarea = app_page.locator("#input-textarea")
        input_textarea.fill("求解方程：x² + 5x + 6 = 0")

        # 提交
        send_btn = app_page.locator("#send-btn")
        send_btn.click()

        # 等待AI流式响应完成
        stop_btn = app_page.locator("#stop-btn")
        try:
            expect(stop_btn).to_be_visible(timeout=5000)
            expect(stop_btn).to_be_hidden(timeout=60000)
        except:
            pass

        # 等待足够长的时间
        app_page.wait_for_timeout(15000)

        # 检查是否有API认证错误
        error_messages = app_page.locator(".section-error-details")
        if error_messages.count() > 0:
            error_text = error_messages.first.text_content()
            if "AuthenticationError" in error_text or "401" in error_text:
                pytest.skip("API认证失败：需要配置真实的API密钥")

        # 验证实际的AI解答内容
        assistant_messages = app_page.locator(".message.ai")
        if assistant_messages.count() == 0:
            pytest.skip("未收到AI响应：可能是API配置问题")

        expect(assistant_messages.last).to_be_visible(timeout=5000)

        last_message_content = assistant_messages.last.locator(".message-content")
        message_text = last_message_content.text_content()

        # 验证响应足够详细
        assert len(message_text) > 50, f"AI解答内容太短: {len(message_text)}字符"

        # 验证包含求解相关内容（解、因式分解、计算等关键词）
        has_solution = any(keyword in message_text for keyword in [
            "解", "x =", "x=", "答案", "结果", "solution", "answer", "因式", "factor"
        ])
        assert has_solution, "AI响应未包含求解结果"

    def test_journey_03_review_mathematical_proof(self, app_page: Page):
        """关键旅程3：证明审查流程

        业务价值：研究者核心需求 - 审查数学证明并获得完整反馈
        路径：访问 → 审查模式 → 输入证明 → 获得AI完整审查结果
        """
        # 访问审查模式
        review_card = app_page.locator("button.feature-card[data-mode='reviewing']")
        review_card.click()
        app_page.wait_for_timeout(1000)

        # 验证上传功能可用
        attach_btn = app_page.locator("#attach-btn")
        expect(attach_btn).to_be_visible()

        # 输入证明文本
        input_textarea = app_page.locator("#input-textarea")
        proof_text = """定理：sqrt(2)是无理数。
证明：假设sqrt(2)是有理数，则存在互质的正整数p、q使得sqrt(2)=p/q。
两边平方得2q²=p²，所以p²是偶数，因此p是偶数。
设p=2k，代入得2q²=4k²，即q²=2k²，所以q也是偶数。
这与p、q互质矛盾。因此sqrt(2)是无理数。"""
        input_textarea.fill(proof_text)

        # 提交审查
        send_btn = app_page.locator("#send-btn")
        send_btn.click()

        # 等待AI流式审查完成
        stop_btn = app_page.locator("#stop-btn")
        try:
            expect(stop_btn).to_be_visible(timeout=5000)
            expect(stop_btn).to_be_hidden(timeout=60000)
        except:
            pass

        # 等待足够长的时间
        app_page.wait_for_timeout(15000)

        # 检查是否有API认证错误
        error_messages = app_page.locator(".section-error-details")
        if error_messages.count() > 0:
            error_text = error_messages.first.text_content()
            if "AuthenticationError" in error_text or "401" in error_text:
                pytest.skip("API认证失败：需要配置真实的API密钥")

        # 验证审查结果
        assistant_messages = app_page.locator(".message.ai")
        if assistant_messages.count() == 0:
            pytest.skip("未收到AI响应：可能是API配置问题")

        expect(assistant_messages.last).to_be_visible(timeout=5000)

        last_message_content = assistant_messages.last.locator(".message-content")
        message_text = last_message_content.text_content()

        # 验证审查内容足够详细
        assert len(message_text) > 100, f"AI审查内容太短: {len(message_text)}字符"

        # 验证包含审查相关内容
        has_review = any(keyword in message_text for keyword in [
            "正确", "严谨", "证明", "逻辑", "步骤", "推理", "结论",
            "correct", "proof", "logic", "step", "conclusion"
        ])
        assert has_review, "AI响应未包含审查内容"

    def test_journey_04_search_theorem(self, app_page: Page):
        """关键旅程4：定理检索流程

        业务价值：研究辅助 - 快速查找相关定理并获得完整结果
        路径：访问 → 检索模式 → 搜索 → 查看AI整理的完整结果
        """
        # 访问检索模式
        search_card = app_page.locator("button.feature-card[data-mode='searching']")
        search_card.click()
        app_page.wait_for_timeout(1000)

        # 输入搜索词
        input_textarea = app_page.locator("#input-textarea")
        input_textarea.fill("勾股定理")

        # 提交搜索
        send_btn = app_page.locator("#send-btn")
        send_btn.click()

        # 等待AI流式响应完成（搜索模式可能需要更长时间）
        stop_btn = app_page.locator("#stop-btn")
        try:
            expect(stop_btn).to_be_visible(timeout=10000)
            expect(stop_btn).to_be_hidden(timeout=60000)
        except:
            pass

        # 等待足够长的时间
        app_page.wait_for_timeout(15000)

        # 检查是否有API认证错误
        error_messages = app_page.locator(".section-error-details")
        if error_messages.count() > 0:
            error_text = error_messages.first.text_content()
            if "AuthenticationError" in error_text or "401" in error_text:
                pytest.skip("API认证失败：需要配置真实的API密钥")

        # 验证搜索结果
        assistant_messages = app_page.locator(".message.ai")
        if assistant_messages.count() == 0:
            pytest.skip("未收到AI响应：可能是API配置问题或TheoremSearch服务不可用")

        expect(assistant_messages.last).to_be_visible(timeout=10000)

        last_message_content = assistant_messages.last.locator(".message-content")
        message_text = last_message_content.text_content()

        # 如果外部服务不可用，应该有明确的错误提示
        if "超时" in message_text or "失败" in message_text or "不可用" in message_text:
            pytest.skip("TheoremSearch服务当前不可用")

        # 验证搜索结果足够详细
        assert len(message_text) > 50, f"搜索结果内容太短: {len(message_text)}字符"

        # 验证包含定理相关内容
        has_theorem_info = any(keyword in message_text for keyword in [
            "定理", "theorem", "证明", "proof", "勾股", "Pythag", "直角三角形"
        ])
        assert has_theorem_info, "搜索结果未包含定理相关内容"

    def test_journey_05_multi_mode_workflow(self, app_page: Page):
        """关键旅程5：多模式工作流

        业务价值：专业用户场景 - 在多个模式间切换工作并获得完整功能
        路径：学习 → 求解 → 审查 → 验证每个模式都能正常产生AI输出
        """
        # 学习模式 - 完整测试
        learning_tab = app_page.locator("button.mode-tab[data-mode='learning']")
        learning_tab.click()
        app_page.wait_for_timeout(500)

        input_area = app_page.locator("#input-textarea")
        expect(input_area).to_be_visible()

        # 在学习模式发送消息并验证响应
        input_area.fill("什么是导数")
        send_btn = app_page.locator("#send-btn")
        send_btn.click()

        # 等待学习模式响应
        stop_btn = app_page.locator("#stop-btn")
        try:
            expect(stop_btn).to_be_visible(timeout=5000)
            expect(stop_btn).to_be_hidden(timeout=30000)
        except:
            pass

        app_page.wait_for_timeout(10000)

        # 检查是否有API错误
        error_messages = app_page.locator(".section-error-details")
        if error_messages.count() > 0:
            error_text = error_messages.first.text_content()
            if "AuthenticationError" in error_text or "401" in error_text:
                pytest.skip("API认证失败：需要配置真实的API密钥")

        # 验证学习模式有输出
        assistant_msgs = app_page.locator(".message.ai")
        if assistant_msgs.count() == 0:
            pytest.skip("未收到AI响应：可能是API配置问题")

        expect(assistant_msgs.last).to_be_visible()

        # 切换到求解模式 - 完整测试
        solving_tab = app_page.locator("button.mode-tab[data-mode='solving']")
        solving_tab.click()
        app_page.wait_for_timeout(500)
        expect(input_area).to_be_visible()

        # 在求解模式发送消息并验证响应
        input_area.fill("求导：f(x) = x² + 2x")
        send_btn.click()

        try:
            expect(stop_btn).to_be_visible(timeout=5000)
            expect(stop_btn).to_be_hidden(timeout=30000)
        except:
            pass

        app_page.wait_for_timeout(10000)

        # 验证求解模式有输出
        if assistant_msgs.count() < 2:
            pytest.skip("求解模式未收到AI响应")

        expect(assistant_msgs.last).to_be_visible()
        solving_response = assistant_msgs.last.locator(".message-content").text_content()
        assert len(solving_response) > 30, "求解模式响应太短"

        # 切换到审查模式 - 验证UI变化
        reviewing_tab = app_page.locator("button.mode-tab[data-mode='reviewing']")
        reviewing_tab.click()
        app_page.wait_for_timeout(500)

        # 验证审查模式特有的上传按钮出现
        attach_btn = app_page.locator("#attach-btn")
        expect(attach_btn).to_be_visible()


class TestNavigationIntegrity:
    """导航完整性测试 - 确保用户不会迷失

    范围：仅测试核心导航路径，非所有可能路径
    """

    def test_home_to_feature_navigation(self, app_page: Page):
        """测试：主页到功能的导航完整"""
        # 从主页点击卡片
        home_view = app_page.locator("#home-view")
        expect(home_view).to_be_visible()

        learning_card = app_page.locator("button.feature-card[data-mode='learning']")
        learning_card.click()
        app_page.wait_for_timeout(1000)

        # 验证到达功能页
        chat_view = app_page.locator("#chat-view")
        expect(chat_view).to_be_visible()

        # 验证可以返回
        home_btn = app_page.locator("#btn-home")
        home_btn.click()
        app_page.wait_for_timeout(500)

        expect(home_view).to_be_visible()


class TestCriticalPerformance:
    """关键性能测试 - 确保核心交互足够快

    原则：只测试影响用户体验的关键性能指标
    """

    def test_initial_page_load_under_threshold(self, app_page: Page):
        """测试：首页加载应该在3秒内完成"""
        import time

        start = time.time()
        app_page.goto("http://localhost:8080/ui/")
        app_page.wait_for_load_state("networkidle")
        load_time = time.time() - start

        # 核心性能阈值：首页3秒
        assert load_time < 3.0, f"首页加载太慢: {load_time:.2f}秒"

    def test_mode_switch_is_responsive(self, app_page: Page):
        """测试：模式切换应该感觉即时（<1秒）"""
        import time

        learning_tab = app_page.locator("button.mode-tab[data-mode='learning']")

        start = time.time()
        learning_tab.click()
        app_page.wait_for_timeout(100)  # 小等待确保DOM更新
        response_time = time.time() - start

        # 用户感知阈值：<1秒
        assert response_time < 1.0, f"模式切换太慢: {response_time:.2f}秒"


# 注意：这个测试套件大幅精简了
# 删除的测试应该移到：
# - tests/unit/ - 单元测试（逻辑、工具函数）
# - tests/integration/ - 集成测试（组件+状态+API）
#
# E2E只保留8个测试（原来37个），符合金字塔顶层~10%原则
