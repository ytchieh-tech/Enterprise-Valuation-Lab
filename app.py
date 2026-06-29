import json
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List

import pandas as pd
import streamlit as st

try:
    import yfinance as yf
except Exception:
    yf = None


# ============================================================
# Enterprise Valuation Lab V6.3
# Industry Batch Calibration Engine｜產業批量校準引擎
# ============================================================

st.set_page_config(
    page_title="Enterprise Valuation Lab V6.3",
    page_icon="🏛️",
    layout="wide"
)

st.title("🏛️ Enterprise Valuation Lab")
st.subheader("V6.3｜Industry Batch Calibration Engine：產業批量校準 + 異常股偵測")
st.info(
    "本版重點：在財報完整度通過後，開始對母模型樣本股批量估值，"
    "先檢查 AI Robot、PCB/CCL、AI Semiconductor、Financial 四大母模型是否可進入量產。"
)

# ------------------------------------------------------------
# Settings
# ------------------------------------------------------------

st.sidebar.header("Industry Batch Calibration")
data_mode = st.sidebar.radio("財報資料模式", ["fallback 備援資料", "貼上財報狗 JSON"], index=0)
selected_industry = st.sidebar.selectbox(
    "選擇產業母模型",
    ["AI Robot", "PCB / CCL", "AI Semiconductor", "Financial"]
)

st.sidebar.caption("V6.3：先看產業是否 PASS，再抓異常股討論。")


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


def parse_statementdog_json(raw: str) -> Dict[str, Any]:
    if not raw.strip():
        return {}
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    return {}


def weighted_valuation(model_scores: Dict[str, int], valuation: Dict[str, Dict[str, float]], top_n: int = 3):
    candidates = []
    for m, v in valuation.items():
        score = model_scores.get(m, 0)
        if score >= 60:
            candidates.append((m, score, v))
    candidates = sorted(candidates, key=lambda x: x[1], reverse=True)[:top_n]
    total = sum(s for _, s, _ in candidates)
    if not candidates or total <= 0:
        return None, []
    result = {}
    for case in ["bear", "base", "bull"]:
        result[case] = sum(v[case] * s for _, s, v in candidates) / total
    weights = [(m, s, s / total) for m, s, _ in candidates]
    return result, weights


def calibration_status(base: Optional[float], price: Optional[float], tolerance: float):
    if base is None or price is None or price <= 0:
        return "待校準", None
    gap = base / price - 1
    if abs(gap) <= tolerance:
        return "PASS", gap
    if abs(gap) <= tolerance * 1.5:
        return "WATCH", gap
    return "FAIL", gap


def score_status(status: str) -> int:
    return {"PASS": 1, "WATCH": 0, "FAIL": -1, "待校準": 0}.get(status, 0)


def rating(score: float) -> str:
    if score >= 90:
        return "S 核心模型"
    if score >= 80:
        return "A 強烈推薦"
    if score >= 70:
        return "B 可用"
    if score >= 60:
        return "C 觀察"
    return "D 淘汰"


def financial_completeness(fin: Dict[str, Any]) -> int:
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


def fmt(x, digits=2):
    if x is None:
        return "N/A"
    try:
        return f"{float(x):,.{digits}f}"
    except Exception:
        return str(x)


# ------------------------------------------------------------
# Industry mother models
# ------------------------------------------------------------

