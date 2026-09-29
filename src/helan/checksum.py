"""确定性校验器：身份证 / 银行卡(Luhn) / 统一社会信用代码 / 手机号段。

这是 helan 区别于"纯正则脱敏"的核心：一个候选串只有通过
官方校验算法才算命中，从数学上消灭大部分误报。
"""

from __future__ import annotations

import datetime
import random
import re

from .data import MOBILE_SEGMENTS, PROVINCES

# ---------- 身份证（GB 11643-1999，ISO 7064 MOD 11-2） ----------

_ID_WEIGHTS = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
_ID_CHECK_MAP = "10X98765432"

_ID18_RE = re.compile(r"^\d{17}[0-9X]$")
_ID15_RE = re.compile(r"^\d{15}$")


def id_card_check_digit(first17: str) -> str:
    if len(first17) != 17 or not first17.isdigit():
        raise ValueError("需要 17 位数字")
    total = sum(int(d) * w for d, w in zip(first17, _ID_WEIGHTS))
    return _ID_CHECK_MAP[total % 11]


def _birth_valid(yyyymmdd: str) -> bool:
    try:
        birth = datetime.date(int(yyyymmdd[:4]), int(yyyymmdd[4:6]), int(yyyymmdd[6:8]))
    except ValueError:
        return False
    return datetime.date(1900, 1, 1) <= birth <= datetime.date.today()


def id_card_valid(value: str, *, today: datetime.date | None = None) -> bool:
    """18 位身份证严格校验：省级区划 + 出生日期 + MOD 11-2 校验码。"""
    _ = today  # 预留：限制出生日期不得晚于今天
    value = value.strip().upper()
    if not _ID18_RE.match(value):
        return False
    if value[:2] not in PROVINCES:
        return False
    if not _birth_valid(value[6:14]):
        return False
    return id_card_check_digit(value[:17]) == value[17]


def id_card_15_valid(value: str) -> bool:
    """15 位一代身份证：无校验码，只校验区划与出生日期，可信度低于 18 位。"""
    value = value.strip()
    if not _ID15_RE.match(value):
        return False
    if value[:2] not in PROVINCES:
        return False
    # 15 位：YYMMDD 为 19yy 年
    return _birth_valid("19" + value[6:12])


def id_card_upgrade_15(value: str) -> str | None:
    """15 位升 18 位（补世纪位 + 计算校验码），失败返回 None。"""
    value = value.strip()
    if not id_card_15_valid(value):
        return None
    first17 = value[:6] + "19" + value[6:]
    return first17 + id_card_check_digit(first17)


# ---------- 银行卡（Luhn，ISO/IEC 7812） ----------

_DIGITS_RE = re.compile(r"^\d+$")


def luhn_check_digit(payload: str) -> str:
    """对不含校验位的主体计算 Luhn 校验位。"""
    if not payload or not _DIGITS_RE.match(payload):
        raise ValueError("需要非空数字串")
    total = 0
    double = True  # 从校验位左侧第一位开始（即主体最后一位）倍乘
    for ch in reversed(payload):
        d = int(ch)
        if double:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        double = not double
    return str((10 - total % 10) % 10)


def luhn_valid(value: str) -> bool:
    value = re.sub(r"[ -]", "", value.strip())
    if not _DIGITS_RE.match(value) or len(value) < 13 or len(value) > 19:
        return False
    return luhn_check_digit(value[:-1]) == value[-1]


# ---------- 统一社会信用代码（GB 32100-2015，MOD 31-3） ----------

_USCC_WEIGHTS = (1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28)


def _uscc_value(ch: str) -> int:
    from .data import USCC_CHARSET

    pos = USCC_CHARSET.find(ch)
    if pos < 0:
        raise ValueError(f"字符不在 GB 32100 字符集内: {ch!r}")
    return pos


