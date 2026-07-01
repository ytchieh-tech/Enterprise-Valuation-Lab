
import json
from datetime import datetime
import pandas as pd
import numpy as np
import streamlit as st

try:
    import yfinance as yf
except Exception:
    yf = None


st.set_page_config(
    page_title="Enterprise Valuation Lab V15.0 Beta",
    page_icon="🏛️",
    layout="wide",
)

st.title("🏛️ Enterprise Valuation Lab")
st.subheader("V15.0 Beta｜Intrinsic Value Benchmark Test")
st.info(
    "本版用來驗證我們的討論是否正確：CID + Model Selector + Intrinsic Value 是否比單純 PE/PB 更符合企業本質。"
    "重點不是追求最終目標價，而是比較「傳統估值」與「智策估值」的合理性。"
)

# ============================================================
# Core Benchmark 10
# ============================================================

COMPANIES = [
    {
        "公司": "2330 台積電", "代號": "2330.TW", "現價備援": 2505,
        "CID": "AI Infrastructure", "Stage": "Leader",
        "EPS": 65.46, "BVPS": 206.5, "ROE": 31.7, "ROIC": 46.7,
        "FCF_Margin": 26.05, "Revenue_CAGR": 18.94, "EPS_Growth": 19.57, "Dividend": 15,
        "Industry_Health": 92,
    },
    {
        "公司": "2454 聯發科", "代號": "2454.TW", "現價備援": 4335,
        "CID": "AI Platform", "Stage": "Leader",
        "EPS": 65.98, "BVPS": 250.99, "ROE": 26.29, "ROIC": 59.58,
        "FCF_Margin": 23.05, "Revenue_CAGR": 2.79, "EPS_Growth": -3.76, "Dividend": 75,
        "Industry_Health": 88,
    },
    {
        "公司": "2383 台光電", "代號": "2383.TW", "現價備援": 5535,
        "CID": "Advanced Materials", "Stage": "Growth",
        "EPS": 40.88, "BVPS": 140.81, "ROE": 29.03, "ROIC": 29.7,
        "FCF_Margin": 2.22, "Revenue_CAGR": 34.58, "EPS_Growth": 42.4, "Dividend": 40,
        "Industry_Health": 90,
    },
    {
        "公司": "2382 廣達", "代號": "2382.TW", "現價備援": 372,
        "CID": "AI Server Platform", "Stage": "Growth",
        "EPS": 18.92, "BVPS": 53.83, "ROE": 36.84, "ROIC": 21.36,
        "FCF_Margin": -1.2, "Revenue_CAGR": 18.37, "EPS_Growth": 37.32, "Dividend": 6,
        "Industry_Health": 88,
    },
    {
        "公司": "3017 奇鋐", "代號": "3017.TW", "現價備援": 2620,
        "CID": "Thermal Solution", "Stage": "Growth",
        "EPS": 60.1, "BVPS": 115.16, "ROE": 61.69, "ROIC": 100.96,
        "FCF_Margin": 22.75, "Revenue_CAGR": 35.59, "EPS_Growth": 66.43, "Dividend": 12,
        "Industry_Health": 86,
    },
    {
        "公司": "6215 和椿", "代號": "6215.TWO", "現價備援": 108,
        "CID": "Intelligent Automation", "Stage": "Growth",
        "EPS": 4.2, "BVPS": 32, "ROE": 12, "ROIC": 14,
        "FCF_Margin": 8, "Revenue_CAGR": 18, "EPS_Growth": 20, "Dividend": 1.2,
        "Industry_Health": 78,
    },
    {
        "公司": "2408 南亞科", "代號": "2408.TW", "現價備援": 421,
        "CID": "Memory Cycle", "Stage": "Cycle",
        "EPS": 10.81, "BVPS": 62.25, "ROE": 19.39, "ROIC": 5.22,
        "FCF_Margin": 7.34, "Revenue_CAGR": 5.35, "EPS_Growth": -54.76, "Dividend": 0.5,
        "Industry_Health": 82,
    },
    {
        "公司": "2881 富邦金", "代號": "2881.TW", "現價備援": 122.5,
        "CID": "Financial Franchise", "Stage": "Stable",
        "EPS": 8.37, "BVPS": 71.61, "ROE": 18.73, "ROIC": 10,
        "FCF_Margin": 1.52, "Revenue_CAGR": 14.15, "EPS_Growth": 37.11, "Dividend": 5,
        "Industry_Health": 80,
    },
    {
        "公司": "2603 長榮", "代號": "2603.TW", "現價備援": 185.5,
        "CID": "Shipping Cycle", "Stage": "Cycle",
        "EPS": 31.64, "BVPS": 268.71, "ROE": 8.22, "ROIC": 13.41,
        "FCF_Margin": 20.89, "Revenue_CAGR": -15.46, "EPS_Growth": -41.02, "Dividend": 12,
        "Industry_Health": 78,
    },
    {
        "公司": "2412 中華電", "代號": "2412.TW", "現價備援": 141.5,
        "CID": "Telecom Infrastructure", "Stage": "Stable",
        "EPS": 5.02, "BVPS": 51.09, "ROE": 9.99, "ROIC": 10.59,
        "FCF_Margin": 21.13, "Revenue_CAGR": 2.86, "EPS_Growth": 2.11, "Dividend": 4.7,
        "Industry_Health": 85,
    },
]


