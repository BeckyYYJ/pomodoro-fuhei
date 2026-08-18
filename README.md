# 番茄钟 + 项目看板

[![Latest Release](https://img.shields.io/github/v/release/BeckyYYJ/pomodoro-fuhei)](https://github.com/BeckyYYJ/pomodoro-fuhei/releases/latest)

一个基于 Python、PySide6 和 SQLite 的本地桌面效率工具，将番茄工作法、项目管理和统计分析整合在一起。AI开发自用实用小软件。

## 功能

- 番茄钟倒计时：专注、短休息、长休息循环
- 正计时模式：记录开放式专注时长
- 多项目管理：创建、重命名和删除项目
- 项目看板：待办、进行中、已完成三列展示
- 卡片拖拽：拖动卡片即可修改任务状态
- 待办管理：分类、任务和具体步骤三级管理
- 任务优先级：低、中、高优先级标记
- 任务进度：根据具体步骤自动计算完成进度
- 统计分析：番茄数量、专注时长、完成率和累计数据
- 最近 7 天图表：番茄数量和专注时间柱状图
- 贡献热力图：查看长期专注记录
- 个性化设置：专注时长、休息时长、音效、界面边距和字体大小
- 本地数据：SQLite 存储，无需网络和云端服务
- 深色极简 UI：统一深色主题，适合长时间使用

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
```

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
| `ui_todo.py` | 待办与步骤管理 |
| `ui_timer.py` | 计时界面 |
| `ui_stats.py` | 统计界面 |
| `ui_settings.py` | 设置界面 |

## 许可证

暂未指定许可证。
