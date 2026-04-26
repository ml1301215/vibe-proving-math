"""Nanonets 响应解析、Markdown 大章节切分、裁决归一化单元测试。"""
from __future__ import annotations

import textwrap

import pytest

from core.nanonets_client import NanonetsExtractResult, _markdown_from_body
from modes.research.section_reviewer import (
    aggregate_overall_verdict,
    enforce_verdict_rules,
    split_major_sections,
)


def test_markdown_from_body_extracts_string():
    body = {
        "success": True,
        "status": "completed",
        "result": {"markdown": {"content": "# Hello\n\nworld"}},
    }
    assert _markdown_from_body(body).startswith("# Hello")


def test_split_major_sections_headings():
    md = textwrap.dedent("""
        # Paper Title

        Preamble para.

        ## 1. Introduction
        Intro body.

        ## 2. Results
        Result body.
    """).strip()
    secs = split_major_sections(md)
    titles = [s["title"] for s in secs]
    assert "Paper Title" in titles
    assert any("Introduction" in t for t in titles)
    assert any("Results" in t for t in titles)


def test_enforce_verdict_not_checked_cannot_be_correct():
    sec = {
        "section_title": "X",
        "main_claims": [
            {
                "role": "theorem",
                "statement": "For all n, n=n.",
                "proof_present": False,
                "verification_status": "not_checked",
                "verdict": "Correct",
                "source_quote": "",
            }
        ],
    }
    out = enforce_verdict_rules(sec)
    assert out["main_claims"][0]["verdict"] == "NotChecked"


def test_enforce_verdict_section_heading_downgraded():
    sec = {
        "section_title": "Introduction",
        "main_claims": [
            {
                "role": "theorem",
                "statement": "Introduction",
                "proof_present": True,
                "verification_status": "verified",
                "verdict": "Correct",
                "source_quote": "Introduction",
            }
        ],
    }
    out = enforce_verdict_rules(sec)
    assert out["main_claims"][0]["verification_status"] == "not_checked"
    assert out["main_claims"][0]["verdict"] == "NotChecked"


def test_aggregate_overall_all_not_checked():
    sections = [
        {
            "main_claims": [{"verdict": "NotChecked"}],
            "logic_issues": [],
        }
    ]
    assert aggregate_overall_verdict(sections) == "NotChecked"


def test_aggregate_overall_mixed_partial():
    sections = [
        {"main_claims": [{"verdict": "Correct"}], "logic_issues": []},
        {"main_claims": [{"verdict": "NotChecked"}], "logic_issues": []},
    ]
    assert aggregate_overall_verdict(sections) == "Partial"


@pytest.mark.parametrize(
    "body,expect_ok",
    [
        (
            {
                "success": True,
                "status": "completed",
                "record_id": "abc",
                "result": {"markdown": {"content": "   "}},
            },
            False,
        ),
        (
            {
                "success": True,
                "status": "completed",
                "record_id": "abc",
                "result": {"markdown": {"content": "# Hi\n\nx"}},
            },
            True,
        ),
    ],
)
def test_nanonets_result_dataclass_from_extract(body, expect_ok):
    from modes.research.section_reviewer import parse_nanonets_extract_mock_body

    r = parse_nanonets_extract_mock_body(body)
    assert r.ok is expect_ok
    assert isinstance(r, NanonetsExtractResult)