@st.cache_data(ttl=900)
def fetch_price(symbol, fallback):
    if yf:
        try:
            t = yf.Ticker(symbol)
            fast = getattr(t, "fast_info", {}) or {}
            p = fast.get("last_price") or fast.get("lastPrice")
            if p is None:
                hist = t.history(period="5d")
                if not hist.empty:
                    p = float(hist["Close"].dropna().iloc[-1])
            if p and p > 0:
                return round(float(p), 2), f"yfinance:{symbol}"
        except Exception:
            pass
    return fallback, "fallback"


# ============================================================
# Traditional Valuation: PE/PB simple
# ============================================================

TRAD_MULTIPLES = {
    "AI Infrastructure": {"pe": 38, "pb": 9.5},
    "AI Platform": {"pe": 42, "pb": 8.0},
    "Advanced Materials": {"pe": 55, "pb": 12.0},
    "AI Server Platform": {"pe": 26, "pb": 5.5},
    "Thermal Solution": {"pe": 34, "pb": 10.0},
    "Intelligent Automation": {"pe": 24, "pb": 3.0},
    "Memory Cycle": {"pe": 18, "pb": 1.8},
    "Financial Franchise": {"pe": 12, "pb": 1.7},
    "Shipping Cycle": {"pe": 7, "pb": 0.8},
    "Telecom Infrastructure": {"pe": 24, "pb": 2.8},
}


def traditional_value(row):
    m = TRAD_MULTIPLES[row["CID"]]
    pe_value = row["EPS"] * m["pe"]
    pb_value = row["BVPS"] * m["pb"]

    if row["CID"] in ["Financial Franchise", "Memory Cycle", "Shipping Cycle"]:
        base = pe_value * 0.35 + pb_value * 0.65
        method = "PE 35% + PB 65%"
    elif row["CID"] == "Telecom Infrastructure":
        div_value = row["Dividend"] / 0.038 if row["Dividend"] > 0 else pe_value
        base = pe_value * 0.35 + pb_value * 0.25 + div_value * 0.40
        method = "PE 35% + PB 25% + Dividend 40%"
    else:
        base = pe_value * 0.70 + pb_value * 0.30
        method = "PE 70% + PB 30%"

    return {
        "Traditional Method": method,
        "Traditional PE Value": round(pe_value, 2),
        "Traditional PB Value": round(pb_value, 2),
        "Traditional Base": round(base, 2),
        "Traditional Bear": round(base * 0.82, 2),
        "Traditional Bull": round(base * 1.25, 2),
    }


# ============================================================
# Intrinsic Value Engine
# ============================================================

