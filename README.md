# The Veil of Hidden Names — Helan

简体中文 · [English](README.en.md)

> 展示名 **The Veil of Hidden Names** 意为“隐名之幕”；Helan 是该项目的短名。

**中文优先的 PII 检测与脱敏库。校验和级识别，可逆 Vault 还原，格式保留假名——帮助你在把数据交给大模型或其他服务前发现并处理敏感信息。**

[![PyPI](https://img.shields.io/pypi/v/helan)](https://pypi.org/project/helan/)
[![Python](https://img.shields.io/pypi/pyversions/helan)](https://pypi.org/project/helan/)
[![CI](https://github.com/cloudydreamland/TheVeilOfHiddenNames/actions/workflows/ci.yml/badge.svg)](https://github.com/cloudydreamland/TheVeilOfHiddenNames/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

![helan 演示：识别 → 可逆脱敏 → 精确还原（真实运行输出）](docs/assets/demo.svg)

## 为什么需要它 / Why

在将中文业务文本送入 LLM、RAG 或其他外部处理服务前，开发者常需要识别并处理个人信息。通用识别框架可扩展，但中文证件校验、误报控制和可恢复脱敏通常需要额外规则与评测。

`helan`（Helan）把这件事做成零依赖标准件：

- **格式校验**：对身份证、银行卡和统一社会信用代码应用相应校验规则，减少仅凭位数与字符模式产生的误报；其他实体依赖上下文规则，仍可能漏检或误报
- **偏移不变量**：每个实体保证 `entity.text == source[start:end]`（fuzz 测试永久守护），脱敏结果可精确引用回原文
- **可逆 Vault**：用占位符脱敏并通过受保护的 Vault 还原；Vault 含有恢复敏感信息，必须与原文同等保护
- **格式保留假名**：`fake` 算子生成的假身份证能通过身份证校验、假银行卡能通过 Luhn——替换后的数据仍是"合法格式"，适合造测试集与演示数据
- **零必装依赖**：核心纯 Python；jieba（人名 NER 补召回）与 LLM（语义级兜底）全部可选
- **自带评测**：内置 12 篇中文语料 + P/R/F1 报告，数字如实

## 安装 / Install

```bash
python -m pip install helan
python -m pip install "helan[jieba]"  # 可选增强，按需安装
```

从源码安装（开发或最新版）：

```bash
git clone https://github.com/cloudydreamland/TheVeilOfHiddenNames.git
cd TheVeilOfHiddenNames
python -m pip install .
```

## 快速开始 / Quickstart

```python
from helan import mask, restore, recognize

text = "出租方张伟明（身份证 11010519491231002X，电话 13812345678）同意将房屋出租。"

# 只识别

for e in recognize(text):
    print(e.type, e.start, e.end, e.text)

# 可逆脱敏：只处理身份证，占位符可精确还原
# （types 限定识别范围；不传 types 时所有类型按默认算子脱敏）

masked, vault = mask(text, ops={"ID_CARD": "vault"}, types=["ID_CARD"])
original = restore(masked, vault)
assert original == text

# 不可逆脱敏：手机号换成"合法格式"的假号码

masked, _ = mask(text, ops={"PHONE": "fake"})
```

命令行：

```bash
helan scan 合同.txt --json            # 只识别
helan mask 合同.txt -o 脱敏.txt --ops ID_CARD:vault,PHONE:fake --vault-out vault.json
helan restore 脱敏.txt --vault vault.json -o 还原.txt
helan eval                            # 内置基准报告
```

## 实体类型与算子

| 类型 | 识别方式 | 默认算子 |
|---|---|---|
| ID_CARD 身份证 | 区划+出生日期+MOD 11-2 校验码 | partial（前3后4） |
| BANK_CARD 银行卡 | Luhn 校验（支持空格/连字符分组） | partial（留后4） |
| USCC 统一社会信用代码 | GB 32100 MOD 31-3 校验 | partial |
| PHONE 手机号 | 号段表严格校验 | partial（138\*\*\*\*5678） |
| PERSON_NAME 人名 | 称谓/引导词/顿号枚举上下文；jieba nr 可选 | partial（张\*\*） |
| ADDRESS 地址 | 引导词上下文 | redact |
| LANDLINE / EMAIL / IP / URL / PASSPORT / LICENSE_PLATE | 规则+守卫 | partial/redact |
| TW_ID_CARD 台湾身份证 | 地区字母码+性别位+加权 MOD 10 校验 | partial |
| POSTAL_CODE / QQ / 微信号 / OFFICER_ID | 关键词上下文（军官证为 format-only，如实标注） | redact/partial |
| ID_CARD 全角/符号分隔写法 | 1101 0519 4912 3100 2X 等分隔归一化后过校验和 | partial |

算子：`redact`（标签替换）/ `partial`（部分保留）/ `hash`（加盐稳定假名）/ `fake`（合法格式假数据）/ `vault`（可逆占位）/ 任意自定义 callable。

## 与现有方案的关系 / Landscape

我们曾用固定版本的 `presidio-analyzer` 与本项目内置语料做对照。测试范围、配置、语料及局限见[方法和完整结果](docs/presidio_zh.md)；这些结果只适用于该次设置，不代表所有 Presidio 中文部署：

| 方案 | 实测/事实 |
|---|---|
| Presidio 等通用框架 | 提供可配置的识别与匿名化管线；中文效果取决于所选 recognizer、规则和评测语料 |
| 自定义正则 | 易于嵌入，但需要自行实现格式校验、上下文规则、偏移处理和评测 |
| Helan | 聚焦中文规则、原文偏移以及多种脱敏算子；适用范围和评测边界见下文 |

选题取证（为什么这个缺口是真的）见 [GAP_PROOF.md](GAP_PROOF.md)。

## 评测 / Evaluation

内置基准（14 篇中文合成文档（含散文体）/ 48 个 gold 实体）真实结果：[benchmarks/results.md](benchmarks/results.md)

- 当前快照：default 配置 **P 1.000 / R 1.000 / F1 1.000**；无上下文配置 R 0.644（人名/地址全靠上下文层）
- **诚实声明**：语料为合成文档（由本库假数据生成器构造，标注零噪声），分布窄于真实业务文档，数字代表格式级能力上限，不外推为生产效果

## 性能 / Performance

2MB 混合文本、单核（[benchmarks/perf.md](benchmarks/perf.md)）：完整管线 **2.35 MB/s**（3.4 万实体），比"同正则、零校验"的手搓基线慢 2.8 倍——这个代价买的是误报治理。

## 从 presidio 迁移 / Migration

```python
from helan.compat_presidio import MianjuAnalyzer

results = MianjuAnalyzer().analyze(text="证件号 23144319731204692X", entities=["ID_CARD"])
for r in results:
    print(r.entity_type, r.start, r.end, r.score)   # 属性面与 presidio 一致
```

## 大文本 / Streaming

```python
from helan import recognize_iter, read_file_chunks

for e in recognize_iter(read_file_chunks("huge.txt"), chunk_size=65536, overlap=512):
    print(e.type, e.start, e.end, e.text)   # 返回绝对偏移；该测试样本与整读结果一致，详见性能报告
```

约束：单实体长度须小于 overlap（URL 已加 512 上限与之匹配）。

## 路线图 / Roadmap

见 [ROADMAP.md](ROADMAP.md)。当前 v0.1.0：17 类型识别（含台湾身份证校验和、全角分隔身份证写法）+ 4 类算子 + Vault 还原 + 内置评测 + 流式 API + 黑名单校准，194 项测试全绿。
