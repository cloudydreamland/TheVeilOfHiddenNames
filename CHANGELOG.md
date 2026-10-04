# CHANGELOG

## 0.1.0 (2026-10-05)

首个稳定版。功能与 0.1.0rc1 一致；本版统一包内 `__version__` 与 PyPI 发布版本
（此前 rc1 包内显示 0.1.0，存在不一致），README 安装说明更新为 PyPI 安装优先。

## 0.1.0-rc1 (2026-09-27)

自 0.1.0-alpha 起新增：

- 5 类实体（12→17）：POSTAL_CODE / QQ_NUMBER / WECHAT_ID / TW_ID_CARD（校验和）/ OFFICER_ID（format-only）
- 大陆身份证全角/符号分隔写法支持（空格/·/．/-/全角空格归一化后过校验和）
- `helan calibrate`：PERSON_NAME 停用词黑名单校准（基于 gold 的真实 FP 统计）
- `recognize_iter` / `read_file_chunks`：大文本流式识别（回退保头 + 单调游标去重，2MB 与整读 100% 一致）
- `helan.bench`：吞吐基准（2.35 MB/s vs 纯正则 3 倍安全代价）+ resolver O(n²) 修复（38.4s→0.87s）
- `compat_presidio.MianjuAnalyzer`：presidio 兼容适配层（同 .analyze() 属性面）
- LLM recognizer：max_per_second 限速 + 429/5xx 指数退避重试
- jieba NER 实测（PERSON P 1.000→0.700）→ **默认关闭，显式 opt-in**；装了未启用会有一次性提示
- 实体组常量：ID_LIKE / CONTACT / FINANCE / ONLINE（types 与 ops 均可用组名）
- CLI：`--types`、glob 批量脱敏（mask_directory，单文件失败不中断）
- 语料扩至 14 篇（含散文体）/ 48 gold；测试 202 项；实测报告 docs/presidio_zh.md、docs/ner_options.md

## 0.1.0 (2026-09-27)

- 12 类中文 PII 实体识别：身份证/银行卡/统一社会信用代码（校验和级）、手机号（号段表）、座机/邮箱/IP/URL/护照/车牌（规则级）、人名/地址（上下文级，jieba 与 LLM 可选补召回）
- 4 类脱敏算子：redact / partial / hash（加盐稳定假名）/ fake（校验和合法的格式保留假数据）
- 可逆 Vault：全局一致占位符、精确还原、JSON 落盘
- 冲突消解：优先级 > 长度 > 分数贪心；偏移不变量 fuzz 守护
- CLI：scan / mask / restore / eval
- 内置评测：12 篇中文合成语料，P/R/F1 双口径报告
- 151 项测试，ruff 0 error
