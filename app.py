
import json
from datetime import datetime

import pandas as pd
import streamlit as st

try:
    import yfinance as yf
except Exception:
    yf = None


st.set_page_config(page_title="Enterprise Valuation Lab V12.6", page_icon="🏛️", layout="wide")

st.title("🏛️ Enterprise Valuation Lab")
st.subheader("V12.6｜CID Identity Tree Engine 修正版")
st.info(
    "本版修正 V12.5 的 Confidence 過低問題：把相近身份放入同一 Identity Tree，"
    "同樹系身份不視為衝突；只有跨樹系身份才降低信心度。"
)


# ============================================================
# Helpers
# ============================================================

@st.cache_data(ttl=900)
def fetch_price(symbol, fallback=None):
    candidates = []
    if symbol.endswith(".TW") or symbol.endswith(".TWO"):
        candidates.append(symbol)
        base = symbol.split(".")[0]
        candidates.append(base + (".TWO" if symbol.endswith(".TW") else ".TW"))
    else:
        candidates += [symbol + ".TW", symbol + ".TWO"]

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
                    return float(price), f"yfinance：{ticker}"
            except Exception:
                pass

    if fallback is not None:
        return float(fallback), "fallback 備援價"
    return None, "抓不到現價"


def normalize_scores(raw):
    total = sum(max(0, v) for v in raw.values())
    if total <= 0:
        return {}
    scores = {k: round(max(0, v) / total * 100, 1) for k, v in raw.items()}
    diff = round(100 - sum(scores.values()), 1)
    if scores and abs(diff) >= 0.1:
        best = max(scores, key=scores.get)
        scores[best] = round(scores[best] + diff, 1)
    return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))


# ============================================================
# Identity Tree
# ============================================================

IDENTITY_TREE = {
    "AI Infrastructure Family": [
        "AI Infrastructure", "Compute Infrastructure", "AI Server Platform",
        "Cloud Infrastructure", "AI Infrastructure Material", "Thermal Solution"
    ],
    "Semiconductor Family": [
        "Semiconductor", "Foundry", "Advanced Manufacturing", "Advanced Packaging",
        "AI Platform", "Edge AI", "Mobile SoC"
    ],
    "Advanced Materials Family": [
        "Advanced Materials", "PCB/CCL", "AI Infrastructure Material"
    ],
    "Automation Family": [
        "Intelligent Automation", "Robot Integrator", "Robot Component",
        "Industrial Equipment", "Automation"
    ],
    "Memory Cycle Family": [
        "Memory Cycle", "Super Cycle", "Specialty Memory", "Commodity Tech"
    ],
    "Financial Family": [
        "Financial Franchise", "Insurance Holding", "Banking Holding"
    ],
    "Traditional Family": [
        "Traditional Industry", "ODM", "Notebook ODM", "Server ODM", "Industrial Component"
    ],
    "Growth Family": [
        "Growth Re-rating"
    ],
}

IDENTITY_TO_TREE = {}
for tree, ids in IDENTITY_TREE.items():
    for i in ids:
        IDENTITY_TO_TREE[i] = tree


def identity_tree_of(identity):
    return IDENTITY_TO_TREE.get(identity, "Other Family")


def cid_identity_scores(company, fin):
    industry_tag = company["base_identity"]
    vdf = fin.get("VDF_Exposure", 0)
    cycle = fin.get("Cycle_Score", 0)
    capex = fin.get("Capex_Direction", 0)
    multiple = fin.get("Market_Multiple", 0)
    growth = fin.get("Revenue_CAGR", 0)
    roic = fin.get("ROIC", 0)
    fcf = fin.get("FCF_Margin", 0)

    raw = {}

    # Objective base identity / revenue identity, 40%
    for identity, weight in industry_tag.items():
        raw[identity] = raw.get(identity, 0) + weight * 0.40

    # Capex direction, 20%
    if capex >= 75:
        raw["AI Infrastructure"] = raw.get("AI Infrastructure", 0) + 18
        raw["AI Server Platform"] = raw.get("AI Server Platform", 0) + 8
    elif capex >= 55:
        raw["Advanced Manufacturing"] = raw.get("Advanced Manufacturing", 0) + 10
        raw["Advanced Materials"] = raw.get("Advanced Materials", 0) + 8
    else:
        raw["Traditional Industry"] = raw.get("Traditional Industry", 0) + 5

    # VDF / value driver, 20%
    if vdf >= 80:
        raw["AI Infrastructure"] = raw.get("AI Infrastructure", 0) + 12
        raw["Compute Infrastructure"] = raw.get("Compute Infrastructure", 0) + 8
    elif vdf >= 65:
        raw["Intelligent Automation"] = raw.get("Intelligent Automation", 0) + 8
        raw["AI Platform"] = raw.get("AI Platform", 0) + 6
    elif vdf <= 10 and company["sector"] == "Financial":
        raw["Financial Franchise"] = raw.get("Financial Franchise", 0) + 18

    # Market perception / cycle, 20%
    if multiple >= 80 and growth >= 20:
        raw["Growth Re-rating"] = raw.get("Growth Re-rating", 0) + 12
    if cycle >= 80:
        raw["Memory Cycle"] = raw.get("Memory Cycle", 0) + 18
        raw["Super Cycle"] = raw.get("Super Cycle", 0) + 10
    if roic >= 25 and fcf >= 15:
        raw["Structural Compounder"] = raw.get("Structural Compounder", 0) + 16
    if company["sector"] == "Financial":
        raw["Financial Franchise"] = raw.get("Financial Franchise", 0) + 12

    return normalize_scores(raw)


