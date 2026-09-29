"""可选：jieba 词性(nr=人名)识别器。未安装 jieba 时 `available()` 返回 False。"""

from __future__ import annotations

from ..types import PERSON_NAME, Entity

_JIEBA_ERR = "使用 jieba 人名识别需要安装可选依赖: pip install 'helan[jieba]'"


def available() -> bool:
    try:
        import jieba  # noqa: F401
    except ImportError:
        return False
    return True


def make_jieba_person_recognizer():
    """返回 recognizer: text -> list[Entity]。相邻 nr 词合并为一个人名。"""
    try:
        import jieba.posseg as pseg
    except ImportError as exc:  # pragma: no cover - 依赖缺失分支
        raise ImportError(_JIEBA_ERR) from exc

    def recognize(text: str) -> list[Entity]:
        out: list[Entity] = []
        run_start: int | None = None
        run_len = 0
        pos = 0
        for token in pseg.cut(text):
            word = token.word
            if token.flag == "nr":
                if run_start is None:
                    run_start = pos
                run_len += len(word)
            else:
                if run_start is not None:
                    out.append(
                        Entity(
                            type=PERSON_NAME,
                            start=run_start,
                            end=run_start + run_len,
                            text=text[run_start : run_start + run_len],
                            score=0.65,
                            source="ner",
                            meta={"tagger": "jieba"},
                        )
                    )
                    run_start, run_len = None, 0
            pos += len(word)
        if run_start is not None:
            out.append(
                Entity(
                    type=PERSON_NAME,
                    start=run_start,
                    end=run_start + run_len,
                    text=text[run_start : run_start + run_len],
                    score=0.65,
                    source="ner",
                    meta={"tagger": "jieba"},
                )
            )
        return out

    return recognize
