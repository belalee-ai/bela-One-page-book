# 当前验收入口

2026-09-22：0.2 三系统自动检查已通过：[运行记录](https://github.com/belalee-ai/bela-One-page-book/actions/runs/35694095654)。首轮发现的 Windows 编码问题已修复，PDF 文件摘要与阅读版生成也已纳入检查。

0.2 的实际结果、已修复问题和待测环境见 [更新与对抗检查](docs/release-0.2.md)。下面保留 0.1 历史记录，不代表新功能已在所有环境测过。

# 0.1 验收说明 · 2026-09-21

状态：本地已安装，已上传 GitHub；三系统自动检查通过，仍为待视觉/MOBI验收的试用版。

已验证：
- GitHub Actions：Windows、Linux、macOS 三系统均通过环境检测、Python 测试、状态检查与示例网页生成。[运行记录](https://github.com/belalee-ai/bela-One-page-book/actions/runs/35559536928)。首轮发现 Windows 中文输出编码失败，修复后重跑通过。
- macOS，Python 3.12；标准库 11 项测试通过：EPUB spine 顺序、GB18030 文本、缺 MOBI/缺 PDF 解析器、空材料、有效结构、假引文、坏出处、空白来源、HTML 转义与无网络请求、上下文长度上限。
- 原创 EPUB → book.md/source.json → guide.json 校验 → index.html/guide.md → 两书合并网页，命令行流程通过。
- 两页合成 PDF 经 pypdf 提取，保留两页位置；混合批次的不支持文件单独报错，后续 PDF 正常完成。
- 8 组状态行为检查通过（Node 的轻量 DOM 替身，不是浏览器）：开始/继续、导览/原书独立完成、备份合并不覆盖已完成状态、坏备份拒绝、存储失败提示、文字转义。
- Skill 结构验证器通过；JS 语法检查通过。
- 压缩包在临时干净目录解压，Python 关闭 site-packages 后仍通过 11 项标准库测试与示例 render；归档路径、CRC、无私人绝对路径检查通过。此项不等于另一操作系统实测。

未完成：
- 独立 file 网页的浏览器视觉与交互验收：内置浏览器安全策略拒绝本地 file 地址访问，未绕过限制。不能沿用原项目页面截图作为本模板验收证据。
- Windows/Linux 的真实桌面浏览器、移动端设备实测；Calibre MOBI 转换实测（本机缺 Calibre）；扫描 OCR（未内置）；真实厚书端到端覆盖测试。
- 五主题与响应式 CSS 已包含，但新便携模板的 390/768/1440 截图、备份文件浏览器下载/上传、系统 reduced-motion 待补。

用户原来的本地服务和真实书架记录未被替换。本包生成网页无模型调用，不等于已有网页的“上传后后台自动生成”服务器。此版优先验证可迁移核心流程，插画素材、原书内置翻页器和服务器属于后续可选能力。

复查：运行 scripts/test_booktool.py；如有 Node 运行 scripts/test_state.cjs。使用 examples 的 JSON 运行 render 可生成原创短文示例。测试不读取私人书籍。
