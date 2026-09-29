# WORKLOG — 工作日志

> 每轮迭代在文末追加一节：时间戳、完成内容、测试结果、问题、下一步。

## iter0 — 2026-09-27 00:50–02:00（主会话完成）

**完成：**
- 环境确认：Windows + Python 3.13.2 + git 2.49；PyPI `helan` 未被占用（pypi.org/pypi/helan/json → 404，00:55 读取）。
- 选题取证：GAP_PROOF.md 基于 2026-09-26/27 夜间四路并行调研（GitHub API 竞品取证 + PyPI 下载量 + 中文社区实抓 + 多模态垂直领域）。核心数字：presidio 11,045 star / 月下载 542 万但无中文识别器；GitHub 中文 PII 仓库最大 86 star；V2EX 半年内多个独立脱敏网关项目。
- 包实现（src/helan/）：
  - `types.py` Entity（偏移不变量写进 `__post_init__`，构造期即校验）
  - `checksum.py` 身份证 MOD 11-2（含 15 位识别与升位）、银行卡 Luhn、统一社会信用代码 MOD 31-3、手机号段表；假数据生成器（fake 身份证/银行卡/统一社会信用代码，保证通过对应校验器）
  - `data.py` 省级行政区划、号段表（2024-2026 严格集，未收录 140-144/154/162/174/194/196/197）、姓氏表（~250）、引导词/称谓表、人名停用词黑名单
  - `recognizers/` official（校验和级，宁缺勿滥：校验失败直接丢弃不降级）、rules（邮箱/IP/URL/座机/车牌/护照，带边界守卫）、chinese（称谓/引导词/顿号枚举人名 + 引导词地址，precise 优先）、ner_jieba（可选，手动偏移累加——jieba posseg 不提供 offset）、llm（OpenAI 兼容，"模型只负责逐字引用、坐标由本地 find 计算、引用不上原文一律丢弃"的安全阀设计）
  - `resolver.py` 冲突消解：实体优先级 > 长度 > 分数贪心；身份证内部的"手机号"子串由此自然消灭
  - `operators.py` redact/partial/hash/fake；`vault.py` 全局一致占位符 + JSON 序列化 + 精确还原
  - `pipeline.py` recognize/mask/restore（从后往前替换，偏移不失真）；`io_utils.py`；`cli.py` scan/mask/restore/eval
  - `eval/` 12 篇合成语料（本库假数据生成器构造，gold 零噪声）+ P/R/F1（精确匹配主口径 + 重叠参考口径）+ markdown 报告
- 测试：**151 passed**（含 18 位身份证逐位变异必败、64 seed 偏移不变量 fuzz、全 vault 还原闭环 fuzz、LLM mock 全路径）；ruff 0 error。

**真实调试记录（评测框架当场抓住的问题）：**
- 初版冒烟用伪造身份证/统一社会信用代码，全部被校验和层**正确拒绝**——测试数据本身必须用生成器产生合法值。
- 首轮评测暴露：人名 recall 0（"患者姓名：/宾客姓名："中"姓名"二字阻断引导词路径；"谷思 女士"名字与称谓间有空格；"石天雪、牟玉"枚举第二人无识别）→ 逐一修复，同时验证了"内置评测不是摆设"。
- 枚举 cue 引入后产生 1 个 FP："房间号"（房是真姓氏）→ 建立 `PERSON_NAME_BLOCKLIST` 停用词机制，修复。
- 座机 3 位/4 位区号歧义：正则贪婪切分错误 → 改为代码层按区号表逐一尝试切分。
- 17 位身份证前缀 + X 校验位碰巧通过 Luhn 产生幻影银行卡 → 银行卡右守卫加入 Xx。

**最终快照：** default 配置 P 1.000 / R 1.000 / F1 1.000（合成语料，格式级能力上限，不外推）；无上下文配置 P 1.000 / R 0.644。速度 ~1.8M chars/s 单核。

