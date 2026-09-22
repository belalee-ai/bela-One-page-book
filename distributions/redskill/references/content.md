# 内容与核对契约

## 文件关系

`source.json`：`{id,title,format,warnings,units:[{id,label,text}]}`。PDF 编号是文件页序，EPUB 是 spine 文档位置，不编造印刷页码。`book.md` 对应 U1 等编号。大型单元若无法完整读完，应在工作材料中可靠分段并保留原位置映射，变更后重建覆盖记录，不把部分阅读直接标为完整。

`reading.json`：`version`、`source_digest`、`units:[{id,status,note}]`。来源摘要是脚本对完整 source 对象稳定序列化后的 SHA-256。状态：unread/read/partial/unreadable/excluded。除 unread 外必须有说明；排除只能用于空白、目录等有理由不参与正文概览的单元，不用来掩盖漏读。每个来源单元恰有一条记录。引用的单元必须读完。

`guide.json`：沿用包内 [原创示例](../examples/guide.json)。必填 title/author/intro/coverage/spoilers/scope；scope 是 full 或 partial。synopsis/map/routes 各 1–12 个 `{title,text,units,evidence}` 节点。evidence 是 `[{unit:1,text:"该单元中的逐字原文"}]`，每个所引单元至少一个依据，每段最多 200 字。多处同样文字时当前定位首次出现；如会导致歧义，选取包含区别信息的原文。

结构图 diagrams 1–2 幅，type 为 topics/sequence/contrast，各 2–4 节点，节点同样带 evidence。无真实数值不画统计走势；顺序和因果必须有依据。

quotes 0–8 条，每条 `{text,context,unit}`，text 最多 100 字且逐字存在。原书金句不足时少放，不凑数。网页按每条依据/引文独立保存短上下文，即使来自同一页也不共用错误片段。不把原书全文放进分享页。

## 核对流程

助手逐章阅读后更新 reading；生成 guide 后，调用 prepare-review 生成 review 草稿。它绑定工具版本、source 摘要、guide 摘要和 reading 快照；semantic 和 spoiler_check 默认 pending。

语义核对要回看每条梗概、脑图关系、路线与短句解释对应原文，检查否定、条件、说话者、时间顺序和因果；核对完成后记录具体发现，并将 semantic.status 写为 reviewed。脚本只能核对逐字依据存在，不能判断其是否支持观点。即使人为伪填 reviewed 也不能让脚本获得语义判断能力。

剧透核对要检查原书标题是否准确，正文是否需隐藏；小说一般设置 spoilers:true，所有生成内容都进入确认门，不靠单个梗概折叠。spoiler_check.notes 记录判断。MD 阅读器可能不支持 details，纯文本里仍会看到结局；不要声称跨阅读器防剧透。

核对后 guide/source 再发生任何变更，摘要不一致会阻止 render，必须重新核对。完整导览要求所有单元 read 或有理由 excluded；partial 允许保留未读单元，网页自动显示实际计数与缺口。覆盖说明由整理者提供，台账不能证明模型绝对理解正确。

`review.json` 的 notes 不应含隐私或密钥；仅供工作目录审查，不随成品公开。生成只输出定位与短片段，不把长书全文装入 HTML。

## 选书页数据

render 交付的 books.json 带 format_version 与 generator_version。shelf 在写网页前校验版本、必需字段、引用 ID 和短上下文；缺失时说明重新生成，不产生伪成功网页。旧版交付目录须用当前版重新生成后再合并，不直接编辑版本号跳过检查。该检查只保证呈现数据结构，不代替正文语义核对。
