
import json
from datetime import datetime

import pandas as pd
import streamlit as st

try:
    import yfinance as yf
except Exception:
    yf = None


st.set_page_config(
    page_title="Enterprise Valuation Lab V14.0",
    page_icon="🏛️",
    layout="wide",
)

st.title("🏛️ Enterprise Valuation Lab")
st.subheader("V14.0｜Valuation Core Prototype 估值核心原型")
st.info(
    "V14.0 開始把 CID → Business Stage → Model Selector → Valuation Core 串起來。"
    "本版目標不是追求最終精準股價，而是讓不同公司身份能自動選模型並產生 Bear / Base / Bull 合理價區間。"
)


@st.cache_data(ttl=900)
def fetch_price(symbol, fallback=None):
    candidates = [symbol]
    if symbol.endswith(".TW"):
        candidates.append(symbol.split(".")[0] + ".TWO")
    if symbol.endswith(".TWO"):
        candidates.append(symbol.split(".")[0] + ".TW")

    if yf is not None:
        for ticker in candidates:
            try:
                t = yf.Ticker(ticker)
                fast = getattr(t, "fast_info", {}) or {}
                price = fast.get("last_price") or fast.get("lastPrice")
                if price is None:
                    hist = t.history(period="5d", interval="1d")
                    if not hist.empty:
                        price = float(hist["Close"].dropna().iloc[-1])
                if price and price > 0:
                    return round(float(price), 2), f"yfinance：{ticker}"
            except Exception:
                pass
    return fallback, "fallback 備援價"


# ============================================================
# V14 Core Sample：10家公司，10種身份/模型
# 注意：此處財務因子為原型測試用，正式版需接真實財報資料庫。
# ============================================================