industries = {
    "AI Robot": {
        "description": "AI機器人 / 自動化設備 / 智慧製造",
        "tolerance": 0.20,
        "required_financial_score": 95,
        "candidate_models": ["AI Robot Premium", "Robot Growth", "Automation PE", "EV/Sales", "DCF-FCFF"],
        "production_rule": "平均誤差 <= 20%，且 FAIL 數 = 0，才允許批量導入整個機器人產業。",
        "samples": ["6215 和椿", "2049 上銀", "4540 全球傳動"],
    },
    "PCB / CCL": {
        "description": "PCB / 高階CCL / AI高速材料",
        "tolerance": 0.15,
        "required_financial_score": 95,
        "candidate_models": ["AI Material Premium", "ROIC Premium", "DCF-FCFF", "PE", "EV/EBITDA"],
        "production_rule": "平均誤差 <= 15%，且 FAIL 數 = 0，才允許批量導入 PCB / CCL 產業。",
        "samples": ["2383 台光電", "3037 欣興", "8046 南電", "3189 景碩"],
    },
    "AI Semiconductor": {
        "description": "AI半導體 / 晶圓代工 / IC設計",
        "tolerance": 0.15,
        "required_financial_score": 98,
        "candidate_models": ["DCF-FCFF", "EVA", "EBO", "AI Premium", "Forward PE"],
        "production_rule": "平均誤差 <= 15%，且 FAIL 數 = 0，才允許批量導入半導體產業。",
        "samples": ["2330 台積電", "2454 聯發科", "2303 聯電", "5347 世界先進"],
    },
    "Financial": {
        "description": "金控 / 銀行 / 保險",
        "tolerance": 0.15,
        "required_financial_score": 95,
        "candidate_models": ["PB-ROE", "Residual Income", "Dividend Yield"],
        "production_rule": "平均誤差 <= 15%，且 FAIL 數 = 0，才允許批量導入金融股。",
        "samples": ["2881 富邦金", "2882 國泰金", "2891 中信金", "2886 兆豐金"],
    },
}


# ------------------------------------------------------------
# Company database
# Valuations are mother-model calibration ranges.
# They are intended to test whether industry model can explain current price.
# ------------------------------------------------------------