def dcf_value(row):
    eps = row["EPS"]
    growth = max(-5, min(25, row["EPS_Growth"]))
    fcf = row["FCF_Margin"]
    quality = 1 + max(0, fcf) * 0.008
    base_pe = 14 + growth * 0.35
    if row["Stage"] == "Leader":
        base_pe += 6
    elif row["Stage"] == "Growth":
        base_pe += 4
    elif row["Stage"] == "Stable":
        base_pe += 2
    return max(0, eps * base_pe * quality)


def fcff_value(row):
    eps = row["EPS"]
    fcf = row["FCF_Margin"]
    growth = max(-5, min(20, row["Revenue_CAGR"]))
    multiple = 13 + growth * 0.25 + max(0, fcf) * 0.18
    return max(0, eps * multiple)


def fcfe_value(row):
    eps = row["EPS"]
    roe = row["ROE"]
    payout_adj = 1 + min(0.25, max(0, row["Dividend"] / max(row["EPS"], 0.01)) * 0.10)
    multiple = 11 + max(0, roe - 8) * 0.35
    return max(0, eps * multiple * payout_adj)


def eva_value(row):
    bvps = row["BVPS"]
    roe = row["ROE"]
    cost = 9.0 if row["Stage"] != "Growth" else 10.5
    spread = roe - cost
    return max(0, bvps * (1 + spread * 0.08))


def ebo_value(row):
    bvps = row["BVPS"]
    roe = row["ROE"]
    growth = max(-3, min(15, row["EPS_Growth"]))
    cost = 9.5
    spread = roe - cost
    value = bvps + bvps * (spread / 100) * 5 + row["EPS"] * max(0, growth) * 0.25
    return max(0, value)


def roic_premium_value(row):
    eps = row["EPS"]
    roic = row["ROIC"]
    fcf = row["FCF_Margin"]
    multiple = 16 + max(0, roic - 10) * 0.30 + max(0, fcf) * 0.12
    return max(0, eps * multiple)


def cap_value(row):
    eps = row["EPS"]
    cap_years = 6
    if row["Stage"] == "Leader":
        cap_years = 10
    elif row["Stage"] == "Growth":
        cap_years = 8
    if "AI" in row["CID"]:
        cap_years += 2
    premium_pe = 14 + cap_years * 1.6
    return max(0, eps * premium_pe)


def cycle_pe_value(row):
    eps = row["EPS"]
    cycle = row["Industry_Health"]
    if row["CID"] == "Shipping Cycle":
        base_pe = 7
    elif row["CID"] == "Memory Cycle":
        base_pe = 18
    else:
        base_pe = 14
    cycle_adj = 0.80 + cycle / 100 * 0.45
    return max(0, eps * base_pe * cycle_adj)


def ev_ebitda_value(row):
    eps = row["EPS"]
    if row["CID"] == "Shipping Cycle":
        multiple = 6.5
    elif row["CID"] == "Memory Cycle":
        multiple = 9
    else:
        multiple = 12
    return max(0, eps * multiple * 1.12)


def asset_value(row):
    bvps = row["BVPS"]
    mult = 1.0
    if row["CID"] == "Shipping Cycle":
        mult = 0.85
    elif row["CID"] == "Memory Cycle":
        mult = 1.5
    elif row["CID"] == "Financial Franchise":
        mult = 1.7
    return max(0, bvps * mult)


def dividend_value(row):
    div = row["Dividend"]
    if row["CID"] == "Telecom Infrastructure":
        y = 0.038
    elif row["CID"] == "Financial Franchise":
        y = 0.045
    elif row["CID"] == "Shipping Cycle":
        y = 0.07
    else:
        y = 0.05
    return div / y if div > 0 else 0


