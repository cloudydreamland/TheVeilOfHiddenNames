"""resolver / operators / vault / pipeline 集成测试。"""

from __future__ import annotations

import random

import pytest

from helan import checksum as C
from helan.operators import fake, hash_pseudonym, partial, redact
from helan.pipeline import DEFAULT_OPS, mask, recognize, restore
from helan.resolver import resolve
from helan.types import ID_CARD, PHONE, Entity
from helan.vault import Vault


def _mk(t: str, text: str, start: int, score: float = 0.9, source: str = "rule") -> Entity:
    return Entity(type=t, start=start, end=start + len(text), text=text, score=score, source=source)


ID_A = "23144319731204692X"


class TestResolver:
    def test_phone_inside_id_card_suppressed(self):
        id_ent = _mk(ID_CARD, ID_A, 2, score=0.95)
        phone_ent = _mk(PHONE, ID_A[3:14], 5, score=0.9)
        resolved = resolve([phone_ent, id_ent])
        assert [e.type for e in resolved] == [ID_CARD]

    def test_priority_beats_length(self):
        a = _mk(PHONE, "13812345678", 0, score=0.9)
        b = _mk("ADDRESS", "13812345678以及后面更长的地址内容", 0, score=0.6)
        resolved = resolve([a, b])
        assert [e.type for e in resolved] == [PHONE]

    def test_score_threshold(self):
        low = _mk("ADDRESS", "某地某路某号", 0, score=0.4)
        assert resolve([low], min_score=0.5) == []

    def test_adjacent_not_overlap(self):
        a = _mk(PHONE, "13812345678", 0)
        b = _mk(PHONE, "13912345678", 11)
        assert len(resolve([a, b])) == 2

    def test_output_sorted(self):
        a = _mk(PHONE, "13812345678", 20)
        b = _mk(PHONE, "13912345678", 0)
        resolved = resolve([a, b])
        assert [e.start for e in resolved] == [0, 20]

    def test_scale_not_quadratic(self):
        """3 万实体规模必须在秒级完成(防 O(n²) 回潮,iter2 曾因此 40 秒/2MB)。"""
        import random
        import time

        rng = random.Random(7)
        raw = []
        for i in range(30000):
            start = rng.randint(0, 100000)
            raw.append(_mk(PHONE, "13812345678", start, score=rng.random()))
        t0 = time.perf_counter()
        resolved = resolve(raw)
        elapsed = time.perf_counter() - t0
        assert len(resolved) > 0
        assert elapsed < 5.0, f"resolver 回归到平方级: {elapsed:.1f}s"


class TestOperators:
    def test_redact_labels(self):
        assert redact(_mk(ID_CARD, "x", 0)) == "[身份证号]"
        assert redact(_mk(PHONE, "x", 0)) == "[手机号]"

    def test_partial_phone(self):
        assert partial(_mk(PHONE, "13812345678", 0)) == "138****5678"

    def test_partial_id(self):
        masked = partial(_mk(ID_CARD, ID_A, 0))
        assert masked == ID_A[:3] + "*" * 11 + ID_A[-4:]

    def test_partial_person(self):
        assert partial(_mk("PERSON_NAME", "张伟明", 0)) == "张**"
        assert partial(_mk("PERSON_NAME", "李楠", 0)) == "李*"

    def test_partial_email(self):
        assert partial(_mk("EMAIL", "uming@example.cn", 0)) == "u***@example.cn"

    def test_hash_stable_and_salted(self):
        e = _mk(PHONE, "13812345678", 0)
        assert hash_pseudonym(e) == hash_pseudonym(e)
        assert hash_pseudonym(e, salt="a") != hash_pseudonym(e, salt="b")

    def test_fake_outputs_pass_validators(self):
        e_id = _mk(ID_CARD, C.make_fake_id_card(random.Random(3)), 0)
        assert C.id_card_valid(fake(e_id, salt="s1"))
        e_bank = _mk("BANK_CARD", "6217000265423513", 0)
        assert C.luhn_valid(fake(e_bank, salt="s2"))
        e_uscc = _mk("USCC", "9111H3XC2H9TLKWUBL", 0)
        assert C.uscc_valid(fake(e_uscc, salt="s3"))
        e_phone = _mk(PHONE, "13812345678", 0)
        assert C.mobile_prefix_valid(fake(e_phone, salt="s4"))

    def test_fake_deterministic(self):
        e = _mk(ID_CARD, ID_A, 0)
        assert fake(e, salt="k") == fake(e, salt="k")

    def test_fake_differs_from_original(self):
        e = _mk(ID_CARD, ID_A, 0)
        assert fake(e, salt="k") != ID_A


