# Amazon ABA 爆品关键词监测系统

> 从亚马逊 ABA 热搜词榜单中，自动发现你所在类目正在爆发的关键词，生成飞书多维表格 + 仪表盘报告。

比如你做宠物用品，它能帮你发现 "dog calming treats" 这周突然从 10 万名冲到 500 名——比竞争对手早发现一周，就是你的优势。

---

## 功能亮点

- **任意类目**：对讲机、保健品、宠物用品、美妆护肤……首次运行交互式配置，无需改代码
- **AI 驱动**：自动生成类目词典、分类关键词、撰写分析摘要，搭配任意 AI IDE 使用
- **飞书报告**：自动创建多维表格 + 仪表盘，每周数据追加积累，打开链接即可查看
- **三级预警**：Tier 1（高优先级）/ Tier 2（观察区）/ Tier 3（长尾），快速定位最有价值的词
- **Sorftime 深度数据**：搜索量趋势、CPC、竞品数据、扩展词，一次查到位

---

## 效果展示

运行 `step3` 后自动在飞书生成：

| 输出 | 说明 |
|:---|:---|
| 关键词监测表 | 17 字段主表（排名、搜索量、CPC、AI 分析等） |
| 扩展关键词表 | Tier 1 关键词的延伸变体词 |
| 周报摘要表 | 每周汇总（各 Tier 数量、核心发现） |
| 仪表盘 | 5 张图表（Tier 分布、爆发类型、搜索量趋势等） |
| 筛选视图 | Tier 1 高优先级 / Tier 2 观察区 |

> 截图占位：在此放置飞书多维表格截图

---

## 前置要求

