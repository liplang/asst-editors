# LIP 编辑器支持

本目录是独立的编辑器支持包。语言实现、CLI 和仓库根配置无需修改；新增配置、辅助工具、生成脚本与验证代码都集中在这里。可以只安装需要的编辑器。以下命令从 LIP 仓库根目录执行，配置示例中的 `/path/to/lip` 替换为仓库的绝对路径。

| 编辑器 | 编辑功能 | 工具入口 |
|---|---|---|
| Emacs 27.1+ | 主模式、高亮、结构缩进、注释、名称补全、交互模板、Imenu | 编译检查、错误跳转、运行、构建 |
| Neovim 0.9+ | 高亮、结构缩进、注释、补全、模板；可选 Lua 配置与保存检查 | Quickfix、终端运行与构建 |
| Vim 9+ | 与 Neovim 共用原生 runtime，兼容 Vim 9 的 legacy Vimscript | Quickfix、终端运行与构建 |
| VS Code 1.85+ | TextMate 高亮、括号、缩进规则、代码片段、核心函数补全和悬停、符号列表 | Problems 诊断、可选保存检查、运行与构建任务 |
| Zed | Tree-sitter 高亮、括号、结构缩进、大纲、函数文本对象；另附代码片段 | 检查、运行、构建任务 |
| Sublime Text 4 | 高亮、注释、括号、缩进规则、代码片段补全 | 检查构建系统、运行与生成可执行文件 |

这些支持文件依据 `LIP-1.0-SPEC` 与当前编译器编写：

- 仅 `#` 开始行注释。`//` 是整除，`*/` 是对数，`**` 是幂，`|>` 是管道，`<+` 是 Claim join。
- 普通字符串和三引号字符串支持 `\"`、`\\`、`\n`、`\r`、`\t`、`\u{HEX}`，没有插值、单引号字符串、C 风格块注释或 raw 前缀。
- 三引号字符串内的空格、换行、`#` 和括号属于正文。Emacs/Vim/Neovim 的结构缩进保留正文原样；不要对整份程序应用其他语言的格式化器。
- 类型名具有上下文含义；`go/python/host/lip` 是 import 后的上下文名称。核心函数只有规范中的 13 个；Claim 与外部 operation 分开处理。

当前没有 LIP LSP 或规范化格式化器。本包不声明语义重命名、跨文件定义跳转、调试器或完整自动格式化能力。Zed 的 Tree-sitter 是宽容的编辑结构语法，允许未完成的程序，语义正确性由同一个 LIP 编译器检查。

## 公共工具

纯编辑功能无需 Go、Node.js 或 Python 后台进程。检查、运行与构建需要两个命令：`lipc` 使用现有 CLI；`lipcheck` 是本目录的独立辅助程序，直接调用现有的 source-set loader 和编译器，只编译，不执行 Flow，也不生成 Go 文件。

```sh
make -C editors tools
export PATH="$PWD/.build/editors/bin:$PATH"
lipcheck examples/basics/01_hello.lip
lipc run examples/basics/01_hello.lip
```

需要 Go 1.25+。构建缓存与全部产物放在仓库 `.build/`，不安装到用户目录。`make clean` 会删除它们；长期使用时，可以把两个二进制复制到 PATH 中的个人工具目录，或者重新构建。GUI 编辑器可能不继承终端 PATH，可以在各编辑器配置中使用可执行文件的绝对路径。

没有 Make 的 Windows 环境可在仓库根目录执行：

```powershell
New-Item -ItemType Directory -Force .build/editors/bin
go build -o .build/editors/bin/lipcheck.exe ./editors/tools/lipcheck
go build -o .build/editors/bin/lipc.exe ./cmd/lipc
$env:PATH = "$PWD\.build\editors\bin;$env:PATH"
```

检查器参数与编译器的公共参数一致，全部放在文件名前：

```sh
lipcheck -entry Main -project /path/to/project program.lip
lipcheck -host demo examples/ecosystem/18_proposals.lip
```

