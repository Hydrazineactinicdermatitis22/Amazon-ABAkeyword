# 亚马逊 ABA 爆品关键词监测系统 - AI Agent 操作指南

> 本文档适用于任何 AI IDE（Kiro、Trae、Antigravity、Cursor、Claude Code 等）。
> Agent 按照本文档指令执行即可完成完整监测流程。

## 前置要求

1. Python 3.8+
2. Sorftime MCP 已配置（必须）
3. 飞书 lark-cli 已安装且完成认证（`npm install -g lark-cli && lark-cli config init && lark-cli auth login`）

### Sorftime MCP 配置方法

在 IDE 的 MCP 配置文件中添加：
```json
{
  "mcpServers": {
    "sorftimeMCP": {
      "url": "https://mcp.sorftime.com?key=你的API_KEY"
    }
  }
}
```
或设置环境变量：`SORFTIME_API_KEY=你的API_KEY`

---

## 首次使用：类目初始化

### 1. 运行初始化
```bash
python general-ABAkeyword-monitor/main.py init
```
按提示输入目标类目（如"对讲机"、"宠物用品"）。

### 2. Agent 任务：生成词典
读取 `reports/.exchange/dict_draft.json`，按其中 prompt 生成词典。
写入 `reports/.exchange/dict_draft_output.json`。

### 3. 确认词典
```bash
python general-ABAkeyword-monitor/main.py init-confirm
```

---

## 日常监测流程

### Step 1：抓取 + 本地匹配
```bash
python general-ABAkeyword-monitor/main.py step1
```

### Agent 任务：LLM 分类
读取 `reports/.exchange/llm_input.json`，对每个关键词：
- 判断是否与目标类目相关
- 分类（标签见 prompt）
- 提供中文翻译

写入 `reports/.exchange/llm_output.json`：
```json
{"keyword": {"label": "ingredient", "zh": "中文翻译"}, ...}
```

### Step 2：分层 + Sorftime 查询
```bash
python general-ABAkeyword-monitor/main.py step2
```

### Agent 任务：写分析摘要
读取 `reports/.exchange/analysis_input.json`，为每个 Tier 1 关键词写 2-3 句中文分析。
做赛道聚类，写核心发现。

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

**首次运行**会在飞书自动创建多维表格（3 张数据表 + 仪表盘 + 筛选视图）。
**后续运行**复用已有表格，追加本周数据。

完成后告知用户飞书多维表格链接。

---

## Tier 分层规则

| 等级 | 条件 |
|:---|:---|
| Tier 1 | TOP 1000 且涨幅 ≥50% 或 ≥1000 位 |
| Tier 2 | 1000-50000 且从 10万+ 进入 5万内 |
| Tier 3 | 50000+ 首次出现或大幅跨越 |

## 分类标签说明

| 标签 | 含义 |
|:---|:---|
| ingredient | 核心产品/成分 |
| benefit | 功效/用途 |
| brand | 品牌 |
| condition | 场景/症状 |
| form | 形态/规格 |
| irrelevant | 无关 |

---

## 飞书多维表格输出结构

### 关键词监测表（主表，17 个字段）
关键词、周次、中文名、Tier(单选)、当前排名、前周排名、排名变化、
分类(单选)、爆发类型(单选)、月搜索量、峰值搜索量、CPC($)、
环比变化(%)、历史最佳排名、数据来源、AI分析、抓取时间

### 扩展关键词表
主关键词、周次、扩展词、周搜索量、月搜索量、CPC、季节性

### 周报摘要表
周次、抓取总数、类目相关数、Tier1/2/3数量、排除数量、核心发现、新增词典词、生成时间

### 仪表盘（5 个图表）
关键词总数(统计卡片)、Tier分布(饼图)、爆发类型分布(饼图)、分类分布(饼图)、周搜索量趋势(柱状图)

### 筛选视图
- Tier 1 高优先级（按排名变化降序）
- Tier 2 观察区（按排名变化降序）

---

## 注意事项

- Windows 下运行需设置 `export PYTHONIOENCODING=utf-8` 或 `set PYTHONIOENCODING=utf-8`
- lark-cli 必须通过 `lark-cli config init` 和 `lark-cli auth login` 完成认证后才能使用
- 多维表格配置保存在 `category_config.json`，删除其中 `bitable_token` 相关字段可强制重建表格
