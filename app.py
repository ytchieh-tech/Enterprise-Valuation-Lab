import json
from datetime import datetime

import pandas as pd
import streamlit as st

try:
    import yfinance as yf
except Exception:
    yf = None

st.set_page_config(
    page_title="Enterprise Valuation Lab V5",
    page_icon="🏛️",
    layout="wide"
)

st.title("🏛️ Enterprise Valuation Lab")
st.subheader("V5｜資料蒐集 + 現價自動更新 + 模型池擴充測試")
st.info("重點：先蒐集 12 家公司資料，現價改為自動更新；尚未校準的公司先標示『待校準』，避免硬塞不可靠估值。")

# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------

@st.cache_data(ttl=900)
def fetch_quote(ticker: str):
    """Fetch latest price from yfinance. TTL 15 minutes."""
    if yf is None:
        return None, "yfinance 未安裝"
    try:
        t = yf.Ticker(ticker)
        fast = getattr(t, "fast_info", {}) or {}
        price = fast.get("last_price") or fast.get("lastPrice")
        if price is None:
            hist = t.history(period="5d", interval="1d")
            if not hist.empty:
                price = float(hist["Close"].dropna().iloc[-1])
        if price is None:
            return None, "抓不到現價"
        return float(price), "自動更新"
    except Exception as e:
        return None, f"現價抓取失敗：{e}"


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


def weighted_valuation(company: dict, top_n: int = 3):
    scores = company.get("model_scores", {})
    vals = company.get("valuation", {})
    candidates = []
    for m, v in vals.items():
        s = scores.get(m, 0)
        if s >= 60:
            candidates.append((m, s, v))
    candidates = sorted(candidates, key=lambda x: x[1], reverse=True)[:top_n]
    total_score = sum(s for _, s, _ in candidates)
    if total_score == 0 or not candidates:
        return None, []
    result = {}
    for case in ["bear", "base", "bull"]:
        result[case] = sum(v[case] * s for _, s, v in candidates) / total_score
    weights = [(m, s, s / total_score) for m, s, _ in candidates]
    return result, weights


def judge_price(price, fair):
    if fair is None or price is None:
        return "待校準"
    bear, bull = fair["bear"], fair["bull"]
    if price < bear:
        return "低估區"
    if price <= bull:
        return "合理區間"
    return "高估區"


def calibration_result(price, fair):
    if fair is None or price is None:
        return "待校準", None
    gap = (fair["base"] / price - 1) * 100
    abs_gap = abs(gap)
    if abs_gap <= 15:
        return "PASS", gap
    if abs_gap <= 30:
        return "WATCH", gap
    return "FAIL", gap

# ------------------------------------------------------------
# Company database
# first 4 calibrated; others are model-selection/data-collection only
# ------------------------------------------------------------

