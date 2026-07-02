
import json
from datetime import datetime
import numpy as np
import pandas as pd
import streamlit as st

try:
    import yfinance as yf
except Exception:
    yf = None

st.set_page_config(page_title="智策企業估值實驗室 V20.3", page_icon="🏛️", layout="wide")
st.title("🏛️ Enterprise Valuation Lab")
st.subheader("V20.3｜股價人工覆核版：記憶體價格強制修正")
st.info("本版針對記憶體族群啟用人工覆核價格，不再直接採用 yfinance 連線價；保留原始股價、修正股價與審查備註，避免10倍錯誤影響估值判讀。")

BENCHMARK = [
    # AI Infrastructure
    {"公司":"2330 台積電","代號":"2330.TW","CID":"AI Infrastructure","Stage":"Leader","fallback_price":2505,"fallback":{"EPS":65.46,"BVPS":206.5,"ROE":31.7,"ROIC":46.7,"FCF_Margin":26.05,"Revenue_CAGR":18.94,"EPS_Growth":19.57,"Dividend":15,"Industry_Health":92}},
    {"公司":"3661 世芯-KY","代號":"3661.TW","CID":"AI Infrastructure","Stage":"Growth","fallback_price":3200,"fallback":{"EPS":62,"BVPS":170,"ROE":36,"ROIC":32,"FCF_Margin":18,"Revenue_CAGR":35,"EPS_Growth":38,"Dividend":12,"Industry_Health":88}},
    {"公司":"3443 創意","代號":"3443.TW","CID":"AI Infrastructure","Stage":"Growth","fallback_price":1200,"fallback":{"EPS":32,"BVPS":92,"ROE":34,"ROIC":30,"FCF_Margin":16,"Revenue_CAGR":24,"EPS_Growth":26,"Dividend":8,"Industry_Health":86}},

    # AI Platform
    {"公司":"2454 聯發科","代號":"2454.TW","CID":"AI Platform","Stage":"Leader","fallback_price":4335,"fallback":{"EPS":65.98,"BVPS":250.99,"ROE":26.29,"ROIC":59.58,"FCF_Margin":23.05,"Revenue_CAGR":2.79,"EPS_Growth":-3.76,"Dividend":75,"Industry_Health":88}},
    {"公司":"2379 瑞昱","代號":"2379.TW","CID":"AI Platform","Stage":"Leader","fallback_price":580,"fallback":{"EPS":26,"BVPS":115,"ROE":22,"ROIC":28,"FCF_Margin":18,"Revenue_CAGR":8,"EPS_Growth":10,"Dividend":16,"Industry_Health":82}},
    {"公司":"3034 聯詠","代號":"3034.TW","CID":"AI Platform","Stage":"Leader","fallback_price":520,"fallback":{"EPS":34,"BVPS":160,"ROE":22,"ROIC":28,"FCF_Margin":20,"Revenue_CAGR":5,"EPS_Growth":6,"Dividend":28,"Industry_Health":78}},

    # AI Server
    {"公司":"2382 廣達","代號":"2382.TW","CID":"AI Server Platform","Stage":"Growth","fallback_price":372,"fallback":{"EPS":18.92,"BVPS":53.83,"ROE":36.84,"ROIC":21.36,"FCF_Margin":-1.2,"Revenue_CAGR":18.37,"EPS_Growth":37.32,"Dividend":6,"Industry_Health":88}},
    {"公司":"3231 緯創","代號":"3231.TW","CID":"AI Server Platform","Stage":"Growth","fallback_price":145,"fallback":{"EPS":8.5,"BVPS":42,"ROE":20,"ROIC":13,"FCF_Margin":4,"Revenue_CAGR":16,"EPS_Growth":22,"Dividend":3,"Industry_Health":84}},
    {"公司":"6669 緯穎","代號":"6669.TW","CID":"AI Server Platform","Stage":"Growth","fallback_price":2800,"fallback":{"EPS":95,"BVPS":360,"ROE":28,"ROIC":22,"FCF_Margin":8,"Revenue_CAGR":20,"EPS_Growth":24,"Dividend":40,"Industry_Health":86}},

    # Advanced Materials
    {"公司":"2383 台光電","代號":"2383.TW","CID":"Advanced Materials","Stage":"Growth","fallback_price":5535,"fallback":{"EPS":40.88,"BVPS":140.81,"ROE":29.03,"ROIC":29.7,"FCF_Margin":2.22,"Revenue_CAGR":34.58,"EPS_Growth":42.4,"Dividend":40,"Industry_Health":90}},
    {"公司":"6274 台燿","代號":"6274.TWO","CID":"Advanced Materials","Stage":"Growth","fallback_price":210,"fallback":{"EPS":8.5,"BVPS":55,"ROE":16,"ROIC":14,"FCF_Margin":6,"Revenue_CAGR":20,"EPS_Growth":28,"Dividend":4,"Industry_Health":86}},
    {"公司":"2368 金像電","代號":"2368.TW","CID":"Advanced Materials","Stage":"Growth","fallback_price":320,"fallback":{"EPS":14,"BVPS":62,"ROE":23,"ROIC":19,"FCF_Margin":10,"Revenue_CAGR":22,"EPS_Growth":30,"Dividend":5,"Industry_Health":86}},

    # Thermal
    {"公司":"3017 奇鋐","代號":"3017.TW","CID":"Thermal Solution","Stage":"Growth","fallback_price":2620,"fallback":{"EPS":60.1,"BVPS":115.16,"ROE":61.69,"ROIC":100.96,"FCF_Margin":22.75,"Revenue_CAGR":35.59,"EPS_Growth":66.43,"Dividend":12,"Industry_Health":86}},
    {"公司":"3324 雙鴻","代號":"3324.TWO","CID":"Thermal Solution","Stage":"Growth","fallback_price":950,"fallback":{"EPS":30,"BVPS":115,"ROE":28,"ROIC":24,"FCF_Margin":12,"Revenue_CAGR":24,"EPS_Growth":35,"Dividend":8,"Industry_Health":84}},
    {"公司":"3653 健策","代號":"3653.TW","CID":"Thermal Solution","Stage":"Leader","fallback_price":1350,"fallback":{"EPS":32,"BVPS":160,"ROE":22,"ROIC":20,"FCF_Margin":15,"Revenue_CAGR":18,"EPS_Growth":20,"Dividend":8,"Industry_Health":80}},

    # Automation
    {"公司":"6215 和椿","代號":"6215.TWO","CID":"Intelligent Automation","Stage":"Growth","fallback_price":108,"fallback":{"EPS":4.2,"BVPS":32,"ROE":12,"ROIC":14,"FCF_Margin":8,"Revenue_CAGR":18,"EPS_Growth":20,"Dividend":1.2,"Industry_Health":78}},
    {"公司":"2049 上銀","代號":"2049.TW","CID":"Intelligent Automation","Stage":"Growth","fallback_price":350,"fallback":{"EPS":7.5,"BVPS":92,"ROE":8,"ROIC":7,"FCF_Margin":5,"Revenue_CAGR":8,"EPS_Growth":10,"Dividend":4,"Industry_Health":72}},
    {"公司":"2359 所羅門","代號":"2359.TW","CID":"Intelligent Automation","Stage":"Growth","fallback_price":165,"fallback":{"EPS":5,"BVPS":38,"ROE":13,"ROIC":12,"FCF_Margin":6,"Revenue_CAGR":20,"EPS_Growth":28,"Dividend":2,"Industry_Health":78}},

    # Memory
    {"公司":"2408 南亞科","代號":"2408.TW","CID":"Memory Cycle","Stage":"Cycle","fallback_price":421,"fallback":{"EPS":10.81,"BVPS":62.25,"ROE":19.39,"ROIC":5.22,"FCF_Margin":7.34,"Revenue_CAGR":5.35,"EPS_Growth":-54.76,"Dividend":0.5,"Industry_Health":82}},
    {"公司":"2344 華邦電","代號":"2344.TW","CID":"Memory Cycle","Stage":"Cycle","fallback_price":30,"fallback":{"EPS":0.6,"BVPS":22,"ROE":3,"ROIC":2,"FCF_Margin":-3,"Revenue_CAGR":4,"EPS_Growth":-20,"Dividend":0.2,"Industry_Health":76}},
    {"公司":"2337 旺宏","代號":"2337.TW","CID":"Memory Cycle","Stage":"Cycle","fallback_price":28,"fallback":{"EPS":0.5,"BVPS":25,"ROE":2,"ROIC":1,"FCF_Margin":-5,"Revenue_CAGR":-3,"EPS_Growth":-30,"Dividend":0.1,"Industry_Health":72}},

    # Financial
    {"公司":"2881 富邦金","代號":"2881.TW","CID":"Financial Franchise","Stage":"Stable","fallback_price":122.5,"fallback":{"EPS":8.37,"BVPS":71.61,"ROE":18.73,"ROIC":10,"FCF_Margin":1.52,"Revenue_CAGR":14.15,"EPS_Growth":37.11,"Dividend":5,"Industry_Health":80}},
    {"公司":"2882 國泰金","代號":"2882.TW","CID":"Financial Franchise","Stage":"Stable","fallback_price":70,"fallback":{"EPS":5.5,"BVPS":58,"ROE":11,"ROIC":8,"FCF_Margin":2,"Revenue_CAGR":8,"EPS_Growth":12,"Dividend":3,"Industry_Health":78}},
    {"公司":"2891 中信金","代號":"2891.TW","CID":"Financial Franchise","Stage":"Stable","fallback_price":45,"fallback":{"EPS":3.6,"BVPS":28,"ROE":13,"ROIC":8,"FCF_Margin":2,"Revenue_CAGR":8,"EPS_Growth":12,"Dividend":2,"Industry_Health":78}},

    # Shipping
    {"公司":"2603 長榮","代號":"2603.TW","CID":"Shipping Cycle","Stage":"Cycle","fallback_price":185.5,"fallback":{"EPS":31.64,"BVPS":268.71,"ROE":8.22,"ROIC":13.41,"FCF_Margin":20.89,"Revenue_CAGR":-15.46,"EPS_Growth":-41.02,"Dividend":12,"Industry_Health":78}},
    {"公司":"2609 陽明","代號":"2609.TW","CID":"Shipping Cycle","Stage":"Cycle","fallback_price":78,"fallback":{"EPS":11,"BVPS":88,"ROE":12,"ROIC":10,"FCF_Margin":18,"Revenue_CAGR":-12,"EPS_Growth":-35,"Dividend":5,"Industry_Health":76}},
    {"公司":"2615 萬海","代號":"2615.TW","CID":"Shipping Cycle","Stage":"Cycle","fallback_price":95,"fallback":{"EPS":6,"BVPS":65,"ROE":9,"ROIC":8,"FCF_Margin":14,"Revenue_CAGR":-10,"EPS_Growth":-28,"Dividend":3,"Industry_Health":74}},

    # Telecom
    {"公司":"2412 中華電","代號":"2412.TW","CID":"Telecom Infrastructure","Stage":"Stable","fallback_price":141.5,"fallback":{"EPS":5.02,"BVPS":51.09,"ROE":9.99,"ROIC":10.59,"FCF_Margin":21.13,"Revenue_CAGR":2.86,"EPS_Growth":2.11,"Dividend":4.7,"Industry_Health":85}},
    {"公司":"3045 台灣大","代號":"3045.TW","CID":"Telecom Infrastructure","Stage":"Stable","fallback_price":120,"fallback":{"EPS":4.5,"BVPS":38,"ROE":12,"ROIC":9,"FCF_Margin":18,"Revenue_CAGR":3,"EPS_Growth":3,"Dividend":4.3,"Industry_Health":82}},
    {"公司":"4904 遠傳","代號":"4904.TW","CID":"Telecom Infrastructure","Stage":"Stable","fallback_price":90,"fallback":{"EPS":3.6,"BVPS":30,"ROE":12,"ROIC":9,"FCF_Margin":17,"Revenue_CAGR":3,"EPS_Growth":4,"Dividend":3.2,"Industry_Health":82}},
]

