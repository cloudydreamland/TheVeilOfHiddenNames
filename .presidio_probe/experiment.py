"""iter1 实验脚本:presidio 模式识别层 vs helan,同一语料同一口径。

方法说明(诚实性):
- presidio 的 AnalyzerEngine 需要 spacy NER 模型(本次网络无法下载 GitHub 模型包),
  因此直接实例化其"语言无关"的 pattern 识别器(CreditCard/Email/Url/Ip/Phone)——
  这正是 presidio 在中文上**理论上能工作**的层,是最有利于 presidio 的测法。
  人名/地址(NER 层)未测:英文 NER 跑中文文本无意义,且 presidio 无中文专用识别器。
- PhoneRecognizer 跑两个变体:默认区号表(无 CN)与显式加 CN。
- 口径与 helan eval 一致:span 级 (type,start,end) 精确匹配。
"""

from __future__ import annotations

import sys

sys.path.insert(0, "src")
from helan.eval.corpus import build_corpus  # noqa: E402

from presidio_analyzer.predefined_recognizers import (  # noqa: E402
    CreditCardRecognizer,
    EmailRecognizer,
    IpRecognizer,
    PhoneRecognizer,
    UrlRecognizer,
)

# presidio entity -> helan entity 映射
MAP = {
    "CREDIT_CARD": "BANK_CARD",
    "EMAIL_ADDRESS": "EMAIL",
    "IP_ADDRESS": "IP_ADDRESS",
    "URL": "URL",
    "PHONE_NUMBER": "PHONE",
}

# 只对这 5 类比较(presidio 无中文身份证/统一社会信用代码/车牌/护照/人名/地址识别器)
COMPARABLE = {"BANK_CARD", "EMAIL", "URL", "IP_ADDRESS", "PHONE"}


# 每个识别器只对其对应类型的 gold 负责(FN 口径正确化)
REC_TYPES = {
    "credit_card": {"BANK_CARD"},
    "email": {"EMAIL"},
    "url": {"URL"},
    "ip": {"IP_ADDRESS"},
    "phone_default": {"PHONE"},
    "phone_cn": {"PHONE"},
}


def main():
    docs = build_corpus()
    recognizers = {
        "credit_card": CreditCardRecognizer(),
        "email": EmailRecognizer(),
        "url": UrlRecognizer(),
        "ip": IpRecognizer(),
        "phone_default": PhoneRecognizer(),
        "phone_cn": PhoneRecognizer(supported_regions=("CN",)),
    }
    totals = {name: {"tp": 0, "fp": 0, "fn": 0} for name in recognizers}
    interesting: list[str] = []

    for doc in docs:
        preds_by_rec = {}
        for name, rec in recognizers.items():
            try:
                raw = rec.analyze(doc.text, entities=None, nlp_artifacts=None)
            except Exception as exc:  # noqa: BLE001
                print(f"  [{name}] ERROR on {doc.doc_id}: {exc}", file=sys.stderr)
                raw = []
            preds_by_rec[name] = [
                (MAP.get(r.entity_type, r.entity_type), r.start, r.end, r.score) for r in raw
            ]

        for name, preds in preds_by_rec.items():
            own_gold = [g for g in doc.gold if g.type in REC_TYPES[name]]
            for etype, start, end, score in preds:
                hit = any(etype == g.type and start == g.start and end == g.end for g in own_gold)
                if hit:
                    totals[name]["tp"] += 1
                else:
                    totals[name]["fp"] += 1
                    ctx = doc.text[max(0, start - 12) : end + 12].replace("\n", "|")
                    interesting.append(f"[{name}] FP {etype} {score:.2f} {ctx!r} ({doc.doc_id})")
            for g in own_gold:
                if not any(
                    etype == g.type and start == g.start and end == g.end
                    for etype, start, end, _s in preds
                ):
                    totals[name]["fn"] += 1

    print("=== presidio 模式层实测(12 篇语料, 5 类可比实体, 精确匹配口径) ===")
    for name, t in totals.items():
        p = t["tp"] / (t["tp"] + t["fp"]) if (t["tp"] + t["fp"]) else 0
        r = t["tp"] / (t["tp"] + t["fn"]) if (t["tp"] + t["fn"]) else 0
        f1 = 2 * p * r / (p + r) if (p + r) else 0
        print(f"{name:14s} TP={t['tp']:3d} FP={t['fp']:3d} FN={t['fn']:3d}  P={p:.3f} R={r:.3f} F1={f1:.3f}")
    print("\n=== FP 样本(最多 20 条) ===")
    for line in interesting[:20]:
        print(line)


if __name__ == "__main__":
    main()