def tree_scores(identity_scores):
    raw = {}
    for identity, score in identity_scores.items():
        tree = identity_tree_of(identity)
        raw[tree] = raw.get(tree, 0) + score
    return dict(sorted(raw.items(), key=lambda x: x[1], reverse=True))


def confidence_from_identity_tree(identity_scores):
    """
    修正版 Confidence：
    1. 先計算 Identity Tree 分布。
    2. 同樹系身份不互相扣分。
    3. 主樹系分數高且跨樹系差距大，Confidence 提升。
    """
    if not identity_scores:
        return 0, "需人工確認", {}, "N/A"

    trees = tree_scores(identity_scores)
    tree_values = list(trees.values())
    main_tree = list(trees.keys())[0]
    main_tree_score = tree_values[0]
    second_tree_score = tree_values[1] if len(tree_values) > 1 else 0
    tree_spread = main_tree_score - second_tree_score

    ids = list(identity_scores.values())
    main_identity_score = ids[0]
    second_identity_score = ids[1] if len(ids) > 1 else 0
    main_identity = list(identity_scores.keys())[0]
    second_identity = list(identity_scores.keys())[1] if len(identity_scores) > 1 else ""

    same_tree_bonus = 0
    if second_identity and identity_tree_of(main_identity) == identity_tree_of(second_identity):
        same_tree_bonus = 18

    # 主樹系集中度 + 主樹系與第二樹系差距 + 同樹系獎勵
    confidence = main_tree_score * 0.75 + tree_spread * 0.55 + same_tree_bonus
    confidence = round(max(0, min(100, confidence)), 1)

    if confidence >= 80:
        label = "身份明確"
    elif confidence >= 60:
        label = "身份偏明確"
    elif confidence >= 40:
        label = "轉型中 / 多重身份"
    else:
        label = "需人工確認"

    return confidence, label, trees, main_tree


def legacy_confidence(identity_scores):
    vals = list(identity_scores.values())
    if not vals:
        return 0
    top = vals[0]
    second = vals[1] if len(vals) > 1 else 0
    return round(min(100, max(0, top * 0.7 + (top - second) * 0.6)), 1)


def drift_direction(company):
    drift = company.get("identity_drift", {})
    if not drift:
        return "暫無歷史"
    years = sorted(drift.keys())
    first = drift[years[0]]
    last = drift[years[-1]]
    first_top = max(first, key=first.get)
    last_top = max(last, key=last.get)
    if first_top != last_top:
        return f"{first_top} → {last_top}"
    return f"{last_top} 穩定"


def completeness(fin):
    fields = [
        "Revenue_CAGR", "EPS_CAGR", "ROIC", "ROE", "FCF_Margin",
        "VDF_Exposure", "Cycle_Score", "Capex_Direction", "Market_Multiple"
    ]
    missing = [f for f in fields if fin.get(f) is None]
    ok = len(fields) - len(missing)
    return round(ok / len(fields) * 100, 1), missing


# ============================================================
# CID Pilot sample
# ============================================================

