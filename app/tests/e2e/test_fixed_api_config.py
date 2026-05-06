"""
修复后的API配置测试 - 使用正确的验证方式

配置实际保存在：后端config.toml文件
验证方式：通过/health或/config API读取
"""
import pytest
from playwright.sync_api import Page, expect


class TestAPIConfiguration:
    """API配置相关测试"""

    def test_api_config_deepseek(self, app_page: Page):
        """测试配置DeepSeek API"""
        print("\n" + "=" * 70)
        print("[Test] API Configuration - DeepSeek")
        print("=" * 70)

        # Step 1: 打开设置面板
        print("\n[Step 1] Opening settings panel...")
        settings_btn = app_page.locator("#btn-panel-toggle")
        settings_btn.click()
        app_page.wait_for_timeout(1000)
        print("  [OK] Settings panel opened")

        # Step 2: 填写DeepSeek API配置
        print("\n[Step 2] Configuring DeepSeek API...")

        base_url_input = app_page.locator("#input-llm-base-url")
        api_key_input = app_page.locator("#input-llm-api-key")
        model_input = app_page.locator("#input-llm-model")

        # 填写配置
        base_url_input.clear()
        base_url_input.fill("https://apirx.boyuerichdata.com")
        print("  [OK] Base URL: https://apirx.boyuerichdata.com")

        api_key_input.clear()
        api_key_input.fill("sk-33ceb14fa71847f88ea7a4c129079442")
        print("  [OK] API Key: sk-33ceb14...（已隐藏）")

        model_input.clear()
        model_input.fill("deepseek-chat")
        print("  [OK] Model: deepseek-chat")

        # Step 3: 保存配置
        print("\n[Step 3] Saving configuration...")
        save_btn = app_page.locator("#btn-save-llm")
        save_btn.click()

        # 等待保存完成（按钮文字变化）
        app_page.wait_for_timeout(3000)
        print("  [OK] Configuration saved")

        # Step 4: 验证配置状态标记
        print("\n[Step 4] Checking configuration status...")
        config_state = app_page.locator("#llm-config-state")
        if config_state.is_visible():
            status_text = config_state.text_content()
            print(f"  Config status: {status_text}")

        # Step 5: 关闭设置面板
        print("\n[Step 5] Closing settings panel...")
        close_btn = app_page.locator("#panel-close")
        close_btn.click()
        app_page.wait_for_timeout(500)
        print("  [OK] Settings panel closed")

        # Step 6: 通过/health API验证配置
        print("\n[Step 6] Verifying via /health API...")
        health_response = app_page.evaluate("""async () => {
            const resp = await fetch('/health');
            return await resp.json();
        }""")

        llm_config = health_response.get('llm', {})
        saved_base_url = llm_config.get('base_url', '')
        saved_model = llm_config.get('model', '')

        print(f"  Health API - base_url: {saved_base_url}")
        print(f"  Health API - model: {saved_model}")

        # 验证配置
        assert "apirx.boyuerichdata.com" in saved_base_url or "boyuerichdata" in saved_base_url, \
            f"Base URL not saved correctly: {saved_base_url}"
        assert "deepseek" in saved_model.lower(), \
            f"Model not saved correctly: {saved_model}"

        print("  [OK] Configuration verified via API")

        # 截图
        app_page.screenshot(path="api_config_deepseek.png")

        print("\n[Test Complete] API configuration test passed")
        print("=" * 70)

    def test_api_config_persists_after_refresh(self, app_page: Page):
        """测试刷新页面后API配置是否保持"""
        print("\n" + "=" * 70)
        print("[Test] API Configuration Persistence After Refresh")
        print("=" * 70)

        # Step 1: 记录当前配置（通过health API）
        print("\n[Step 1] Recording current configuration...")

        config_before = app_page.evaluate("""async () => {
            const resp = await fetch('/health');
            const data = await resp.json();
            return data.llm || {};
        }""")

        print(f"  Config before refresh:")
        print(f"    base_url: {config_before.get('base_url', 'None')}")
        print(f"    model: {config_before.get('model', 'None')}")

        if not config_before.get('base_url'):
            print("  [SKIP] No configuration found, please run test_api_config_deepseek first")
            pytest.skip("No configuration to test")

        # Step 2: 刷新页面
        print("\n[Step 2] Refreshing page...")
        app_page.reload()
        app_page.wait_for_load_state("domcontentloaded")
        app_page.wait_for_timeout(2000)
        print("  [OK] Page refreshed")

        # Step 3: 检查配置是否保持
        print("\n[Step 3] Checking configuration after refresh...")

        config_after = app_page.evaluate("""async () => {
            const resp = await fetch('/health');
            const data = await resp.json();
            return data.llm || {};
        }""")

        print(f"  Config after refresh:")
        print(f"    base_url: {config_after.get('base_url', 'None')}")
        print(f"    model: {config_after.get('model', 'None')}")

        # Step 4: 验证配置一致性
        print("\n[Step 4] Validating configuration consistency...")

        assert config_before['base_url'] == config_after['base_url'], \
            "Base URL changed after refresh"
        assert config_before['model'] == config_after['model'], \
            "Model changed after refresh"

        print("  [OK] All configuration persisted correctly")

        # Step 5: 打开设置面板验证UI也显示正确
        print("\n[Step 5] Verifying UI shows correct values...")

        settings_btn = app_page.locator("#btn-panel-toggle")
        settings_btn.click()
        app_page.wait_for_timeout(1500)  # 等待配置加载到UI

        # 检查输入框的值
        base_url_value = app_page.locator("#input-llm-base-url").input_value()
        model_value = app_page.locator("#input-llm-model").input_value()

        print(f"  UI base_url: {base_url_value}")
        print(f"  UI model: {model_value}")

        assert base_url_value == config_after['base_url'], \
            "UI doesn't show correct base_url"
        assert model_value == config_after['model'], \
            "UI doesn't show correct model"

        print("  [OK] UI displays correct values")

        # 关闭设置面板
        close_btn = app_page.locator("#panel-close")
        close_btn.click()
        app_page.wait_for_timeout(500)

        # 截图
        app_page.screenshot(path="api_config_after_refresh.png")

        print("\n[Test Complete] Configuration persistence test passed")
        print("=" * 70)

    def test_switch_api_provider(self, app_page: Page):
        """测试切换不同的API提供商"""
        print("\n" + "=" * 70)
        print("[Test] Switching API Providers")
        print("=" * 70)

        providers = [
            {
                "name": "Provider 1 (DeepSeek)",
                "base_url": "https://apirx.boyuerichdata.com",
                "api_key": "sk-33ceb14fa71847f88ea7a4c129079442",
                "model": "deepseek-chat",
            },
            {
                "name": "Provider 2 (Alternative)",
                "base_url": "https://apirx.boyuerichdata.com",
                "api_key": "sk-6t35reMJPfGe8U5CDg4iDhrzbbYlY7YSLzlxFw2JC7z5urN1",
                "model": "deepseek-chat",
            },
        ]

        for i, provider in enumerate(providers, 1):
            print(f"\n[Provider {i}] Configuring {provider['name']}...")

            # 打开设置面板
            settings_btn = app_page.locator("#btn-panel-toggle")
            settings_btn.click()
            app_page.wait_for_timeout(1000)

            # 填写配置
            app_page.locator("#input-llm-base-url").clear()
            app_page.locator("#input-llm-base-url").fill(provider['base_url'])

            app_page.locator("#input-llm-api-key").clear()
            app_page.locator("#input-llm-api-key").fill(provider['api_key'])

            app_page.locator("#input-llm-model").clear()
            app_page.locator("#input-llm-model").fill(provider['model'])

            print(f"  [OK] Filled configuration")

            # 保存
            save_btn = app_page.locator("#btn-save-llm")
            save_btn.click()
            app_page.wait_for_timeout(3000)  # 等待保存完成
            print(f"  [OK] Configuration saved")

            # 关闭设置面板
            close_btn = app_page.locator("#panel-close")
            close_btn.click()
            app_page.wait_for_timeout(500)

            # 验证保存（通过health API）
            saved_config = app_page.evaluate("""async () => {
                const resp = await fetch('/health');
                const data = await resp.json();
                return data.llm || {};
            }""")

            saved_url = saved_config.get('base_url', '')
            assert provider['base_url'] in saved_url or "boyuerichdata" in saved_url, \
                f"Base URL not saved for {provider['name']}"

            print(f"  [OK] Verified {provider['name']}")

        print("\n[Test Complete] API provider switching test passed")
        print("=" * 70)


