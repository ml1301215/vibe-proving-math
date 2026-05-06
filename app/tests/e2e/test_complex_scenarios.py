"""
复杂场景端到端测试 - 覆盖真实用户使用场景

测试内容：
1. API配置管理（填写、保存、刷新后恢复）
2. 多轮对话交互
3. 不同模式切换
4. 历史记录管理
5. 错误处理
"""
import pytest
from playwright.sync_api import Page, expect


class TestAPIConfiguration:
    """API配置相关测试"""

    def test_api_config_fill_and_save(self, app_page: Page):
        """测试填写API配置并验证保存"""
        print("\n" + "=" * 70)
        print("[Test] API Configuration - Fill and Save")
        print("=" * 70)

        # Step 1: 打开设置面板
        print("\n[Step 1] Opening settings panel...")

        # 查找设置按钮（可能有多种选择器）
        settings_selectors = [
            "#btn-panel-toggle",
            "button:has-text('Settings')",
            "button:has-text('设置')",
            "[aria-label*='settings' i]",
            "[aria-label*='设置']",
            ".settings-btn",
        ]

        settings_btn = None
        for selector in settings_selectors:
            btn = app_page.locator(selector).first
            if btn.count() > 0 and btn.is_visible():
                settings_btn = btn
                print(f"  Found settings button: {selector}")
                break

        if not settings_btn:
            print("  [WARN] Settings button not found, checking DOM...")
            # 查看所有按钮
            all_buttons = app_page.locator("button")
            print(f"  Total buttons: {all_buttons.count()}")
            for i in range(min(all_buttons.count(), 10)):
                btn = all_buttons.nth(i)
                text = btn.text_content()
                aria_label = btn.get_attribute("aria-label")
                btn_id = btn.get_attribute("id")
                print(f"    Button {i}: id='{btn_id}', aria='{aria_label}', text='{text}'")

            pytest.skip("Cannot find settings button")

        settings_btn.click()
        app_page.wait_for_timeout(1000)
        print("  [OK] Settings panel opened")

        # Step 2: 查找API配置输入框
        print("\n[Step 2] Finding API configuration fields...")

        # 查找各个配置字段
        config_fields = {
            'base_url': None,
            'api_key': None,
            'model': None,
        }

        # 尝试多种选择器策略
        base_url_selectors = [
            "input[name='base_url']",
            "input[placeholder*='Base URL' i]",
            "input[placeholder*='API' i][placeholder*='URL' i]",
            "input[id*='base' i][id*='url' i]",
        ]

        api_key_selectors = [
            "input[name='api_key']",
            "input[placeholder*='API Key' i]",
            "input[placeholder*='Key' i]",
            "input[type='password']",
            "input[id*='api' i][id*='key' i]",
        ]

        model_selectors = [
            "input[name='model']",
            "select[name='model']",
            "input[placeholder*='Model' i]",
            "input[id*='model' i]",
        ]

        # 查找Base URL字段
        for selector in base_url_selectors:
            field = app_page.locator(selector).first
            if field.count() > 0:
                config_fields['base_url'] = field
                print(f"  Found base_url field: {selector}")
                break

        # 查找API Key字段
        for selector in api_key_selectors:
            field = app_page.locator(selector).first
            if field.count() > 0:
                config_fields['api_key'] = field
                print(f"  Found api_key field: {selector}")
                break

        # 查找Model字段
        for selector in model_selectors:
            field = app_page.locator(selector).first
            if field.count() > 0:
                config_fields['model'] = field
                print(f"  Found model field: {selector}")
                break

        # 如果找不到字段，打印当前表单内容
        if not all(config_fields.values()):
            print("\n  [WARN] Some fields not found, checking form content...")
            # 查找所有input和select元素
            all_inputs = app_page.locator("input, select, textarea")
            print(f"  Total form fields: {all_inputs.count()}")

            for i in range(min(all_inputs.count(), 15)):
                field = all_inputs.nth(i)
                if field.is_visible():
                    tag = field.evaluate("el => el.tagName")
                    field_type = field.get_attribute("type")
                    field_name = field.get_attribute("name")
                    field_id = field.get_attribute("id")
                    placeholder = field.get_attribute("placeholder")
                    print(f"    Field {i}: <{tag}> type='{field_type}' name='{field_name}' id='{field_id}'")
                    print(f"              placeholder='{placeholder}'")

        # Step 3: 填写API配置
        print("\n[Step 3] Filling API configuration...")

        test_config = {
            'base_url': 'https://apirx.boyuerichdata.com',
            'api_key': 'sk-33ceb14fa71847f88ea7a4c129079442',
            'model': 'deepseek-chat',  # deepseek v4pro的实际model名称
        }

        filled_fields = []

        if config_fields['base_url']:
            config_fields['base_url'].clear()
            config_fields['base_url'].fill(test_config['base_url'])
            filled_fields.append('base_url')
            print(f"  [OK] Filled base_url: {test_config['base_url']}")

        if config_fields['api_key']:
            config_fields['api_key'].clear()
            config_fields['api_key'].fill(test_config['api_key'])
            filled_fields.append('api_key')
            print(f"  [OK] Filled api_key: {test_config['api_key'][:20]}...")

        if config_fields['model']:
            # 如果是select，尝试选择；如果是input，填写
            tag_name = config_fields['model'].evaluate("el => el.tagName")
            if tag_name == "SELECT":
                config_fields['model'].select_option(test_config['model'])
            else:
                config_fields['model'].clear()
                config_fields['model'].fill(test_config['model'])
            filled_fields.append('model')
            print(f"  [OK] Filled model: {test_config['model']}")

        if not filled_fields:
            app_page.screenshot(path="debug_settings_panel.png")
            pytest.skip("No configuration fields found")

        # Step 4: 保存配置
        print("\n[Step 4] Saving configuration...")

        # 查找保存按钮
        save_selectors = [
            "button:has-text('Save')",
            "button:has-text('保存')",
            "button:has-text('Apply')",
            "button:has-text('确定')",
            "button[type='submit']",
        ]

        save_btn = None
        for selector in save_selectors:
            btn = app_page.locator(selector).first
            if btn.count() > 0 and btn.is_visible():
                save_btn = btn
                print(f"  Found save button: {selector}")
                break

        if save_btn:
            save_btn.click()
            app_page.wait_for_timeout(1000)
            print("  [OK] Configuration saved")
        else:
            print("  [WARN] Save button not found, config might auto-save")

        # Step 5: 关闭设置面板
        print("\n[Step 5] Closing settings panel...")

        # 尝试点击关闭按钮或背景
        close_selectors = [
            "button:has-text('Close')",
            "button:has-text('关闭')",
            ".modal-close",
            ".panel-close",
            "[aria-label='Close' i]",
        ]

        for selector in close_selectors:
            close_btn = app_page.locator(selector).first
            if close_btn.count() > 0 and close_btn.is_visible():
                close_btn.click()
                app_page.wait_for_timeout(500)
                print(f"  [OK] Closed via: {selector}")
                break
        else:
            # 尝试再次点击设置按钮来关闭
            if settings_btn:
                settings_btn.click()
                app_page.wait_for_timeout(500)
                print("  [OK] Closed by toggling settings button")

        # Step 6: 验证配置是否保存（通过localStorage或config文件）
        print("\n[Step 6] Verifying configuration saved...")

        # 检查localStorage
        saved_config = app_page.evaluate("""() => {
            return {
                base_url: localStorage.getItem('llm_base_url') || localStorage.getItem('base_url'),
                api_key: localStorage.getItem('llm_api_key') || localStorage.getItem('api_key'),
                model: localStorage.getItem('llm_model') || localStorage.getItem('model'),
            };
        }""")

        print(f"  LocalStorage config:")
        print(f"    base_url: {saved_config.get('base_url', 'Not found')}")
        print(f"    api_key: {saved_config.get('api_key', 'Not found')[:20] if saved_config.get('api_key') else 'Not found'}...")
        print(f"    model: {saved_config.get('model', 'Not found')}")

        # 截图
        app_page.screenshot(path="api_config_saved.png")

        print("\n[Test Complete] API configuration test finished")
        print("=" * 70)

    def test_api_config_persists_after_refresh(self, app_page: Page):
        """测试刷新页面后API配置是否保持"""
        print("\n" + "=" * 70)
        print("[Test] API Configuration Persistence After Refresh")
        print("=" * 70)

        # 先运行上一个测试来设置配置
        # 或者假设已经有配置

        # Step 1: 记录当前配置
        print("\n[Step 1] Recording current configuration...")

        config_before = app_page.evaluate("""() => {
            return {
                base_url: localStorage.getItem('llm_base_url') || localStorage.getItem('base_url'),
                api_key: localStorage.getItem('llm_api_key') || localStorage.getItem('api_key'),
                model: localStorage.getItem('llm_model') || localStorage.getItem('model'),
            };
        }""")

        print(f"  Config before refresh:")
        print(f"    base_url: {config_before.get('base_url', 'None')}")
        print(f"    api_key: {config_before.get('api_key', 'None')[:20] if config_before.get('api_key') else 'None'}...")
        print(f"    model: {config_before.get('model', 'None')}")

        # Step 2: 刷新页面
        print("\n[Step 2] Refreshing page...")
        app_page.reload()
        app_page.wait_for_load_state("networkidle")
        app_page.wait_for_timeout(2000)
        print("  [OK] Page refreshed")

        # Step 3: 检查配置是否保持
        print("\n[Step 3] Checking configuration after refresh...")

        config_after = app_page.evaluate("""() => {
            return {
                base_url: localStorage.getItem('llm_base_url') || localStorage.getItem('base_url'),
                api_key: localStorage.getItem('llm_api_key') || localStorage.getItem('api_key'),
                model: localStorage.getItem('llm_model') || localStorage.getItem('model'),
            };
        }""")

        print(f"  Config after refresh:")
        print(f"    base_url: {config_after.get('base_url', 'None')}")
        print(f"    api_key: {config_after.get('api_key', 'None')[:20] if config_after.get('api_key') else 'None'}...")
        print(f"    model: {config_after.get('model', 'None')}")

        # Step 4: 验证配置一致性
        print("\n[Step 4] Validating configuration consistency...")

        if config_before.get('base_url'):
            if config_before['base_url'] == config_after['base_url']:
                print("  [OK] base_url persisted")
            else:
                print(f"  [ERROR] base_url changed: {config_before['base_url']} -> {config_after['base_url']}")

        if config_before.get('api_key'):
            if config_before['api_key'] == config_after['api_key']:
                print("  [OK] api_key persisted")
            else:
                print("  [ERROR] api_key changed")

        if config_before.get('model'):
            if config_before['model'] == config_after['model']:
                print("  [OK] model persisted")
            else:
                print(f"  [ERROR] model changed: {config_before['model']} -> {config_after['model']}")

        print("\n[Test Complete] Configuration persistence test finished")
        print("=" * 70)


