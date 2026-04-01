"""通用配置 - 亚马逊 ABA 爆品关键词监测系统

类目参数化：所有类目相关配置从 category_config.json 动态读取。
Sorftime key 自动从 mcp.json 提取或环境变量读取。
"""
import os
import sys
import subprocess
import json

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── 自动安装依赖 ───
def ensure_dependencies():
    req_path = os.path.join(SKILL_DIR, "requirements.txt")
    if not os.path.exists(req_path):
        return
    try:
        import httpx, selectolax, jinja2  # noqa: F401
    except ImportError:
        print("📦 首次运行，自动安装依赖...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q", "-r", req_path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        print("✅ 依赖安装完成")

ensure_dependencies()

# ─── AMZ123 抓取配置 ───
AMZ123_BASE_URL = "https://www.amz123.com/usatopkeywords"
MAX_PAGES = 5
SCRAPE_COMBOS = [
    {"rank": "1_1000",      "uprank": "1001",     "label": "高排名+高涨幅"},
    {"rank": "1001_10000",  "uprank": "1001",     "label": "中排名+高涨幅"},
    {"rank": "10001_50000", "uprank": "1001",     "label": "低排名+高涨幅"},
    {"rank": "50001",       "uprank": "1001",     "label": "超低排名+高涨幅"},
    {"rank": "1_1000",      "uprank": "101_1000", "label": "高排名+中涨幅"},
    {"rank": "1001_10000",  "uprank": "101_1000", "label": "中排名+中涨幅"},
]

# ─── Tier 分层阈值 ───
TIER1_RANK_THRESHOLD = 1000
TIER2_RANK_THRESHOLD = 50000
TIER1_SURGE_RATIO = 0.5
TIER1_SURGE_ABS = 1000
TIER2_CROSS_FROM = 100000
TIER2_CROSS_TO = 50000
TIER3_CROSS_FROM = 200000
TIER3_CROSS_TO = 100000
REBOUND_PEAK_THRESHOLD = 100

# ─── Sorftime 并发配置 ───
SORFTIME_BASE_URL = "https://mcp.sorftime.com"
SORFTIME_CONCURRENCY = 10
SORFTIME_TIMEOUT = 30
VERIFY_SSL = os.environ.get("VERIFY_SSL", "false").lower() == "true"

# ─── Sorftime API Key 提取 ───
def _extract_sorftime_key():
    """从 mcp.json 自动提取 Sorftime key（工作区级 → 用户级）"""
    def _try_extract(mcp_path):
        if not os.path.exists(mcp_path):
            return None
        try:
            with open(mcp_path, "r", encoding="utf-8") as f:
                mcp = json.load(f)
            url = mcp.get("mcpServers", {}).get("sorftimeMCP", {}).get("url", "")
            if "key=" in url:
                key = url.split("key=", 1)[1].split("&")[0]
                if key and not key.startswith("YOUR_"):
                    return key
        except Exception:
            pass
        return None

    # 从 skill 目录向上查找工作区级
    d = SKILL_DIR
    for _ in range(10):
        key = _try_extract(os.path.join(d, ".kiro", "settings", "mcp.json"))
        if key:
            return key
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    # 用户级
    return _try_extract(os.path.join(os.path.expanduser("~"), ".kiro", "settings", "mcp.json")) or ""

SORFTIME_API_KEY = os.environ.get("SORFTIME_API_KEY", "") or _extract_sorftime_key()

# ─── 工作区根目录 ───
def _find_workspace_root():
    d = SKILL_DIR
    for _ in range(10):
        if os.path.isdir(os.path.join(d, ".kiro")):
            if os.path.basename(d) != ".kiro":
                return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return os.getcwd()

WORKSPACE_ROOT = _find_workspace_root()

# ─── 类目配置 ───
CATEGORY_CONFIG_PATH = os.path.join(SKILL_DIR, "category_config.json")

def load_category_config() -> dict:
    """加载当前类目配置"""
    if not os.path.exists(CATEGORY_CONFIG_PATH):
        return {}
    with open(CATEGORY_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_category_config(cfg: dict):
    with open(CATEGORY_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def get_category_name() -> str:
    cfg = load_category_config()
    return cfg.get("category_name", "未配置")

def get_category_name_en() -> str:
    cfg = load_category_config()
    return cfg.get("category_name_en", "unknown")

# ─── 数据存储路径（按类目隔离）───
def _get_data_dir():
    cfg = load_category_config()
    cat_en = cfg.get("category_name_en", "default")
    return os.path.join(SKILL_DIR, "data", cat_en)

@property
def DATA_DIR():
    return _get_data_dir()

# 为了兼容模块级引用，提供函数
def get_data_dir():
    return _get_data_dir()

def get_dict_path():
    return os.path.join(get_data_dir(), "category_dict.json")

def get_exclusion_path():
    return os.path.join(get_data_dir(), "exclusion_rules.json")

def get_db_path():
    return os.path.join(get_data_dir(), "history.db")

# ─── 报告输出 ───
REPORT_DIR = os.path.join(WORKSPACE_ROOT, "reports")
TEMPLATE_DIR = os.path.join(SKILL_DIR, "templates")
EXCHANGE_DIR = os.path.join(WORKSPACE_ROOT, "reports", ".exchange")

# ─── 启动检查 ───
def check_sorftime_ready() -> bool:
    if not SORFTIME_API_KEY:
        print()
        print("=" * 70)
        print("❌  Sorftime MCP 未配置！本工具必须配置 Sorftime 才能运行。")
        print("=" * 70)
        print()
        print("📋 配置步骤：")
        print()
        print("  1. 获取 Sorftime API Key：")
        print("     访问 https://www.sorftime.com 注册并获取 MCP API Key")
        print()
        print("  2. 配置 mcp.json（选择以下任一位置）：")
        print()
        ws_path = os.path.join(WORKSPACE_ROOT, ".kiro", "settings", "mcp.json")
        user_path = os.path.join(os.path.expanduser("~"), ".kiro", "settings", "mcp.json")
        print(f"     工作区级: {ws_path}")
        print(f"     用户级:   {user_path}")
        print()
        print("  3. 在 mcp.json 中添加以下内容：")
        print()
        print('     {')
        print('       "mcpServers": {')
        print('         "sorftimeMCP": {')
        print('           "url": "https://mcp.sorftime.com?key=你的API_KEY"')
        print('         }')
        print('       }')
        print('     }')
        print()
        print("  4. 或者设置环境变量：")
        print("     set SORFTIME_API_KEY=你的API_KEY")
        print()
        print("=" * 70)
        return False
    return True

def get_bitable_config() -> dict:
    """获取 bitable 相关配置（token、table_ids、dashboard_id）"""
    cfg = load_category_config()
    return {
        "bitable_token": cfg.get("bitable_token", ""),
        "bitable_url": cfg.get("bitable_url", ""),
        "table_ids": cfg.get("table_ids", {}),
        "dashboard_id": cfg.get("dashboard_id", ""),
    }

def save_bitable_config(bitable_token, bitable_url, table_ids, dashboard_id):
    """保存 bitable 配置到 category_config.json"""
    cfg = load_category_config()
    cfg["bitable_token"] = bitable_token
    cfg["bitable_url"] = bitable_url
    cfg["table_ids"] = table_ids
    cfg["dashboard_id"] = dashboard_id
    save_category_config(cfg)

def check_category_ready() -> bool:
    cfg = load_category_config()
    if not cfg.get("category_name"):
        print()
        print("⚠️  尚未初始化类目配置！请先运行：")
        print(f"   python {os.path.join(SKILL_DIR, 'main.py')} init")
        print()
        return False
    return True
