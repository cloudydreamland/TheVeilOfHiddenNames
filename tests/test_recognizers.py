"""官方校验级 recognizer + 上下文 recognizer 测试。"""

from __future__ import annotations

import random

from helan import checksum as C
from helan.recognizers.chinese import recognize_address, recognize_person
from helan.recognizers.official import (
    recognize_bank_card,
    recognize_id_card,
    recognize_phone,
    recognize_uscc,
)


def _valid_id(rng: random.Random) -> str:
    return C.make_fake_id_card(rng)


class TestIdCardRecognizer:
    def test_detects_valid(self):
        rng = random.Random(1)
        value = _valid_id(rng)
        ents = recognize_id_card(f"身份证号 {value} 有效")
        assert len(ents) == 1
        assert ents[0].score == 0.95
        assert ents[0].source == "checksum"

    def test_rejects_invalid_checksum(self):
        rng = random.Random(2)
        value = _valid_id(rng)
        flipped = value[:-1] + ("0" if value[-1] != "0" else "1")
        assert recognize_id_card(f"身份证号 {flipped} 无效") == []

    def test_guard_inside_longer_digits(self):
        rng = random.Random(3)
        value = _valid_id(rng)
        assert recognize_id_card("9" + value + "9") == []

    def test_legacy_15_flagged(self):
        id18 = _valid_id(random.Random(4))
        id15 = id18[:6] + id18[8:14] + id18[14:17]
        ents = recognize_id_card(f"旧证 {id15} 尾")
        assert len(ents) == 1
        assert ents[0].meta["legacy15"] is True
        assert ents[0].meta["upgraded"] == C.id_card_upgrade_15(id15)


class TestBankRecognizer:
    def test_contiguous(self):
        rng = random.Random(5)
        value = C.make_fake_bank_card(rng)
        ents = recognize_bank_card(f"卡号 {value} 尾")
        assert len(ents) == 1
        assert ents[0].meta["normalized"] == value

    def test_grouped_with_spaces(self):
        value = "6217 0016 1559 4078"
        ents = recognize_bank_card(f"卡号 {value} 尾")
        assert len(ents) == 1
        assert ents[0].meta["normalized"] == value.replace(" ", "")

    def test_luhn_failure_rejected(self):
        assert recognize_bank_card("卡号 6217000010023456785 尾") == []

    def test_id_card_with_x_never_bank(self):
        # X 校验位的身份证不可能是纯数字银行卡
        value = "23144319731204692X"
        assert recognize_bank_card(f"证号 {value} 尾") == []


class TestUsccRecognizer:
    def test_detects_valid(self):
        rng = random.Random(7)
        value = C.make_fake_uscc(rng)
        ents = recognize_uscc(f"代码 {value} 尾")
        assert len(ents) == 1 and ents[0].source == "checksum"

    def test_guarded_by_alnum(self):
        rng = random.Random(8)
        value = C.make_fake_uscc(rng)
        assert recognize_uscc(f"A{value}B") == []


class TestPhoneRecognizer:
    def test_valid(self):
        ents = recognize_phone("电话 13812345678。")
        assert ents[0].text == "13812345678" and ents[0].score == 0.9

    def test_segment_rejected(self):
        assert recognize_phone("电话 14012345678。") == []

    def test_guard(self):
        assert recognize_phone("编号9138123456789") == []


class TestPersonContext:
    def test_honorific(self):
        ents = recognize_person("今天张伟明先生来访。")
        assert [(e.text, e.meta["cue"]) for e in ents] == [("张伟明", "honorific")]

    def test_honorific_surname_only_excluded(self):
        # 只有姓没有名， precision 优先，不命中
        assert recognize_person("王先生来了。") == []

    def test_lead_word(self):
        ents = recognize_person("患者王建国，已于昨日出院。")
        assert [(e.text, e.meta["cue"]) for e in ents] == [("王建国", "lead_word")]

    def test_lead_with_parenthetical(self):
        ents = recognize_person("出租方（甲方）：张伟明，联系电话略。")
        assert ents[0].text == "张伟明"

    def test_no_context_no_match(self):
        assert recognize_person("张伟明是谁？") == []

    def test_name_followed_by_cjk_not_matched(self):
        # 姓名后紧跟汉字（如动词），precise 模式不冒险
        assert recognize_person("患者王建国出院了。") == []


class TestAddressContext:
    def test_keyed_address(self):
        ents = recognize_address("家庭住址：浙江省杭州市西湖区文三路120号。")
        assert ents[0].text == "浙江省杭州市西湖区文三路120号"
        assert ents[0].score == 0.6

    def test_requires_tail_word(self):
        assert recognize_address("地址：随便写的一段话") == []

    def test_head_form(self):
        ents = recognize_address("公司住所位于北京市朝阳区建国路88号。")
        assert ents[0].text == "北京市朝阳区建国路88号"
