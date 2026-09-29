"""helan 命令行：scan / mask / restore / eval。

示例：
  helan scan 合同.txt --json
  helan mask 合同.txt -o 脱敏.txt --ops ID_CARD:vault,PHONE:fake --vault-out vault.json
  helan restore 脱敏.txt --vault vault.json -o 还原.txt
  helan eval --write benchmarks/results.md
"""

from __future__ import annotations

import argparse
import sys

from .calibrate import render as calibrate_render
from .eval import run_report
from .io_utils import load_vault, mask_directory, read_text, write_text
from .pipeline import mask, recognize, restore


def _parse_ops(raw: str | None) -> dict[str, str] | None:
    if not raw:
        return None
    ops: dict[str, str] = {}
    for pair in raw.split(","):
        key, _, value = pair.strip().partition(":")
        if not key or not value:
            raise SystemExit(f"--ops 格式错误: {pair!r}（应为 类型:算子，逗号分隔）")
        ops[key] = value
    return ops


def _parse_types(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    return [item.strip() for item in raw.split(",") if item.strip()]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="helan", description="Helan：中文 PII 检测与脱敏")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="只识别，不替换")
    scan.add_argument("input")
    scan.add_argument("--json", action="store_true", help="输出 JSONL")
    scan.add_argument("--min-score", type=float, default=0.5)
    scan.add_argument("--types", help="逗号分隔的类型或组（如 ID_LIKE,PHONE）")

    mk = sub.add_parser("mask", help="脱敏并输出（input 可为 glob 模式批量）")
    mk.add_argument("input")
    mk.add_argument("-o", "--output", help="输出文件；批量模式下为输出目录")
    mk.add_argument("--ops", help="类型/组:算子 逗号分隔，如 ID_LIKE:vault,PHONE:fake")
    mk.add_argument("--types", help="逗号分隔的类型或组（如 ID_LIKE,PHONE）")
    mk.add_argument("--vault-out", help="可逆映射输出路径（配合 vault 算子）")
    mk.add_argument("--salt", default="helan")
    mk.add_argument("--min-score", type=float, default=0.5)

    rs = sub.add_parser("restore", help="还原占位符")
    rs.add_argument("input")
    rs.add_argument("--vault", required=True)
    rs.add_argument("-o", "--output", required=True)

    ev = sub.add_parser("eval", help="运行内置基准")
    ev.add_argument("--write", help="把 markdown 报告写入文件")

    cal = sub.add_parser("calibrate", help="PERSON_NAME 停用词黑名单校准")
    cal.add_argument("--write", help="把 markdown 报告写入文件")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.command == "scan":
        text = read_text(args.input)
        entities = recognize(text, types=_parse_types(args.types), min_score=args.min_score)
        if args.json:
            from .io_utils import entities_to_jsonl

            print(entities_to_jsonl(entities))
        else:
            for e in entities:
                print(f"{e.start:>6}-{e.end:<6} {e.type:<14} {e.score:.2f} {e.source:<9} {e.text}")
        return 0

    if args.command == "mask":
        types = _parse_types(args.types)
        ops = _parse_ops(args.ops)
        if any(ch in args.input for ch in "*?["):
            if not args.output:
                raise SystemExit("批量模式（glob 输入）需要 -o 输出目录")
            summary = mask_directory(args.input, args.output, ops, vault_dir=args.vault_out, salt=args.salt, min_score=args.min_score, types=types)
            failed = [s for s in summary if not s["ok"]]
            print(f"批量完成：{len(summary) - len(failed)} 成功 / {len(failed)} 失败 -> {args.output}", file=sys.stderr)
            for s in failed:
                print(f"  失败 {s['src']}: {s['error']}", file=sys.stderr)
            return 0 if not failed else 1
        text = read_text(args.input)
        masked, vault = mask(text, ops, types=types, salt=args.salt, min_score=args.min_score)
        write_text(args.output, masked)
        if args.vault_out:
            vault.save(args.vault_out)
        print(f"脱敏完成：{len(vault)} 个占位符 -> {args.output}", file=sys.stderr)
        return 0

    if args.command == "restore":
        vault = load_vault(args.vault)
        restored = restore(read_text(args.input), vault)
        write_text(args.output, restored)
        print(f"还原完成 -> {args.output}", file=sys.stderr)
        return 0

    if args.command == "calibrate":
        report_md = calibrate_render()
        if args.write:
            write_text(args.write, report_md)
            print(f"报告已写入 {args.write}", file=sys.stderr)
        else:
            print(report_md)
        return 0

    if args.command == "eval":
        report_md = run_report()
        if args.write:
            write_text(args.write, report_md)
            print(f"报告已写入 {args.write}", file=sys.stderr)
        else:
            print(report_md)
        return 0

    return 1