companies = {
    "2330 台積電": {
        "symbol": "2330.TW", "fallback_price": 2370, "sector": "Semiconductor",
        "base_identity": {"Semiconductor": 40, "Advanced Manufacturing": 35, "Foundry": 25},
        "fallback_financials": {"Revenue_CAGR": 18, "EPS_CAGR": 22, "ROIC": 32, "ROE": 31, "FCF_Margin": 22, "VDF_Exposure": 85, "Cycle_Score": 72, "Capex_Direction": 90, "Market_Multiple": 78},
        "identity_drift": {"2022": {"Foundry": 55, "Semiconductor": 30, "Advanced Packaging": 15}, "2024": {"Advanced Manufacturing": 45, "Foundry": 35, "AI Infrastructure": 20}, "2026": {"AI Infrastructure": 55, "Advanced Manufacturing": 30, "Foundry": 15}},
    },
    "2383 台光電": {
        "symbol": "2383.TW", "fallback_price": 5450, "sector": "PCB / CCL",
        "base_identity": {"Advanced Materials": 50, "PCB/CCL": 35, "AI Infrastructure Material": 15},
        "fallback_financials": {"Revenue_CAGR": 28, "EPS_CAGR": 35, "ROIC": 30, "ROE": 32, "FCF_Margin": 18, "VDF_Exposure": 88, "Cycle_Score": 86, "Capex_Direction": 70, "Market_Multiple": 88},
        "identity_drift": {"2022": {"PCB/CCL": 60, "Advanced Materials": 30, "AI Infrastructure Material": 10}, "2024": {"Advanced Materials": 50, "PCB/CCL": 30, "AI Infrastructure Material": 20}, "2026": {"Advanced Materials": 60, "AI Infrastructure Material": 30, "PCB/CCL": 10}},
    },
    "3017 奇鋐": {
        "symbol": "3017.TW", "fallback_price": 980, "sector": "Thermal",
        "base_identity": {"Thermal Solution": 45, "AI Infrastructure": 35, "Advanced Manufacturing": 20},
        "fallback_financials": {"Revenue_CAGR": 25, "EPS_CAGR": 30, "ROIC": 24, "ROE": 28, "FCF_Margin": 13, "VDF_Exposure": 82, "Cycle_Score": 78, "Capex_Direction": 75, "Market_Multiple": 86},
        "identity_drift": {"2022": {"Thermal Solution": 70, "Industrial Component": 30}, "2024": {"Thermal Solution": 55, "AI Infrastructure": 35, "Industrial Component": 10}, "2026": {"AI Infrastructure": 55, "Thermal Solution": 35, "Advanced Manufacturing": 10}},
    },
    "2454 聯發科": {
        "symbol": "2454.TW", "fallback_price": 3910, "sector": "Semiconductor",
        "base_identity": {"AI Platform": 45, "Semiconductor": 30, "Edge AI": 25},
        "fallback_financials": {"Revenue_CAGR": 15, "EPS_CAGR": 18, "ROIC": 24, "ROE": 25, "FCF_Margin": 20, "VDF_Exposure": 82, "Cycle_Score": 70, "Capex_Direction": 45, "Market_Multiple": 85},
        "identity_drift": {"2022": {"Mobile SoC": 60, "Semiconductor": 30, "AI Platform": 10}, "2024": {"Mobile SoC": 40, "AI Platform": 35, "Semiconductor": 25}, "2026": {"AI Platform": 60, "Edge AI": 25, "Semiconductor": 15}},
    },
    "2382 廣達": {
        "symbol": "2382.TW", "fallback_price": 310, "sector": "ODM",
        "base_identity": {"AI Server Platform": 45, "ODM": 35, "Cloud Infrastructure": 20},
        "fallback_financials": {"Revenue_CAGR": 20, "EPS_CAGR": 25, "ROIC": 18, "ROE": 22, "FCF_Margin": 8, "VDF_Exposure": 80, "Cycle_Score": 78, "Capex_Direction": 80, "Market_Multiple": 82},
        "identity_drift": {"2022": {"Notebook ODM": 80, "Server ODM": 20}, "2024": {"Notebook ODM": 50, "AI Server Platform": 40, "ODM": 10}, "2026": {"AI Server Platform": 60, "Cloud Infrastructure": 25, "ODM": 15}},
    },
    "3231 緯創": {
        "symbol": "3231.TW", "fallback_price": 145, "sector": "ODM",
        "base_identity": {"AI Server Platform": 40, "ODM": 40, "Cloud Infrastructure": 20},
        "fallback_financials": {"Revenue_CAGR": 18, "EPS_CAGR": 28, "ROIC": 16, "ROE": 20, "FCF_Margin": 6, "VDF_Exposure": 76, "Cycle_Score": 75, "Capex_Direction": 78, "Market_Multiple": 80},
        "identity_drift": {"2022": {"Notebook ODM": 70, "Server ODM": 30}, "2024": {"AI Server Platform": 45, "Notebook ODM": 40, "ODM": 15}, "2026": {"AI Server Platform": 58, "ODM": 25, "Cloud Infrastructure": 17}},
    },
    "6215 和椿": {
        "symbol": "6215.TWO", "fallback_price": 100.5, "sector": "Automation",
        "base_identity": {"Intelligent Automation": 45, "Robot Integrator": 35, "Industrial Equipment": 20},
        "fallback_financials": {"Revenue_CAGR": 18, "EPS_CAGR": 20, "ROIC": 14, "ROE": 12, "FCF_Margin": 8, "VDF_Exposure": 72, "Cycle_Score": 65, "Capex_Direction": 55, "Market_Multiple": 78},
        "identity_drift": {"2022": {"Industrial Equipment": 60, "Automation": 40}, "2024": {"Intelligent Automation": 40, "Industrial Equipment": 35, "Robot Integrator": 25}, "2026": {"Intelligent Automation": 55, "Robot Integrator": 30, "Industrial Equipment": 15}},
    },
    "2049 上銀": {
        "symbol": "2049.TW", "fallback_price": 318.5, "sector": "Automation",
        "base_identity": {"Intelligent Automation": 35, "Robot Component": 35, "Industrial Equipment": 30},
        "fallback_financials": {"Revenue_CAGR": 9, "EPS_CAGR": 8, "ROIC": 12, "ROE": 10, "FCF_Margin": 10, "VDF_Exposure": 55, "Cycle_Score": 55, "Capex_Direction": 45, "Market_Multiple": 60},
        "identity_drift": {"2022": {"Industrial Equipment": 55, "Robot Component": 35, "Intelligent Automation": 10}, "2024": {"Robot Component": 40, "Industrial Equipment": 35, "Intelligent Automation": 25}, "2026": {"Robot Component": 40, "Intelligent Automation": 35, "Industrial Equipment": 25}},
    },
    "4540 全球傳動": {
        "symbol": "4540.TW", "fallback_price": 55.6, "sector": "Automation",
        "base_identity": {"Robot Component": 40, "Industrial Equipment": 35, "Intelligent Automation": 25},
        "fallback_financials": {"Revenue_CAGR": 10, "EPS_CAGR": 8, "ROIC": 8, "ROE": 7, "FCF_Margin": 7, "VDF_Exposure": 45, "Cycle_Score": 58, "Capex_Direction": 40, "Market_Multiple": 55},
        "identity_drift": {"2022": {"Industrial Equipment": 60, "Robot Component": 30, "Intelligent Automation": 10}, "2024": {"Robot Component": 40, "Industrial Equipment": 40, "Intelligent Automation": 20}, "2026": {"Robot Component": 45, "Intelligent Automation": 30, "Industrial Equipment": 25}},
    },
    "2408 南亞科": {
        "symbol": "2408.TW", "fallback_price": 95, "sector": "Memory",
        "base_identity": {"Memory Cycle": 70, "Semiconductor": 20, "Commodity Tech": 10},
        "fallback_financials": {"Revenue_CAGR": 35, "EPS_CAGR": 45, "ROIC": 7, "ROE": 8, "FCF_Margin": -3, "VDF_Exposure": 45, "Cycle_Score": 88, "Capex_Direction": 65, "Market_Multiple": 82},
        "identity_drift": {"2022": {"Memory Cycle": 80, "Semiconductor": 20}, "2024": {"Memory Cycle": 75, "Commodity Tech": 15, "Semiconductor": 10}, "2026": {"Memory Cycle": 65, "Super Cycle": 25, "Semiconductor": 10}},
    },
    "2344 華邦電": {
        "symbol": "2344.TW", "fallback_price": 30, "sector": "Memory",
        "base_identity": {"Memory Cycle": 60, "Specialty Memory": 25, "Commodity Tech": 15},
        "fallback_financials": {"Revenue_CAGR": 20, "EPS_CAGR": 30, "ROIC": 6, "ROE": 7, "FCF_Margin": -5, "VDF_Exposure": 35, "Cycle_Score": 82, "Capex_Direction": 55, "Market_Multiple": 75},
        "identity_drift": {"2022": {"Memory Cycle": 70, "Specialty Memory": 20, "Commodity Tech": 10}, "2024": {"Memory Cycle": 65, "Specialty Memory": 25, "Commodity Tech": 10}, "2026": {"Memory Cycle": 60, "Specialty Memory": 25, "Super Cycle": 15}},
    },
    "2881 富邦金": {
        "symbol": "2881.TW", "fallback_price": 128.5, "sector": "Financial",
        "base_identity": {"Financial Franchise": 60, "Insurance Holding": 30, "Banking Holding": 10},
        "fallback_financials": {"Revenue_CAGR": 8, "EPS_CAGR": 12, "ROIC": 10, "ROE": 14, "FCF_Margin": 8, "VDF_Exposure": 5, "Cycle_Score": 55, "Capex_Direction": 10, "Market_Multiple": 50},
        "identity_drift": {"2022": {"Financial Franchise": 60, "Insurance Holding": 30, "Banking Holding": 10}, "2024": {"Financial Franchise": 62, "Insurance Holding": 28, "Banking Holding": 10}, "2026": {"Financial Franchise": 60, "Insurance Holding": 30, "Banking Holding": 10}},
    },
    "2891 中信金": {
        "symbol": "2891.TW", "fallback_price": 70.3, "sector": "Financial",
        "base_identity": {"Financial Franchise": 55, "Banking Holding": 35, "Insurance Holding": 10},
        "fallback_financials": {"Revenue_CAGR": 6, "EPS_CAGR": 9, "ROIC": 9, "ROE": 13, "FCF_Margin": 7, "VDF_Exposure": 5, "Cycle_Score": 52, "Capex_Direction": 10, "Market_Multiple": 48},
        "identity_drift": {"2022": {"Financial Franchise": 55, "Banking Holding": 35, "Insurance Holding": 10}, "2024": {"Financial Franchise": 56, "Banking Holding": 34, "Insurance Holding": 10}, "2026": {"Financial Franchise": 55, "Banking Holding": 35, "Insurance Holding": 10}},
    },
}