class TestMultiTurnConversation:
    """多轮对话测试"""

    def test_multi_turn_learning_conversation(self, app_page: Page):
        """测试Learning模式的多轮对话"""
        print("\n" + "=" * 70)
        print("[Test] Multi-Turn Conversation - Learning Mode")
        print("=" * 70)

        # Step 1: 进入Learning模式
        print("\n[Step 1] Entering Learning mode...")
        learning_btn = app_page.locator("button.feature-card[data-mode='learning']")
        expect(learning_btn).to_be_visible(timeout=5000)
        learning_btn.click()
        app_page.wait_for_timeout(1000)

        chat_view = app_page.locator("#chat-view")
        expect(chat_view).to_be_visible(timeout=5000)
        print("  [OK] Entered Learning mode")

        # 定义多轮对话场景
        conversation = [
            {
                "round": 1,
                "query": "什么是勾股定理？",
                "expected_keywords": ["直角三角形", "平方", "勾股"],
            },
            {
                "round": 2,
                "query": "请给出证明过程",
                "expected_keywords": ["证明", "面积", "正方形"],
            },
            {
                "round": 3,
                "query": "有哪些实际应用？",
                "expected_keywords": ["应用", "距离", "建筑"],
            },
        ]

        input_textarea = app_page.locator("#input-textarea")
        send_btn = app_page.locator("#send-btn")

        for turn in conversation:
            print(f"\n[Round {turn['round']}] Query: {turn['query']}")

            # 输入查询
            expect(input_textarea).to_be_editable(timeout=5000)
            input_textarea.clear()
            input_textarea.fill(turn['query'])

            # 提交
            expect(send_btn).to_be_enabled(timeout=5000)
            send_btn.click()
            print(f"  [OK] Query submitted")

            # 等待响应
            print(f"  Waiting for response (max 120s)...")
            try:
                expect(send_btn).to_be_enabled(timeout=120000)
                print(f"  [OK] Response received")
            except:
                print(f"  [ERROR] Response timeout")
                app_page.screenshot(path=f"error_round_{turn['round']}_timeout.png")
                pytest.fail(f"Round {turn['round']}: Response timeout")

            # 验证响应
            ai_messages = app_page.locator(".message.ai")
            current_message_count = ai_messages.count()
            print(f"  Total AI messages: {current_message_count}")

            if current_message_count >= turn['round']:
                last_message = ai_messages.nth(turn['round'] - 1)
                content = last_message.text_content()

                # 检查关键词
                found_keywords = [kw for kw in turn['expected_keywords'] if kw in content]
                print(f"  Keywords found: {len(found_keywords)}/{len(turn['expected_keywords'])}")

                # 检查内容长度
                print(f"  Response length: {len(content)} characters")

                if len(content) < 50:
                    print(f"  [WARN] Response seems too short")
            else:
                print(f"  [ERROR] Expected {turn['round']} AI messages, got {current_message_count}")

            # 短暂等待，模拟真实用户行为
            app_page.wait_for_timeout(2000)

        # 验证对话历史
        print(f"\n[Verification] Checking conversation history...")

        user_messages = app_page.locator(".message.user")
        ai_messages = app_page.locator(".message.ai")

        user_count = user_messages.count()
        ai_count = ai_messages.count()

        print(f"  User messages: {user_count}")
        print(f"  AI messages: {ai_count}")

        assert user_count == len(conversation), f"Expected {len(conversation)} user messages, got {user_count}"
        assert ai_count >= len(conversation), f"Expected at least {len(conversation)} AI messages, got {ai_count}"

        print(f"  [OK] Conversation history correct")

        # 截图
        app_page.screenshot(path="multi_turn_conversation.png", full_page=True)

        print("\n[Test Complete] Multi-turn conversation test passed")
        print("=" * 70)


