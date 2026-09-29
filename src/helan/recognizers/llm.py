"""可选：LLM recognizer（任意 OpenAI 兼容 /chat/completions 端点）。

用于规则与校验和覆盖不到的语义级实体（无上下文人名、口语化地址等）。
核心安全阀：模型返回的每个 span 都必须满足偏移不变量
（``text == 原文[start:end]``），不满足的一律丢弃——
不信任模型的坐标，只信任它能逐字引用原文的能力。
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from ..types import ADDRESS, BANK_CARD, ID_CARD, PERSON_NAME, Entity

PROMPT = """你是中文 PII 标注器。从文本中找出以下类型的个人信息：PERSON_NAME(人名), \
ID_CARD(身份证), BANK_CARD(银行卡号), ADDRESS(地址)。只标注明确出现的实体。\
输出 JSON，不要输出其他内容：
{{"entities": [{{"type": "...", "text": "逐字引用原文", "count": 出现序号从1开始}}]}}
文本：
{text}"""


class LLMRecognizerError(RuntimeError):
    pass


class _RetryableError(RuntimeError):
    """429/5xx/网络错误的内部信号：可重试。"""


class LLMRecognizer:
    """调用 OpenAI 兼容端点做语义级 PII 识别。

    偏移对齐策略：模型只负责"逐字引用"，坐标由本地 ``str.find`` 计算；
    第 count 次出现的实体用第 count 次命中位置。引用不到原文的实体丢弃。
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key_env: str = "MIANJU_LLM_API_KEY",
        api_key: str | None = None,
        types: tuple[str, ...] = (PERSON_NAME, ID_CARD, BANK_CARD, ADDRESS),
        timeout: float = 30.0,
        max_chars: int = 3000,
        max_per_second: float = 2.0,
        retries: int = 2,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key if api_key is not None else os.environ.get(api_key_env, "")
        self.types = tuple(types)
        self.timeout = timeout
        self.max_chars = max_chars
        self.max_per_second = max_per_second  # 限速：相邻请求的最小间隔
        self.retries = retries  # 429/5xx/网络错误的指数退避重试次数
        self._last_request_at: float = 0.0

    def _throttle(self) -> None:
        if self.max_per_second <= 0:
            return
        import time

        min_interval = 1.0 / self.max_per_second
        now = time.monotonic()
        wait = self._last_request_at + min_interval - now
        if wait > 0:
            time.sleep(wait)
        self._last_request_at = time.monotonic()

    def _post(self, payload: dict) -> dict:
        import time

        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            self._throttle()
            try:
                return self._post_once(payload)
            except _RetryableError as exc:
                last_error = exc
                time.sleep(0.5 * (2**attempt))  # 指数退避 0.5s/1s/2s...
        assert last_error is not None
        raise LLMRecognizerError(f"重试 {self.retries} 次后仍失败: {last_error}")

    def _post_once(self, payload: dict) -> dict:
        req = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:200]
            if exc.code in (429, 500, 502, 503, 504):
                raise _RetryableError(f"HTTP {exc.code}: {body}") from exc
            raise LLMRecognizerError(f"HTTP {exc.code}: {body}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise _RetryableError(f"请求失败: {exc}") from exc

    def _parse(self, raw: str, text: str) -> list[Entity]:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMRecognizerError(f"模型输出不是合法 JSON: {raw[:120]}") from exc
        out: list[Entity] = []
        cursor: dict[tuple[str, str], int] = {}
        for item in data.get("entities", []):
            etype = item.get("type")
            quoted = item.get("text", "")
            if etype not in self.types or not quoted:
                continue
            key = (etype, quoted)
            nth = cursor.get(key, 0)
            cursor[key] = nth + 1
            pos = -1
            for _ in range(nth + 1):
                pos = text.find(quoted, pos + 1)
                if pos < 0:
                    break
            if pos < 0:
                continue  # 模型没能逐字引用原文 -> 丢弃
            out.append(
                Entity(
                    type=etype,
                    start=pos,
                    end=pos + len(quoted),
                    text=quoted,
                    score=0.8,
                    source="llm",
                    meta={"model": self.model},
                )
            )
        return out

    def __call__(self, text: str) -> list[Entity]:
        out: list[Entity] = []
        for i in range(0, len(text), self.max_chars):
            chunk = text[i : i + self.max_chars]
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": PROMPT.format(text=chunk)}],
                "temperature": 0,
            }
            resp = self._post(payload)
            try:
                content = resp["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as exc:
                raise LLMRecognizerError(f"响应结构异常: {str(resp)[:120]}") from exc
            for e in self._parse(content, chunk):
                out.append(
                    Entity(
                        type=e.type,
                        start=e.start + i,
                        end=e.end + i,
                        text=e.text,
                        score=e.score,
                        source=e.source,
                        meta=e.meta,
                    )
                )
        return out