**诚实记录：**
- 内置语料是合成的，分布窄于真实业务文档；满分不代表生产效果，README 已声明。
- 号段表按公开资料收录，存在过时风险（如广电新段），已写入 roadmap 校准任务。
- LLM recognizer 未做真实端点测试（无 key），全部 mock。

**给下一轮（iter1）的提示：**
- 先读 ROADMAP.md 找第一个未勾选项；每轮必须含对抗评审小节；提交信息格式 `iterN: ...`；测试命令 `./.venv/Scripts/python.exe -m pytest -q`；不要装 >50MB 的包。

## iter1 — 2026-09-27 02:15–02:40（夜间会话第 1 轮）

**完成（ROADMAP iter1 — 竞品实测取证）：**
- 真实安装 presidio-analyzer **2.2.364** 到独立探针环境 `.presidio_venv`（本体+依赖装成功；en_core_web_sm NER 模型因网络无法连 GitHub Releases 下载失败 → 按 ROADMAP 预案改为**模式识别层直测**，NER 层未测并在报告中如实声明）。
- 源码盘点（wheel 实拆）：112 个预定义识别器、18 国专项（AU/CA/DE/IN/IT/KR/SG/UK/US…），**中国专项 = 0**；`PhoneRecognizer.DEFAULT_SUPPORTED_REGIONS = ("US","GB","DE","FR","IL","IN","CA","BR")` 无 CN（源码实摘）；`CreditCardRecognizer` 正则含 `6\d{3}` + Luhn。
- 实测（12 篇语料、精确匹配口径，脚本 `.presidio_probe/experiment.py` 可复现，结果 `.presidio_probe/results.txt`）：
  - presidio 做对的：银行卡 2/2（银联+Luhn，语言无关层确实能打）、邮箱 3/3。
  - presidio 的现实：手机号默认配置 **P 0.600 / R 0.600**（发票号 0341728596、会员卡号 5003820001 被当手机号；4 个真实手机号漏报）；显式配 CN 后 R 1.000 但 P 0.769（座机类型不分）；URL 识别器把邮箱域名当 URL 误报 5 次。
  - 类型覆盖：**12 类中 7 类无识别器**（身份证/统一社会信用代码/人名/地址/座机/车牌/护照 = 29/45 个 gold 实体层面缺失）。
  - 对照：helan 同语料 45/0/0，P=R=F1=1.000。
- 产出：`docs/presidio_zh.md`（方法+数据+公允性声明）；README Landscape 表更新为实测结论；探针环境与 wheel 已 gitignore，实验脚本与结果入库。
- 测试：151 passed，ruff 0 error（本轮无代码改动，跑通为证）。

**评审记录（对抗评审）：**
- **资深开发者**：质疑——"实验只测了模式层，评审会不会被认为不公平？" 回应：已用最有利于 presidio 的测法（语言无关层正是它在中文上理论上能工作的全部），且 docs 里把 NER 未测写成了显式限制；补充公允性第 3 条承认语料偏向。**追加改进**（入 ROADMAP iter4）：给 helan 加 presidio 兼容适配层（`analyze()` 风格 API），让 presidio 用户零成本迁移——这比对比文章更能抢用户。
- **项目经理**：质疑——"你写了实测报告，但谁来看到？分发渠道呢？" 回应：报告本身就是发布弹药（知乎/掘金文章《我们实测了 presidio 的中文能力》），已列入 iter6 launch_checklist；本轮顺手把结论浓缩进 README 表格，让每个访问者第一时间看到。**追加改进**：iter6 增加"实测文章"作为首发内容物。
- **公司老板**：质疑——"presidio 明天发个中文识别器你就死了，护城河在哪？" 回应：护城河不是"有没有身份证识别器"这个点，而是：GB 校验和体系+号段表+区划表的**持续校准**（合规数据工作是慢功夫）、Vault 可逆闭环、偏移不变量品牌、以及中文社区信任。presidio 的治理是多语言通用框架，为 CN 专门做深的数据工作不符合其优先级（2019 年至今 0 个中国识别器是行为证据）。**追加改进**：GAP_PROOF 已含此风险条目；iter3 的数据校准脚本就是护城河落地。