# ============================================================
# UI data
# ============================================================

rows = []
tree_rows = []
drift_rows = []

for name, company in companies.items():
    price, price_source = fetch_price(company["symbol"], company["fallback_price"])
    fin = company["fallback_financials"]
    ids = cid_identity_scores(company, fin)
    old_conf = legacy_confidence(ids)
    new_conf, label, trees, main_tree = confidence_from_identity_tree(ids)
    comp, missing = completeness(fin)
    main_identity = max(ids, key=ids.get) if ids else "N/A"
    second_identity = list(ids.keys())[1] if len(ids) > 1 else ""
    second_score = ids.get(second_identity, 0) if second_identity else 0

    rows.append({
        "公司": name,
        "代號": company["symbol"],
        "現價": price,
        "主身份": main_identity,
        "主身份分數": ids.get(main_identity, 0),
        "副身份": second_identity,
        "副身份分數": second_score,
        "主樹系": main_tree,
        "舊Confidence": old_conf,
        "新Confidence": new_conf,
        "改善": round(new_conf - old_conf, 1),
        "信心分級": label,
        "Identity Drift": drift_direction(company),
        "財報完整度": comp,
        "現價來源": price_source,
        "身份分布": "、".join([f"{k}:{v}%" for k, v in ids.items()]),
        "樹系分布": "、".join([f"{k}:{v:.1f}%" for k, v in trees.items()]),
        "Revenue CAGR": fin.get("Revenue_CAGR"),
        "EPS CAGR": fin.get("EPS_CAGR"),
        "ROIC": fin.get("ROIC"),
        "ROE": fin.get("ROE"),
        "FCF Margin": fin.get("FCF_Margin"),
        "VDF Exposure": fin.get("VDF_Exposure"),
        "Cycle Score": fin.get("Cycle_Score"),
        "Capex Direction": fin.get("Capex_Direction"),
        "Market Multiple": fin.get("Market_Multiple"),
        "缺漏欄位": ", ".join(missing),
    })

    for tree, score in trees.items():
        tree_rows.append({"公司": name, "Identity Tree": tree, "Score": round(score, 1)})

    for year, dist in company.get("identity_drift", {}).items():
        for identity, score in dist.items():
            drift_rows.append({"公司": name, "年份": year, "Identity": identity, "Score": score})

