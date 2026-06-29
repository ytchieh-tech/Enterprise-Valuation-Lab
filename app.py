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
# Enterprise Valuation Lab V6.2
# Financial Completeness Engine｜四大母模型財報完整度驗證
# ============================================================

st.set_page_config(
    page_title="Enterprise Valuation Lab V6.2",
    page_icon="🏛️",
    layout="wide"
)

st.title("🏛️ Enterprise Valuation Lab")
st.subheader("V6.2｜四大母模型財報完整度驗證引擎")
st.info(
    "本版重點：先檢查四大母模型的財報資料是否完整。"
    "只有母模型可信度達標，才允許進入產業批量校準。"
)


# ------------------------------------------------------------
# Settings
# ------------------------------------------------------------

st.sidebar.header("Financial Completeness Engine")
data_mode = st.sidebar.radio(
    "財報資料模式",
    ["fallback 備援資料", "貼上財報狗 JSON"],
    index=0
)

st.sidebar.caption("V6.2：先驗證財報完整度，再做估值。")


# ------------------------------------------------------------
# Required financial schema
# ------------------------------------------------------------

FINANCIAL_SCHEMA = {
    "損益表": {
        "fields": ["Revenue", "Operating_Income", "Net_Income", "EPS"],
        "weight": 0.40,
    },
    "資產負債表": {
        "fields": ["Total_Assets", "Equity", "Total_Liabilities", "Cash"],
        "weight": 0.30,
    },
    "現金流量表": {
        "fields": ["Operating_Cash_Flow", "Capex", "FCF"],
        "weight": 0.30,
    },
}

ALL_FIELDS = []
for section in FINANCIAL_SCHEMA.values():
    ALL_FIELDS.extend(section["fields"])


# ------------------------------------------------------------
# Helper functions
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


def section_completeness(fin: Dict[str, Any], fields: List[str]) -> Tuple[int, List[str]]:
    missing = []
    for f in fields:
        v = fin.get(f, None)
        if v is None or v == "" or v == "N/A":
            missing.append(f)
    score = round((len(fields) - len(missing)) / len(fields) * 100)
    return score, missing


def financial_score(fin: Dict[str, Any]) -> Tuple[float, Dict[str, Any], List[str]]:
    total = 0.0
    detail = {}
    all_missing = []

    for section, cfg in FINANCIAL_SCHEMA.items():
        score, missing = section_completeness(fin, cfg["fields"])
        weighted = score * cfg["weight"]
        total += weighted
        detail[section] = {
            "score": score,
            "missing": missing,
            "weight": cfg["weight"],
            "weighted": weighted,
        }
        all_missing.extend(missing)

    return round(total, 1), detail, all_missing


def source_rank(source: str) -> int:
    ranking = {
        "MOPS": 100,
        "財報狗": 95,
        "Goodinfo": 85,
        "yfinance": 70,
        "fallback": 55,
    }
    for key, val in ranking.items():
        if key in source:
            return val
    return 50


def model_confidence(fin_score: float, source: str, sample_count: int) -> float:
    src = source_rank(source)
    sample_factor = min(sample_count / 3, 1) * 100
    confidence = fin_score * 0.55 + src * 0.25 + sample_factor * 0.20
    return round(confidence, 1)


def status_from_score(score: float, threshold: float) -> str:
    if score >= threshold:
        return "PASS"
    if score >= threshold - 10:
        return "WATCH"
    return "FAIL"


def fmt_price(p):
    return "N/A" if p is None else f"{p:.2f}"


# ------------------------------------------------------------
# Four core industry mother models
# ------------------------------------------------------------