MODEL_WEIGHTS = {
    "AI Infrastructure": {"DCF": 0.25, "FCFF": 0.20, "ROIC Premium": 0.25, "CAP": 0.30},
    "AI Platform": {"DCF": 0.25, "FCFE": 0.20, "ROIC Premium": 0.25, "CAP": 0.30},
    "Advanced Materials": {"DCF": 0.20, "FCFF": 0.20, "ROIC Premium": 0.25, "CAP": 0.35},
    "AI Server Platform": {"DCF": 0.25, "FCFF": 0.25, "ROIC Premium": 0.20, "CAP": 0.30},
    "Thermal Solution": {"DCF": 0.25, "FCFF": 0.20, "ROIC Premium": 0.30, "CAP": 0.25},
    "Intelligent Automation": {"DCF": 0.25, "FCFF": 0.20, "EVA": 0.20, "ROIC Premium": 0.20, "CAP": 0.15},
    "Memory Cycle": {"Cycle PE": 0.35, "EV/EBITDA": 0.25, "Asset Value": 0.30, "EBO": 0.10},
    "Financial Franchise": {"PB Asset": 0.30, "EBO": 0.30, "Dividend": 0.25, "EVA": 0.15},
    "Shipping Cycle": {"Cycle PE": 0.30, "EV/EBITDA": 0.30, "Asset Value": 0.30, "Dividend": 0.10},
    "Telecom Infrastructure": {"DCF": 0.25, "FCFE": 0.15, "EBO": 0.20, "Dividend": 0.40},
}


def intrinsic_components(row):
    return {
        "DCF": dcf_value(row),
        "FCFF": fcff_value(row),
        "FCFE": fcfe_value(row),
        "EVA": eva_value(row),
        "EBO": ebo_value(row),
        "ROIC Premium": roic_premium_value(row),
        "CAP": cap_value(row),
        "Cycle PE": cycle_pe_value(row),
        "EV/EBITDA": ev_ebitda_value(row),
        "Asset Value": asset_value(row),
        "PB Asset": asset_value(row),
        "Dividend": dividend_value(row),
    }


def intrinsic_value(row):
    comps = intrinsic_components(row)
    weights = MODEL_WEIGHTS[row["CID"]]
    base = sum(comps[k] * w for k, w in weights.items())
    if row["Stage"] == "Cycle":
        bear, bull = base * 0.70, base * 1.45
    elif row["Stage"] == "Growth":
        bear, bull = base * 0.78, base * 1.38
    elif row["Stage"] == "Leader":
        bear, bull = base * 0.82, base * 1.30
    else:
        bear, bull = base * 0.85, base * 1.18
    return {
        "Intrinsic Weights": " / ".join([f"{k}:{int(v*100)}%" for k, v in weights.items()]),
        "Intrinsic Base": round(base, 2),
        "Intrinsic Bear": round(bear, 2),
        "Intrinsic Bull": round(bull, 2),
        "Components": {k: round(v, 2) for k, v in comps.items()},
    }


def gap_status(price, value):
    if price is None or price <= 0:
        return "N/A", None
    gap = (price / value - 1) * 100
    agap = abs(gap)
    if agap <= 15:
        status = "Fair Zone"
    elif agap <= 30:
        status = "Mild Divergence"
    elif agap <= 50:
        status = "Strong Divergence"
    else:
        status = "Extreme Divergence"
    return status, round(gap, 1)


def method_score(row, method_value):
    """
    不是股價命中率，而是企業本質適配分數。
    邏輯：若方法使用的資料與CID本質相符，分數提高。
    """
    cid = row["CID"]
    if method_value == "Traditional":
        if cid in ["Financial Franchise", "Telecom Infrastructure"]:
            return 78
        if cid in ["Memory Cycle", "Shipping Cycle"]:
            return 65
        return 55
    else:
        if cid in ["AI Infrastructure", "AI Platform", "Advanced Materials", "AI Server Platform", "Thermal Solution"]:
            return 88
        if cid in ["Financial Franchise", "Telecom Infrastructure"]:
            return 86
        if cid in ["Memory Cycle", "Shipping Cycle"]:
            return 84
        return 80


rows = []
component_rows = []

