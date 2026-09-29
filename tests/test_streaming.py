"""流式识别与基准模块测试。"""

from __future__ import annotations

import random

import pytest

from helan import checksum as C
from helan.bench import run as bench_run
from helan.eval.corpus import build_corpus
from helan.pipeline import recognize
from helan.streaming import DEFAULT_OVERLAP, read_file_chunks, recognize_iter


def _corpus_texts():
    return [d.text for d in build_corpus()]


class TestRecognizeIterEquivalence:
    @pytest.mark.parametrize("shift", [-7, -1, 0, 1, 13, 64])
    def test_stream_equals_whole_read_on_corpus(self, shift):
        """不同 chunk 边界偏移下,流式结果必须与整读一致。"""
        for text in _corpus_texts():
            # 用 shift 把每个实体的位置相对边界挪动
            shifted_text = ("\u3000" * max(0, shift)) + text if shift > 0 else text
            whole = {(e.type, e.start, e.end) for e in recognize(shifted_text)}
            streamed = {
                (e.type, e.start, e.end)
                for e in recognize_iter(
                    [shifted_text[i : i + 64] for i in range(0, len(shifted_text), 64)],
                    chunk_size=64,
                    overlap=48,
                )
            }
            assert streamed == whole, f"shift={shift}: {streamed ^ whole}"

    def test_id_card_cut_at_every_boundary(self):
        """身份证跨 chunk 边界的每个切口都必须被完整识别。"""
        rng = random.Random(5)
        idcard = C.make_fake_id_card(rng)
        text = f"前置说明文字,{idcard},后置说明文字。"
        whole = {(e.type, e.start, e.end) for e in recognize(text)}
        assert any(t == "ID_CARD" for t, _s, _e in whole)
        # 在身份证的每一位处切割(overlap=24 > 18 位,保证实体头部不被切掉)
        id_pos = text.index(idcard)
        for cut in range(id_pos, id_pos + len(idcard)):
            chunks = [text[:cut], text[cut:]]
            streamed = {(e.type, e.start, e.end) for e in recognize_iter(chunks, chunk_size=32, overlap=24)}
            assert "ID_CARD" in {t for t, _s, _e in streamed}, f"cut={cut} 丢失身份证"
            assert streamed == whole, f"cut={cut}: {streamed ^ whole}"

    def test_offsets_absolute_and_invariant(self):
        text = _corpus_texts()[0] + _corpus_texts()[1]
        chunks = [text[i : i + 50] for i in range(0, len(text), 50)]
        entities = list(recognize_iter(chunks, chunk_size=50, overlap=40))
        for e in entities:
            assert e.text == text[e.start : e.end]
        starts = [e.start for e in entities]
        assert starts == sorted(starts)

    def test_generator_input(self):
        text = _corpus_texts()[2]
        chunks = iter(text[i : i + 40] for i in range(0, len(text), 40))
        streamed = list(recognize_iter(chunks, chunk_size=40, overlap=32))
        whole = list(recognize(text))
        assert [(e.type, e.start, e.end) for e in streamed] == [
            (e.type, e.start, e.end) for e in whole
        ]

    def test_file_chunks(self, tmp_path):
        text = _corpus_texts()[3] + _corpus_texts()[4]
        path = tmp_path / "big.txt"
        path.write_text(text, encoding="utf-8")
        streamed = list(recognize_iter(read_file_chunks(str(path), chunk_size=64), chunk_size=64, overlap=48))
        whole = {(e.type, e.start, e.end) for e in recognize(text)}
        assert {(e.type, e.start, e.end) for e in streamed} == whole

    def test_overlap_must_be_smaller_than_chunk(self):
        with pytest.raises(ValueError):
            list(recognize_iter(["abc"], chunk_size=8, overlap=8))

    def test_overlap_too_small_rejected(self):
        with pytest.raises(ValueError):
            list(recognize_iter(["abc" * 100], chunk_size=64, overlap=6))

    def test_default_overlap_constant(self):
        # overlap 必须能覆盖 URL 上限(512),否则病态长 URL 会在边界漏检
        assert DEFAULT_OVERLAP == 512


class TestBench:
    def test_bench_small_smoke(self):
        result = bench_run(0.05)
        assert result["size_mb"] >= 0.04
        assert result["entities"] > 0
        assert result["full_mbps"] > 0
        assert result["baseline_secs"] > 0
