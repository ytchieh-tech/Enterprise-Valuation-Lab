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
# Enterprise Valuation Lab V6.1
# Financial Data Engine｜財報狗接口 + fallback 備援資料
# ============================================================

st.set_page_config(
    page_title="Enterprise Valuation Lab V6.1",
    page_icon="🏛️",
    layout="wide"
)

st.title("🏛️ Enterprise Valuation Lab")
st.subheader("V6.1｜Financial Data Engine：財報狗接口 + 現價更新 + 財報缺漏檢查")
st.info(
    "本版重點：yfinance 負責現價；財報狗資料先採「可貼上 / 可匯入」接口；"
    "若抓不到財報，使用 fallback 財報因子並清楚標示來源，避免系統亂補資料。"
)


# ------------------------------------------------------------
# Sidebar settings
# ------------------------------------------------------------

st.sidebar.header("Financial Data Engine")
data_mode = st.sidebar.radio(
    "財報資料模式",
    ["fallback 備援資料", "貼上財報狗 JSON"],
    index=0
)

st.sidebar.caption("V6.1：先把財報欄位標準化，下一版再串實際 API。")


# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------

@st.cache_data(ttl=900)
def fetch_price_yfinance(symbol: str, fallback_price: Optional[float] = None) -> Tuple[Optional[float], str]:
    """Fetch price using yfinance. If failed, return fallback price."""
    candidates = []
    if symbol.endswith(".TW") or symbol.endswith(".TWO"):
        candidates.append(symbol)
        base = symbol.split(".")[0]
        if symbol.endswith(".TW"):
            candidates.append(base + ".TWO")
        else:
            candidates.append(base + ".TW")
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

    return None, "抓不到現價，且無 fallback"


def completeness(fin: Dict[str, Any], required: List[str]) -> Tuple[int, List[str]]:
    missing = []
    for k in required:
        v = fin.get(k, None)
        if v is None or v == "" or v == "N/A":
            missing.append(k)
    score = round((len(required) - len(missing)) / len(required) * 100) if required else 0
    return score, missing


def rating(score: float) -> str:
    if score >= 90:
        return "S 核心模型"
    if score >= 80:
        return "A 強烈推薦"
    if score >= 70:
        return "B 可用"
    if score >= 60:
        return "C 觀察"
    return "D 不建議 / 淘汰"


def valuation_status(base: Optional[float], price: Optional[float], tolerance: float = 0.15) -> Tuple[str, Optional[float]]:
    if base is None or price is None or price == 0:
        return "待校準", None
    gap = base / price - 1
    if abs(gap) <= tolerance:
        return "PASS", gap
    if abs(gap) <= tolerance * 1.5:
        return "WATCH", gap
    return "FAIL", gap


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


def parse_statementdog_json(raw: str) -> Dict[str, Any]:
    """A simple connector-like parser for 財報狗 JSON pasted by user.

    Expected example:
    {
      "6215": {
        "EPS": 3.2,
        "ROE": 12.5,
        "Revenue_Growth": 18,
        "Gross_Margin": 32,
        "Debt_Ratio": 28,
        "FCF": 420000,
        "BVPS": 38
      }
    }
    """
    if not raw.strip():
        return {}
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    return {}


# ------------------------------------------------------------
# Industry model definitions
# ------------------------------------------------------------

REQUIRED_FIELDS = [
    "EPS",
    "ROE",
    "Revenue_Growth",
    "Gross_Margin",
    "Debt_Ratio",
    "FCF",
    "BVPS",
]

industries = {
    "AI Robot": {
        "description": "AI機器人 / 自動化設備 / 智慧製造",
        "candidate_models": ["AI Robot Premium", "Robot Growth", "Automation PE", "EV/Sales", "DCF-FCFF"],
        "samples": ["6215 和椿", "2049 上銀", "4540 全球傳動"],
        "tolerance": 0.20,
    },
    "Mature Foundry": {
        "description": "成熟製程晶圓代工",
        "candidate_models": ["DCF-FCFF", "EVA", "EBO", "PE", "PB-ROE"],
        "samples": ["2303 聯電", "5347 世界先進"],
        "tolerance": 0.15,
    },
    "PCB / CCL": {
        "description": "PCB / 高階CCL / AI高速材料",
        "candidate_models": ["AI Material Premium", "ROIC Premium", "DCF-FCFF", "PE", "EV/EBITDA"],
        "samples": ["2383 台光電", "3037 欣興"],
        "tolerance": 0.15,
    },
}