def uscc_check_char(first17: str) -> str:
    from .data import USCC_CHARSET

    if len(first17) != 17:
        raise ValueError("需要 17 位主体")
    total = sum(_uscc_value(ch) * w for ch, w in zip(first17, _USCC_WEIGHTS))
    return USCC_CHARSET[(31 - total % 31) % 31]


def uscc_valid(value: str) -> bool:
    from .data import USCC_CHARSET

    value = value.strip().upper()
    if len(value) != 18:
        return False
    if any(ch not in USCC_CHARSET for ch in value):
        return False
    return uscc_check_char(value[:17]) == value[17]


# ---------- 手机号段 ----------


def mobile_prefix_valid(digits11: str) -> bool:
    return len(digits11) == 11 and digits11.isdigit() and digits11[:3] in MOBILE_SEGMENTS


# ---------- 假数据生成（校验和合法，用于测试/演示数据替换） ----------


def make_fake_id_card(rng) -> str:
    provinces = sorted(PROVINCES)
    prov = rng.choice(provinces)
    city = f"{rng.randint(1, 8)}{rng.randint(0, 9)}"  # 市级两位（假数据不对应真实区划）
    county = f"{rng.randint(1, 9)}{rng.randint(0, 9)}"  # 县级两位
    year = rng.randint(1965, 2004)
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    seq = f"{rng.randint(0, 999):03d}"
    first17 = f"{prov}{city}{county}{year}{month:02d}{day:02d}{seq}"
    return first17 + id_card_check_digit(first17)


def make_fake_bank_card(rng: random.Random, bin_prefix: str = "621700") -> str:
    payload = bin_prefix + "".join(str(rng.randint(0, 9)) for _ in range(15 - len(bin_prefix)))
    return payload + luhn_check_digit(payload)


def make_fake_uscc(rng: random.Random, prefix: str = "9111") -> str:
    from .data import USCC_CHARSET

    body = prefix + "".join(rng.choice(USCC_CHARSET) for _ in range(13))
    return body + uscc_check_char(body)


# ---------- 台湾地区身份证（1 字母 + 9 数字，MOD 10） ----------


def tw_id_check_digit(letter_and_9: str) -> str:
    """对「字母 + 前 8 位数字」计算第 9 位校验码。"""
    from .data import TW_LETTER_CODES

    letter = letter_and_9[0].upper()
    if letter not in TW_LETTER_CODES or not letter_and_9[1:].isdigit() or len(letter_and_9) != 9:
        raise ValueError("需要 字母+8位数字")
    code = TW_LETTER_CODES[letter]
    digits = [code // 10, code % 10] + [int(d) for d in letter_and_9[1:]]
    weights = (1, 9, 8, 7, 6, 5, 4, 3, 2, 1)
    total = sum(d * w for d, w in zip(digits, weights))
    check = (10 - total % 10) % 10
    return letter_and_9[:9] + str(check)


def tw_id_valid(value: str) -> bool:
    """台湾身份证：字母地区码 + 9 数字；第 2 位为性别（1 男 2 女）；加权 MOD 10。"""
    from .data import TW_LETTER_CODES

    value = value.strip().upper()
    if len(value) != 10 or value[0] not in TW_LETTER_CODES or not value[1:].isdigit():
        return False
    if value[1] not in ("1", "2"):  # 性别位（9 位数字的第 1 位）
        return False
    code = TW_LETTER_CODES[value[0]]
    digits = [code // 10, code % 10] + [int(d) for d in value[1:]]  # 11 个值（含校验位）
    weights = (1, 9, 8, 7, 6, 5, 4, 3, 2, 1, 1)  # 11 个权重，校验位权重为 1
    return sum(d * w for d, w in zip(digits, weights)) % 10 == 0


def make_fake_tw_id(rng) -> str:
    import string

    from .data import TW_LETTER_CODES

    letter = rng.choice(sorted(TW_LETTER_CODES))
    body = letter + rng.choice("12") + "".join(rng.choices(string.digits, k=7))
    return tw_id_check_digit(body)