companies = [
    {
        "公司": "2330 台積電", "代號": "2330.TW", "fallback": 2370,
        "CID": "AI Infrastructure", "Stage": "Leader",
        "Revenue_CAGR": 18, "EPS": 85, "EPS_Growth": 22, "ROIC": 32, "ROE": 31, "FCF_Margin": 22,
        "BVPS": 220, "Dividend": 15, "Cycle": 55, "Industry_Health": 92,
        "Base_PE": 27, "Base_PB": 7.5, "EV_EBITDA": 18
    },
    {
        "公司": "2454 聯發科", "代號": "2454.TW", "fallback": 4335,
        "CID": "AI Platform", "Stage": "Leader",
        "Revenue_CAGR": 15, "EPS": 125, "EPS_Growth": 18, "ROIC": 24, "ROE": 25, "FCF_Margin": 20,
        "BVPS": 520, "Dividend": 75, "Cycle": 50, "Industry_Health": 88,
        "Base_PE": 28, "Base_PB": 5.5, "EV_EBITDA": 17
    },
    {
        "公司": "2383 台光電", "代號": "2383.TW", "fallback": 5535,
        "CID": "Advanced Materials", "Stage": "Growth",
        "Revenue_CAGR": 28, "EPS": 135, "EPS_Growth": 35, "ROIC": 30, "ROE": 32, "FCF_Margin": 18,
        "BVPS": 430, "Dividend": 40, "Cycle": 58, "Industry_Health": 90,
        "Base_PE": 36, "Base_PB": 9.5, "EV_EBITDA": 22
    },
    {
        "公司": "2382 廣達", "代號": "2382.TW", "fallback": 310,
        "CID": "AI Server Platform", "Stage": "Growth",
        "Revenue_CAGR": 22, "EPS": 18, "EPS_Growth": 25, "ROIC": 18, "ROE": 22, "FCF_Margin": 8,
        "BVPS": 80, "Dividend": 6, "Cycle": 65, "Industry_Health": 88,
        "Base_PE": 18, "Base_PB": 3.6, "EV_EBITDA": 12
    },
    {
        "公司": "3017 奇鋐", "代號": "3017.TW", "fallback": 980,
        "CID": "Thermal Solution", "Stage": "Growth",
        "Revenue_CAGR": 25, "EPS": 45, "EPS_Growth": 30, "ROIC": 24, "ROE": 28, "FCF_Margin": 13,
        "BVPS": 150, "Dividend": 12, "Cycle": 58, "Industry_Health": 86,
        "Base_PE": 24, "Base_PB": 6.2, "EV_EBITDA": 16
    },
    {
        "公司": "6215 和椿", "代號": "6215.TWO", "fallback": 108,
        "CID": "Intelligent Automation", "Stage": "Growth",
        "Revenue_CAGR": 18, "EPS": 4.2, "EPS_Growth": 20, "ROIC": 14, "ROE": 12, "FCF_Margin": 8,
        "BVPS": 32, "Dividend": 1.2, "Cycle": 62, "Industry_Health": 78,
        "Base_PE": 24, "Base_PB": 3.0, "EV_EBITDA": 13
    },
    {
        "公司": "2408 南亞科", "代號": "2408.TW", "fallback": 95,
        "CID": "Memory Cycle", "Stage": "Cycle",
        "Revenue_CAGR": 35, "EPS": 3.8, "EPS_Growth": 45, "ROIC": 7, "ROE": 8, "FCF_Margin": -3,
        "BVPS": 58, "Dividend": 0.5, "Cycle": 92, "Industry_Health": 82,
        "Base_PE": 22, "Base_PB": 1.8, "EV_EBITDA": 9
    },
    {
        "公司": "2881 富邦金", "代號": "2881.TW", "fallback": 128.5,
        "CID": "Financial Franchise", "Stage": "Stable",
        "Revenue_CAGR": 8, "EPS": 9.5, "EPS_Growth": 12, "ROIC": 10, "ROE": 14, "FCF_Margin": 8,
        "BVPS": 85, "Dividend": 5.0, "Cycle": 35, "Industry_Health": 80,
        "Base_PE": 13, "Base_PB": 1.45, "EV_EBITDA": 0
    },
    {
        "公司": "2603 長榮", "代號": "2603.TW", "fallback": 230,
        "CID": "Shipping Cycle", "Stage": "Cycle",
        "Revenue_CAGR": -8, "EPS": 18, "EPS_Growth": -15, "ROIC": 18, "ROE": 20, "FCF_Margin": 15,
        "BVPS": 175, "Dividend": 12, "Cycle": 95, "Industry_Health": 78,
        "Base_PE": 8, "Base_PB": 1.25, "EV_EBITDA": 6
    },
    {
        "公司": "2412 中華電", "代號": "2412.TW", "fallback": 130,
        "CID": "Telecom Infrastructure", "Stage": "Stable",
        "Revenue_CAGR": 3, "EPS": 4.8, "EPS_Growth": 4, "ROIC": 10, "ROE": 10, "FCF_Margin": 16,
        "BVPS": 42, "Dividend": 4.7, "Cycle": 25, "Industry_Health": 85,
        "Base_PE": 27, "Base_PB": 3.1, "EV_EBITDA": 12
    },
]


# ============================================================
# Valuation Model Functions
# ============================================================

def industry_multiplier(health):
    """
    產業健康度倍率：
    50 = 1.00
    100 = 1.25
    0 = 0.75
    """
    return round(0.75 + (health / 100) * 0.50, 3)


def dcf_value(eps, growth, quality_factor=1.0):
    # 原型簡化DCF：EPS × 合理PE，成長越高、品質越高，倍數越高
    pe = 12 + min(20, growth * 0.45) + quality_factor * 4
    return eps * pe


def roic_premium_value(eps, roic, fcf_margin):
    premium = 1 + max(0, roic - 10) * 0.025 + max(0, fcf_margin) * 0.01
    return eps * 18 * premium


def cap_premium_value(eps, stage, cid):
    base = 18
    if stage == "Leader":
        base += 8
    if "AI" in cid:
        base += 5
    if "Infrastructure" in cid:
        base += 3
    return eps * base