# ------------------------------------------------------------
# Company database
# fallback financials are placeholders for structure testing.
# Replace them with StatementDog/TWSE actuals when available.
# ------------------------------------------------------------

companies = {
    "6215 和椿": {
        "code": "6215",
        "symbol": "6215.TWO",
        "industry": "AI Robot",
        "type": "AI Robot / 自動化設備",
        "fallback_price": 101,
        "financial_fallback": {
            "EPS": 2.8,
            "ROE": 11.5,
            "Revenue_Growth": 18.0,
            "Gross_Margin": 31.0,
            "Debt_Ratio": 28.0,
            "FCF": 180,
            "BVPS": 35.0,
        },
        "model_scores": {
            "AI Robot Premium": 96,
            "Robot Growth": 94,
            "Automation PE": 90,
            "EV/Sales": 82,
            "DCF-FCFF": 68,
            "PB-ROE": 50,
            "Dividend Yield": 25,
        },
        "valuation": {
            "AI Robot Premium": {"bear": 86, "base": 98, "bull": 122},
            "Robot Growth": {"bear": 82, "base": 95, "bull": 118},
            "Automation PE": {"bear": 78, "base": 92, "bull": 112},
            "EV/Sales": {"bear": 72, "base": 88, "bull": 108},
            "DCF-FCFF": {"bear": 65, "base": 78, "bull": 95},
        },
        "calibration_note": "AI Robot Premium 已納入；以 Robot Growth 與 Automation PE 作為核心校準。",
    },
    "2049 上銀": {
        "code": "2049",
        "symbol": "2049.TW",
        "industry": "AI Robot",
        "type": "傳動元件 / 線性滑軌 / 機器人供應鏈",
        "fallback_price": 320,
        "financial_fallback": {
            "EPS": 7.5,
            "ROE": 9.5,
            "Revenue_Growth": 8.0,
            "Gross_Margin": 34.0,
            "Debt_Ratio": 32.0,
            "FCF": 950,
            "BVPS": 88.0,
        },
        "model_scores": {
            "Robot Growth": 88,
            "Automation PE": 86,
            "AI Robot Premium": 82,
            "EV/Sales": 76,
            "DCF-FCFF": 72,
            "PB-ROE": 58,
        },
        "valuation": {},  # 待產業模型測試，不硬塞
        "calibration_note": "待校準：先驗證是否可套用 AI Robot 產業母模型。",
    },
    "4540 全球傳動": {
        "code": "4540",
        "symbol": "4540.TW",
        "industry": "AI Robot",
        "type": "傳動元件 / 自動化零組件",
        "fallback_price": 55,
        "financial_fallback": {
            "EPS": 1.4,
            "ROE": 6.8,
            "Revenue_Growth": 10.0,
            "Gross_Margin": 29.0,
            "Debt_Ratio": 35.0,
            "FCF": 120,
            "BVPS": 28.0,
        },
        "model_scores": {
            "Automation PE": 84,
            "Robot Growth": 82,
            "EV/Sales": 78,
            "AI Robot Premium": 75,
            "DCF-FCFF": 62,
            "PB-ROE": 50,
        },
        "valuation": {},
        "calibration_note": "待校準：觀察機器人族群模型是否適用中小型零組件股。",
    },
    "2303 聯電": {
        "code": "2303",
        "symbol": "2303.TW",
        "industry": "Mature Foundry",
        "type": "成熟製程晶圓代工",
        "fallback_price": 45,
        "financial_fallback": {
            "EPS": 3.6,
            "ROE": 12.0,
            "Revenue_Growth": 3.0,
            "Gross_Margin": 31.0,
            "Debt_Ratio": 22.0,
            "FCF": 48000,
            "BVPS": 32.0,
        },
        "model_scores": {
            "DCF-FCFF": 90,
            "EVA": 86,
            "EBO": 82,
            "PE": 78,
            "PB-ROE": 74,
        },
        "valuation": {},
        "calibration_note": "待校準：成熟製程母模型樣本。",
    },
    "5347 世界先進": {
        "code": "5347",
        "symbol": "5347.TWO",
        "industry": "Mature Foundry",
        "type": "成熟製程晶圓代工",
        "fallback_price": 100,
        "financial_fallback": {
            "EPS": 4.8,
            "ROE": 15.0,
            "Revenue_Growth": 5.0,
            "Gross_Margin": 36.0,
            "Debt_Ratio": 18.0,
            "FCF": 18000,
            "BVPS": 41.0,
        },
        "model_scores": {
            "DCF-FCFF": 88,
            "EVA": 86,
            "EBO": 82,
            "PE": 80,
            "PB-ROE": 72,
        },
        "valuation": {},
        "calibration_note": "待校準：成熟製程母模型樣本。",
    },
    "2383 台光電": {
        "code": "2383",
        "symbol": "2383.TW",
        "industry": "PCB / CCL",
        "type": "AI CCL / 高階材料",
        "fallback_price": 5450,
        "financial_fallback": {
            "EPS": 75.0,
            "ROE": 31.0,
            "Revenue_Growth": 28.0,
            "Gross_Margin": 39.0,
            "Debt_Ratio": 25.0,
            "FCF": 24000,
            "BVPS": 210.0,
        },
        "model_scores": {
            "AI Material Premium": 96,
            "ROIC Premium": 92,
            "DCF-FCFF": 86,
            "PE": 84,
            "EV/EBITDA": 78,
        },
        "valuation": {},
        "calibration_note": "待校準：PCB/CCL 產業母模型樣本。",
    },
    "3037 欣興": {
        "code": "3037",
        "symbol": "3037.TW",
        "industry": "PCB / CCL",
        "type": "PCB / IC載板",
        "fallback_price": 976,
        "financial_fallback": {
            "EPS": 18.0,
            "ROE": 17.0,
            "Revenue_Growth": 18.0,
            "Gross_Margin": 28.0,
            "Debt_Ratio": 34.0,
            "FCF": 30000,
            "BVPS": 108.0,
        },
        "model_scores": {
            "ROIC Premium": 88,
            "AI Material Premium": 86,
            "DCF-FCFF": 82,
            "PE": 78,
            "EV/EBITDA": 76,
        },
        "valuation": {},
        "calibration_note": "待校準：PCB/CCL 產業母模型樣本。",
    },
}


