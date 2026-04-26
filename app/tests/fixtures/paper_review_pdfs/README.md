# 论文审查 PDF 测试数据（可选）

本目录**不包含**受版权保护的论文 PDF。开源仓库中相关集成测试已标记为 `@pytest.mark.slow`，并在缺少文件时自动跳过。

若需在本地跑完整 PDF 解析回归，请自行将合法获得的 PDF 放入本目录，文件名需与测试用例一致，例如：

- `lll_elementary_2026_arxiv.pdf`
- `szemeredi_finitary_2004_arxiv.pdf`
- `proof_course_notes_2026_arxiv.pdf`
- `green_tao_primes_ap_2008_annals.pdf`
- `sphere_packing_24_2017_annals.pdf`

然后执行：

```bash
cd app
pytest tests/test_paper_review_agent.py -m slow -v
```

请勿将无权分发的 PDF 提交到公开仓库。
