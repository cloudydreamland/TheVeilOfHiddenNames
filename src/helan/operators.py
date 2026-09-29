"""脱敏算子：redact / partial / fake（+ vault 占位由 pipeline 处理）。

设计原则：
- partial 按中文习惯保留位数（手机前3后4、身份证前3后4、人名保留姓氏）。
- fake 生成**通过本项目校验器**的合法格式假数据——替换后的文本仍可通过
  任何"格式校验"，适合造测试集/演示数据；这是不可逆替换。
- 所有算子只依赖 entity.text，不依赖原文其他部分，保证可组合。
"""

from __future__ import annotations

import hashlib
import random

from . import checksum
from .data import (
    FAKE_BANK_BINS,
    FAKE_EMAIL_DOMAINS,
    FAKE_GIVEN_CHARS,
    FAKE_USCC_PREFIXES,
    MOBILE_SEGMENTS,
    SURNAMES,
)
from .types import Entity

REDACT_LABELS: dict[str, str] = {
    "PERSON_NAME": "[姓名]",
    "ID_CARD": "[身份证号]",
    "BANK_CARD": "[银行卡号]",
    "USCC": "[统一社会信用代码]",
    "PASSPORT": "[护照号]",
    "PHONE": "[手机号]",
    "LANDLINE": "[电话]",
    "EMAIL": "[邮箱]",
    "IP_ADDRESS": "[IP地址]",
    "URL": "[网址]",
    "LICENSE_PLATE": "[车牌号]",
    "ADDRESS": "[地址]",
}


def redact(entity: Entity, **_) -> str:
    return REDACT_LABELS.get(entity.type, "[已脱敏]")


def _mask_keep(value: str, head: int, tail: int) -> str:
    if len(value) <= head + tail:
        return "*" * len(value)
    return value[:head] + "*" * (len(value) - head - tail) + value[len(value) - tail :]


def partial(entity: Entity, **_) -> str:
    """按类型的中文脱敏习惯保留部分字符。"""
    t, v = entity.type, entity.text
    if t == "PHONE":
        return v[:3] + "****" + v[-4:] if len(v) == 11 else _mask_keep(v, 3, 4)
    if t == "ID_CARD":
        return v[:3] + "***********" + v[-4:] if len(v) == 18 else _mask_keep(v, 3, 4)
    if t == "BANK_CARD":
        return _mask_keep(v, 0, 4)
    if t == "PERSON_NAME":
        return v[0] + "*" * (len(v) - 1)
    if t == "EMAIL":
        local, _, domain = v.partition("@")
        head = local[0] if local else "*"
        return f"{head}***@{domain}"
    if t == "LANDLINE":
        return _mask_keep(v, 4, 2)
    if t in ("USCC", "PASSPORT"):
        return _mask_keep(v, 2, 2)
    if t == "LICENSE_PLATE":
        return v[0] + v[1] + "*" * (len(v) - 3) + v[-1] if len(v) > 4 else _mask_keep(v, 2, 0)
    return _mask_keep(v, 1, 1)


def hash_pseudonym(entity: Entity, salt: str = "helan", **_) -> str:
    """加盐哈希假名：同一原文在相同 salt 下得到稳定一致的新假名（可关联分析）。"""
    digest = hashlib.sha256((salt + "\x1f" + entity.type + "\x1f" + entity.text).encode("utf-8")).hexdigest()
    return f"{entity.type[:4].lower()}_{digest[:12]}"


# ---------- fake：格式合法的假数据 ----------


def _rng_for(entity: Entity, salt: str) -> random.Random:
    seed = int(hashlib.sha256(f"{salt}\x1f{entity.type}\x1f{entity.text}".encode()).hexdigest()[:12], 16)
    return random.Random(seed)


def fake(entity: Entity, salt: str = "helan", **_) -> str:
    rng = _rng_for(entity, salt)
    t = entity.type
    if t == "ID_CARD":
        return checksum.make_fake_id_card(rng)
    if t == "PHONE":
        return rng.choice(sorted(MOBILE_SEGMENTS)) + "".join(str(rng.randint(0, 9)) for _ in range(8))
    if t == "BANK_CARD":
        return checksum.make_fake_bank_card(rng, rng.choice(FAKE_BANK_BINS))
    if t == "USCC":
        return checksum.make_fake_uscc(rng, rng.choice(FAKE_USCC_PREFIXES))
    if t == "PERSON_NAME":
        return rng.choice(SURNAMES) + "".join(rng.choice(FAKE_GIVEN_CHARS) for _ in range(rng.randint(1, 2)))
    if t == "EMAIL":
        return f"user{rng.randint(100, 999)}@{rng.choice(FAKE_EMAIL_DOMAINS)}"
    if t == "LANDLINE":
        return f"0{rng.randint(10, 29)}-{rng.randint(20000000, 99999999)}"
    if t == "PASSPORT":
        return rng.choice("EGDSP") + "".join(str(rng.randint(0, 9)) for _ in range(8))
    if t == "LICENSE_PLATE":
        prov = rng.choice("京津沪渝冀辽吉黑苏浙皖闽赣鲁豫鄂湘粤")
        letter = rng.choice("ABCDEFGHJKLMNP")
        tail = "".join(rng.choice("ABCDEFGHJKLMNP0123456789") for _ in range(5))
        return f"{prov}{letter}{tail}"
    if t == "IP_ADDRESS":
        return ".".join(str(rng.randint(1, 254)) for _ in range(4))
    if t == "URL":
        return f"https://example.org/{rng.randint(1000, 9999)}"
    if t == "ADDRESS":
        return f"北京市朝阳区示例路{rng.randint(1, 999)}号"
    return "[已替换]"


OPERATORS: dict[str, object] = {
    "redact": redact,
    "partial": partial,
    "hash": hash_pseudonym,
    "fake": fake,
}

# 这些算子不可逆（原文不保留）；可逆替换请用 pipeline 的 vault 占位模式
IRREVERSIBLE_OPERATORS = frozenset(OPERATORS)
