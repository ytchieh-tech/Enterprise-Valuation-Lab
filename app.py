import json
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

import pandas as pd
import streamlit as st

try:
    import yfinance as yf
except Exception:
    yf = None


# ============================================================
# Enterprise Valuation Lab V7
# Industry Batch Calibration Executor
# ============================================================

st.set_page_config(
    page_title="Enterprise Valuation Lab V7",
    page_icon="🏛️",
    layout="wide"
)

st.title("🏛️ Enterprise Valuation Lab")
st.subheader("V7｜產業批量校準執行器")
st.info("一次跑完四大母模型：AI Robot、PCB/CCL、AI Semiconductor、Financial，產出 PASS率、平均偏離、異常股與可擴散產業清單。")


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

@st.cache_data(ttl=900)
def fetch_price_yfinance(symbol: str, fallback_price: Optional[float] = None) -> Tuple[Optional[float], str]:
    candidates = []
    if symbol.endswith(".TW") or symbol.endswith(".TWO"):
        candidates.append(symbol)
        base = symbol.split(".")[0]
        candidates.append(base + (".TWO" if symbol.endswith(".TW") else ".TW"))
    else:
        candidates.extend([symbol + ".TW", symbol + ".TWO"])

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
                if price is not None and price > 0:
                    return float(price), f"yfinance 自動更新：{ticker}"
            except Exception:
                pass

    if fallback_price is not None:
        return float(fallback_price), "fallback 手動備援價"
    return None, "抓不到現價"


def weighted_valuation(model_scores: Dict[str, int], valuation: Dict[str, Dict[str, float]], top_n: int = 3):
    candidates = []
    for m, v in valuation.items():
        s = model_scores.get(m, 0)
        if s >= 60:
            candidates.append((m, s, v))
    candidates = sorted(candidates, key=lambda x: x[1], reverse=True)[:top_n]
    total = sum(s for _, s, _ in candidates)
    if total <= 0:
        return None, []
    out = {}
    for case in ["bear", "base", "bull"]:
        out[case] = sum(v[case] * s for _, s, v in candidates) / total
    weights = [(m, s, s / total) for m, s, _ in candidates]
    return out, weights


def status_from_gap(gap: Optional[float], tolerance: float) -> str:
    if gap is None:
        return "待校準"
    if abs(gap) <= tolerance:
        return "PASS"
    if abs(gap) <= tolerance * 1.5:
        return "WATCH"
    return "FAIL"


def fmt_num(x, digits=2):
    if x is None:
        return "N/A"
    return f"{x:,.{digits}f}"


def make_financials(eps, revenue, op_income, net_income, assets, equity, liabilities, cash, ocf, capex):
    return {
        "Revenue": revenue,
        "Operating_Income": op_income,
        "Net_Income": net_income,
        "EPS": eps,
        "Total_Assets": assets,
        "Equity": equity,
        "Total_Liabilities": liabilities,
        "Cash": cash,
        "Operating_Cash_Flow": ocf,
        "Capex": capex,
        "FCF": ocf - capex,
    }


def financial_completeness(fin):
    required = [
        "Revenue", "Operating_Income", "Net_Income", "EPS",
        "Total_Assets", "Equity", "Total_Liabilities", "Cash",
        "Operating_Cash_Flow", "Capex", "FCF"
    ]
    ok = 0
    for k in required:
        v = fin.get(k)
        if v is not None and v != "" and v != "N/A":
            ok += 1
    return round(ok / len(required) * 100)


# ------------------------------------------------------------
# Industry master models
# ------------------------------------------------------------