STRUCTURAL_CAL = {
    "AI Infrastructure":{"Base":1.25,"Growth":1.10,"ROIC":1.20,"CAP":1.15,"Confidence":"High","Status":"Stable"},
    "AI Platform":{"Base":1.35,"Growth":1.10,"ROIC":1.20,"CAP":1.15,"Confidence":"Medium","Status":"Observe"},
    "AI Server Platform":{"Base":1.10,"Growth":1.05,"ROIC":1.05,"CAP":1.05,"Confidence":"Medium","Status":"Observe"},
    "Advanced Materials":{"Base":1.75,"Growth":1.35,"ROIC":1.10,"CAP":1.20,"Confidence":"Low","Status":"Research Needed"},
    "Thermal Solution":{"Base":1.30,"Growth":1.20,"ROIC":1.15,"CAP":1.10,"Confidence":"High","Status":"Stable"},
    "Intelligent Automation":{"Base":1.20,"Growth":1.10,"ROIC":1.05,"CAP":1.05,"Confidence":"Medium","Status":"Observe"},
    "Memory Cycle":{"Base":1.00,"Growth":1.00,"ROIC":1.00,"CAP":1.00,"Confidence":"Medium","Status":"Cycle"},
    "Financial Franchise":{"Base":1.00,"Growth":1.00,"ROIC":1.00,"CAP":1.00,"Confidence":"High","Status":"Stable"},
    "Shipping Cycle":{"Base":1.00,"Growth":1.00,"ROIC":1.00,"CAP":1.00,"Confidence":"Medium","Status":"Cycle"},
    "Telecom Infrastructure":{"Base":1.00,"Growth":1.00,"ROIC":1.00,"CAP":1.00,"Confidence":"High","Status":"Stable"},
}

