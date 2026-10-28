# 办公效率工具与看板参考调研

调研日期：2026-10-28。本文是供选择的调研资料，不是已确认的开发需求。

## 目标和依据

目标：参考其他效率软件，选择适合当前番茄钟应用的功能与看板 UI。先选择参考，再确定开发范围。

暂按个人自用、Windows 桌面、本地存储的方向判断；依据是当前 README 对产品的描述。这一定位可以调整。

本次阅读了 README、数据库、主窗口、项目工作区、看板、待办和计时代码。没有运行桌面界面：当前 Python 环境缺少 PySide6。下面的现状属于源码检查，外部图片属于产品官方公开示例，均不是本次实际操作这些软件得到的截图，也不构成完整视觉或无障碍审计。公开示例可能与软件最新版外观不同。

## 当前已有能力与缺口

已有：番茄钟、正计时、多项目、待办/进行中/已完成三列、跨列拖拽、分类/任务/步骤、优先级、步骤完成率、专注统计和热力图、字体和边距设置。

从代码确认的改进机会：

| 现状 | 建议 | 代码依据 |
| --- | --- | --- |
| 看板的“＋”仅提示去待办页新建，没有连接新建操作 | 在列内直接新增任务，继承该列状态 | `ui_board.py` 的 `BoardWidget.__init__` |
| 卡片支持拖拽，未提供点击打开详情的操作 | 点击卡片打开详情侧栏，直接修改步骤、备注、优先级 | `ui_board.py` 的 `CardFrame` |
| 卡片固定为 180×180 | 改为随列宽调整的横向卡片，允许标题换行，提供紧凑/舒适密度 | `ui_board.py` 的 `CardFrame.__init__` |
| 专注记录只关联项目，没有关联任务 | 从卡片启动专注，把实际用时记到任务 | `database.py` 的 `records`；`ui_timer.py` 的 `work_started` |
| 任务没有计划日期、截止日期、提醒、重复规则字段 | 区分“安排哪天做”和“最晚何时交”，再补今日视图与提醒 | `database.py` 的 `cards` |
| 导航按计时、统计、设置、项目组织 | 增加收集箱和跨项目今日视图 | `ui_sidebar.py` 的 `FUNCTION_KEYS` |
| 未见任务全局搜索、标签筛选、应用内备份恢复功能 | 增加搜索筛选、备份恢复、导出 | 已检查的 UI、数据层和设置页 |

## 参考产品及可借鉴做法

下面的“应用建议”是针对本项目的判断，不代表这些产品只能用于该场景，也不是逐项功能完备性比较。