def vdf_premium_value(eps, growth, industry_health):
    pe = 16 + min(22, growth * 0.55) + (industry_health - 50) * 0.08
    return eps * pe


def pb_roe_value(bvps, roe):
    # PB 約略由 ROE 決定
    pb = 0.7 + max(0, roe) * 0.055
    return bvps * pb


def residual_income_value(bvps, roe, cost_of_equity=9):
    spread = max(-5, roe - cost_of_equity)
    return bvps * (1 + spread * 0.08)


def dividend_yield_value(dividend, target_yield):
    if target_yield <= 0:
        return 0
    return dividend / target_yield


def cycle_pe_value(eps, cycle_score, base_pe):
    cycle_adj = 0.75 + cycle_score / 100 * 0.55
    return eps * base_pe * cycle_adj


def ev_ebitda_proxy(eps, ev_ebitda):
    # 原型版用 EPS × EV/EBITDA代理，正式版需用 EBITDA / 股本
    return eps * ev_ebitda * 1.15


def asset_value(bvps, stage, cid):
    mult = 1.0
    if stage == "Cycle":
        mult = 1.15
    if "Shipping" in cid:
        mult += 0.15
    if "Memory" in cid:
        mult += 0.05
    return bvps * mult


def model_selector(cid, stage):
    if cid == "AI Infrastructure":
        return {
            "主模型": "DCF + ROIC + CAP",
            "權重": {"DCF": 0.50, "ROIC Premium": 0.30, "CAP Premium": 0.20},
        }
    if cid in ["AI Platform", "Advanced Materials", "AI Server Platform", "Thermal Solution"]:
        return {
            "主模型": "VDF + DCF + ROIC",
            "權重": {"VDF Premium": 0.45, "DCF": 0.35, "ROIC Premium": 0.20},
        }
    if cid == "Intelligent Automation":
        return {
            "主模型": "Automation Blend",
            "權重": {"VDF Premium": 0.40, "DCF": 0.35, "PB-ROE": 0.25},
        }
    if cid == "Memory Cycle":
        return {
            "主模型": "Cycle PE + PB + Asset",
            "權重": {"Cycle PE": 0.45, "PB-ROE": 0.25, "Asset Value": 0.30},
        }
    if cid == "Financial Franchise":
        return {
            "主模型": "PB-ROE + RI + Dividend",
            "權重": {"PB-ROE": 0.50, "Residual Income": 0.30, "Dividend Yield": 0.20},
        }
    if cid == "Shipping Cycle":
        return {
            "主模型": "Cycle PE + EV/EBITDA + Asset",
            "權重": {"Cycle PE": 0.40, "EV/EBITDA": 0.40, "Asset Value": 0.20},
        }
    if cid == "Telecom Infrastructure":
        return {
            "主模型": "DCF + Dividend + RI",
            "權重": {"DCF": 0.40, "Dividend Yield": 0.35, "Residual Income": 0.25},
        }
    return {
        "主模型": "Hybrid",
        "權重": {"DCF": 0.50, "PB-ROE": 0.30, "VDF Premium": 0.20},
    }


def valuation_components(row):
    eps = row["EPS"]
    growth = row["EPS_Growth"]
    roic = row["ROIC"]
    roe = row["ROE"]
    fcf = row["FCF_Margin"]
    bvps = row["BVPS"]
    div = row["Dividend"]
    cycle = row["Cycle"]
    base_pe = row["Base_PE"]
    ev_ebitda = row["EV_EBITDA"]
    cid = row["CID"]
    stage = row["Stage"]
    health = row["Industry_Health"]

    comps = {
        "DCF": dcf_value(eps, growth, 1.0 if stage in ["Growth", "Leader"] else 0.4),
        "ROIC Premium": roic_premium_value(eps, roic, fcf),
        "CAP Premium": cap_premium_value(eps, stage, cid),
        "VDF Premium": vdf_premium_value(eps, growth, health),
        "PB-ROE": pb_roe_value(bvps, roe),
        "Residual Income": residual_income_value(bvps, roe),
        "Dividend Yield": dividend_yield_value(div, 0.04 if stage == "Stable" else 0.05),
        "Cycle PE": cycle_pe_value(eps, cycle, base_pe),
        "EV/EBITDA": ev_ebitda_proxy(eps, ev_ebitda),
        "Asset Value": asset_value(bvps, stage, cid),
    }
    return {k: round(v, 2) for k, v in comps.items()}


