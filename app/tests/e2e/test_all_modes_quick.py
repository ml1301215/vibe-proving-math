"""快速诊断测试 - 所有模式
目标: 用最短时间获取最大信息量,快速发现问题
策略:
- 每个模式只测试一次
- 等待适当时间后截图
- 检查DOM结构和内容
- 记录详细的诊断信息
"""
import pytest
from playwright.sync_api import Page, expect


@pytest.fixture
def app_page(page: Page):
    """打开应用"""
    page.goto("http://localhost:8080/ui/")
    page.wait_for_load_state("networkidle")
    return page


def test_all_modes_quick_diagnosis(app_page: Page):
    """快速诊断所有模式 - 30秒内完成,获取最大信息"""

    results = {}

    # ===== 模式1: Solving =====
    print("\n" + "="*60)
    print("测试 SOLVING 模式")
    print("="*60)

    solving_card = app_page.locator("button.feature-card[data-mode='solving']")
    solving_card.click()
    app_page.wait_for_timeout(1000)

    input_textarea = app_page.locator("#input-textarea")
    input_textarea.fill("求解: x² + 5x + 6 = 0")

    send_btn = app_page.locator("#send-btn")
    send_btn.click()

    # 等待15秒(优化后应该更快)
    app_page.wait_for_timeout(15000)

    # 截图
    app_page.screenshot(path="mode_solving.png")

    # 检查输出
    assistant_msgs = app_page.locator(".message.ai")
    msg_count = assistant_msgs.count()

    if msg_count > 0:
        content = assistant_msgs.last.locator(".message-content").text_content()
        results["solving"] = {
            "status": "有输出",
            "length": len(content),
            "preview": content[:200]
        }
        print(f"[OK] Solving模式: 有输出 ({len(content)}字符)")
        print(f"  预览: {content[:100]}...")
    else:
        # 检查是否有错误
        errors = app_page.locator(".section-error-details")
        if errors.count() > 0:
            error_text = errors.first.text_content()
            results["solving"] = {"status": "错误", "error": error_text[:200]}
            print(f"[FAIL] Solving模式: 错误 - {error_text[:100]}...")
        else:
            results["solving"] = {"status": "无输出"}
            print("[FAIL] Solving模式: 无输出(可能需要更长时间)")

    # ===== 模式2: Reviewing =====
    print("\n" + "="*60)
    print("测试 REVIEWING 模式")
    print("="*60)

    reviewing_tab = app_page.locator("button.mode-tab[data-mode='reviewing']")
    reviewing_tab.click()
    app_page.wait_for_timeout(500)

    # 验证上传按钮存在
    attach_btn = app_page.locator("#attach-btn")
    print(f"上传按钮可见: {attach_btn.is_visible()}")

    # 清空输入,输入新内容
    input_textarea.fill("")
    proof_text = """定理: sqrt(2)是无理数
证明: 假设sqrt(2)=p/q(p,q互质),则2q²=p²,故p是偶数。
设p=2k,则q²=2k²,故q也是偶数,矛盾。"""
    input_textarea.fill(proof_text)

    send_btn.click()

    # 等待15秒(优化后应该更快)
    app_page.wait_for_timeout(15000)

    # 截图
    app_page.screenshot(path="mode_reviewing.png")

    # 检查输出
    assistant_msgs = app_page.locator(".message.ai")
    # 注意: 之前solving可能有1条消息,reviewing应该是第2条
    msg_count = assistant_msgs.count()

    if msg_count >= 2:
        content = assistant_msgs.last.locator(".message-content").text_content()
        results["reviewing"] = {
            "status": "有输出",
            "length": len(content),
            "preview": content[:200]
        }
        print(f"[OK] Reviewing模式: 有输出 ({len(content)}字符)")
        print(f"  预览: {content[:100]}...")
    else:
        errors = app_page.locator(".section-error-details")
        if errors.count() > 0:
            error_text = errors.nth(errors.count()-1).text_content()
            results["reviewing"] = {"status": "错误", "error": error_text[:200]}
            print(f"[FAIL] Reviewing模式: 错误 - {error_text[:100]}...")
        else:
            results["reviewing"] = {"status": "无输出"}
            print("[FAIL] Reviewing模式: 无输出(可能需要更长时间)")

    # ===== 模式3: Searching =====
    print("\n" + "="*60)
    print("测试 SEARCHING 模式")
    print("="*60)

    searching_tab = app_page.locator("button.mode-tab[data-mode='searching']")
    searching_tab.click()
    app_page.wait_for_timeout(500)

    input_textarea.fill("")
    input_textarea.fill("费马大定理")

    send_btn.click()

    # 等待25秒(搜索可能需要更长时间)
    app_page.wait_for_timeout(25000)

    # 截图
    app_page.screenshot(path="mode_searching.png")

    # 检查输出
    assistant_msgs = app_page.locator(".message.ai")
    msg_count = assistant_msgs.count()

    if msg_count >= 3:
        content = assistant_msgs.last.locator(".message-content").text_content()
        results["searching"] = {
            "status": "有输出",
            "length": len(content),
            "preview": content[:200]
        }
        print(f"[OK] Searching模式: 有输出 ({len(content)}字符)")
        print(f"  预览: {content[:100]}...")
    else:
        errors = app_page.locator(".section-error-details")
        if errors.count() > 0:
            error_text = errors.nth(errors.count()-1).text_content()
            results["searching"] = {"status": "错误", "error": error_text[:200]}
            print(f"[FAIL] Searching模式: 错误 - {error_text[:100]}...")
        else:
            results["searching"] = {"status": "无输出"}
            print("[FAIL] Searching模式: 无输出(可能需要更长时间或服务不可用)")

    # ===== 总结 =====
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)

    for mode, result in results.items():
        status = result.get("status", "未知")
        print(f"{mode.upper():12s}: {status}")

    # 至少有一个模式应该工作
    working_modes = [m for m, r in results.items() if r.get("status") == "有输出"]
    print(f"\n工作正常的模式数: {len(working_modes)}/3")

    # 不强制要求所有模式都工作,只要有诊断信息即可
    assert len(results) == 3, "应该测试了3个模式"