# ------------------------------------------------------------
# StatementDog JSON input
# ------------------------------------------------------------

statementdog_data = {}
if data_mode == "貼上財報狗 JSON":
    st.sidebar.subheader("貼上財報狗 JSON")
    raw_json = st.sidebar.text_area(
        "格式：以股票代號為 key",
        height=220,
        placeholder='{"6215":{"EPS":2.8,"ROE":11.5,"Revenue_Growth":18,"Gross_Margin":31,"Debt_Ratio":28,"FCF":180,"BVPS":35}}'
    )
    statementdog_data = parse_statementdog_json(raw_json)
    if raw_json.strip() and not statementdog_data:
        st.sidebar.error("JSON 解析失敗，請檢查格式。")


def get_financials(company: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    code = company["code"]
    if data_mode == "貼上財報狗 JSON" and code in statementdog_data:
        fin = company["financial_fallback"].copy()
        fin.update(statementdog_data.get(code, {}))
        return fin, "財報狗 JSON 貼上資料"
    return company["financial_fallback"].copy(), "fallback 財報因子"


# ------------------------------------------------------------
# UI controls
# ------------------------------------------------------------

industry_name = st.sidebar.selectbox("選擇產業模型", list(industries.keys()))
industry = industries[industry_name]

available_companies = [k for k, v in companies.items() if v["industry"] == industry_name]
stock = st.selectbox("選擇樣本公司", available_companies)
company = companies[stock]
price, price_source = fetch_price_yfinance(company["symbol"], company.get("fallback_price"))
fin, fin_source = get_financials(company)
score, missing = completeness(fin, REQUIRED_FIELDS)

st.sidebar.divider()
st.sidebar.metric("產業模型數", len(industries))
st.sidebar.metric("目前產業樣本數", len(available_companies))
st.sidebar.metric("財報完整度", f"{score}%")
st.sidebar.caption("先確認財報欄位能不能齊，再決定是否做估值校準。")


# ------------------------------------------------------------
# Main page
# ------------------------------------------------------------

st.header("一、產業母模型")
c1, c2 = st.columns(2)
c1.metric("產業", industry_name)
c2.metric("產業說明", industry["description"])
st.write("候選模型池：")
st.code("、".join(industry["candidate_models"]))

st.divider()

st.header("二、公司定位")
c1, c2, c3, c4 = st.columns(4)
c1.metric("股票代號", company["symbol"])
c2.metric("公司", stock)
c3.metric("公司類型", company["type"])
c4.metric("現價", "N/A" if price is None else f"{price:.2f}")
st.caption(f"現價來源：{price_source}｜更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

st.header("三、財報因子資料")
factor_cols = st.columns(4)
factor_cols[0].metric("EPS", fin.get("EPS", "N/A"))
factor_cols[1].metric("ROE", fin.get("ROE", "N/A"))
factor_cols[2].metric("營收成長%", fin.get("Revenue_Growth", "N/A"))
factor_cols[3].metric("毛利率%", fin.get("Gross_Margin", "N/A"))

factor_cols2 = st.columns(3)
factor_cols2[0].metric("負債比%", fin.get("Debt_Ratio", "N/A"))
factor_cols2[1].metric("FCF", fin.get("FCF", "N/A"))
factor_cols2[2].metric("BVPS", fin.get("BVPS", "N/A"))

st.caption(f"財報資料來源：{fin_source}")

if missing:
    st.warning(f"缺漏欄位：{', '.join(missing)}")
else:
    st.success("財報欄位完整，可進入模型適配與估值校準。")

st.header("四、模型適配分數")
score_df = pd.DataFrame([
    {"模型": m, "適配分數": s, "評級": rating(s)}
    for m, s in sorted(company["model_scores"].items(), key=lambda x: x[1], reverse=True)
])
st.dataframe(score_df, use_container_width=True)

st.header("五、保留 Top 模型")
valuation_result, weights = weighted_valuation(company["model_scores"], company["valuation"], top_n=3)

top_models = sorted(company["model_scores"].items(), key=lambda x: x[1], reverse=True)[:3]
cols = st.columns(3)
for col, (m, s) in zip(cols, top_models):
    col.success(f"{m}\n\n分數 {s}｜{rating(s)}")

st.header("六、估值校準狀態")
if valuation_result:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Bear", f"{valuation_result['bear']:.0f}")
    c2.metric("Base", f"{valuation_result['base']:.0f}")
    c3.metric("Bull", f"{valuation_result['bull']:.0f}")
    c4.metric("現價", "N/A" if price is None else f"{price:.0f}")
    status, gap = valuation_status(valuation_result["base"], price, industry["tolerance"])
    st.subheader(f"校準結果：{status}")
    if gap is not None:
        st.write(f"Base 合理價相對現價差距：{gap:.1%}")
else:
    st.info("此公司目前尚未建立 Bear / Base / Bull 估值區間，狀態維持待校準。")

st.info(company["calibration_note"])

st.header("七、產業樣本總表")
rows = []
for name in available_companies:
    c = companies[name]
    p, ps = fetch_price_yfinance(c["symbol"], c.get("fallback_price"))
    f, fs = get_financials(c)
    comp, miss = completeness(f, REQUIRED_FIELDS)
    val, w = weighted_valuation(c["model_scores"], c["valuation"], top_n=3)
    status, gap = valuation_status(val["base"] if val else None, p, industry["tolerance"]) if val else ("待校準", None)
    rows.append({
        "公司": name,
        "代號": c["symbol"],
        "現價": p,
        "現價來源": ps,
        "財報來源": fs,
        "財報完整度": comp,
        "缺漏數": len(miss),
        "Top1模型": sorted(c["model_scores"].items(), key=lambda x: x[1], reverse=True)[0][0],
        "校準狀態": status,
        "偏離%": None if gap is None else round(gap * 100, 1),
    })

st.dataframe(pd.DataFrame(rows), use_container_width=True)

st.header("八、匯出 JSON")
export = {
    "version": "V6.1 Financial Data Engine",
    "industry": industry_name,
    "selected_company": stock,
    "price": price,
    "price_source": price_source,
    "financial_source": fin_source,
    "financial_completeness": score,
    "missing_fields": missing,
    "financials": fin,
    "top_models": [m for m, _ in top_models],
    "valuation": valuation_result,
}
st.code(json.dumps(export, ensure_ascii=False, indent=2), language="json")
