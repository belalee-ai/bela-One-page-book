# 安装一页读书：复制一句话就开始

安装通常只需要做一次。以后换书，直接把书交给助手，不用重新安装。

## 方法一：让你正在用的助手安装（推荐）

在支持本地文件操作、运行命令和 Skill 的助手中，复制发送：

```text
请帮我安装一页读书 Skill：
https://github.com/belalee-ai/bela-One-page-book

先确认你当前支持的 Skill 安装方式，把完整 Skill 安装到当前工具可识别的位置，不要只下载 SKILL.md。装好后检查文件是否齐全，并用自带示例验证能否生成网页。如果缺少权限、运行环境或不支持安装，请说明具体原因和可用的替代方式。
```

不用先找隐藏文件夹，也不用自己解压。助手必须实际检查安装结果；仅回复“好的，已了解”不代表安装成功。

## 方法二：直接复制终端命令

下面使用 [Vercel Skills CLI](https://github.com/vercel-labs/skills)。电脑需要 Node.js/npm 和可用的 Git。macOS、Linux 的终端和 Windows 的 PowerShell 都可使用这些命令。

不确定选择哪个工具，先用交互安装，跟着提示选：

```sh
npx skills add belalee-ai/bela-One-page-book --skill bela-one-page-book --global
```

知道自己用哪个，就选对应的一条。`--global` 表示装到自己的用户目录，之后换项目也能用；`--copy` 使用完整文件副本。

### Claude Code

```sh
npx skills add belalee-ai/bela-One-page-book --skill bela-one-page-book --agent claude-code --global --copy
```

### Cursor

```sh
npx skills add belalee-ai/bela-One-page-book --skill bela-one-page-book --agent cursor --global --copy
```

### Codex

```sh
npx skills add belalee-ai/bela-One-page-book --skill bela-one-page-book --agent codex --global --copy
```

## WorkBuddy：复制到对话里

在 WorkBuddy 中复制发送下面的安装请求。它是一段交给助手执行的任务，不是假定存在的终端命令；当前版本能否直接从仓库安装，以实际检查结果为准。

```text
请帮我在 WorkBuddy 中安装一页读书 Skill：
https://github.com/belalee-ai/bela-One-page-book

请先检查当前 WorkBuddy 支持的技能安装方式和仓库访问权限。能从仓库安装时，请安装完整文件；如果当前版本必须通过“添加技能”导入本地包，请替我准备符合要求的完整技能包，并告诉我接下来点哪里，不要让我手动拆分文件。装好后用自带示例验证是否能生成网页。若暂时不能运行脚本，先说明限制，并提供文字版体验。
```

[WorkBuddy 官方说明](https://open.workbuddy.cn/docs/skill)提供的入口是：**专家·技能·连接器 → 技能 → 添加技能**；也有[导入本地技能包或通过对话查找、创建技能](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market)的方式。若界面要求本地包，按界面选择完整包，不必自己拆出脚本和模板。

Claude Code、Cursor、Codex 的命令按 Skills CLI 支持列表核对。WorkBuddy 按自己的安装入口处理，不能套用 CodeBuddy 的命令。以上不代表本项目已在所有工具里完成安装和整本书生成实测；遇到缺项时按下方说明继续。

## 装好后怎么开始

开启新对话，发送：

```text
使用 bela-one-page-book。先检查安装是否完整，再用自带的 examples 示例生成一页读书网页，让我看看效果。
```

在 Codex 中也可以写 `$bela-one-page-book`；其他工具可以直接说 Skill 名称，或从它自己的 Skill 菜单选择。

成功的检查结果应包括：能找到 `SKILL.md`、`scripts`、`assets`、`references`，并实际产出示例网页。只有识别到名字，还不代表文件和运行环境都齐全。

随后在对话里上传 PDF、EPUB、TXT 或 MD，或者提供助手可以访问的本地路径：

```text
使用 bela-one-page-book，帮我整理这本书。想先看梗概和脑图，再挑章节读原书。网页先用莫兰迪风格。
```

MOBI 需要 Calibre，扫描书需要额外文字识别；不必提前装齐所有可选工具。继续看 [详细使用方法](docs/usage.md)。

## 用什么系统和浏览器

**第一次体验，建议用电脑生成，在桌面版 Chrome 或 Edge 中阅读。** 这是目前的使用建议，不是所有系统、浏览器均已验收的承诺。

| 你手上的设备 | 建议怎么用 |
|---|---|
| Windows 电脑 | 建议 Windows 11，使用当前版 Edge 或 Chrome；生成时还需支持 Skill 的助手和 Python 3.9+ |
| Mac | 使用仍受系统与浏览器支持的 macOS，优先当前版 Chrome 或 Edge；Safari 可试用，交互和记录保存仍待实测 |
| Linux 电脑 | 使用当前受支持的发行版，优先 Chrome 或 Edge；先确认所选 AI 助手是否有 Linux 版本，浏览器能运行不代表助手也能运行 |
| 手机或平板 | 建议先在电脑生成，再尝试阅读成品；本地 HTML 打开、文件备份和窄屏体验尚未完成设备实测，不作为第一选择 |
| 老电脑、不能更新的系统 | 先阅读随网页交付的 `guide.md` 文字版；无法运行的新浏览器或脚本不必硬装 |

浏览器的系统门槛会更新，以 [Chrome 官方要求](https://support.google.com/chrome/answer/95346?hl=zh-Hans)和 [Edge 官方要求](https://learn.microsoft.com/en-us/deployedge/microsoft-edge-supported-operating-systems)为准。以上系统建议用于选择阅读环境；WorkBuddy、Claude Code、Cursor、Codex 各自的系统要求需要单独确认。

**生成与阅读分开看：** 生成时需要助手、文件权限和 Python；阅读已经生成的 `index.html` 只需要浏览器，不需要再次安装 Skill。不要把阅读网页当作上传和生成入口。

### 网页怎么打开

1. 找到助手交付的 `index.html`，保留整个输出文件夹。
2. 右键文件，选择“打开方式 → Google Chrome / Microsoft Edge”；不要仅在聊天附件或文件预览窗口中查看。
3. 第一次打开，试一下切换风格、展开脑图、查看出处，再标记一次阅读状态并刷新，确认当前浏览器能记住。
4. 后续尽量使用同一浏览器、同一用户资料和同一个文件位置。无痕窗口不适合保存长期阅读记录。

阅读状态存在浏览器本地。直接打开 HTML 时，记录是否保留还受浏览器的本地文件策略影响；换浏览器、换设备或移动文件后，不能保证继续读位置还在。平时无需每天点保存，迁移前用页面的导出备份，到新环境再导入。若浏览器拒绝保存，按页面提示保留备份；打不开时先用 `guide.md` 阅读。

### 哪些已经测试

0.1 的 Windows、macOS、Linux 生成脚本自动检查已通过。0.2 已在 macOS 内置 Chromium 实测 PDF 阅读、标注、恢复与备份导入；其他浏览器、手机和平板仍待实测，本轮三系统 CI 以对应提交为准。GitHub 展示图来自原型页面，不能代替便携版验收。详见 [测试结果](TESTING.md)。

## 遇到问题怎么办

| 你看到的情况 | 怎么继续 |
|---|---|
| GitHub 显示 404、无权限或下载失败 | 仓库已公开，无需作者授权。先核对仓库地址、网络和代理；仍失败时把实际报错交给助手检查 |
| 找不到 npx | 让助手检查 Node.js/npm 并引导安装；Codex 也可使用自带的 skill-installer，不必为了它单独安装 Node.js |
| Git 不可用、网络失败 | 让助手说明实际缺项；解决后重试，或使用下面的 ZIP 备用安装 |
| 已安装同名 Skill | 先核对现有版本与本地改动，再决定更新；不要把正在使用的文件直接覆盖 |
| 助手只能聊天，不能写文件或运行程序 | 可先整理文字版梗概与脑图；完整网页生成移到支持文件和程序运行的工具中继续 |
| 能安装但没有 Python | 让助手检测 Python 3.9+，给当前系统的安装指引；暂时无法运行时先交付文字版 |
| 工具带有“导入 Skill”入口 | 按它自己的格式要求导入完整包；不能因为有入口就假定它也支持脚本执行 |

仓库已公开，正常查看和下载无需登录 GitHub；网络或本地运行环境的问题仍需根据实际报错处理。

## 方法三：手动下载（备用）

前两种方式不适用，或者需要离线传递文件时，再使用 ZIP。

### 下载完整文件夹

1. 打开 [GitHub 仓库](https://github.com/belalee-ai/bela-One-page-book)。如果看到 404，先核对链接和网络连接。
2. 点文件列表上方的 **Code**，再点 **Download ZIP**。
3. 解压下载的文件，把解压后的文件夹改名为 `bela-one-page-book`。
4. 打开它，应该能直接看到 `SKILL.md`、`scripts`、`assets` 等。不要再套一层同名文件夹。

如果使用的助手有“导入 Skill”入口，可以按它的提示导入这个完整文件夹。不同助手入口不完全一样，不必强行套用下面的目录。

### 放到哪里

使用 Codex 的本地安装目录时，可把整个文件夹放在用户目录下的 `.codex/skills/` 中：

| 系统 | 安装位置示例 |
|---|---|
| macOS / Linux | `~/.codex/skills/bela-one-page-book/` |
| Windows | `%USERPROFILE%\.codex\skills\bela-one-page-book\` |

`~` 和 `%USERPROFILE%` 都表示你自己的用户文件夹。若你改过 Codex 配置目录，以实际目录为准。macOS 可以在访达“前往 → 前往文件夹”中粘贴路径；Windows 可以在文件资源管理器地址栏粘贴路径。没有 `skills` 文件夹时可以先新建。

最后的层级应当是：

```text
skills/
└── bela-one-page-book/
    ├── SKILL.md
    ├── scripts/
    ├── assets/
    └── references/
```

请保留完整包，不能只放 `SKILL.md`。脚本和网页模板也会被用到。


完整文件夹中的脚本和网页模板都要保留。手动安装目录与工具版本有关，优先让助手查当前入口；上面的命令方式会替你选择目录。

## 本次验证范围

已核对仓库根目录的 Skill 结构，以及安装工具文档中的命令与工具标识。三系统的生成脚本检查见 [测试说明](TESTING.md)。本轮在独立目录解包检查发行包，作者本机 Codex Skill 也同步更新；这不等于已经完成 Claude Code、Cursor 或 WorkBuddy 的客户端加载与完整生成实测。

## 0.2 的 PDF 标注与升级

安装完整 Skill 后，让助手重新生成交付目录。文字导览仍可双击 HTML；想在 PDF 上划线，在交付目录运行 `python start_reader.py`（Windows 也可用 `py -3 start_reader.py`），打开显示的本机地址。保留整个 `reader` 文件夹。0.1 的阅读进度 JSON 可恢复，旧 guide/source 材料需要按新核对契约重新生成。详细步骤见 [PDF 标注说明](docs/pdf-annotations.md)。
