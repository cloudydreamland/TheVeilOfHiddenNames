"""模糊测试：偏移不变量与还原闭环的性质保证（固定种子，可复现）。"""

from __future__ import annotations

import random

from helan import checksum as C
from helan.pipeline import DEFAULT_OPS, mask, recognize, restore

SEEDS = list(range(64))

FILLER = [
    "这是一段普通的中文文本，包含一些数字12345和文字。",
    "会议纪要，编号2026-09-001，讨论了项目进度与预算安排。",
    "The quick brown fox jumps over the lazy dog. 订单 998877。",
    "，。；：？！、",
    "",
    "账户余额 1,234.56 元，汇率 6.95。",
]


def _splice(rng: random.Random) -> str:
    """把合法实体随机拼进随机填充文本。"""
    parts = []
    for _ in range(rng.randint(2, 6)):
        parts.append(rng.choice(FILLER))
        kind = rng.randint(0, 4)
        if kind == 0:
            parts.append(C.make_fake_id_card(rng))
        elif kind == 1:
            prefixes = sorted(C.MOBILE_SEGMENTS)
            parts.append(rng.choice(prefixes) + f"{rng.randint(0, 99999999):08d}")
        elif kind == 2:
            parts.append(C.make_fake_bank_card(rng))
        elif kind == 3:
            parts.append(C.make_fake_uscc(rng))
    parts.append(rng.choice(FILLER))
    return "".join(parts)


def test_offset_invariant_under_fuzz():
    for seed in SEEDS:
        rng = random.Random(seed)
        text = _splice(rng)
        for e in recognize(text):
            assert e.text == text[e.start : e.end], (
                f"seed={seed}: {e} vs {text[e.start:e.end]!r}"
            )


def test_no_overlap_after_resolve():
    for seed in SEEDS:
        rng = random.Random(1000 + seed)
        text = _splice(rng)
        ents = recognize(text)
        for a, b in zip(ents, ents[1:]):
            assert a.end <= b.start, f"seed={seed}: 重叠 {a} {b}"


def test_full_vault_roundtrip_under_fuzz():
    ops = {k: "vault" for k in DEFAULT_OPS}
    for seed in SEEDS:
        rng = random.Random(2000 + seed)
        text = _splice(rng)
        masked, vault = mask(text, ops=ops)
        assert restore(masked, vault) == text, f"seed={seed}: 还原失败"


def test_masked_text_never_contains_original_for_checksum_types():
    for seed in SEEDS:
        rng = random.Random(3000 + seed)
        text = _splice(rng)
        masked, _ = mask(text)  # 默认全部不可逆算子
        for e in recognize(text):
            if e.source == "checksum":
                assert e.text not in masked
