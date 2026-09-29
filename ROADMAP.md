# ROADMAP — 夜间自动化迭代驱动表

> 规则：自动迭代每一轮从上到下找第一个未勾选条目，完整做完（代码+测试+文档）再勾选。
> 每条目设计为一轮（≤45 分钟）可完成。做完更新 WORKLOG.md 并提交。
> 每轮固定动作：① 选条目实现；② **对抗评审**（以资深开发者/项目经理/老板三视角挑刺，可上网核查竞品与用户抱怨，结论写入 WORKLOG 的"评审记录"）；③ 有效批评转化为新条目追加到本表末尾；④ 全量 pytest + ruff 必须绿；⑤ 提交。

## 迭代条目

- [x] **iter0（2026-09-27 凌晨，主会话完成）**：12 类实体识别（校验和级：身份证/银行卡/统一社会信用代码/手机号段；规则级：座机/邮箱/IP/URL/护照/车牌；上下文级：人名/地址）、4 类算子（redact/partial/hash/fake）、可逆 Vault（全局一致占位符+精确还原）、冲突消解（优先级>长度>分数贪心）、偏移不变量 fuzz（64 seed）、CLI（scan/mask/restore/eval）、内置 12 篇语料评测（default 配置 F1=1.000）、LLM recognizer（OpenAI 兼容，偏移对齐安全阀，mock 测试）、151 项测试全绿 + ruff 清零。
- [x] **iter1 — 竞品实测取证**：真实安装 presidio(或读其源码)，写 `docs/presidio_zh.md`：用我们内置语料的同款实体测 presidio 中文表现，记录它能抓到什么/漏什么（如实，包括它做对的）；README"与现有方案的关系"表格据此更新为实测结论。若安装过重（>50MB 依赖），允许改为源码走读 + 记录走读证据。→ 完成：presidio-analyzer 2.2.364 真实安装（模式层直测，NER 层因网络无法下载模型未测并如实记录）；源码盘点 112 个识别器/18 国专项/中国 0 个；实测银行卡与邮箱满分、手机号默认 P 0.600、URL 误报 5 次、7/12 类型缺失；docs/presidio_zh.md + README 已更新。
- [x] **iter2 — 性能基准 + 大文本流式**：`helan.bench`：MB 级文本吞吐基准（当前 1.7-2.3M chars/s 单核），对比"纯正则基线"的耗时差距（如实报告校验和层的开销）；`recognize_iter` 流式 API：按行/块处理超大文件并跨块合并实体（ID 卡号跨行场景）；基准结果写 `benchmarks/perf.md`。→ 完成：**评审当场抓到并修复 resolver O(n²)**（2MB/3.3 万实体时 38.4s → 0.87s，2.35 MB/s，安全代价 2.8 倍）；`recognize_iter` 滑窗 API（回退保头 + 单游标去重），2MB 流式与整读 100% 一致，身份证任意切口跨窗测试通过；URL 加 512 上限匹配 overlap 约束；新增规模回归测试防 O(n²) 回潮；166 项测试全绿。
- [x] **iter3 — 遗漏实体与中文特有场景**：补 邮编(6位带边界)、QQ/微信号(前缀上下文)、港澳台证件、军官证格式；处理"数字中间有全角空格/点号分隔"的身份证写法；停用词黑名单扩充机制（`data.PERSON_NAME_BLOCKLIST` 的校准脚本：跑语料统计 FP 自动建议）。每类都要有正反测试。→ 完成：17 类型；TW 身份证（字母内码+性别位+11 权重 MOD 10，A123456789 经典向量通过）；全角空格/·/．/- 分隔身份证归一化过校验和；邮编/QQ/微信（关键词上下文）；军官证 format-only（meta 如实标注、score 0.6）；`helan calibrate` 校准命令（基于 gold 的真实 FP 统计，本轮语料 FP=0）；新增 2 篇散文体语料（iter2 评审要求），14 篇/48 gold 恢复满分；港澳原生格式**诚实未实现**（校验算法无权威样例，拒绝伪实现），18 位居住证(71/81/82 码)天然支持并有测试；194 项测试全绿。
- [x] **iter4 — NER 召回层**：jieba 人名识别的对比数据（开关 jieba 跑内置语料，如实记录召回变化进 benchmarks/results.md 新增列）；评估 LAC / HanLP 的许可与体积，写 `docs/ner_options.md` 选型结论；LLM recognizer 加批量与限速（复用 qiegao JudgeRunner 思路）。**（iter1 评审追加）presidio 兼容适配层**：提供 `MianjuAnalyzer.analyze(text, entities, language)` 风格 API（返回 score/start/end/entity_type 对象），让 presidio 用户零成本迁移，`docs/presidio_zh.md` 结尾加迁移示例。→ 完成：jieba 实测 PERSON P 1.000→0.700（6 个 FP：温馨提示/张江路/双肩包…），R 不变——**据此产品决策默认关闭 jieba 改显式 opt-in**，results.md 第三列如实展示代价（F1 0.920、吞吐掉 400 倍）；`docs/ner_options.md` 选型（LAC/HanLP/LTP 因体积/许可不内置）；LLM recognizer 加 max_per_second 限速 + 429/5xx 指数退避重试（400 不重试）；`compat_presidio.MianjuAnalyzer` + 5 项迁移测试 + 迁移示例；202 项测试全绿。
- [x] **iter5 — 打磨与 RC**：`mask_file` 批量接口（glob 目录）；`--types` 参数进 CLI；README 英文版段（README_EN.md，简洁版）；CHANGELOG 正式化；`python -m build` 出 sdist/wheel 验证；全量测试 + tag v0.1.0-rc1。→ 完成：`mask_directory`（glob 批量、单文件失败不中断、逐文件摘要）+ CLI `--types`/组名 + glob 输入模式；实体组常量 ID_LIKE/CONTACT/FINANCE/ONLINE（iter3 评审追加，types 与 ops 都吃组名）；jieba 装了未启用的一次性 UserWarning（iter4 评审追加）；README_EN.md；CHANGELOG rc1；py.typed 打包；build 出 wheel 验证（17 模块 + console_script + py.typed）；202 项测试全绿；tag v0.1.0-rc1。
- [ ] **iter6 — 发布工程**：launch_checklist（知乎/掘金/V2EX/安全社区群发文案要点）；PyPI 发布检查单（token、trusted publisher）；demo GIF/asciinema 脚本；给 2-3 个 RAG/Agent 开源项目提 issue/PR 建议集成（如实记录哪些回了）。
- [ ] **iter7 —（延伸）第二项目预研**：若以上全部完成：按同一 GAP_PROOF 方法启动"API 中转站模型验真工具"（见调研记录：45.83% 假模型实测、V2EX 半年 3+ 独立轮子），输出 GAP_PROOF 草稿与 iter0 计划，不动手写代码。

- [ ] **iter8 —（评审追加候补）mask_iter 流式脱敏**：读块→脱敏→写块，Vault 跨块共享与全局一致占位符；替换算子为 fake/partial 时直接流式输出，vault 占位符跨块去重；与 recognize_iter 共用滑窗参数；端到端测试：大文件流式脱敏产物与整读脱敏产物逐字符一致。

## 收尾条目

- [x] **wrap-up**：全量测试与 lint 最终确认；写 REPORT.md（夜间总结：完成清单、测试状态、诚实未完成项、给用户的下一步建议）；最终提交。（202 passed / ruff 0 error，2026-09-27 07:15）

## 用户醒来后的人工事项

- 注册 GitHub 仓库并 push；PyPI 发布需用户 token
- 中英文社区发布（launch_checklist 在 iter6）
- 若要跑 LLM recognizer 实测：设置 `MIANJU_LLM_API_KEY`