WEIGHTS = {
    "AI Infrastructure":{"DCF":0.25,"FCFF":0.20,"ROIC Premium":0.25,"CAP":0.30},
    "AI Platform":{"DCF":0.25,"FCFE":0.20,"ROIC Premium":0.25,"CAP":0.30},
    "AI Server Platform":{"DCF":0.25,"FCFF":0.25,"ROIC Premium":0.20,"CAP":0.30},
    "Advanced Materials":{"DCF":0.20,"FCFF":0.20,"ROIC Premium":0.25,"CAP":0.35},
    "Thermal Solution":{"DCF":0.25,"FCFF":0.20,"ROIC Premium":0.30,"CAP":0.25},
    "Intelligent Automation":{"DCF":0.25,"FCFF":0.20,"EVA":0.20,"ROIC Premium":0.20,"CAP":0.15},
    "Memory Cycle":{"Cycle PE":0.35,"EV/EBITDA":0.25,"Asset Value":0.30,"EBO":0.10},
    "Financial Franchise":{"PB Asset":0.30,"EBO":0.30,"Dividend":0.25,"EVA":0.15},
    "Shipping Cycle":{"Cycle PE":0.30,"EV/EBITDA":0.30,"Asset Value":0.30,"Dividend":0.10},
    "Telecom Infrastructure":{"DCF":0.25,"FCFE":0.15,"EBO":0.20,"Dividend":0.40},
}


# ============================================================
# V16.0 Growth Horizon Engine
# 市場不是只看TTM，而是依CID折現不同年限的未來成長。
# ============================================================

GROWTH_HORIZON = {
    "Financial Franchise": {"Years": 2, "Cap": 1.15, "Confidence": "High", "Mode": "Stable cash-flow"},
    "Telecom Infrastructure": {"Years": 2, "Cap": 1.20, "Confidence": "High", "Mode": "Dividend stability"},
    "Shipping Cycle": {"Years": 2, "Cap": 1.35, "Confidence": "Medium", "Mode": "Cycle earnings"},
    "AI Server Platform": {"Years": 3, "Cap": 1.60, "Confidence": "Medium", "Mode": "AI server growth"},
    "Thermal Solution": {"Years": 3, "Cap": 1.75, "Confidence": "Medium", "Mode": "Thermal growth"},
    "AI Platform": {"Years": 4, "Cap": 1.90, "Confidence": "Medium", "Mode": "AI edge/platform"},
    "AI Infrastructure": {"Years": 5, "Cap": 2.20, "Confidence": "Medium", "Mode": "AI compute infrastructure"},
    "Advanced Materials": {"Years": 5, "Cap": 2.50, "Confidence": "Low", "Mode": "AI material upgrade cycle"},
    "Intelligent Automation": {"Years": 6, "Cap": 2.80, "Confidence": "Low", "Mode": "AI robotics option value"},
    "Memory Cycle": {"Years": 4, "Cap": 3.00, "Confidence": "Low", "Mode": "Memory cycle forward pricing"},
}

def normalized_growth_rate(r):
    """
    Forward Growth Proxy：
    40% EPS Growth + 30% Revenue CAGR + 20% ROIC品質 + 10% FCF品質
    """
    eps_g = max(-10, min(60, r["EPS_Growth"])) / 100
    rev_g = max(-10, min(50, r["Revenue_CAGR"])) / 100
    roic_quality = max(0, min(40, r["ROIC"] - 8)) / 100
    fcf_quality = max(0, min(25, r["FCF_Margin"])) / 100
    g = eps_g * 0.40 + rev_g * 0.30 + roic_quality * 0.20 + fcf_quality * 0.10
    return max(-0.05, min(0.35, g))

def growth_horizon_multiplier(r):
    cfg = GROWTH_HORIZON[r["CID"]]
    g = normalized_growth_rate(r)
    years = cfg["Years"]
    raw = (1 + g) ** years
    capped = min(raw, cfg["Cap"])
    return round(capped, 3), round(g * 100, 1), years, cfg["Cap"], cfg["Confidence"], cfg["Mode"]

# ============================================================
# V17 Alpha Market Implied Growth Engine
# 先不做財測，只反推市場隱含成長。
# ============================================================

def historical_growth_alpha(r):
    rev = max(-50, min(80, r["Revenue_CAGR"]))
    eps = max(-80, min(100, r["EPS_Growth"]))
    return round(rev * 0.5 + eps * 0.5, 1)

def implied_growth_alpha(historical_growth, premium):
    if premium is None:
        return None
    return round(historical_growth * premium, 1)

def implied_growth_status(implied_growth):
    if implied_growth is None:
        return "N/A"
    if implied_growth < 0:
        return "Negative"
    if implied_growth < 10:
        return "Low"
    if implied_growth < 25:
        return "Normal"
    if implied_growth < 50:
        return "High"
    return "Extreme"


# ============================================================
# V20 中文化與雙軌估值輔助函式
# ============================================================

CID_ZH = {
    "AI Infrastructure": "AI基礎建設",
    "AI Platform": "AI平台",
    "AI Server Platform": "AI伺服器平台",
    "Advanced Materials": "高階材料",
    "Thermal Solution": "散熱解決方案",
    "Intelligent Automation": "AI自動化",
    "Memory Cycle": "記憶體循環",
    "Financial Franchise": "金融特許權",
    "Shipping Cycle": "航運循環",
    "Telecom Infrastructure": "電信基礎建設",
}

STATUS_ZH = {
    "Fair Zone": "合理區",
    "Mild Divergence": "輕度偏離",
    "Strong Divergence": "明顯偏離",
    "Extreme Divergence": "極端偏離",
    "N/A": "無資料",
}

ENGINE_MAP = {
    "AI Infrastructure": "未來價值引擎",
    "AI Platform": "未來價值引擎",
    "AI Server Platform": "未來價值引擎",
    "Advanced Materials": "未來價值引擎",
    "Thermal Solution": "未來價值引擎",
    "Intelligent Automation": "現況估值引擎",
    "Memory Cycle": "景氣循環引擎",
    "Financial Franchise": "現況估值引擎",
    "Shipping Cycle": "現況估值引擎",
    "Telecom Infrastructure": "現況估值引擎",
}

