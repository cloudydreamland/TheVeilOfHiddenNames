"""大文本流式识别。

算法:滑窗 + 安全区提交 + 回退保头。
- 累积 chunk 直到 >= chunk_size;
- 安全区 = buffer[:-overlap],只提交"完全落在安全区内"的实体;
- 推进时窗口起点**回退 overlap 个字符**(保留跨界实体的头部),
  跨界实体在下一窗被完整重检;
- 重检产生的重复由单调 `last_emitted_end` 游标去重
  (消解后实体互不重叠,故游标判断是充分的);
- 结束时对剩余 buffer 做最后一次完整识别。

约束(诚实声明):**单实体长度必须小于 overlap**。URL 正则已加 512 字符上限,
默认 overlap=512 与之匹配;超过 overlap 的病态实体在窗口边界会漏检。
流式结果与整读结果在窗口边界附近可能存在极小冲突消解差异。
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

from .pipeline import recognize
from .types import Entity

DEFAULT_CHUNK_SIZE = 65536
DEFAULT_OVERLAP = 512  # 必须大于可检测实体的最大长度(URL 上限 512)


def read_file_chunks(path: str, encoding: str = "utf-8", chunk_size: int = DEFAULT_CHUNK_SIZE) -> Iterator[str]:
    """按字符块读取文本文件,供 recognize_iter 使用。"""
    with open(path, encoding=encoding) as fh:
        while True:
            block = fh.read(chunk_size)
            if not block:
                break
            yield block


def recognize_iter(
    chunks: Iterator[str] | Callable[[], Iterator[str]],
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
    min_score: float = 0.5,
    types: list[str] | tuple[str] | None = None,
    jieba: bool | None = None,
    llm_recognizer=None,
) -> Iterator[Entity]:
    """流式识别:输入 chunk 迭代器,输出绝对偏移的 Entity 迭代器。

    实体保证偏移不变量、互不重叠、按绝对位置升序。
    """
    if callable(chunks) and not hasattr(chunks, "__next__"):
        chunks = chunks()
    if overlap >= chunk_size:
        raise ValueError("overlap 必须小于 chunk_size")
    if overlap < 16:
        raise ValueError("overlap 过小会切断长实体(18 位身份证要求 overlap >= 18, 建议 >= 256)")

    buffer = ""
    base = 0  # buffer[0] 的绝对偏移
    last_emitted_end = 0  # 已提交实体的最大绝对终点(去重+顺序游标)

    for chunk in chunks:
        buffer += chunk
        if len(buffer) < chunk_size:
            continue
        safe_end = len(buffer) - overlap
        limit_abs = base + safe_end
        for e in recognize(buffer, types, min_score=min_score, jieba=jieba, llm_recognizer=llm_recognizer):
            abs_start = e.start + base
            abs_end = e.end + base
            if abs_end <= limit_abs and abs_start >= last_emitted_end:
                last_emitted_end = abs_end
                yield Entity(
                    type=e.type,
                    start=abs_start,
                    end=abs_end,
                    text=e.text,
                    score=e.score,
                    source=e.source,
                    meta=e.meta,
                )
        keep_from = max(0, safe_end - overlap)  # 回退保头:跨界实体的头部留在窗口里
        buffer = buffer[keep_from:]
        base += keep_from

    for e in recognize(buffer, types, min_score=min_score, jieba=jieba, llm_recognizer=llm_recognizer):
        abs_start = e.start + base
        if abs_start >= last_emitted_end:
            last_emitted_end = e.end + base
            yield Entity(
                type=e.type,
                start=abs_start,
                end=e.end + base,
                text=e.text,
                score=e.score,
                source=e.source,
                meta=e.meta,
            )
