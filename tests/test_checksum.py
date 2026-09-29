"""校验器测试：锚定向量 + 变异必败性质。"""

from __future__ import annotations

import random

import pytest

from helan import checksum as C

ID_A = "23144319731204692X"  # 锚定：生成器产出并通过校验的真实向量
ID_B = "217011197804176164"
BANK_A = "6217000265423513"
USCC_A = "9111H3XC2H9TLKWUBL"


class TestIdCard:
    def test_pinned_valid(self):
        assert C.id_card_valid(ID_A)
        assert C.id_card_valid(ID_B)

    def test_check_digit_manual(self):
        # 230404 -> 校验码按 MOD 11-2 手工复核
        first17 = ID_A[:17]
        assert C.id_card_check_digit(first17) == ID_A[17].upper()

    def test_x_lowercase_accepted(self):
        assert C.id_card_valid(ID_A.lower())

    @pytest.mark.parametrize("pos", range(18))
    def test_single_digit_mutation_fails(self, pos):
        rng = random.Random(pos)
        chars = list(ID_A)
        while True:
            repl = rng.choice("0123456789X")
            if repl != chars[pos]:
                chars[pos] = repl
                break
        mutated = "".join(chars)
        assert not C.id_card_valid(mutated), f"变异未被抓到: {mutated}"

    def test_bad_province(self):
        assert not C.id_card_valid("90" + ID_A[2:])

    def test_bad_birth(self):
        # 13月不存在
        body = list(ID_A)
        body[10] = "1"
        body[11] = "3"
        assert not C.id_card_valid("".join(body))

    def test_bad_length(self):
        assert not C.id_card_valid(ID_A[:-1])
        assert not C.id_card_valid(ID_A + "0")

    def test_generated_always_valid(self):
        rng = random.Random(1234)
        for _ in range(200):
            assert C.id_card_valid(C.make_fake_id_card(rng))

    def test_upgrade_15(self):
        id15 = ID_B[:6] + ID_B[8:14] + ID_B[14:17]  # 去世纪与校验位
        upgraded = C.id_card_upgrade_15(id15)
        assert upgraded is not None
        assert C.id_card_valid(upgraded)
        assert C.id_card_15_valid(id15)


class TestLuhn:
    def test_pinned_valid(self):
        assert C.luhn_valid(BANK_A)
        assert C.luhn_valid("6217 0016 1559 4078")  # 带空格分组

    def test_check_digit_roundtrip(self):
        payload = BANK_A[:-1]
        assert C.luhn_check_digit(payload) == BANK_A[-1]

    def test_known_bad(self):
        assert not C.luhn_valid("1234567890123456")

    def test_too_short_or_long(self):
        assert not C.luhn_valid("123456789012")  # 12 位
        assert not C.luhn_valid("12345678901234567890")  # 20 位

    def test_generated_always_valid(self):
        rng = random.Random(99)
        for _ in range(100):
            assert C.luhn_valid(C.make_fake_bank_card(rng))


class TestUscc:
    def test_pinned_valid(self):
        assert C.uscc_valid(USCC_A)
        assert C.uscc_valid(USCC_A.lower())

    def test_excluded_charset_rejected(self):
        # I/O/S/V/Z 不在 GB 32100 字符集
        assert not C.uscc_valid("9111IOSV2H9TLKWUBL")

    @pytest.mark.parametrize("pos", range(18))
    def test_mutation_fails(self, pos):
        rng = random.Random(pos + 500)
        from helan.data import USCC_CHARSET

        chars = list(USCC_A)
        while True:
            repl = rng.choice(USCC_CHARSET)
            if repl != chars[pos]:
                chars[pos] = repl
                break
        assert not C.uscc_valid("".join(chars))

    def test_generated_always_valid(self):
        rng = random.Random(7)
        for _ in range(100):
            assert C.uscc_valid(C.make_fake_uscc(rng))


class TestMobile:
    def test_valid_segments(self):
        for prefix in ("130", "138", "149", "155", "166", "171", "178", "186", "199"):
            assert C.mobile_prefix_valid(prefix + "12345678")

    def test_invalid_segments(self):
        for prefix in ("120", "140", "154", "162", "174", "194", "197"):
            assert not C.mobile_prefix_valid(prefix + "12345678")

    def test_wrong_length(self):
        assert not C.mobile_prefix_valid("1381234567")
        assert not C.mobile_prefix_valid("138123456789")