FUTURE_MULTIPLIER = {
    "AI Infrastructure": 1.45,
    "AI Platform": 1.35,
    "AI Server Platform": 1.25,
    "Advanced Materials": 1.55,
    "Thermal Solution": 1.35,
    "Intelligent Automation": 1.15,
    "Memory Cycle": 2.20,
    "Financial Franchise": 1.00,
    "Shipping Cycle": 1.05,
    "Telecom Infrastructure": 1.00,
}

CID_MATURITY = {
    "金融特許權": {"成熟度": "A級", "判讀": "暫時封版", "處理": "維持現況估值引擎"},
    "電信基礎建設": {"成熟度": "A級", "判讀": "暫時封版", "處理": "維持現況估值引擎"},
    "航運循環": {"成熟度": "A級", "判讀": "暫時封版", "處理": "維持現況估值引擎"},
    "AI自動化": {"成熟度": "B級", "判讀": "觀察", "處理": "先不大幅調整"},
    "AI伺服器平台": {"成熟度": "B級", "判讀": "觀察", "處理": "保留未來價值引擎"},
    "散熱解決方案": {"成熟度": "B級", "判讀": "觀察", "處理": "保留未來價值引擎"},
    "AI平台": {"成熟度": "C級", "判讀": "持續優化", "處理": "檢查AI成長模型"},
    "AI基礎建設": {"成熟度": "C級", "判讀": "持續優化", "處理": "檢查AI高成長模型"},
    "高階材料": {"成熟度": "C級", "判讀": "持續優化", "處理": "建議拆分AI高階材料"},
    "記憶體循環": {"成熟度": "D級", "判讀": "重新建模", "處理": "改用景氣循環/PB模型"},
}

# ============================================================
# V20.2 股價資料審查層
# 目的：先排除資料源/倍率錯誤，再討論估值模型。
# 注意：區間是審查用，不是估值判斷。
# ============================================================

PRICE_AUDIT_RULES = {
    "2408.TW": {"審查群組": "記憶體", "最低合理價": 10, "最高合理價": 120, "備註": "南亞科"},
    "2344.TW": {"審查群組": "記憶體", "最低合理價": 5, "最高合理價": 80, "備註": "華邦電"},
    "2337.TW": {"審查群組": "記憶體", "最低合理價": 5, "最高合理價": 80, "備註": "旺宏"},
    "2049.TW": {"審查群組": "AI自動化", "最低合理價": 80, "最高合理價": 800, "備註": "上銀"},
    "2359.TW": {"審查群組": "AI自動化", "最低合理價": 20, "最高合理價": 400, "備註": "所羅門"},
}

# 連線價格若出現10倍錯誤，先以人工覆核價格保護模型。
# 後續若改接 TWSE/TPEX 官方資料源，可移除此覆核表。
FORCE_PRICE_OVERRIDE = {
    "2408.TW": {"覆核價格": 40.70, "覆核原因": "記憶體連線價疑似10倍錯誤，改用人工覆核價"},
    "2344.TW": {"覆核價格": 18.35, "覆核原因": "記憶體連線價疑似10倍錯誤，改用人工覆核價"},
    "2337.TW": {"覆核價格": 14.55, "覆核原因": "記憶體連線價疑似10倍錯誤，改用人工覆核價"},
}

def audit_and_fix_price(symbol, price):
    rule = PRICE_AUDIT_RULES.get(symbol)
    if symbol in FORCE_PRICE_OVERRIDE:
        override = FORCE_PRICE_OVERRIDE[symbol]
        fixed_price = override["覆核價格"]
        raw = price
        note = f'{rule["審查群組"] if rule else "人工覆核"}｜{override["覆核原因"]}；原始連線價={raw}，覆核價={fixed_price}'
        return fixed_price, "人工覆核覆蓋", note, True

    if not rule:
        return price, "未列入審查", "", False

    low = rule["最低合理價"]
    high = rule["最高合理價"]
    group = rule["審查群組"]

    if price is None:
        return price, "缺少股價", f"{group}｜無法取得股價", False

    fixed_price = price
    auto_fixed = False
    note = ""

    # 常見錯誤：14.55 被顯示成 145.5，183.5 被顯示成 18.35 的反向也保留人工標記。
    if price > high and low <= price / 10 <= high:
        fixed_price = round(price / 10, 2)
        auto_fixed = True
        note = f"{group}｜疑似10倍股價錯誤，已由 {price} 修正為 {fixed_price}"
    elif price < low and low <= price * 10 <= high:
        fixed_price = round(price * 10, 2)
        auto_fixed = True
        note = f"{group}｜疑似0.1倍股價錯誤，已由 {price} 修正為 {fixed_price}"
    elif low <= price <= high:
        note = f"{group}｜股價通過審查"
    else:
        note = f"{group}｜股價超出審查區間，請人工確認：{price}"

    status = "已自動修正" if auto_fixed else ("通過" if low <= fixed_price <= high else "需人工確認")
    return fixed_price, status, note, auto_fixed

def future_value_multiplier(r):
    base = FUTURE_MULTIPLIER.get(r["CID"], 1.0)
    growth_quality = max(0, min(35, normalized_growth_rate(r) * 100)) / 100
    if ENGINE_MAP.get(r["CID"]) == "現況估值引擎":
        return round(base, 3)
    if ENGINE_MAP.get(r["CID"]) == "景氣循環引擎":
        cycle_boost = 1 + max(0, (r["Industry_Health"] - 70)) / 100
        return round(min(base * cycle_boost, 3.0), 3)
    return round(min(base * (1 + growth_quality * 0.35), 2.8), 3)

def price_position(current_price, current_fair, future_fair):
    if current_price <= current_fair:
        return "低於現況價值"
    if current_price <= future_fair:
        return "現況～未來合理區"
    return "高於未來價值"

def valuation_level(premium):
    """估值狀態：只判斷現價相對合理價是否高低估。"""
    if premium is None:
        return "無資料"
    if premium < 0.80:
        return "嚴重低估"
    if premium < 1.20:
        return "合理區間"
    if premium < 1.80:
        return "偏高估"
    if premium < 3.00:
        return "高估"
    return "極度高估"

def market_sentiment_v201(premium, implied_growth, cid):
    """市場情緒：獨立判斷市場是否正在交易未來成長或景氣循環。"""
    if premium is None:
        return "無資料"
    if cid == "Memory Cycle" and premium >= 1.5:
        return "景氣復甦預期"
    ig = 0 if implied_growth is None else implied_growth
    if premium < 0.85 and ig < 15:
        return "保守"
    if premium < 1.20:
        return "中性"
    if premium < 1.80 or ig < 30:
        return "樂觀"
    if premium < 3.00 or ig < 55:
        return "高度樂觀"
    return "狂熱"

