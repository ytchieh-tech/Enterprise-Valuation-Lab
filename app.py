
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
    page_title="Enterprise Valuation Lab V15.0.1",
    page_icon="🏛️",
    layout="wide",
)

st.title("🏛️ Enterprise Valuation Lab")
st.subheader("V15.0.1｜Multiplier Calibration Engine 倍率校正引擎")
st.info(
    "本版延續 V15.0 Beta：不修正 CID、不修正 Model Selector，"
    "只針對不同 CID 的估值倍率尺度做校正，驗證 Fair Zone 是否改善。"
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


# ============================================================
# CID Calibration Library
# ============================================================

CALIBRATION_LIBRARY = {
    "AI Infrastructure": {
        "Base Multiplier": 1.25,
        "Growth Premium": 1.10,
        "ROIC Premium": 1.20,
        "CAP Premium": 1.15,
        "Reason": "AI基礎建設龍頭，高ROIC、高FCF與長競爭優勢期間需提高尺度。"
    },
    "AI Platform": {
        "Base Multiplier": 1.35,
        "Growth Premium": 1.10,
        "ROIC Premium": 1.20,
        "CAP Premium": 1.15,
        "Reason": "平台型半導體具高ROIC與高現金流，V15.0原始倍率偏保守。"
    },
    "Advanced Materials": {
        "Base Multiplier": 1.75,
        "Growth Premium": 1.35,
        "ROIC Premium": 1.10,
        "CAP Premium": 1.20,
        "Reason": "AI材料具高度成長溢價，需補上Growth Premium Layer。"
    },
    "AI Server Platform": {
        "Base Multiplier": 1.10,
        "Growth Premium": 1.05,
        "ROIC Premium": 1.05,
        "CAP Premium": 1.05,
        "Reason": "AI伺服器平台仍偏製造/組裝，校正幅度較小。"
    },
    "Thermal Solution": {
        "Base Multiplier": 1.30,
        "Growth Premium": 1.20,
        "ROIC Premium": 1.15,
        "CAP Premium": 1.10,
        "Reason": "散熱族群受AI伺服器需求拉動，高ROIC公司需要成長溢價。"
    },
    "Intelligent Automation": {
        "Base Multiplier": 1.20,
        "Growth Premium": 1.10,
        "ROIC Premium": 1.05,
        "CAP Premium": 1.05,
        "Reason": "自動化與機器人仍屬早期成長，溢價存在但需保守。"
    },
    "Memory Cycle": {
        "Base Multiplier": 1.00,
        "Growth Premium": 1.00,
        "ROIC Premium": 1.00,
        "CAP Premium": 1.00,
        "Reason": "記憶體以週期為主，暫不做成長倍率校正。"
    },
    "Financial Franchise": {
        "Base Multiplier": 1.00,
        "Growth Premium": 1.00,
        "ROIC Premium": 1.00,
        "CAP Premium": 1.00,
        "Reason": "金融股主要由PB-ROE、EBO與股利折現決定，暫不額外校正。"
    },
    "Shipping Cycle": {
        "Base Multiplier": 1.00,
        "Growth Premium": 1.00,
        "ROIC Premium": 1.00,
        "CAP Premium": 1.00,
        "Reason": "航運以景氣循環、運價與資產價值決定，暫不額外校正。"
    },
    "Telecom Infrastructure": {
        "Base Multiplier": 1.00,
        "Growth Premium": 1.00,
        "ROIC Premium": 1.00,
        "CAP Premium": 1.00,
        "Reason": "電信穩定現金流以DCF與股利折現為主，暫不額外校正。"
    },
}


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


def raw_components(row):
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


def calibrated_components(row):
    comps = raw_components(row)
    cal = CALIBRATION_LIBRARY[row["CID"]]
    out = {}
    for k, v in comps.items():
        factor = cal["Base Multiplier"]
        if k in ["DCF", "FCFF", "FCFE"]:
            factor *= cal["Growth Premium"]
        if k == "ROIC Premium":
            factor *= cal["ROIC Premium"]
        if k == "CAP":
            factor *= cal["CAP Premium"]
        out[k] = v * factor
    return out


def composite_value(row, calibrated=True):
    comps = calibrated_components(row) if calibrated else raw_components(row)
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
    return round(bear, 2), round(base, 2), round(bull, 2), comps


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


rows = []
component_rows = []
calibration_rows = []

for c in COMPANIES:
    price, source = fetch_price(c["代號"], c["現價備援"])
    row = {**c, "現價": price, "Price Source": source}
    raw_bear, raw_base, raw_bull, raw_comps = composite_value(row, calibrated=False)
    cal_bear, cal_base, cal_bull, cal_comps = composite_value(row, calibrated=True)

    raw_status, raw_gap = gap_status(price, raw_base)
    cal_status, cal_gap = gap_status(price, cal_base)
    cal = CALIBRATION_LIBRARY[c["CID"]]

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
        "Raw Bear": raw_bear,
        "Raw Base": raw_base,
        "Raw Bull": raw_bull,
        "Raw Gap%": raw_gap,
        "Raw Status": raw_status,
        "Calibrated Bear": cal_bear,
        "Calibrated Base": cal_base,
        "Calibrated Bull": cal_bull,
        "Calibrated Gap%": cal_gap,
        "Calibrated Status": cal_status,
        "Base Multiplier": cal["Base Multiplier"],
        "Growth Premium": cal["Growth Premium"],
        "ROIC Premium Factor": cal["ROIC Premium"],
        "CAP Premium Factor": cal["CAP Premium"],
        "Calibration Reason": cal["Reason"],
        "Intrinsic Weights": " / ".join([f"{k}:{int(v*100)}%" for k, v in MODEL_WEIGHTS[c["CID"]].items()]),
        "Price Source": source,
    })

    for k, v in raw_comps.items():
        component_rows.append({
            "公司": c["公司"],
            "CID": c["CID"],
            "模型": k,
            "Raw模型值": round(v, 2),
            "Calibrated模型值": round(cal_comps[k], 2),
            "是否使用": "Yes" if k in MODEL_WEIGHTS[c["CID"]] else "No",
            "權重": MODEL_WEIGHTS[c["CID"]].get(k, 0),
        })

