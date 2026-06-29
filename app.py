
import json
from datetime import datetime
import pandas as pd
import streamlit as st

try:
    import yfinance as yf
except Exception:
    yf = None

st.set_page_config(page_title="Enterprise Valuation Lab V12.7", page_icon="🏛️", layout="wide")

st.title("🏛️ Enterprise Valuation Lab")
st.subheader("V12.7｜CID Confidence 2.0 + Identity Concentration Engine")
st.info(
    "本版修正 V12.6 的過度補償問題：同樹系身份會加分，但不會直接推到100分。"
    "Confidence 改由 Tree Concentration、Identity Concentration、Drift Stability、Data Completeness 綜合計算。"
)

# ============================================================
# Price
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
        "Growth Re-rating", "Structural Compounder"
    ],
}

IDENTITY_TO_TREE = {}
for tree, identities in IDENTITY_TREE.items():
    for identity in identities:
        IDENTITY_TO_TREE[identity] = tree

def identity_tree_of(identity):
    return IDENTITY_TO_TREE.get(identity, "Other Family")

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

def tree_scores(identity_scores):
    raw = {}
    for identity, score in identity_scores.items():
        tree = identity_tree_of(identity)
        raw[tree] = raw.get(tree, 0) + score
    return dict(sorted(raw.items(), key=lambda x: x[1], reverse=True))

def concentration_score(scores):
    vals = list(scores.values())
    if not vals:
        return 0
    top = vals[0]
    second = vals[1] if len(vals) > 1 else 0
    third = vals[2] if len(vals) > 2 else 0
    # 分數集中度：主項分數 + 主副差距 - 分散懲罰
    dispersion_penalty = max(0, third * 0.25)
    return max(0, min(100, top * 0.75 + (top - second) * 0.45 - dispersion_penalty))

def drift_stability_score(company):
    drift = company.get("identity_drift", {})
    if not drift:
        return 60
    years = sorted(drift.keys())
    first = drift[years[0]]
    last = drift[years[-1]]
    first_top = max(first, key=first.get)
    last_top = max(last, key=last.get)
    first_tree = identity_tree_of(first_top)
    last_tree = identity_tree_of(last_top)
    last_top_score = last[last_top]

    if first_top == last_top:
        return 90
    if first_tree == last_tree:
        return 80
    if last_top_score >= 55:
        return 70
    return 55

def data_completeness(fin):
    fields = [
        "Revenue_CAGR", "EPS_CAGR", "ROIC", "ROE", "FCF_Margin",
        "VDF_Exposure", "Cycle_Score", "Capex_Direction", "Market_Multiple"
    ]
    ok = sum(1 for f in fields if fin.get(f) is not None)
    return round(ok / len(fields) * 100, 1)

def confidence_v125(identity_scores):
    vals = list(identity_scores.values())
    if not vals:
        return 0
    top = vals[0]
    second = vals[1] if len(vals) > 1 else 0
    return round(min(100, max(0, top * 0.7 + (top - second) * 0.6)), 1)

def confidence_v126(identity_scores):
    if not identity_scores:
        return 0
    trees = tree_scores(identity_scores)
    vals = list(trees.values())
    main_tree_score = vals[0]
    second_tree_score = vals[1] if len(vals) > 1 else 0
    tree_spread = main_tree_score - second_tree_score

    ids = list(identity_scores.keys())
    same_tree_bonus = 0
    if len(ids) >= 2 and identity_tree_of(ids[0]) == identity_tree_of(ids[1]):
        same_tree_bonus = 18
    return round(max(0, min(100, main_tree_score * 0.75 + tree_spread * 0.55 + same_tree_bonus)), 1)

