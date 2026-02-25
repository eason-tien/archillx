"""
ArcHillx — WebSocket Event Broadcaster — V5.1
=============================================
改进 / Improvements:
  1. schema_version: "v1"  每条事件携带协议版本，保护旧客户端向前兼容
  2. Backpressure 可观测指标：
       queue_len        当前队列深度
       dropped_total    因队列满被丢弃的消息总数
       disconnect_reason 最后断线原因（"queue_full" | "ws_error" | "client_close"）
  3. Global 统计：total_broadcast / total_dropped

连接方式 / Connection:
    ws://host:8000/ws/events?token=<admin_token>

事件格式 / Event format (JSON):
    {
        "schema_version": "v1",
        "event":   "RISK_HIGH",
        "ts":      "2026-02-21T10:00:00Z",
        "lang":    "zh-CN",
        "message": "...",
        "data":    { ... }
    }
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Dict, Optional
from fastapi import WebSocket, WebSocketDisconnect

# ── Config ─────────────────────────────────────────────────────────────────
_MAX_CLIENTS   = int(  os.getenv("AH_WS_MAX_CLIENTS",  "50"))
_HEARTBEAT_SEC = float(os.getenv("AH_WS_HEARTBEAT",    "20"))
_QUEUE_SIZE    = int(  os.getenv("AH_WS_QUEUE_SIZE",   "100"))

# Protocol version — bump when payload schema changes incompatibly
_SCHEMA_VERSION = "v1"


# ── Per-client wrapper ─────────────────────────────────────────────────────

class _Client:
    """WebSocket connection with its own async queue and observability counters."""

    def __init__(self, ws: WebSocket, client_id: str):
        self.ws               = ws
        self.client_id        = client_id
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=_QUEUE_SIZE)
        self.connected_at     = time.time()
        # ── Backpressure counters ──────────────────────────────────────────
        self.dropped_total    = 0           # messages dropped due to full queue
        self.disconnect_reason: str = ""    # populated on disconnect

    async def enqueue(self, payload: dict) -> bool:
        """Non-blocking enqueue. Returns False (and increments drop counter) if full."""
        try:
            self.queue.put_nowait(payload)
            return True
        except asyncio.QueueFull:
            self.dropped_total += 1
            return False


# ── Broadcaster ─────────────────────────────────────────────────────────────

class WebSocketBroadcaster:
    """
    Singleton broadcaster.

    Public API (called from route handlers):
      connect(ws, client_id)       → register new connection
      disconnect(client_id)        → deregister + clean up
      broadcast(event_type, data)  → push to all clients
      status()                     → observability snapshot
    """

    def __init__(self):
        self._clients: Dict[str, _Client] = {}
        self._lock = asyncio.Lock()
        # Global counters
        self._total_broadcast = 0
        self._total_dropped   = 0

    # ── Connection management ──────────────────────────────────────────────

    async def connect(self, ws: WebSocket, client_id: str) -> bool:
        if len(self._clients) >= _MAX_CLIENTS:
            await ws.close(code=1008, reason="Max clients reached")
            return False
        await ws.accept()
        async with self._lock:
            self._clients[client_id] = _Client(ws, client_id)
        return True

    async def disconnect(self, client_id: str, reason: str = ""):
        async with self._lock:
            client = self._clients.pop(client_id, None)
            if client and reason:
                client.disconnect_reason = reason
            if client:
                # Accumulate global drop stats before removal
                self._total_dropped += client.dropped_total

    # ── Broadcasting ───────────────────────────────────────────────────────

    async def broadcast(
        self,
        event_type:        str,
        data:              dict,
        formatted_message: str  = "",
        lang:              str  = "zh-CN",
    ):
        """
        Push event to all connected clients.
        Payload always includes schema_version for forward-compatibility.
        """
        payload = {
            "schema_version": _SCHEMA_VERSION,
            "event":   event_type,
            "ts":      _utcnow(),
            "lang":    lang,
            "message": formatted_message,
            "data":    data,
        }

        if not self._clients:
            return

        async with self._lock:
            clients = list(self._clients.values())

        self._total_broadcast += 1
        full_clients: list[str] = []

        for client in clients:
            ok = await client.enqueue(payload)
            if not ok:
                full_clients.append(client.client_id)

        # Disconnect clients whose queues have been full (backpressure → drop)
        for cid in full_clients:
            await self.disconnect(cid, reason="queue_full")

    # ── Per-client sender loop ────────────────────────────────────────────

    async def run_sender(self, client_id: str):
        """
        Drain the client queue and send messages via WebSocket.
        Sends periodic heartbeats with schema_version.
        """
        client = self._clients.get(client_id)
        if not client:
            return

        last_hb   = time.time()
        disc_reason = "client_close"

        try:
            while True:
                try:
                    msg = await asyncio.wait_for(
                        client.queue.get(), timeout=_HEARTBEAT_SEC
                    )
                    await client.ws.send_text(json.dumps(msg, ensure_ascii=False))
                except asyncio.TimeoutError:
                    now = time.time()
                    if now - last_hb >= _HEARTBEAT_SEC:
                        try:
                            await client.ws.send_text(json.dumps({
                                "schema_version": _SCHEMA_VERSION,
                                "event": "ping",
                                "ts":    _utcnow(),
                            }))
                            last_hb = now
                        except Exception:
                            disc_reason = "ws_error"
                            break
        except WebSocketDisconnect:
            disc_reason = "client_close"
        except Exception:
            disc_reason = "ws_error"
        finally:
            await self.disconnect(client_id, reason=disc_reason)

    # ── Observability / Status ────────────────────────────────────────────

    def status(self) -> dict:
        """
        Returns detailed observability snapshot.

        Per-client fields:
          id               client UUID
          connected_sec    seconds since connection
          queue_len        current depth (backpressure indicator)
          dropped_total    messages dropped for this client
          disconnect_reason last disconnect reason (empty if still connected)
        """
        clients_info = []
        total_queue_len    = 0
        total_dropped_live = 0

        for cid, c in self._clients.items():
            qlen = c.queue.qsize()
            total_queue_len    += qlen
            total_dropped_live += c.dropped_total
            clients_info.append({
                "id":               cid,
                "connected_sec":    int(time.time() - c.connected_at),
                "queue_len":        qlen,
                "dropped_total":    c.dropped_total,
                "disconnect_reason": c.disconnect_reason,
            })

        return {
            "schema_version":      _SCHEMA_VERSION,
            "active_connections":  len(self._clients),
            "max_clients":         _MAX_CLIENTS,
            "total_broadcast":     self._total_broadcast,
            "total_dropped":       self._total_dropped + total_dropped_live,
            "total_queue_len":     total_queue_len,
            "clients":             clients_info,
        }


# ── Helpers ───────────────────────────────────────────────────────────────

def _utcnow() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Global singleton ──────────────────────────────────────────────────────
broadcaster = WebSocketBroadcaster()
