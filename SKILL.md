---
name: general-ABA-keyword-monitor
description: 亚马逊 ABA 爆品关键词监测系统（通用版），支持任意类目，从 AMZ123 热搜词榜单自动发现潜力爆发关键词，生成飞书多维表格 + 仪表盘报告
inclusion: manual
---

# 亚马逊 ABA 爆品关键词监测系统（通用版）

## 概述

从亚马逊 ABA 热搜词榜单中自动发现指定类目的潜力爆发关键词，生成飞书多维表格 + 仪表盘可视化报告。
支持任意亚马逊类目（对讲机、保健品、宠物用品、美妆护肤等），首次运行时交互式配置。
每周数据自动追加到同一张多维表格，积累历史趋势。

## 前提

- Python 3.8+（依赖自动安装）
- 必须配置 Sorftime MCP（key 会被 Python 自动提取）
- 必须配置飞书 lark-cli（通过 npm 安装：`npm install -g lark-cli`，并完成 `lark-cli config init` 初始化）

## 快速开始（提示语）

小白用户只需在 AI 对话框中说一句话即可启动：

> **首次初始化：**
> "帮我用 general-ABAkeyword-monitor 监测亚马逊关键词，我做的是【你的类目】，运行 python general-ABAkeyword-monitor/main.py init，然后按流程走完整个监测"

> **每周例行监测：**
> "帮我跑一下本周的 ABA 关键词监测"

> **仅生成报告（数据已抓取的情况下）：**
> "帮我运行 python general-ABAkeyword-monitor/main.py step3 生成飞书报告"

## 首次使用：类目初始化

### Step 0：初始化类目

```bash
python general-ABAkeyword-monitor/main.py init
```

按提示输入目标类目名称（如"对讲机"），系统会输出 `reports/.exchange/dict_draft.json`。

### Agent 任务：生成类目词典

读取 `reports/.exchange/dict_draft.json`，按 prompt 要求生成初始词典和排除规则。

写入 `reports/.exchange/dict_draft_output.json`：
```json
{
  "category_dict": {"ingredients": [...], "benefits": [...], "brands": [...], "health_markers": [...]},
  "exclusion_rules": {"exclude_patterns": [...], "exclude_keywords": [...]},
  "classification_labels": {"description": "各标签含义描述"}
}
```

### Step 0.5：确认词典

```bash
python general-ABAkeyword-monitor/main.py init-confirm
```

系统展示词典摘要，用户确认后保存。

---

## 日常监测流程（3 步）

### Step 1：抓取 + 本地词典匹配

```bash
python general-ABAkeyword-monitor/main.py step1
```

输出 `reports/.exchange/llm_input.json`。

### Agent 任务：LLM 分类 + 中文翻译

读取 `reports/.exchange/llm_input.json`，对每个关键词分类并翻译。
分类标签根据类目动态生成（见 llm_input.json 中的 prompt）。

写入 `reports/.exchange/llm_output.json`：
```json
{"keyword": {"label": "ingredient", "zh": "中文翻译"}, ...}
```

### Step 2：分层 + Sorftime 异步查询

```bash
python general-ABAkeyword-monitor/main.py step2
```

### Agent 任务：写分析摘要

读取 `reports/.exchange/analysis_input.json`，为每个 Tier 1 关键词写分析摘要。

写入 `reports/.exchange/analysis_output.json`：
```json
{
  "keyword_analysis": {"keyword": "分析摘要", ...},
  "tracks": [{"name": "赛道名", "icon": "emoji", "keywords": [...], "summary": "描述"}],
  "core_findings": ["发现1", "发现2", ...]
}
```

### Step 3：生成飞书多维表格报告（必须执行）

```bash
python general-ABAkeyword-monitor/main.py step3
```

**首次运行**会自动创建飞书多维表格（含 3 张数据表 + 仪表盘 + 筛选视图），后续运行复用已有表格追加数据。

完成后告知用户飞书多维表格链接。

---

## 飞书多维表格结构

step3 生成的多维表格包含：

### 3 张数据表
| 表名 | 内容 |
|:---|:---|
| 关键词监测 | 主表，每周关键词的排名/搜索量/CPC/爆发类型/AI分析等 17 个字段 |
| 扩展关键词 | Tier 1 关键词的延伸变体词数据 |
| 周报摘要 | 每周一条汇总记录（抓取数、各 Tier 数量、核心发现） |

### 2 个筛选视图
- **Tier 1 高优先级** — 只显示 Tier 1 关键词，按排名变化降序
- **Tier 2 观察区** — 只显示 Tier 2 关键词，按排名变化降序

### 仪表盘（5 个图表）
| 图表 | 类型 | 用途 |
|:---|:---|:---|
| 关键词总数 | 统计卡片 | 当前数据总量 |
| Tier 分布 | 饼图 | 关键词优先级分布 |
| 爆发类型分布 | 饼图 | 首次爆发/回弹/持续上升等占比 |
| 分类分布 | 饼图 | 核心产品/功效/品牌等占比 |
| 周搜索量趋势 | 柱状图 | 跨周搜索量变化趋势 |

### 数据持久化
多维表格配置（token、table_id 等）保存在 `category_config.json`，后续运行自动复用，无需重建。

---

## 踩坑经验

### lark-cli 在 Python subprocess 中找不到
Windows 下 `lark-cli` 是 npm 全局安装的 `.cmd` 文件，Python 的 `subprocess.run(["lark-cli", ...])` 可能找不到。
解决：代码中通过 `shutil.which("lark-cli")` 自动查找，并兼容 Windows npm 默认路径 `%APPDATA%/npm/lark-cli.cmd`。

### lark-cli 返回值结构
- `+base-create` → token 在 `data.base.base_token`，URL 在 `data.base.url`
- `+table-create` → table_id 在 `data.table.id`
- `+view-create` → view_id 在 `data.views[].id`
- `+dashboard-create` → dashboard_id 在 `data.dashboard.dashboard_id`
- 错误信息可能输出到 stderr 而非 stdout，需要两者都读取

### 字段格式（+table-create 的 --fields）
- select 类型：用 `"type": "select"` + `"multiple": false` + `"options": [...]`（顶层），**不是** `"type": "single_select"` + `"property": {"options": [...]}`
- number 类型：`"style"` 放在顶层，**不是** `"property": {"style": {...}}`
- 完整格式参考 `lark-base-shortcut-field-properties.md`

### Windows 编码问题
运行 Python 脚本时需要 `export PYTHONIOENCODING=utf-8`，否则中文 emoji 输出会报 GBK 编码错误。

### benefit 词误匹配
对讲机等细分品类容易被 "portable"、"wireless"、"rechargeable" 等通用功能词误匹配。
建议在排除规则中加入 `portable air conditioners`、`portable fan`、`wireless keyboard and mouse` 等高频泛品类词。