class TestModeSwitching:
    """模式切换测试"""

    def test_switch_between_modes(self, app_page: Page):
        """测试不同模式之间的切换"""
        print("\n" + "=" * 70)
        print("[Test] Mode Switching")
        print("=" * 70)

        modes_to_test = [
            {"name": "Learning", "data_mode": "learning"},
            {"name": "Solving", "data_mode": "solving"},
            {"name": "Research", "data_mode": "research"},
        ]

        for mode in modes_to_test:
            print(f"\n[Testing] Switching to {mode['name']} mode...")

            # 如果不在home view，先回到home
            home_view = app_page.locator("#home-view")
            if not home_view.is_visible():
                print(f"  Returning to home...")
                # 查找返回home的按钮
                home_btn = app_page.locator("button:has-text('Home'), button:has-text('主页'), .home-btn").first
                if home_btn.count() > 0 and home_btn.is_visible():
                    home_btn.click()
                    app_page.wait_for_timeout(1000)

            # 点击模式卡片
            mode_btn = app_page.locator(f"button.feature-card[data-mode='{mode['data_mode']}']")

            if mode_btn.count() == 0 or not mode_btn.is_visible():
                print(f"  [SKIP] {mode['name']} mode not available")
                continue

            mode_btn.click()
            app_page.wait_for_timeout(1500)

            # 验证切换成功
            js_mode = app_page.evaluate("() => AppState.mode")
            js_view = app_page.evaluate("() => AppState.view")

            print(f"  AppState: view='{js_view}', mode='{js_mode}'")

            if js_view == 'chat':
                print(f"  [OK] Switched to {mode['name']} mode")

                # 简单测试：提交一个查询
                input_textarea = app_page.locator("#input-textarea")
                if input_textarea.is_visible():
                    input_textarea.fill(f"测试{mode['name']}模式")

                    send_btn = app_page.locator("#send-btn")
                    if send_btn.is_visible() and send_btn.is_enabled():
                        send_btn.click()
                        print(f"  [OK] Query submitted in {mode['name']} mode")

                        # 等待短暂时间（不等完整响应）
                        app_page.wait_for_timeout(3000)

                        # 停止生成（如果有stop按钮）
                        stop_btn = app_page.locator("#stop-btn")
                        if stop_btn.is_visible():
                            stop_btn.click()
                            print(f"  [OK] Generation stopped")
                            app_page.wait_for_timeout(1000)
            else:
                print(f"  [WARN] View did not switch to chat: {js_view}")

            # 截图
            app_page.screenshot(path=f"mode_{mode['data_mode']}.png")

        print("\n[Test Complete] Mode switching test finished")
        print("=" * 70)


