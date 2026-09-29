# The Veil of Hidden Names — Helan

[English](README.md) · 简体中文

> 名字取自古英语 **helan**——「隐藏、遮蔽」，与 *heal*（完整、痊愈）同源：把敏感处藏好，数据才得完整。

**中文优先的 PII 检测与脱敏库。([English](README_EN.md))校验和级识别，可逆 Vault 还原，格式保留假名——把"数据喂给大模型前"这件事做成标准件。**

[![CI](https://github.com/cloudydreamland/TheVeilOfHiddenNames/actions/workflows/ci.yml/badge.svg)](.github/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## 为什么需要它 / Why

中国团队把数据喂给大模型（云端 API、RAG、微调）之前要做的第一件事是脱敏，而现状是：

- **微软 Presidio 每月 542 万次下载**，证明"LLM 管道脱敏"是刚需——但它对中文基本不可用（中文无空格分词、身份证/银行卡/统一社会信用代码的校验体系它一概不知）
- GitHub 上中文 PII 开源项目只有个位数、全部 100 star 以下、多数诞生于近几个月——**需求真实，无人做成**
- 国内团队现状：手搓正则。正则治不了误报（一串 18 位数字到底是不是身份证，正则说了不算，**校验算法说了算**）

`helan`（Helan）把这件事做成零依赖标准件：

- **校验和级识别**：身份证（GB 11643 MOD 11-2）、银行卡（Luhn）、统一社会信用代码（GB 32100 MOD 31-3）只有通过官方校验算法才算命中；手机号过号段表。纯正则方案从数学上无法做到
- **偏移不变量**：每个实体保证 `entity.text == source[start:end]`（fuzz 测试永久守护），脱敏结果可精确引用回原文
- **可逆 Vault**：占位符脱敏 + 精确还原的完整闭环；同一原文全局统一假名。"双向还原"是目前开源界的空白点
- **格式保留假名**：`fake` 算子生成的假身份证能通过身份证校验、假银行卡能通过 Luhn——替换后的数据仍是"合法格式"，适合造测试集与演示数据
- **零必装依赖**：核心纯 Python；jieba（人名 NER 补召回）与 LLM（语义级兜底）全部可选
- **自带评测**：内置 12 篇中文语料 + P/R/F1 报告，数字如实

## 安装 / Install

```bash
# 克隆仓库后，在项目根目录安装
python -m pip install .
# 发布到 PyPI 后也可直接安装；jieba 为可选功能
python -m pip install helan
python -m pip install ".[jieba]"
```

## 快速开始 / Quickstart

```python
from helan import mask, restore, recognize

text = "出租方张伟明（身份证 11010519491231002X，电话 13812345678）同意将房屋出租。"

# 只识别

for e in recognize(text):
    print(e.type, e.start, e.end, e.text)

# 可逆脱敏：身份证换成占位符，可精确还原

masked, vault = mask(text, ops={"ID_CARD": "vault"})
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

我们真实安装 presidio-analyzer 2.2.364 并用本库内置语料做了同口径实测（方法与完整数据：[docs/presidio_zh.md](docs/presidio_zh.md)）：

| 方案 | 实测/事实 |
|---|---|
| Presidio（微软） | 11k star、月下载 542 万，但 12 类实体中 7 类无识别器（无身份证/统一社会信用代码/车牌/座机）；手机号默认区号表不含 CN，实测 P 0.600（发票号、会员卡号被当手机号）；URL 识别器把邮箱域名误报 5 次。做对的：银行卡（含银联+Luhn）与邮箱满分 |
| 国内手搓正则 | 误报不可控（无校验和）、无还原闭环、无评测 |
| 企业级 AI 网关 | 面向大厂、重部署；个人开发者与小团队需要的是库级标准件 |
| maskit 等近期个人项目 | 验证了需求存在，但均未做偏移保证、校验和过滤与格式保留假名 |

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
    print(e.type, e.start, e.end, e.text)   # 绝对偏移，2MB 实测与整读 100% 一致
```

约束：单实体长度须小于 overlap（URL 已加 512 上限与之匹配）。

## 路线图 / Roadmap

见 [ROADMAP.md](ROADMAP.md)。当前 v0.1.0：17 类型识别（含台湾身份证校验和、全角分隔身份证写法）+ 4 类算子 + Vault 还原 + 内置评测 + 流式 API + 黑名单校准，194 项测试全绿。