def confidence_v127(identity_scores, company, fin):
    trees = tree_scores(identity_scores)
    tree_conc = concentration_score(trees)
    identity_conc = concentration_score(identity_scores)
    drift = drift_stability_score(company)
    complete = data_completeness(fin)

    # Same-tree 只作溫和加分，不再直接推滿
    ids = list(identity_scores.keys())
    same_tree_bonus = 0
    if len(ids) >= 2 and identity_tree_of(ids[0]) == identity_tree_of(ids[1]):
        same_tree_bonus = 6

    confidence = (
        tree_conc * 0.38 +
        identity_conc * 0.27 +
        drift * 0.20 +
        complete * 0.15 +
        same_tree_bonus
    )
    confidence = round(max(0, min(95, confidence)), 1)

    if confidence >= 80:
        label = "身份明確"
    elif confidence >= 65:
        label = "身份偏明確"
    elif confidence >= 50:
        label = "轉型中 / 多重身份"
    else:
        label = "需人工確認"

    detail = {
        "Tree Concentration": round(tree_conc, 1),
        "Identity Concentration": round(identity_conc, 1),
        "Drift Stability": round(drift, 1),
        "Data Completeness": round(complete, 1),
        "Same Tree Bonus": same_tree_bonus,
    }
    return confidence, label, detail

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
    for identity, weight in industry_tag.items():
        raw[identity] = raw.get(identity, 0) + weight * 0.40

    if capex >= 75:
        raw["AI Infrastructure"] = raw.get("AI Infrastructure", 0) + 18
        raw["AI Server Platform"] = raw.get("AI Server Platform", 0) + 8
    elif capex >= 55:
        raw["Advanced Manufacturing"] = raw.get("Advanced Manufacturing", 0) + 10
        raw["Advanced Materials"] = raw.get("Advanced Materials", 0) + 8
    else:
        raw["Traditional Industry"] = raw.get("Traditional Industry", 0) + 5

    if vdf >= 80:
        raw["AI Infrastructure"] = raw.get("AI Infrastructure", 0) + 12
        raw["Compute Infrastructure"] = raw.get("Compute Infrastructure", 0) + 8
    elif vdf >= 65:
        raw["Intelligent Automation"] = raw.get("Intelligent Automation", 0) + 8
        raw["AI Platform"] = raw.get("AI Platform", 0) + 6
    elif vdf <= 10 and company["sector"] == "Financial":
        raw["Financial Franchise"] = raw.get("Financial Franchise", 0) + 18

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

# ============================================================
# Companies
# ============================================================