industries = {
    "AI Robot": {
        "description": "AI機器人 / 自動化設備 / 智慧製造",
        "required_threshold": 95,
        "candidate_models": ["AI Robot Premium", "Robot Growth", "Automation PE", "EV/Sales", "DCF-FCFF"],
        "samples": ["6215 和椿", "2049 上銀", "4540 全球傳動"],
    },
    "PCB / CCL": {
        "description": "PCB / 高階CCL / AI高速材料",
        "required_threshold": 95,
        "candidate_models": ["AI Material Premium", "ROIC Premium", "DCF-FCFF", "PE", "EV/EBITDA"],
        "samples": ["2383 台光電", "3037 欣興", "8046 南電", "3189 景碩"],
    },
    "AI Semiconductor": {
        "description": "AI半導體 / 晶圓代工 / IC設計",
        "required_threshold": 98,
        "candidate_models": ["DCF-FCFF", "EVA", "EBO", "AI Premium", "Forward PE"],
        "samples": ["2330 台積電", "2454 聯發科", "2303 聯電", "5347 世界先進"],
    },
    "Financial": {
        "description": "金控 / 銀行 / 保險",
        "required_threshold": 95,
        "candidate_models": ["PB-ROE", "Residual Income", "Dividend Yield"],
        "samples": ["2881 富邦金", "2882 國泰金", "2891 中信金", "2886 兆豐金"],
    },
}


# ------------------------------------------------------------
# Company database
# fallback financials are structure placeholders.
# Replace with StatementDog/MOPS actuals when available.
# ------------------------------------------------------------

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


