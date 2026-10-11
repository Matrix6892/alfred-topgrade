# Alfred 的 Topgrade 工作流

[English](../README.md) · [Русский](README.ru.md) · **简体中文**

在 Alfred 中输入 `topgrade`，即可在一个可重复使用的终端会话中更新软件。
优先使用 Ghostty；如果未安装 Ghostty 或版本过旧，则自动使用 macOS 自带的 Terminal.app。

- 首次运行创建一个专用 Ghostty 标签页或 Terminal 窗口。
- 更新进行时，重复请求会被忽略，不会排队，也不会创建更多终端。
- 更新完成后，下次请求在同一会话中运行。
- 关闭会话后，下次请求会创建新的会话。
- 重用会话不会改变焦点。新建 Ghostty 标签页时可能短暂切换焦点，随后恢复原标签页和窗格。
- `topgradecheck` 只检查版本，不更新软件。

## 在新 Mac 上安装

需要 Alfred 5 **Powerpack**、Python 3.9 或更新版本，以及 Topgrade。
如果已经安装 Homebrew：

```sh
brew install python topgrade
brew install --cask alfred
```

Ghostty 是可选的：

```sh
brew install --cask ghostty
```

1. 下载 [Topgrade.alfredworkflow](https://github.com/Matrix6892/alfred-topgrade/releases/latest/download/Topgrade.alfredworkflow)。
2. 打开文件并导入 Alfred。
3. 在 Alfred 中运行 `topgradecheck`。首次运行时，在 macOS 提示中允许 Alfred 控制所选终端。
4. 需要更新软件时，运行 `topgrade`。

没有 Ghostty 时会自动选择 Terminal.app，无须额外配置。
更新确认和 sudo 密码提示由你的 Topgrade 设置决定。

## 从源代码安装或更新

```sh
git clone https://github.com/Matrix6892/alfred-topgrade.git
cd alfred-topgrade
python3 install.py --dry-run
python3 install.py
```

安装程序会找到 Alfred 当前使用的偏好设置，包括同步文件夹中的设置。
它只替换本工作流，并将旧文件夹保存在偏好设置包旁边的 `Topgrade Workflow Backups` 中。
其他工作流和 Topgrade 配置保持不变。更新工作流前，请关闭专用 Topgrade 会话，
以便下次运行加载新代码。

自定义偏好设置位置：

```sh
python3 install.py --preferences "/path/to/Alfred.alfredpreferences"
```

## 行为与可选设置

原生标签页创建需要 Ghostty 1.3.1 或更新版本。
Terminal.app 的原生脚本接口创建的是**窗口**，因此备用方案重复使用一个专用窗口。
首次创建可能将终端应用置于前台；重复运行不会改变焦点。
会话专供 Topgrade 使用，在两次更新之间等待 Alfred 请求，而不是提供普通 shell 提示符。
之前的输出仍可通过滚动查看。

如果存在 `~/.local/bin/topgrade`，工作流会优先使用它；否则从 PATH 和标准 Homebrew
路径查找 Topgrade。工作流不会复制原机器的个人配置，也不会强制自动确认更新。
如有需要，请正常配置 `~/.config/topgrade.toml`。

可在 Alfred 工作流设置中添加以下环境变量：

| 变量 | 用途 |
| --- | --- |
| `TOPGRADE_TERMINAL` | 默认 `auto`，也可设置为 `terminal` 或 `ghostty` |
| `TOPGRADE_BINARY` | 自定义可执行文件或启动脚本的绝对路径 |
| `TOPGRADE_PYTHON` | 安装在其他位置的 Python 3.9+ 的绝对路径 |

运行中的会话会继续使用当前终端应用；切换应用前请关闭该会话。
恢复保存的 Ghostty 标签页时，会话从空闲状态开始，不会自动触发更新。

## 故障排除与卸载

- **自动化权限被拒绝：**系统设置 → 隐私与安全性 → 自动化 → Alfred，允许控制
  Ghostty 或 Terminal。权限错误不会悄悄将更新转移到其他应用。
- **会话没有响应：**只关闭专用 Topgrade 标签页或窗口，然后重试。
- **找不到 Python：**通过 Homebrew 安装，或设置 `TOPGRADE_PYTHON`。
- **Ghostty 创建窗口而非标签页：**退出不支持标签页的非原生全屏模式。
- **卸载：**关闭专用会话，并在 Alfred 偏好设置中删除 Topgrade 工作流。
  本项目不会安装后台服务或登录项。

诊断状态保存在 `~/Library/Caches/topgrade-alfred/`，不会包含在仓库或发布文件中。

## 测试与构建

无须安装额外 Python 包：

```sh
python3 -m unittest discover -s tests -v
python3 scripts/build.py
```

构建生成内容可重复的 `dist/Topgrade.alfredworkflow`。
测试覆盖重复请求、会话重用、错误、关闭后的恢复、空闲启动、终端回退、Topgrade 查找、
安装备份和包的可重复构建。GitHub 检查在 macOS 上运行，编译 Terminal 脚本，
但不会执行真实的软件更新。

Ghostty 脚本接口已根据 1.3.1 版本核对。在真实 Terminal.app 中进行的版本检查已验证会话创建
和重用，且重复运行时会话、窗口数量和选中窗口保持不变。完整交互式更新和整个应用重启属于单独的手动检查，
测试套件不会执行这些操作。详见[运行契约](ARCHITECTURE.md)。

## 许可证与图标

GPL-3.0-only。图标保留了 Topgrade 原始标识的设计元素，并为 Alfred 调整了构图。
[致谢](../CREDITS.md) · [图标提示词](ICON.md)。
