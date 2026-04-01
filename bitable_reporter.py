"""飞书多维表格报告生成器 — 替代 HTML reporter

首次运行：创建 Bitable + 3张表 + 视图 + 仪表盘
后续运行：复用已有 Bitable，追加本周数据
"""
import json
import logging
import os
import shutil
import subprocess
import time
from datetime import datetime
from dataclasses import asdict

import config
from analyzer import TrendData

logger = logging.getLogger(__name__)

# ─── 字段映射常量 ───
BURST_LABEL = {
    "first_burst": "首次爆发",
    "rebound": "回弹",
    "steady_rise": "持续上升",
    "declining": "下降中",
    "long_tail_expansion": "长尾扩展",
    "unknown": "未知",
}

CATEGORY_LABEL = {
    "ingredient": "核心产品",
    "benefit": "功效/场景",
    "brand": "品牌",
    "condition": "场景/症状",
    "form": "形态/规格",
    "irrelevant": "无关",
}

# ─── lark-cli 封装 ───
def _find_lark_cli():
    """查找 lark-cli 可执行文件路径"""
    # 优先用 shutil.which（它在 Windows 下也会查 .cmd）
    path = shutil.which("lark-cli")
    if path:
        return path
    # Windows npm 全局安装位置
    npm_path = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "npm", "lark-cli.cmd")
    if os.path.exists(npm_path):
        return npm_path
    return "lark-cli"  # fallback

_LARK_CLI = _find_lark_cli()