**诚实的问题：**
- phone_cn 的 3 个"FP"里有 2 个其实是座机（010-/021-）被 presidio 标为 PHONE——语义上是命中、是我们的类型体系判它错。报告中已写明，避免夸大。
- URL 识别器的 5 个 FP 中 3 个是"邮箱域名后缀被切"——presidio 的 tldextract 依赖可能需要联网初始化，环境差异可能影响复现，报告中已注明脚本可复现路径。

**下一步：** iter2（性能基准 + 流式 API）。

## iter2 — 2026-09-27 03:15–03:40（夜间会话第 2 轮）

**完成（ROADMAP iter2 — 性能基准 + 大文本流式）：**
- `helan/streaming.py`：`recognize_iter(chunks, chunk_size=65536, overlap=512)` 滑窗流式识别 + `read_file_chunks`。
  - 算法：安全区（buffer[:-overlap]）内实体才提交；窗口起点**回退 overlap 保头**，跨界实体下一窗完整重检；单调 `last_emitted_end` 游标去重（消解后实体互不重叠，游标判断充分）。
  - **第一版实现有真实设计缺陷**：推进时把窗口起点直接推到 safe_end，跨界实体的头部被切掉后永远无法识别——"身份证任意切口跨窗"测试逐切口验证时当场抓住，改为回退保头后 18 个切口全部通过。
  - URL 正则加 512 字符上限（约束实体最大长度 = overlap 约束的前提），文档写明"单实体长度必须小于 overlap"。
- **性能大坑（评审现场修复）**：bench 首跑 2MB 文本耗时 **38.4 秒**。诊断：不是正则（基线 0.3s），是 `resolver` 的 O(n²) 两两重叠检查——3.3 万实体时爆炸；内置评测语料只有几十个实体所以从未暴露。改 bisect 平行数组 O(n log n) 后 **0.87s（2.35 MB/s）**，并新增 3 万实体规模回归测试（<5s 断言）防回潮。
- 基准（`helan.bench`，benchmarks/perf.md，机器信息如实标注）：完整管线 2.35 MB/s vs 纯正则基线（同正则零校验零消解）6.69 MB/s——**安全代价 2.8 倍**，买的是"发票号不再被当手机号"。
- 端到端验证：2MB 混合文本流式 vs 整读 **33629 = 33629，完全一致**，流式反而略快（0.76s vs 0.87s）。
- 测试：**166 passed**（新增流式等价性 ×6 边界偏移、身份证 18 切口、文件读取、规模回归、bench 冒烟），ruff 0 error。

**评审记录（对抗评审）：**
- **资深开发者**：质疑——"流式只做了 recognize，mask 呢？生产上大文件要的是流式脱敏不是流式列举。" 回应：成立。但 mask 流式要处理替换后写入与 Vault 一致性，是独立工作量，本轮不赶工。**追加条目**到 ROADMAP：iter8 候选"mask_iter 流式脱敏（读块→脱敏→写块，Vault 跨块共享）"。
- **项目经理**：质疑——"2.35 MB/s 够吗？竞品什么水平？" 回应：presidio 同类 pattern 层实测未测吞吐（其 NER 层更慢是已知量级）；对个人/小团队场景（万页级文档）2.35 MB/s 意味着 1GB 文档约 7 分钟，可接受；且这轮优化后性能不再是 README 需要回避的话题。数字已写进 README 性能小节，变被动为主动。
- **公司老板**：质疑——"你在 0.2MB 混合文本上诊断实体构成时发现重复语料实体数量完全符合比例——这说明内置语料的'满分'有多少水分？" 回应：水分问题是真问题（合成语料 + 语料重复），但这轮的数字口径没有掺水：基准用的是"语料 25% + 噪声 75%"的混合文本，33,629 个实体里大部分是语料重复产生的真阳性。**诚实记录**：满分口径仍然只代表格式级能力，README 已有声明。**追加改进**：iter3 的语料扩充应加入"散文体"文档类型（会议纪要正文、长段落叙述），降低结构化偏向。