industries = {
    "AI Robot": {
        "version": "Robot Mother Model V1",
        "description": "AI機器人 / 自動化設備 / 智慧製造",
        "tolerance": 0.20,
        "candidate_models": ["AI Robot Premium", "Robot Growth", "Automation PE", "EV/Sales", "DCF-FCFF"],
        "production_rule": "平均偏離 <= 20%，FAIL = 0，允許進入機器人產業擴散。",
        "samples": ["6215 和椿", "2049 上銀", "4540 全球傳動"],
    },
    "PCB / CCL": {
        "version": "PCB/CCL Mother Model V1",
        "description": "PCB / 高階CCL / AI高速材料",
        "tolerance": 0.15,
        "candidate_models": ["AI Material Premium", "ROIC Premium", "DCF-FCFF", "PE", "EV/EBITDA"],
        "production_rule": "平均偏離 <= 15%，FAIL = 0，允許進入PCB/CCL產業擴散。",
        "samples": ["2383 台光電", "3037 欣興", "8046 南電", "3189 景碩"],
    },
    "AI Semiconductor": {
        "version": "AI Semiconductor Mother Model V1",
        "description": "AI半導體 / 晶圓代工 / IC設計",
        "tolerance": 0.15,
        "candidate_models": ["DCF-FCFF", "EVA", "EBO", "AI Premium", "Forward PE"],
        "production_rule": "平均偏離 <= 15%，FAIL = 0，允許進入半導體產業擴散。",
        "samples": ["2330 台積電", "2454 聯發科", "2303 聯電", "5347 世界先進"],
    },
    "Financial": {
        "version": "Financial Mother Model V1",
        "description": "金控 / 銀行 / 保險",
        "tolerance": 0.15,
        "candidate_models": ["PB-ROE", "Residual Income", "Dividend Yield"],
        "production_rule": "平均偏離 <= 15%，FAIL = 0，允許進入金融股擴散。",
        "samples": ["2881 富邦金", "2882 國泰金", "2891 中信金", "2886 兆豐金"],
    },
}


# ------------------------------------------------------------
# Company model database
# ------------------------------------------------------------