companies = {
    "2330 台積電": {
        "symbol": "2330.TW",
        "type": "AI半導體 / 晶圓代工龍頭",
        "life_cycle": "高資本支出、高ROIC、AI成長溢價",
        "status": "已校準",
        "features": {"ROE": "高", "FCF": "強但受資本支出影響", "EPS CAGR": "高", "負債": "低", "股利特徵": "穩定"},
        "model_scores": {"DCF-FCFF": 94, "EVA": 90, "AI Premium": 86, "EBO": 78, "EV/EBITDA": 74, "PB-ROE": 48, "Dividend Yield": 35, "Cycle PE": 20},
        "valuation": {"DCF-FCFF": {"bear": 1750, "base": 2100, "bull": 2450}, "EVA": {"bear": 1650, "base": 2050, "bull": 2400}, "AI Premium": {"bear": 2050, "base": 2480, "bull": 2850}, "EBO": {"bear": 1550, "base": 1900, "bull": 2250}, "EV/EBITDA": {"bear": 1700, "base": 2150, "bull": 2550}},
    },
    "2308 台達電": {
        "symbol": "2308.TW",
        "type": "AI Infrastructure Compounder / 電源、散熱、工業自動化",
        "life_cycle": "AI電力基建與品質複利企業",
        "status": "已校準",
        "features": {"ROE": "高且穩定", "FCF": "穩定", "EPS CAGR": "中高", "負債": "低", "股利特徵": "穩定配息"},
        "model_scores": {"Quality Compounder": 96, "AI Infrastructure Premium": 94, "EVA": 88, "DCF-FCFF": 82, "Residual Income": 72, "PB-ROE": 58, "EV/EBITDA": 55, "Cycle PE": 18},
        "valuation": {"Quality Compounder": {"bear": 1650, "base": 1900, "bull": 2250}, "AI Infrastructure Premium": {"bear": 1700, "base": 2000, "bull": 2400}, "EVA": {"bear": 1350, "base": 1650, "bull": 2050}, "DCF-FCFF": {"bear": 1250, "base": 1550, "bull": 1900}, "Residual Income": {"bear": 1100, "base": 1400, "bull": 1700}},
    },
    "2603 長榮": {
        "symbol": "2603.TW",
        "type": "航運循環股",
        "life_cycle": "景氣循環、獲利波動、運價敏感",
        "status": "已校準",
        "features": {"ROE": "波動", "FCF": "波動", "EPS CAGR": "循環", "負債": "中", "股利特徵": "高波動"},
        "model_scores": {"EV/EBITDA": 94, "Cycle PE": 90, "FCF Yield": 82, "Asset Value": 76, "PB-ROE": 35, "Residual Income": 32, "DCF-FCFF": 28, "AI Premium": 5},
        "valuation": {"EV/EBITDA": {"bear": 150, "base": 195, "bull": 250}, "Cycle PE": {"bear": 145, "base": 185, "bull": 235}, "FCF Yield": {"bear": 140, "base": 180, "bull": 225}, "Asset Value": {"bear": 135, "base": 170, "bull": 215}},
    },
    "2881 富邦金": {
        "symbol": "2881.TW",
        "type": "金融金控",
        "life_cycle": "金融資產股、ROE與股利主導估值",
        "status": "已校準",
        "features": {"ROE": "穩定", "FCF": "金融業不適用", "EPS CAGR": "中", "負債": "金融業特殊結構", "股利特徵": "重要估值因子"},
        "model_scores": {"PB-ROE": 96, "Residual Income": 91, "Dividend Yield": 85, "PE": 66, "DCF-FCFF": 10, "EV/EBITDA": 5, "AI Premium": 0, "Cycle PE": 20},
        "valuation": {"PB-ROE": {"bear": 110, "base": 132, "bull": 155}, "Residual Income": {"bear": 105, "base": 128, "bull": 150}, "Dividend Yield": {"bear": 100, "base": 122, "bull": 145}, "PE": {"bear": 98, "base": 118, "bull": 140}},
    },
    "2303 聯電": {
        "symbol": "2303.TW", "type": "成熟半導體 / 晶圓代工", "life_cycle": "成熟製程、景氣循環中低", "status": "待校準",
        "features": {"ROE": "中", "FCF": "中", "EPS CAGR": "低~中", "負債": "低", "股利特徵": "中高"},
        "model_scores": {"PB-ROE": 86, "EV/EBITDA": 82, "EBO": 78, "Dividend Yield": 72, "DCF-FCFF": 70, "AI Premium": 25, "Cycle PE": 62},
        "valuation": {},
    },
    "5347 世界先進": {
        "symbol": "5347.TWO", "type": "成熟半導體 / 特殊製程", "life_cycle": "成熟製程、股利與循環並重", "status": "待校準",
        "features": {"ROE": "中", "FCF": "中", "EPS CAGR": "低~中", "負債": "低", "股利特徵": "重要"},
        "model_scores": {"PB-ROE": 86, "EV/EBITDA": 82, "Dividend Yield": 78, "EBO": 74, "DCF-FCFF": 68, "AI Premium": 20, "Cycle PE": 62},
        "valuation": {},
    },
    "2382 廣達": {
        "symbol": "2382.TW", "type": "AI伺服器 / ODM", "life_cycle": "AI伺服器成長，毛利率較低但營收彈性高", "status": "待校準",
        "features": {"ROE": "高", "FCF": "中", "EPS CAGR": "高", "負債": "中低", "股利特徵": "中"},
        "model_scores": {"AI Server Cycle": 94, "EV/EBITDA": 88, "PE": 84, "AI Premium": 78, "DCF-FCFF": 70, "PB-ROE": 55},
        "valuation": {},
    },
    "3231 緯創": {
        "symbol": "3231.TW", "type": "AI伺服器 / ODM", "life_cycle": "AI伺服器成長但波動較高", "status": "待校準",
        "features": {"ROE": "中高", "FCF": "波動", "EPS CAGR": "高", "負債": "中", "股利特徵": "中"},
        "model_scores": {"AI Server Cycle": 92, "EV/EBITDA": 86, "PE": 82, "AI Premium": 76, "Cycle PE": 70, "DCF-FCFF": 58},
        "valuation": {},
    },
    "6215 和椿": {
        "symbol": "6215.TWO", "type": "自動化設備 / 中小型成長股", "life_cycle": "工業自動化與設備需求循環", "status": "待校準",
        "features": {"ROE": "中", "FCF": "波動", "EPS CAGR": "中高", "負債": "低~中", "股利特徵": "中"},
        "model_scores": {"Quality Compounder": 82, "PE": 78, "EV/EBITDA": 74, "DCF-FCFF": 70, "PB-ROE": 65, "Cycle PE": 58},
        "valuation": {},
    },
    "2606 裕民": {
        "symbol": "2606.TW", "type": "散裝航運循環股", "life_cycle": "景氣循環、運價與船隊資產主導", "status": "待校準",
        "features": {"ROE": "波動", "FCF": "波動", "EPS CAGR": "循環", "負債": "中", "股利特徵": "高波動"},
        "model_scores": {"EV/EBITDA": 92, "Cycle PE": 88, "Asset Value": 82, "FCF Yield": 78, "PB-ROE": 38, "DCF-FCFF": 25},
        "valuation": {},
    },
    "2882 國泰金": {
        "symbol": "2882.TW", "type": "金融金控", "life_cycle": "壽險資產重估與股利主導", "status": "待校準",
        "features": {"ROE": "中高", "FCF": "金融業不適用", "EPS CAGR": "中", "負債": "金融業特殊結構", "股利特徵": "重要"},
        "model_scores": {"PB-ROE": 94, "Residual Income": 90, "Dividend Yield": 84, "PE": 68, "EBO": 62, "DCF-FCFF": 8},
        "valuation": {},
    },
    "2891 中信金": {
        "symbol": "2891.TW", "type": "金融金控", "life_cycle": "銀行獲利與股利穩定性主導", "status": "待校準",
        "features": {"ROE": "穩定", "FCF": "金融業不適用", "EPS CAGR": "中", "負債": "金融業特殊結構", "股利特徵": "重要"},
        "model_scores": {"PB-ROE": 94, "Residual Income": 88, "Dividend Yield": 86, "PE": 70, "EBO": 62, "DCF-FCFF": 8},
        "valuation": {},
    },
}

