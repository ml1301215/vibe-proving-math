"""研究模式 Pipeline：问题解决 —— Generation-Verification-Revision 循环。

参考：Aletheia (arXiv:2602.10177) + Rethlas 自适应控制架构。
关键设计原则：
  1. Generator 与 Verifier 严格解耦（Verifier 不见 Generator 思维链）
  2. TheoremSearch 强制核查所有引用（防幻觉引用）
  3. 主动拒绝：置信度不足时返回 "No confident solution"，而非编造
  4. 修订循环：验证反馈驱动 proof 修订，最多 3 轮
  5. 脆弱性测试：子目标分解前先构造反例，若存在则直接终止
  6. 失败路径持久化：历次失败原因传入子目标分解，避免重蹈覆辙

Pipeline：
  Phase 0: 直接检索判断（similarity > 0.75 则直接返回引用）
  Phase 1: direct_proving + verify + revision loop（最多 3 轮）
  Phase 1.5: 若 Phase 1 失败 → counterexample test（脆弱性检验）
  Phase 2: 若无反例 → subgoal_decomp（传入失败上下文）+ 对每个子目标重试 Phase 1
  Phase 3: verify_sequential（独立验证，与 Generator 解耦）
  Output:  结构化证明蓝图 + 引用来源 + 置信度分级

输出：SolverResult（JSON 可序列化）
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Optional

logger = logging.getLogger(__name__)

from core.text_sanitize import strip_non_math_latex, strip_non_math_latex_preserve_code, sanitize_dict
from skills.direct_proving import direct_proving, ProofResult
from skills.subgoal_decomp import subgoal_decomp, DecompResult
from skills.verify_sequential import verify_sequential, VerificationResult
from skills.search_theorems import search_theorems, TheoremMatch, format_theorems_for_prompt
from skills.counterexamples import find_counterexample, CounterexampleResult

_CONFIDENCE_THRESHOLD = 0.6  # 低于此值视为 "No confident solution"
_MAX_REVISIONS = 1            # 优化: 从3轮降到1轮,加快响应速度（简单问题不需要多轮修订）

# 疑问式命题关键词（中英文），命中时优先走反例路径
_INTERROGATIVE_PATTERNS = (
    "是否有", "是否存在", "是否成立", "是否总是", "是否一定",
    "能否", "会不会", "有没有",
    "is it true", "does there exist", "is there", "can we always",
    "does it hold", "is it always", "is it possible",
    "? ", "？",
)

# 进度回调：(step, message) -> awaitable
ProgressCb = Optional[Callable[[str, str], Awaitable[None]]]


async def _emit(progress: ProgressCb, step: str, msg: str) -> None:
    if progress is None:
        return
    try:
        await progress(step, msg)
    except Exception:
        pass


@dataclass
class SolverResult:
    blueprint: str             # 证明蓝图（Markdown）
    references: list[dict]     # 引用的定理列表（来自 TheoremSearch 核查）
    confidence: float          # 0.0-1.0
    verdict: str               # "proved" | "partial" | "No confident solution" | "direct_hit" | "counterexample"
    obstacles: list[str] = field(default_factory=list)   # 已知障碍
    subgoals: list[dict] = field(default_factory=list)   # 子目标（若做了分解）
    verification: Optional[dict] = None  # 验证结果摘要
    failed_paths: list[str] = field(default_factory=list)  # 历次失败原因摘要
    token_count: int = 0       # 估算 token 消耗

    def sanitized_blueprint(self) -> str:
        return strip_non_math_latex_preserve_code(self.blueprint)

    def sanitized_references(self) -> list[dict]:
        return sanitize_dict(self.references)

    def sanitized_obstacles(self) -> list[str]:
        return [strip_non_math_latex(o) for o in self.obstacles]

    def sanitized_failed_paths(self) -> list[str]:
        return [strip_non_math_latex_preserve_code(p) for p in self.failed_paths]

    def to_dict(self) -> dict:
        return {
            "blueprint": self.sanitized_blueprint(),
            "references": self.sanitized_references(),
            "confidence": self.confidence,
            "verdict": self.verdict,
            "obstacles": self.sanitized_obstacles(),
            "subgoals": sanitize_dict(self.subgoals),
            "verification": sanitize_dict(self.verification),
            "failed_paths": self.sanitized_failed_paths(),
        }

    def is_confident(self) -> bool:
        return self.confidence >= _CONFIDENCE_THRESHOLD and self.verdict not in ("No confident solution",)


async def _verify_references(references: list[str]) -> list[dict]:
    """用 TheoremSearch 核查 LLM 给出的引用，返回每条的验证结果。"""
    verified = []
    for ref in references:
        try:
            results = await search_theorems(ref, top_k=3, min_sim=0.4)
            if results and results[0].similarity >= 0.65:
                verified.append({
                    "name": ref,
                    "status": "verified",
                    "matched": results[0].name,
                    "similarity": results[0].similarity,
                    "link": results[0].link,
                })
            else:
                verified.append({
                    "name": ref,
                    "status": "not_found",
                    "matched": None,
                    "similarity": results[0].similarity if results else 0.0,
                    "link": None,
                })
        except Exception as e:
            verified.append({"name": ref, "status": f"error: {type(e).__name__}: {e}", "matched": None, "similarity": 0, "link": None})
    return verified


def _is_interrogative(statement: str) -> bool:
    """判断命题是否为疑问式（'是否有X'/'does there exist'等），这类命题应优先测反例。"""
    s_lower = statement.lower()
    return any(kw in s_lower for kw in _INTERROGATIVE_PATTERNS)


async def _safe_verify(proof: str, statement: str) -> Optional["VerificationResult"]:
    """安全调用 verify_sequential，捕获异常返回 None。异常会重试一次。"""
    for attempt in range(2):
        try:
            return await verify_sequential(proof, statement)
        except Exception as e:
            logger.warning("verify_sequential failed (attempt %d/2): %s: %s", attempt + 1, type(e).__name__, e)
    return None


async def _attempt_proof_with_revision(
    statement: str,
    model: Optional[str],
    max_revisions: int = _MAX_REVISIONS,
    extra_context: Optional[str] = None,
    progress: ProgressCb = None,
    phase_label: str = "proof",
    lang: Optional[str] = None,
) -> tuple[ProofResult, VerificationResult | None, list[str]]:
    """单次直接证明尝试 + 最多 max_revisions 轮验证-修订循环。

    返回 (proof, verify_result, failed_paths)。
    failed_paths 记录每轮修订中验证器报出的错误，供后续分解使用。
    """
    failed_paths: list[str] = []

    async def _safe_prove(stmt: str, ctx: Optional[str] = None) -> ProofResult:
        try:
            return await direct_proving(stmt, use_search=True, model=model, extra_context=ctx, lang=lang)
        except Exception as e:
            return ProofResult(
                proof="", confidence=0.0, status="failed",
                gaps=[f"{type(e).__name__}: {e}"], references=[]
            )

    await _emit(progress, phase_label, "正在生成证明…")
    proof = await _safe_prove(statement, extra_context)

    for rev in range(max_revisions):
        if not proof.is_successful():
            break
        await _emit(progress, phase_label, f"正在验证证明（第 {rev + 1} 轮）…")
        verify = await _safe_verify(proof.proof, statement)
        # Bug Fix: verify=None 表示验证器调用失败（不是"通过"），不能直接返回
        if verify is None:
            # 记录验证器失败，降低置信度但不进入修订（修订需要具体错误）
            failed_paths.append(f"第 {rev + 1} 次验证器调用失败（API异常），结果不可信")
            # 如果还有修订机会，尝试让 Generator 生成更自包含的证明
            if rev < max_revisions - 1:
                revision_context = (
                    (extra_context + "\n\n") if extra_context else ""
                ) + (
                    "IMPORTANT: The previous proof could not be independently verified due to "
                    "system errors. Please write a proof that is entirely self-contained: "
                    "prove every cited theorem from first principles, do not rely on external references, "
                    "and make every logical step maximally explicit and checkable."
                )
                await _emit(progress, phase_label, f"验证器失败，请求自包含证明（第 {rev + 1} → {rev + 2} 轮）…")
                proof = await _safe_prove(statement, revision_context)
            continue
        if not verify.has_errors():
            return proof, verify, failed_paths

        # 收集本轮验证错误
        error_lines = [
            f"- [{s.verdict}] Step {s.step_num}: {s.reason}"
            + (f" (cited: {s.cited_theorem})" if s.cited_theorem else "")
            for s in verify.steps if s.verdict != "passed"
        ]
        round_summary = f"第 {rev + 1} 次尝试失败：\n" + "\n".join(error_lines)
        failed_paths.append(round_summary)

        # TheoremSearch 核查摘要：未找到的引用需要特别告知 generator
        ts_feedback_lines: list[str] = []
        for r in (verify.theorem_search_results or []):
            if r["status"] == "found":
                ts_feedback_lines.append(
                    f"  ✓ '{r['cited']}' exists in TheoremSearch (sim={r['similarity']:.0%},"
                    f" matched: {r['matched_name']})"
                )
            else:
                ts_feedback_lines.append(
                    f"  ✗ '{r['cited']}' NOT FOUND in TheoremSearch"
                    + (f" (closest: '{r['matched_name']}' sim={r['similarity']:.0%})" if r["matched_name"] else "")
                    + " — do NOT cite this theorem; find an alternative or prove the step from first principles."
                )
        ts_section = ""
        if ts_feedback_lines:
            ts_section = (
                "\n\nTheoremSearch citation verification results:\n"
                + "\n".join(ts_feedback_lines)
                + "\n\nIMPORTANT: Only cite theorems marked ✓. For theorems marked ✗, either:\n"
                "  (a) Prove the claim from first principles without citing that theorem, or\n"
                "  (b) Find a different theorem from TheoremSearch that does the same job."
            )

        # 构造修订上下文：把错误信息 + TheoremSearch 结果喂回 Generator
        revision_context = (
            (extra_context + "\n\n") if extra_context else ""
        ) + (
            f"IMPORTANT: A previous proof attempt was REJECTED by an independent verifier "
            f"equipped with TheoremSearch (a real math theorem database).\n\n"
            f"Verifier errors (fix ALL of these):\n"
            + "\n".join(error_lines)
            + ts_section
            + "\n\nPlease write a COMPLETELY NEW proof that addresses every error above."
        )
        await _emit(progress, phase_label, f"验证失败，正在修订（第 {rev + 1} → {rev + 2} 轮）…")
        proof = await _safe_prove(statement, revision_context)

    if proof.is_successful():
        await _emit(progress, phase_label, f"正在做最终验证…")
        verify = await _safe_verify(proof.proof, statement)
        return proof, verify, failed_paths
    return proof, None, failed_paths


async def _solve_inner(statement: str, model=None, progress: ProgressCb = None, lang: Optional[str] = None, extra_context: str = "") -> SolverResult:
    """实际求解逻辑。"""
    # ── 前置：检测命题类型 ────────────────────────────────────────────────────
    is_interrogative = _is_interrogative(statement)

    # ── Phase 0: 直接检索判断 + 预取定理（结果将复用给 Phase 1）──────────────
    await _emit(progress, "search", "正在检索相关定理与已知结果…")
    phase0_hits: list = []
    try:
        # min_sim=0.3 与 direct_proving 内部保持一致，命中缓存节省一次网络请求
        phase0_hits = await search_theorems(statement, top_k=5, min_sim=0.3)
        if phase0_hits and phase0_hits[0].similarity >= 0.75:
            top = phase0_hits[0]
            return SolverResult(
                blueprint=f"## 直接命中已知结果\n\n**{top.name}**\n\n{top.body}\n\n来源: [{top.paper_title}]({top.link})",
                references=[{
                    "name": top.name,
                    "status": "verified",
                    "matched": top.name,
                    "similarity": top.similarity,
                    "link": top.link,
                }],
                confidence=top.similarity,
                verdict="direct_hit",
            )
    except Exception as e:
        logger.warning("Phase 0 (direct search) failed: %s: %s", type(e).__name__, e)

    # ── Phase 0.5（仅疑问式命题）: 提前反例测试 ──────────────────────────────
    # 对"是否有/是否存在"型命题，反例测试优先于直接证明尝试，节省无效 LLM 调用
    if is_interrogative:
        await _emit(progress, "counterexample", "检测到疑问式命题，优先进行反例测试…")
        try:
            ce_early = await find_counterexample(statement, model=model, lang=lang)
            if ce_early.found and ce_early.confidence >= 0.80:
                return SolverResult(
                    blueprint=(
                        f"## 命题可能为假：发现潜在反例\n\n"
                        f"**反例：** {ce_early.counterexample}\n\n"
                        f"**说明：** {ce_early.explanation}\n\n"
                        + (f"**备注：** {ce_early.note}\n\n" if ce_early.note else "")
                    ),
                    references=[],
                    confidence=ce_early.confidence,
                    verdict="counterexample",
                    obstacles=["发现潜在反例，命题可能不成立"],
                    failed_paths=[],
                )
        except Exception as e:
            logger.warning("Phase 0.5 (early counterexample) failed: %s: %s", type(e).__name__, e)

    proof, verify_result, failed_paths = await _attempt_proof_with_revision(
        statement, model, max_revisions=_MAX_REVISIONS,
        extra_context=extra_context or None,
        progress=progress, phase_label="proving", lang=lang,
    )

    # Phase 1 成功（通过验证）
    # 注意：verify_result=None（验证器异常）不视为"通过"，置信度大幅折扣
    if proof.is_successful() and (verify_result is None or not verify_result.has_errors()):
        await _emit(progress, "verifying", "正在核查引用…")
        verified_refs = await _verify_references(proof.references)
        cleaned_refs = [r for r in verified_refs if r.get("status") == "verified"]
        unverified = [r["name"] for r in verified_refs if r.get("status") != "verified"]
        obstacles = [f"未能核实的引用：{name}" for name in unverified]
        # 若验证器未成功运行（None），置信度打 5 折以体现不确定性
        conf_factor = 1.0 if verify_result else 0.5
        return SolverResult(
            blueprint=f"## 完整证明\n\n{proof.proof}",
            references=cleaned_refs,
            confidence=proof.confidence * conf_factor,
            verdict=proof.status,
            obstacles=obstacles + (["验证器调用失败，置信度已保守折扣"] if not verify_result else []),
            verification=verify_result.to_dict() if verify_result else None,
            failed_paths=failed_paths,
        )

    # ── Phase 1.5: 脆弱性测试 —— 尝试构造反例 ────────────────────────────────
    await _emit(progress, "counterexample", "正在检验命题的可证性（反例测试）…")
    # 仅传入逻辑失败记录（过滤掉技术性 API 错误消息，避免污染 LLM 上下文）
    logical_failures = [fp for fp in failed_paths if "验证器调用失败" not in fp]
    ce_context = ""
    if logical_failures:
        ce_context = "Previous proof attempts revealed these difficulties:\n" + "\n".join(logical_failures[-2:])
    try:
        ce_result = await find_counterexample(statement, context=ce_context, model=model, lang=lang)
        if ce_result.found and ce_result.confidence >= 0.75:
            # 高置信度找到反例 → 命题可能为假，直接报告
            return SolverResult(
                    blueprint=(
                    f"## 命题可能为假：发现潜在反例\n\n"
                    f"**反例：** {ce_result.counterexample}\n\n"
                    f"**说明：** {ce_result.explanation}\n\n"
                    + (f"**备注：** {ce_result.note}\n\n" if ce_result.note else "")
                ),
                references=[],
                confidence=ce_result.confidence,
                verdict="counterexample",
                obstacles=["发现潜在反例，命题可能不成立"],
                failed_paths=failed_paths,
            )
    except Exception as e:
        logger.warning("Phase 1.5 (counterexample) failed: %s: %s", type(e).__name__, e)

    # ── Phase 2: 子目标分解 ───────────────────────────────────────────────────
    # 疑问式命题（"是否有/是否存在"）：若经过两轮反例测试仍无确定结论，
    # 说明问题可能是开放的前沿难题，不应强行子目标分解（代价高且结论不可靠）
    if is_interrogative:
        error_detail = "经过多轮证明尝试与反例检验均未得出确定结论。此类命题可能属于未解决的前沿问题，建议查阅最新文献。"
        if logical_failures:
            error_detail += "\n\n**探索过程中的发现：**\n" + "\n".join(f"- {fp}" for fp in logical_failures[-3:])
        return SolverResult(
            blueprint=(
                "## ⚠️ 无确定结论（疑问式命题）\n\n"
                f"{error_detail}\n\n"
                "_提示：若有更多上下文（如论文背景、已知特例），可补充后重新提交。_"
            ),
            references=[],
            confidence=0.0,
            verdict="No confident solution",
            obstacles=["疑问式命题，反例测试与直接证明均未给出确定结论"],
            failed_paths=failed_paths,
        )

    await _emit(progress, "decomposing", "正在分解为子目标…")

    # 把失败路径和搜索结果传入分解，帮助 LLM 选择不同策略
    decomp_context = ""
    if failed_paths:
        decomp_context += "Previous proof attempts failed with these issues:\n"
        decomp_context += "\n".join(failed_paths) + "\n\n"
        decomp_context += "Please propose a decomposition strategy that AVOIDS these pitfalls.\n"

    decomp = await subgoal_decomp(statement, model=model, extra_context=decomp_context, lang=lang)

    if not decomp.subgoals:
        # 汇总所有失败原因，全部暴露给用户
        error_lines = []
        if proof.gaps:
            error_lines.append("**Phase 1 (直接证明) 失败原因：**")
            for g in proof.gaps:
                error_lines.append(f"- {g}")
        if decomp.strategy and "分解失败" in decomp.strategy:
            error_lines.append(f"\n**Phase 2 (子目标分解) 失败原因：**\n- {decomp.strategy}")
        if failed_paths:
            error_lines.append("\n**历次失败记录：**")
            for fp in failed_paths:
                error_lines.append(f"- {fp}")
        if not error_lines:
            error_lines.append("- 未找到有效的证明路径（所有阶段均静默失败，请检查 API 连通性）")

        error_detail = "\n".join(error_lines)
        return SolverResult(
            blueprint=(
                "## ⚠️ 求解失败\n\n"
                f"{error_detail}\n\n"
                "_提示：若显示 API / 模型错误，请确认服务器已重启并使用了正确的 API 密钥和模型名。_"
            ),
            references=[],
            confidence=max(proof.confidence * 0.5, 0.0),
            verdict="No confident solution",
            obstacles=proof.gaps or [decomp.strategy or "无子目标"],
            failed_paths=failed_paths,
        )

    # 对每个子目标尝试证明（含各自的修订循环）
    subgoal_results = []
    all_proved = True
    all_refs: list[str] = list(proof.references)
    subgoal_failed_paths: list[str] = []

    for idx, sg in enumerate(decomp.subgoals, 1):
        await _emit(progress, "subgoal", f"正在证明子目标 {idx}/{len(decomp.subgoals)}：{sg.statement[:50]}…")
        sg_context = sg.hint if sg.hint else None
        sg_proof, sg_verify, sg_failed = await _attempt_proof_with_revision(
            sg.statement, model, max_revisions=2,
            extra_context=sg_context,
            progress=progress, phase_label=f"subgoal_{idx}", lang=lang,
        )
        all_refs.extend(sg_proof.references)
        subgoal_failed_paths.extend(sg_failed)
        subgoal_results.append({
            "id": sg.id,
            "statement": sg.statement,
            "proof": sg_proof.proof,
            "status": sg_proof.status,
            "confidence": sg_proof.confidence,
            "verified": (sg_verify.overall == "passed") if sg_verify else False,
        })
        if not sg_proof.is_successful():
            all_proved = False

    # 构建综合证明
    blueprint_lines = ["## 完整证明（子目标分解）\n"]
    blueprint_lines.append(f"**证明策略：** {decomp.strategy}\n")
    for sg_r in subgoal_results:
        status_emoji = "✓" if sg_r["status"] == "proved" else "△" if sg_r["status"] == "partial" else "✗"
        blueprint_lines.append(f"### {sg_r['id']}. {sg_r['statement']}")
        blueprint_lines.append(f"*{status_emoji} 置信度 {sg_r['confidence']:.0%}*\n")
        if sg_r["proof"]:
            blueprint_lines.append(sg_r["proof"])
        blueprint_lines.append("")

    # 附上失败路径摘要（折叠，对用户透明但不喧宾夺主）
    all_failed = failed_paths + subgoal_failed_paths
    if all_failed:
        blueprint_lines.append("\n<details>\n<summary>探索过程（点击展开）</summary>\n")
        for fp in all_failed[:4]:
            blueprint_lines.append(f"> {fp}\n")
        blueprint_lines.append("</details>\n")

    await _emit(progress, "verifying", "正在核查引用…")
    verified_refs = await _verify_references(list(set(all_refs)))
    avg_conf = sum(s["confidence"] for s in subgoal_results) / max(len(subgoal_results), 1)

    verdict = "proved" if all_proved else ("partial" if avg_conf > 0.4 else "No confident solution")
    obstacles = []
    if not all_proved:
        failed_sgs = [s["statement"][:60] for s in subgoal_results if s["status"] == "failed"]
        obstacles = [f"无法证明子目标: {f}" for f in failed_sgs]

    return SolverResult(
        blueprint="\n".join(blueprint_lines),
        references=verified_refs,
        confidence=avg_conf,
        verdict=verdict,
        obstacles=obstacles,
        subgoals=subgoal_results,
        failed_paths=all_failed,
    )


async def solve(
    statement: str,
    *,
    model: Optional[str] = None,
    time_budget_seconds: Optional[int] = None,
    progress: ProgressCb = None,
    lang: Optional[str] = None,
    extra_context: str = "",
) -> SolverResult:
    """研究模式主入口：运行完整的 GVR 证明 pipeline。"""
    import traceback as _tb
    try:
        return await _solve_inner(statement, model, progress=progress, lang=lang, extra_context=extra_context)
    except Exception as e:
        tb = _tb.format_exc()
        return SolverResult(
            blueprint=(
                "## ⚠️ 求解异常\n\n"
                f"**错误类型：** `{type(e).__name__}`\n\n"
                f"**错误信息：** {e}\n\n"
                f"<details><summary>完整堆栈（点击展开）</summary>\n\n```\n{tb}\n```\n</details>"
            ),
            references=[],
            confidence=0.0,
            verdict="error",
            obstacles=[f"{type(e).__name__}: {e}"],
        )


_LATEX_SYSTEM = """You are an expert mathematician and LaTeX typesetter.
Convert the given proof blueprint into a complete, compilable LaTeX document.