companies = {
    # AI Robot
    "6215 和椿": {
        "code": "6215", "symbol": "6215.TWO", "industry": "AI Robot", "fallback_price": 100.5,
        "financial": make_financials(2.8, 6200, 520, 360, 7800, 4100, 3700, 950, 420, 240),
        "model_scores": {"AI Robot Premium": 96, "Robot Growth": 94, "Automation PE": 90, "EV/Sales": 82, "DCF-FCFF": 68},
        "valuation": {
            "AI Robot Premium": {"bear": 86, "base": 98, "bull": 122},
            "Robot Growth": {"bear": 82, "base": 95, "bull": 118},
            "Automation PE": {"bear": 78, "base": 92, "bull": 112},
            "EV/Sales": {"bear": 72, "base": 88, "bull": 108},
            "DCF-FCFF": {"bear": 65, "base": 78, "bull": 95},
        },
    },
    "2049 上銀": {
        "code": "2049", "symbol": "2049.TW", "industry": "AI Robot", "fallback_price": 318.5,
        "financial": make_financials(7.5, 28000, 3600, 2400, 78000, 36000, 42000, 7200, 3900, 1700),
        "model_scores": {"Robot Growth": 88, "Automation PE": 86, "AI Robot Premium": 82, "EV/Sales": 76, "DCF-FCFF": 72},
        "valuation": {
            "Robot Growth": {"bear": 260, "base": 326, "bull": 390},
            "Automation PE": {"bear": 250, "base": 315, "bull": 370},
            "AI Robot Premium": {"bear": 270, "base": 338, "bull": 410},
            "EV/Sales": {"bear": 235, "base": 300, "bull": 360},
            "DCF-FCFF": {"bear": 220, "base": 285, "bull": 345},
        },
    },
    "4540 全球傳動": {
        "code": "4540", "symbol": "4540.TW", "industry": "AI Robot", "fallback_price": 55.6,
        "financial": make_financials(1.4, 4200, 260, 150, 7600, 3000, 4600, 520, 280, 160),
        "model_scores": {"Automation PE": 84, "Robot Growth": 82, "EV/Sales": 78, "AI Robot Premium": 75, "DCF-FCFF": 62},
        "valuation": {
            "Automation PE": {"bear": 45, "base": 56, "bull": 68},
            "Robot Growth": {"bear": 48, "base": 59, "bull": 72},
            "EV/Sales": {"bear": 42, "base": 54, "bull": 66},
            "AI Robot Premium": {"bear": 50, "base": 61, "bull": 75},
            "DCF-FCFF": {"bear": 38, "base": 49, "bull": 60},
        },
    },

    # PCB / CCL
    "2383 台光電": {
        "code": "2383", "symbol": "2383.TW", "industry": "PCB / CCL", "fallback_price": 5450,
        "financial": make_financials(75, 95000, 28000, 22000, 165000, 72000, 93000, 22000, 26000, 9000),
        "model_scores": {"AI Material Premium": 96, "ROIC Premium": 92, "DCF-FCFF": 86, "PE": 84, "EV/EBITDA": 78},
        "valuation": {
            "AI Material Premium": {"bear": 4500, "base": 5600, "bull": 6800},
            "ROIC Premium": {"bear": 4300, "base": 5400, "bull": 6500},
            "DCF-FCFF": {"bear": 3900, "base": 5100, "bull": 6200},
            "PE": {"bear": 4000, "base": 5250, "bull": 6400},
            "EV/EBITDA": {"bear": 3800, "base": 5000, "bull": 6100},
        },
    },
    "3037 欣興": {
        "code": "3037", "symbol": "3037.TW", "industry": "PCB / CCL", "fallback_price": 976,
        "financial": make_financials(18, 160000, 26000, 19000, 330000, 155000, 175000, 36000, 38000, 19000),
        "model_scores": {"ROIC Premium": 88, "AI Material Premium": 86, "DCF-FCFF": 82, "PE": 78, "EV/EBITDA": 76},
        "valuation": {
            "ROIC Premium": {"bear": 800, "base": 980, "bull": 1180},
            "AI Material Premium": {"bear": 840, "base": 1010, "bull": 1220},
            "DCF-FCFF": {"bear": 760, "base": 940, "bull": 1120},
            "PE": {"bear": 780, "base": 955, "bull": 1150},
            "EV/EBITDA": {"bear": 740, "base": 920, "bull": 1100},
        },
    },
    "8046 南電": {
        "code": "8046", "symbol": "8046.TW", "industry": "PCB / CCL", "fallback_price": 360,
        "financial": make_financials(12, 52000, 8200, 6100, 120000, 53000, 67000, 13000, 12500, 6200),
        "model_scores": {"ROIC Premium": 86, "AI Material Premium": 82, "DCF-FCFF": 78, "PE": 76, "EV/EBITDA": 74},
        "valuation": {
            "ROIC Premium": {"bear": 300, "base": 365, "bull": 430},
            "AI Material Premium": {"bear": 310, "base": 380, "bull": 450},
            "DCF-FCFF": {"bear": 280, "base": 345, "bull": 410},
            "PE": {"bear": 285, "base": 350, "bull": 420},
            "EV/EBITDA": {"bear": 275, "base": 340, "bull": 405},
        },
    },
    "3189 景碩": {
        "code": "3189", "symbol": "3189.TW", "industry": "PCB / CCL", "fallback_price": 125,
        "financial": make_financials(5.2, 34000, 3600, 2500, 98000, 44000, 54000, 8500, 7200, 3800),
        "model_scores": {"DCF-FCFF": 82, "ROIC Premium": 78, "PE": 76, "EV/EBITDA": 72, "AI Material Premium": 68},
        "valuation": {
            "DCF-FCFF": {"bear": 100, "base": 123, "bull": 150},
            "ROIC Premium": {"bear": 105, "base": 128, "bull": 155},
            "PE": {"bear": 98, "base": 120, "bull": 145},
            "EV/EBITDA": {"bear": 95, "base": 118, "bull": 142},
            "AI Material Premium": {"bear": 110, "base": 135, "bull": 160},
        },
    },

    # AI Semiconductor
    "2330 台積電": {
        "code": "2330", "symbol": "2330.TW", "industry": "AI Semiconductor", "fallback_price": 2340,
        "financial": make_financials(85, 3000000, 1350000, 1100000, 6500000, 4100000, 2400000, 1800000, 1550000, 900000),
        "model_scores": {"DCF-FCFF": 94, "EVA": 90, "AI Premium": 86, "EBO": 78, "Forward PE": 74},
        "valuation": {
            "DCF-FCFF": {"bear": 1750, "base": 2100, "bull": 2450},
            "EVA": {"bear": 1650, "base": 2050, "bull": 2400},
            "AI Premium": {"bear": 2050, "base": 2480, "bull": 2850},
            "EBO": {"bear": 1550, "base": 1900, "bull": 2250},
            "Forward PE": {"bear": 1800, "base": 2200, "bull": 2600},
        },
    },
    "2454 聯發科": {
        "code": "2454", "symbol": "2454.TW", "industry": "AI Semiconductor", "fallback_price": 1500,
        "financial": make_financials(70, 560000, 130000, 110000, 820000, 560000, 260000, 260000, 130000, 25000),
        "model_scores": {"Forward PE": 90, "EVA": 86, "DCF-FCFF": 82, "EBO": 78, "AI Premium": 74},
        "valuation": {
            "Forward PE": {"bear": 1200, "base": 1500, "bull": 1800},
            "EVA": {"bear": 1150, "base": 1450, "bull": 1750},
            "DCF-FCFF": {"bear": 1100, "base": 1400, "bull": 1700},
            "EBO": {"bear": 1080, "base": 1350, "bull": 1650},
            "AI Premium": {"bear": 1250, "base": 1550, "bull": 1900},
        },
    },
    "2303 聯電": {
        "code": "2303", "symbol": "2303.TW", "industry": "AI Semiconductor", "fallback_price": 45,
        "financial": make_financials(3.6, 220000, 52000, 43000, 600000, 380000, 220000, 120000, 76000, 42000),
        "model_scores": {"DCF-FCFF": 88, "EVA": 84, "EBO": 80, "Forward PE": 76, "PB-ROE": 72},
        "valuation": {
            "DCF-FCFF": {"bear": 38, "base": 46, "bull": 55},
            "EVA": {"bear": 36, "base": 44, "bull": 53},
            "EBO": {"bear": 37, "base": 45, "bull": 54},
            "Forward PE": {"bear": 35, "base": 43, "bull": 52},
            "PB-ROE": {"bear": 34, "base": 42, "bull": 50},
        },
    },
    "5347 世界先進": {
        "code": "5347", "symbol": "5347.TWO", "industry": "AI Semiconductor", "fallback_price": 100,
        "financial": make_financials(4.8, 52000, 13000, 9500, 130000, 82000, 48000, 26000, 18000, 9000),
        "model_scores": {"DCF-FCFF": 88, "EVA": 86, "EBO": 82, "Forward PE": 80, "PB-ROE": 72},
        "valuation": {
            "DCF-FCFF": {"bear": 80, "base": 98, "bull": 118},
            "EVA": {"bear": 82, "base": 100, "bull": 120},
            "EBO": {"bear": 78, "base": 96, "bull": 116},
            "Forward PE": {"bear": 76, "base": 94, "bull": 114},
            "PB-ROE": {"bear": 74, "base": 92, "bull": 110},
        },
    },

    # Financial
    "2881 富邦金": {
        "code": "2881", "symbol": "2881.TW", "industry": "Financial", "fallback_price": 130,
        "financial": make_financials(10.5, 900000, 150000, 120000, 12000000, 900000, 11100000, 800000, 0, 0),
        "model_scores": {"PB-ROE": 96, "Residual Income": 91, "Dividend Yield": 85},
        "valuation": {
            "PB-ROE": {"bear": 112, "base": 132, "bull": 152},
            "Residual Income": {"bear": 108, "base": 128, "bull": 148},
            "Dividend Yield": {"bear": 104, "base": 124, "bull": 142},
        },
    },
    "2882 國泰金": {
        "code": "2882", "symbol": "2882.TW", "industry": "Financial", "fallback_price": 70,
        "financial": make_financials(6.2, 820000, 120000, 95000, 11500000, 760000, 10740000, 720000, 0, 0),
        "model_scores": {"PB-ROE": 94, "Residual Income": 90, "Dividend Yield": 84},
        "valuation": {
            "PB-ROE": {"bear": 58, "base": 70, "bull": 82},
            "Residual Income": {"bear": 56, "base": 68, "bull": 80},
            "Dividend Yield": {"bear": 54, "base": 66, "bull": 78},
        },
    },
    "2891 中信金": {
        "code": "2891", "symbol": "2891.TW", "industry": "Financial", "fallback_price": 42,
        "financial": make_financials(3.4, 430000, 90000, 70000, 8800000, 520000, 8280000, 450000, 0, 0),
        "model_scores": {"PB-ROE": 94, "Residual Income": 88, "Dividend Yield": 86},
        "valuation": {
            "PB-ROE": {"bear": 35, "base": 42, "bull": 49},
            "Residual Income": {"bear": 34, "base": 41, "bull": 48},
            "Dividend Yield": {"bear": 33, "base": 40, "bull": 47},
        },
    },
    "2886 兆豐金": {
        "code": "2886", "symbol": "2886.TW", "industry": "Financial", "fallback_price": 40,
        "financial": make_financials(2.8, 260000, 68000, 52000, 5200000, 420000, 4780000, 320000, 0, 0),
        "model_scores": {"PB-ROE": 92, "Residual Income": 88, "Dividend Yield": 86},
        "valuation": {
            "PB-ROE": {"bear": 33, "base": 40, "bull": 47},
            "Residual Income": {"bear": 32, "base": 39, "bull": 46},
            "Dividend Yield": {"bear": 31, "base": 38, "bull": 45},
        },
    },
}


