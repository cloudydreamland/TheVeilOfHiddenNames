"""Vault：可逆脱敏的映射库。

占位符形如 ``<ID_CARD_1>``，同一 (type, text) 复用同一占位符——
这既是省空间的去重，也保证"同一身份证号在全文中被一致地假名化"。
序列化为 JSON，可落盘随脱敏产物一起交给有权限的一方做还原。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class Vault:
    prefix: str = ""
    mapping: dict[str, dict] = field(default_factory=dict)  # placeholder -> {type, text}
    _reverse: dict[tuple[str, str], str] = field(default_factory=dict, repr=False)

    def place(self, entity_type: str, text: str) -> str:
        key = (entity_type, text)
        existing = self._reverse.get(key)
        if existing is not None:
            return existing
        placeholder = f"<{self.prefix}{entity_type}_{len(self.mapping) + 1}>"
        self.mapping[placeholder] = {"type": entity_type, "text": text}
        self._reverse[key] = placeholder
        return placeholder

    def restore(self, masked_text: str) -> str:
        out = masked_text
        for placeholder, record in self.mapping.items():
            if placeholder in out:
                out = out.replace(placeholder, record["text"])
        return out

    def restore_json(self, data: str) -> str:
        """还原一个 JSON 文档中所有字符串值里的占位符（逐 key 浅处理）。"""
        return self.restore(data)

    def to_json(self) -> str:
        return json.dumps(
            {"prefix": self.prefix, "mapping": self.mapping},
            ensure_ascii=False,
            indent=2,
        )

    @classmethod
    def from_json(cls, raw: str) -> Vault:
        data = json.loads(raw)
        vault = cls(prefix=data.get("prefix", ""))
        for placeholder, record in data.get("mapping", {}).items():
            vault.mapping[placeholder] = record
            vault._reverse[(record["type"], record["text"])] = placeholder
        return vault

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.to_json())

    @classmethod
    def load(cls, path: str) -> Vault:
        with open(path, encoding="utf-8") as fh:
            return cls.from_json(fh.read())

    def __len__(self) -> int:
        return len(self.mapping)