class TestVault:
    def test_place_and_restore(self):
        v = Vault()
        p1 = v.place(PHONE, "13812345678")
        p2 = v.place(PHONE, "13812345678")  # 去重
        assert p1 == p2
        assert len(v) == 1
        assert v.restore(f"电话{p1}已记") == "电话13812345678已记"

    def test_different_type_same_text_distinct(self):
        v = Vault()
        p1 = v.place(PHONE, "12345678")
        p2 = v.place("URL", "12345678")
        assert p1 != p2

    def test_save_load_roundtrip(self, tmp_path):
        v = Vault()
        p = v.place(ID_CARD, ID_A)
        path = tmp_path / "v.json"
        v.save(str(path))
        v2 = Vault.load(str(path))
        assert v2.restore(f"证{p}案") == f"证{ID_A}案"

    def test_json_format(self):
        v = Vault()
        v.place(PHONE, "13812345678")
        data = v.to_json()
        assert "PHONE_1" in data


class TestPipeline:
    def test_mask_default_ops(self):
        text = f"电话13812345678，证号{ID_A}。"
        masked, vault = mask(text)
        assert "13812345678" not in masked
        assert "138****5678" in masked
        assert ID_A not in masked
        assert len(vault) == 0  # 默认无 vault 算子

    def test_mask_vault_restore_roundtrip(self):
        text = f"证号{ID_A}，电话13812345678。"
        masked, vault = mask(text, ops={"ID_CARD": "vault", "PHONE": "vault"})
        assert restore(masked, vault) == text

    def test_mask_fake_is_irreversible(self):
        text = "电话13812345678。"
        masked, vault = mask(text, ops={"PHONE": "fake"})
        assert "13812345678" not in masked
        assert len(vault) == 0
        assert restore(masked, vault) != text  # fake 不可逆，这是设计而非缺陷

    def test_mask_all_vault_golden_roundtrip(self):
        text = f"出租方（甲方）：张伟明，电话13812345678，证号{ID_A}，代码9111H3XC2H9TLKWUBL。"
        ops = {k: "vault" for k in DEFAULT_OPS}
        masked, vault = mask(text, ops=ops)
        assert restore(masked, vault) == text
        assert len(vault) >= 3

    def test_ops_unknown_type_raises(self):
        with pytest.raises(ValueError):
            mask("x", ops={"NOT_A_TYPE": "redact"})

    def test_callable_op(self):
        text = "电话13812345678。"
        masked, _ = mask(text, ops={"PHONE": lambda e, salt: "【固话】"})
        assert masked == "电话【固话】。"

    def test_recognize_offset_invariant_on_sample(self):
        text = f"证号{ID_A}，电话13812345678，邮箱 someone@example.com 结束。"
        for e in recognize(text):
            assert e.text == text[e.start : e.end]

    def test_empty_text(self):
        assert recognize("") == []
        masked, _ = mask("")
        assert masked == ""

    def test_types_filter(self):
        text = f"证号{ID_A}，电话13812345678。"
        ents = recognize(text, types=["PHONE"])
        assert [e.type for e in ents] == [PHONE]
