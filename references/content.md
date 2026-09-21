# 来源与内容契约

提取产物 source.json：{id,title,format,warnings,units:[{id,label,text}]}。book.md 对应 U1 等编号。PDF 使用文件页序；EPUB 使用 spine 文档序号与标题，不能编造印刷页码。助手记录每单元阅读覆盖，不把提取当阅读。

guide.json：
```json
{"title":"书名","author":"可核实作者","intro":"这本书讲什么","coverage":"实际阅读范围和缺口","spoilers":false,"synopsis":[{"title":"问题","text":"梗概","units":[1]}],"map":[{"title":"分支","text":"关系说明","units":[1]}],"diagrams":[{"title":"图题","type":"topics","nodes":[{"title":"节点一","text":"解释","units":[1]},{"title":"节点二","text":"解释","units":[2]}]}],"quotes":[{"text":"逐字短摘录","context":"上下文","unit":1}],"routes":[{"title":"先读哪里","text":"原因及前置内容","units":[1]}]}
```

synopsis/map/routes 各1–12项；diagrams 1–2幅，每图2–4节点；type 为 topics/sequence/contrast。顺序和对照必须有来源支持，否则用 topics；不编造数值、因果或人生曲线。quotes 0–8条、每条最多100字，逐字存在单个来源单元中；没有可靠原文时为空。示例不是实际交付内容。

知识类解释论证与边界；小说/传记保留事件、选择、冲突，不强套行动清单。原文、解释和外部背景分开。文案自然、具体，不堆“颠覆认知”或制造焦虑；引文不能润色后仍称原文。脚本只能检查结构与引文存在，助手负责语义和全书覆盖。
