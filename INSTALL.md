# 先装好，再把书放进来

安装通常只需要做一次。以后换一本书，直接在助手对话里上传就可以。

## 下载完整文件夹

1. 打开 [GitHub 仓库](https://github.com/belalee-ai/bela-One-page-book)。如果看到 404，先确认账号有没有这个仓库的访问权限。
2. 点文件列表上方的 **Code**，再点 **Download ZIP**。
3. 解压下载的文件，把解压后的文件夹改名为 `bela-one-page-book`。
4. 打开它，应该能直接看到 `SKILL.md`、`scripts`、`assets` 等。不要再套一层同名文件夹。

如果使用的助手有“导入 Skill”入口，可以按它的提示导入这个完整文件夹。不同助手入口不完全一样，不必强行套用下面的目录。

## 放到哪里

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

## 确认助手能认出来

重新打开一个任务，发送：

> 使用 $bela-one-page-book。先检查这个 Skill 是否安装完整，再告诉我可以上传哪些书籍文件。

如果助手没有找到它，把你放置文件夹的位置告诉助手，让它核对。不要反复改名或在很多目录各放一份。

## 第一次可以先用示例

仓库自带了一份原创短文，只用于体验流程，不需要上传自己的书。对助手说：

> 使用一页读书自带的 examples 示例生成一个网页，让我先看看效果。

能运行程序的助手会检查 Python 并调用随包工具。如果当前环境不能生成文件，就先给文字版，并说明还缺什么。

## 正式读一本书

在助手的对话附件里上传 PDF、EPUB、TXT 或 MD，或提供助手能访问的本地路径，然后说：

> 使用 $bela-one-page-book，帮我整理这本书。想先看梗概和脑图，再挑章节读原书。网页先用莫兰迪风格。

MOBI 需要 Calibre；扫描书需要额外文字识别。助手会先检查，不需要提前安装所有可选工具。后续操作见 [详细使用方法](docs/usage.md)。

<details>
<summary>会用命令行，想自己跑一下示例</summary>

在解压后的文件夹运行。`python` 换成当前可用的 Python 3.9+；Windows 也可能使用 `py -3`。

```sh
python scripts/booktool.py preflight
python scripts/booktool.py render examples/guide.json --source examples/source.json --out demo
```

打开 `demo/index.html`。这两条命令检查环境并把已经整理好的示例变成网页；它们不会自动阅读和总结一本新书。

</details>