df = pd.DataFrame(rows)
tree_df = pd.DataFrame(tree_rows)
drift_df = pd.DataFrame(drift_rows)

summary = pd.DataFrame([
    {"指標": "樣本公司數", "V12.5": len(df), "V12.6": len(df)},
    {"指標": "平均Confidence", "V12.5": f"{round(df['舊Confidence'].mean(), 1)}%", "V12.6": f"{round(df['新Confidence'].mean(), 1)}%"},
    {"指標": "需人工確認數", "V12.5": int((df["舊Confidence"] < 40).sum()), "V12.6": int((df["新Confidence"] < 40).sum())},
    {"指標": "身份明確/偏明確數", "V12.5": int((df["舊Confidence"] >= 60).sum()), "V12.6": int((df["新Confidence"] >= 60).sum())},
])

page = st.sidebar.radio(
    "功能",
    ["CID Overview", "Identity Tree View", "Confidence Fix Compare", "Identity Drift", "Company Detail", "Export JSON"]
)
selected_company = st.sidebar.selectbox("選擇公司", df["公司"].tolist())

st.sidebar.header("V12.6 CID 控制台")
st.sidebar.metric("樣本公司", len(df))
st.sidebar.metric("平均Confidence", f"{round(df['新Confidence'].mean(), 1)}%")
st.sidebar.metric("需人工確認", int((df["新Confidence"] < 40).sum()))

