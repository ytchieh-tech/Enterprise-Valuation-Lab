import json
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

import pandas as pd
import streamlit as st

try:
    import yfinance as yf
except Exception:
    yf = None

st.set_page_config(
    page_title="Enterprise Valuation Lab V6",
    page_icon="🏛️",
    layout="wide"
)

st.title("🏛️ Enterprise Valuation Lab")
st.subheader("V6｜產業校準中心 + 財報資料蒐集")
st.info("先以產業母模型為主：每個產業挑 1～2 家樣本股，先蒐集財報因子，再進入估值校準。")

# ------------------------------------------------------------
# Universe: industry model samples
# ------------------------------------------------------------
INDUSTRY_GROUPS: Dict[str, Dict[str, Any]] = {
    "AI Semiconductor": {
        "description": "AI半導體 / 先進製程 / IC設計",
        "models": ["DCF-FCFF", "EVA", "EBO", "AI Premium", "EV/EBITDA"],
        "stocks": {
            "2330.TW": {"name": "台積電", "fallback_price": 2340},
            "2454.TW": {"name": "聯發科", "fallback_price": 1500},
        },
    },
    "AI Infrastructure": {
        "description": "AI電力基建 / 電源 / 資料中心供應鏈",
        "models": ["Quality Compounder", "EVA", "DCF-FCFF", "AI Infrastructure Premium"],
        "stocks": {
            "2308.TW": {"name": "台達電", "fallback_price": 1900},
            "2301.TW": {"name": "光寶科", "fallback_price": 110},
        },
    },
    "Financial": {
        "description": "金融金控 / 銀行 / 保險",
        "models": ["PB-ROE", "Residual Income", "Dividend Yield"],
        "stocks": {
            "2881.TW": {"name": "富邦金", "fallback_price": 130},
            "2882.TW": {"name": "國泰金", "fallback_price": 85},
        },
    },
    "Shipping": {
        "description": "航運循環股",
        "models": ["EV/EBITDA", "Cycle PE", "FCF Yield", "Asset Value"],
        "stocks": {
            "2603.TW": {"name": "長榮", "fallback_price": 182},
            "2609.TW": {"name": "陽明", "fallback_price": 70},
        },
    },
    "AI Robot": {
        "description": "AI Robot / 自動化 / 工業機器人",
        "models": ["AI Robot Premium", "Robot Growth", "Automation PE", "EV/Sales"],
        "stocks": {
            "6215.TWO": {"name": "和椿", "fallback_price": 101},
            "2049.TW": {"name": "上銀", "fallback_price": 260},
            "4540.TWO": {"name": "全球傳動", "fallback_price": 45},
        },
    },
    "PCB / CCL": {
        "description": "PCB / 高階CCL / AI高速材料",
        "models": ["AI Material Premium", "ROIC Premium", "DCF-FCFF", "PE", "EV/EBITDA"],
        "stocks": {
            "2383.TW": {"name": "台光電", "fallback_price": 1200},
            "3037.TW": {"name": "欣興", "fallback_price": 160},
        },
    },
    "Mature Foundry": {
        "description": "成熟製程晶圓代工",
        "models": ["DCF-FCFF", "EVA", "EBO", "PB-ROE", "EV/EBITDA"],
        "stocks": {
            "2303.TW": {"name": "聯電", "fallback_price": 50},
            "5347.TWO": {"name": "世界先進", "fallback_price": 95},
        },
    },
    "Memory": {
        "description": "記憶體 / 模組 / 控制IC",
        "models": ["Cycle PE", "EV/EBITDA", "FCF Yield", "Inventory Cycle"],
        "stocks": {
            "3260.TWO": {"name": "威剛", "fallback_price": 120},
            "8299.TWO": {"name": "群聯", "fallback_price": 650},
        },
    },
}

# ------------------------------------------------------------
# Quote and financial helpers
# ------------------------------------------------------------
@st.cache_data(ttl=900, show_spinner=False)
def fetch_quote(ticker: str, fallback_price: Optional[float] = None) -> Tuple[Optional[float], str]:
    if yf is None:
        return fallback_price, "fallback：yfinance 未安裝"

    candidates = [ticker]
    if ticker.endswith(".TWO"):
        candidates.append(ticker.replace(".TWO", ".TW"))
    elif ticker.endswith(".TW"):
        candidates.append(ticker.replace(".TW", ".TWO"))

    for tkr in candidates:
        try:
            t = yf.Ticker(tkr)
            fast = getattr(t, "fast_info", {}) or {}
            price = fast.get("last_price") or fast.get("lastPrice")
            if price is None:
                hist = t.history(period="5d", interval="1d")
                if hist is not None and not hist.empty:
                    close = hist["Close"].dropna()
                    if len(close):
                        price = float(close.iloc[-1])
            if price is not None and float(price) > 0:
                return float(price), f"yfinance 自動更新：{tkr}"
        except Exception:
            pass

    return fallback_price, "fallback 手動備援價" if fallback_price is not None else "現價抓取失敗"