companies = {
    "2330 台積電": {
        "symbol": "2330.TW", "fallback_price": 2370, "sector": "Semiconductor",
        "base_identity": {"Semiconductor": 40, "Advanced Manufacturing": 35, "Foundry": 25},
        "fin": {"Revenue_CAGR": 18, "EPS_CAGR": 22, "ROIC": 32, "ROE": 31, "FCF_Margin": 22, "VDF_Exposure": 85, "Cycle_Score": 72, "Capex_Direction": 90, "Market_Multiple": 78},
        "identity_drift": {"2022": {"Foundry": 55, "Semiconductor": 30, "Advanced Packaging": 15}, "2024": {"Advanced Manufacturing": 45, "Foundry": 35, "AI Infrastructure": 20}, "2026": {"AI Infrastructure": 55, "Advanced Manufacturing": 30, "Foundry": 15}},
    },
    "2383 台光電": {
        "symbol": "2383.TW", "fallback_price": 5450, "sector": "PCB / CCL",
        "base_identity": {"Advanced Materials": 50, "PCB/CCL": 35, "AI Infrastructure Material": 15},
        "fin": {"Revenue_CAGR": 28, "EPS_CAGR": 35, "ROIC": 30, "ROE": 32, "FCF_Margin": 18, "VDF_Exposure": 88, "Cycle_Score": 86, "Capex_Direction": 70, "Market_Multiple": 88},
        "identity_drift": {"2022": {"PCB/CCL": 60, "Advanced Materials": 30, "AI Infrastructure Material": 10}, "2024": {"Advanced Materials": 50, "PCB/CCL": 30, "AI Infrastructure Material": 20}, "2026": {"Advanced Materials": 60, "AI Infrastructure Material": 30, "PCB/CCL": 10}},
    },
    "3017 奇鋐": {
        "symbol": "3017.TW", "fallback_price": 980, "sector": "Thermal",
        "base_identity": {"Thermal Solution": 45, "AI Infrastructure": 35, "Advanced Manufacturing": 20},
        "fin": {"Revenue_CAGR": 25, "EPS_CAGR": 30, "ROIC": 24, "ROE": 28, "FCF_Margin": 13, "VDF_Exposure": 82, "Cycle_Score": 78, "Capex_Direction": 75, "Market_Multiple": 86},
        "identity_drift": {"2022": {"Thermal Solution": 70, "Industrial Component": 30}, "2024": {"Thermal Solution": 55, "AI Infrastructure": 35, "Industrial Component": 10}, "2026": {"AI Infrastructure": 55, "Thermal Solution": 35, "Advanced Manufacturing": 10}},
    },
    "2454 聯發科": {
        "symbol": "2454.TW", "fallback_price": 3910, "sector": "Semiconductor",
        "base_identity": {"AI Platform": 45, "Semiconductor": 30, "Edge AI": 25},
        "fin": {"Revenue_CAGR": 15, "EPS_CAGR": 18, "ROIC": 24, "ROE": 25, "FCF_Margin": 20, "VDF_Exposure": 82, "Cycle_Score": 70, "Capex_Direction": 45, "Market_Multiple": 85},
        "identity_drift": {"2022": {"Mobile SoC": 60, "Semiconductor": 30, "AI Platform": 10}, "2024": {"Mobile SoC": 40, "AI Platform": 35, "Semiconductor": 25}, "2026": {"AI Platform": 60, "Edge AI": 25, "Semiconductor": 15}},
    },
    "2382 廣達": {
        "symbol": "2382.TW", "fallback_price": 310, "sector": "ODM",
        "base_identity": {"AI Server Platform": 45, "ODM": 35, "Cloud Infrastructure": 20},
        "fin": {"Revenue_CAGR": 20, "EPS_CAGR": 25, "ROIC": 18, "ROE": 22, "FCF_Margin": 8, "VDF_Exposure": 80, "Cycle_Score": 78, "Capex_Direction": 80, "Market_Multiple": 82},
        "identity_drift": {"2022": {"Notebook ODM": 80, "Server ODM": 20}, "2024": {"Notebook ODM": 50, "AI Server Platform": 40, "ODM": 10}, "2026": {"AI Server Platform": 60, "Cloud Infrastructure": 25, "ODM": 15}},
    },
    "3231 緯創": {
        "symbol": "3231.TW", "fallback_price": 145, "sector": "ODM",
        "base_identity": {"AI Server Platform": 40, "ODM": 40, "Cloud Infrastructure": 20},
        "fin": {"Revenue_CAGR": 18, "EPS_CAGR": 28, "ROIC": 16, "ROE": 20, "FCF_Margin": 6, "VDF_Exposure": 76, "Cycle_Score": 75, "Capex_Direction": 78, "Market_Multiple": 80},
        "identity_drift": {"2022": {"Notebook ODM": 70, "Server ODM": 30}, "2024": {"AI Server Platform": 45, "Notebook ODM": 40, "ODM": 15}, "2026": {"AI Server Platform": 58, "ODM": 25, "Cloud Infrastructure": 17}},
    },
    "6215 和椿": {
        "symbol": "6215.TWO", "fallback_price": 100.5, "sector": "Automation",
        "base_identity": {"Intelligent Automation": 45, "Robot Integrator": 35, "Industrial Equipment": 20},
        "fin": {"Revenue_CAGR": 18, "EPS_CAGR": 20, "ROIC": 14, "ROE": 12, "FCF_Margin": 8, "VDF_Exposure": 72, "Cycle_Score": 65, "Capex_Direction": 55, "Market_Multiple": 78},
        "identity_drift": {"2022": {"Industrial Equipment": 60, "Automation": 40}, "2024": {"Intelligent Automation": 40, "Industrial Equipment": 35, "Robot Integrator": 25}, "2026": {"Intelligent Automation": 55, "Robot Integrator": 30, "Industrial Equipment": 15}},
    },
    "2049 上銀": {
        "symbol": "2049.TW", "fallback_price": 318.5, "sector": "Automation",
        "base_identity": {"Intelligent Automation": 35, "Robot Component": 35, "Industrial Equipment": 30},
        "fin": {"Revenue_CAGR": 9, "EPS_CAGR": 8, "ROIC": 12, "ROE": 10, "FCF_Margin": 10, "VDF_Exposure": 55, "Cycle_Score": 55, "Capex_Direction": 45, "Market_Multiple": 60},
        "identity_drift": {"2022": {"Industrial Equipment": 55, "Robot Component": 35, "Intelligent Automation": 10}, "2024": {"Robot Component": 40, "Industrial Equipment": 35, "Intelligent Automation": 25}, "2026": {"Robot Component": 40, "Intelligent Automation": 35, "Industrial Equipment": 25}},
    },
    "4540 全球傳動": {
        "symbol": "4540.TW", "fallback_price": 55.6, "sector": "Automation",
        "base_identity": {"Robot Component": 40, "Industrial Equipment": 35, "Intelligent Automation": 25},
        "fin": {"Revenue_CAGR": 10, "EPS_CAGR": 8, "ROIC": 8, "ROE": 7, "FCF_Margin": 7, "VDF_Exposure": 45, "Cycle_Score": 58, "Capex_Direction": 40, "Market_Multiple": 55},
        "identity_drift": {"2022": {"Industrial Equipment": 60, "Robot Component": 30, "Intelligent Automation": 10}, "2024": {"Robot Component": 40, "Industrial Equipment": 40, "Intelligent Automation": 20}, "2026": {"Robot Component": 45, "Intelligent Automation": 30, "Industrial Equipment": 25}},
    },
    "2408 南亞科": {
        "symbol": "2408.TW", "fallback_price": 95, "sector": "Memory",
        "base_identity": {"Memory Cycle": 70, "Semiconductor": 20, "Commodity Tech": 10},
        "fin": {"Revenue_CAGR": 35, "EPS_CAGR": 45, "ROIC": 7, "ROE": 8, "FCF_Margin": -3, "VDF_Exposure": 45, "Cycle_Score": 88, "Capex_Direction": 65, "Market_Multiple": 82},
        "identity_drift": {"2022": {"Memory Cycle": 80, "Semiconductor": 20}, "2024": {"Memory Cycle": 75, "Commodity Tech": 15, "Semiconductor": 10}, "2026": {"Memory Cycle": 65, "Super Cycle": 25, "Semiconductor": 10}},
    },
    "2344 華邦電": {
        "symbol": "2344.TW", "fallback_price": 30, "sector": "Memory",
        "base_identity": {"Memory Cycle": 60, "Specialty Memory": 25, "Commodity Tech": 15},
        "fin": {"Revenue_CAGR": 20, "EPS_CAGR": 30, "ROIC": 6, "ROE": 7, "FCF_Margin": -5, "VDF_Exposure": 35, "Cycle_Score": 82, "Capex_Direction": 55, "Market_Multiple": 75},
        "identity_drift": {"2022": {"Memory Cycle": 70, "Specialty Memory": 20, "Commodity Tech": 10}, "2024": {"Memory Cycle": 65, "Specialty Memory": 25, "Commodity Tech": 10}, "2026": {"Memory Cycle": 60, "Specialty Memory": 25, "Super Cycle": 15}},
    },
    "2881 富邦金": {
        "symbol": "2881.TW", "fallback_price": 128.5, "sector": "Financial",
        "base_identity": {"Financial Franchise": 60, "Insurance Holding": 30, "Banking Holding": 10},
        "fin": {"Revenue_CAGR": 8, "EPS_CAGR": 12, "ROIC": 10, "ROE": 14, "FCF_Margin": 8, "VDF_Exposure": 5, "Cycle_Score": 55, "Capex_Direction": 10, "Market_Multiple": 50},
        "identity_drift": {"2022": {"Financial Franchise": 60, "Insurance Holding": 30, "Banking Holding": 10}, "2024": {"Financial Franchise": 62, "Insurance Holding": 28, "Banking Holding": 10}, "2026": {"Financial Franchise": 60, "Insurance Holding": 30, "Banking Holding": 10}},
    },
    "2891 中信金": {
        "symbol": "2891.TW", "fallback_price": 70.3, "sector": "Financial",
        "base_identity": {"Financial Franchise": 55, "Banking Holding": 35, "Insurance Holding": 10},
        "fin": {"Revenue_CAGR": 6, "EPS_CAGR": 9, "ROIC": 9, "ROE": 13, "FCF_Margin": 7, "VDF_Exposure": 5, "Cycle_Score": 52, "Capex_Direction": 10, "Market_Multiple": 48},
        "identity_drift": {"2022": {"Financial Franchise": 55, "Banking Holding": 35, "Insurance Holding": 10}, "2024": {"Financial Franchise": 56, "Banking Holding": 34, "Insurance Holding": 10}, "2026": {"Financial Franchise": 55, "Banking Holding": 35, "Insurance Holding": 10}},
    },
}

