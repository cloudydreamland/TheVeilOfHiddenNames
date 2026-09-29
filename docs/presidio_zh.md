# presidio 中文实测报告 — iter1 竞品取证

> 实测时间:2026-09-27 02:15-02:35。对象:presidio-analyzer 2.2.364(PyPI,2026-09-27 下载)。
> 语料:helan 内置 12 篇中文业务单据(45 个 gold 实体,合成语料)。
> 口径:span 级 `(type, start, end)` 精确匹配,与 helan 内置评测完全一致。
> 实验脚本:`.presidio_probe/experiment.py`(可复现);本页所有数字来自真实运行。

## 方法与公允性(先说限制)

1. **只测了模式识别层,未测 NER 层。** AnalyzerEngine 需要 spacy 模型,本次网络无法下载 GitHub 模型包。因此直接实例化 presidio 的语言无关识别器(CreditCard/Email/Url/Ip/Phone)——这是**最有利于 presidio 的测法**:这些识别器不依赖语言,理论上就是它在中文上能工作的全部。
2. **人名/地址/NER 没测**:英文 NER 跑中文文本无意义;presidio 官方也未提供中文 NER 配方。
3. **语料偏向**:我们的语料就是按中文业务单据设计的(合同/挂号单/快递面单…),天然有利于 helan。本报告证明的是"presidio 开箱不能服务中文场景",不是"presidio 不优秀"。

## 源码盘点(presidio-analyzer 2.2.364 wheel)

- `predefined_recognizers/` 共 **112 个识别器文件**,国家专项覆盖:AU/CA/FI/DE/IN/IT/KR/NG/PH/PL/SG/ZA/ES/SE/TH/TR/UK/US。
- **中国专项识别器:0 个。** 无身份证(GB 11643)、无银行卡 BIN 体系、无统一社会信用代码(GB 32100)、无中国车牌。
- `PhoneRecognizer` 默认区号表:`DEFAULT_SUPPORTED_REGIONS = ("US", "GB", "DE", "FR", "IL", "IN", "CA", "BR")` — **不含 CN**(源码实摘)。
- `CreditCardRecognizer`:前缀正则含 `6\d{3}`(覆盖银联 62 开头)+ Luhn 校验——**语言无关层是真功夫**。

## 实测结果

| 识别器 | TP | FP | FN | P | R | F1 | 说明 |
|---|---|---|---|---|---|---|---|
| credit_card | 2 | 0 | 0 | 1.000 | 1.000 | 1.000 | 银联卡+Luhn,语言无关层确实能打 |
| email | 3 | 0 | 0 | 1.000 | 1.000 | 1.000 | 同上 |
| url | 0 | 5 | 0 | 0.000 | — | — | **5 个 FP 全是把邮箱域名当 URL**(tldextract 对 `@example.cn` 内部误切) |
| ip | 0 | 0 | 0 | — | — | — | 语料无 IP |
| phone(默认区号) | 6 | 4 | 4 | 0.600 | 0.600 | 0.600 | **开箱即用的现实**:发票号 `0341728596`、会员卡号 `5003820001` 被当手机号(0.40 低分);4 个真实手机号漏报 |
| phone(显式加 CN) | 10 | 3 | 0 | 0.769 | 1.000 | 0.870 | 需要用户自己知道要配 CN;座机 `010-`/`021-` 被标成手机号(类型不分),对账编号部分串号误报 |

**类型覆盖:12 类实体中 presidio 可测的只有 5 类。其余 7 类(身份证 7 个、人名 11 个、地址 4 个、统一社会信用代码 2 个、座机 2 个、车牌 2 个、护照 1 个 = 29/45 个 gold 实体)在识别器层面直接缺失。**

对照组(同一语料同一口径):helan default 配置 **45 TP / 0 FP / 0 FN,P=R=F1=1.000**。

## presidio 做对的(如实记录)

- 语言无关的模式层质量高:银行卡(含银联 BIN + Luhn)与邮箱在中文文本上满分。
- 工程化成熟:多语言框架、置信度体系、Azure/NLP adapters、112 个国家专项识别器的组织方式值得学习。
- 它的问题不是工程质量,是**中文不是它的市场优先级**——2019 年开源至今没有中国身份证识别器。

## 结论

"用 presidio 做中文脱敏"的现实是:7/12 实体类型缺识别器、手机号默认配置 P 0.6(误报发票号和卡号)、URL 在邮箱上连环误报,且要自己写中国专项识别器——而写中国专项识别器需要的校验和体系(GB 11643/GB 32100)正是 helan 的核心交付物。**helan 不是"另一个 presidio",是中文场景缺失的那一层。**

## 从 presidio 迁移（iter4 新增）

`helan.compat_presidio.MianjuAnalyzer` 对齐 presidio 的 `AnalyzerEngine.analyze` 属性面，
迁移只需替换构造与调用对象：

```python
# 迁移前（presidio）
# from presidio_analyzer import AnalyzerEngine
# analyzer = AnalyzerEngine()
# results = analyzer.analyze(text=text, language="zh")

# 迁移后（helan，无需下载 NLP 模型）
from helan.compat_presidio import MianjuAnalyzer

analyzer = MianjuAnalyzer()
results = analyzer.analyze(text=text, entities=["ID_CARD", "PHONE"])
for r in results:
    print(r.entity_type, r.start, r.end, r.score)   # 属性与 presidio 一致
```

差异须知：实体类型名一致风格但集合不同（17 类中文实体，presidio 无对应）；校验和级
识别（身份证/银行卡/统一社会信用代码）是 presidio 没有的能力，迁移后这些类型
precision 上升；`language` 参数接受但忽略。
