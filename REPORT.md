# REPORT — helan 夜间自动化迭代总结（2026-09-27 00:50 → 07:15）

> 执行方式：主会话完成 iter0（完整项目初版），此后 5 轮自动化迭代（每小时一轮，防并发锁 + 每轮三视角对抗评审）。
> 全程未 push 远程；所有提交在本地 `main`，tag `v0.1.0-rc1`。

## 一句话总结

**helanv0.1.0-rc1 完成**：中文优先的 PII 检测与脱敏库，17 类实体（5 类带官方校验和）、4 类脱敏算子、可逆 Vault、流式识别、presidio 兼容层、内置评测与基准；202 项测试全绿，ruff 清零，wheel 构建验证通过。选题经四路真实调研（GitHub API 竞品取证 + PyPI 下载量 + 中文社区 + 多模态垂直领域）交叉验证。

## 每轮完成清单

| 轮次 | 时间 | 完成内容 | 测试 |
|---|---|---|---|
| iter0 | 00:50–02:00 | 完整项目：12 类实体、4 算子、Vault、CLI、评测（F1 1.000）、LLM 识别器 | 151 |
| iter1 | 02:15–02:40 | **presidio 2.2.364 真实安装实测**：112 个识别器/18 国专项/中国 0 个；同口径对比：银行卡与邮箱满分、手机号默认 P 0.600、7/12 类型缺失；docs/presidio_zh.md | 151 |
| iter2 | 03:15–03:40 | `recognize_iter` 流式（2MB 与整读 100% 一致）；**bench 首跑抓到 resolver O(n²)**：38.4s→0.87s（2.35 MB/s）；`helan.bench` + perf.md | 166 |
| iter3 | 04:15–04:45 | +5 类实体（17 类）：邮编/QQ/微信/台湾身份证（校验和）/军官证（format-only）；全角分隔身份证；`helan calibrate`；散文体语料 | 194 |
| iter4 | 05:15–05:21 | **jieba 实测：PERSON P 1.000→0.700** → 默认关闭改 opt-in；LLM 限速+指数退避；presidio 兼容层 `MianjuAnalyzer` + 迁移指南；ner_options.md | 202 |
| iter5 | 06:15–06:20 | 实体组（ID_LIKE 等，types/ops 都吃组名）；批量脱敏 `mask_directory` + CLI glob；jieba 一次性提示；README_EN；py.typed；wheel 验证；tag rc1 | 202 |
| wrap-up | 07:15 | 最终确认（202 passed / ruff 0）+ 本报告 | 202 |

## 关键数字（全部真实运行，出处见对应文档）

- 内置评测（14 篇/48 gold，含散文体）：default 配置 **P 1.000 / R 1.000 / F1 1.000**；+jieba 配置 P 0.885（代价如实展示）
- 性能（2MB 混合文本，单核）：**2.35 MB/s**，比纯正则基线慢 3.0 倍（误报治理的代价）
- 竞品实测：presidio 中文场景 7/12 类型无识别器、手机号默认 P 0.600；银行卡/邮箱层它确实能打（如实记录）
- 安全性质：偏移不变量（64 seed fuzz + 逐位变异必败）、全 vault 还原闭环 fuzz、身份证任意切口跨窗流式

## 夜间抓到的真 bug（评审/测试当场修复）

1. resolver O(n²)（3.3 万实体 38 秒）→ bisect O(n log n)，并加规模回归测试
2. 流式首版切头缺陷（跨窗实体永远无法识别）→ 回退保头 + 单调游标去重
3. TW 身份证权重少 1 个（zip 截断，校验位没进求和）→ 200 生成向量自测当场全挂后修复
4. 人名识别的"姓名阻断"“为连接词”、“房间号”FP（房是真姓氏）→ 引导词表 + 连接词 + 停用词黑名单机制
5. 17 位身份证前缀碰巧过 Luhn 产生幻影银行卡 → 银行卡右守卫加 Xx
6. 银行分组正则、座机区号歧义切分、IP 尾部句点误拦——均为测试先行的真实修复

## 诚实未完成项

1. **iter6（发布工程）未执行**：launch_checklist、PyPI 发布、demo 脚本、集成外联。原因：07 点窗口按协议收尾；且 PyPI 发布需要你的账号 token（安全边界，不代做）。
2. **iter7（第二项目预研）未执行**：协议规定仅在"全部完成且 7 点前"触发，本轮未满足。
3. LLM recognizer 与 jieba 数字均来自 mock/合成语料，无真实端点与真实分布验证。
4. 港澳原生证件格式未实现（校验算法无权威样例，拒绝伪实现——见 test_iter3 留白测试）。
5. iter8 候补（mask_iter 流式脱敏）在 ROADMAP 排队。

## 给你的下一步建议（按优先级）

1. **注册 GitHub 仓库并 push**：`cd helan && git remote add origin <url> && git push -u origin main --tags`（tag v0.1.0-rc1 已就位）。
2. **PyPI 发布**：`python -m build` 产物已在 `dist/`；用你的 token `twine upload dist/*`（或配 trusted publisher）。包名 `helan` 已验证可用（00:55 查询 404）。
3. **发布内容物现成**：README（含 presidio 实测表）+ docs/presidio_zh.md 可直接改写成知乎/掘金文章《我们实测了 presidio 的中文 PII 能力》；launch_checklist 在 qiegao 的方法论里照搬即可。
4. **若要跑 LLM 兜底识别**：`set MIANJU_LLM_API_KEY=<key>` 后用 `LLMRecognizer`；实测前建议先跑 docs/eval_guide 思路的小规模验证。
5. **一个提醒**：qiegao 与 helan 现在都是"待发布"状态。建议先集中火力把 helan 推出去（需求更宽、时点更新），qiegao 跟进，两个仓库互相导流。

## 工作流复盘（对你个人的价值）

这套"ROADMAP 驱动 + 每小时对抗评审 + 诚实 WORKLOG + 测试/lint 门禁"的夜间流程，5 轮共抓出 6 个真 bug（含 2 个设计级缺陷），每一轮的评审质疑都转化成了具体改进。它就是当初调研里那个"只有你能做"的方向的活证据——helan 的仓库本身就是这套方法的 demo。