Requirements:
- Use \\documentclass{amsart}
- Include packages: amsmath, amsthm, amssymb, hyperref
- Define theorem environments: theorem, lemma, proposition, corollary, definition, remark, proof
- Use proper theorem/proof LaTeX environments (\\begin{theorem}...\\begin{proof}...\\end{proof}...\\end{theorem})
- All math must be in proper LaTeX: $...$ for inline, \\[...\\] or equation environment for display
- Numbered steps should use enumerate or align environments as appropriate
- Include \\begin{document}...\\end{document}
- Use \\maketitle with a short \\title based on the theorem being proved

CRITICAL: Output ONLY the LaTeX code. No explanation, no markdown fences, no commentary before or after.
Start your output with \\documentclass{amsart} and end with \\end{document}.
"""


async def generate_proof_latex(blueprint: str, statement: str = "", model: Optional[str] = None) -> AsyncIterator[str]:
    """将证明蓝图转换为可编译的 LaTeX 代码（流式输出）。"""
    from core.llm import stream_chat

    # 如果提供了statement，在用户消息中包含它
    if statement:
        user_message = f"**Problem Statement:**\n{statement}\n\n**Proof Blueprint:**\n{blueprint}"
    else:
        user_message = blueprint

    async for chunk in stream_chat(
        user_message,
        system=_LATEX_SYSTEM,
        model=model,
        max_tokens=16384,
    ):
        yield chunk