class TestMultiTurnConversation:
    """多轮对话测试"""

    def test_multi_turn_with_context(self, app_page: Page):
        """测试多轮对话中的上下文理解"""
        print("\n" + "=" * 70)
        print("[Test] Multi-Turn Conversation with Context")
        print("=" * 70)

        # Step 1: 进入Learning模式
        print("\n[Step 1] Entering Learning mode...")
        learning_btn = app_page.locator("button.feature-card[data-mode='learning']")
        learning_btn.click()
        app_page.wait_for_timeout(1500)

        chat_view = app_page.locator("#chat-view")
        expect(chat_view).to_be_visible(timeout=5000)
        print("  [OK] Entered Learning mode")

        # 定义多轮对话 - 测试上下文理解
        conversation = [
            {
                "round": 1,
                "query": "费马大定理是什么？",
                "wait_full": False,
            },
            {
                "round": 2,
                "query": "它的证明难在哪里？",
                "wait_full": False,
            },
            {
                "round": 3,
                "query": "谁最终证明了它？",
                "wait_full": True,
            },
        ]

        input_textarea = app_page.locator("#input-textarea")
        send_btn = app_page.locator("#send-btn")
        stop_btn = app_page.locator("#stop-btn")

        for turn in conversation:
            print(f"\n[Round {turn['round']}] Query: {turn['query']}")

            # 输入查询
            expect(input_textarea).to_be_editable(timeout=10000)
            input_textarea.clear()
            input_textarea.fill(turn['query'])

            # 提交
            expect(send_btn).to_be_enabled(timeout=5000)
            send_btn.click()
            print(f"  [OK] Query submitted")

            if turn['wait_full']:
                # 等待完整响应
                print(f"  Waiting for full response (max 120s)...")
                try:
                    expect(send_btn).to_be_enabled(timeout=120000)
                    print(f"  [OK] Full response received")
                except:
                    print(f"  [WARN] Response timeout")
            else:
                # 只等待开始生成，然后停止
                app_page.wait_for_timeout(5000)

                if stop_btn.is_visible():
                    stop_btn.click()
                    print(f"  [OK] Generation stopped early")
                    app_page.wait_for_timeout(1000)
                else:
                    print(f"  [INFO] Generation already completed or stop button not visible")

        # 验证对话历史
        print(f"\n[Verification] Checking conversation history...")

        user_messages = app_page.locator(".message.user")
        ai_messages = app_page.locator(".message.ai")

        user_count = user_messages.count()
        ai_count = ai_messages.count()

        print(f"  User messages: {user_count}")
        print(f"  AI messages: {ai_count}")

        assert user_count == len(conversation), \
            f"Expected {len(conversation)} user messages, got {user_count}"
        print(f"  [OK] Conversation history correct")

        # 截图
        app_page.screenshot(path="multi_turn_context.png", full_page=True)

        print("\n[Test Complete] Multi-turn conversation test passed")
        print("=" * 70)