# ============================================================
# Build data
# ============================================================

rows, tree_rows, component_rows, drift_rows = [], [], [], []

for name, company in companies.items():
    price, price_source = fetch_price(company["symbol"], company["fallback_price"])
    fin = company["fin"]
    ids = cid_identity_scores(company, fin)
    trees = tree_scores(ids)
    old125 = confidence_v125(ids)
    old126 = confidence_v126(ids)
    new127, label, components = confidence_v127(ids, company, fin)

    main_identity = max(ids, key=ids.get)
    second_identity = list(ids.keys())[1] if len(ids) > 1 else ""
    main_tree = max(trees, key=trees.get)
    second_tree = list(trees.keys())[1] if len(trees) > 1 else ""

    rows.append({
        "公司": name,
        "代號": company["symbol"],
        "現價": price,
        "主身份": main_identity,
        "主身份分數": ids[main_identity],
        "副身份": second_identity,
        "副身份分數": ids.get(second_identity, 0),
        "主樹系": main_tree,
        "第二樹系": second_tree,
        "V12.5 Confidence": old125,
        "V12.6 Confidence": old126,
        "V12.7 Confidence": new127,
        "V12.7分級": label,
        "V12.6→V12.7": round(new127 - old126, 1),
        "Identity Drift": drift_direction(company),
        "身份分布": "、".join([f"{k}:{v}%" for k, v in ids.items()]),
        "樹系分布": "、".join([f"{k}:{v:.1f}%" for k, v in trees.items()]),
        "現價來源": price_source,
    })

    for tree, score in trees.items():
        tree_rows.append({"公司": name, "Identity Tree": tree, "Score": round(score, 1)})

    for k, v in components.items():
        component_rows.append({"公司": name, "Component": k, "Score": v})

    for year, dist in company.get("identity_drift", {}).items():
        for identity, score in dist.items():
            drift_rows.append({"公司": name, "年份": year, "Identity": identity, "Score": score})