def _run_cli(args: list, timeout=30) -> dict:
    """执行 lark-cli 命令，返回解析后的 JSON"""
    cmd = [_LARK_CLI] + args
    logger.debug(f"CLI: {' '.join(cmd[:6])}...")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8")
        # lark-cli 可能输出到 stdout 或 stderr
        output = (r.stdout or r.stderr or "").strip()
        if not output:
            logger.error(f"lark-cli 无输出")
            return {"ok": False, "error": "no output"}
        return json.loads(output)
    except json.JSONDecodeError:
        logger.error(f"lark-cli 输出非 JSON: {r.stdout[:300]}")
        return {"ok": False, "error": r.stdout[:300]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _cli_ok(result: dict, action: str) -> bool:
    if result.get("ok"):
        return True
    logger.error(f"{action} 失败: {result.get('error', result)}")
    return False


# ─── enrichment（从 reporter.py 移植） ───
def _enrich(td: TrendData, keyword_analysis: dict) -> dict:
    """将 TrendData 转换为 bitable 字段值字典"""
    d = {}
    d["关键词"] = td.keyword
    d["中文名"] = td.zh_name or ""
    d["Tier"] = f"Tier {td.tier}"
    d["当前排名"] = td.current_rank
    d["前周排名"] = td.previous_rank or 0
    # 排名变化：正数=排名上升（previous > current）
    if td.previous_rank and td.previous_rank > 0:
        d["排名变化"] = td.previous_rank - td.current_rank
    else:
        d["排名变化"] = td.rank_change
    d["分类"] = CATEGORY_LABEL.get(td.category, td.category)
    d["爆发类型"] = BURST_LABEL.get(td.burst_type, "未知")

    # 搜索量
    vols = [(m.get("searchVolume") or m.get("volume", 0))
            for m in (td.monthly_volumes or [])
            if (m.get("searchVolume") or m.get("volume", 0)) > 0]
    d["月搜索量"] = vols[-1] if vols else 0
    d["峰值搜索量"] = max(vols) if vols else 0

    # CPC
    cpc_val = None
    for m in reversed(td.monthly_volumes or []):
        if isinstance(m, dict) and m.get("cpc") and float(m["cpc"]) > 0:
            cpc_val = float(m["cpc"])
            break
    if not cpc_val and td.cpc_history:
        for c in reversed(td.cpc_history):
            if isinstance(c, dict):
                v = c.get("cpc") or c.get("bid")
                if v and float(v) > 0:
                    cpc_val = float(v)
                    break
    d["CPC"] = round(cpc_val, 2) if cpc_val else 0

    d["环比变化"] = round(td.volume_mom_change * 100, 1) if td.volume_mom_change is not None else 0
    d["历史最佳排名"] = td.historical_peak_rank or 0
    d["数据来源"] = td.combo_label
    d["AI分析"] = keyword_analysis.get(td.keyword, "")
    return d


# ─── Bitable 创建 ───
def _create_bitable(category_name: str) -> tuple:
    """创建多维表格，返回 (base_token, bitable_url)"""
    name = f"{category_name} ABA关键词监测"
    res = _run_cli(["base", "+base-create", "--name", name])
    if not _cli_ok(res, "创建多维表格"):
        return None, None
    data = res.get("data", {})
    base_info = data.get("base", data)
    token = base_info.get("base_token") or base_info.get("app_token", "")
    url = base_info.get("url", "")
    logger.info(f"多维表格已创建: {url}")
    return token, url


def _create_keywords_table(base_token: str) -> str:
    """创建关键词监测主表"""
    fields = json.dumps([
        {"name": "关键词", "type": "text"},
        {"name": "周次", "type": "text"},
        {"name": "中文名", "type": "text"},
        {"name": "Tier", "type": "select", "multiple": False, "options": [
            {"name": "Tier 1", "hue": "Red", "lightness": "Standard"},
            {"name": "Tier 2", "hue": "Orange", "lightness": "Standard"},
            {"name": "Tier 3", "hue": "Blue", "lightness": "Standard"},
        ]},
        {"name": "当前排名", "type": "number", "style": {"type": "plain", "precision": 0}},
        {"name": "前周排名", "type": "number", "style": {"type": "plain", "precision": 0}},
        {"name": "排名变化", "type": "number", "style": {"type": "plain", "precision": 0}},
        {"name": "分类", "type": "select", "multiple": False, "options": [
            {"name": "核心产品", "hue": "Green", "lightness": "Standard"},
            {"name": "功效/场景", "hue": "Blue", "lightness": "Standard"},
            {"name": "品牌", "hue": "Purple", "lightness": "Standard"},
            {"name": "场景/症状", "hue": "Yellow", "lightness": "Standard"},
            {"name": "形态/规格", "hue": "Turquoise", "lightness": "Standard"},
            {"name": "无关", "hue": "Gray", "lightness": "Standard"},
        ]},
        {"name": "爆发类型", "type": "select", "multiple": False, "options": [
            {"name": "首次爆发", "hue": "Red", "lightness": "Standard"},
            {"name": "回弹", "hue": "Orange", "lightness": "Standard"},
            {"name": "持续上升", "hue": "Green", "lightness": "Standard"},
            {"name": "下降中", "hue": "Gray", "lightness": "Standard"},
            {"name": "长尾扩展", "hue": "Blue", "lightness": "Standard"},
            {"name": "未知", "hue": "Gray", "lightness": "Lighter"},
        ]},
        {"name": "月搜索量", "type": "number", "style": {"type": "plain", "precision": 0, "thousands_separator": True}},
        {"name": "峰值搜索量", "type": "number", "style": {"type": "plain", "precision": 0, "thousands_separator": True}},
        {"name": "CPC", "type": "number", "style": {"type": "currency", "precision": 2, "currency_code": "USD"}},
        {"name": "环比变化", "type": "number", "style": {"type": "plain", "precision": 1}},
        {"name": "历史最佳排名", "type": "number", "style": {"type": "plain", "precision": 0}},
        {"name": "数据来源", "type": "text"},
        {"name": "AI分析", "type": "text"},
        {"name": "抓取时间", "type": "datetime"},
    ], ensure_ascii=False)

    res = _run_cli(["base", "+table-create",
                     "--base-token", base_token,
                     "--name", "关键词监测",
                     "--fields", fields])
    if not _cli_ok(res, "创建关键词监测表"):
        return ""
    table_id = res.get("data", {}).get("table", {}).get("id", "")
    logger.info(f"关键词监测表: {table_id}")
    return table_id


def _create_extended_table(base_token: str) -> str:
    """创建扩展关键词表"""
    fields = json.dumps([
        {"name": "主关键词", "type": "text"},
        {"name": "周次", "type": "text"},
        {"name": "扩展词", "type": "text"},
        {"name": "周搜索量", "type": "number", "style": {"type": "plain", "precision": 0, "thousands_separator": True}},
        {"name": "月搜索量", "type": "number", "style": {"type": "plain", "precision": 0, "thousands_separator": True}},
        {"name": "CPC", "type": "number", "style": {"type": "currency", "precision": 2, "currency_code": "USD"}},
        {"name": "季节性", "type": "text"},
    ], ensure_ascii=False)

    res = _run_cli(["base", "+table-create",
                     "--base-token", base_token,
                     "--name", "扩展关键词",
                     "--fields", fields])
    if not _cli_ok(res, "创建扩展关键词表"):
        return ""
    table_id = res.get("data", {}).get("table", {}).get("id", "")
    logger.info(f"扩展关键词表: {table_id}")
    return table_id


def _create_summary_table(base_token: str) -> str:
    """创建周报摘要表"""
    fields = json.dumps([
        {"name": "周次", "type": "text"},
        {"name": "抓取总数", "type": "number", "style": {"type": "plain", "precision": 0}},
        {"name": "类目相关数", "type": "number", "style": {"type": "plain", "precision": 0}},
        {"name": "Tier1数量", "type": "number", "style": {"type": "plain", "precision": 0}},
        {"name": "Tier2数量", "type": "number", "style": {"type": "plain", "precision": 0}},
        {"name": "Tier3数量", "type": "number", "style": {"type": "plain", "precision": 0}},
        {"name": "排除数量", "type": "number", "style": {"type": "plain", "precision": 0}},
        {"name": "核心发现", "type": "text"},
        {"name": "新增词典词", "type": "text"},
        {"name": "生成时间", "type": "datetime"},
    ], ensure_ascii=False)

    res = _run_cli(["base", "+table-create",
                     "--base-token", base_token,
                     "--name", "周报摘要",
                     "--fields", fields])
    if not _cli_ok(res, "创建周报摘要表"):
        return ""
    table_id = res.get("data", {}).get("table", {}).get("id", "")
    logger.info(f"周报摘要表: {table_id}")
    return table_id


# ─── 视图创建 ───
def _create_views(base_token: str, table_id: str):
    """为关键词监测表创建筛选视图"""
    views = json.dumps([
        {"name": "Tier 1 高优先级", "type": "grid"},
        {"name": "Tier 2 观察区", "type": "grid"},
    ], ensure_ascii=False)
    res = _run_cli(["base", "+view-create",
                     "--base-token", base_token,
                     "--table-id", table_id,
                     "--json", views])
    if not _cli_ok(res, "创建视图"):
        return

    # 解析返回的 view_id 列表
    view_list = res.get("data", {}).get("views", [])
    if not view_list or len(view_list) < 2:
        logger.warning("视图创建返回数据不完整，跳过筛选设置")
        return

    # Tier 1 视图过滤
    tier1_view_id = view_list[0].get("id") or view_list[0].get("view_id", "")
    if tier1_view_id:
        _run_cli(["base", "+view-set-filter",
                   "--base-token", base_token,
                   "--table-id", table_id,
                   "--view-id", tier1_view_id,
                   "--json", json.dumps({
                       "conjunction": "and",
                       "conditions": [{"field_name": "Tier", "operator": "is", "value": ["Tier 1"]}]
                   }, ensure_ascii=False)])
        _run_cli(["base", "+view-set-sort",
                   "--base-token", base_token,
                   "--table-id", table_id,
                   "--view-id", tier1_view_id,
                   "--json", json.dumps([
                       {"field_name": "排名变化", "desc": True}
                   ], ensure_ascii=False)])

    # Tier 2 视图过滤
    tier2_view_id = view_list[1].get("id") or view_list[1].get("view_id", "")
    if tier2_view_id:
        _run_cli(["base", "+view-set-filter",
                   "--base-token", base_token,
                   "--table-id", table_id,
                   "--view-id", tier2_view_id,
                   "--json", json.dumps({
                       "conjunction": "and",
                       "conditions": [{"field_name": "Tier", "operator": "is", "value": ["Tier 2"]}]
                   }, ensure_ascii=False)])
        _run_cli(["base", "+view-set-sort",
                   "--base-token", base_token,
                   "--table-id", table_id,
                   "--view-id", tier2_view_id,
                   "--json", json.dumps([
                       {"field_name": "排名变化", "desc": True}
                   ], ensure_ascii=False)])

    logger.info("视图和筛选配置完成")


# ─── 仪表盘创建 ───
def _create_dashboard(base_token: str) -> str:
    """创建仪表盘并添加图表"""
    res = _run_cli(["base", "+dashboard-create",
                     "--base-token", base_token,
                     "--name", "ABA监测仪表盘",
                     "--theme-style", "SimpleBlue"])
    if not _cli_ok(res, "创建仪表盘"):
        return ""
    dashboard_id = res.get("data", {}).get("dashboard", {}).get("dashboard_id", "")
    if not dashboard_id:
        return ""
    logger.info(f"仪表盘: {dashboard_id}")

    charts = [
        ("关键词总数", "statistics",
         {"table_name": "关键词监测", "count_all": True}),
        ("Tier 分布", "pie",
         {"table_name": "关键词监测", "count_all": True,
          "group_by": [{"field_name": "Tier", "mode": "integrated"}]}),
        ("爆发类型分布", "pie",
         {"table_name": "关键词监测", "count_all": True,
          "group_by": [{"field_name": "爆发类型", "mode": "integrated"}]}),
        ("分类分布", "pie",
         {"table_name": "关键词监测", "count_all": True,
          "group_by": [{"field_name": "分类", "mode": "integrated"}]}),
        ("排名变化 Top", "bar",
         {"table_name": "关键词监测",
          "series": [{"field_name": "排名变化", "rollup": "MAX"}],
          "group_by": [{"field_name": "关键词", "mode": "integrated",
                        "sort": {"field_name": "排名变化", "order": "desc"}}]}),
        ("周搜索量趋势", "column",
         {"table_name": "关键词监测",
          "series": [{"field_name": "月搜索量", "rollup": "SUM"}],
          "group_by": [{"field_name": "周次", "mode": "integrated"}]}),
    ]

    for name, chart_type, data_config in charts:
        r = _run_cli(["base", "+dashboard-block-create",
                       "--base-token", base_token,
                       "--dashboard-id", dashboard_id,
                       "--name", name,
                       "--type", chart_type,
                       "--data-config", json.dumps(data_config, ensure_ascii=False)])
        if _cli_ok(r, f"图表 {name}"):
            logger.info(f"  图表 [{name}] 已添加")
        time.sleep(0.5)

    return dashboard_id


# ─── 初始化 / 复用 ───
def ensure_bitable() -> dict:
    """确保 Bitable 存在，返回 {base_token, table_ids, dashboard_id, bitable_url}"""
    bt_cfg = config.get_bitable_config()

    if bt_cfg["bitable_token"] and bt_cfg["table_ids"].get("keywords"):
        logger.info(f"复用已有多维表格: {bt_cfg['bitable_url']}")
        return bt_cfg

    category_name = config.get_category_name()
    logger.info("首次运行，创建飞书多维表格...")

    base_token, bitable_url = _create_bitable(category_name)
    if not base_token:
        return {}

    time.sleep(1)

    kw_table = _create_keywords_table(base_token)
    time.sleep(0.5)
    ext_table = _create_extended_table(base_token)
    time.sleep(0.5)
    summary_table = _create_summary_table(base_token)
    time.sleep(0.5)

    if not all([kw_table, ext_table, summary_table]):
        logger.error("表创建不完整")
        return {}

    table_ids = {"keywords": kw_table, "extended": ext_table, "summary": summary_table}

    _create_views(base_token, kw_table)
    time.sleep(0.5)

    dashboard_id = _create_dashboard(base_token)

    config.save_bitable_config(base_token, bitable_url, table_ids, dashboard_id)
    logger.info("多维表格初始化完成，配置已保存")

    return {
        "bitable_token": base_token,
        "bitable_url": bitable_url,
        "table_ids": table_ids,
        "dashboard_id": dashboard_id,
    }


# ─── 数据写入 ───
def _write_record(base_token: str, table_id: str, record: dict):
    """写入单条记录"""
    res = _run_cli(["base", "+record-upsert",
                     "--base-token", base_token,
                     "--table-id", table_id,
                     "--json", json.dumps(record, ensure_ascii=False)])
    return res.get("ok", False)


def write_results(bt_cfg: dict, results: list, tiered_data: dict, analysis: dict):
    """将本周数据写入 3 张表"""
    base_token = bt_cfg["bitable_token"]
    kw_table = bt_cfg["table_ids"]["keywords"]
    ext_table = bt_cfg["table_ids"]["extended"]
    summary_table = bt_cfg["table_ids"]["summary"]

    now = datetime.now()
    week_label = f"{now.year}-W{now.isocalendar()[1]:02d}"
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    keyword_analysis = analysis.get("keyword_analysis", {})

    # 写入关键词监测表
    logger.info(f"写入 {len(results)} 条关键词记录...")
    success_count = 0
    for td in results:
        record = _enrich(td, keyword_analysis)
        record["周次"] = week_label
        record["抓取时间"] = timestamp
        if _write_record(base_token, kw_table, record):
            success_count += 1
        time.sleep(0.3)  # 避免限流
    logger.info(f"关键词表写入完成: {success_count}/{len(results)}")

    # 写入扩展关键词表
    ext_count = 0
    for td in results:
        if not td.extended_keywords:
            continue
        for ek in td.extended_keywords:
            kw_name = ek.get("关键词") or ek.get("keyword", "")
            record = {
                "主关键词": td.keyword,
                "周次": week_label,
                "扩展词": kw_name,
                "周搜索量": ek.get("周搜索量", 0) or 0,
                "月搜索量": ek.get("月搜索量", 0) or 0,
                "CPC": float(ek.get("cpc推荐竞价", 0) or 0) if ek.get("cpc推荐竞价") else 0,
                "季节性": ek.get("季节性", ""),
            }
            if _write_record(base_token, ext_table, record):
                ext_count += 1
            time.sleep(0.3)
    if ext_count:
        logger.info(f"扩展关键词表写入: {ext_count} 条")

    # 写入周报摘要表
    core_findings = analysis.get("core_findings", [])
    new_words = tiered_data.get("new_words", {})
    new_words_text = "; ".join(
        f"{cat}: {', '.join(words)}"
        for cat, words in new_words.items() if words
    )
    tier_counts = {1: 0, 2: 0, 3: 0}
    for td in results:
        tier_counts[td.tier] = tier_counts.get(td.tier, 0) + 1

    summary_record = {
        "周次": week_label,
        "抓取总数": tiered_data.get("total_scraped", 0),
        "类目相关数": tiered_data.get("total_category", 0),
        "Tier1数量": tier_counts[1],
        "Tier2数量": tier_counts[2],
        "Tier3数量": tier_counts[3],
        "排除数量": len(tiered_data.get("excluded_keywords", {})),
        "核心发现": "\n".join(f"{i+1}. {f}" for i, f in enumerate(core_findings)),
        "新增词典词": new_words_text,
        "生成时间": timestamp,
    }
    _write_record(base_token, summary_table, summary_record)
    logger.info("周报摘要写入完成")


# ─── 主入口 ───
def generate_bitable_report(results, total_scraped, total_category, new_dict_words,
                            analysis=None, excluded_keywords=None, sorftime_stats=None,
                            tiered_data=None):
    """生成飞书多维表格报告 — step3 调用入口"""
    analysis = analysis or {}
    tiered_data = tiered_data or {
        "total_scraped": total_scraped,
        "total_category": total_category,
        "new_words": new_dict_words,
        "excluded_keywords": excluded_keywords or {},
        "sorftime_stats": sorftime_stats or {},
    }

    bt_cfg = ensure_bitable()
    if not bt_cfg:
        logger.error("多维表格初始化失败")
        return None

    write_results(bt_cfg, results, tiered_data, analysis)

    url = bt_cfg.get("bitable_url", "")
    logger.info(f"飞书多维表格报告完成: {url}")
    return url