def final_valuation(row):
    selector = model_selector(row["CID"], row["Stage"])
    comps = valuation_components(row)
    weights = selector["權重"]

    base_value = sum(comps[k] * w for k, w in weights.items())
    mult = industry_multiplier(row["Industry_Health"])
    fair_value = base_value * mult

    # 區間由 Stage / Cycle 決定
    if row["Stage"] == "Cycle":
        bear_spread, bull_spread = 0.70, 1.45
    elif row["Stage"] == "Growth":
        bear_spread, bull_spread = 0.78, 1.35
    elif row["Stage"] == "Leader":
        bear_spread, bull_spread = 0.82, 1.28
    else:
        bear_spread, bull_spread = 0.85, 1.18

    bear = fair_value * bear_spread
    bull = fair_value * bull_spread
    return {
        "Model Family": selector["主模型"],
        "Model Weights": " / ".join([f"{k}:{int(v*100)}%" for k, v in weights.items()]),
        "Base Value Before Industry": round(base_value, 2),
        "Industry Multiplier": mult,
        "Bear": round(bear, 2),
        "Base": round(fair_value, 2),
        "Bull": round(bull, 2),
        "Components": comps,
    }


rows = []
component_rows = []

for c in companies:
    price, source = fetch_price(c["代號"], c["fallback"])
    val = final_valuation(c)
    upside = (val["Base"] / price - 1) * 100 if price and price > 0 else None
    status = "合理偏低" if upside is not None and upside > 15 else "合理偏高" if upside is not None and upside < -15 else "合理區間"

    rows.append({
        **c,
        "現價": price,
        "現價來源": source,
        "Model Family": val["Model Family"],
        "Model Weights": val["Model Weights"],
        "Base Value Before Industry": val["Base Value Before Industry"],
        "Industry Multiplier": val["Industry Multiplier"],
        "Bear": val["Bear"],
        "Base": val["Base"],
        "Bull": val["Bull"],
        "Upside%": round(upside, 1) if upside is not None else None,
        "價格判斷": status,
    })

    for k, v in val["Components"].items():
        component_rows.append({
            "公司": c["公司"],
            "估值模型": k,
            "模型估值": v,
            "CID": c["CID"],
            "Stage": c["Stage"],
        })

df = pd.DataFrame(rows)
component_df = pd.DataFrame(component_rows)

summary = pd.DataFrame([
    {"項目": "樣本公司數", "結果": len(df)},
    {"項目": "平均Industry Health", "結果": f"{round(df['Industry_Health'].mean(), 1)}%"},
    {"項目": "平均Industry Multiplier", "結果": round(df["Industry Multiplier"].mean(), 3)},
    {"項目": "平均Upside", "結果": f"{round(df['Upside%'].mean(), 1)}%"},
    {"項目": "合理偏低公司數", "結果": int((df["價格判斷"] == "合理偏低").sum())},
    {"項目": "合理偏高公司數", "結果": int((df["價格判斷"] == "合理偏高").sum())},
])

st.sidebar.header("V14.0 Valuation Core 控制台")
page = st.sidebar.radio(
    "功能",
    [
        "Valuation Overview",
        "CID → Model → Value",
        "Company Valuation Card",
        "Model Components",
        "Industry Multiplier",
        "Valuation Ranking",
        "Export JSON",
    ],
)
selected_company = st.sidebar.selectbox("選擇公司", df["公司"].tolist())