| 依赖 | 说明 |
|:---|:---|
| Python 3.8+ | `python --version` 检查 |
| AI IDE | Kiro / Trae / Cursor / Claude Code 任选 |
| Sorftime MCP | 数据引擎，[sorftime.com](https://www.sorftime.com) 注册获取 API Key |
| 飞书 lark-cli | 报告输出，`npm install -g lark-cli` |

---

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/你的用户名/Amazon-ABAkeyword.git
cd Amazon-ABAkeyword
```

### 2. 配置 Sorftime MCP

在你的 AI IDE 的 MCP 配置文件中添加：

```json
{
  "mcpServers": {
    "sorftimeMCP": {
      "url": "https://mcp.sorftime.com?key=你的API_KEY"
    }
  }
}
```

或设置环境变量：

```bash
export SORFTIME_API_KEY=你的API_KEY
```

### 3. 配置飞书 lark-cli

```bash
npm install -g lark-cli
lark-cli config init
lark-cli auth login
```

### 4. 开始使用

在 AI IDE 对话框里说一句话即可：

> "帮我用这个工具监测亚马逊关键词，我做的是**宠物用品**，运行 `python main.py init`，然后按流程走完整个监测"

Python 依赖（httpx、selectolax、jinja2）会在首次运行时自动安装。

---

## 使用流程

### 首次使用：类目初始化

```bash
# Step 0: 初始化类目
python main.py init
# → 按提示输入类目名称，系统输出 reports/.exchange/dict_draft.json
# → AI 读取后生成词典，写入 dict_draft_output.json

# Step 0.5: 确认词典
python main.py init-confirm
```

### 日常监测：每周跑一次

对 AI 说："帮我跑一下本周的 ABA 数据"，或手动分步执行：

```bash
# Step 1: 抓取 AMZ123 + 本地词典匹配
python main.py step1
# → AI 读取 llm_input.json，分类+翻译，写入 llm_output.json

# Step 2: 分层 + Sorftime 深度查询
python main.py step2
# → AI 读取 analysis_input.json，写分析摘要，写入 analysis_output.json

# Step 3: 生成飞书多维表格报告
python main.py step3
# → 自动创建/追加飞书多维表格，输出报告链接
```

---

## 飞书多维表格结构

### 3 张数据表

**关键词监测（主表，17 字段）**

| 字段 | 类型 | 说明 |
|:---|:---|:---|
| 关键词 | 文本 | 英文原词 |
| 周次 | 文本 | 如 2026-W14 |
| 中文名 | 文本 | AI 翻译 |
| Tier | 单选 | Tier 1 / 2 / 3 |
| 当前排名 | 数字 | ABA 当前排名 |
| 前周排名 | 数字 | 上周排名 |
| 排名变化 | 数字 | 正数=上升 |
| 分类 | 单选 | 核心产品/功效/品牌等 |
| 爆发类型 | 单选 | 首次爆发/回弹/持续上升等 |
| 月搜索量 | 数字 | 最新月搜索量 |
| 峰值搜索量 | 数字 | 历史峰值 |
| CPC | 数字 | 美元 |
| 环比变化 | 数字 | 百分比 |
| 历史最佳排名 | 数字 | |
| 数据来源 | 文本 | 抓取组合标签 |
| AI分析 | 文本 | AI 撰写的分析摘要 |
| 抓取时间 | 日期 | |

**扩展关键词表** — 主关键词、扩展词、搜索量、CPC、季节性

**周报摘要表** — 周次、抓取总数、各 Tier 数量、核心发现

### 仪表盘（5 张图表）

- 关键词总数（统计卡片）
- Tier 分布（饼图）
- 爆发类型分布（饼图）
- 分类分布（饼图）
- 周搜索量趋势（柱状图）

### 筛选视图

- **Tier 1 高优先级** — 按排名变化降序
- **Tier 2 观察区** — 按排名变化降序

---

## Tier 分层规则

| 等级 | 条件 | 说明 |
|:---|:---|:---|
| Tier 1 | TOP 1000 且涨幅 >=50% 或 >=1000 位 | 高优先级，需立即关注 |
| Tier 2 | 1000-50000 且从 10万+ 进入 5万内 | 中优先级，持续观察 |
| Tier 3 | 50000+ 首次出现或大幅跨越 | 长尾信号，备选关注 |

## 分类标签

| 标签 | 含义 | 示例 |
|:---|:---|:---|
| ingredient | 核心产品词 | walkie talkie, dog treats |
| benefit | 功效/场景 | waterproof, long range |
| brand | 品牌 | Motorola, Baofeng |
| condition | 场景/症状 | camping, emergency |
| form | 形态/规格 | rechargeable, 2 pack |
| irrelevant | 无关 | — |

---

## 文件结构

```
Amazon-ABAkeyword/
├── main.py                    # 主入口 (init / step1 / step2 / step3)
├── config.py                  # 配置 (Sorftime key 提取 + Bitable 持久化)
├── scraper.py                 # AMZ123 ABA 热搜词抓取
├── classifier.py              # 关键词分类器 (本地词典 + LLM)
├── analyzer.py                # Tier 分层 + 爆发类型判断
├── sorftime_client.py         # Sorftime 异步批量查询
├── category_init.py           # 类目初始化交互流程
├── bitable_reporter.py        # 飞书多维表格报告生成
├── reporter.py                # HTML 报告生成 (备用)
├── db.py                      # SQLite 历史存储
├── requirements.txt           # Python 依赖 (自动安装)
├── category_config.example.json  # 配置模板
├── SKILL.md                   # AI IDE Skill 描述
├── AGENT_GUIDE.md             # AI Agent 操作指南
├── LICENSE                    # MIT
├── templates/
│   └── report.html            # HTML 报告模板 (备用)
└── data/                      # 运行时生成 (git ignored)
    └── {类目}/
        ├── category_dict.json
        ├── exclusion_rules.json
        └── history.db
```

---

## 常见问题

### Sorftime 未配置？

检查 MCP 配置文件中 `sorftimeMCP` 的 key 是否正确，或设置环境变量：

```bash
# Windows
set SORFTIME_API_KEY=你的KEY

# Mac/Linux
export SORFTIME_API_KEY=你的KEY
```

### 飞书报告生成失败？

1. 确认 lark-cli 已认证：`lark-cli auth login`
2. Windows 下 Python 找不到 lark-cli？检查 `%APPDATA%/npm/` 下是否有 `lark-cli.cmd`
3. 想重建表格？删除 `category_config.json` 中的 `bitable_token` 相关字段

### Windows 中文乱码？

```bash
set PYTHONIOENCODING=utf-8
```

### 可以同时监测多个类目吗？

目前一个项目实例监测一个类目。想监测多个类目，复制一份项目文件夹即可。

### 词典不够准？

- 每次运行自动学习新词并回写词典
- 手动编辑 `data/{类目}/category_dict.json` 添加/删除词
- 重新运行 `python main.py init` 可重新初始化

---

## 数据来源

| 来源 | 提供数据 |
|:---|:---|
| [AMZ123](https://www.amz123.com) | ABA 热搜词排名、涨跌幅 |
| [Sorftime](https://www.sorftime.com) | 搜索量趋势、CPC、竞品数据、扩展词 |

---

## License

[MIT](LICENSE)
