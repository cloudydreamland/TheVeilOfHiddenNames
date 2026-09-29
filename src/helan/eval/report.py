"""评测报告：多配置对比，输出 markdown。数字如实，不做任何美化。"""

from __future__ import annotations

import time
from dataclasses import dataclass

from ..pipeline import build_recognizers, recognize
from .corpus import Doc, build_corpus
from .metrics import Report, evaluate


@dataclass
class ConfigResult:
    name: str
    report: Report
    seconds: float
    chars: int


def _run_config(docs: list[Doc], name: str, **kwargs) -> ConfigResult:
    recognizers = build_recognizers(**kwargs)
    start = time.perf_counter()
    predictions = {doc.doc_id: recognize(doc.text, recognizers=recognizers) for doc in docs}
    seconds = time.perf_counter() - start
    chars = sum(len(doc.text) for doc in docs)
    return ConfigResult(name=name, report=evaluate(docs, predictions), seconds=seconds, chars=chars)


def run_all() -> list[ConfigResult]:
    docs = build_corpus()
    results = [
        _run_config(docs, "checksum+rules（无上下文）", types=[
            "ID_CARD", "BANK_CARD", "USCC", "PASSPORT", "PHONE",
            "LANDLINE", "EMAIL", "IP_ADDRESS", "URL", "LICENSE_PLATE",
        ]),
        _run_config(docs, "default（含上下文人名/地址）"),
    ]
    try:
        import jieba  # noqa: F401

        has_jieba = True
    except ImportError:
        has_jieba = False
    if has_jieba:
        results.append(
            _run_config(docs, "default+jieba（NER 补召回，如实展示精度代价）", jieba=True)
        )
    return results


def _fmt_row(config: ConfigResult) -> str:
    micro = config.report.micro
    speed = config.chars / config.seconds / 1000 if config.seconds > 0 else 0.0
    return (
        f"| {config.name} | {micro.tp}/{micro.fp}/{micro.fn} "
        f"| {micro.precision:.3f} | {micro.recall:.3f} | {micro.f1:.3f} | {speed:.0f} |"
    )


def render_markdown(results: list[ConfigResult], docs: list[Doc]) -> str:
    total_entities = sum(len(doc.gold) for doc in docs)
    lines = [
        "# helan 内置基准结果",
        "",
        f"- 语料：{len(docs)} 篇合成中文文档 / {total_entities} 个 gold 实体（由合法假数据生成器构造，标注零噪声）",
        "- 口径：span 级 (type, start, end) 精确匹配；P=precision, R=recall, F1",
        "- 速度为单核 Python 吞吐（千字符/秒），仅数量级参考",
        "- 合成语料分布窄于真实业务文档，数字代表格式级能力上限，不外推",
        "",
        "| 配置 | TP/FP/FN | P | R | F1 | 速度(K chars/s) |",
        "|---|---|---|---|---|---|",
    ]
    lines.extend(_fmt_row(config) for config in results)
    lines.append("")
    lines.append("## 分类型明细（default 配置，即最后一行）")
    lines.append("")
    lines.append("| 类型 | TP | FP | FN | P | R | F1 |")
    lines.append("|---|---|---|---|---|---|---|")
    default = results[-1]
    for etype in sorted(default.report.per_type):
        stats = default.report.per_type[etype]
        lines.append(
            f"| {etype} | {stats.tp} | {stats.fp} | {stats.fn} "
            f"| {stats.precision:.3f} | {stats.recall:.3f} | {stats.f1:.3f} |"
        )
    return "\n".join(lines)


def main() -> str:
    docs = build_corpus()
    results = run_all()
    return render_markdown(results, docs)


if __name__ == "__main__":
    print(main())
