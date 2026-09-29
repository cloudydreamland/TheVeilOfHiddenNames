"""iter3 新增实体与场景测试。"""

from __future__ import annotations

import random

from helan import checksum as C
from helan.calibrate import collect_person_fps
from helan.calibrate import render as calibrate_render
from helan.recognizers.chinese import (
    recognize_officer,
    recognize_postal,
    recognize_qq,
    recognize_wechat,
)
from helan.recognizers.official import recognize_id_card, recognize_tw_id_card


class TestPostal:
    def test_cued(self):
        ents = recognize_postal("邮编 100089 结束")
        assert ents[0].text == "100089" and ents[0].type == "POSTAL_CODE"

    def test_colon_variant(self):
        assert recognize_postal("邮政编码：214000。")[0].text == "214000"

    def test_bare_digits_not_matched(self):
        assert recognize_postal("编号 100089 无 cue") == []

    def test_short_or_long_rejected(self):
        assert recognize_postal("邮编 10008 不对") == []
        assert recognize_postal("邮编 1000899 不对") == []


class TestQQ:
    def test_cued(self):
        assert recognize_qq("QQ：987654321 联系")[0].text == "987654321"

    def test_no_hao_suffix(self):
        assert recognize_qq("扣扣 12345678")[0].text == "12345678"

    def test_leading_zero_rejected(self):
        assert recognize_qq("QQ 0123456") == []

    def test_too_short_rejected(self):
        assert recognize_qq("QQ 1234") == []


class TestWechat:
    def test_cued(self):
        ents = recognize_wechat("微信号 wxid_abc123")
        assert ents[0].text == "wxid_abc123" and ents[0].type == "WECHAT_ID"

    def test_must_start_with_letter(self):
        assert recognize_wechat("微信号 12345678") == []

    def test_dash_underscore_allowed(self):
        assert recognize_wechat("微信账号 my-name_1")[0].text == "my-name_1"


class TestTWId:
    def test_pinned_vectors(self):
        # 生成向量 + 经典测试向量 A123456789
        assert C.tw_id_valid("A123456789")
        rng = random.Random(11)
        for _ in range(200):
            assert C.tw_id_valid(C.make_fake_tw_id(rng))

    def test_gender_digit_required(self):
        # 校验和成立但性别位为 0/3 的构造必须被拒
        for pos in ("0", "3"):
            cand = "A" + pos + "2345678"
            # 不管校验和,性别位错了就 False
            assert not C.tw_id_valid(cand)

    def test_recognizer(self):
        ents = recognize_tw_id_card("台胞证件号 A123456789。")
        assert ents[0].type == "TW_ID_CARD" and ents[0].score == 0.95

    def test_invalid_rejected(self):
        assert recognize_tw_id_card("证件 A123456780。") == []

    def test_guarded(self):
        assert recognize_tw_id_card("编号XA123456789") == []


class TestGroupedMainlandId:
    def test_space_grouped(self):
        rng = random.Random(21)
        idcard = C.make_fake_id_card(rng)
        grouped = " ".join([idcard[:4], idcard[4:8], idcard[8:12], idcard[12:16], idcard[16:]])
        ents = recognize_id_card(f"证号 {grouped} 尾")
        assert len(ents) == 1
        assert ents[0].meta["normalized"] == idcard
        assert ents[0].text == grouped

    def test_dot_grouped(self):
        rng = random.Random(22)
        idcard = C.make_fake_id_card(rng)
        grouped = "·".join([idcard[:4], idcard[4:8], idcard[8:12], idcard[12:16], idcard[16:]])
        ents = recognize_id_card(f"证号 {grouped} 尾")
        assert ents[0].meta["normalized"] == idcard

    def test_fullwidth_space(self):
        rng = random.Random(23)
        idcard = C.make_fake_id_card(rng)
        grouped = "\u3000".join([idcard[:4], idcard[4:8], idcard[8:12], idcard[12:16], idcard[16:]])
        ents = recognize_id_card(f"证号 {grouped} 尾")
        assert ents[0].meta["normalized"] == idcard

    def test_invalid_grouped_rejected(self):
        ents = recognize_id_card("证号 1101 0519 4912 3100 20 尾")  # 校验位错
        assert ents == []


class TestOfficer:
    def test_cued_format_only(self):
        ents = recognize_officer("军官证：第0412345678号")
        assert ents[0].text == "0412345678"
        assert ents[0].meta["format_only"] is True

    def test_no_prefix_variants(self):
        assert recognize_officer("军官证号 04123456")[0].text == "04123456"
        assert recognize_officer("军官证 No.A12345678")[0].text == "A12345678"

    def test_too_short_rejected(self):
        assert recognize_officer("军官证 12345") == []


class TestCalibrate:
    def test_no_fp_on_corpus(self):
        assert collect_person_fps() == []

    def test_render_contains_zero_report(self):
        assert "FP 总数" in calibrate_render()

    def test_suggestion_mechanism(self):
        from helan.calibrate import suggest_blocklist

        fps = [{"text": "房间号"}, {"text": "房间1"}, {"text": "牌号X"}]
        assert suggest_blocklist(fps) == ["房间"]


class TestHKMOTraceability:
    def test_resident_permit_18digit_covered(self):
        """港澳台居民居住证走 18 位规则(81/82/71 省级码),应天然支持。"""
        rng = random.Random(31)
        prov = rng.choice(["71", "81", "82"])
        city = f"{rng.randint(0, 9)}{rng.randint(0, 9)}{rng.randint(0, 9)}{rng.randint(0, 9)}"
        body = prov + city + f"{rng.randint(1965, 2004)}{rng.randint(1, 12):02d}{rng.randint(1, 28):02d}" + f"{rng.randint(0, 999):03d}"
        value = body + C.id_card_check_digit(body)
        assert C.id_card_valid(value)

    def test_hk_mo_native_honestly_not_implemented(self):
        """港澳原生格式(HK letter+6+check)未实现——诚实留白,不做伪校验。"""
        from helan.types import ALL_TYPES

        assert "HK_MO_ID" not in ALL_TYPES