def _safe_float(x):
    try:
        if x is None or pd.isna(x):
            return None
        return float(x)
    except Exception:
        return None


def _get_latest_from_df(df: pd.DataFrame, possible_rows) -> Optional[float]:
    if df is None or df.empty:
        return None
    for row in possible_rows:
        if row in df.index:
            s = df.loc[row].dropna()
            if len(s):
                return _safe_float(s.iloc[0])
    return None

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_financial_factors(ticker: str) -> Dict[str, Any]:
    """Collect factors available from yfinance. Missing values are kept as None."""
    factors: Dict[str, Any] = {
        "資料來源": "yfinance + fallback/可推導欄位",
        "營收": None,
        "毛利": None,
        "營業利益": None,
        "稅後淨利": None,
        "股東權益": None,
        "總資產": None,
        "總負債": None,
        "營業現金流": None,
        "資本支出": None,
        "自由現金流FCF": None,
        "EBITDA": None,
        "EPS_TTM": None,
        "ROE": None,
        "ROA": None,
        "負債比": None,
        "FCF_Margin": None,
        "Dividend_Yield": None,
        "Trailing_PE": None,
        "Forward_PE": None,
        "PB": None,
        "Market_Cap": None,
        "Enterprise_Value": None,
        "資料完整度": 0,
        "缺漏欄位": [],
    }

    if yf is None:
        factors["缺漏欄位"] = [k for k in factors.keys() if k not in ["資料來源", "資料完整度", "缺漏欄位"]]
        return factors

    try:
        t = yf.Ticker(ticker)
        info = getattr(t, "info", {}) or {}
        fin = t.financials
        bs = t.balance_sheet
        cf = t.cashflow

        revenue = _get_latest_from_df(fin, ["Total Revenue", "Operating Revenue"])
        gross_profit = _get_latest_from_df(fin, ["Gross Profit"])
        operating_income = _get_latest_from_df(fin, ["Operating Income"])
        net_income = _get_latest_from_df(fin, ["Net Income", "Net Income Common Stockholders"])
        ebitda = _get_latest_from_df(fin, ["EBITDA", "Normalized EBITDA"])

        equity = _get_latest_from_df(bs, ["Stockholders Equity", "Total Equity Gross Minority Interest"])
        assets = _get_latest_from_df(bs, ["Total Assets"])
        liabilities = _get_latest_from_df(bs, ["Total Liabilities Net Minority Interest", "Total Liabilities"])

        ocf = _get_latest_from_df(cf, ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"])
        capex = _get_latest_from_df(cf, ["Capital Expenditure", "Capital Expenditures"])

        fcf = info.get("freeCashflow")
        fcf = _safe_float(fcf)
        if fcf is None and ocf is not None and capex is not None:
            # Yahoo capex is often negative, so OCF + CAPEX is common FCF approximation.
            fcf = ocf + capex

        factors.update({
            "營收": revenue,
            "毛利": gross_profit,
            "營業利益": operating_income,
            "稅後淨利": net_income,
            "股東權益": equity,
            "總資產": assets,
            "總負債": liabilities,
            "營業現金流": ocf,
            "資本支出": capex,
            "自由現金流FCF": fcf,
            "EBITDA": ebitda,
            "EPS_TTM": _safe_float(info.get("trailingEps")),
            "Dividend_Yield": _safe_float(info.get("dividendYield")),
            "Trailing_PE": _safe_float(info.get("trailingPE")),
            "Forward_PE": _safe_float(info.get("forwardPE")),
            "PB": _safe_float(info.get("priceToBook")),
            "Market_Cap": _safe_float(info.get("marketCap")),
            "Enterprise_Value": _safe_float(info.get("enterpriseValue")),
        })

        if net_income is not None and equity not in [None, 0]:
            factors["ROE"] = net_income / equity
        else:
            factors["ROE"] = _safe_float(info.get("returnOnEquity"))

        if net_income is not None and assets not in [None, 0]:
            factors["ROA"] = net_income / assets
        else:
            factors["ROA"] = _safe_float(info.get("returnOnAssets"))

        if liabilities is not None and assets not in [None, 0]:
            factors["負債比"] = liabilities / assets

        if fcf is not None and revenue not in [None, 0]:
            factors["FCF_Margin"] = fcf / revenue

    except Exception as e:
        factors["資料來源"] = f"yfinance 財報抓取失敗：{e}"

    core_keys = [
        "營收", "稅後淨利", "股東權益", "總資產", "總負債",
        "營業現金流", "自由現金流FCF", "EBITDA", "EPS_TTM", "ROE",
        "ROA", "負債比", "Dividend_Yield", "Trailing_PE", "PB"
    ]
    missing = [k for k in core_keys if factors.get(k) is None]
    complete = len(core_keys) - len(missing)
    factors["資料完整度"] = round(complete / len(core_keys) * 100, 1)
    factors["缺漏欄位"] = missing
    return factors


def fmt_num(x, pct=False):
    if x is None:
        return "N/A"
    try:
        if pct:
            return f"{float(x) * 100:.2f}%"
        if abs(float(x)) >= 1e12:
            return f"{float(x) / 1e12:.2f} 兆"
        if abs(float(x)) >= 1e8:
            return f"{float(x) / 1e8:.2f} 億"
        return f"{float(x):,.2f}"
    except Exception:
        return "N/A"


def industry_status(group: Dict[str, Any]):
    rows = []
    for ticker, meta in group["stocks"].items():
        price, src = fetch_quote(ticker, meta.get("fallback_price"))
        factors = fetch_financial_factors(ticker)
        rows.append({
            "代號": ticker,
            "公司": meta["name"],
            "現價": price,
            "現價來源": src,
            "資料完整度": factors["資料完整度"],
            "缺漏數": len(factors["缺漏欄位"]),
        })
    return pd.DataFrame(rows)

# ------------------------------------------------------------
# Sidebar controls
# ------------------------------------------------------------
industry = st.sidebar.selectbox("選擇產業模型", list(INDUSTRY_GROUPS.keys()))
group = INDUSTRY_GROUPS[industry]

st.sidebar.header("產業校準中心")
st.sidebar.metric("產業模型數", len(INDUSTRY_GROUPS))
st.sidebar.metric("目前產業樣本數", len(group["stocks"]))
st.sidebar.caption("V6 先蒐集財報因子，暫不硬塞估值。")

# ------------------------------------------------------------
# Main layout
# ------------------------------------------------------------
st.header("一、產業母模型")
col1, col2 = st.columns([1, 2])
col1.metric("產業", industry)
col2.write(group["description"])

st.subheader("產業候選模型池")
st.write("、".join(group["models"]))

st.divider()
st.header("二、樣本股資料完整度")
status_df = industry_status(group)
st.dataframe(status_df, use_container_width=True)

st.divider()
st.header("三、個股財報因子檢查")
stock_label = st.selectbox(
    "選擇樣本股",
    [f"{meta['name']} / {ticker}" for ticker, meta in group["stocks"].items()]
)
selected_ticker = stock_label.split(" / ")[-1]
selected_meta = group["stocks"][selected_ticker]
price, price_src = fetch_quote(selected_ticker, selected_meta.get("fallback_price"))
factors = fetch_financial_factors(selected_ticker)

c1, c2, c3, c4 = st.columns(4)
c1.metric("現價", fmt_num(price))
c2.metric("現價來源", price_src)
c3.metric("財報完整度", f"{factors['資料完整度']}%")
c4.metric("缺漏欄位數", len(factors["缺漏欄位"]))

st.subheader("核心財報因子")
factor_rows = []
for k in [
    "營收", "毛利", "營業利益", "稅後淨利", "股東權益", "總資產", "總負債",
    "營業現金流", "資本支出", "自由現金流FCF", "EBITDA", "EPS_TTM",
    "ROE", "ROA", "負債比", "FCF_Margin", "Dividend_Yield", "Trailing_PE", "Forward_PE", "PB",
    "Market_Cap", "Enterprise_Value"
]:
    pct = k in ["ROE", "ROA", "負債比", "FCF_Margin", "Dividend_Yield"]
    factor_rows.append({"因子": k, "值": fmt_num(factors.get(k), pct=pct)})
st.dataframe(pd.DataFrame(factor_rows), use_container_width=True)

if factors["缺漏欄位"]:
    st.warning("缺漏欄位：" + "、".join(factors["缺漏欄位"]))
else:
    st.success("核心欄位完整，可進入模型校準。")

st.divider()
st.header("四、產業資料蒐集 JSON")
export_data = {
    industry: {
        "description": group["description"],
        "models": group["models"],
        "stocks": status_df.to_dict(orient="records"),
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
}
st.code(json.dumps(export_data, ensure_ascii=False, indent=2), language="json")

st.caption("注意：V6 目標是先確認財報資料能否抓齊。估值校準會在資料完整度達標後進行。")