# ------------------------------------------------------------
# Compute results
# ------------------------------------------------------------

def compute_company(name: str):
    c = companies[name]
    ind = industries[c["industry"]]
    price, price_source = fetch_price_yfinance(c["symbol"], c["fallback_price"])
    valuation, weights = weighted_valuation(c["model_scores"], c["valuation"], top_n=3)
    gap = None
    if valuation and price:
        gap = valuation["base"] / price - 1
    status = status_from_gap(gap, ind["tolerance"])
    return {
        "公司": name,
        "代號": c["symbol"],
        "產業": c["industry"],
        "現價": price,
        "現價來源": price_source,
        "財報完整度": financial_completeness(c["financial"]),
        "Top模型": "、".join([m for m, _, _ in weights]),
        "Bear": None if valuation is None else round(valuation["bear"], 2),
        "Base": None if valuation is None else round(valuation["base"], 2),
        "Bull": None if valuation is None else round(valuation["bull"], 2),
        "偏離%": None if gap is None else round(gap * 100, 1),
        "校準狀態": status,
    }


def compute_industry(industry_name: str):
    ind = industries[industry_name]
    rows = [compute_company(n) for n in ind["samples"]]
    gaps = [abs(r["偏離%"]) for r in rows if r["偏離%"] is not None]
    avg_gap = None if not gaps else round(sum(gaps) / len(gaps), 1)
    pass_count = sum(r["校準狀態"] == "PASS" for r in rows)
    watch_count = sum(r["校準狀態"] == "WATCH" for r in rows)
    fail_count = sum(r["校準狀態"] == "FAIL" for r in rows)
    pass_rate = round(pass_count / len(rows) * 100, 1) if rows else 0
    avg_fin = round(sum(r["財報完整度"] for r in rows) / len(rows), 1)

    if fail_count == 0 and avg_gap is not None and avg_gap <= ind["tolerance"] * 100:
        status = "PASS｜可擴散"
    elif fail_count <= 1 and avg_gap is not None and avg_gap <= ind["tolerance"] * 150:
        status = "WATCH｜先檢查異常股"
    else:
        status = "FAIL｜不可擴散"

    return {
        "產業": industry_name,
        "版本": ind["version"],
        "樣本數": len(rows),
        "平均偏離%": avg_gap,
        "PASS率%": pass_rate,
        "PASS數": pass_count,
        "WATCH數": watch_count,
        "FAIL數": fail_count,
        "平均財報完整度": avg_fin,
        "狀態": status,
        "rows": rows,
    }


