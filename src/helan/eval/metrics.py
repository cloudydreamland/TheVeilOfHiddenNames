"""指标：span 级精确匹配为主口径，重叠命中为参考口径。"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..types import Entity
from .corpus import Doc


@dataclass
class TypeStats:
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tp_overlap: int = 0

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0


@dataclass
class Report:
    per_type: dict[str, TypeStats] = field(default_factory=dict)

    def stats(self, entity_type: str) -> TypeStats:
        return self.per_type.setdefault(entity_type, TypeStats())

    @property
    def micro(self) -> TypeStats:
        total = TypeStats()
        for stats in self.per_type.values():
            total.tp += stats.tp
            total.fp += stats.fp
            total.fn += stats.fn
            total.tp_overlap += stats.tp_overlap
        return total


def _overlaps(a: Entity, b: Entity) -> bool:
    return a.start < b.end and b.start < a.end


def evaluate(docs: list[Doc], predictions: dict[str, list[Entity]]) -> Report:
    """predictions: doc_id -> 识别结果。gold 与 pred 均按 (type,start,end) 精确匹配计 TP。"""
    report = Report()
    for doc in docs:
        gold = doc.gold
        pred = predictions.get(doc.doc_id, [])
        pred_matched: set[int] = set()
        gold_matched: set[int] = set()

        for i, g in enumerate(gold):
            stats = report.stats(g.type)
            hit = -1
            hit_overlap = -1
            for j, p in enumerate(pred):
                if p.type != g.type:
                    continue
                if (p.start, p.end) == (g.start, g.end):
                    hit = j
                    break
                if hit_overlap < 0 and _overlaps(p, g):
                    hit_overlap = j
            if hit >= 0:
                stats.tp += 1
                pred_matched.add(hit)
                gold_matched.add(i)
                stats.tp_overlap += 1
            else:
                stats.fn += 1
                if hit_overlap >= 0:
                    stats.tp_overlap += 1

        for j, p in enumerate(pred):
            if j not in pred_matched:
                report.stats(p.type).fp += 1
        _ = gold_matched
    return report
