"""presidio 兼容适配层：让 presidio 用户零成本迁移。

用法::

    from helan.compat_presidio import MianjuAnalyzer

    analyzer = MianjuAnalyzer()
    results = analyzer.analyze(text="证件号 11010519491231002X", entities=["ID_CARD"])
    for r in results:
        print(r.entity_type, r.start, r.end, r.score)

接口刻意对齐 presidio 的 `AnalyzerEngine.analyze`：
- 返回对象带 `.entity_type / .start / .end / .score / .analysis_explanation` 属性；
- `entities=None` 表示全部类型；`language` 参数接受但忽略（helan 只做中文，
  它就是你要配的那个中文 recognizer 包）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from .pipeline import recognize
from .types import ALL_TYPES, Entity


@dataclass
class RecognizerResult:
    """对齐 presidio 的 RecognizerResult 属性面。"""

    entity_type: str
    start: int
    end: int
    score: float
    analysis_explanation: str = ""
    recognition_meta: dict = field(default_factory=dict)

    @classmethod
    def from_entity(cls, e: Entity) -> RecognizerResult:
        return cls(
            entity_type=e.type,
            start=e.start,
            end=e.end,
            score=e.score,
            analysis_explanation=f"source={e.source}",
            recognition_meta=dict(e.meta),
        )


class MianjuAnalyzer:
    """presidio 风格的 AnalyzerEngine 替身。

    与 presidio 的语义差异（迁移时须知）：
    - 实体类型名是 helan 的（ID_CARD/BANK_CARD/...，全大写下划线，与 presidio 命名一致）；
    - 校验和级识别（身份证/银行卡/统一社会信用代码）presidio 没有——迁移后这些类型
      的 precision 会上升；
    - 不需要下载 NLP 模型，`language` 参数被忽略。
    """

    supported_entities: ClassVar[list[str]] = sorted(ALL_TYPES)
    supported_languages: ClassVar[list[str]] = ["zh", "en"]  # en 仅支持语言无关类型（邮箱/IP/URL/银行卡）

    def analyze(
        self,
        text: str,
        entities: list[str] | None = None,
        nlp_artifacts=None,
        language: str = "zh",
        min_score: float = 0.5,
        **kwargs,
    ) -> list[RecognizerResult]:
        _ = language, nlp_artifacts, kwargs  # 兼容签名，语义见类注释
        types = entities if entities else None
        return [
            RecognizerResult.from_entity(e) for e in recognize(text, types=types, min_score=min_score)
        ]
