"""recognizer 公共工具：带边界守卫的正则匹配。"""

from __future__ import annotations

import re

from ..types import Entity

# 守卫字符：匹配两侧不得出现这些字符，防止从更长 token 内部切出一半
_DIGIT_GUARD = "0-9"
_ALNUM_GUARD = "0-9A-Za-z"
_CS_GUARD = "0-9A-HJ-NP-RTUWXY"


def guarded_pattern(pattern: str, *, left: str = _DIGIT_GUARD, right: str | None = None) -> re.Pattern[str]:
    """在 pattern 外侧包一层负向断言。默认两侧都是数字守卫。"""
    right = _DIGIT_GUARD if right is None else right
    return re.compile(rf"(?<![{left}])(?:{pattern})(?![{right}])")


def make(entity_type: str, match: re.Match[str], score: float, source: str, **meta) -> Entity:
    start, end = match.span()
    return Entity(
        type=entity_type,
        start=start,
        end=end,
        text=match.group(0),
        score=score,
        source=source,
        meta=meta,
    )
