# 发布清单 — helan v0.1.0-rc1

> 产出就绪度：代码/测试/文档/wheel 已齐（见 REPORT.md）。本清单是"从 rc1 到被看见"的动作序列。

## 1. 仓库与 PyPI（机器步骤，10 分钟）

- [ ] GitHub 建空仓库（不要勾选自动生成 README），命名 `helan`
- [ ] `git remote add origin <URL> && git push -u origin main --tags`（tag v0.1.0-rc1 一起推）
- [ ] 仓库设置：About 栏描述 + topics（`pii` `chinese-nlp` `data-masking` `privacy` `llm` `compliance`）
- [ ] PyPI：`twine upload dist/*`（dist/ 已构建好；或配 trusted publisher 后从 GitHub Actions 发）
- [ ] PyPI 项目页：填 description、指向 GitHub

## 2. 首发内容物（第一天，2 小时）

- [ ] 知乎/掘金文章：《我们实测了 presidio 的中文 PII 能力：7 类实体没有识别器》——素材即 docs/presidio_zh.md，结尾自然引出 helan
- [ ] V2EX 发帖（分享创造节点）：标题突出"个保法 + 喂大模型前脱敏 + 离线零依赖"
- [ ] GitHub Discussions/README 置顶：快速上手 30 秒可复制
- [ ] 评测数字三处对齐检查：README / benchmarks/results.md / 文章

## 3. 一周内跟进

- [ ] 回应 issue 一律 24h 内（哪怕只是"已收到"）；star 者感谢
- [ ] 监控 PyPI 下载量与 referrer（验证 presidio 迁移层是否带来流量——iter4 评审的观测项）
- [ ] 3-5 个 RAG/Agent 项目提集成建议 issue（qiegao 同款打法：提供现成 patch 而非愿望）
- [ ] HN 投放：**等真实使用数据后**（下载量或第一个第三方案例），现在投只会一轮游

## 4. 已知诚实缺口（对外口径用）

- 评测为合成语料（标注零噪声但分布窄），数字代表格式级能力上限——README 已声明，对外宣发同样保持该口径
- LLM recognizer / jieba 数字来自 mock 与合成语料，无真实端点与真实分布验证
- 港澳原生证件格式未实现（拒绝伪校验，欢迎社区 PR + 测试向量）
- mask_iter 流式脱敏、实体组文档等在 ROADMAP iter8/后续排队
