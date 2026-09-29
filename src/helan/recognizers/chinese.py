"""中文上下文 recognizer：人称谓/引导词人名 + 地址。

诚实声明：不依赖分词器的零依赖实现是**精确优先**的——只在高置信上下文
（称谓、引导词）中识别人名与地址，召回有限；装了 jieba 可自动获得
`nr` 词性识别器补召回，见 ner_jieba.py。
"""

from __future__ import annotations

import re

from ..data import (
    ADDRESS_HEADS,
    ADDRESS_KEYS,
    ADDRESS_TAILS,
    HONORIFICS,
    LEAD_WORDS,
    OFFICER_KEYS,
    PERSON_NAME_BLOCKLIST,
    POSTAL_KEYS,
    QQ_KEYS,
    SURNAMES,
    WECHAT_KEYS,
)
from ..types import ADDRESS, OFFICER_ID, PERSON_NAME, POSTAL_CODE, QQ_NUMBER, WECHAT_ID, Entity

# 称谓后置：张伟明先生 / 王女士 / 谷思 女士（称谓不入 span，允许名字与称谓间空白）
_HONORIFIC_ALT = "|".join(HONORIFICS)
_NAME_AFTER_HONORIFIC = re.compile(
    rf"(?<![0-9A-Za-z])([{SURNAMES}])([\u4e00-\u9fff]{{1,2}})(?=\s*(?:{_HONORIFIC_ALT}))"
)

# 引导词前置：联系人：张伟 / 患者王建国 / 出租方（甲方）：张伟明 / 检查员为成杰怡
_LEAD_ALT = "|".join(LEAD_WORDS)
_NAME_AFTER_LEAD = re.compile(
    rf"(?:{_LEAD_ALT})\s*(?:（[^）]{{1,12}}）)?\s*(?:[:：]|为)?\s*"
    rf"([{SURNAMES}])([\u4e00-\u9fff]{{1,2}})(?![\u4e00-\u9fff])"
)

# 顿号枚举中的后续人名：出席：石天雪、牟玉 （前有顿号/逗号，后有边界）
_NAME_IN_ENUM = re.compile(
    rf"(?<=[、，])\s*([{SURNAMES}])([\u4e00-\u9fff]{{1,2}})(?![\u4e00-\u9fff])"
)

# 地址：引导词后到句读的一段，内含至少一个地址尾词
_ADDR_KEY_ALT = "|".join(ADDRESS_KEYS)
_ADDR_HEAD_ALT = "|".join(ADDRESS_HEADS)
_ADDR_RE = re.compile(
    rf"(?:{_ADDR_KEY_ALT}|{_ADDR_HEAD_ALT})\s*[:：]?\s*"
    rf"([\u4e00-\u9fffA-Za-z0-9()（）-]{{8,60}}?)(?=[。；;！!？?\n，,]|$)"
)


def _blocked(text: str, start: int, end: int) -> bool:
    value = text[start:end]
    return value in PERSON_NAME_BLOCKLIST or value[:2] in PERSON_NAME_BLOCKLIST


def recognize_person(text: str) -> list[Entity]:
    out: list[Entity] = []
    seen: set[tuple[int, int]] = set()

    for m in _NAME_AFTER_HONORIFIC.finditer(text):
        start = m.start()
        end = m.end()
        if (start, end) in seen:
            continue
        seen.add((start, end))
        out.append(
            Entity(
                type=PERSON_NAME,
                start=start,
                end=end,
                text=m.group(0),
                score=0.7,
                source="context",
                meta={"cue": "honorific"},
            )
        )
    for m in _NAME_AFTER_LEAD.finditer(text):
        # 引导词后的姓名：span 只含姓名本身
        start, end = m.span(1)[0], m.end()
        if (start, end) in seen:
            continue
        seen.add((start, end))
        out.append(
            Entity(
                type=PERSON_NAME,
                start=start,
                end=end,
                text=text[start:end],
                score=0.7,
                source="context",
                meta={"cue": "lead_word"},
            )
        )
    for m in _NAME_IN_ENUM.finditer(text):
        start, end = m.span(1)[0], m.end()
        if (start, end) in seen or _blocked(text, start, end):
            continue
        seen.add((start, end))
        out.append(
            Entity(
                type=PERSON_NAME,
                start=start,
                end=end,
                text=text[start:end],
                score=0.6,
                source="context",
                meta={"cue": "enumeration"},
            )
        )
    return out