for cid, cal in CALIBRATION_LIBRARY.items():
    calibration_rows.append({
        "CID": cid,
        "Base Multiplier": cal["Base Multiplier"],
        "Growth Premium": cal["Growth Premium"],
        "ROIC Premium": cal["ROIC Premium"],
        "CAP Premium": cal["CAP Premium"],
        "Reason": cal["Reason"],
    })

df = pd.DataFrame(rows)
component_df = pd.DataFrame(component_rows)
calibration_df = pd.DataFrame(calibration_rows)

cid_summary = df.groupby("CID").agg(
    公司數=("公司", "count"),
    Raw_Fair_Zone=("Raw Status", lambda x: int((x == "Fair Zone").sum())),
    Calibrated_Fair_Zone=("Calibrated Status", lambda x: int((x == "Fair Zone").sum())),
    平均RawGap=("Raw Gap%", "mean"),
    平均CalibratedGap=("Calibrated Gap%", "mean"),
).reset_index()
cid_summary["平均RawGap"] = cid_summary["平均RawGap"].round(1)
cid_summary["平均CalibratedGap"] = cid_summary["平均CalibratedGap"].round(1)

summary = pd.DataFrame([
    {"項目": "樣本公司數", "結果": len(df)},
    {"項目": "Raw Fair Zone公司數", "結果": int((df["Raw Status"] == "Fair Zone").sum())},
    {"項目": "Calibrated Fair Zone公司數", "結果": int((df["Calibrated Status"] == "Fair Zone").sum())},
    {"項目": "Raw平均絕對Gap", "結果": f"{round(df['Raw Gap%'].abs().mean(), 1)}%"},
    {"項目": "Calibrated平均絕對Gap", "結果": f"{round(df['Calibrated Gap%'].abs().mean(), 1)}%"},
    {"項目": "改善公司數", "結果": int((df["Calibrated Gap%"].abs() < df["Raw Gap%"].abs()).sum())},
])


st.sidebar.header("V15.0.1 Calibration 控制台")
page = st.sidebar.radio(
    "功能",
    [
        "Calibration Overview",
        "Raw vs Calibrated",
        "Calibration Center",
        "Fair Zone Heat Map",
        "Company Detail",
        "Component Calibration",
        "Export JSON",
    ],
)
selected = st.sidebar.selectbox("選擇公司", df["公司"].tolist())

st.sidebar.divider()
st.sidebar.metric("樣本公司", len(df))
st.sidebar.metric("Raw Fair Zone", int((df["Raw Status"] == "Fair Zone").sum()))
st.sidebar.metric("Calibrated Fair Zone", int((df["Calibrated Status"] == "Fair Zone").sum()))

