"""recognizer 组装与注册表。"""

from __future__ import annotations

from ..types import OFFICER_ID, POSTAL_CODE, QQ_NUMBER, WECHAT_ID, Recognizer
from .chinese import (
    CONTEXT_RECOGNIZERS,
    recognize_officer,
    recognize_postal,
    recognize_qq,
    recognize_wechat,
)
from .official import CHECKSUM_RECOGNIZERS
from .rules import RULE_RECOGNIZERS

__all__ = [
    "CHECKSUM_RECOGNIZERS",
    "CONTEXT_RECOGNIZERS",
    "RECOGNIZERS",
    "RULE_RECOGNIZERS",
    "Recognizer",
]

RECOGNIZERS: dict[str, Recognizer] = {}
RECOGNIZERS.update(CHECKSUM_RECOGNIZERS)
RECOGNIZERS.update(RULE_RECOGNIZERS)
RECOGNIZERS.update(CONTEXT_RECOGNIZERS)
RECOGNIZERS.update(
    {
        POSTAL_CODE: recognize_postal,
        QQ_NUMBER: recognize_qq,
        WECHAT_ID: recognize_wechat,
        OFFICER_ID: recognize_officer,
    }
)