# ------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------

st.sidebar.title("功能")
mode = st.sidebar.radio("模式", ["單股檢視", "12家公司資料總覽"])

if mode == "12家公司資料總覽":
    rows = []
    for name, c in companies.items():
        price, note = fetch_quote(c["symbol"])
        fair, weights = weighted_valuation(c)
        cal, gap = calibration_result(price, fair)
        rows.append({
            "公司": name,
            "Ticker": c["symbol"],
            "類型": c["type"],
            "狀態": c["status"],
            "現價": None if price is None else round(price, 2),
            "現價來源": note,
            "Top模型": " / ".join([m for m, _, _ in weights]) if weights else "待建立估值區間",
            "Base合理價": None if fair is None else round(fair["base"], 2),
            "誤差%": None if gap is None else round(gap, 2),
            "校準": cal,
        })
    st.header("12 家公司資料總覽")
    st.dataframe(pd.DataFrame(rows), use_container_width=True)
    st.caption("待校準公司目前只完成模型池與現價蒐集，尚未產生 Bear/Base/Bull 估值。")
    st.stop()

stock = st.selectbox("選擇公司", list(companies.keys()))
company = companies[stock]

live_price, price_note = fetch_quote(company["symbol"])
if live_price is None:
    st.warning(f"現價未成功更新：{price_note}")