industry_results = [compute_industry(ind) for ind in industries]
industry_summary = pd.DataFrame([{k: v for k, v in r.items() if k != "rows"} for r in industry_results])
all_rows = []
for r in industry_results:
    all_rows.extend(r["rows"])
all_df = pd.DataFrame(all_rows)


# ------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------

st.sidebar.header("V7 控制台")
selected_industry = st.sidebar.selectbox("檢視產業", list(industries.keys()))
view_mode = st.sidebar.radio("顯示篩選", ["全部", "只看異常股", "只看可擴散產業"], index=0)

st.sidebar.divider()
st.sidebar.metric("產業母模型", len(industries))
st.sidebar.metric("樣本公司", len(all_df))
pass_industries = sum("可擴散" in r["狀態"] for r in industry_results)
st.sidebar.metric("可擴散產業", f"{pass_industries}/{len(industries)}")
overall_gap = round(all_df["偏離%"].abs().mean(), 1)
st.sidebar.metric("整體平均偏離", f"{overall_gap}%")


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

st.header("一、四大母模型批量校準總覽")
display_summary = industry_summary.copy()
if view_mode == "只看可擴散產業":
    display_summary = display_summary[display_summary["狀態"].str.contains("可擴散")]
st.dataframe(display_summary, use_container_width=True)

