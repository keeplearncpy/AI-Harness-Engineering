"""
Harness Engine — 飞书（Lark）适配器。

通过两种模式接收飞书机器人/应用的消息：

  * webhook  — 事件订阅模式（"将事件发送至开发者服务器"）：
      URL 验证（challenge）、签名校验（X-Lark-Signature）、
      AES-256-CBC 解密（Encrypt Key）、解析 im.message.receive_v1 事件。
  * websocket — 长连接模式（推荐，无需公网 URL）：
      先调用 /callback/ws/endpoint 获取连接地址，
      再收发 connect / ping-pong / event / disconnect 帧，
      事件帧为 protobuf 编码（pbbp2.Frame），需回 ack。

回复通过飞书开放平台 API（im/v1/messages/{message_id}/reply）发送，
使用带过期缓存的 tenant_access_token。

支持多机器人：每个 LarkAdapter 实例对应一个飞书应用，
实例间 token 与长连接完全隔离。

官方文档：
  https://open.feishu.cn/document/ukTMukTMukTM/uYDNxYjL2QTM24iN0EjN
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import math
import re
import time
from typing import Optional

import httpx

from core.config import settings
from core.messaging.base import PlatformAdapter, UnifiedMessage, WebhookResult

log = logging.getLogger("harness.messaging.lark")

# 接收消息事件类型
EVENT_MESSAGE_RECEIVE = "im.message.receive_v1"
EVENT_URL_VERIFICATION = "url_verification"
# 卡片按钮点击事件（用于 CI/CD 审批卡片）
EVENT_CARD_ACTION = "card.action.trigger"

# 长连接接入点发现接口（当前网关协议）。
# 返回的 URL 自带认证信息；connect 帧使用 tenant_access_token。
WS_ENDPOINT_PATH = "/callback/ws/endpoint"

PING_INTERVAL = 45        # 默认心跳间隔，会被接入点返回的 ClientConfig 覆盖
RECONNECT_DELAY = 5       # 断线重连间隔（秒）
TOKEN_EXPIRE_MARGIN = 60  # token 提前多少秒刷新

# 流式回复参数（通过 PATCH 分段更新消息，模拟打字机效果）
STREAM_CHUNK_SIZE = 20     # 每次追加的最小字符数
STREAM_INTERVAL = 0.2      # 追加间隔（秒）
STREAM_MAX_UPDATES = 30    # 最多更新次数（长文本自动放大块大小）


# =============================================================
# pbbp2.Frame 的最小 protobuf wire 编解码
#   Frame  { uint64 SeqID=1; uint64 LogID=2; int32 service=3;
#            int32 method=4; repeated Header headers=5;
#            string payload_encoding=6; string payload_type=7;
#            bytes payload=8; string LogIDNew=9; }
#   Header { string key=1; string value=2; }
# method: 0 = CONTROL（ping/pong...），1 = DATA（event/card...）
# =============================================================

def _pb_varint(value: int) -> bytes:
    out = bytearray()
    while value > 0x7F:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.append(value)
    return bytes(out)


def _pb_read_varint(data: bytes, pos: int):
    result = 0
    shift = 0
    while pos < len(data):
        b = data[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, pos
        shift += 7
    return result, pos


def _pb_field_varint(field: int, value: int) -> bytes:
    return _pb_varint(field << 3) + _pb_varint(value)


def _pb_field_bytes(field: int, data: bytes) -> bytes:
    return _pb_varint((field << 3) | 2) + _pb_varint(len(data)) + data


def parse_lark_frame(raw: bytes) -> dict:
    """
    解析 pbbp2.Frame 为普通字典。

    注意：网关偶尔会用同一字段号发送空的 length-delimited 值
    （例如空的 field 2）。为保证健壮性，标量字段（1/2/3/4）
    只接受 varint wire type，5/8 只接受 length-delimited。
    """
    frame = {"seq_id": 0, "log_id": 0, "service": 0, "method": 0,
             "headers": {}, "payload": b""}
    pos, n = 0, len(raw)
    while pos < n:
        tag, pos = _pb_read_varint(raw, pos)
        field, wt = tag >> 3, tag & 7
        if wt == 0:
            val, pos = _pb_read_varint(raw, pos)
        elif wt == 2:
            length, pos = _pb_read_varint(raw, pos)
            val = raw[pos:pos + length]
            pos += length
        elif wt == 5:
            val = raw[pos:pos + 4]
            pos += 4
        elif wt == 1:
            val = raw[pos:pos + 8]
            pos += 8
        else:
            break

        if wt == 0:
            if field == 1:
                frame["seq_id"] = val
            elif field == 2:
                frame["log_id"] = val
            elif field == 3:
                frame["service"] = val
            elif field == 4:
                frame["method"] = val
        elif wt == 2:
            if field == 5:
                # 解析 Header 子消息
                key = value = ""
                p2, m = 0, len(val)
                while p2 < m:
                    t2, p2 = _pb_read_varint(val, p2)
                    f2, w2 = t2 >> 3, t2 & 7
                    if w2 != 2:
                        break
                    ln, p2 = _pb_read_varint(val, p2)
                    chunk = val[p2:p2 + ln]
                    p2 += ln
                    if f2 == 1:
                        key = chunk.decode("utf-8", "replace")
                    elif f2 == 2:
                        value = chunk.decode("utf-8", "replace")
                if key:
                    frame["headers"][key] = value
            elif field == 8:
                frame["payload"] = val
    return frame


def build_lark_ack_frame(seq_id: int, log_id: int, service: int,
                         headers: dict) -> bytes:
    """构造每个事件所需的 DATA ack 帧（不 ack 网关会重推）。"""
    out = bytearray()
    out += _pb_field_varint(1, seq_id)
    out += _pb_field_varint(2, log_id)
    out += _pb_field_varint(3, service)
    out += _pb_field_varint(4, 1)  # DATA
    for k, v in headers.items():
        item = _pb_field_bytes(1, k.encode()) + _pb_field_bytes(2, v.encode())
        out += _pb_field_bytes(5, item)
    out += _pb_field_bytes(8, b'{"code":200}')
    return bytes(out)


class LarkAdapter(PlatformAdapter):
    """接收飞书应用消息并通过开放平台 API 回复。"""

    platform = "lark"

    def __init__(self, app_id: str = "", app_secret: str = "", name: str = "lark",
                 agent: str = "", verification_token: str = "",
                 encrypt_key: str = "", on_message=None):
        super().__init__(on_message)
        self.name = name                      # 应用名（多机器人区分）
        self.agent = agent                    # 该机器人绑定的处理 agent
        self.on_card_action = None            # 卡片按钮回调（审批等）
        self._app_id = app_id or settings.lark_app_id
        self._app_secret = app_secret or settings.lark_app_secret
        self._verification_token = verification_token or settings.lark_verification_token
        self._encrypt_key = encrypt_key or settings.lark_encrypt_key
        self._client = httpx.AsyncClient(timeout=30)
        self._token: Optional[str] = None
        self._token_expires_at: float = 0.0
        self._ws_task: Optional[asyncio.Task] = None
        self._ping_interval = PING_INTERVAL

    # =============================================================
    # 能力判断
    # =============================================================

    def is_configured(self) -> bool:
        return bool(self._app_id and self._app_secret)

    # =============================================================
    # tenant_access_token（带缓存，按实例隔离）
    # =============================================================

    async def _get_tenant_access_token(self) -> str:
        if self._token and time.time() < self._token_expires_at:
            return self._token

        url = f"{settings.lark_domain}/open-apis/auth/v3/tenant_access_token/internal"
        r = await self._client.post(url, json={
            "app_id": self._app_id,
            "app_secret": self._app_secret,
        })
        r.raise_for_status()
        data = r.json()
        if data.get("code") != 0:
            raise RuntimeError(f"飞书 token 获取失败: {data}")

        self._token = data["tenant_access_token"]
        # expire 单位为秒
        self._token_expires_at = time.time() + int(data.get("expire", 7200)) - TOKEN_EXPIRE_MARGIN
        return self._token

    # =============================================================
    # webhook 模式 — 事件订阅
    # =============================================================

    async def handle_webhook(self, request) -> WebhookResult:
        raw_body = await request.body()
        try:
            body = json.loads(raw_body)
        except Exception:
            return WebhookResult(status="error", status_code=400,
                                 body={"code": 400, "msg": "invalid json"})

        # --- 已开启加密策略（Encrypt Key）的载荷 ---
        if "encrypt" in body:
            if not self._encrypt_key:
                return WebhookResult(status="error", status_code=400,
                                     body={"code": 400, "msg": "未配置 encrypt_key"})
            if not self._verify_signature(request.headers, raw_body):
                return WebhookResult(status="error", status_code=401,
                                     body={"code": 401, "msg": "invalid signature"})
            body = self._decrypt(body["encrypt"])

        # --- URL 验证：原样回传 challenge ---
        if body.get("type") == EVENT_URL_VERIFICATION:
            challenge = body.get("challenge", "")
            log.info(f"[lark:{self.name}] 收到 URL 验证请求")
            return WebhookResult(status="challenge", body={"challenge": challenge})

        # --- 明文模式下校验 Verification Token ---
        if not self._encrypt_key and self._verification_token:
            token = body.get("header", {}).get("token", "")
            if token and token != self._verification_token:
                return WebhookResult(status="error", status_code=401,
                                     body={"code": 401, "msg": "invalid token"})

        # --- 只处理消息事件与卡片动作事件 ---
        event_type = body.get("header", {}).get("event_type", "")
        if event_type == EVENT_CARD_ACTION:
            self._handle_card_action_event(body.get("event", {}))
            return WebhookResult(status="ok", body={"code": 0})
        if event_type != EVENT_MESSAGE_RECEIVE:
            return WebhookResult(status="ignored", body={"code": 0})

        msg = self._parse_message_event(body.get("event", {}))
        if msg is None:
            return WebhookResult(status="ok", body={"code": 0})

        # 在飞书超时前先应答，处理放到后台任务
        if self.on_message:
            asyncio.create_task(self._process(msg))
        return WebhookResult(status="ok", body={"code": 0})

    def _verify_signature(self, headers, raw_body: bytes) -> bool:
        """校验 sha256(timestamp + nonce + encrypt_key + 原始报文) == X-Lark-Signature。"""
        timestamp = headers.get("x-lark-request-timestamp", "")
        nonce = headers.get("x-lark-request-nonce", "")
        signature = headers.get("x-lark-signature", "")
        if not (timestamp and nonce and signature):
            return False
        content = f"{timestamp}{nonce}{self._encrypt_key}".encode() + raw_body
        expected = hashlib.sha256(content).hexdigest()
        return hmac.compare_digest(expected, signature)

    def _decrypt(self, ciphertext: str) -> dict:
        """AES-256-CBC 解密（key = sha256(encrypt_key)，iv = 前 16 字节）。"""
        from Crypto.Cipher import AES
        raw = base64.b64decode(ciphertext)
        key = hashlib.sha256(self._encrypt_key.encode()).digest()
        iv = raw[:AES.block_size]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        plain = cipher.decrypt(raw[AES.block_size:])
        # 去掉 PKCS7 填充
        pad = plain[-1]
        plain = plain[:-pad]
        return json.loads(plain.decode("utf-8"))

    # =============================================================
    # 事件解析 — 飞书事件 → UnifiedMessage
    # =============================================================

    def _parse_message_event(self, event: dict) -> Optional[UnifiedMessage]:
        message = event.get("message", {}) or {}

        # 忽略机器人自己发的消息（防回环）
        sender = event.get("sender", {}) or {}
        if sender.get("sender_type") == "app":
            return None
        if (sender.get("sender_id", {}) or {}).get("sender_type") == "app":
            return None

        msg_type = message.get("message_type", "")
        content = self._parse_json(message.get("content", ""))
        if msg_type == "text":
            text = content.get("text", "")
        elif msg_type == "post":
            text = self._extract_post_text(content)
        else:
            text = ""

        text = (text or "").strip()
        if not text:
            return None

        sender_id = sender.get("sender_id", {}) or {}
        mentions = message.get("mentions", []) or []
        return UnifiedMessage(
            platform=self.platform,
            message_id=message.get("message_id", ""),
            chat_id=message.get("chat_id", ""),
            chat_type=message.get("chat_type", ""),
            text=text,
            user_id=sender_id.get("open_id", "") or sender_id.get("user_id", ""),
            user_name=sender_id.get("name", ""),
            reply_to_message_id=message.get("parent_id", ""),
            mentioned_bot=bool(mentions),
            timestamp=message.get("create_time", ""),
            app_id=self._app_id,
            agent=self.agent,
            raw=event,
        )

    @staticmethod
    def _extract_post_text(content: dict) -> str:
        """把富文本 post 消息压平成纯文本。"""
        parts = []
        for line in content.get("content", []) or []:
            for seg in line:
                if isinstance(seg, dict) and seg.get("tag") == "text":
                    parts.append(seg.get("text", ""))
        return "\n".join(parts).strip()

    # =============================================================
    # 卡片动作事件（CI/CD 审批等）
    # =============================================================

    def _handle_card_action_event(self, event: dict):
        """
        card.action.trigger 事件：提取按钮 value 交给 on_card_action 回调。

        value 由发卡片方决定，约定为 dict（如 {"run_id":..., "approved": true}）。
        """
        action = event.get("action", {}) or {}
        value = action.get("value", {}) or {}
        if isinstance(value, str):
            value = self._parse_json(value)
        if not isinstance(value, dict) or not value:
            log.debug(f"[lark:{self.name}] 卡片动作无有效 value，忽略")
            return
        if self.on_card_action:
            asyncio.create_task(self.on_card_action(value))
        else:
            log.warning(f"[lark:{self.name}] 收到卡片动作但未绑定 on_card_action")

    # =============================================================
    # 回复 — 走开放平台 API
    # =============================================================

    async def send_reply(self, msg: UnifiedMessage, text: str) -> bool:
        if not msg.message_id:
            return False
        # 含 Markdown 表格 → 卡片表格渲染（一次发送）
        if self._contains_markdown_table(text):
            ok = await self._send_card_reply(msg, text)
            if ok:
                return True
            log.warning(f"[lark:{self.name}] 卡片发送失败，降级为流式文本")
        # 纯文本 → 流式输出（打字机效果）
        return await self._send_stream_text_reply(msg, text)

    # =============================================================
    # 出站通知 — 主动向会话发消息（无需被回复的消息）
    # =============================================================

    async def send_message(self, chat_id: str, msg_type: str, content: str) -> bool:
        """主动向会话发送消息（用于出站通知 / 审批卡片）。"""
        if not chat_id or not self.is_configured():
            return False
        try:
            token = await self._get_tenant_access_token()
            r = await self._client.post(
                f"{settings.lark_domain}/open-apis/im/v1/messages",
                params={"receive_id_type": "chat_id"},
                headers={"Authorization": f"Bearer {token}",
                         "Content-Type": "application/json; charset=utf-8"},
                json={"receive_id": chat_id, "msg_type": msg_type, "content": content},
            )
            data = r.json()
            if data.get("code") != 0:
                log.error(f"[lark:{self.name}] 主动发送失败: {data}")
                return False
            return True
        except Exception as e:
            log.error(f"[lark:{self.name}] 主动发送异常: {e}")
            return False

    async def send_markdown(self, chat_id: str, text: str) -> bool:
        """以 markdown 卡片向会话发送文本（出站通知）。"""
        return await self.send_message(chat_id, "interactive", self._markdown_card(text))

    async def _reply_api(self, msg: UnifiedMessage, payload: dict) -> Optional[dict]:
        """调用 reply 接口，返回响应体（失败返回 None）。"""
        try:
            token = await self._get_tenant_access_token()
            r = await self._client.post(
                f"{settings.lark_domain}/open-apis/im/v1/messages/{msg.message_id}/reply",
                headers={"Authorization": f"Bearer {token}",
                         "Content-Type": "application/json; charset=utf-8"},
                json=payload,
            )
            data = r.json()
            if data.get("code") != 0:
                log.error(f"[lark:{self.name}] 回复失败: {data}")
                return None
            return data
        except Exception as e:
            log.error(f"[lark:{self.name}] 回复异常: {e}")
            return None

    async def _send_stream_text_reply(self, msg: UnifiedMessage, text: str) -> bool:
        """
        流式文本回复：先发占位卡片，再通过 PATCH 分段更新 markdown 内容。
        注意：飞书的编辑消息接口只支持卡片消息，
        因此占位与更新均使用 interactive 卡片 + markdown 元素。
        需要应用开通权限：im:message:update（更新应用自己发送的消息）。
        """
        placeholder = self._markdown_card("...")
        data = await self._reply_api(msg, {
            "msg_type": "interactive",
            "content": placeholder,
        })
        if not data:
            return False
        message_id = (data.get("data") or {}).get("message_id", "")
        if not message_id:
            return False

        # 计算块大小：长文本减少更新次数
        total = len(text)
        chunk_size = max(STREAM_CHUNK_SIZE, math.ceil(total / STREAM_MAX_UPDATES))
        try:
            token = await self._get_tenant_access_token()
            sent = ""
            for i in range(0, total, chunk_size):
                sent = text[:i + chunk_size]
                r = await self._client.patch(
                    f"{settings.lark_domain}/open-apis/im/v1/messages/{message_id}",
                    headers={"Authorization": f"Bearer {token}",
                             "Content-Type": "application/json; charset=utf-8"},
                    json={"content": self._markdown_card(sent)},
                )
                if r.json().get("code") != 0:
                    raise RuntimeError(f"流式更新失败: {r.json()}")
                await asyncio.sleep(STREAM_INTERVAL)
            return True
        except Exception as e:
            log.error(f"[lark:{self.name}] 流式更新异常: {e}")
            # 兜底：一次性把完整文本更新到占位卡片
            try:
                token = await self._get_tenant_access_token()
                r = await self._client.patch(
                    f"{settings.lark_domain}/open-apis/im/v1/messages/{message_id}",
                    headers={"Authorization": f"Bearer {token}",
                             "Content-Type": "application/json; charset=utf-8"},
                    json={"content": self._markdown_card(text)},
                )
                if r.json().get("code") == 0:
                    return True
            except Exception:
                pass
            # 仍失败则补发一条完整回复
            await self._reply_api(msg, {
                "msg_type": "interactive",
                "content": self._markdown_card(text),
            })
            return False

    @staticmethod
    def _markdown_card(text: str) -> str:
        """构造单 markdown 元素的卡片 JSON 字符串。"""
        card = {
            "config": {"wide_screen_mode": True},
            "elements": [{"tag": "markdown", "content": text}],
        }
        return json.dumps(card, ensure_ascii=False)

    async def _send_card_reply(self, msg: UnifiedMessage, text: str) -> bool:
        """含表格的回复以 interactive 卡片发送（markdown + table 元素）。"""
        card = self._build_table_card(text)
        data = await self._reply_api(msg, {
            "msg_type": "interactive",
            "content": json.dumps(card, ensure_ascii=False),
        })
        return bool(data)

    # -------------------------------------------------------------
    # Markdown 表格检测与卡片构建
    # -------------------------------------------------------------

    @staticmethod
    def _contains_markdown_table(text: str) -> bool:
        lines = text.splitlines()
        for i in range(1, len(lines)):
            if LarkAdapter._is_table_separator(lines[i]) and "|" in lines[i - 1]:
                return True
        return False

    @staticmethod
    def _is_table_separator(line: str) -> bool:
        return bool(re.match(r"^\s*\|?[\s:|-]+\|[\s:|-]*$", line)) and "-" in line

    def _build_table_card(self, text: str) -> dict:
        """把 Markdown（含表格）转成飞书卡片结构。"""
        lines = text.splitlines()
        elements = []
        text_buf: list[str] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            # 表格：上一行是表头，当前行是分隔行
            if (i > 0 and self._is_table_separator(line)
                    and "|" in lines[i - 1]):
                if text_buf and text_buf[-1] == lines[i - 1]:
                    text_buf.pop()
                # 收集表格数据行
                header_line = lines[i - 1]
                rows: list[str] = []
                i += 1
                while i < len(lines) and "|" in lines[i]:
                    rows.append(lines[i])
                    i += 1
                # 刷新普通文本块
                if text_buf:
                    elements.append({"tag": "markdown",
                                     "content": "\n".join(text_buf).strip()})
                    text_buf = []
                elements.append(self._build_table_element(header_line, rows))
                continue
            text_buf.append(line)
            i += 1

        if text_buf:
            elements.append({"tag": "markdown",
                             "content": "\n".join(text_buf).strip()})

        return {"config": {"wide_screen_mode": True}, "elements": elements}

    @staticmethod
    def _table_cells(line: str) -> list[str]:
        return [c.strip() for c in line.strip().strip("|").split("|")]

    def _build_table_element(self, header_line: str, rows: list[str]) -> dict:
        header = self._table_cells(header_line)
        row_cells = [self._table_cells(r) for r in rows]
        width = max([len(header)] + [len(r) for r in row_cells])

        def norm(cells: list[str]) -> list[str]:
            return cells + [""] * (width - len(cells))

        def to_cells(cells: list[str]) -> list[dict]:
            return [{"data": {"tag": "plain_text", "content": c}}
                    for c in norm(cells)]

        return {
            "tag": "table",
            "header": {"cells": to_cells(header)},
            "rows": [{"cells": to_cells(r)} for r in row_cells],
        }

    # =============================================================
    # listener 模式 — 长连接（WebSocket）
    # =============================================================

    async def start_listener(self, on_message) -> Optional[asyncio.Task]:
        if not self.is_configured():
            log.info(f"[lark:{self.name}] 未配置凭证，跳过长连接")
            return None
        if settings.lark_event_mode != "websocket":
            log.info(f"[lark:{self.name}] 事件模式为 '{settings.lark_event_mode}'，跳过长连接")
            return None

        self.on_message = on_message
        self._ws_task = asyncio.create_task(self._ws_loop())
        return self._ws_task

    async def _ws_loop(self):
        """
        维护长连接，自动重连 + 心跳。

        当前网关协议：
          1. POST {domain}/callback/ws/endpoint → 返回带认证的 wss 地址
          2. 连接后立即发送 {"type":"connect","token":...}
          3. 事件帧为 protobuf pbbp2.Frame（method=DATA），必须逐一 ack；
             兼容旧网关的 JSON 帧
          4. 服务端 ping → 回 pong；客户端 ping 保活
        """
        import websockets

        while True:
            try:
                ws_url = await self._get_ws_endpoint()
                token = await self._get_tenant_access_token()
                async with websockets.connect(ws_url, open_timeout=20) as ws:
                    await ws.send(json.dumps({"type": "connect", "token": token}))

                    heartbeat = asyncio.create_task(self._ws_heartbeat(ws))
                    try:
                        async for raw in ws:
                            if await self._handle_ws_frame(ws, raw):
                                break  # 服务端要求断开
                    finally:
                        heartbeat.cancel()
                        await asyncio.gather(heartbeat, return_exceptions=True)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.error(f"[lark:{self.name}] 长连接异常，{RECONNECT_DELAY}s 后重连: {e}")

            await asyncio.sleep(RECONNECT_DELAY)

    async def _get_ws_endpoint(self) -> str:
        """获取长连接 wss 地址（当前网关协议）。"""
        r = await self._client.post(
            f"{settings.lark_domain}{WS_ENDPOINT_PATH}",
            json={"AppID": self._app_id, "AppSecret": self._app_secret},
        )
        data = r.json()
        if data.get("code") != 0:
            raise RuntimeError(f"飞书长连接接入点获取失败: {data}")

        cfg = data.get("data", {}).get("ClientConfig") or {}
        if cfg.get("PingInterval"):
            self._ping_interval = int(cfg["PingInterval"])
        return data["data"]["URL"]

    async def _ws_heartbeat(self, ws):
        while True:
            await asyncio.sleep(self._ping_interval)
            await ws.send(json.dumps({"type": "ping"}))

    async def _handle_ws_frame(self, ws, raw) -> bool:
        """处理一个 ws 帧。返回 True 表示服务端要求断开。"""
        if isinstance(raw, (bytes, bytearray)):
            return await self._handle_ws_proto_frame(ws, bytes(raw))

        try:
            frame = json.loads(raw)
        except Exception:
            log.debug(f"[lark:{self.name}] 无法解析的 ws 帧: {raw[:120]}")
            return False

        ftype = frame.get("type")
        if ftype == "connected":
            log.info(f"[lark:{self.name}] 长连接已建立")
        elif ftype == "connect":
            # 网关对 connect 帧的回显 —— 连接已认证
            log.info(f"[lark:{self.name}] 长连接认证成功（connect 回显）")
        elif ftype == "ping":
            # 服务端心跳请求
            await ws.send(json.dumps({"type": "pong"}))
        elif ftype == "event":
            # 旧网关的 JSON 事件帧（兼容保留）
            data = frame.get("data", {}) or {}
            event_type = data.get("header", {}).get("event_type", "")
            if event_type == EVENT_MESSAGE_RECEIVE:
                msg = self._parse_message_event(data.get("event", {}))
                if msg is not None and self.on_message:
                    asyncio.create_task(self._process(msg))
            elif event_type == EVENT_CARD_ACTION:
                self._handle_card_action_event(data.get("event", {}))
        elif ftype == "disconnect":
            log.warning(f"[lark:{self.name}] 服务端要求断开: {frame.get('reason')}")
            return True
        elif ftype == "pong":
            pass
        else:
            log.debug(f"[lark:{self.name}] 未处理的 ws 帧类型: {ftype}")
        return False

    async def _handle_ws_proto_frame(self, ws, raw: bytes) -> bool:
        """处理 protobuf pbbp2.Frame（当前网关格式）。"""
        try:
            frame = parse_lark_frame(raw)
        except Exception as e:
            log.error(f"[lark:{self.name}] protobuf 帧解析失败: {e}")
            return False

        if frame["method"] != 1:  # CONTROL 帧无需 ack
            return False

        mtype = frame["headers"].get("type", "")
        if mtype != "event":
            log.debug(f"[lark:{self.name}] 忽略的 protobuf 帧类型: {mtype}")
            return False

        if int(frame["headers"].get("sum", "1")) > 1:
            log.warning(f"[lark:{self.name}] 暂不支持分片事件（sum>1），已忽略")
            return False

        # 立即 ack —— 未 ack 的事件会被飞书重推
        try:
            ack = build_lark_ack_frame(
                frame["seq_id"], frame["log_id"], frame["service"], frame["headers"])
            await ws.send(ack)
        except Exception as e:
            log.error(f"[lark:{self.name}] ack 发送失败: {e}")

        payload = frame["payload"]
        if not payload or not payload.startswith(b"{"):
            log.debug(f"[lark:{self.name}] 非 JSON 事件载荷: {payload[:120]}")
            return False

        data = json.loads(payload.decode("utf-8", "replace"))
        event_type = data.get("header", {}).get("event_type", "")
        if event_type == EVENT_MESSAGE_RECEIVE:
            msg = self._parse_message_event(data.get("event", {}))
            if msg is not None and self.on_message:
                asyncio.create_task(self._process(msg))
        elif event_type == EVENT_CARD_ACTION:
            self._handle_card_action_event(data.get("event", {}))
        return False

    # =============================================================
    # 清理
    # =============================================================

    async def close(self):
        if self._ws_task and not self._ws_task.done():
            self._ws_task.cancel()
            await asyncio.gather(self._ws_task, return_exceptions=True)
        await self._client.aclose()