valuation_result, weights = weighted_valuation(company, top_n=3)
calibration, gap = calibration_result(live_price, valuation_result)

st.divider()
st.header("一、公司定位")
c1, c2, c3, c4 = st.columns(4)
c1.metric("股票代號", company["symbol"])
c2.metric("公司類型", company["type"])
c3.metric("資料狀態", company["status"])
c4.metric("現價", "N/A" if live_price is None else f"{live_price:.2f}")
st.caption(f"現價狀態：{price_note}｜更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

st.header("二、公司特徵")
feature_cols = st.columns(len(company["features"]))
for col, (k, v) in zip(feature_cols, company["features"].items()):
    col.metric(k, v)

st.header("三、模型適配分數")
score_df = pd.DataFrame([
    {"模型": m, "適配分數": s, "評級": rating(s)}
    for m, s in sorted(company["model_scores"].items(), key=lambda x: x[1], reverse=True)
])
st.dataframe(score_df, use_container_width=True)

st.header("四、保留 Top 模型")
if weights:
    cols = st.columns(len(weights))
    for col, (m, s, w) in zip(cols, weights):
        col.success(f"{m}\n\n分數 {s}｜權重 {w:.1%}")
else:
    st.warning("目前只完成模型池，尚未建立估值區間；請先蒐集 EPS、BVPS、FCF、EBITDA、股利等資料後校準。")

st.header("五、各模型估值區間")
valuation_rows = []
for m, v in company.get("valuation", {}).items():
    valuation_rows.append({
        "模型": m,
        "適配分數": company["model_scores"].get(m, 0),
        "Bear 保守價": v["bear"],
        "Base 合理價": v["base"],
        "Bull 樂觀價": v["bull"],
        "是否納入": "是" if any(m == x[0] for x in weights) else "否"
    })
if valuation_rows:
    st.dataframe(pd.DataFrame(valuation_rows), use_container_width=True)
else:
    st.info("此公司尚未建立估值區間，先完成現價與模型池蒐集。")

st.header("六、綜合估值區間")
if valuation_result:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Bear 保守價", f"{valuation_result['bear']:.0f}")
    c2.metric("Base 合理價", f"{valuation_result['base']:.0f}")
    c3.metric("Bull 樂觀價", f"{valuation_result['bull']:.0f}")
    c4.metric("現價", "N/A" if live_price is None else f"{live_price:.0f}")

    verdict = judge_price(live_price, valuation_result)
    st.subheader(f"判斷：{verdict}")
    if gap is not None:
        st.write(f"Base 合理價相對現價差距：{gap:.1f}%")
        if calibration == "PASS":
            st.success("校準結果：PASS｜Base合理價與現價差距在 ±15% 內。")
        elif calibration == "WATCH":
            st.warning("校準結果：WATCH｜偏離 15%~30%，需要檢查權重或估值區間。")
        else:
            st.error("校準結果：FAIL｜偏離超過 30%，需重新校準模型權重或估值基準。")
else:
    st.info("尚無綜合估值區間。")

st.header("七、匯出給主平台 JSON")
export_data = {
    company["symbol"]: {
        "name": stock,
        "type": company["type"],
        "status": company["status"],
        "selected_models": [m for m, _, _ in weights],
        "weights": {m: round(w, 4) for m, _, w in weights},
        "valuation": {
            "bear": round(valuation_result["bear"], 2) if valuation_result else None,
            "base": round(valuation_result["base"], 2) if valuation_result else None,
            "bull": round(valuation_result["bull"], 2) if valuation_result else None,
        } if valuation_result else None,
        "current_price": None if live_price is None else round(live_price, 2),
        "price_source": price_note,
        "calibration": calibration,
        "gap_percent": None if gap is None else round(gap, 2),
        "judgement": judge_price(live_price, valuation_result) if valuation_result else "待校準",
    }
}
st.code(json.dumps(export_data, ensure_ascii=False, indent=2), language="json")