companies = {
    # AI Robot
    "6215 和椿": {
        "code": "6215", "symbol": "6215.TWO", "industry": "AI Robot", "fallback_price": 100.5,
        "financial": make_financials(2.8, 6200, 520, 360, 7800, 4100, 3700, 950, 420, 240),
        "model_scores": {
            "AI Robot Premium": 96, "Robot Growth": 94, "Automation PE": 90, "EV/Sales": 82, "DCF-FCFF": 68
        },
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
        "model_scores": {
            "Robot Growth": 88, "Automation PE": 86, "AI Robot Premium": 82, "EV/Sales": 76, "DCF-FCFF": 72
        },
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
        "model_scores": {
            "Automation PE": 84, "Robot Growth": 82, "EV/Sales": 78, "AI Robot Premium": 75, "DCF-FCFF": 62
        },
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
        "model_scores": {
            "AI Material Premium": 96, "ROIC Premium": 92, "DCF-FCFF": 86, "PE": 84, "EV/EBITDA": 78
        },
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
        "model_scores": {
            "ROIC Premium": 88, "AI Material Premium": 86, "DCF-FCFF": 82, "PE": 78, "EV/EBITDA": 76
        },
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
        "model_scores": {
            "ROIC Premium": 86, "AI Material Premium": 82, "DCF-FCFF": 78, "PE": 76, "EV/EBITDA": 74
        },
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
        "model_scores": {
            "DCF-FCFF": 82, "ROIC Premium": 78, "PE": 76, "EV/EBITDA": 72, "AI Material Premium": 68
        },
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
        "model_scores": {
            "DCF-FCFF": 94, "EVA": 90, "AI Premium": 86, "EBO": 78, "Forward PE": 74
        },
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
        "model_scores": {
            "Forward PE": 90, "EVA": 86, "DCF-FCFF": 82, "EBO": 78, "AI Premium": 74
        },
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
        "model_scores": {
            "DCF-FCFF": 88, "EVA": 84, "EBO": 80, "PE": 76, "PB-ROE": 72
        },
        "valuation": {
            "DCF-FCFF": {"bear": 38, "base": 46, "bull": 55},
            "EVA": {"bear": 36, "base": 44, "bull": 53},
            "EBO": {"bear": 37, "base": 45, "bull": 54},
            "PE": {"bear": 35, "base": 43, "bull": 52},
            "PB-ROE": {"bear": 34, "base": 42, "bull": 50},
        },
    },
    "5347 世界先進": {
        "code": "5347", "symbol": "5347.TWO", "industry": "AI Semiconductor", "fallback_price": 100,
        "financial": make_financials(4.8, 52000, 13000, 9500, 130000, 82000, 48000, 26000, 18000, 9000),
        "model_scores": {
            "DCF-FCFF": 88, "EVA": 86, "EBO": 82, "PE": 80, "PB-ROE": 72
        },
        "valuation": {
            "DCF-FCFF": {"bear": 80, "base": 98, "bull": 118},
            "EVA": {"bear": 82, "base": 100, "bull": 120},
            "EBO": {"bear": 78, "base": 96, "bull": 116},
            "PE": {"bear": 76, "base": 94, "bull": 114},
            "PB-ROE": {"bear": 74, "base": 92, "bull": 110},
        },
    },

    # Financial
    "2881 富邦金": {
        "code": "2881", "symbol": "2881.TW", "industry": "Financial", "fallback_price": 130,
        "financial": make_financials(10.5, 900000, 150000, 120000, 12000000, 900000, 11100000, 800000, 0, 0),
        "model_scores": {
            "PB-ROE": 96, "Residual Income": 91, "Dividend Yield": 85
        },
        "valuation": {
            "PB-ROE": {"bear": 112, "base": 132, "bull": 152},
            "Residual Income": {"bear": 108, "base": 128, "bull": 148},
            "Dividend Yield": {"bear": 104, "base": 124, "bull": 142},
        },
    },
    "2882 國泰金": {
        "code": "2882", "symbol": "2882.TW", "industry": "Financial", "fallback_price": 70,
        "financial": make_financials(6.2, 820000, 120000, 95000, 11500000, 760000, 10740000, 720000, 0, 0),
        "model_scores": {
            "PB-ROE": 94, "Residual Income": 90, "Dividend Yield": 84
        },
        "valuation": {
            "PB-ROE": {"bear": 58, "base": 70, "bull": 82},
            "Residual Income": {"bear": 56, "base": 68, "bull": 80},
            "Dividend Yield": {"bear": 54, "base": 66, "bull": 78},
        },
    },
    "2891 中信金": {
        "code": "2891", "symbol": "2891.TW", "industry": "Financial", "fallback_price": 42,
        "financial": make_financials(3.4, 430000, 90000, 70000, 8800000, 520000, 8280000, 450000, 0, 0),
        "model_scores": {
            "PB-ROE": 94, "Residual Income": 88, "Dividend Yield": 86
        },
        "valuation": {
            "PB-ROE": {"bear": 35, "base": 42, "bull": 49},
            "Residual Income": {"bear": 34, "base": 41, "bull": 48},
            "Dividend Yield": {"bear": 33, "base": 40, "bull": 47},
        },
    },
    "2886 兆豐金": {
        "code": "2886", "symbol": "2886.TW", "industry": "Financial", "fallback_price": 40,
        "financial": make_financials(2.8, 260000, 68000, 52000, 5200000, 420000, 4780000, 320000, 0, 0),
        "model_scores": {
            "PB-ROE": 92, "Residual Income": 88, "Dividend Yield": 86
        },
        "valuation": {
            "PB-ROE": {"bear": 33, "base": 40, "bull": 47},
            "Residual Income": {"bear": 32, "base": 39, "bull": 46},
            "Dividend Yield": {"bear": 31, "base": 38, "bull": 45},
        },
    },
}


# ------------------------------------------------------------
# Optional StatementDog JSON input
# ------------------------------------------------------------

statementdog_data = {}
if data_mode == "貼上財報狗 JSON":
    st.sidebar.subheader("貼上財報狗 JSON")
    raw_json = st.sidebar.text_area(
        "格式：以股票代號為 key",
        height=240,
        placeholder='{"6215":{"Revenue":6200,"Operating_Income":520,"Net_Income":360,"EPS":2.8,"Total_Assets":7800,"Equity":4100,"Total_Liabilities":3700,"Cash":950,"Operating_Cash_Flow":420,"Capex":240,"FCF":180}}'
    )
    statementdog_data = parse_statementdog_json(raw_json)
    if raw_json.strip() and not statementdog_data:
        st.sidebar.error("JSON 解析失敗，請檢查格式。")