df = pd.DataFrame(rows)
tree_df = pd.DataFrame(tree_rows)
component_df = pd.DataFrame(component_rows)
drift_df = pd.DataFrame(drift_rows)

summary = pd.DataFrame([
    {"指標": "樣本公司數", "V12.5": len(df), "V12.6": len(df), "V12.7": len(df)},
    {"指標": "平均Confidence", "V12.5": f"{round(df['V12.5 Confidence'].mean(),1)}%", "V12.6": f"{round(df['V12.6 Confidence'].mean(),1)}%", "V12.7": f"{round(df['V12.7 Confidence'].mean(),1)}%"},
    {"指標": ">=95分公司數", "V12.5": int((df["V12.5 Confidence"] >= 95).sum()), "V12.6": int((df["V12.6 Confidence"] >= 95).sum()), "V12.7": int((df["V12.7 Confidence"] >= 95).sum())},
    {"指標": "需人工確認數", "V12.5": int((df["V12.5 Confidence"] < 50).sum()), "V12.6": int((df["V12.6 Confidence"] < 50).sum()), "V12.7": int((df["V12.7 Confidence"] < 50).sum())},
    {"指標": "身份明確/偏明確數", "V12.5": int((df["V12.5 Confidence"] >= 65).sum()), "V12.6": int((df["V12.6 Confidence"] >= 65).sum()), "V12.7": int((df["V12.7 Confidence"] >= 65).sum())},
])

# ============================================================
# UI
# ============================================================

st.sidebar.header("V12.7 CID 控制台")
page = st.sidebar.radio(
    "功能",
    ["CID Overview", "Confidence 2.0 Compare", "Confidence Components", "Identity Tree View", "Identity Drift", "Company Detail", "Export JSON"]
)
selected_company = st.sidebar.selectbox("選擇公司", df["公司"].tolist())

