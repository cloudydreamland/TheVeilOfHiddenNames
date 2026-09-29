"""冲突消解：多个 recognizer 会命中重叠 span，按 优先级 > 长度 > 分数 贪心保留。

实体优先级刻画"这是谁的菜"：一张 18 位身份证内部出现的 11 位数字不该再算手机号；
一个统一社会信用代码内部的子串不该再算其他东西。包含关系由此自然消解。

性能：候选排序 O(n log n)；重叠检查用 bisect 在已接受集合（互不重叠、有序）上
做 O(log n) 判定——2MB 文本 3 万+ 实体时，O(n²) 两两比较会拖到 40 秒量级（已踩过）。
"""

from __future__ import annotations

from bisect import bisect_right

from .types import (
    ADDRESS,
    BANK_CARD,
    EMAIL,
    ID_CARD,
    IP_ADDRESS,
    LANDLINE,
    LICENSE_PLATE,
    OFFICER_ID,
    PASSPORT,
    PERSON_NAME,
    PHONE,
    POSTAL_CODE,
    QQ_NUMBER,
    TW_ID_CARD,
    URL,
    USCC,
    WECHAT_ID,
    Entity,
)

# 数值越大越优先
PRIORITY: dict[str, int] = {
    ID_CARD: 90,
    TW_ID_CARD: 88,
    BANK_CARD: 85,
    USCC: 85,
    PASSPORT: 80,
    PHONE: 70,
    EMAIL: 70,
    LANDLINE: 65,
    LICENSE_PLATE: 60,
    PERSON_NAME: 50,
    ADDRESS: 40,
    URL: 30,
    IP_ADDRESS: 30,
    QQ_NUMBER: 35,
    WECHAT_ID: 35,
    OFFICER_ID: 45,
    POSTAL_CODE: 25,
}


def resolve(entities: list[Entity], min_score: float = 0.5) -> list[Entity]:
    """贪心消解：按 (优先级, 长度, 分数) 降序逐一收编，与已收编重叠的丢弃。

    返回按 start 升序、互不重叠的实体列表。
    """
    candidates = [e for e in entities if e.score >= min_score]
    candidates.sort(
        key=lambda e: (
            -PRIORITY.get(e.type, 0),
            -(e.end - e.start),
            -e.score,
            e.start,
        )
    )
    accepted: list[Entity] = []
    starts: list[int] = []  # 与 accepted 平行，按 start 升序
    ends: list[int] = []
    for cand in candidates:
        i = bisect_right(starts, cand.start) - 1  # start <= cand.start 的最后一个
        if i >= 0 and ends[i] > cand.start:
            continue  # 与前一个已接受实体重叠
        j = i + 1  # start > cand.start 的第一个
        if j < len(starts) and starts[j] < cand.end:
            continue  # 与后一个已接受实体重叠
        accepted.insert(j, cand)
        starts.insert(j, cand.start)
        ends.insert(j, cand.end)
    accepted.sort(key=lambda e: (e.start, e.end))
    return accepted
