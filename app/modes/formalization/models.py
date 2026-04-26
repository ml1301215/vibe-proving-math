from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from core.text_sanitize import strip_non_math_latex


LEAN_PLAYGROUND_URL = "https://live.lean-lang.org/"


@dataclass
class RetrievalHit:
    kind: str
    title: str
    body: str
    source: str
    source_url: str = ""
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "title": strip_non_math_latex(self.title),
            "body": strip_non_math_latex(self.body),
            "source": self.source,
            "source_url": self.source_url,
            "score": self.score,
            "metadata": self.metadata,
        }


@dataclass
class FormalizationBlueprint:
    goal_summary: str
    target_shape: str = ""
    definitions: list[str] = field(default_factory=list)
    planned_imports: list[str] = field(default_factory=list)
    intermediate_lemmas: list[str] = field(default_factory=list)
    strategy: str = ""
    notes: list[str] = field(default_factory=list)
    revision: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_summary": strip_non_math_latex(self.goal_summary),
            "target_shape": strip_non_math_latex(self.target_shape),
            "definitions": [strip_non_math_latex(x) for x in self.definitions],
            "planned_imports": [strip_non_math_latex(x) for x in self.planned_imports],
            "intermediate_lemmas": [strip_non_math_latex(x) for x in self.intermediate_lemmas],
            "strategy": strip_non_math_latex(self.strategy),
            "notes": [strip_non_math_latex(x) for x in self.notes],
            "revision": self.revision,
        }


@dataclass
class FormalizationCandidate:
    lean_code: str
    theorem_statement: str = ""
    uses_mathlib: bool = False
    proof_status: str = "statement_only"
    explanation: str = ""
    confidence: float = 0.0
    origin: str = "generated"
    blueprint_revision: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "lean_code": self.lean_code,
            "theorem_statement": self.theorem_statement,
            "uses_mathlib": self.uses_mathlib,
            "proof_status": self.proof_status,
            "explanation": strip_non_math_latex(self.explanation),
            "confidence": self.confidence,
            "origin": self.origin,
            "blueprint_revision": self.blueprint_revision,
        }


@dataclass
class VerificationReport:
    status: str
    error: str = ""
    failure_mode: str = "none"
    diagnostics: list[str] = field(default_factory=list)
    verifier: str = "local_lean"
    passed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "error": self.error,
            "failure_mode": self.failure_mode,
            "diagnostics": list(self.diagnostics),
            "verifier": self.verifier,
            "passed": self.passed,
        }


@dataclass
class FormalizationAttempt:
    attempt: int
    action: str
    blueprint_revision: int
    candidate: FormalizationCandidate
    verification: VerificationReport

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempt": self.attempt,
            "action": self.action,
            "blueprint_revision": self.blueprint_revision,
            "candidate": self.candidate.to_dict(),
            "verification": self.verification.to_dict(),
        }


@dataclass
class FormalizeResult:
    status: str
    lean_code: str = ""
    theorem_name: str = ""
    source: str = ""
    source_url: str = LEAN_PLAYGROUND_URL
    match_score: float = 0.0
    match_explanation: str = ""
    proof_status: str = ""
    uses_mathlib: bool = False
    confidence: float = 0.0
    explanation: str = ""
    compilation: dict[str, Any] = field(default_factory=dict)
    iterations: int = 1
    auto_optimized: bool = False
    attempt_history: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""
    blueprint: Optional[dict[str, Any]] = None
    selected_candidate: Optional[dict[str, Any]] = None
    verification_trace: list[dict[str, Any]] = field(default_factory=list)
    retrieval_context: list[dict[str, Any]] = field(default_factory=list)
    failure_mode: str = "none"
    next_action_hint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "lean_code": self.lean_code,
            "theorem_name": self.theorem_name,
            "source": self.source,
            "source_url": self.source_url,
            "match_score": self.match_score,
            "match_explanation": strip_non_math_latex(self.match_explanation),
            "proof_status": self.proof_status,
            "uses_mathlib": self.uses_mathlib,
            "confidence": self.confidence,
            "explanation": strip_non_math_latex(self.explanation),
            "compilation": self.compilation,
            "iterations": self.iterations,
            "auto_optimized": self.auto_optimized,
            "attempt_history": self.attempt_history,
            "error": strip_non_math_latex(self.error),
            "blueprint": self.blueprint,
            "selected_candidate": self.selected_candidate,
            "verification_trace": self.verification_trace,
            "retrieval_context": self.retrieval_context,
            "failure_mode": self.failure_mode,
            "next_action_hint": strip_non_math_latex(self.next_action_hint),
        }
