# 一页读书 0.1 · 安装使用

解压后保留完整 bela-one-page-book 文件夹，放入助手支持的 Skill 目录或使用其导入功能；不要只复制 SKILL.md。Codex 常见位置是用户目录下 .codex/skills，其他宿主按其说明。重新打开任务后说：

> 使用 $bela-one-page-book，帮我把这几本书做成一页读书，先从我选的这本开始。

附上 PDF、EPUB、TXT、MD；MOBI 需要 Calibre，扫描书需要额外 OCR。助手先检测，缺什么再引导，不用安装全部设计 Skill。

新书由宿主助手分析生成；网页本身不自动调用 AI。成品 index.html 可直接打开，无需 Python、模型或 Skill，也不依赖在线字体/图片。多本可汇成一个选书页面。

开始读后变继续读，记录最后展开的栏目；导览读完和原书读完分别手动确认。自动保存不必每天点，导入导出用于备份。清理数据、无痕、换浏览器或文件位置可能影响记录；请保留原书和交付文件。备份仅包含状态，不包含原书。

无执行环境时可先得到 MD；有合适电脑再生成网页。本包是便携生成基础版，不包含既有私人服务器、网页上传自动生成或内置原书翻页器。来源弹窗给定位与短上下文，完整阅读仍使用原书。

包内无私人书籍、密钥、第三方插画库。跨平台脚本不等于所有平台都已实测，见验收说明。模型分析遵循宿主服务数据政策，不能称生成全程离线。

试运行（在解压后的文件夹中，由有执行能力的助手运行；python 换成实际可用的 Python 3）：

```sh
python scripts/booktool.py preflight
python scripts/booktool.py render examples/guide.json --source examples/source.json --out demo
```

打开 demo/index.html；示例是原创验收短文，不包含任何真实用户书籍。版本状态见 TESTING.md。
