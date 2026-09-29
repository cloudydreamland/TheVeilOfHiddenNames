"""文件 IO：批量脱敏 / 实体导出。"""

from __future__ import annotations

import glob
import json
import os

from .pipeline import mask
from .types import Entity
from .vault import Vault


def read_text(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def write_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def mask_file(
    src: str,
    dst: str,
    ops: dict[str, str] | None = None,
    *,
    vault_path: str | None = None,
    salt: str = "helan",
    min_score: float = 0.5,
) -> Vault:
    text = read_text(src)
    masked, vault = mask(text, ops, salt=salt, min_score=min_score)
    write_text(dst, masked)
    if vault_path:
        vault.save(vault_path)
    return vault


def entities_to_jsonl(entities: list[Entity]) -> str:
    lines = [
        json.dumps(
            {
                "type": e.type,
                "start": e.start,
                "end": e.end,
                "text": e.text,
                "score": e.score,
                "source": e.source,
            },
            ensure_ascii=False,
        )
        for e in entities
    ]
    return "\n".join(lines)


def load_vault(path: str) -> Vault:
    return Vault.load(path)


def mask_directory(
    pattern: str,
    out_dir: str,
    ops: dict[str, str] | None = None,
    *,
    vault_dir: str | None = None,
    salt: str = "helan",
    min_score: float = 0.5,
    types: list[str] | tuple[str] | None = None,
) -> list[dict]:
    """按 glob 模式批量脱敏文件，输出到 out_dir（保持文件名）。

    返回逐文件摘要 [{src, dst, vault, ok, error}]；单文件失败不中断批量，
    错误如实记录在摘要里。
    """
    os.makedirs(out_dir, exist_ok=True)
    if vault_dir:
        os.makedirs(vault_dir, exist_ok=True)
    summary: list[dict] = []
    for src in sorted(glob.glob(pattern)):
        if os.path.isdir(src):
            continue
        dst = os.path.join(out_dir, os.path.basename(src))
        vault_path = os.path.join(vault_dir, os.path.basename(src) + ".vault.json") if vault_dir else None
        try:
            text = read_text(src)
            masked, vault = mask(text, ops, types=types, salt=salt, min_score=min_score)
            write_text(dst, masked)
            if vault_path:
                vault.save(vault_path)
            summary.append({"src": src, "dst": dst, "vault": vault_path, "ok": True, "error": "", "placeholders": len(vault)})
        except Exception as exc:  # noqa: BLE001 - 批量场景下单文件失败不中断
            summary.append({"src": src, "dst": dst, "vault": vault_path, "ok": False, "error": str(exc), "placeholders": 0})
    return summary