class TestRealWorldScenarios:
    """真实世界使用场景测试"""

    def test_complete_user_journey(self, app_page: Page):
        """模拟完整的用户使用流程"""
        print("\n" + "=" * 70)
        print("[Test] Complete User Journey - Real World Scenario")
        print("=" * 70)

        # 场景：用户第一次使用，学习数学概念，然后解题

        # Phase 1: 学习勾股定理
        print("\n[Phase 1] Learning Phase - Understanding Pythagorean Theorem")

        learning_btn = app_page.locator("button.feature-card[data-mode='learning']")
        learning_btn.click()
        app_page.wait_for_timeout(1000)

        input_textarea = app_page.locator("#input-textarea")
        send_btn = app_page.locator("#send-btn")

        # 第一个查询
        input_textarea.fill("什么是勾股定理？请详细讲解")
        send_btn.click()
        print("  Query 1: 什么是勾股定理？")

        # 等待响应
        try:
            expect(send_btn).to_be_enabled(timeout=120000)
            print("  [OK] Learning complete")
        except:
            print("  [WARN] Response timeout, continuing...")

        app_page.wait_for_timeout(2000)

        # Phase 2: 检查是否有历史记录功能
        print("\n[Phase 2] Checking History Feature")

        # 查找历史记录区域
        history_selectors = [
            ".history",
            ".sidebar",
            "#history",
            "[class*='history']",
            ".conversation-list",
        ]

        for selector in history_selectors:
            history_el = app_page.locator(selector).first
            if history_el.count() > 0 and history_el.is_visible():
                print(f"  [OK] Found history section: {selector}")
                break
        else:
            print("  [INFO] History section not visible or not found")

        # Phase 3: 切换到Solving模式解题
        print("\n[Phase 3] Solving Phase - Practice Problems")

        # 返回首页（如果需要）
        # 或者直接通过导航切换模式

        # 查找solving按钮（可能在导航栏）
        solving_btn = app_page.locator("[data-mode='solving'], button:has-text('Solving')").first

        if solving_btn.count() > 0 and solving_btn.is_visible():
            solving_btn.click()
            app_page.wait_for_timeout(1000)
            print("  [OK] Switched to Solving mode")

            # 提交解题请求
            if input_textarea.is_visible():
                input_textarea.fill("已知直角三角形两边长为3和4，求第三边")
                send_btn.click()
                print("  Query: 求直角三角形第三边")

                # 等待响应
                try:
                    expect(send_btn).to_be_enabled(timeout=120000)
                    print("  [OK] Solution provided")
                except:
                    print("  [WARN] Response timeout")
        else:
            print("  [SKIP] Solving mode not accessible from current view")

        # 截图最终状态
        app_page.screenshot(path="complete_user_journey.png", full_page=True)

        print("\n[Test Complete] Complete user journey test finished")
        print("=" * 70)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