def deviation_rate(price, fair):
    if fair and fair > 0:
        return round((price / fair - 1) * 100, 1)
    return None

def safe_num(x):
    try:
        if x is None or pd.isna(x): return None
        return float(x)
    except Exception:
        return None

def get_row(df, names):
    if df is None or df.empty: return None
    idx = {str(i).lower(): i for i in df.index}
    for n in names:
        if n.lower() in idx:
            s = df.loc[idx[n.lower()]]
            if isinstance(s, pd.Series):
                for v in s:
                    val = safe_num(v)
                    if val is not None: return val
            return safe_num(s)
    return None

def cagr(vals):
    vals = [safe_num(v) for v in vals if safe_num(v) is not None and safe_num(v) > 0]
    if len(vals) < 2: return None
    newest, oldest, years = vals[0], vals[-1], len(vals)-1
    if oldest <= 0: return None
    return (newest/oldest)**(1/years)-1

@st.cache_data(ttl=1800)
def fetch_market_and_financials(symbol, fallback_price, fallback):
    data = dict(fallback)
    meta = {"Price Source":"fallback", "Financial Source":"fallback", "Data Completeness":0, "Notes":[]}
    price = fallback_price
    if yf is None:
        meta["Notes"].append("yfinance未安裝，使用備援資料。")
        return price, data, meta
    try:
        t = yf.Ticker(symbol)
        fast = getattr(t, "fast_info", {}) or {}
        p = fast.get("last_price") or fast.get("lastPrice")
        if p is None:
            hist = t.history(period="5d")
            if not hist.empty: p = float(hist["Close"].dropna().iloc[-1])
        if p and p > 0:
            price = round(float(p), 2)
            meta["Price Source"] = f"yfinance:{symbol}"
        try: info = t.info or {}
        except Exception: info = {}
        income, balance, cashflow = t.financials, t.balance_sheet, t.cashflow
        shares = safe_num(info.get("sharesOutstanding")) or safe_num(fast.get("shares"))
        eps = safe_num(info.get("trailingEps")); bvps = safe_num(info.get("bookValue"))
        roe_info = safe_num(info.get("returnOnEquity")); div_rate = safe_num(info.get("dividendRate"))
        revenue = get_row(income, ["Total Revenue", "Operating Revenue"])
        net_income = get_row(income, ["Net Income", "Net Income Common Stockholders"])
        ebit = get_row(income, ["EBIT", "Operating Income"])
        tax_exp = get_row(income, ["Tax Provision", "Income Tax Expense"])
        pretax = get_row(income, ["Pretax Income", "Income Before Tax"])
        equity = get_row(balance, ["Stockholders Equity", "Total Equity Gross Minority Interest", "Common Stock Equity"])
        debt = get_row(balance, ["Total Debt", "Long Term Debt", "Short Long Term Debt Total"])
        cash = get_row(balance, ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"])
        ocf = get_row(cashflow, ["Operating Cash Flow", "Total Cash From Operating Activities"])
        capex = get_row(cashflow, ["Capital Expenditure", "Capital Expenditures"])
        rev_cagr = eps_growth = None
        if income is not None and not income.empty:
            for nm in ["Total Revenue", "Operating Revenue"]:
                if nm in income.index:
                    rev_cagr = cagr(income.loc[nm].values); break
            for nm in ["Net Income", "Net Income Common Stockholders"]:
                if nm in income.index:
                    eps_growth = cagr(income.loc[nm].values); break
        if eps is None and net_income is not None and shares and shares > 0: eps = net_income/shares
        if bvps is None and equity is not None and shares and shares > 0: bvps = equity/shares
        roe = None
        if roe_info is not None: roe = roe_info*100 if abs(roe_info)<1 else roe_info
        elif net_income is not None and equity and equity > 0: roe = net_income/equity*100
        tax_rate = 0.2
        if tax_exp is not None and pretax and pretax > 0: tax_rate = max(0.05, min(0.35, tax_exp/pretax))
        invested = equity + (debt or 0) - (cash or 0) if equity is not None else None
        roic = ebit*(1-tax_rate)/invested*100 if ebit is not None and invested and invested > 0 else None
        fcf_margin = (ocf+capex)/revenue*100 if ocf is not None and capex is not None and revenue and revenue > 0 else None
        extracted = {"EPS":eps, "BVPS":bvps, "ROE":roe, "ROIC":roic, "FCF_Margin":fcf_margin, "Revenue_CAGR":rev_cagr*100 if rev_cagr is not None else None, "EPS_Growth":eps_growth*100 if eps_growth is not None else None, "Dividend":div_rate}
        real_count = 0
        for k,v in extracted.items():
            if v is not None and np.isfinite(v):
                data[k] = round(float(v), 2); real_count += 1
        meta["Data Completeness"] = round(real_count/len(extracted)*100, 1)
        meta["Financial Source"] = "yfinance + fallback" if real_count < len(extracted) else "yfinance"
        missing = [k for k,v in extracted.items() if v is None or not np.isfinite(v)]
        if missing: meta["Notes"].append("Fallback欄位：" + "、".join(missing))
    except Exception as e:
        meta["Notes"].append(f"抓取失敗：{e}")
    return price, data, meta

def dcf(r):
    g=max(-5,min(25,r["EPS_Growth"])); q=1+max(0,r["FCF_Margin"])*.008; pe=14+g*.35
    if r["Stage"]=="Leader": pe+=6
    elif r["Stage"]=="Growth": pe+=4
    elif r["Stage"]=="Stable": pe+=2
    return max(0,r["EPS"]*pe*q)
def fcff(r): return max(0,r["EPS"]*(13+max(-5,min(20,r["Revenue_CAGR"]))*0.25+max(0,r["FCF_Margin"])*0.18))
def fcfe(r): return max(0,r["EPS"]*(11+max(0,r["ROE"]-8)*0.35)*(1+min(.25,max(0,r["Dividend"]/max(r["EPS"],.01))*0.10)))
def eva(r): return max(0,r["BVPS"]*(1+(r["ROE"]-(10.5 if r["Stage"]=="Growth" else 9))*0.08))
def ebo(r): return max(0,r["BVPS"]+r["BVPS"]*((r["ROE"]-9.5)/100)*5+r["EPS"]*max(0,max(-3,min(15,r["EPS_Growth"])))*0.25)
def roic_value(r): return max(0,r["EPS"]*(16+max(0,r["ROIC"]-10)*0.30+max(0,r["FCF_Margin"])*0.12))
def cap_value(r):
    y=10 if r["Stage"]=="Leader" else 8 if r["Stage"]=="Growth" else 6
    if "AI" in r["CID"]: y+=2
    return max(0,r["EPS"]*(14+y*1.6))
def cycle_pe(r): return max(0,r["EPS"]*(7 if r["CID"]=="Shipping Cycle" else 18 if r["CID"]=="Memory Cycle" else 14)*(0.80+r["Industry_Health"]/100*0.45))
def ev_ebitda(r): return max(0,r["EPS"]*(6.5 if r["CID"]=="Shipping Cycle" else 9 if r["CID"]=="Memory Cycle" else 12)*1.12)
def asset_value(r): return max(0,r["BVPS"]*(.85 if r["CID"]=="Shipping Cycle" else 1.5 if r["CID"]=="Memory Cycle" else 1.7 if r["CID"]=="Financial Franchise" else 1))
def div_value(r):
    y=.038 if r["CID"]=="Telecom Infrastructure" else .045 if r["CID"]=="Financial Franchise" else .07 if r["CID"]=="Shipping Cycle" else .05
    return r["Dividend"]/y if r["Dividend"] > 0 else 0

def components(r):
    raw = {"DCF":dcf(r),"FCFF":fcff(r),"FCFE":fcfe(r),"EVA":eva(r),"EBO":ebo(r),"ROIC Premium":roic_value(r),"CAP":cap_value(r),"Cycle PE":cycle_pe(r),"EV/EBITDA":ev_ebitda(r),"Asset Value":asset_value(r),"PB Asset":asset_value(r),"Dividend":div_value(r)}
    cal = STRUCTURAL_CAL[r["CID"]]; out = {}
    for k,v in raw.items():
        f=cal["Base"]
        if k in ["DCF","FCFF","FCFE"]: f*=cal["Growth"]
        if k=="ROIC Premium": f*=cal["ROIC"]
        if k=="CAP": f*=cal["CAP"]
        out[k]=v*f
    return out

def valuation(r):
    comps=components(r); weights=WEIGHTS[r["CID"]]; base=sum(comps[k]*w for k,w in weights.items())
    if r["Stage"]=="Cycle": bear,bull=base*.70,base*1.45
    elif r["Stage"]=="Growth": bear,bull=base*.78,base*1.38
    elif r["Stage"]=="Leader": bear,bull=base*.82,base*1.30
    else: bear,bull=base*.85,base*1.18
    return round(bear,2),round(base,2),round(bull,2),comps

def gap_status(price,value):
    if not value or value<=0: return None,"N/A"
    gap=(price/value-1)*100; ag=abs(gap)
    status="Fair Zone" if ag<=15 else "Mild Divergence" if ag<=30 else "Strong Divergence" if ag<=50 else "Extreme Divergence"
    return round(gap,1),status

rows=[]; comp_rows=[]
progress = st.sidebar.empty()
for i,item in enumerate(BENCHMARK, start=1):
    progress.caption(f"載入資料 {i}/{len(BENCHMARK)}：{item['公司']}")
    raw_price, fin, meta = fetch_market_and_financials(item["代號"], item["fallback_price"], item["fallback"])
    price, price_audit_status, price_audit_note, price_auto_fixed = audit_and_fix_price(item["代號"], raw_price)
    r = {**item, **fin, "現價":price}
    bear, fair, bull, comps = valuation(r)
    gap, stat = gap_status(price, fair)
    ghe_mult, forward_g, horizon_years, horizon_cap, ghe_conf, ghe_mode = growth_horizon_multiplier(r)
    exp_bear = round(bear * ghe_mult, 2)
    exp_fair = round(fair * ghe_mult, 2)
    exp_bull = round(bull * ghe_mult, 2)
    exp_gap, exp_stat = gap_status(price, exp_fair)
    fef = round(price / fair, 3) if fair and fair > 0 else None
    historical_g = historical_growth_alpha(r)
    implied_g = implied_growth_alpha(historical_g, fef)
    implied_status = implied_growth_status(implied_g)
    future_mult = future_value_multiplier(r)
    future_bear = round(bear * future_mult, 2)
    future_fair = round(fair * future_mult, 2)
    future_bull = round(bull * future_mult, 2)
    future_gap, future_status = gap_status(price, future_fair)
    cid_zh = CID_ZH.get(item["CID"], item["CID"])
    status_zh = STATUS_ZH.get(stat, stat)
    engine_type = ENGINE_MAP.get(item["CID"], "現況估值引擎")
    position = price_position(price, fair, future_fair)
    valuation_status_new = valuation_level(fef)
    sentiment = market_sentiment_v201(fef, implied_g, item["CID"])
    deviation = deviation_rate(price, fair)
    future_deviation = deviation_rate(price, future_fair)
    cal = STRUCTURAL_CAL[item["CID"]]
    rows.append({"公司":item["公司"],"代號":item["代號"],"產業定位":cid_zh,"CID":item["CID"],"Stage":item["Stage"],"現價":price,"原始股價":raw_price,"股價審查":price_audit_status,"股價審查備註":price_audit_note,"股價自動修正":price_auto_fixed,
                 "現況保守價":bear,"現況合理價":fair,"現況樂觀價":bull,"現況偏離%":gap,"估值狀態":status_zh,
                 "未來倍率":future_mult,"未來保守價":future_bear,"未來合理價":future_fair,"未來樂觀價":future_bull,"未來偏離%":future_gap,
                 "現價位置":position,"估值狀態V20.1":valuation_status_new,"市場情緒":sentiment,"使用引擎":engine_type,
                 "市場溢價倍數":fef,"歷史成長率%":historical_g,"市場隱含成長%":implied_g,"隱含成長狀態":implied_status,
                 "Bear":bear,"Fair Value":fair,"Bull":bull,"Gap%":gap,"Status":stat,
                 "Premium":fef,"Historical Growth%":historical_g,"Implied Growth%":implied_g,"Implied Growth Status":implied_status,
                 "GHE Multiplier":ghe_mult,"Forward Growth Proxy%":forward_g,"Horizon Years":horizon_years,"Horizon Cap":horizon_cap,
                 "Expected Bear":exp_bear,"Expected Fair":exp_fair,"Expected Bull":exp_bull,"Expected Gap%":exp_gap,"Expected Status":exp_stat,
                 "Market FEF":fef,"GHE Confidence":ghe_conf,"GHE Mode":ghe_mode,
                 "EPS":r["EPS"],"BVPS":r["BVPS"],"ROE":r["ROE"],"ROIC":r["ROIC"],"FCF_Margin":r["FCF_Margin"],"Revenue_CAGR":r["Revenue_CAGR"],"EPS_Growth":r["EPS_Growth"],"Dividend":r["Dividend"],
                 "Data Completeness":meta["Data Completeness"],"Price Source":meta["Price Source"],"Financial Source":meta["Financial Source"],
                 "Calibration Confidence":cal["Confidence"],"Calibration Status":cal["Status"],"Notes":"；".join(meta["Notes"])})
    for k,v in comps.items(): comp_rows.append({"公司":item["公司"],"CID":item["CID"],"模型":k,"模型值":round(v,2),"是否使用":"Yes" if k in WEIGHTS[item["CID"]] else "No","權重":WEIGHTS[item["CID"]].get(k,0)})
progress.empty()

df=pd.DataFrame(rows); component_df=pd.DataFrame(comp_rows)
cid_summary=df.groupby("CID").agg(公司數=("公司","count"),平均Gap=("Gap%","mean"),中位數Gap=("Gap%","median"),平均絕對Gap=("Gap%",lambda x:x.abs().mean()),Expected平均Gap=("Expected Gap%","mean"),Expected平均絕對Gap=("Expected Gap%",lambda x:x.abs().mean()),FEF中位數=("Market FEF","median"),Premium平均=("Premium","mean"),HistoricalGrowth平均=("Historical Growth%","mean"),ImpliedGrowth平均=("Implied Growth%","mean"),ImpliedGrowth中位數=("Implied Growth%","median"),GHE倍率中位數=("GHE Multiplier","median"),Gap標準差=("Gap%","std"),FairZone數=("Status",lambda x:int((x=="Fair Zone").sum())),ExpectedFairZone數=("Expected Status",lambda x:int((x=="Fair Zone").sum())),平均資料完整度=("Data Completeness","mean")).reset_index().round(2)
def cid_grade(row):
    if row["公司數"] < 3: return "待補樣本"
    if row["平均絕對Gap"] <= 20 and row["Gap標準差"] <= 25: return "A級：可暫時凍結"
    if row["平均絕對Gap"] <= 40: return "B級：觀察"
    return "C級：需研究"
cid_summary["CID成熟度"] = cid_summary.apply(cid_grade, axis=1)

sector_summary = df.groupby(["產業定位","使用引擎"]).agg(
    公司數=("公司","count"),
    平均現價=("現價","mean"),
    平均現況合理價=("現況合理價","mean"),
    平均未來合理價=("未來合理價","mean"),
    平均市場溢價=("市場溢價倍數","mean"),
    平均現況偏離=("現況偏離%","mean"),
    平均未來偏離=("未來偏離%","mean"),
).reset_index().round(2)

hot_rank = sector_summary.sort_values("平均市場溢價", ascending=False).reset_index(drop=True)
hot_rank.insert(0, "排名", hot_rank.index + 1)

outlier_rank = df.copy()
outlier_rank["偏離絕對值"] = outlier_rank["現況偏離%"].abs()
outlier_rank = outlier_rank.sort_values("偏離絕對值", ascending=False).reset_index(drop=True)
outlier_rank.insert(0, "排名", outlier_rank.index + 1)

summary=pd.DataFrame([
    {"項目":"樣本公司數","結果":len(df)},
    {"項目":"CID數","結果":df["CID"].nunique()},
    {"項目":"Intrinsic Fair Zone公司數","結果":int((df["Status"]=="Fair Zone").sum())},
    {"項目":"Expected Fair Zone公司數","結果":int((df["Expected Status"]=="Fair Zone").sum())},
    {"項目":"Intrinsic平均絕對Gap","結果":f"{round(df['Gap%'].abs().mean(),1)}%"},
    {"項目":"Expected平均絕對Gap","結果":f"{round(df['Expected Gap%'].abs().mean(),1)}%"},
    {"項目":"平均Premium","結果":round(df["Premium"].mean(),2)},
    {"項目":"平均Historical Growth","結果":f"{round(df['Historical Growth%'].mean(),1)}%"},
    {"項目":"平均Implied Growth","結果":f"{round(df['Implied Growth%'].mean(),1)}%"},
    {"項目":"平均資料完整度","結果":f"{round(df['Data Completeness'].mean(),1)}%"},
    {"項目":"C級CID數","結果":int((cid_summary["CID成熟度"].str.startswith("C級")).sum())},
])

st.sidebar.header("V20.1 控制台")
page=st.sidebar.radio("功能",["類股估值總覽","股價審查中心","類股成熟度中心","類股熱度排行榜","異常值排行榜","雙軌估值","市場情緒儀表板","個股明細","模型中心","原始Benchmark","Export JSON"])
selected=st.sidebar.selectbox("選擇公司",df["公司"].tolist())
st.sidebar.divider(); st.sidebar.metric("樣本公司",len(df)); st.sidebar.metric("Intrinsic Fair",int((df["Status"]=="Fair Zone").sum())); st.sidebar.metric("Expected Fair",int((df["Expected Status"]=="Fair Zone").sum())); st.sidebar.metric("平均溢價",round(df["市場溢價倍數"].mean(),2)); st.sidebar.metric("極度高估",int((df["估值狀態V20.1"]=="極度高估").sum()))

if page=="類股估值總覽":
    st.header("一、類股估值總覽")
    st.write("依類股分類呈現：現價、現況合理價、未來合理價與市場情緒。")
    for sector in df["產業定位"].drop_duplicates():
        sdf = df[df["產業定位"] == sector]
        avg_premium = round(sdf["市場溢價倍數"].mean(), 2)
        st.subheader(f"{sector}｜平均溢價 {avg_premium}")
        st.dataframe(
            sdf[["公司","代號","現價","現況保守價","現況合理價","現況樂觀價","未來合理價","估值狀態V20.1","市場情緒","現價位置","使用引擎"]],
            use_container_width=True
        )

elif page=="股價審查中心":
    st.header("二、股價審查中心")
    st.write("記憶體族群已改用人工覆核價格；上銀、所羅門保留審查區間，若超出區間再標記人工確認。")
    audit_df = df[df["代號"].isin(list(PRICE_AUDIT_RULES.keys()))][
        ["公司","代號","產業定位","原始股價","現價","股價審查","股價自動修正","股價審查備註","現況合理價","未來合理價","估值狀態V20.1","Price Source"]
    ].copy()
    st.dataframe(audit_df, use_container_width=True)

    st.subheader("審查規則")
    rule_df = pd.DataFrame([
        {"代號": k, **v, "人工覆核價格": FORCE_PRICE_OVERRIDE.get(k, {}).get("覆核價格", "")} for k, v in PRICE_AUDIT_RULES.items()
    ])
    st.dataframe(rule_df, use_container_width=True)

    st.subheader("需要人工確認")
    st.dataframe(audit_df[audit_df["股價審查"].isin(["需人工確認","已自動修正","人工覆核覆蓋"])], use_container_width=True)

elif page=="類股成熟度中心":
    st.header("二、類股成熟度中心")
    st.write("A級暫時封版；B級觀察；C級持續優化；D級重新建模。")
    maturity_df = pd.DataFrame([
        {"產業定位": k, **v} for k, v in CID_MATURITY.items()
    ])
    st.dataframe(maturity_df, use_container_width=True)
    st.subheader("需優先研究類股")
    st.dataframe(
        maturity_df[maturity_df["成熟度"].isin(["C級","D級"])],
        use_container_width=True
    )

elif page=="類股熱度排行榜":
    st.header("二、類股熱度排行榜")
    st.write("以平均市場溢價倍數觀察市場目前追捧的類股。")
    st.dataframe(hot_rank[["排名","產業定位","使用引擎","公司數","平均市場溢價","平均現況偏離","平均未來偏離"]], use_container_width=True)
    st.bar_chart(hot_rank.set_index("產業定位")["平均市場溢價"])

elif page=="異常值排行榜":
    st.header("三、異常值排行榜")
    st.write("列出目前價格偏離現況合理價最多的公司，作為後續模型修正與研究重點。")
    st.dataframe(
        outlier_rank[["排名","公司","代號","產業定位","現價","現況合理價","未來合理價","現況偏離%","未來偏離%","估值狀態V20.1","市場情緒","使用引擎"]].head(15),
        use_container_width=True
    )
    st.bar_chart(outlier_rank.head(15).set_index("公司")["偏離絕對值"])

elif page=="雙軌估值":
    st.header("四、雙軌估值")
    st.write("同時比較市場現價、現況價值與未來價值。")
    st.dataframe(
        df[["公司","產業定位","現價","現況保守價","現況合理價","現況樂觀價","未來保守價","未來合理價","未來樂觀價","現價位置"]],
        use_container_width=True
    )
    st.bar_chart(df.set_index("公司")[["現況合理價","未來合理價","現價"]])

elif page=="市場情緒儀表板":
    st.header("五、市場情緒儀表板")
    st.write("用市場溢價倍數與現價位置判讀市場情緒。")
    sentiment_table = df.groupby(["產業定位","市場情緒"]).size().reset_index(name="公司數")
    valuation_table = df.groupby(["產業定位","估值狀態V20.1"]).size().reset_index(name="公司數")
    st.subheader("市場情緒分布")
    st.dataframe(sentiment_table, use_container_width=True)
    st.subheader("估值狀態分布")
    st.dataframe(valuation_table, use_container_width=True)
    st.subheader("類股摘要")
    st.dataframe(sector_summary, use_container_width=True)

elif page=="個股明細":
    st.header("六、個股明細")
    row=df[df["公司"]==selected].iloc[0]
    comps=component_df[component_df["公司"]==selected]
    c1,c2,c3,c4=st.columns(4)
    c1.metric("現價",f"{row['現價']:,.2f}")
    c2.metric("現況合理價",f"{row['現況合理價']:,.2f}",f"{row['現況偏離%']}%")
    c3.metric("未來合理價",f"{row['未來合理價']:,.2f}",f"{row['未來偏離%']}%")
    c4.metric("估值狀態",row["估值狀態V20.1"])
    st.dataframe(pd.DataFrame([
        {"項目":"產業定位","內容":row["產業定位"]},
        {"項目":"使用引擎","內容":row["使用引擎"]},
        {"項目":"現價位置","內容":row["現價位置"]},{"項目":"估值狀態","內容":row["估值狀態V20.1"]},{"項目":"市場情緒","內容":row["市場情緒"]},
        {"項目":"市場溢價倍數","內容":row["市場溢價倍數"]},
        {"項目":"歷史成長率%","內容":row["歷史成長率%"]},
        {"項目":"市場隱含成長%","內容":row["市場隱含成長%"]},
        {"項目":"資料完整度","內容":row["Data Completeness"]},
        {"項目":"原始股價","內容":row["原始股價"]},{"項目":"股價審查","內容":row["股價審查"]},{"項目":"股價審查備註","內容":row["股價審查備註"]},{"項目":"股價來源","內容":row["Price Source"]},
        {"項目":"財務來源","內容":row["Financial Source"]},
        {"項目":"備註","內容":row["Notes"]},
    ]), use_container_width=True)
    st.subheader("使用模型")
    used=comps[comps["是否使用"]=="Yes"]
    st.dataframe(used,use_container_width=True)
    st.bar_chart(used.set_index("模型")["模型值"])

elif page=="模型中心":
    st.header("七、模型中心")
    st.write("V20 將模型分成三種：現況估值、未來價值、景氣循環。")
    model_df = pd.DataFrame([
        {"模型":"現況估值引擎","適用類股":"金融特許權、電信基礎建設、航運循環、AI自動化","目的":"回答公司目前值多少"},
        {"模型":"未來價值引擎","適用類股":"AI基礎建設、AI平台、AI伺服器平台、高階材料、散熱解決方案","目的":"回答未來成長實現後值多少"},
        {"模型":"景氣循環引擎","適用類股":"記憶體循環","目的":"避免單年EPS造成估值崩潰"},
    ])
    st.dataframe(model_df, use_container_width=True)
    st.subheader("結構校正資料")
    st.dataframe(pd.DataFrame([{"CID":cid,"中文類股":CID_ZH.get(cid,cid),**vals} for cid,vals in STRUCTURAL_CAL.items()]),use_container_width=True)

elif page=="原始Benchmark":
    st.header("八、原始Benchmark")
    st.write("保留原本 Benchmark 與 MIGE 欄位，方便回溯驗證。")
    st.dataframe(df, use_container_width=True)

elif page=="Export JSON":
    st.header("九、Export JSON")
    export={"version":"V20.3 Manual Price Override Layer","updated_at":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"purpose":"Force manual reviewed prices for memory stocks when yfinance prices show 10x errors; keep audit layer for Hiwin and Solomon.","valuation_results":df.to_dict(orient="records"),"cid_summary":cid_summary.to_dict(orient="records"),"components":component_df.to_dict(orient="records"),"structural_calibration":STRUCTURAL_CAL,"growth_horizon":GROWTH_HORIZON,"summary":summary.to_dict(orient="records"),"price_audit_rules":PRICE_AUDIT_RULES,"force_price_override":FORCE_PRICE_OVERRIDE,"sector_summary":sector_summary.to_dict(orient="records"),"hot_rank":hot_rank.to_dict(orient="records"),"outlier_rank":outlier_rank.to_dict(orient="records")}
    st.code(json.dumps(export,ensure_ascii=False,indent=2),language="json")
