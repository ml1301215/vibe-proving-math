import inspect

from modes.research.solver import SolverResult
from modes.research import reviewer as reviewer_module
from modes.research import parser as parser_module
from modes.research.parser import TheoremProofPair
from modes.formalization.pipeline import FormalizeResult
from skills.search_theorems import TheoremMatch
from skills import verify_sequential as verify_module


def test_solver_result_sanitizes_blueprint_but_preserves_code_blocks():
    result = SolverResult(
        blueprint=(
            "## 完整证明\n\n"
            "\\textbf{结论}：由 $x^2 \\ge 0$ 得证。\n\n"
            "```text\n"
            "C:\\Users\\me\\proof.lean: error: unknown identifier\n"
            "```"
        ),
        references=[{"name": r"\textbf{Lagrange's theorem}", "status": "verified"}],
        confidence=0.9,
        verdict="proved",
        obstacles=[r"\emph{仍需补充一个引理}"],
        failed_paths=[r"上一轮报错：```text\nC:\tmp\Foo.lean: error\n```"],
    )

    data = result.to_dict()
    assert "\\textbf" not in data["blueprint"]
    assert "$x^2 \\ge 0$" in data["blueprint"]
    assert "C:\\Users\\me\\proof.lean" in data["blueprint"]
    assert data["references"][0]["name"] == "Lagrange's theorem"
    assert data["obstacles"][0] == "仍需补充一个引理"


def test_formalize_result_sanitizes_explanation_only():
    result = FormalizeResult(
        status="generated",
        lean_code="theorem demo : True := by\n  trivial",
        explanation=r"\textbf{解释}：证明了 $True$。",
        match_explanation=r"\emph{匹配说明}",
        compilation={"status": "error", "error": r"C:\tmp\Foo.lean:1: error"},
    )

    data = result.to_dict()
    assert data["explanation"] == "解释：证明了 $True$。"
    assert data["match_explanation"] == "匹配说明"
    assert data["compilation"]["error"] == r"C:\tmp\Foo.lean:1: error"


def test_theorem_match_to_dict_sanitizes_fields():
    match = TheoremMatch(
        name=r"\textbf{Cauchy-Schwarz}",
        body=r"若 $a,b \in \mathbb{R}$，则 \emph{不等式}成立。",
        slogan=r"\cite{x} 一个经典结果",
        similarity=0.9,
        score=0.95,
        link="https://example.com",
        paper_title=r"\textit{Algebra}",
        paper_authors=[r"\textbf{Lang}", "Artin"],
    )

    data = match.to_dict()
    assert data["name"] == "Cauchy-Schwarz"
    assert "不等式" in data["body"]
    assert "\\emph" not in data["body"]
    assert data["slogan"] == "一个经典结果"
    assert data["paper_title"] == "Algebra"
    assert data["paper_authors"] == ["Lang", "Artin"]


def test_review_prompts_require_inline_latex_for_math():
    assert "$...$" in reviewer_module._LATEX_STYLE_INSTRUCTION
    assert "$...$" in verify_module._LATEX_STYLE_INSTRUCTION
    assert "$...$" in parser_module._LATEX_STYLE_INSTRUCTION
    assert verify_module._LATEX_STYLE_INSTRUCTION in verify_module._VERIFY_USER_TEMPLATE
    assert "_LATEX_STYLE_INSTRUCTION" in inspect.getsource(reviewer_module._review_statement_without_proof)
    assert "_LATEX_STYLE_INSTRUCTION" in inspect.getsource(parser_module.extract_statement_candidates_from_text)
    assert "Output style for mathematical expressions" in verify_module._VERIFY_SYSTEM


def test_theorem_review_to_dict_normalizes_math_and_strips_backticks():
    review = reviewer_module.TheoremReview(
        theorem=TheoremProofPair(
            env_type="theorem",
            ref="定理1.1",
            statement="设 `k` 是特征为3的域，且 p=3，令 g ∈ G。",
            proof=None,
            source="paper.pdf",
            location_hint="section 1 (page 1)",
            page_span="page 1",
        ),
        verification=None,
        citation_checks=[],
        issues=[],
        verdict="Correct",
    )

    data = review.to_dict()
    assert "`" not in data["theorem_name"]
    assert "$p=3$" in data["theorem_name"] or "$p=3$" in data["statement"]
    assert "\\in" in data["statement"]