| 产品 | 已核实的参考能力 | 应用建议 | 来源 |
| --- | --- | --- | --- |
| 滴答清单 / TickTick | 快速收集、标签筛选、提醒与重复、日历、看板、番茄钟 | 最适合作为个人效率功能参考：今日、截止日期、重复任务、任务专注 | [官方功能页](https://ticktick.com/features) |
| Todoist | 看板/列表布局、分区、拖动任务、排序筛选、快捷切换 | 列内快速新增，保持卡片简洁，让同一任务切换视图 | [官方看板说明](https://www.todoist.com/help/todoist/features/use-the-board-layout-in-todoist-AiAVsyEI) |
| Linear | 看板/列表、按状态或其他属性分组、隐藏列、快捷键、快速预览 | 深色紧凑看板、筛选工具栏、可折叠列和快捷操作 | [官方看板说明](https://linear.app/docs/board-layout) |
| Trello | 看板任务管理、模板、自动化、计划器和多种视图 | 学习列内新增、标签、日期、检查清单的直观呈现 | [官方项目管理示例](https://trello.com/zh-Hans/use-cases/project-management) |
| Notion | 按属性分组、排序筛选、可配置卡片属性 | 允许用户选择显示哪些字段，备注与资料放在任务详情中 | [官方看板说明](https://www.notion.com/help/boards) |
| Sunsama | 每日规划、任务与日历结合；公开界面包含任务估时和时间安排 | “今日工作台”可选择任务总量、估算负荷、安排时间块 | [官方网站](https://www.sunsama.com/)；[可视化规划](https://www.sunsama.com/blog/visual-planning) |
| Super Productivity | 任务/子任务直接计时、估时与实际对比、本地离线、历史与导出 | 产品定位最接近本项目；优先打通任务、专注、复盘 | [官方时间追踪说明](https://super-productivity.com/use-cases/time-tracker/) |
| PowerToys Command Palette | 统一命令入口、键盘操作、搜索和快速启动 | 只借鉴交互：Ctrl+K 找任务、切项目、开始专注 | [Microsoft 官方说明](https://learn.microsoft.com/en-us/windows/powertoys/command-palette/overview) |
| Obsidian Canvas | 本地保存、笔记与图片/PDF/网页等材料关联 | 后续可给项目添加资料链接和附件；暂不需要做无限画布 | [官方 Canvas 介绍](https://obsidian.md/canvas) |

## A–F 图片选择

图片用于对比布局、信息密度和操作方式；不表示要照搬产品品牌、协作结构或全部功能。

### A — Linear：深色、紧凑、适合任务较多

建议借鉴：窄侧栏、轻量工具栏、状态列、短卡片、筛选和快捷预览。与当前深色主题的延续性较好。

![A Linear 官方看板示例](https://webassets.linear.app/images/ornj730p/production/04115ca5eb44c3c6fc38d9998e6a7af068cb8b61-3424x1920.png?auto=format&dpr=2&q=95&w=1440)

[来源：Linear Board layout](https://linear.app/docs/board-layout)

### B — Todoist：清爽、轻量、容易上手

建议借鉴：简洁卡片、完成勾选、日期提示、列内直接新增。适合每天主要管理少量个人任务。

![B Todoist 官方看板示例](https://res.cloudinary.com/imagist/image/fetch/q_auto%2Cf_auto%2Cc_scale%2Cw_800/https%3A%2F%2Fget.todoist.help%2Fhc%2Farticle_attachments%2F18241420403228)

[来源：Todoist 看板说明](https://www.todoist.com/help/todoist/features/use-the-board-layout-in-todoist-AiAVsyEI)

### C — Trello：直观卡片、标签与检查清单

建议借鉴：列内新增、标签色块、截止日期和步骤计数。若用于本应用，头像和协作入口可以不采用。

![C Trello 官方项目看板示例](https://images.ctfassets.net/rz1oowkt5gyp/3sQXvhjNQvqEH67HDl7ybE/ece4de0cfa51ca6d22c6e6a8e6a43a2d/Product-Hero-Illo.png?w=1080)

[来源：Trello 项目管理](https://trello.com/zh-Hans/use-cases/project-management)

### D — Notion：属性丰富、展示可配置

建议借鉴：任务资料与正文、标签和属性、卡片字段显示设置、多种分组。适合任务经常附带文档与说明的工作。

![D Notion 官方路线图看板示例](https://images.ctfassets.net/spoqsaf9291f/5wVv2TfJjHLW3lvTLNVgV/d6a5b97bcec3a9113542c1c812bb2030/Projects_database.png)

[图片来源：Notion 路线图模板](https://www.notion.com/templates/roadmap)；[功能来源：Notion 看板说明](https://www.notion.com/help/boards)

### E — 滴答清单：任务、日期和个人生活分类

建议借鉴：收集箱、今日、计划日期、标签和日期提示，并与现有番茄钟连接。这里的手机和桌面展示是官方功能宣传图。

![E TickTick 官方看板展示](https://d107mjio2rjf74.cloudfront.net/sites/res/newFeatures/tick/feature5/kanban.png)

[来源：TickTick 官方功能](https://ticktick.com/features)

### F — Sunsama：按天规划＋右侧时间轴

这是一种每日规划工作台，列代表日期，与按状态分列的项目看板有所不同。

建议借鉴：任务估时、当天任务总量、时间块、日终复盘。适合作为“今日”页面，不必替换项目看板。

![F Sunsama 官方每日规划示例](https://pub-f7ae218077e542729e28e6f8f45a9a40.r2.dev/images/65aebf9e238281880051f1c3_M8cIH5waRTi-KY16OyCiR3AnyrwEUcsJUKbdnwpXoui9oJ5zXFb0SLR5Pe0aS5Xu29etNSHcKeoxtupK4Qxu8M13Gshm-7A_cOzvqX3X5KBB2jMft9xqRNpnbVICq1OujpfuTcNXdO7JyisxCdv3oIU.png)

[来源：Sunsama 可视化规划](https://www.sunsama.com/blog/visual-planning)

## 功能优先级建议

以下是候选顺序，具体取舍等待用户选图和选择功能。

| 编号 | 优先级 | 候选功能 | 用户获得的效果 | 相对改动量 |
| --- | --- | --- | --- | --- |
| 1 | 第一批 | 看板列内新增＋点击详情编辑 | 减少看板与待办页来回切换 | 中 |
| 2 | 第一批 | 任务绑定番茄钟＋全局迷你计时条 | 知道正在做什么、每项任务花了多久 | 中至大 |
| 3 | 第一批 | 收集箱＋跨项目今日视图＋计划/截止日期 | 打开软件能立即决定今天做什么 | 大 |
| 4 | 第一批 | 全局搜索＋优先级/标签筛选＋排序 | 任务多起来仍能快速找到目标 | 中 |
| 5 | 第一批 | 自动备份/恢复＋归档/撤销 | 本地工作记录可恢复，完成列不无限堆积 | 中 |
| 6 | 第二批 | 重复任务＋系统提醒 | 周报、复习、缴费等任务不靠反复手填 | 中至大 |
| 7 | 第二批 | 预计番茄数/时长＋实际用时对比 | 判断一天能做多少，逐渐改进估时 | 中 |
| 8 | 第二批 | 自定义列、阻塞标记、进行中数量提示 | 展示等待与卡点，避免同时开太多任务 | 中至大 |
| 9 | 第二批 | 当天时间轴＋日/周复盘 | 把任务安排进真实时间，回顾成果和阻塞 | 大 |
| 10 | 后续 | 资料链接、附件、Markdown 备注、模板 | 减少寻找项目资料和重复建任务的操作 | 中 |
| 11 | 后续 | 命令面板、全局快速收集、托盘与悬浮计时 | 从其他软件中快速录入和控制专注 | 中至大 |
| 12 | 需求明确后 | 云同步、团队协作、AI 辅助 | 取决于多设备、共享和自动化的真实需要 | 大 |

“相对改动量”仅为依据现有结构的初判，不是工时承诺。涉及数据结构的新功能需要迁移与旧数据兼容；任务关联专注记录后，删除任务应保留历史用时。

## 三种组合方向

1. **推荐：A 的外观＋E 的个人任务流程。** 深色紧凑看板，配收集箱、今日、任务详情和卡片启动专注。适合继续强化现有软件。
2. **B/C 的轻量卡片方向。** 优先做直接新建、拖动、编辑、标签和日期；学习成本较低。
3. **A 的项目看板＋F 的今日工作台。** 两个入口共享任务，项目页看进度，今日页分配时间；规划能力更强，但开发范围更大。

## 待用户选择

### A / B / F 图片加载失败后的备用来源

原外链在用户端未显示。以下换用其他网站刊载的产品截图；属于历史界面参考，不保证与上方官方示例是同一张图。浏览器预览本次超时，不能据此确认用户端已恢复显示。

- A Linear：[查看图片](https://assets.findstack.com/94u1m3853avqbkkt4e11xc9vzzs9)，[图片来源 Findstack](https://findstack.com/products/linear/reviews)。
- B Todoist：[查看图片](https://cdn.mos.cms.futurecdn.net/C8XPiK9gmoHc2hUbcqVsmX.jpg)，[图片来源 Windows Central](https://www.windowscentral.com/todoist-introduces-new-boards-feature-project-organization)。
- F Sunsama：[查看图片](https://buffer.com/resources/content/images/2025/06/Productivity-tools-sunsama.png)，[图片来源 Buffer](https://buffer.com/resources/productivity-tools/)。

可以这样回复：

> 外观选 A，卡片操作参考 C，今日页参考 F；功能先做 1、2、4、5；暂时不做云同步。

也可以只选最喜欢的两个编号，然后再比较适合本软件的布局。