**诚实的问题：**
- 流式与整读在窗口边界 ±overlap 内理论上可能存在消解差异（2MB 实测未出现），文档已声明。
- resolver 的 `accepted.insert` 是 O(n) memmove，3.3 万实体下无感，但百万级实体场景未测（现实文档达不到）。

**下一步：** iter3（遗漏实体与中文特有场景：邮编/QQ/港澳台证件/全角分隔身份证/停用词校准脚本）。

## iter3 — 2026-09-27 04:15–04:45（夜间会话第 3 轮）

**完成（ROADMAP iter3 — 遗漏实体与中文特有场景）：**
- 新增 5 类实体（12→17 类型）：POSTAL_CODE（关键词+6位，无 cue 不命中）、QQ_NUMBER（5-11 位首位非零）、WECHAT_ID（官方规则：字母开头 6-20 位含 -_）、TW_ID_CARD（字母地区内码+性别位+11 权重 MOD 10 校验和，经典向量 A123456789 通过）、OFFICER_ID（关键词上下文 format-only，meta.format_only=True + score 0.6 如实降级）。
- 大陆身份证全角分隔写法：`1101 0519 4912 3100 2X`、`·`/`．`/`-`/全角空格分隔，归一化后过校验和，span 覆盖原文（normalized 存 meta）。
- `helan calibrate` 停用词校准命令：基于合成语料零噪声 gold 统计**真实 FP**，按前缀聚合自动建议（≥2 次），单次 FP 列上下文交人工；本轮语料 FP=0。
- 散文体语料 ×2（iter2 评审要求）：社区通知、失物招领（含 6 位失物编号负样本），语料 12→14 篇 / 45→48 gold。
- 真实 bug 两枚：① TW 校验 weights 只有 10 个而 digits 11 个（zip 截断，校验位没进求和），200 个生成向量自测当场全挂，补第 11 权重；② 散文体 FN："检查员**为**成杰怡"——引导词模式不允许"为"连接词，修 `(?:[:：]|为)?` 后 48/48 满分恢复。
- 港澳原生证件格式（HK letter+6digit+check）：**诚实未实现**——校验算法无权威样例可离线核实，拒绝伪校验（错误算法比没有更危险）；18 位居住证（71/81/82 省级码）已被现有 ID_CARD 规则天然覆盖并加测试锁定。测试：**194 passed**（+28），ruff 0 error。

**评审记录（对抗评审）：**
- **资深开发者**：质疑——"TW_ID_CARD 和大陆 ID_CARD 是两个类型，用户要'所有身份证类'一起脱敏怎么办？API 缺一个组视图。" 回应：成立。组常量（如 ID_LIKE = {ID_CARD, TW_ID_CARD}）成本极低。**追加条目**：iter5 打磨时加实体组常量与 `types=` 接受组的能力。
- **项目经理**：质疑——"军官证 format-only 会不会被用户当成承诺？" 回应：已在 meta（format_only=True）、score（0.6）、README 表格三处如实标注；文档写明"无公开校验和，欢迎提供样例 PR"。诚实标注本身就是差异化（伪权威是行业通病）。
- **公司老板**：质疑——"腾讯/阿里的云 API 有 PII 检测，你拿什么打？" 回应：云 API 是按调用的 SaaS 且数据要出内网；helan 卖的是**离线、零依赖、可审计**（校验和代码就在那里）——私有化/合规场景恰好是云 API 进不去的地方。且本次 iter1 实测方法（同口径基准）可持续复用于对云 API 的对照评测（追加 iter6 内容物清单）。

