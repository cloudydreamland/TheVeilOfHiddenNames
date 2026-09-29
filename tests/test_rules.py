"""规则类 recognizer 测试。"""

from __future__ import annotations

from helan.recognizers.rules import (
    recognize_email,
    recognize_ip,
    recognize_landline,
    recognize_passport,
    recognize_plate,
    recognize_url,
)


class TestEmail:
    def test_simple(self):
        ents = recognize_email("邮箱 user.ming@example.cn 结束")
        assert len(ents) == 1
        assert ents[0].text == "user.ming@example.cn"

    def test_multi_level_domain(self):
        assert recognize_email("a@mail.example.com.cn")[0].end - recognize_email("a@mail.example.com.cn")[0].start == 21

    def test_rejects_leading_dot(self):
        assert recognize_email(".user@example.com") == []

    def test_no_false_in_text(self):
        assert recognize_email("没有邮箱的文本") == []


class TestIp:
    def test_valid(self):
        ents = recognize_ip("服务器 IP 是 192.168.1.100。")
        assert ents[0].text == "192.168.1.100"

    def test_octet_range(self):
        assert recognize_ip("256.1.1.1") == []
        assert recognize_ip("10.0.0.999") == []

    def test_guard_inside_digits(self):
        assert recognize_ip("版本号12.168.1.2345") == []

    def test_trailing_dot_allowed(self):
        ents = recognize_ip("IP:10.0.0.1.")
        assert ents[0].text == "10.0.0.1"


class TestUrl:
    def test_basic(self):
        ents = recognize_url("详见 https://example.com/a/b?x=1 说明")
        assert ents[0].text == "https://example.com/a/b?x=1"

    def test_chinese_trailing_punct_trimmed(self):
        ents = recognize_url("打开 https://example.com/x。")
        assert ents[0].text.endswith("x")
        assert ents[0].meta["trimmed_len"] == len("https://example.com/x")


class TestLandline:
    def test_valid_area(self):
        ents = recognize_landline("电话 010-65542317。")
        assert ents[0].text == "010-65542317"

    def test_no_dash(self):
        assert recognize_landline("电话 02163321588。")[0].text == "02163321588"

    def test_unknown_area_rejected(self):
        assert recognize_landline("电话 099-1234567") == []


class TestPlate:
    def test_standard(self):
        ents = recognize_plate("车牌 京AD1289 停放")
        assert ents[0].text == "京AD1289"

    def test_with_dot(self):
        assert recognize_plate("车牌 京A·D1289 停放")[0].text == "京A·D1289"

    def test_new_energy_six(self):
        assert recognize_plate("新能源 沪BD12345")[0].text == "沪BD12345"

    def test_i_o_excluded(self):
        assert recognize_plate("车牌 京AI1234") == []


class TestPassport:
    def test_valid(self):
        ents = recognize_passport("护照号 E12345678。")
        assert ents[0].text == "E12345678"

    def test_guarded(self):
        assert recognize_passport("编号XE1234567890") == []

    def test_short_rejected(self):
        assert recognize_passport("E1234567") == []