st.sidebar.divider()
st.sidebar.metric("樣本公司", len(df))
st.sidebar.metric("平均Confidence", f"{round(df['V12.7 Confidence'].mean(),1)}%")
st.sidebar.metric(">=95分公司", int((df["V12.7 Confidence"] >= 95).sum()))

if page == "CID Overview":
    st.header("一、CID Overview")
    st.write("V12.7 把 V12.6 的過度補償壓回合理區間，避免太多公司直接變成 100 分。")
    st.dataframe(df, use_container_width=True)
    st.subheader("版本修正摘要")
    st.dataframe(summary, use_container_width=True)

elif page == "Confidence 2.0 Compare":
    st.header("二、Confidence 2.0 Compare")
    cols = ["公司", "主身份", "副身份", "主樹系", "V12.5 Confidence", "V12.6 Confidence", "V12.7 Confidence", "V12.7分級", "V12.6→V12.7"]
    st.dataframe(df[cols], use_container_width=True)
    st.bar_chart(df.set_index("公司")[["V12.5 Confidence", "V12.6 Confidence", "V12.7 Confidence"]])

elif page == "Confidence Components":
    st.header("三、Confidence Components")
    st.write("V12.7 Confidence = Tree Concentration + Identity Concentration + Drift Stability + Data Completeness。")
    st.dataframe(component_df, use_container_width=True)

    selected = component_df[component_df["公司"] == selected_company]
    if not selected.empty:
        st.subheader(f"{selected_company} Confidence Components")
        st.bar_chart(selected.set_index("Component")["Score"])

elif page == "Identity Tree View":
    st.header("四、Identity Tree View")
    st.write("同一樹系代表同價值鏈內的多重角色；跨樹系才代表真正衝突或轉型。")
    tree_map = [{"Identity Tree": k, "包含身份": "、".join(v)} for k, v in IDENTITY_TREE.items()]
    st.dataframe(pd.DataFrame(tree_map), use_container_width=True)

    st.subheader("公司樹系分布")
    st.dataframe(tree_df, use_container_width=True)

elif page == "Identity Drift":
    st.header("五、Identity Drift")
    st.dataframe(drift_df, use_container_width=True)
    selected = drift_df[drift_df["公司"] == selected_company]
    if not selected.empty:
        pivot = selected.pivot_table(index="年份", columns="Identity", values="Score", fill_value=0)
        st.subheader(f"{selected_company} Identity Drift Chart")
        st.line_chart(pivot)

elif page == "Company Detail":
    st.header("六、Company Detail")
    row = df[df["公司"] == selected_company].iloc[0]
    company_tree = tree_df[tree_df["公司"] == selected_company]
    comps = component_df[component_df["公司"] == selected_company]
    company = companies[selected_company]
    ids = cid_identity_scores(company, company["fin"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("主身份", row["主身份"])
    c2.metric("主樹系", row["主樹系"])
    c3.metric("V12.7 Confidence", f"{row['V12.7 Confidence']}%")
    c4.metric("分級", row["V12.7分級"])

    st.subheader("身份分布")
    st.dataframe(pd.DataFrame([{"Identity": k, "Score": v, "Tree": identity_tree_of(k)} for k, v in ids.items()]), use_container_width=True)

    st.subheader("樹系分布")
    st.dataframe(company_tree, use_container_width=True)

    st.subheader("Confidence Components")
    st.dataframe(comps, use_container_width=True)

    st.info(
        "V12.7 不再把同樹系身份直接推滿分，而是用集中度、漂移穩定度與資料完整度共同計算。"
        "這樣可避免廣達、上銀等多重身份公司被過度判定為100分。"
    )

elif page == "Export JSON":
    st.header("七、Export JSON")
    export = {
        "version": "V12.7 CID Confidence 2.0",
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "confidence_formula": {
            "Tree Concentration": 0.38,
            "Identity Concentration": 0.27,
            "Drift Stability": 0.20,
            "Data Completeness": 0.15,
            "Same Tree Bonus": "max +6",
            "Confidence Cap": 95
        },
        "cid_results": df.to_dict(orient="records"),
        "confidence_components": component_df.to_dict(orient="records"),
        "identity_tree": IDENTITY_TREE,
        "summary": summary.to_dict(orient="records")
    }
    st.code(json.dumps(export, ensure_ascii=False, indent=2), language="json")
