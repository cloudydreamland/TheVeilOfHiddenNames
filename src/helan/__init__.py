"""Helan — 中文优先的 PII 检测与脱敏库。

快速上手::

    from helan import mask, restore, Vault

    masked, vault = mask(text, ops={"ID_CARD": "vault", "PHONE": "fake"})
    original = restore(masked, vault)
"""

from .pipeline import DEFAULT_OPS, build_recognizers, mask, recognize, restore
from .streaming import read_file_chunks, recognize_iter
from .types import (
    ADDRESS,
    ALL_TYPES,
    BANK_CARD,
    EMAIL,
    ENTITY_TYPES,
    ID_CARD,
    IP_ADDRESS,
    LANDLINE,
    LICENSE_PLATE,
    PASSPORT,
    PERSON_NAME,
    PHONE,
    URL,
    USCC,
    Entity,
)
from .vault import Vault

__version__ = "0.1.0"

__all__ = [
    "ADDRESS",
    "ALL_TYPES",
    "BANK_CARD",
    "DEFAULT_OPS",
    "EMAIL",
    "ENTITY_TYPES",
    "ID_CARD",
    "IP_ADDRESS",
    "LANDLINE",
    "LICENSE_PLATE",
    "PASSPORT",
    "PERSON_NAME",
    "PHONE",
    "URL",
    "USCC",
    "Entity",
    "Vault",
    "__version__",
    "build_recognizers",
    "mask",
    "read_file_chunks",
    "recognize",
    "recognize_iter",
    "restore",
]