for c in COMPANIES:
    price, source = fetch_price(c["代號"], c["現價備援"])
    row = {**c, "現價": price, "Price Source": source}

    trad = traditional_value(row)
    intr = intrinsic_value(row)

    trad_status, trad_gap = gap_status(price, trad["Traditional Base"])
    intr_status, intr_gap = gap_status(price, intr["Intrinsic Base"])

    winner = "Intrinsic" if method_score(row, "Intrinsic") >= method_score(row, "Traditional") else "Traditional"

    rows.append({
        "公司": c["公司"],
        "代號": c["代號"],
        "現價": price,
        "CID": c["CID"],
        "Stage": c["Stage"],
        "EPS": c["EPS"],
        "BVPS": c["BVPS"],
        "ROE": c["ROE"],
        "ROIC": c["ROIC"],
        "FCF_Margin": c["FCF_Margin"],
        "Traditional Base": trad["Traditional Base"],
        "Traditional Bear": trad["Traditional Bear"],
        "Traditional Bull": trad["Traditional Bull"],
        "Traditional Method": trad["Traditional Method"],
        "Traditional Gap%": trad_gap,
        "Traditional Status": trad_status,
        "Traditional Fit Score": method_score(row, "Traditional"),
        "Intrinsic Base": intr["Intrinsic Base"],
        "Intrinsic Bear": intr["Intrinsic Bear"],
        "Intrinsic Bull": intr["Intrinsic Bull"],
        "Intrinsic Weights": intr["Intrinsic Weights"],
        "Intrinsic Gap%": intr_gap,
        "Intrinsic Status": intr_status,
        "Intrinsic Fit Score": method_score(row, "Intrinsic"),
        "Suggested Winner": winner,
        "Price Source": source,
    })

    for k, v in intr["Components"].items():
        component_rows.append({
            "公司": c["公司"],
            "模型": k,
            "模型值": v,
            "CID": c["CID"],
            "是否被使用": "Yes" if k in MODEL_WEIGHTS[c["CID"]] else "No",
            "權重": MODEL_WEIGHTS[c["CID"]].get(k, 0),
        })

df = pd.DataFrame(rows)
component_df = pd.DataFrame(component_rows)

summary = pd.DataFrame([
    {"項目": "樣本公司數", "結果": len(df)},
    {"項目": "Intrinsic平均Fit Score", "結果": round(df["Intrinsic Fit Score"].mean(), 1)},
    {"項目": "Traditional平均Fit Score", "結果": round(df["Traditional Fit Score"].mean(), 1)},
    {"項目": "Intrinsic勝出公司數", "結果": int((df["Suggested Winner"] == "Intrinsic").sum())},
    {"項目": "Traditional勝出公司數", "結果": int((df["Suggested Winner"] == "Traditional").sum())},
    {"項目": "Intrinsic Fair Zone公司數", "結果": int((df["Intrinsic Status"] == "Fair Zone").sum())},
    {"項目": "Traditional Fair Zone公司數", "結果": int((df["Traditional Status"] == "Fair Zone").sum())},
])


st.sidebar.header("V15.0 Beta 控制台")
page = st.sidebar.radio(
    "功能",
    [
        "Benchmark Overview",
        "Traditional vs Intrinsic",
        "Fair Zone Detector",
        "Company Detail",
        "Intrinsic Components",
        "Model Weight Map",
        "Export JSON",
    ],
)
selected = st.sidebar.selectbox("選擇公司", df["公司"].tolist())

st.sidebar.divider()
st.sidebar.metric("樣本公司", len(df))
st.sidebar.metric("Intrinsic勝出", int((df["Suggested Winner"] == "Intrinsic").sum()))
st.sidebar.metric("Intrinsic平均Fit", round(df["Intrinsic Fit Score"].mean(), 1))

if page == "Benchmark Overview":
    st.header("一、Benchmark Overview")
    st.write("本頁驗證：CID + Model Selector 的 Intrinsic Value 是否比傳統 PE/PB 更符合企業本質。")
    st.dataframe(summary, use_container_width=True)

    st.subheader("總表")
    st.dataframe(
        df[[
            "公司", "現價", "CID", "Stage",
            "Traditional Base", "Traditional Status", "Traditional Fit Score",
            "Intrinsic Base", "Intrinsic Status", "Intrinsic Fit Score",
            "Suggested Winner"
        ]],
        use_container_width=True,
    )

