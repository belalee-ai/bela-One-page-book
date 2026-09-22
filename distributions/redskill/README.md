# 一页读书 · REDSkill 0.2 候选包

把书整理成有出处的梗概、脑图、短句和阅读路线，并可在 PDF 原书里划线和记笔记。与 GitHub 0.2 版共用核心代码；**代码已打包，不代表已通过小红书平台审核或完整获取链路实测。**

## 怎么使用

1. 在支持文件读取和脚本执行的助手中启用此 Skill，提供 PDF、EPUB、TXT 或 Markdown。MOBI 需要转换工具，扫描件需要 OCR；没有执行环境先交付文字导览。
2. 让助手提取正文、分章阅读、核对出处，再生成网页。可一次提供多本，逐本生成后合并到选书页。
3. 文字导览可双击 HTML 打开。要在 PDF 划线，保留整个交付目录，让助手运行里面的 `python start_reader.py`，打开显示的本机地址，再添加生成导览时用的同一份 PDF。
4. 摘录自动保存，默认显示最新 4 条，可展开。只显示首次标注日期；按最近修改时间排列。需要迁移时导出进度与标注，不用每天点保存。

[PDF 划线详细步骤](docs/pdf-annotations.md) · [本次检查与待测项](docs/release-0.2.md) · [制作来源与致谢](references/credits.md)

网页没有模型调用，新增书籍仍在助手对话中处理。EPUB/MOBI 可以制作导览，当前原文标注仅支持可选择文字的 PDF。五种风格为马蒂斯、莫兰迪、旧书纸张、瑞士极简和夜读。

## 平台不接受怎么办

包内有 Markdown、Python、JavaScript、MJS、WASM 等代码和资源。平台是否允许、读者是否能运行，必须以实际上传和获取测试为准。若平台不接受完整包，不改后缀或隐藏代码绕过限制；在平台分享使用说明与 GitHub 安装入口，或者只提供文字导览。

公开安装入口：https://github.com/belalee-ai/bela-One-page-book

## 维护者自测

```sh
python scripts/test_booktool.py
node scripts/test_state.cjs
node scripts/test_annotations.cjs
python scripts/test_reader_server.py
python scripts/booktool.py render examples/guide.json --source examples/source.json --review examples/review.json --out demo
```

示例核对记录只适用于原创测试材料，不能直接套到用户的新书。默认阅读组件已随包包含，不需要先安装其他设计 Skill。PDF.js 6.2.108 的许可证与来源保留在 assets/reader/pdfjs/。