def get_financials(company):
    fin = company["financial"].copy()
    code = company["code"]
    source = "內建 / fallback 財報因子"
    if data_mode == "貼上財報狗 JSON" and code in statementdog_data:
        fin.update(statementdog_data[code])
        source = "財報狗 JSON 貼上資料"
    return fin, source


# ------------------------------------------------------------
# Batch calibration functions
# ------------------------------------------------------------

def compute_company_result(name: str) -> Dict[str, Any]:
    c = companies[name]
    ind = industries[c["industry"]]
    price, price_source = fetch_price_yfinance(c["symbol"], c["fallback_price"])
    fin, fin_source = get_financials(c)
    fscore = financial_completeness(fin)
    valuation, weights = weighted_valuation(c["model_scores"], c["valuation"], top_n=3)
    status, gap = calibration_status(valuation["base"] if valuation else None, price, ind["tolerance"])
    return {
        "公司": name,
        "代號": c["symbol"],
        "產業": c["industry"],
        "現價": price,
        "現價來源": price_source,
        "財報來源": fin_source,
        "財報完整度": fscore,
        "Top模型": "、".join([m for m, _, _ in weights]) if weights else "",
        "Bear": None if not valuation else round(valuation["bear"], 2),
        "Base": None if not valuation else round(valuation["base"], 2),
        "Bull": None if not valuation else round(valuation["bull"], 2),
        "偏離%": None if gap is None else round(gap * 100, 1),
        "校準狀態": status,
    }


def compute_industry_summary(industry_name: str) -> Dict[str, Any]:
    samples = industries[industry_name]["samples"]
    results = [compute_company_result(name) for name in samples]
    gaps = [abs(r["偏離%"]) for r in results if r["偏離%"] is not None]
    avg_gap = round(sum(gaps) / len(gaps), 1) if gaps else None
    pass_count = sum(1 for r in results if r["校準狀態"] == "PASS")
    watch_count = sum(1 for r in results if r["校準狀態"] == "WATCH")
    fail_count = sum(1 for r in results if r["校準狀態"] == "FAIL")
    avg_fin = round(sum(r["財報完整度"] for r in results) / len(results), 1) if results else 0

    tol_pct = industries[industry_name]["tolerance"] * 100
    if fail_count == 0 and avg_gap is not None and avg_gap <= tol_pct and avg_fin >= industries[industry_name]["required_financial_score"]:
        status = "產業模型 PASS"
    elif fail_count <= 1 and avg_gap is not None and avg_gap <= tol_pct * 1.5:
        status = "產業模型 WATCH"
    else:
        status = "產業模型 FAIL"

    return {
        "產業": industry_name,
        "樣本數": len(results),
        "平均偏離%": avg_gap,
        "PASS數": pass_count,
        "WATCH數": watch_count,
        "FAIL數": fail_count,
        "平均財報完整度": avg_fin,
        "容忍度%": tol_pct,
        "狀態": status,
        "results": results,
    }


# ------------------------------------------------------------
# Sidebar summary
# ------------------------------------------------------------

all_summaries = [compute_industry_summary(ind) for ind in industries]
summary_df = pd.DataFrame([{k: v for k, v in s.items() if k != "results"} for s in all_summaries])

selected_summary = compute_industry_summary(selected_industry)
selected_results = selected_summary["results"]
selected_df = pd.DataFrame(selected_results)

st.sidebar.divider()
st.sidebar.metric("產業母模型數", len(industries))
st.sidebar.metric("樣本公司總數", sum(len(v["samples"]) for v in industries.values()))
st.sidebar.metric("目前產業狀態", selected_summary["狀態"])
if selected_summary["平均偏離%"] is not None:
    st.sidebar.metric("平均偏離", f"{selected_summary['平均偏離%']}%")


