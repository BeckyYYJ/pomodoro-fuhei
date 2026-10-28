# 番茄钟 + 项目看板

[![Latest Release](https://img.shields.io/github/v/release/BeckyYYJ/pomodoro-fuhei)](https://github.com/BeckyYYJ/pomodoro-fuhei/releases/latest)

一个基于 Python、PySide6 和 SQLite 的本地桌面效率工具，将番茄工作法、项目管理和统计分析整合在一起。AI开发自用实用小软件。

## 功能

- 番茄钟倒计时：专注、短休息、长休息循环
- 正计时模式：记录开放式专注时长
- 多项目管理：创建、重命名和删除项目
- 项目看板：待办、进行中、已完成三列展示
- 卡片拖拽：拖动卡片即可修改任务状态
- Trello 风格看板：纵向自适应卡片、列内直接新建、点击或按 Enter 打开任务详情
- 任务详情：编辑标题、备注、分类、优先级、标签和具体步骤；取消不保存修改
- 搜索与筛选：支持当前项目或全部项目，按关键词、优先级、标签筛选及排序
- 完成时间：任务进入 Done 时记录本地日期和时间（精确到秒），移出后清除，再次完成重新记录
- 待办管理：分类、任务和具体步骤三级管理
- 任务优先级：低、中、高优先级标记
- 任务进度：根据具体步骤自动计算完成进度
- 统计分析：番茄数量、专注时长、完成率和累计数据
- 最近 7 天图表：番茄数量和专注时间柱状图
- 贡献热力图：查看长期专注记录
- 个性化设置：专注时长、休息时长、音效、界面边距和字体大小
- 本地数据：SQLite 存储，无需网络和云端服务
- 浅色 / 深色主题：在设置中选择主题并保存，立即生效，重启后保留

## 环境要求

- Python 3.12+
- Windows（当前版本主要面向 Windows 桌面环境）

## 安装与运行

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

首次运行会自动创建 `pomodoro_data.db` 数据库和默认项目。

## 测试

```powershell
python test_board.py
python test_logic.py
python -m unittest test_kanban test_ui -v
```

首次使用新版会自动升级原有 SQLite 表。旧任务没有可靠完成时间时保持为空；不会把升级时间填作完成时间。现有番茄钟与正计时仍按项目记录，不关联具体任务。

看板主题预览：[浅色](docs/previews/kanban-light.png) · [深色](docs/previews/kanban-dark.png)。预览使用临时示例数据，不写入实际数据库。

## 打包

项目提供了 PyInstaller 配置，可以运行：

```powershell
build.bat
```

生成的桌面程序位于 `dist/` 目录。

## 项目结构

| 文件 | 说明 |
| --- | --- |
| `main.py` | 程序入口 |
| `database.py` | SQLite 数据层和 CRUD 操作 |
| `timer_logic.py` | 番茄钟核心逻辑 |
| `ui_main.py` | 主窗口和全局导航 |
| `ui_board.py` | 项目看板 |
| `ui_card_dialog.py` | 看板和待办共用的任务详情编辑器 |
| `ui_theme.py` | 浅色和深色主题 |
| `ui_todo.py` | 待办与步骤管理 |
| `ui_timer.py` | 计时界面 |
| `ui_stats.py` | 统计界面 |
| `ui_settings.py` | 设置界面 |

## 许可证

暂未指定许可证。
