"""吞吐基准:helan 完整管线 vs 纯正则基线。

诚实口径:
- "纯正则基线"= 用与 helan 完全相同的正则抓候选,但**不做任何校验和验证、
  不做冲突消解**——它代表"手搓正则脱敏"的成本上限(它更快,但会产出大量误报)。
- 差值就是校验和验证 + 冲突消解的安全代价。
- 单核、CPython、Windows;数字只代表本机,不外推。
"""

from __future__ import annotations

import argparse
import random
import time

from .eval.corpus import build_corpus
from .pipeline import recognize

MACHINE = "Windows / CPython 3.13 / 单核"


def build_mixed_text(target_mb: float, seed: int = 2026) -> str:
    """语料文档 + 随机中文数字噪声,拼到目标大小。噪声保证正则层有真实扫描压力。"""
    rng = random.Random(seed)
    base_docs = [d.text for d in build_corpus()]
    filler_pool = (
        "本段为普通业务文本，用于模拟真实文档中的非敏感内容，包含数字 12345 与标点。",
        "会议决定、预算安排、项目进度、交付节点、验收标准等事项。",
        "The quick brown fox jumps over the lazy dog 9988776655.",
        "账户余额、汇率、结算周期、手续费率等财务信息。",
    )
    parts: list[str] = []
    total = 0
    target = int(target_mb * 1024 * 1024)
    while total < target:
        if rng.random() < 0.25:
            parts.append(rng.choice(base_docs))
        else:
            parts.append(rng.choice(filler_pool))
        total += len(parts[-1])
    return "\n".join(parts)


def regex_baseline_scan(text: str) -> int:
    """纯正则基线:与 helan 相同的正则抓候选,不验证、不消解。返回候选数。"""
    import re

    from helan.data import HONORIFICS, LEAD_WORDS, SURNAMES
    from helan.recognizers import chinese
    from helan.recognizers.base import guarded_pattern

    patterns = [
        re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+"),
        guarded_pattern(r"(?:\d{1,3}\.){3}\d{1,3}", left="0-9.", right="0-9"),
        re.compile(r"https?://[^\s<>\"'，。；！？、]{1,512}"),
        guarded_pattern(r"(?:0\d{2,3})-?[2-9]\d{6,7}"),
        guarded_pattern(r"\d{17}[0-9Xx]"),
        guarded_pattern(r"\d{15}"),
        guarded_pattern(r"\d{13,19}", right="0-9Xx"),
        guarded_pattern(r"1[3-9]\d{9}"),
        chinese._ADDR_RE,
    ]
    count = 0
    for pat in patterns:
        for _m in pat.finditer(text):
            count += 1
    _ = HONORIFICS, LEAD_WORDS, SURNAMES
    return count


def run(target_mb: float) -> dict:
    text = build_mixed_text(target_mb)
    size_mb = len(text) / 1024 / 1024

    t0 = time.perf_counter()
    entities = recognize(text)
    t1 = time.perf_counter()
    full_secs = t1 - t0

    t0 = time.perf_counter()
    candidates = regex_baseline_scan(text)
    baseline_secs = time.perf_counter() - t0

    return {
        "size_mb": size_mb,
        "entities": len(entities),
        "full_secs": full_secs,
        "full_mbps": size_mb / full_secs,
        "baseline_secs": baseline_secs,
        "baseline_mbps": size_mb / baseline_secs,
        "baseline_candidates": candidates,
        "machine": MACHINE,
    }


def render(result: dict) -> str:
    return (
        "# helan 性能基准\n\n"
        f"- 机器:{result['machine']}(数字只代表本机,不外推)\n"
        f"- 文本:{result['size_mb']:.2f} MB 合成混合文本(内置语料 25% + 普通业务噪声 75%)\n"
        f"- helan 完整管线(校验和+规则+上下文+消解):**{result['full_mbps']:.2f} MB/s**"
        f"({result['full_secs']:.2f}s,{result['entities']} 个实体)\n"
        f"- 纯正则基线(同正则、零校验、零消解,手搓方案的速度上限):{result['baseline_mbps']:.2f} MB/s"
        f"({result['baseline_secs']:.2f}s,{result['baseline_candidates']} 个未验证候选)\n"
        f"- **安全代价:完整管线比纯正则慢 {result['full_secs'] / result['baseline_secs']:.1f} 倍**——"
        "这个代价买的是误报治理(发票号不再被当成手机号)。\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="helan.bench")
    parser.add_argument("--mb", type=float, default=2.0)
    parser.add_argument("--write", help="markdown 结果写入路径")
    args = parser.parse_args(argv)
    result = run(args.mb)
    report = render(result)
    print(report)
    if args.write:
        from .io_utils import write_text

        write_text(args.write, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