if page == "Calibration Overview":
    st.header("一、Calibration Overview")
    st.write("比較 V15.0 原始 Intrinsic Value 與 V15.0.1 校正後 Intrinsic Value。")
    st.dataframe(summary, use_container_width=True)

    st.subheader("總表")
    st.dataframe(
        df[[
            "公司", "現價", "CID", "Stage",
            "Raw Base", "Raw Gap%", "Raw Status",
            "Calibrated Base", "Calibrated Gap%", "Calibrated Status",
            "Base Multiplier", "Growth Premium", "ROIC Premium Factor", "CAP Premium Factor"
        ]],
        use_container_width=True,
    )

elif page == "Raw vs Calibrated":
    st.header("二、Raw vs Calibrated")
    st.write("確認倍率校正是否改善 Fair Zone。")
    show = df[[
        "公司", "現價", "Raw Bear", "Raw Base", "Raw Bull", "Raw Gap%", "Raw Status",
        "Calibrated Bear", "Calibrated Base", "Calibrated Bull", "Calibrated Gap%", "Calibrated Status"
    ]]
    st.dataframe(show, use_container_width=True)
    chart_df = df.set_index("公司")[["Raw Gap%", "Calibrated Gap%"]]
    st.bar_chart(chart_df)

elif page == "Calibration Center":
    st.header("三、Calibration Center")
    st.write("CID層級的倍率資料庫。校正對象是CID，不是單一公司。")
    st.dataframe(calibration_df, use_container_width=True)

    st.subheader("CID改善摘要")
    st.dataframe(cid_summary, use_container_width=True)

elif page == "Fair Zone Heat Map":
    st.header("四、Fair Zone Heat Map")
    st.write("檢查哪些公司仍然偏離，需要未來做 Forecast Revision 或更細的CID倍率庫。")
    heat = df[[
        "公司", "CID", "現價", "Raw Base", "Raw Gap%", "Raw Status",
        "Calibrated Base", "Calibrated Gap%", "Calibrated Status",
        "Calibration Reason"
    ]]
    st.dataframe(heat, use_container_width=True)

elif page == "Company Detail":
    st.header("五、Company Detail")
    row = df[df["公司"] == selected].iloc[0]
    comps = component_df[component_df["公司"] == selected]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("現價", f"{row['現價']:,.2f}")
    c2.metric("Raw Base", f"{row['Raw Base']:,.2f}", f"{row['Raw Gap%']}%")
    c3.metric("Calibrated Base", f"{row['Calibrated Base']:,.2f}", f"{row['Calibrated Gap%']}%")
    c4.metric("Calibrated Status", row["Calibrated Status"])

    detail = pd.DataFrame([
        {"項目": "CID", "內容": row["CID"]},
        {"項目": "Stage", "內容": row["Stage"]},
        {"項目": "Intrinsic Weights", "內容": row["Intrinsic Weights"]},
        {"項目": "Base Multiplier", "內容": row["Base Multiplier"]},
        {"項目": "Growth Premium", "內容": row["Growth Premium"]},
        {"項目": "ROIC Premium Factor", "內容": row["ROIC Premium Factor"]},
        {"項目": "CAP Premium Factor", "內容": row["CAP Premium Factor"]},
        {"項目": "Reason", "內容": row["Calibration Reason"]},
    ])
    st.dataframe(detail, use_container_width=True)

    st.subheader("Component Calibration")
    st.dataframe(comps, use_container_width=True)
    used = comps[comps["是否使用"] == "Yes"].set_index("模型")[["Raw模型值", "Calibrated模型值"]]
    st.bar_chart(used)

elif page == "Component Calibration":
    st.header("六、Component Calibration")
    st.write("各模型在校正前後的變化。")
    st.dataframe(component_df, use_container_width=True)

elif page == "Export JSON":
    st.header("七、Export JSON")
    export = {
        "version": "V15.0.1 Multiplier Calibration Engine",
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "purpose": "Calibrate valuation scale by CID without changing CID or Model Selector.",
        "results": df.to_dict(orient="records"),
        "components": component_df.to_dict(orient="records"),
        "calibration_library": CALIBRATION_LIBRARY,
        "cid_summary": cid_summary.to_dict(orient="records"),
        "summary": summary.to_dict(orient="records"),
    }
    st.code(json.dumps(export, ensure_ascii=False, indent=2), language="json")
