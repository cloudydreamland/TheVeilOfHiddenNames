"""校验和级 recognizer：身份证 / 银行卡 / 统一社会信用代码。

原则：宁缺勿滥。这类实体只有通过官方校验算法才上报——
校验失败的候选串直接丢弃，而不是降级为低分命中（降级会引入大量误报，
对脱敏场景而言，误报的代价（破坏原文可用性）高于漏报）。
"""

from __future__ import annotations

import re

from .. import checksum
from ..data import MOBILE_SEGMENTS
from ..types import BANK_CARD, ID_CARD, PHONE, TW_ID_CARD, USCC, Entity
from .base import guarded_pattern, make

_ID18_RE = guarded_pattern(r"\d{17}[0-9Xx]")
_ID15_RE = guarded_pattern(r"\d{15}")

_MOBILE_RE = guarded_pattern(r"1[3-9]\d{9}")

# 大陆身份证全角/符号分隔写法：1101 0519 4912 3100 2X / 1101·0519·4912·3100·2X
_ID_GROUPED_RE = guarded_pattern(r"\d{4}(?:[ 　.．·•-]\d{4}){3}[ 　.．·•-]\d[0-9Xx]")

_TW_ID_RE = re.compile(r"(?<![0-9A-Za-z])([A-Z])([12]\d{8})(?![0-9A-Za-z])", re.IGNORECASE)

# 连续 13-19 位数字；或 4 位一组、空格/连字符分隔（银行卡常见写法）
# 右守卫含 Xx：防止 17 位身份证前缀 + X 校验位被当作银行卡
_BANK_CONTIGUOUS_RE = guarded_pattern(r"\d{13,19}", right="0-9Xx")
_BANK_GROUPED_RE = guarded_pattern(r"\d{4}(?:[ -]\d{4}){2,4}", right="0-9Xx")

_USCC_RE = guarded_pattern(
    r"[0-9A-HJ-NP-RTUWXY]{18}", left="0-9A-Za-z", right="0-9A-Za-z"
)


def recognize_id_card(text: str) -> list[Entity]:
    out = []
    for m in _ID18_RE.finditer(text):
        value = m.group(0)
        if checksum.id_card_valid(value):
            out.append(make(ID_CARD, m, 0.95, "checksum"))
    for m in _ID_GROUPED_RE.finditer(text):
        normalized = re.sub(r"[ 　.．·•-]", "", m.group(0))
        if checksum.id_card_valid(normalized):
            out.append(make(ID_CARD, m, 0.95, "checksum", normalized=normalized))
    for m in _ID15_RE.finditer(text):
        value = m.group(0)
        if any(e.start <= m.start() and e.end >= m.end() for e in out):
            continue  # 已被 18 位命中覆盖
        if checksum.id_card_15_valid(value):
            upgraded = checksum.id_card_upgrade_15(value)
            out.append(
                make(
                    ID_CARD,
                    m,
                    0.8,
                    "rule",
                    legacy15=True,
                    upgraded=upgraded,
                )
            )
    return out


def recognize_bank_card(text: str) -> list[Entity]:
    out = []
    seen_spans: set[tuple[int, int]] = set()

    def _add(m: re.Match[str]) -> None:
        span = m.span()
        if span in seen_spans:
            return
        value = re.sub(r"[ -]", "", m.group(0))
        if checksum.luhn_valid(value):
            seen_spans.add(span)
            out.append(make(BANK_CARD, m, 0.95, "checksum", normalized=value))

    for m in _BANK_CONTIGUOUS_RE.finditer(text):
        _add(m)
    for m in _BANK_GROUPED_RE.finditer(text):
        _add(m)
    return out


def recognize_uscc(text: str) -> list[Entity]:
    out = []
    for m in _USCC_RE.finditer(text):
        value = m.group(0)
        if checksum.uscc_valid(value):
            out.append(make(USCC, m, 0.95, "checksum"))
    return out


def recognize_phone(text: str) -> list[Entity]:
    """手机号：号段表严格校验（号段表随时间校准，见 data.MOBILE_SEGMENTS）。"""
    out = []
    for m in _MOBILE_RE.finditer(text):
        value = m.group(0)
        if value[:3] in MOBILE_SEGMENTS:
            out.append(make(PHONE, m, 0.9, "rule"))
    return out


def recognize_tw_id_card(text: str) -> list[Entity]:
    out = []
    for m in _TW_ID_RE.finditer(text):
        value = m.group(0).upper()
        if checksum.tw_id_valid(value):
            out.append(make(TW_ID_CARD, m, 0.95, "checksum"))
    return out


CHECKSUM_RECOGNIZERS = {
    ID_CARD: recognize_id_card,
    TW_ID_CARD: recognize_tw_id_card,
    BANK_CARD: recognize_bank_card,
    USCC: recognize_uscc,
    PHONE: recognize_phone,
}