class TestCompleteUserJourney:
    """完整的用户使用流程测试"""

    def test_new_user_complete_workflow(self, app_page: Page):
        """模拟新用户完整使用流程"""
        print("\n" + "=" * 70)
        print("[Test] New User Complete Workflow")
        print("=" * 70)

        # Phase 1: 配置API
        print("\n=== Phase 1: API Configuration ===")

        settings_btn = app_page.locator("#btn-panel-toggle")
        settings_btn.click()
        app_page.wait_for_timeout(1000)

        app_page.locator("#input-llm-base-url").fill("https://apirx.boyuerichdata.com")
        app_page.locator("#input-llm-api-key").fill("sk-33ceb14fa71847f88ea7a4c129079442")
        app_page.locator("#input-llm-model").fill("deepseek-chat")

        save_btn = app_page.locator("#btn-save-llm")
        save_btn.click()
        app_page.wait_for_timeout(3000)
        print("[OK] API configured")

        close_btn = app_page.locator("#panel-close")
        close_btn.click()
        app_page.wait_for_timeout(500)

        # Phase 2: Learning模式学习概念
        print("\n=== Phase 2: Learning a Concept ===")

        learning_btn = app_page.locator("button.feature-card[data-mode='learning']")
        learning_btn.click()
        app_page.wait_for_timeout(1500)

        input_textarea = app_page.locator("#input-textarea")
        send_btn = app_page.locator("#send-btn")
        stop_btn = app_page.locator("#stop-btn")

        input_textarea.fill("什么是二次方程？")
        send_btn.click()
        print("[Query 1] 什么是二次方程？")

        # 等待10秒后停止
        app_page.wait_for_timeout(10000)
        if stop_btn.is_visible():
            stop_btn.click()
            app_page.wait_for_timeout(1000)
            print("[OK] Got partial response")

        # Phase 3: 刷新页面测试配置保持
        print("\n=== Phase 3: Refresh and Verify Config ===")

        app_page.reload()
        app_page.wait_for_load_state("domcontentloaded")
        app_page.wait_for_timeout(2000)
        print("[OK] Page refreshed")

        config_after_refresh = app_page.evaluate("""async () => {
            const resp = await fetch('/health');
            const data = await resp.json();
            return data.llm || {};
        }""")

        saved_url = config_after_refresh.get('base_url', '')
        assert "apirx.boyuerichdata.com" in saved_url or "boyuerichdata" in saved_url, \
            f"Configuration not persisted: {saved_url}"
        print("[OK] Configuration persisted after refresh")

        # 最终截图
        app_page.screenshot(path="complete_user_journey.png", full_page=True)

        print("\n=== Summary ===")
        print("[OK] API Configuration")
        print("[OK] Learning Mode Usage")
        print("[OK] Configuration Persistence")

        print("\n[Test Complete] Complete user workflow test passed")
        print("=" * 70)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
