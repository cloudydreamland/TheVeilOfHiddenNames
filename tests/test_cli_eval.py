"""CLI 与评测模块测试。"""

from __future__ import annotations

import random

import pytest

from helan import checksum as C
from helan.cli import main
from helan.eval import build_corpus, evaluate, run_all, run_report
from helan.eval.corpus import Doc
from helan.pipeline import recognize


@pytest.fixture()
def sample_file(tmp_path):
    idcard = C.make_fake_id_card(random.Random(11))
    path = tmp_path / "doc.txt"
    path.write_text(f"证号{idcard}，电话13812345678。\n", encoding="utf-8")
    return path, idcard


class TestCli:
    def test_scan_text_output(self, sample_file, capsys):
        path, idcard = sample_file
        assert main(["scan", str(path)]) == 0
        out = capsys.readouterr().out
        assert "ID_CARD" in out and "PHONE" in out and idcard in out

    def test_scan_jsonl(self, sample_file, capsys):
        path, _ = sample_file
        assert main(["scan", str(path), "--json"]) == 0
        out = capsys.readouterr().out.strip()
        lines = [line for line in out.splitlines() if line]
        assert lines and all('"type"' in line for line in lines)

    def test_mask_restore_roundtrip(self, sample_file, tmp_path):
        path, _ = sample_file
        masked_path = tmp_path / "masked.txt"
        vault_path = tmp_path / "vault.json"
        restored_path = tmp_path / "restored.txt"
        assert main([
            "mask", str(path), "-o", str(masked_path),
            "--ops", "ID_CARD:vault,PHONE:vault", "--vault-out", str(vault_path),
        ]) == 0
        assert main(["restore", str(masked_path), "--vault", str(vault_path), "-o", str(restored_path)]) == 0
        assert restored_path.read_text(encoding="utf-8") == path.read_text(encoding="utf-8")

    def test_eval_writes_report(self, tmp_path):
        out = tmp_path / "results.md"
        assert main(["eval", "--write", str(out)]) == 0
        text = out.read_text(encoding="utf-8")
        assert "基准" in text
        assert "TP/FP/FN" in text

    def test_bad_ops_exits(self, sample_file):
        path, _ = sample_file
        with pytest.raises(SystemExit):
            main(["mask", str(path), "-o", "x.txt", "--ops", "BAD_FORMAT"])


class TestCorpusIntegrity:
    def test_gold_spans_match_text(self):
        for doc in build_corpus():
            for g in doc.gold:
                assert g.text == doc.text[g.start : g.end], f"{doc.doc_id}: {g}"

    def test_gold_disjoint(self):
        for doc in build_corpus():
            ordered = sorted(doc.gold, key=lambda e: e.start)
            for a, b in zip(ordered, ordered[1:]):
                assert a.end <= b.start, f"{doc.doc_id}: gold 重叠 {a} {b}"

    def test_corpus_size(self):
        docs = build_corpus()
        assert len(docs) >= 12
        assert sum(len(d.gold) for d in docs) >= 40


class TestEval:
    def test_perfect_predictions(self):
        docs = build_corpus()
        report = evaluate(docs, {d.doc_id: list(d.gold) for d in docs})
        assert report.micro.fp == 0
        assert report.micro.fn == 0
        assert report.micro.precision == 1.0

    def test_empty_predictions(self):
        docs = build_corpus()
        report = evaluate(docs, {})
        assert report.micro.fn == sum(len(d.gold) for d in docs)

    def test_overlap_counts_separately(self):
        from helan.types import PHONE, Entity

        gold = [Entity(type=PHONE, start=0, end=11, text="13812345678", score=1, source="rule")]
        text = "13812345678"
        pred = [Entity(type=PHONE, start=0, end=10, text="1381234567", score=1, source="rule")]
        report = evaluate([Doc("d", "t", text, gold)], {"d": pred})
        assert report.micro.tp == 0
        assert report.micro.fn == 1
        assert report.micro.fp == 1
        assert report.micro.tp_overlap == 1

    def test_run_all_and_report(self):
        results = run_all()
        # jieba 已安装时有 3 个配置；未安装时 2 个
        assert len(results) in (2, 3)
        names = [r.name for r in results]
        assert any("default" in n for n in names)
        if len(results) == 3:
            assert "jieba" in names[-1]
        md = run_report()
        assert "|" in md and "基准" in md

    def test_pipeline_recall_on_checksum_types(self):
        # 核心承诺：校验和级类型在内置语料上必须接近满分
        docs = build_corpus()
        predictions = {d.doc_id: recognize(d.text) for d in docs}
        report = evaluate(docs, predictions)
        for etype in ("ID_CARD", "PHONE", "BANK_CARD", "USCC"):
            stats = report.per_type.get(etype)
            if stats and (stats.tp + stats.fn) > 0:
                assert stats.recall >= 0.99, f"{etype} recall 掉了: {stats.recall}"


def _gold():  # 保留给未来用例扩展
    from helan.types import PHONE, Entity

    return Entity(type=PHONE, start=0, end=11, text="13812345678", score=1, source="rule")
