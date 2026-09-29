"""核心类型定义。

不变量（与 qiegao 同款承诺）：任何 recognizer 产出的 Entity 必须满足
``entity.text == source[entity.start:entity.end]``，由 fuzz 测试永久守护。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

# 实体类型：API 稳定面，只增不改名
PERSON_NAME = "PERSON_NAME"
ID_CARD = "ID_CARD"
BANK_CARD = "BANK_CARD"
USCC = "USCC"  # 统一社会信用代码
PASSPORT = "PASSPORT"
PHONE = "PHONE"  # 手机号
LANDLINE = "LANDLINE"  # 座机
EMAIL = "EMAIL"
IP_ADDRESS = "IP_ADDRESS"
URL = "URL"
LICENSE_PLATE = "LICENSE_PLATE"
ADDRESS = "ADDRESS"
POSTAL_CODE = "POSTAL_CODE"
QQ_NUMBER = "QQ_NUMBER"
WECHAT_ID = "WECHAT_ID"
TW_ID_CARD = "TW_ID_CARD"  # 台湾地区身份证（带校验和）
OFFICER_ID = "OFFICER_ID"  # 军官证（上下文格式，无公开校验和）

ENTITY_TYPES: tuple[str, ...] = (
    PERSON_NAME, ID_CARD, TW_ID_CARD, BANK_CARD, USCC, PASSPORT, PHONE,
    LANDLINE, EMAIL, IP_ADDRESS, URL, LICENSE_PLATE, ADDRESS,
    POSTAL_CODE, QQ_NUMBER, WECHAT_ID, OFFICER_ID,
)
ALL_TYPES = frozenset(ENTITY_TYPES)

# 识别来源等级：checksum > rule > context > ner > llm
SOURCE_WEIGHT = {"checksum": 4, "rule": 3, "context": 2, "ner": 2, "llm": 2}


@dataclass(frozen=True)
class Entity:
    """一段被识别出的个人信息。start/end 为原文字符偏移，左闭右开。"""

    type: str
    start: int
    end: int
    text: str
    score: float
    source: str  # checksum / rule / context / ner / llm
    meta: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.type not in ALL_TYPES:
            raise ValueError(f"unknown entity type: {self.type!r}")
        if self.end - self.start != len(self.text):
            raise ValueError(
                f"offset invariant violated: span {self.end - self.start} != text {len(self.text)}"
            )


# recognizer：text -> 原始（未消解冲突的）实体列表
Recognizer = Callable[[str], list[Entity]]


# 实体组：`types=`/`entities=`/`ops=` 处可直接传组名（iter3 评审产出）
ENTITY_GROUPS: dict[str, tuple[str, ...]] = {
    "ID_LIKE": (ID_CARD, TW_ID_CARD, PASSPORT, OFFICER_ID),
    "CONTACT": (PHONE, LANDLINE, EMAIL, QQ_NUMBER, WECHAT_ID),
    "FINANCE": (BANK_CARD, USCC),
    "ONLINE": (URL, IP_ADDRESS),
}

ALL_TYPES_AND_GROUPS = frozenset(ENTITY_TYPES) | frozenset(ENTITY_GROUPS)


def resolve_types(types) -> tuple[str, ...] | None:
    """把传入的类型/组名解析为具体类型元组；None 原样返回（= 全部）。"""
    if types is None:
        return None
    out: list[str] = []
    for item in types:
        if item in ENTITY_GROUPS:
            out.extend(ENTITY_GROUPS[item])
        elif item in ALL_TYPES:
            out.append(item)
        else:
            raise ValueError(f"未知实体类型或组: {item!r}（可用组: {sorted(ENTITY_GROUPS)}）")
    return tuple(dict.fromkeys(out))
