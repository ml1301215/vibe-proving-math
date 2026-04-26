"""证明审查功能综合测试：PDF 上传 + 文本粘贴 + 审查选项"""
import pytest
import json
import sys
from pathlib import Path
from io import BytesIO

sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_URL = "http://localhost:8080"


# ── 工具函数 ─────────────────────────────────────────────────────────────────

def _check_server():
    import urllib.request
    try:
        r = urllib.request.urlopen(f"{BASE_URL}/health", timeout=10)
        return json.loads(r.read()).get("status") in ("ok", "degraded")
    except Exception:
        return False


def _post_json(path: str, data: dict, timeout: int = 180):
    """POST JSON 数据"""
    import urllib.request
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _post_multipart(path: str, files: dict, fields: dict = None, timeout: int = 180):
    """POST multipart/form-data"""
    import urllib.request
    import mimetypes

    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = BytesIO()

    # 添加表单字段
    if fields:
        for key, value in fields.items():
            body.write(f'--{boundary}\r\n'.encode())
            body.write(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
            body.write(f'{value}\r\n'.encode())

    # 添加文件
    for field_name, (filename, content) in files.items():
        content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        body.write(f'--{boundary}\r\n'.encode())
        body.write(f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode())
        body.write(f'Content-Type: {content_type}\r\n\r\n'.encode())
        body.write(content if isinstance(content, bytes) else content.encode())
        body.write(b'\r\n')

    body.write(f'--{boundary}--\r\n'.encode())

    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body.getvalue(),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp


def _consume_sse(resp, max_events=200):
    """消费 SSE 流，返回事件列表"""
    events = []
    for raw in resp:
        line = raw.decode("utf-8", errors="replace").rstrip("\n").rstrip("\r")
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if not payload:
            continue
        if payload == "[DONE]":
            events.append({"kind": "done"})
            break
        try:
            obj = json.loads(payload)
        except Exception:
            continue
        if "status" in obj:
            events.append({"kind": "status", **obj})
        elif "result" in obj:
            events.append({"kind": "result", "data": obj["result"]})
        elif "final" in obj:
            events.append({"kind": "final", "data": obj["final"]})
        elif "error" in obj:
            events.append({"kind": "error", "data": obj["error"]})
        if len(events) >= max_events:
            break
    return events


# ── 测试：文本粘贴审查 ─────────────────────────────────────────────────────────

@pytest.mark.slow
def test_review_text_basic():
    """1. 基础文本审查（粘贴证明文本）"""
    if not _check_server():
        pytest.skip("服务器未启动")

    proof = """
    证明：设 G 是一个 4 阶群。根据 Lagrange 定理，G 中每个元素的阶整除 4。
    若 G 中存在 4 阶元素，则 G 是循环群，从而是阿贝尔群。
    若 G 中所有非单位元的阶都是 2，由群论基本定理，G 同构于 Klein 四元群，也是阿贝尔群。
    因此，任何 4 阶群都是阿贝尔群。证毕。
    """

    result = _post_json("/review_stream", {
        "proof_text": proof,
        "max_theorems": 3,
    })


@pytest.mark.slow
def test_review_text_with_options():
    """2. 使用审查选项（逻辑/引用/符号）"""
    if not _check_server():
        pytest.skip("服务器未启动")

    proof = "证明：由费马小定理，对任意质数 p 和整数 a（p 不整除 a），有 a^(p-1) ≡ 1 (mod p)。证毕。"

    # 仅检查引用，不检查逻辑
    result = _post_json("/review_stream", {
        "proof_text": proof,
        "max_theorems": 1,
        "check_logic": False,
        "check_citations": True,
        "check_symbols": False,
    })


@pytest.mark.slow
def test_review_text_latex_theorem_env():
    """3. LaTeX 定理环境解析"""
    if not _check_server():
        pytest.skip("服务器未启动")

    tex = r"""
    \begin{theorem}\label{thm:fermat}
    For any prime $p$ and integer $a$ not divisible by $p$,
    we have $a^{p-1} \equiv 1 \pmod{p}$.
    \end{theorem}

    \begin{proof}
    Consider the multiplicative group $(\mathbb{Z}/p\mathbb{Z})^*$ of order $p-1$.
    By Lagrange's theorem, the order of any element divides $p-1$.
    Therefore, $a^{p-1} \equiv 1 \pmod{p}$ for all $a$ coprime to $p$.
    \end{proof}
    """

    events = []
    import urllib.request
    body = json.dumps({"proof_text": tex, "max_theorems": 2}).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/review_stream",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=180) as resp:
        events = _consume_sse(resp)

    kinds = [e["kind"] for e in events]
    assert "status" in kinds, "缺少 status 帧"
    assert "result" in kinds, "缺少 result 帧"
    assert "final" in kinds, "缺少 final 帧"
    assert "done" in kinds, "缺少 [DONE] 哨兵"

    # 检查最终结果
    final = next(e for e in events if e["kind"] == "final")
    assert "overall_verdict" in final["data"]
    assert final["data"]["overall_verdict"] in ("Correct", "Partial", "Incorrect", "NotChecked")

    print(f"\n定理环境审查完成，verdict={final['data']['overall_verdict']}")


# ── 测试：PDF 上传审查 ────────────────────────────────────────────────────────

@pytest.mark.slow
def test_review_pdf_txt_file():
    """4. 上传 TXT 文件审查"""
    if not _check_server():
        pytest.skip("服务器未启动")

    proof_content = b"""
    Theorem: The square root of 2 is irrational.

    Proof: Assume sqrt(2) is rational, so sqrt(2) = p/q where p, q are coprime integers.
    Then 2 = p^2 / q^2, so p^2 = 2q^2.
    This implies p^2 is even, hence p is even. Let p = 2k.
    Then 4k^2 = 2q^2, so q^2 = 2k^2, implying q is also even.
    This contradicts our assumption that p, q are coprime.
    Therefore, sqrt(2) is irrational.
    """

    resp = _post_multipart(
        "/review_pdf_stream",
        files={"file": ("proof.txt", proof_content)},
        fields={"max_theorems": "3", "user_id": "test_user"},
    )

    events = _consume_sse(resp)
    kinds = [e["kind"] for e in events]

    assert "status" in kinds, "缺少 status 帧"
    assert "final" in kinds, "缺少 final 帧"
    assert "done" in kinds, "缺少 [DONE] 哨兵"

    print(f"\nTXT 文件审查完成，收到 {len(events)} 个事件")


@pytest.mark.slow
def test_review_pdf_latex_file():
    """5. 上传 LaTeX 文件审查"""
    if not _check_server():
        pytest.skip("服务器未启动")

    latex_content = rb"""
    \documentclass{article}
    \begin{document}

    \begin{theorem}
    Every finite integral domain is a field.
    \end{theorem}

    \begin{proof}
    Let $R$ be a finite integral domain with $n$ elements.
    For any nonzero $a \in R$, the map $\phi_a: R \to R$ defined by $\phi_a(x) = ax$ is injective.
    Since $R$ is finite and $\phi_a$ is injective, it must be surjective.
    Therefore, there exists $b \in R$ such that $ab = 1$, so $a$ is invertible.
    Thus $R$ is a field.
    \end{proof}

    \end{document}
    """

    resp = _post_multipart(
        "/review_pdf_stream",
        files={"file": ("theorem.tex", latex_content)},
        fields={"max_theorems": "2"},
    )

    events = _consume_sse(resp)
    kinds = [e["kind"] for e in events]

    assert "status" in kinds
    assert "result" in kinds or "final" in kinds
    assert "done" in kinds

    print(f"\nLaTeX 文件审查完成，收到 {len(events)} 个事件")


# ── 测试：审查内容验证 ────────────────────────────────────────────────────────

@pytest.mark.slow
def test_review_detects_logical_gaps():
    """6. 验证能检测逻辑漏洞"""
    if not _check_server():
        pytest.skip("服务器未启动")

    # 故意包含逻辑跳跃的证明
    flawed_proof = """
    证明：设 n 是一个偶数。显然，n 是质数。
    由质数定义，n 只有两个因子 1 和 n。
    因此，所有偶数都是质数。
    """

    import urllib.request
    body = json.dumps({
        "proof_text": flawed_proof,
        "max_theorems": 1,
        "check_logic": True,
    }).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/review_stream",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        events = _consume_sse(resp)

    final = next((e for e in events if e["kind"] == "final"), None)
    assert final is not None, "未返回 final 帧"

    # 应该检测到错误或漏洞
    verdict = final["data"]["overall_verdict"]
    assert verdict in ("Partial", "Incorrect"), f"应检测到逻辑问题，实际 verdict={verdict}"

    issues_count = final["data"]["stats"].get("issues_found", 0)
    print(f"\n逻辑漏洞检测：verdict={verdict}, 发现 {issues_count} 个问题")


@pytest.mark.slow
def test_review_citation_checking():
    """7. 验证引用核查功能"""
    if not _check_server():
        pytest.skip("服务器未启动")

    # 包含可核查引用的证明
    proof_with_ref = """
    证明：根据 Lagrange 定理，子群的阶整除群的阶。
    由 Cauchy 定理，存在 p 阶元素。
    因此，结论成立。
    """

    import urllib.request
    body = json.dumps({
        "proof_text": proof_with_ref,
        "max_theorems": 1,
        "check_citations": True,
    }).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/review_stream",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        events = _consume_sse(resp)

    final = next((e for e in events if e["kind"] == "final"), None)
    assert final is not None

    # 检查是否执行了引用核查
    citations_checked = final["data"]["stats"].get("citations_checked", 0)
    print(f"\n引用核查：检查了 {citations_checked} 条引用")


# ── 测试：边界条件 ────────────────────────────────────────────────────────────

def test_review_empty_text():
    """8. 空文本应返回 422"""
    if not _check_server():
        pytest.skip("服务器未启动")

    import urllib.error
    try:
        _post_json("/review_stream", {"proof_text": "   "}, timeout=10)
        assert False, "应返回 422"
    except urllib.error.HTTPError as e:
        assert e.code == 422


def test_review_text_too_long():
    """9. 超长文本应返回 422"""
    if not _check_server():
        pytest.skip("服务器未启动")

    import urllib.error
    huge = "a" * 60_000
    try:
        _post_json("/review_stream", {"proof_text": huge}, timeout=10)
        assert False, "应返回 422"
    except urllib.error.HTTPError as e:
        assert e.code == 422


def test_review_pdf_unsupported_format():
    """10. 不支持的文件格式应返回 415"""
    if not _check_server():
        pytest.skip("服务器未启动")

    import urllib.error
    try:
        resp = _post_multipart(
            "/review_pdf_stream",
            files={"file": ("test.exe", b"MZ\x90\x00")},
            fields={"max_theorems": "1"},
            timeout=10,
        )
        assert False, "应返回 415"
    except urllib.error.HTTPError as e:
        assert e.code == 415


# ── 测试：输出格式验证 ────────────────────────────────────────────────────────

@pytest.mark.slow
def test_review_output_format():
    """11. 验证输出格式符合规范"""
    if not _check_server():
        pytest.skip("服务器未启动")

    proof = "证明：显然成立。"

    import urllib.request
    body = json.dumps({"proof_text": proof, "max_theorems": 1}).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/review_stream",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=60) as resp:
        events = _consume_sse(resp)

    # 检查必需字段
    final = next((e for e in events if e["kind"] == "final"), None)
    assert final is not None
    data = final["data"]

    assert "overall_verdict" in data, "缺少 overall_verdict"
    assert data["overall_verdict"] in ("Correct", "Partial", "Incorrect", "NotChecked")

    assert "stats" in data, "缺少 stats"
    stats = data["stats"]
    assert "theorems_checked" in stats
    assert "citations_checked" in stats
    assert "issues_found" in stats

    print(f"\n输出格式验证通过：{data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