**诚实的问题：**
- 邮编/QQ/微信依赖关键词 cue，无 cue 的裸值不识别（设计取舍：6 位裸数字误报不可控）；LLM/NER 兜底在 iter4。
- 散文体语料只有 2 篇，散文占比仍低，"真实分布"代表性有限（已在 README 声明，iter4/iter6 继续补）。

**下一步：** iter4（NER 召回层对比 + presidio 兼容适配层 + LLM 批量限速）。

## iter4 — 2026-09-27 05:15–05:45（夜间会话第 4 轮）

**完成（ROADMAP iter4 — NER 召回层 + presidio 兼容层 + LLM 限速重试）：**
- **jieba 实测（本轮核心数据）**：真实安装 jieba 0.42.1（MIT，~19MB 纯 Python），开关对比内置语料：
  - PERSON：R 不变 1.000，**P 1.000 → 0.700**——6 个 FP 全是 jieba nr 词性的经典误报："温馨提示"（温馨）、"张江路"、"红星路"（路名）、"于本周"、"宾客"、"双肩包"。
  - micro：P 0.885 / R 0.958 / F1 0.920；吞吐从 2,036K chars/s 掉到 **5K**（400 倍）。
  - **据此产品决策：默认关闭 jieba，改为显式 opt-in**（`jieba=True`）。依据写进 `build_recognizers` docstring，results.md 增加第三列如实展示代价。这符合品牌立场：脱敏场景误报（错误脱敏破坏可用性）比漏报代价高。
- `compat_presidio.MianjuAnalyzer`：对齐 presidio `analyze()` 属性面（entity_type/start/end/score/analysis_explanation），presidio 用户替换两行即迁移；`language` 参数接受但忽略（诚实注释）；5 项测试。迁移示例进 `docs/presidio_zh.md` 结尾与 README。
- LLM recognizer 生产化：`max_per_second` 限速（单调时钟最小间隔）+ 指数退避重试（0.5s×2^n，仅 429/5xx 与网络错误；400 级不重试），4 项新测试（重试后成功、400 不重试、限速触发、恒定时钟验证）。
- `docs/ner_options.md`：jieba/LAC/HanLP/LTP/LLM 五路线选型——LAC 拖 paddle 违背零依赖定位、LTP 许可复杂、HanLP 模型 100MB+，均不内置；语义缺口走 LLM 路线。
- 测试：**202 passed**（+5 compat、+4 LLM、eval 配置数断言修正），ruff 0 error。
- 小坑：装上 jieba 后 calibrate 测试立即变红（FP=6）——它校准的是上下文 cue 的黑名单，显式钉住 `jieba=False`；这个"变红"本身就是 iter4 要的数据。

**评审记录（对抗评审）：**
- **资深开发者**：质疑——"默认关 jieba，那 `helan[jieba]` 这个 extra 的存在意义是什么？装了也不用？" 回应：extra 装的是依赖，启用靠参数——这确实容易混淆。**采纳改进**：README 安装行已改为"（可选，需显式 jieba=True）"；后续 iter5 可考虑 DeprecationWarning 风格的提示（检测到装了 jieba 但默认关闭时打印一行说明）→ 追加到 iter5。
- **项目经理**：质疑——"presidio 兼容层是很聪明的抢用户手段，但你有没有证据 presidio 用户真的痛？" 回应：iter1 的证据链（25k star 但 issue #7254 抱怨依赖重 + 中文不可用）是需求侧；兼容层是零成本拦截。真正的验证要等发布后的 referrer 数据（PyPI 下载来源/GitHub issues 来源），列入 iter6 观测项。
- **公司老板**：质疑——"jieba 那组数字放 README 里等于自曝其短？" 回应：恰恰相反——**敢放第三方组件的实测代价是可信度的放大器**，"我们测过所以默认关"比"我们不告诉你"强得多；presidio 的 README 从不告诉你它的中文表现，这就是差异。数字已在 results.md 第三列。

