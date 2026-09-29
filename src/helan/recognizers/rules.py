"""格式规则类 recognizer：邮箱 / IP / URL / 座机 / 车牌 / 护照。"""

from __future__ import annotations

import re

from ..data import LANDLINE_AREA_CODES, PLATE_PROVINCES
from ..types import (
    EMAIL,
    IP_ADDRESS,
    LANDLINE,
    LICENSE_PLATE,
    PASSPORT,
    URL,
    Entity,
)
from .base import guarded_pattern, make

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")

_IPV4_RE = guarded_pattern(
    r"(?:\d{1,3}\.){3}\d{1,3}", left="0-9.", right="0-9"
)

# 512 上限:正常 URL 不受影响,同时约束实体最大长度(流式 overlap 的前提)
_URL_RE = re.compile(r"https?://[^\s<>\"'，。；！？、]{1,512}")

_LANDLINE_RE = guarded_pattern(r"0\d{2,3}-?[2-9]\d{6,7}")

_PLATE_RE = re.compile(
    rf"[{PLATE_PROVINCES}][A-HJ-NP-Z][·•]?(?:[A-HJ-NP-Z0-9]{{5,6}})"
)

_PASSPORT_RE = guarded_pattern(r"[EGDSPh]\d{8}", left="0-9A-Za-z", right="0-9A-Za-z")

_TRAILING_PUNCT = "。，,;；!！?？、）)】》\"'"


def recognize_email(text: str) -> list[Entity]:
    out = []
    for m in _EMAIL_RE.finditer(text):
        local = m.group(0).split("@")[0]
        if not local or local.startswith(".") or local.endswith("."):
            continue
        out.append(make(EMAIL, m, 0.9, "rule"))
    return out


def _ipv4_octets_ok(value: str) -> bool:
    return all(0 <= int(o) <= 255 for o in value.split("."))


def recognize_ip(text: str) -> list[Entity]:
    out = []
    for m in _IPV4_RE.finditer(text):
        value = m.group(0)
        if _ipv4_octets_ok(value):
            out.append(make(IP_ADDRESS, m, 0.9, "rule"))
    return out


def recognize_url(text: str) -> list[Entity]:
    out = []
    for m in _URL_RE.finditer(text):
        value = m.group(0)
        trimmed = value.rstrip(_TRAILING_PUNCT)
        out.append(make(URL, m, 0.9, "rule", trimmed_len=len(trimmed)))
    return out


def recognize_landline(text: str) -> list[Entity]:
    """区号有 2/3 位两种长度，正则无法决定切分；按区号表逐一尝试。"""
    out = []
    for m in _LANDLINE_RE.finditer(text):
        digits = m.group(0).replace("-", "")
        for k in (2, 3):
            if digits[1 : 1 + k] in LANDLINE_AREA_CODES:
                rest = digits[1 + k :]
                if 7 <= len(rest) <= 8:
                    out.append(make(LANDLINE, m, 0.85, "rule", area=digits[: 1 + k]))
                    break
    return out


def recognize_plate(text: str) -> list[Entity]:
    return [make(LICENSE_PLATE, m, 0.85, "rule") for m in _PLATE_RE.finditer(text)]


def recognize_passport(text: str) -> list[Entity]:
    return [make(PASSPORT, m, 0.85, "rule") for m in _PASSPORT_RE.finditer(text)]


# 类型 -> recognizer 注册表（rules 组）
RULE_RECOGNIZERS = {
    EMAIL: recognize_email,
    IP_ADDRESS: recognize_ip,
    URL: recognize_url,
    LANDLINE: recognize_landline,
    LICENSE_PLATE: recognize_plate,
    PASSPORT: recognize_passport,
}
