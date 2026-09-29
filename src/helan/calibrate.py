"""停用词黑名单校准：在内置语料上找出 PERSON_NAME 的真实 FP，自动建议扩充。

原理：合成语料有零噪声 gold，所以这里统计的是**真实 FP**（不是猜测）：
- 逐条列出 FP 的触发 cue 与上下文；
- 按 `text[:2]` 聚合，出现 ≥2 次的前缀自动建议加入 `PERSON_NAME_BLOCKLIST`；
- 单次出现的 FP 交人工判断（宁可漏建议，不可误杀真人名）。

用法：`helan calibrate`（或 `python -m helan.calibrate`）。
"""

from __future__ import annotations

from collections import Counter

from .data import PERSON_NAME_BLOCKLIST
from .eval.corpus import build_corpus
from .pipeline import recognize


def collect_person_fps() -> list[dict]:
    """跑内置语料，收集 PERSON_NAME 的 FP（与 gold 不匹配的命中）。"""
    fps: list[dict] = []
    for doc in build_corpus():
        gold = {
            (g.start, g.end) for g in doc.gold if g.type == "PERSON_NAME"
        }
        for e in recognize(doc.text, jieba=False):
            if e.type == "PERSON_NAME" and (e.start, e.end) not in gold:
                fps.append(
                    {
                        "text": e.text,
                        "cue": e.meta.get("cue", "?"),
                        "doc": doc.doc_id,
                        "context": doc.text[max(0, e.start - 10) : e.end + 10].replace("\n", "|"),
                    }
                )
    return fps


def suggest_blocklist(fps: list[dict], min_count: int = 2) -> list[str]:
    """出现 ≥ min_count 次的两字前缀，自动建议加入黑名单。"""
    counter = Counter(fp["text"][:2] for fp in fps)
    return [prefix for prefix, n in counter.most_common() if n >= min_count]


def render() -> str:
    fps = collect_person_fps()
    lines = [
        "# PERSON_NAME 停用词黑名单校准报告",
        "",
        f"- 数据：内置语料（gold 零噪声），本次 FP 总数 **{len(fps)}**",
        f"- 现行黑名单规模：{len(PERSON_NAME_BLOCKLIST)} 条",
        "",
    ]
    if not fps:
        lines.append("当前语料上 PERSON_NAME 无 FP，黑名单无需扩充。")
        return "\n".join(lines)

    suggestions = suggest_blocklist(fps)
    lines.append("## 自动建议（出现 ≥2 次的前缀）")
    lines.append("")
    lines.append(f"`{suggestions}`" if suggestions else "无")
    lines.append("")
    lines.append("## 全部 FP 明细（单次出现者请人工判断）")
    lines.append("")
    lines.append("| 触发 cue | 文本 | 上下文 | 文档 |")
    lines.append("|---|---|---|---|")
    for fp in fps:
        lines.append(f"| {fp['cue']} | {fp['text']} | `{fp['context']}` | {fp['doc']} |")
    return "\n".join(lines)


def main() -> int:
    print(render())
    return 0


if __name__ == "__main__":
    main()