st.sidebar.divider()
st.sidebar.metric("樣本公司", len(df))
st.sidebar.metric("平均Industry Health", f"{round(df['Industry_Health'].mean(), 1)}%")
st.sidebar.metric("平均Upside", f"{round(df['Upside%'].mean(), 1)}%")

if page == "Valuation Overview":
    st.header("一、Valuation Overview")
    st.write("V14.0 第一版：從 CID 身份出發，自動選模型並產生 Bear / Base / Bull 估值區間。")
    st.dataframe(summary, use_container_width=True)

    st.subheader("估值總表")
    cols = [
        "公司", "代號", "現價", "CID", "Stage", "Model Family", "Model Weights",
        "Industry_Health", "Industry Multiplier", "Bear", "Base", "Bull", "Upside%", "價格判斷"
    ]
    st.dataframe(df[cols], use_container_width=True)

elif page == "CID → Model → Value":
    st.header("二、CID → Model → Value")
    st.write("檢查每家公司從身份辨識到模型選擇，再到估值區間的完整流程。")
    flow = df[[
        "公司", "CID", "Stage", "Model Family", "Model Weights",
        "Base Value Before Industry", "Industry Multiplier", "Base"
    ]]
    st.dataframe(flow, use_container_width=True)

elif page == "Company Valuation Card":
    st.header("三、Company Valuation Card")
    row = df[df["公司"] == selected_company].iloc[0]
    comps = component_df[component_df["公司"] == selected_company]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("現價", f"{row['現價']:,.2f}")
    c2.metric("Base合理價", f"{row['Base']:,.2f}", f"{row['Upside%']}%")
    c3.metric("Bear", f"{row['Bear']:,.2f}")
    c4.metric("Bull", f"{row['Bull']:,.2f}")

    st.subheader("公司身份與模型")
    card = pd.DataFrame([
        {"項目": "CID", "內容": row["CID"]},
        {"項目": "Stage", "內容": row["Stage"]},
        {"項目": "Model Family", "內容": row["Model Family"]},
        {"項目": "Model Weights", "內容": row["Model Weights"]},
        {"項目": "Industry Health", "內容": row["Industry_Health"]},
        {"項目": "Industry Multiplier", "內容": row["Industry Multiplier"]},
        {"項目": "價格判斷", "內容": row["價格判斷"]},
    ])
    st.dataframe(card, use_container_width=True)

    st.subheader("估值模型拆解")
    st.dataframe(comps, use_container_width=True)
    st.bar_chart(comps.set_index("估值模型")["模型估值"])

elif page == "Model Components":
    st.header("四、Model Components")
    st.write("所有公司各模型估值結果。正式版會替換成真實財報計算。")
    st.dataframe(component_df, use_container_width=True)

elif page == "Industry Multiplier":
    st.header("五、Industry Multiplier")
    st.write("產業健康度不是修改公司身份，而是調整估值結果。")
    im = df[["公司", "CID", "Stage", "Industry_Health", "Industry Multiplier", "Base Value Before Industry", "Base"]]
    st.dataframe(im, use_container_width=True)
    st.bar_chart(df.set_index("公司")["Industry Multiplier"])

elif page == "Valuation Ranking":
    st.header("六、Valuation Ranking")
    st.write("依 Upside 排序，用來檢查估值結果是否過度偏離。")
    rank = df.sort_values("Upside%", ascending=False)[[
        "公司", "CID", "Stage", "現價", "Bear", "Base", "Bull", "Upside%", "價格判斷"
    ]]
    st.dataframe(rank, use_container_width=True)
    st.bar_chart(rank.set_index("公司")["Upside%"])

elif page == "Export JSON":
    st.header("七、Export JSON")
    export = {
        "version": "V14.0 Valuation Core Prototype",
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "purpose": "CID → Stage → Model Selector → Valuation Core prototype.",
        "valuation_results": df.to_dict(orient="records"),
        "valuation_components": component_df.to_dict(orient="records"),
        "summary": summary.to_dict(orient="records"),
    }
    st.code(json.dumps(export, ensure_ascii=False, indent=2), language="json")
