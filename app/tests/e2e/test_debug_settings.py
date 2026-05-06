"""调试设置面板结构"""
import pytest
from playwright.sync_api import Page


def test_debug_settings_panel(app_page: Page):
    """调试设置面板的HTML结构"""
    print("\n[DEBUG] Settings Panel Structure")

    # 打开设置面板
    settings_btn = app_page.locator("#btn-panel-toggle")
    settings_btn.click()
    app_page.wait_for_timeout(1000)
    print("[OK] Settings panel opened")

    # 检查所有可见的输入框
    print("\n[Input Fields]")
    all_inputs = app_page.locator("input[type='text'], input[type='password'], input:not([type])")
    for i in range(all_inputs.count()):
        inp = all_inputs.nth(i)
        if inp.is_visible():
            field_id = inp.get_attribute("id")
            field_name = inp.get_attribute("name")
            placeholder = inp.get_attribute("placeholder")
            value = inp.input_value()
            print(f"  Input {i}: id='{field_id}', name='{field_name}'")
            print(f"           placeholder='{placeholder}'")
            print(f"           value='{value}'")

    # 检查所有可见的按钮
    print("\n[Buttons in Settings Panel]")
    all_buttons = app_page.locator("button")
    for i in range(all_buttons.count()):
        btn = all_buttons.nth(i)
        if btn.is_visible():
            btn_text = btn.text_content()
            btn_id = btn.get_attribute("id")
            btn_class = btn.get_attribute("class")
            aria_label = btn.get_attribute("aria-label")

            # 检查按钮是否在settings panel内
            is_in_panel = btn.evaluate("""el => {
                let parent = el.parentElement;
                while (parent) {
                    if (parent.id === 'settings-panel' || parent.id === 'run-panel') {
                        return true;
                    }
                    parent = parent.parentElement;
                }
                return false;
            }""")

            if is_in_panel or 'save' in btn_text.lower() or 'apply' in btn_text.lower():
                print(f"  Button {i}: text='{btn_text}', id='{btn_id}'")
                print(f"            class='{btn_class}'")
                print(f"            aria='{aria_label}'")
                print(f"            in_panel={is_in_panel}")

    # 检查settings panel的HTML结构
    print("\n[Settings Panel HTML]")
    settings_panel = app_page.locator("#settings-panel, #run-panel, .settings-panel, .run-panel").first
    if settings_panel.count() > 0:
        panel_html = settings_panel.inner_html()[:1000]
        print(f"  Panel HTML (first 1000 chars):")
        print(f"  {panel_html}")

    # 截图
    app_page.screenshot(path="debug_settings_structure.png", full_page=True)
    print("\n[OK] Screenshot saved")