st.header("二、全樣本公司批量結果")
display_df = all_df.copy()
if view_mode == "只看異常股":
    display_df = display_df[display_df["校準狀態"].isin(["WATCH", "FAIL"])]
elif view_mode == "只看可擴散產業":
    ok_industries = industry_summary[industry_summary["狀態"].str.contains("可擴散")]["產業"].tolist()
    display_df = display_df[display_df["產業"].isin(ok_industries)]
st.dataframe(display_df, use_container_width=True)

st.header("三、選定產業細節")
selected = compute_industry(selected_industry)
ind = industries[selected_industry]

c1, c2, c3, c4 = st.columns(4)
c1.metric("產業", selected_industry)
c2.metric("平均偏離", "N/A" if selected["平均偏離%"] is None else f"{selected['平均偏離%']}%")
c3.metric("PASS率", f"{selected['PASS率%']}%")
c4.metric("狀態", selected["狀態"])

st.write("模型池：")
st.code("、".join(ind["candidate_models"]))
st.caption(ind["production_rule"])
st.dataframe(pd.DataFrame(selected["rows"]), use_container_width=True)

st.header("四、異常股偵測")
abnormal = all_df[all_df["校準狀態"].isin(["WATCH", "FAIL"])]
if abnormal.empty:
    st.success("目前沒有異常股。四大母模型皆可進一步檢視是否進入全產業擴散。")
else:
    st.warning("以下股票需優先討論，不建議直接批量擴散：")
    st.dataframe(abnormal, use_container_width=True)

st.header("五、可擴散產業清單")
spreadable = industry_summary[industry_summary["狀態"].str.contains("可擴散")]
if spreadable.empty:
    st.warning("目前沒有產業達到可擴散條件。")
else:
    st.success("以下產業已達可擴散條件：")
    st.dataframe(spreadable[["產業", "版本", "平均偏離%", "PASS率%", "平均財報完整度", "狀態"]], use_container_width=True)

st.header("六、公司細節檢視")
selected_company = st.selectbox("選擇公司", list(companies.keys()))
c = companies[selected_company]
company_result = compute_company(selected_company)
valuation, weights = weighted_valuation(c["model_scores"], c["valuation"], top_n=3)

col1, col2, col3, col4 = st.columns(4)
col1.metric("現價", fmt_num(company_result["現價"]))
col2.metric("Base", "N/A" if company_result["Base"] is None else fmt_num(company_result["Base"]))
col3.metric("偏離", "N/A" if company_result["偏離%"] is None else f"{company_result['偏離%']}%")
col4.metric("狀態", company_result["校準狀態"])

st.subheader("Top 模型與權重")
if weights:
    weight_df = pd.DataFrame([
        {"模型": m, "分數": s, "權重%": round(w * 100, 1)}
        for m, s, w in weights
    ])
    st.dataframe(weight_df, use_container_width=True)

st.subheader("模型分數")
score_df = pd.DataFrame([
    {"模型": m, "分數": s}
    for m, s in sorted(c["model_scores"].items(), key=lambda x: x[1], reverse=True)
])
st.dataframe(score_df, use_container_width=True)

st.header("七、匯出 JSON")
export = {
    "version": "V7 Industry Batch Calibration Executor",
    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "industry_summary": industry_summary.to_dict(orient="records"),
    "company_results": all_df.to_dict(orient="records"),
}
st.code(json.dumps(export, ensure_ascii=False, indent=2), language="json")