if page == "CID Overview":
    st.header("一、CID Overview")
    st.write("修正重點：主身份與副身份若屬於同一 Identity Tree，不再視為衝突。")
    st.dataframe(df, use_container_width=True)
    st.subheader("V12.5 vs V12.6 修正摘要")
    st.dataframe(summary, use_container_width=True)

elif page == "Identity Tree View":
    st.header("二、Identity Tree View")
    st.write("從平面身份改成樹狀身份，降低相近身份互相扣分的問題。")
    tree_map = []
    for tree, ids in IDENTITY_TREE.items():
        tree_map.append({"Identity Tree": tree, "包含身份": "、".join(ids)})
    st.dataframe(pd.DataFrame(tree_map), use_container_width=True)

    st.subheader("公司樹系分布")
    st.dataframe(tree_df, use_container_width=True)

elif page == "Confidence Fix Compare":
    st.header("三、Confidence Fix Compare")
    st.write("比較舊版 Confidence 與新版 Identity Tree Confidence。")
    cols = ["公司", "主身份", "副身份", "主樹系", "舊Confidence", "新Confidence", "改善", "信心分級"]
    st.dataframe(df[cols], use_container_width=True)
    chart_df = df.set_index("公司")[["舊Confidence", "新Confidence"]]
    st.bar_chart(chart_df)

elif page == "Identity Drift":
    st.header("四、Identity Drift")
    st.write("觀察公司身份是否從傳統產業轉向新價值驅動角色。")
    st.dataframe(drift_df, use_container_width=True)

    company_drift = drift_df[drift_df["公司"] == selected_company]
    if not company_drift.empty:
        pivot = company_drift.pivot_table(index="年份", columns="Identity", values="Score", fill_value=0)
        st.subheader(f"{selected_company} Identity Drift Chart")
        st.line_chart(pivot)

elif page == "Company Detail":
    st.header("五、Company Detail")
    row = df[df["公司"] == selected_company].iloc[0]
    company_tree = tree_df[tree_df["公司"] == selected_company]
    company = companies[selected_company]
    ids = cid_identity_scores(company, company["fallback_financials"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("主身份", row["主身份"])
    c2.metric("主樹系", row["主樹系"])
    c3.metric("新Confidence", f"{row['新Confidence']}%")
    c4.metric("改善", f"{row['改善']}%")

    st.subheader("身份分布")
    st.dataframe(pd.DataFrame([{"Identity": k, "Score": v, "Tree": identity_tree_of(k)} for k, v in ids.items()]), use_container_width=True)

    st.subheader("樹系分布")
    st.dataframe(company_tree, use_container_width=True)
    st.bar_chart(company_tree.set_index("Identity Tree")["Score"])

    st.info(
        "解釋：如果主身份與副身份在同一樹系，代表公司是同一價值鏈內的多重角色，不應被判定為高度不確定。"
        "只有跨樹系分數接近時，才代表真正的多重身份或轉型中。"
    )

elif page == "Export JSON":
    st.header("六、Export JSON")
    export = {
        "version": "V12.6 CID Identity Tree Engine",
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "identity_tree": IDENTITY_TREE,
        "cid_results": df.to_dict(orient="records"),
        "tree_distribution": tree_df.to_dict(orient="records"),
        "summary": summary.to_dict(orient="records"),
    }
    st.code(json.dumps(export, ensure_ascii=False, indent=2), language="json")
