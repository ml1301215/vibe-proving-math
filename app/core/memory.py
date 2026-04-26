"""LATRACE 记忆客户端。

优化记录：
  - 每个 MemoryClient 实例持有单一 httpx.AsyncClient（连接池复用）
  - 替换所有 `async with httpx.AsyncClient(...)` 短生命周期模式
  - 错误使用 logging 记录，不再静默吞没

封装 LATRACE REST API 的核心操作：
  - 写入对话（ingest）→ POST /ingest/dialog/v1
  - 检索记忆（retrieve）→ POST /retrieval/dialog/v2
  - 搜索记忆（search）→ POST /search
  - 健康检查 → GET /health

项目隔离通过 memory_domain 实现：
  memory_domain = "project/{project_id}"

用法：
    from core.memory import MemoryClient

    mem = MemoryClient(user_id="user-001")
    await mem.ingest("proj-rudin", [
        {"role": "user", "text": "Sylow 定理是什么？"},
        {"role": "assistant", "text": "Sylow 定理是有限群论中..."},
    ])
    memories = await mem.retrieve("proj-rudin", "Sylow 定理")
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx

from .config import latrace_cfg

logger = logging.getLogger(__name__)
_TENANT_ID_HEADER = "X-Tenant-ID"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_turn(role: str, text: str, seq: int) -> dict:
    return {
        "turn_id": f"t{seq:06d}",
        "role": role,
        "text": text,
        "timestamp_iso": _now_iso(),
    }


class MemoryClient:
    """LATRACE 记忆客户端——持有长生命周期 httpx.AsyncClient 以复用连接。"""

    def __init__(
        self,
        user_id: str = "default-user",
        tenant_id: Optional[str] = None,
    ) -> None:
        cfg = latrace_cfg()
        self._base = cfg["base_url"].rstrip("/")
        self._timeout = cfg.get("timeout", 10)
        self._tenant_id = tenant_id or cfg.get("tenant_id", "vibe-proving")
        self.user_id = user_id
        self._flush_count = 0
        self._turn_seq = 0

        # 持有单一 httpx 客户端，避免每次请求新建 TCP 连接
        self._http = httpx.AsyncClient(
            timeout=self._timeout,
            limits=httpx.Limits(
                max_connections=10,
                max_keepalive_connections=5,
                keepalive_expiry=30,
            ),
        )

    async def aclose(self) -> None:
        """显式关闭连接池（应用关闭时调用）。"""
        await self._http.aclose()

    @property
    def _headers(self) -> dict:
        return {
            _TENANT_ID_HEADER: self._tenant_id,
            "Content-Type": "application/json",
        }

    def _memory_domain(self, project_id: str) -> str:
        return f"project/{project_id}"

    async def health(self) -> dict:
        """检查 LATRACE 服务健康状态。

        即使 LATRACE 返回 4xx/5xx（自身内部问题），
        也尝试读取 JSON body 中的 status 字段，
        而不是直接抛出异常把连通状态标记为 unavailable。
        """
        try:
            resp = await self._http.get(
                f"{self._base}/health", headers=self._headers
            )
            try:
                data = resp.json()
            except Exception:
                data = {}
            # 若 JSON 里有 status 字段就用它，否则根据 HTTP 状态码判断
            if "status" not in data:
                data["status"] = "ok" if resp.status_code < 400 else f"http_{resp.status_code}"
            return data
        except Exception as exc:
            logger.warning("LATRACE health check failed: %s", exc)
            return {"status": "unavailable", "error": str(exc)}

    async def ingest(
        self,
        project_id: str,
        turns: list[dict],
        *,
        llm_policy: str = "best_effort",
    ) -> str:
        """
        异步写入对话 turns 到 LATRACE。
        返回 job_id（约 20s 后 LLM 完成事实提取）。

        turns 格式: [{"role": "user"|"assistant", "text": str}]
        """
        self._flush_count += 1
        session_id = f"vp-{self.user_id}-b{self._flush_count:04d}-{uuid.uuid4().hex[:6]}"
        commit_id = f"commit-{session_id}"

        structured_turns = []
        for t in turns:
            self._turn_seq += 1
            structured_turns.append(
                _make_turn(t["role"], t["text"], self._turn_seq)
            )

        payload = {
            "session_id": session_id,
            "commit_id": commit_id,
            "user_tokens": [self.user_id],
            "memory_domain": self._memory_domain(project_id),
            "turns": structured_turns,
            "llm_policy": llm_policy,
            "client_meta": {
                "user_id": self.user_id,
                "memory_policy": "user",
                "stage2_enabled": True,
                "stage3_extract": True,
                "llm_mode": "platform",
            },
        }

        try:
            resp = await self._http.post(
                f"{self._base}/ingest/dialog/v1",
                headers=self._headers,
                json=payload,
            )
            if resp.status_code in (200, 202):
                return resp.json().get("job_id", "")
            logger.warning("LATRACE ingest returned status %d", resp.status_code)
        except Exception as exc:
            logger.warning("LATRACE ingest failed: %s", exc)
        return ""

    async def retrieve(
        self,
        project_id: str,
        query: str,
        *,
        topk: int = 8,
    ) -> list[dict]:
        """
        检索与 query 相关的历史记忆。
        返回 evidence_details 列表，每条有 text 和 score。
        """
        payload = {
            "query": query,
            "user_tokens": [self.user_id],
            "memory_domain": self._memory_domain(project_id),
            "topk": topk,
            "backend": "tkg",
            "tkg_explain": False,
            "llm_policy": "best_effort",
            "client_meta": {
                "user_id": self.user_id,
                "memory_policy": "user",
                "llm_mode": "platform",
            },
        }

        try:
            resp = await self._http.post(
                f"{self._base}/retrieval/dialog/v2",
                headers=self._headers,
                json=payload,
            )
            if resp.status_code != 200:
                logger.debug("LATRACE retrieve returned %d", resp.status_code)
                return []
            data = resp.json()
            evidence = data.get("evidence_details", [])
            return [e for e in evidence if e.get("score", 0) >= 0.05]
        except Exception as exc:
            logger.debug("LATRACE retrieve failed (non-critical): %s", exc)
            return []

    async def search(
        self,
        project_id: str,
        query: str,
        *,
        topk: int = 20,
    ) -> list[dict]:
        """全量搜索记忆节点（用于调试和记忆面板展示）。"""
        payload = {
            "query": query,
            "topk": topk,
            "expand_graph": False,
            "filters": {
                "user_id": [self.user_id],
                "memory_domain": self._memory_domain(project_id),
            },
        }
        try:
            resp = await self._http.post(
                f"{self._base}/search",
                headers=self._headers,
                json=payload,
            )
            if resp.status_code != 200:
                return []
            hits = resp.json().get("hits", [])
            results = []
            for h in hits:
                entry = h.get("entry", {})
                contents = entry.get("contents", [])
                text = " ".join(str(c) for c in contents[:2]).strip()
                if text:
                    results.append({
                        "score": h.get("score", 0),
                        "text": text,
                        "node_type": (entry.get("metadata") or {}).get("node_type", ""),
                    })
            return results
        except Exception as exc:
            logger.debug("LATRACE search failed (non-critical): %s", exc)
            return []

    def format_memories_for_prompt(self, memories: list[dict]) -> str:
        """将检索到的记忆格式化为注入 system prompt 的文本。"""
        if not memories:
            return ""
        lines = ["【相关历史记忆】"]
        for m in memories[:8]:
            text = m.get("text", "").strip()
            if text:
                lines.append(f"- {text}")
        return "\n".join(lines)


def create_memory_client(user_id: str = "default-user") -> MemoryClient:
    """工厂函数，创建 MemoryClient 实例。"""
    return MemoryClient(user_id=user_id)