多 Flow 文件使用 `-entry`；`-project` 固定允许静态 import 的目录边界，省略时使用源码所在目录；教学 Host 示例需要 `-host demo`。检查不会求值 Flow，但 Go/Python 原生 import 的签名发现可能启动相应工具或加载原生模块，与编译器本来的行为一致。

检查成功不输出内容，退出码为 0；编译错误为 1，用法错误为 2。错误采用 `绝对路径:行:列: E-CODE: 消息`，能跳转到实际依赖文件。编译器当前每次返回第一个错误；无源码位置的项目或入口错误显示在根文件第 1 行。检查对象是已保存文件，不读取编辑器中的未保存文本。运行所需的输入可通过 `lipc run -input '{"name":"Ada"}' file.lip` 提供，静态检查不需要入口输入。

## Emacs

在 `init.el` 中加入：

```elisp
(add-to-list 'load-path "/path/to/lip/editors/emacs")
(require 'lip-mode)
(setq lip-compiler-command "/path/to/lip/.build/editors/bin/lipc"
      lip-check-command "/path/to/lip/.build/editors/bin/lipcheck")
```

打开 `.lip` 自动进入 `lip-mode`。`C-c C-c` 检查，`C-c C-r` 运行，`C-c C-b` 询问可执行文件输出路径后构建，`C-c C-s` 选择 Flow、纯函数、循环或 carry 模板。`M-TAB`/`C-M-i` 补全关键字、核心函数和当前 buffer 的名称，`M-x imenu` 列出 Flow 与具名函数。`M-;` 注释，`TAB`/`C-M-\` 缩进；编译窗口中用 `M-g n`/`M-g p` 跳转错误。

特定 buffer 可使用：

```elisp
(setq-local lip-command-arguments '("-entry" "Main" "-host" "demo"))
(setq-local lip-run-arguments '("-input" "{\"name\":\"Ada\"}"))
(setq-local lip-project-root "/path/to/project")
(setq-local lip-indent-offset 2)
```

`lip-command-arguments` 只放检查/运行/构建共有的 `-entry`、`-host`、`-project` 参数；`lip-run-arguments` 可放输入 JSON、并行度或运行预算。命令会先保存当前文件，所有路径与参数分别引用。卸载时移除上述 init 配置。

## Vim 9

在 `vimrc` 中加入，无需插件管理器：

```vim
execute 'set runtimepath^=' . fnameescape('/path/to/lip/editors/vim')
filetype plugin indent on
syntax enable
let g:lip_compiler = '/path/to/lip/.build/editors/bin/lipc'
let g:lip_check = '/path/to/lip/.build/editors/bin/lipcheck'
```

也可以将 `editors/vim` 链接到 `~/.vim/pack/lip/start/lip`。Vim 9 的 `vim9script` 配置可以用 `&runtimepath = '/path/to/lip/editors/vim,' .. &runtimepath`；支持包自身使用两种编辑器都能加载的 legacy Vimscript。

| 操作 | 命令/按键 |
|---|---|
| 检查并打开错误列表 | `:LipCheck`；用 `:cnext` / `:cprevious` 跳转 |
| 运行当前文件 | `:LipRun`；在终端分屏显示输出 |
| 构建可执行文件 | `:LipBuild /path/to/program` |
| 插入模板 | `:LipTemplate flow`、`fn`、`if`、`for`、`carry`、`claimfor`、`match`、`importlip`、`text`，Tab 可选名称 |
| 关键词、核心函数和 buffer 名称补全 | 插入模式 `Ctrl-X Ctrl-O` |
| 缩进 | `==`、`gg=G`，三引号正文保持不变 |

模板插入合法的语法结构，`condition`、`items`、函数名、返回类型等内容由使用者填写。不会占用全局快捷键。

可以全局设置 `g:lip_args`、`g:lip_project`，也可按 buffer 设置：

```vim
let b:lip_args = ['-entry', 'Main', '-host', 'demo']
let b:lip_run_args = ['-input', '{"name":"Ada"}']
let b:lip_project = '/path/to/project'
```

公共参数只使用 `-entry`、`-project` 和 `-host`；运行专用参数用 `b:lip_run_args` 或 `g:lip_run_args`。检查通过 Quickfix 返回结果，执行时使用内置终端，不依赖第三方插件；带空格的路径受到支持。切换 filetype 时会还原本包的 buffer 选项与命令。卸载时移除 runtimepath 配置或包链接。

## Neovim

可以直接使用上面的 Vim runtime；如果需要 Lua 配置，在 `init.lua` 中加入：

```lua
vim.opt.runtimepath:prepend('/path/to/lip/editors/neovim')
require('lip').setup({
  compiler = '/path/to/lip/.build/editors/bin/lipc',
  checker = '/path/to/lip/.build/editors/bin/lipcheck',
  args = {}, -- 例如 { '-entry', 'Main', '-host', 'demo' }
  run_args = {}, -- 例如 { '-input', '{"name":"Ada"}' }
  -- project = '/path/to/project',
  keymaps = true,
  check_on_save = false,
})
vim.cmd('filetype plugin indent on')
vim.cmd('syntax enable')
```

Lua 模块自动加入同目录下的 `../vim` runtime，不需要另装第二个包。支持全部 `:Lip…` 命令，额外提供 buffer 内的 `<localleader>c` 检查与 `<localleader>r` 运行；设 `keymaps = false` 可关闭。`check_on_save = true` 开启保存检查，使用同步的编译检查并将错误放到 Quickfix。纯语法高亮无需安装 nvim-treesitter。

## VS Code

扩展无 npm 运行时依赖。使用 Python 3 标准库生成本地 VSIX，再安装：

```sh
python3 editors/tools/package.py vscode
code --install-extension .build/editors/lip-language.vsix
```

也可以运行 VS Code 的 `Extensions: Install from VSIX…` 选择该文件。打开 `.lip` 后，命令面板提供 `LIP: Check File`、`LIP: Run File`、`LIP: Build Executable`；编辑器右上角有运行入口。检查结果进入 Problems，可以点击跳转，修改文本会清除该文件过期的检查结果。构建会询问输出位置，命令将参数直接交给进程，支持带空格的路径和 JSON 参数。

工作区设置示例：

```json
{
  "lip.compilerPath": "${workspaceFolder}/.build/editors/bin/lipc",
  "lip.checkerPath": "${workspaceFolder}/.build/editors/bin/lipcheck",
  "lip.arguments": ["-entry", "Main"],
  "lip.runArguments": ["-input", "{\"name\":\"Ada\"}"],
  "lip.projectRoot": "${workspaceFolder}",
  "lip.checkOnSave": false,
  "[lip]": {"editor.tabSize": 2, "editor.insertSpaces": true}
}
```

将路径改为实际工具位置；Windows 使用 `.exe`。`lip.arguments` 是所有动作共有的编译选项，`lip.runArguments` 仅用于运行。每个参数是数组中独立的一项。入口只有一个或使用旧式顶层语句时，可以省略 `-entry`。`lip.projectRoot` 为空时，与 CLI 一样以当前源码目录作为 import 边界。

`flow`、`flowvoid`、`fn`、`lambda`、`carry`、`claimfor`、`importlip`、`importpy`、`importgo`、`importhost`、`effect`、`perform`、`pipe`、`text` 等前缀提供带 Tab 占位符的片段。悬停解释核心函数；`Ctrl-Shift-O` 列出 Flow 与具名函数。自动缩进是编辑器的括号规则，不能替代格式化器。未信任工作区仍可高亮和使用片段，工具命令需要工作区信任。

卸载使用扩展面板或 `code --uninstall-extension lip-local.lip-language`。支持 VS Code API 的兼容编辑器可尝试安装同一个 VSIX；未专门验证它们的扩展兼容性。

## Zed

Zed 使用 Tree-sitter。为避免写入不存在的远程仓库地址，本包从当前 grammar 创建本地 Git 仓库，并生成实际路径与 commit 的开发扩展。安装阶段需要 Git、Node.js、Tree-sitter CLI 0.25+，以及 Zed 构建 WASM grammar 所需的环境；Zed 可能在首次安装时下载构建工具。先安装 CLI，再打包：

```sh
npm install -g tree-sitter-cli
python3 editors/tools/package.py zed
```

在 Zed 命令面板执行 `zed: install dev extension`，选择命令输出的 `.build/editors/zed`。脚本先生成 ABI 14 的 parser，再建立本地 grammar revision，未修改当前仓库的 Git 历史。扩展文件与 grammar 仓库都在 `.build/editors/`，使用开发扩展期间需要保留。`make clean` 删除该路径后，请重新生成并安装；不要把开发扩展路径当作已经复制安装的普通扩展。

在 Zed 设置中合并：

```json
{"languages": {"LIP": {"tab_size": 2, "hard_tabs": false}}}
```

将 `editors/zed/tasks.json` 中的任务合并到项目 `.zed/tasks.json`，或者用户全局 `tasks.json`；使用 `task: spawn` 选择 `LIP: Check file`、`Run file` 或 `Build executable`。先保存文件。默认命令使用 PATH 中的 `lipcheck` 与 `lipc`，需要时替换成绝对路径。构建输出为当前文件路径加 `.out`。多 Flow、教学 Host 或跨子目录 import 的项目，在任务 `args` 的源码项前添加 `"-entry", "Main"`、`"-host", "demo"`、`"-project", "$ZED_WORKTREE_ROOT"`；运行输入同样在文件名前添加。

代码片段文件 `editors/zed/snippets/lip.json` 另行复制到 Zed 用户配置目录的 `snippets/lip.json`；也可用 `snippets: configure snippets` 为 LIP 打开片段文件后合并内容。这是带 Tab 占位符的 VS Code 格式片段。不要用整份文件覆盖已有片段。

Zed 提供高亮、大纲、括号与函数文本对象；检查诊断显示在任务终端，本包没有注册不存在的 LSP。安装中若提示找不到 Tree-sitter CLI，先用 `tree-sitter --version` 检查；WASM 工具链或下载失败需要在本机补齐依赖后重试。

## Sublime Text 4

用 `Preferences → Browse Packages…` 打开用户 Packages 目录，将整个 `editors/sublime` 复制或链接为其中的 `LIP` 子目录。重开 `.lip` 后自动高亮。`Ctrl-/` 注释；输入片段前缀并在补全列表中选择。

选择 `Tools → Build System → LIP`：`Ctrl-B` 静态检查，`Ctrl-Shift-B` 选择 Run 或 Build executable。默认生成 `file.lip.out`，避免与源码混用。错误支持双击或 `F4` 跳转；可执行文件从 PATH 寻找。入口、Host、project 和输入等参数可以在项目自己的 `build_systems` 中复制配置后添加，参数均放在 `$file` 前。

## 维护与验证

```text
editors/
  emacs/             原生主模式
  vim/               Vim 9 与 Neovim 共用 runtime
  neovim/            可选 Lua 配置
  vscode/            可独立打包的扩展
  zed/               语言配置、queries、任务与片段
  sublime/           语法、补全、缩进与构建系统
  tree-sitter-lip/   Zed 的结构语法源码
  tools/             编译检查桥、生成与本地打包工具
  tests/             无 GUI 的编辑器集成验证
  language.json      关键字、核心函数说明与声明式片段的数据源
```

维护者可执行：

```sh
make -C editors generate  # 更新 TextMate、Sublime 与声明式片段
make -C editors test      # 构建工具并运行真实编辑器与命令集成验证
make -C editors clean     # 清理编辑器构建产物、Python 缓存、字节码与日志
make test
make race
make vet
make clean
```