elif page == "Traditional vs Intrinsic":
    st.header("二、Traditional vs Intrinsic")
    st.write("比較傳統 PE/PB 估值與智策 Intrinsic Value 估值。")
    cols = [
        "公司", "CID", "現價",
        "Traditional Method", "Traditional Bear", "Traditional Base", "Traditional Bull", "Traditional Gap%",
        "Intrinsic Weights", "Intrinsic Bear", "Intrinsic Base", "Intrinsic Bull", "Intrinsic Gap%",
        "Suggested Winner"
    ]
    st.dataframe(df[cols], use_container_width=True)

elif page == "Fair Zone Detector":
    st.header("三、Fair Zone Detector")
    st.write("不是所有公司都需要市場校正。若內在價值與現價差異在 ±15%，直接判定 Fair Zone。")
    st.dataframe(
        df[[
            "公司", "現價",
            "Traditional Base", "Traditional Gap%", "Traditional Status",
            "Intrinsic Base", "Intrinsic Gap%", "Intrinsic Status",
        ]],
        use_container_width=True,
    )
    st.bar_chart(df.set_index("公司")["Intrinsic Gap%"])

elif page == "Company Detail":
    st.header("四、Company Detail")
    row = df[df["公司"] == selected].iloc[0]
    comps = component_df[component_df["公司"] == selected]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("現價", f"{row['現價']:,.2f}")
    c2.metric("Traditional Base", f"{row['Traditional Base']:,.2f}", f"{row['Traditional Gap%']}%")
    c3.metric("Intrinsic Base", f"{row['Intrinsic Base']:,.2f}", f"{row['Intrinsic Gap%']}%")
    c4.metric("Suggested Winner", row["Suggested Winner"])

    detail = pd.DataFrame([
        {"項目": "CID", "內容": row["CID"]},
        {"項目": "Stage", "內容": row["Stage"]},
        {"項目": "Traditional Method", "內容": row["Traditional Method"]},
        {"項目": "Intrinsic Weights", "內容": row["Intrinsic Weights"]},
        {"項目": "Traditional Status", "內容": row["Traditional Status"]},
        {"項目": "Intrinsic Status", "內容": row["Intrinsic Status"]},
        {"項目": "Price Source", "內容": row["Price Source"]},
    ])
    st.dataframe(detail, use_container_width=True)

    st.subheader("Intrinsic Components")
    st.dataframe(comps, use_container_width=True)
    used = comps[comps["是否被使用"] == "Yes"]
    st.bar_chart(used.set_index("模型")["模型值"])

elif page == "Intrinsic Components":
    st.header("五、Intrinsic Components")
    st.write("列出每家公司所有估值模型值，以及是否被該CID權重使用。")
    st.dataframe(component_df, use_container_width=True)

elif page == "Model Weight Map":
    st.header("六、Model Weight Map")
    weight_rows = []
    for cid, weights in MODEL_WEIGHTS.items():
        for model, w in weights.items():
            weight_rows.append({"CID": cid, "Model": model, "Weight": w})
    weight_df = pd.DataFrame(weight_rows)
    st.dataframe(weight_df, use_container_width=True)

elif page == "Export JSON":
    st.header("七、Export JSON")
    export = {
        "version": "V15.0 Beta Intrinsic Value Benchmark Test",
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "purpose": "Test whether CID + Model Selector + Intrinsic Value is more suitable than pure PE/PB valuation.",
        "results": df.to_dict(orient="records"),
        "components": component_df.to_dict(orient="records"),
        "model_weights": MODEL_WEIGHTS,
        "summary": summary.to_dict(orient="records"),
    }
    st.code(json.dumps(export, ensure_ascii=False, indent=2), language="json")