# ------------------------------------------------------------
# Main page
# ------------------------------------------------------------

st.header("一、產業母模型總覽")
st.dataframe(summary_df, use_container_width=True)

st.header("二、選定產業批量校準")
ind = industries[selected_industry]

c1, c2, c3, c4 = st.columns(4)
c1.metric("產業", selected_industry)
c2.metric("樣本數", selected_summary["樣本數"])
c3.metric("平均偏離", "N/A" if selected_summary["平均偏離%"] is None else f"{selected_summary['平均偏離%']}%")
c4.metric("狀態", selected_summary["狀態"])

st.write("產業說明：", ind["description"])
st.write("模型池：")
st.code("、".join(ind["candidate_models"]))
st.caption(ind["production_rule"])

st.subheader("樣本股批量校準表")
st.dataframe(selected_df, use_container_width=True)

st.header("三、異常股偵測")
abnormal_df = selected_df[selected_df["校準狀態"].isin(["WATCH", "FAIL"])]
if abnormal_df.empty:
    st.success("目前此產業樣本股沒有異常股，可考慮進入產業擴散測試。")
else:
    st.warning("以下股票需要進一步討論或重新校準：")
    st.dataframe(abnormal_df, use_container_width=True)

st.header("四、公司細節檢視")
selected_company = st.selectbox("選擇公司檢視", ind["samples"])
company = companies[selected_company]
result = compute_company_result(selected_company)
fin, fin_source = get_financials(company)

c1, c2, c3, c4 = st.columns(4)
c1.metric("公司", selected_company)
c2.metric("現價", fmt(result["現價"]))
c3.metric("Base", "N/A" if result["Base"] is None else f"{result['Base']:.2f}")
c4.metric("偏離", "N/A" if result["偏離%"] is None else f"{result['偏離%']}%")

st.subheader("模型適配分數")
model_df = pd.DataFrame([
    {"模型": m, "分數": s, "評級": rating(s)}
    for m, s in sorted(company["model_scores"].items(), key=lambda x: x[1], reverse=True)
])
st.dataframe(model_df, use_container_width=True)

st.subheader("各模型估值區間")
valuation_rows = []
valuation, weights = weighted_valuation(company["model_scores"], company["valuation"], top_n=3)
selected_models = {m for m, _, _ in weights}
for m, v in company["valuation"].items():
    valuation_rows.append({
        "模型": m,
        "分數": company["model_scores"].get(m, 0),
        "Bear": v["bear"],
        "Base": v["base"],
        "Bull": v["bull"],
        "是否採用": "是" if m in selected_models else "否"
    })
st.dataframe(pd.DataFrame(valuation_rows), use_container_width=True)

st.subheader("財報因子")
fin_df = pd.DataFrame([{"欄位": k, "值": v} for k, v in fin.items()])
st.dataframe(fin_df, use_container_width=True)

st.header("五、產業擴散建議")
if selected_summary["狀態"] == "產業模型 PASS":
    st.success(
        f"{selected_industry} 母模型已通過樣本股驗證。"
        "下一步可把同產業股票批量匯入，並只針對 WATCH / FAIL 個股討論。"
    )
elif selected_summary["狀態"] == "產業模型 WATCH":
    st.warning(
        f"{selected_industry} 母模型接近通過，但仍有樣本偏離較高。"
        "建議先檢視異常股，再決定是否擴散。"
    )
else:
    st.error(
        f"{selected_industry} 母模型尚未通過。"
        "不建議直接批量套用，需先調整模型池或估值區間。"
    )

st.header("六、匯出 JSON")
export = {
    "version": "V6.3 Industry Batch Calibration Engine",
    "selected_industry": selected_industry,
    "industry_summary": {k: v for k, v in selected_summary.items() if k != "results"},
    "industry_results": selected_results,
}
st.code(json.dumps(export, ensure_ascii=False, indent=2), language="json")
