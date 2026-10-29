# 番茄钟 + 项目看板 v1.0

基于 Python、PySide6 和 SQLite 的 Windows 本地桌面效率工具，无需网络或云端服务。

## 运行桌面版

双击 `dist/PomodoroTimer-v1.0.exe`，无需安装 Python。

数据保存在 exe 同目录的 `pomodoro_data.db`。更换版本时关闭旧程序，保留这个数据库文件即可沿用数据；首次启动新版会自动升级旧表结构。旧任务缺少可靠完成时间时保持为空。

## 功能

- 番茄钟倒计时、短休息、长休息与正计时，按项目保存记录。
- 多项目创建、重命名、删除；查看项目统计、最近七天图表和贡献热力图。
- 待办、进行中、已完成三列看板，拖动卡片修改状态。
- 点击卡片或按 Enter/空格展开步骤，右上角 `edit` 编辑标题、备注、分类、标签、优先级和步骤。
- 进入已完成时记录日期与时间，移出后清除，再次完成重新记录。
- 当前项目或全部项目搜索，优先级/标签筛选，按优先级、标题和时间排序。
- 已完成卡片可右键归档，或通过 Done 列“一键归档”归档当前项目全部已完成卡片，不受筛选影响。
- 项目“归档”查看当前项目，侧栏“归档”查看全部项目；每行四张，支持搜索、筛选和排序。
- 归档保留卡片及步骤和完成时间，可展开查看，只允许删除，删除前确认。
- 设置中切换浅色/深色主题、字号、边距、专注时长与音效，保存后生效。

版本记录见 [CHANGELOG](docs/CHANGELOG.md)，后续需求见 [TODO](docs/TODO.md)。
原始界面调研保留在 [设计记录](docs/research/2026-10-28-productivity-kanban-references.md)。

## 源码运行

建议使用 Python 3.12。运行依赖固定为本次验证的版本。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

源码模式的数据保存在项目根目录，打包版的数据保存在 exe 所在目录。

## 开发与测试

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -v
```

测试使用临时数据库，界面测试使用 Qt offscreen 模式。

## 重新构建

运行 `build.bat`，或执行：

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm PomodoroTimer.spec
```

生成 `dist/PomodoroTimer-v1.0.exe`。`app_info.py` 是版本信息的统一来源，程序标题、exe 文件名和 Windows 文件属性随其更新。`build/` 为可删除的打包中间目录，`.venv/` 为本地开发环境，二者不纳入 Git。

## 项目结构

| 文件或目录 | 职责 |
| --- | --- |
| `main.py` | 程序入口 |
| `app_info.py` | 名称和版本 |
| `database.py` | SQLite 数据、兼容升级及增删改查 |
| `timer_logic.py`、`sound.py` | 计时逻辑与音效 |
| `ui_main.py`、`ui_sidebar.py`、`ui_workspace.py` | 主窗口、导航和项目工作区 |
| `ui_card.py`、`ui_card_dialog.py` | 看板/归档共用卡片及详情编辑器 |
| `ui_board.py`、`ui_archive.py`、`ui_todo.py` | 看板、归档及待办页面 |
| `ui_timer.py`、`ui_stats.py`、`heatmap.py` | 计时、统计及热力图 |
| `ui_settings.py`、`ui_theme.py` | 设置及主题 |
| `tests/` | 数据、计时、归档及界面回归测试 |
| `docs/` | 版本记录、后续需求及设计记录 |
| `PomodoroTimer.spec`、`build.bat` | Windows 打包配置与入口 |

## 许可证

暂未指定许可证。
