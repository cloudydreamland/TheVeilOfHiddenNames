"""主流水线：recognize / mask / restore。

mask 的替换从后往前做，天然保证前面替换不影响后面实体的偏移。
"""

from __future__ import annotations

import warnings

from .operators import OPERATORS
from .recognizers import RECOGNIZERS
from .resolver import resolve
from .types import ALL_TYPES, ENTITY_GROUPS, Entity, Recognizer, resolve_types
from .vault import Vault

_JIEBA_NOTICE_SHOWN = False  # 每进程只提醒一次

# 各类型默认算子：对中文场景按"可用性优先"选择（partial 保留格式可读性）
DEFAULT_OPS: dict[str, str] = {
    "PERSON_NAME": "partial",
    "ID_CARD": "partial",
    "BANK_CARD": "partial",
    "USCC": "partial",
    "PASSPORT": "partial",
    "PHONE": "partial",
    "LANDLINE": "partial",
    "EMAIL": "partial",
    "IP_ADDRESS": "redact",
    "URL": "redact",
    "LICENSE_PLATE": "partial",
    "ADDRESS": "redact",
    "POSTAL_CODE": "redact",
    "QQ_NUMBER": "partial",
    "WECHAT_ID": "partial",
    "TW_ID_CARD": "partial",
    "OFFICER_ID": "redact",
}


def build_recognizers(
    types: list[str] | tuple[str] | None = None,
    *,
    jieba: bool = False,
    llm_recognizer=None,
) -> list[Recognizer]:
    """组装 recognizer 列表。

    types 默认全部内置类型。
    jieba 默认**关闭**（实测依据，2026-09-27，内置语料：PERSON 召回不变 1.000，
    但 P 1.000→0.700——"温馨提示/张江路/双肩包"均被 jieba 标为 nr 人名）。
    需要 NER 补召回时显式 `jieba=True` 并自担精度损失；见 benchmarks/results.md。
    llm_recognizer 显式传入才启用。
    """
    global _JIEBA_NOTICE_SHOWN

    resolved = resolve_types(types)
    selected = set(resolved) if resolved else set(ALL_TYPES)

    out: list[Recognizer] = []
    for etype, fn in RECOGNIZERS.items():
        if etype in selected:
            out.append(fn)

    if not jieba and "PERSON_NAME" in selected:
        from .recognizers import ner_jieba

        if ner_jieba.available() and not _JIEBA_NOTICE_SHOWN:
            _JIEBA_NOTICE_SHOWN = True
            warnings.warn(
                "检测到已安装 jieba 但默认未启用（实测 P 1.000→0.700，见 benchmarks/results.md）。"
                "需要 NER 补召回请显式传 jieba=True。",
                UserWarning,
                stacklevel=3,
            )
    if jieba and "PERSON_NAME" in selected:
        from .recognizers import ner_jieba

        out.append(ner_jieba.make_jieba_person_recognizer())
    if llm_recognizer is not None:
        out.append(llm_recognizer)
    return out


def recognize(
    text: str,
    types: list[str] | tuple[str] | None = None,
    *,
    recognizers: list[Recognizer] | None = None,
    min_score: float = 0.5,
    jieba: bool = False,
    llm_recognizer=None,
) -> list[Entity]:
    """识别文本中的个人信息，返回消解冲突后、按位置排序的实体列表。"""
    if not text:
        return []
    recs = recognizers if recognizers is not None else build_recognizers(
        types, jieba=jieba, llm_recognizer=llm_recognizer
    )
    raw: list[Entity] = []
    for fn in recs:
        raw.extend(fn(text))
    return resolve(raw, min_score=min_score)


def mask(
    text: str,
    ops: dict[str, str] | None = None,
    types: list[str] | tuple[str] | None = None,
    *,
    min_score: float = 0.5,
    salt: str = "helan",
    vault: Vault | None = None,
    recognizers: list[Recognizer] | None = None,
    jieba: bool = False,
    llm_recognizer=None,
) -> tuple[str, Vault]:
    """脱敏：返回 (masked_text, vault)。

    ops: {entity_type: "redact"|"partial"|"hash"|"fake"|"vault"|callable}。
    "vault" 用占位符替换并可由 restore 精确还原；其余为不可逆替换。
    """
    op_map = dict(DEFAULT_OPS)
    if ops:
        expanded_ops: dict[str, str] = {}
        for key, value in ops.items():
            targets = ENTITY_GROUPS.get(key, (key,))
            for target in targets:
                expanded_ops[target] = value
        unknown_ops = set(expanded_ops) - set(DEFAULT_OPS)
        if unknown_ops:
            raise ValueError(f"未知实体类型(ops): {sorted(unknown_ops)}")
        op_map.update(expanded_ops)

    entities = recognize(
        text,
        types,
        min_score=min_score,
        recognizers=recognizers,
        jieba=jieba,
        llm_recognizer=llm_recognizer,
    )

    if vault is None:
        vault = Vault()

    out = text
    for entity in reversed(entities):  # 从后往前替换，偏移不失真
        op_name = op_map.get(entity.type, "redact")
        if op_name == "vault":
            replacement = vault.place(entity.type, entity.text)
        elif callable(op_name):
            replacement = op_name(entity, salt=salt)
        elif op_name in OPERATORS:
            replacement = OPERATORS[op_name](entity, salt=salt)
        else:
            raise ValueError(f"未知算子: {op_name!r}（可用: {sorted(OPERATORS)} + vault/callable）")
        out = out[: entity.start] + replacement + out[entity.end :]
    return out, vault


def restore(masked_text: str, vault: Vault) -> str:
    """用 vault 把占位符精确还原为原文。"""
    return vault.restore(masked_text)