companies = {
    # AI Robot
    "6215 和椿": {
        "code": "6215", "symbol": "6215.TWO", "industry": "AI Robot", "fallback_price": 100.5,
        "financial_source": "fallback 財報因子",
        "financial_fallback": make_financials(2.8, 6200, 520, 360, 7800, 4100, 3700, 950, 420, 240),
    },
    "2049 上銀": {
        "code": "2049", "symbol": "2049.TW", "industry": "AI Robot", "fallback_price": 318.5,
        "financial_source": "fallback 財報因子",
        "financial_fallback": make_financials(7.5, 28000, 3600, 2400, 78000, 36000, 42000, 7200, 3900, 1700),
    },
    "4540 全球傳動": {
        "code": "4540", "symbol": "4540.TW", "industry": "AI Robot", "fallback_price": 55.6,
        "financial_source": "fallback 財報因子",
        "financial_fallback": make_financials(1.4, 4200, 260, 150, 7600, 3000, 4600, 520, 280, 160),
    },

    # PCB / CCL
    "2383 台光電": {
        "code": "2383", "symbol": "2383.TW", "industry": "PCB / CCL", "fallback_price": 5450,
        "financial_source": "fallback 財報因子",
        "financial_fallback": make_financials(75, 95000, 28000, 22000, 165000, 72000, 93000, 22000, 26000, 9000),
    },
    "3037 欣興": {
        "code": "3037", "symbol": "3037.TW", "industry": "PCB / CCL", "fallback_price": 976,
        "financial_source": "fallback 財報因子",
        "financial_fallback": make_financials(18, 160000, 26000, 19000, 330000, 155000, 175000, 36000, 38000, 19000),
    },
    "8046 南電": {
        "code": "8046", "symbol": "8046.TW", "industry": "PCB / CCL", "fallback_price": 360,
        "financial_source": "fallback 財報因子",
        "financial_fallback": make_financials(12, 52000, 8200, 6100, 120000, 53000, 67000, 13000, 12500, 6200),
    },
    "3189 景碩": {
        "code": "3189", "symbol": "3189.TW", "industry": "PCB / CCL", "fallback_price": 125,
        "financial_source": "fallback 財報因子",
        "financial_fallback": make_financials(5.2, 34000, 3600, 2500, 98000, 44000, 54000, 8500, 7200, 3800),
    },

    # AI Semiconductor
    "2330 台積電": {
        "code": "2330", "symbol": "2330.TW", "industry": "AI Semiconductor", "fallback_price": 2340,
        "financial_source": "fallback 財報因子",
        "financial_fallback": make_financials(85, 3000000, 1350000, 1100000, 6500000, 4100000, 2400000, 1800000, 1550000, 900000),
    },
    "2454 聯發科": {
        "code": "2454", "symbol": "2454.TW", "industry": "AI Semiconductor", "fallback_price": 1500,
        "financial_source": "fallback 財報因子",
        "financial_fallback": make_financials(70, 560000, 130000, 110000, 820000, 560000, 260000, 260000, 130000, 25000),
    },
    "2303 聯電": {
        "code": "2303", "symbol": "2303.TW", "industry": "AI Semiconductor", "fallback_price": 45,
        "financial_source": "fallback 財報因子",
        "financial_fallback": make_financials(3.6, 220000, 52000, 43000, 600000, 380000, 220000, 120000, 76000, 42000),
    },
    "5347 世界先進": {
        "code": "5347", "symbol": "5347.TWO", "industry": "AI Semiconductor", "fallback_price": 100,
        "financial_source": "fallback 財報因子",
        "financial_fallback": make_financials(4.8, 52000, 13000, 9500, 130000, 82000, 48000, 26000, 18000, 9000),
    },

    # Financial
    "2881 富邦金": {
        "code": "2881", "symbol": "2881.TW", "industry": "Financial", "fallback_price": 130,
        "financial_source": "fallback 財報因子",
        "financial_fallback": make_financials(10.5, 900000, 150000, 120000, 12000000, 900000, 11100000, 800000, 0, 0),
    },
    "2882 國泰金": {
        "code": "2882", "symbol": "2882.TW", "industry": "Financial", "fallback_price": 70,
        "financial_source": "fallback 財報因子",
        "financial_fallback": make_financials(6.2, 820000, 120000, 95000, 11500000, 760000, 10740000, 720000, 0, 0),
    },
    "2891 中信金": {
        "code": "2891", "symbol": "2891.TW", "industry": "Financial", "fallback_price": 42,
        "financial_source": "fallback 財報因子",
        "financial_fallback": make_financials(3.4, 430000, 90000, 70000, 8800000, 520000, 8280000, 450000, 0, 0),
    },
    "2886 兆豐金": {
        "code": "2886", "symbol": "2886.TW", "industry": "Financial", "fallback_price": 40,
        "financial_source": "fallback 財報因子",
        "financial_fallback": make_financials(2.8, 260000, 68000, 52000, 5200000, 420000, 4780000, 320000, 0, 0),
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


def get_financials(company: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    code = company["code"]
    fin = company["financial_fallback"].copy()
    source = company["financial_source"]

    if data_mode == "貼上財報狗 JSON" and code in statementdog_data:
        fin.update(statementdog_data[code])
        source = "財報狗 JSON 貼上資料"

    return fin, source


# ------------------------------------------------------------
# Build master data
# ------------------------------------------------------------

rows = []
industry_summary = []

for ind_name, ind in industries.items():
    ind_rows = []
    for cname in ind["samples"]:
        c = companies[cname]
        price, price_source = fetch_price_yfinance(c["symbol"], c["fallback_price"])
        fin, fin_source = get_financials(c)
        fscore, detail, missing = financial_score(fin)
        ind_rows.append({
            "產業": ind_name,
            "公司": cname,
            "代號": c["symbol"],
            "現價": price,
            "現價來源": price_source,
            "財報來源": fin_source,
            "財報完整度": fscore,
            "缺漏欄位數": len(missing),
            "缺漏欄位": ", ".join(missing) if missing else "",
        })

    sample_count = len(ind_rows)
    avg_score = round(sum(r["財報完整度"] for r in ind_rows) / sample_count, 1) if sample_count else 0
    weakest = min(ind_rows, key=lambda r: r["財報完整度"]) if ind_rows else None
    sources = "、".join(sorted(set(r["財報來源"] for r in ind_rows)))
    confidence = model_confidence(avg_score, sources, sample_count)
    status = status_from_score(avg_score, ind["required_threshold"])

    industry_summary.append({
        "產業": ind_name,
        "樣本數": sample_count,
        "平均財報完整度": avg_score,
        "最低樣本": weakest["公司"] if weakest else "",
        "最低完整度": weakest["財報完整度"] if weakest else 0,
        "財報來源": sources,
        "母模型可信度": confidence,
        "最低標準": ind["required_threshold"],
        "狀態": status,
    })

    rows.extend(ind_rows)

master_df = pd.DataFrame(rows)
summary_df = pd.DataFrame(industry_summary)


# ------------------------------------------------------------
# UI
# ------------------------------------------------------------

selected_industry = st.sidebar.selectbox("選擇四大母模型", list(industries.keys()))
selected_company = st.sidebar.selectbox(
    "選擇公司",
    industries[selected_industry]["samples"]
)

st.sidebar.divider()
st.sidebar.metric("母模型數", len(industries))
st.sidebar.metric("樣本公司數", len(master_df))
overall_avg = round(master_df["財報完整度"].mean(), 1) if not master_df.empty else 0
st.sidebar.metric("整體財報完整度", f"{overall_avg}%")

pass_count = (summary_df["狀態"] == "PASS").sum()
st.sidebar.metric("母模型 PASS", f"{pass_count}/{len(summary_df)}")
st.sidebar.caption("只有 PASS 的母模型才建議進入產業批量估值。")


st.header("一、四大母模型財報完整度總覽")
st.dataframe(summary_df, use_container_width=True)

st.header("二、選定產業檢視")
ind = industries[selected_industry]
c1, c2, c3 = st.columns(3)
c1.metric("產業", selected_industry)
c2.metric("最低財報標準", f"{ind['required_threshold']}%")
c3.metric("候選模型數", len(ind["candidate_models"]))
st.write("候選模型池：")
st.code("、".join(ind["candidate_models"]))

industry_rows = master_df[master_df["產業"] == selected_industry]
st.subheader("產業樣本股財報完整度")
st.dataframe(industry_rows, use_container_width=True)

st.header("三、公司財報結構檢查")
company = companies[selected_company]
price, price_source = fetch_price_yfinance(company["symbol"], company["fallback_price"])
fin, fin_source = get_financials(company)
fscore, detail, missing = financial_score(fin)

c1, c2, c3, c4 = st.columns(4)
c1.metric("公司", selected_company)
c2.metric("代號", company["symbol"])
c3.metric("現價", fmt_price(price))
c4.metric("財報完整度", f"{fscore}%")
st.caption(f"現價來源：{price_source}｜財報來源：{fin_source}｜更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

section_rows = []
for section, d in detail.items():
    section_rows.append({
        "財報區塊": section,
        "權重": f"{d['weight']:.0%}",
        "完整度": d["score"],
        "加權分數": round(d["weighted"], 1),
        "缺漏欄位": ", ".join(d["missing"]) if d["missing"] else "",
    })
st.dataframe(pd.DataFrame(section_rows), use_container_width=True)

st.subheader("財報欄位值")
fin_df = pd.DataFrame([{"欄位": k, "值": v} for k, v in fin.items()])
st.dataframe(fin_df, use_container_width=True)

if missing:
    st.warning(f"此公司仍缺漏：{', '.join(missing)}")
else:
    st.success("此公司財報三表欄位完整，可進入估值校準。")

st.header("四、母模型批量校準准入判斷")
selected_summary = summary_df[summary_df["產業"] == selected_industry].iloc[0]
status = selected_summary["狀態"]

if status == "PASS":
    st.success(f"{selected_industry} 母模型財報完整度達標，可進入產業批量校準。")
elif status == "WATCH":
    st.warning(f"{selected_industry} 母模型接近達標，建議補齊最低樣本後再校準。")
else:
    st.error(f"{selected_industry} 母模型財報完整度不足，不建議進入批量估值。")

st.write(
    f"母模型可信度：{selected_summary['母模型可信度']}%｜"
    f"平均財報完整度：{selected_summary['平均財報完整度']}%｜"
    f"最低樣本：{selected_summary['最低樣本']} ({selected_summary['最低完整度']}%)"
)

st.header("五、匯出 JSON")
export = {
    "version": "V6.2 Financial Completeness Engine",
    "data_mode": data_mode,
    "selected_industry": selected_industry,
    "selected_company": selected_company,
    "industry_summary": summary_df.to_dict(orient="records"),
    "company_financial_score": fscore,
    "company_missing_fields": missing,
    "company_financials": fin,
}
st.code(json.dumps(export, ensure_ascii=False, indent=2), language="json")