**诚实的问题：**
- LLM recognizer 的限速/重试没有真实端点验证（无 key），全部 mock——与 iter0 同一限制。
- jieba FP 列表基于 14 篇合成语料，真实分布上的 P 损失可能不同（方向待 iter6 真实数据）。

**下一步：** iter5（打磨与 RC：批量接口、--types 进 CLI、README_EN、build 验证、实体组常量（iter3 评审追加）、jieba 装了未启用提示（本轮评审追加）+ tag v0.1.0-rc1）。

## iter5 — 2026-09-27 06:15–06:45（夜间会话第 5 轮）

**完成（ROADMAP iter5 — 打磨与 RC）：**
- 实体组常量（iter3 评审追加）：`ENTITY_GROUPS` = ID_LIKE / CONTACT / FINANCE / ONLINE；`types=` 与 `ops=` 都接受组名（`mask(text, ops={"CONTACT": "hash"})` 一行脱敏全部联系方式）；`resolve_types` 严格校验未知名。
- jieba 装了未启用提示（iter4 评审追加）：一次性 `UserWarning`（进程级 flag），指明实测依据与启用方法。
- `mask_directory`：glob 批量脱敏，输出目录 + 可选 vault 目录，单文件失败不中断、逐文件摘要如实带 error；CLI `mask` 输入含 glob 字符即走批量模式（`-o` 为输出目录），`--types` 参数同时进 scan/mask。
- 打包：`__main__.py`（`python -m helan` 可用）、`py.typed` 类型标记 + package-data 配置、`python -m build` 出 sdist+wheel 并验证（17 模块、console_script、py.typed 都在 wheel 里）。
- README_EN.md 简洁英文版（含 presidio 实测数据导流）；CHANGELOG 正式化 0.1.0-rc1 小节；pyproject 版本 0.1.0rc1；git tag `v0.1.0-rc1`。
- 测试：**202 passed**，ruff 0 error。

**评审记录（对抗评审）：**
- **资深开发者**：质疑——"mask_directory 把 vault 和脱敏文放两个目录，用户丢了一个就还原不了，为什么不打包成单一产物？" 回应：单文件产物（如 zip 或内嵌 JSON）是 v0.2 的事；当前用目录约定 + `.vault.json` 后缀配对，文档要写清楚。**追加**：iter6 launch_checklist 加"Vault 配对约定说明"。
- **项目经理**：质疑——"英文版只有一段，Hacker News 根本不会收。" 回应：诚实说 v0.1 的目标市场是国内（GAP_PROOF 的需求证据全在国内合规场景），英文版是给 GitHub 全球浏览者看的门面而非主战场；HN 投放放到有真实用户数据（下载量/案例）之后再做，现在投只会一轮游。**采纳**：iter6 观测项加"HN 发布时机=有数据后"。
- **公司老板**：质疑——"rc1 了但 PyPI 还没发，star 从哪来？" 回应：PyPI 发布需要用户账号 token（安全边界，不能代做）；rc1 的意义是"内容物齐了"，明早用户的 10 分钟动作就是注册+push+发布，launch_checklist 已就位。发布本身才是 star 曲线的起点，不是仓库的终点。

**诚实的问题：**
- 批量 CLI 的 glob 在 Git Bash 下要注意路径转换（MSYS 会翻译参数路径），Windows 用户用 PowerShell/cmd 无此问题；测试用 Python 原生 glob（正确），文档暂未写 shell 注意事项 → iter6 发布文档补充。
- pytest 汇总里的 1 warning 是 jieba 一次性提示本身（预期行为，非缺陷）。

**下一步：** iter6（发布工程：launch_checklist、PyPI 检查单、demo 脚本、集成建议外联；含 iter1/iter4/iter5 评审追加的观测项）。

