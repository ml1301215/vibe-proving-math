import re
from pathlib import Path


UI_APP = Path(__file__).resolve().parent.parent / "ui" / "app.js"


def test_formalization_examples_use_plain_smoke_cases() -> None:
    text = UI_APP.read_text(encoding="utf-8")
    m = re.search(r"const examplesByMode = \{.*?formalization:\s*\{(?P<body>.*?)\n\s*\},\n\s*\};", text, re.S)
    assert m, "应能定位 app.js 中的 formalization 示例配置"
    block = m.group("body")

    assert "对任意整数 a, b，有 a^2 + b^2 ≥ 2ab" in block
    assert "对任意实数 a, b，有 (a + b)^2 = a^2 + 2ab + b^2" in block
    assert "对任意自然数 a, b, c，若 a ∣ b 且 b ∣ c，则 a ∣ c" in block

    assert "badge:" not in block
    assert "note:" not in block


def test_formalization_empty_state_renders_plain_example_entries() -> None:
    text = UI_APP.read_text(encoding="utf-8")

    assert "ce-example-badge" not in text
    assert "ce-example-note" not in text
    assert "data-raw" in text
    assert "ce-example-main" in text


def test_solving_examples_link_to_firstproof_official_site() -> None:
    text = UI_APP.read_text(encoding="utf-8")

    assert "https://1stproof.org/first-batch.html" in text
    assert "https://arxiv.org/abs/2602.05192" not in text


def test_formalization_result_omits_verbose_panels() -> None:
    text = UI_APP.read_text(encoding="utf-8")

    assert "Formalization Blueprint" not in text
    assert "Verification Trace" not in text
    assert "Retrieval Context" not in text
    assert "Next Step Hint" not in text
    assert "形式化 Blueprint" not in text
    assert "验证轨迹" not in text
    assert "检索上下文" not in text
    assert "下一步建议" not in text


def test_formalization_result_keeps_single_playground_entry_and_harmonic_link() -> None:
    text = UI_APP.read_text(encoding="utf-8")

    assert "Open Lean Playground" not in text
    assert "打开 Lean Playground" not in text
    assert "Verify in Lean Playground" in text
    assert "在 Lean Playground 验证" in text
    assert "https://harmonic.fun/" in text
    assert "Try Harmonic auto-formalization" in text
    assert "试试 Harmonic 自动形式化" in text


def test_formalization_home_examples_include_harmonic_link() -> None:
    text = UI_APP.read_text(encoding="utf-8")

    assert "也可以试试 Harmonic 自动形式化" in text
    assert "You can also try Harmonic auto-formalization" in text
    assert "https://harmonic.fun/" in text


def test_formalization_result_falls_back_to_selected_candidate_code() -> None:
    text = UI_APP.read_text(encoding="utf-8")

    assert "result.lean_code    || selectedCandidate.lean_code || ''" in text


def test_formalization_default_model_is_codex() -> None:
    text = UI_APP.read_text(encoding="utf-8")

    assert "formalization: 'gpt-5.3-codex'" in text
