"""presidio 兼容适配层测试。"""

from __future__ import annotations

from helan.compat_presidio import MianjuAnalyzer, RecognizerResult


class TestMianjuAnalyzer:
    def test_attribute_surface_matches_presidio(self):
        analyzer = MianjuAnalyzer()
        results = analyzer.analyze(text="证件号 23144319731204692X 结束")
        assert any(
            r.entity_type == "ID_CARD" and hasattr(r, "start") and hasattr(r, "end") and hasattr(r, "score")
            for r in results
        )

    def test_entities_filter(self):
        analyzer = MianjuAnalyzer()
        results = analyzer.analyze(text="电话13812345678，证号23144319731204692X。", entities=["PHONE"])
        assert [r.entity_type for r in results] == ["PHONE"]

    def test_language_accepted_and_ignored(self):
        analyzer = MianjuAnalyzer()
        results = analyzer.analyze(text="电话13812345678。", language="zh")
        assert len(results) == 1

    def test_result_dataclass_fields(self):
        r = RecognizerResult(entity_type="PHONE", start=0, end=11, score=0.9)
        assert r.analysis_explanation == ""
        assert r.recognition_meta == {}

    def test_supported_entities_listed(self):
        analyzer = MianjuAnalyzer()
        assert "ID_CARD" in analyzer.supported_entities
        assert "PHONE" in analyzer.supported_entities