def recognize_address(text: str) -> list[Entity]:
    out: list[Entity] = []
    for m in _ADDR_RE.finditer(text):
        value_start = m.start(1)
        value_end = m.end(1)
        value = m.group(1)
        if not any(tail in value for tail in ADDRESS_TAILS):
            continue
        out.append(
            Entity(
                type=ADDRESS,
                start=value_start,
                end=value_end,
                text=value,
                score=0.6,
                source="context",
                meta={"cue": "address_key"},
            )
        )
    return out


CONTEXT_RECOGNIZERS = {
    PERSON_NAME: recognize_person,
    ADDRESS: recognize_address,
}


# 邮编：关键词 + 6 位数字（无校验和，纯上下文口径）
_POSTAL_RE = re.compile(
    rf"(?:{'|'.join(POSTAL_KEYS)})\s*[:：]?\s*(\d{{6}})(?!\d)"
)


def recognize_postal(text: str) -> list[Entity]:
    out = []
    for m in _POSTAL_RE.finditer(text):
        out.append(
            Entity(
                type=POSTAL_CODE,
                start=m.start(1),
                end=m.end(1),
                text=m.group(1),
                score=0.85,
                source="context",
                meta={"cue": "postal_key"},
            )
        )
    return out


# QQ 号：关键词 + 5-11 位数字（首位非 0）
_QQ_RE = re.compile(
    rf"(?:{'|'.join(QQ_KEYS)})\s*[号]?\s*[:：]?\s*([1-9]\d{{4,10}})(?!\d)"
)


def recognize_qq(text: str) -> list[Entity]:
    out = []
    for m in _QQ_RE.finditer(text):
        out.append(
            Entity(
                type=QQ_NUMBER,
                start=m.start(1),
                end=m.end(1),
                text=m.group(1),
                score=0.85,
                source="context",
                meta={"cue": "qq_key"},
            )
        )
    return out


# 微信号：关键词 + 6-20 位字母开头（官方规则：字母开头，含数字/下划线/减号）
_WECHAT_RE = re.compile(
    rf"(?:{'|'.join(WECHAT_KEYS)})\s*[:：]?\s*([A-Za-z][-_A-Za-z0-9]{{5,19}})"
)


def recognize_wechat(text: str) -> list[Entity]:
    out = []
    for m in _WECHAT_RE.finditer(text):
        out.append(
            Entity(
                type=WECHAT_ID,
                start=m.start(1),
                end=m.end(1),
                text=m.group(1),
                score=0.85,
                source="context",
                meta={"cue": "wechat_key"},
            )
        )
    return out


# 军官证：关键词 + 6-12 位数字/大写字母（无公开校验和，format-only，如实标注）
_OFFICER_RE = re.compile(
    rf"(?:{'|'.join(OFFICER_KEYS)})\s*[:：号]?\s*(?:第|No\.?)?\s*([0-9A-Z]{{6,12}})(?![0-9A-Za-z])"
)


def recognize_officer(text: str) -> list[Entity]:
    out = []
    for m in _OFFICER_RE.finditer(text):
        out.append(
            Entity(
                type=OFFICER_ID,
                start=m.start(1),
                end=m.end(1),
                text=m.group(1),
                score=0.6,
                source="context",
                meta={"cue": "officer_key", "format_only": True},
            )
        )
    return out
