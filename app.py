import json
from datetime import datetime

import pandas as pd
import streamlit as st

try:
    import yfinance as yf
except Exception:
    yf = None

st.set_page_config(
    page_title="Enterprise Valuation Lab V5.2",
    page_icon="🏛️",
    layout="wide"
)

st.title("🏛️ Enterprise Valuation Lab")
st.subheader("V5.2｜Calibration Center + 第二批待校準資料庫")
st.info("重點：保留 V5.1 現價備援機制，新增校準中心；已校準公司給估值區間，待校準公司先只蒐集現價與模型池，避免亂給合理價。")

# ------------------------------------------------------------
# Quote helpers
# ------------------------------------------------------------
@st.cache_data(ttl=900, show_spinner=False)
def fetch_quote(ticker: str):
    """Fetch latest price from yfinance. TTL 15 minutes."""
    if yf is None:
        return None, "yfinance 未安裝"

    candidates = [ticker]
    if ticker.endswith(".TW"):
        candidates.append(ticker.replace(".TW", ".TWO"))
    elif ticker.endswith(".TWO"):
        candidates.append(ticker.replace(".TWO", ".TW"))

    for tk in candidates:
        try:
            t = yf.Ticker(tk)
            fast = getattr(t, "fast_info", {}) or {}
            price = fast.get("last_price") or fast.get("lastPrice")
            if price is None:
                hist = t.history(period="5d", interval="1d")
                if hist is not None and not hist.empty:
                    price = float(hist["Close"].dropna().iloc[-1])
            if price is not None and float(price) > 0:
                return float(price), f"yfinance 自動更新｜{tk}"
        except Exception:
            continue
    return None, "抓不到現價"


def get_price(company: dict):
    price, source = fetch_quote(company["ticker"])
    if price is not None:
        return price, source
    fallback = company.get("fallback_price")
    if fallback is not None:
        return float(fallback), "fallback 手動備援價"
    return None, "N/A"


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
    vals = company.get("valuation", {}) or {}
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
    if abs_gap <= 10:
        return "PASS", gap
    if abs_gap <= 15:
        return "WATCH", gap
    return "FAIL", gap

# ------------------------------------------------------------
# Company database
# ------------------------------------------------------------
companies = {
    "2330 台積電": {
        "ticker": "2330.TW", "symbol": "2330.TW", "status": "PASS", "fallback_price": 2340,
        "type": "AI半導體 / 晶圓代工龍頭", "life_cycle": "高資本支出、高ROIC、AI成長溢價",
        "features": {"ROE": "高", "FCF": "強但受資本支出影響", "EPS CAGR": "高", "負債": "低", "股利特徵": "穩定但非高殖利率"},
        "model_scores": {"Quality Compounder": 96, "AI Infrastructure Premium": 92, "EVA": 90, "DCF-FCFF": 86, "EBO": 78, "EV/EBITDA": 74},
        "valuation": {
            "Quality Compounder": {"bear": 1900, "base": 2200, "bull": 2550},
            "AI Infrastructure Premium": {"bear": 2050, "base": 2480, "bull": 2850},
            "EVA": {"bear": 1650, "base": 2050, "bull": 2400},
        },
    },
    "2308 台達電": {
        "ticker": "2308.TW", "symbol": "2308.TW", "status": "PASS", "fallback_price": 1900,
        "type": "AI Infrastructure Compounder / 電源與資料中心基建", "life_cycle": "AI電力基建、高品質複利企業",
        "features": {"ROE": "高且穩定", "FCF": "穩定", "EPS CAGR": "中高", "負債": "低", "股利特徵": "穩定配息"},
        "model_scores": {"Quality Compounder": 96, "AI Infrastructure Premium": 92, "EVA": 90, "DCF-FCFF": 82, "Residual Income": 76, "PB-ROE": 68},
        "valuation": {
            "Quality Compounder": {"bear": 1650, "base": 1900, "bull": 2200},
            "AI Infrastructure Premium": {"bear": 1700, "base": 1950, "bull": 2300},
            "EVA": {"bear": 1500, "base": 1700, "bull": 2000},
        },
    },
    "2603 長榮": {
        "ticker": "2603.TW", "symbol": "2603.TW", "status": "PASS", "fallback_price": 182,
        "type": "航運循環股", "life_cycle": "景氣循環、獲利波動、運價敏感",
        "features": {"ROE": "波動", "FCF": "波動", "EPS CAGR": "循環", "負債": "中", "股利特徵": "高波動股利"},
        "model_scores": {"EV/EBITDA": 94, "Cycle PE": 90, "FCF Yield": 82, "Asset Value": 76, "PB-ROE": 35},
        "valuation": {
            "EV/EBITDA": {"bear": 155, "base": 190, "bull": 230},
            "Cycle PE": {"bear": 150, "base": 180, "bull": 215},
            "FCF Yield": {"bear": 150, "base": 190, "bull": 225},
        },
    },
    "2881 富邦金": {
        "ticker": "2881.TW", "symbol": "2881.TW", "status": "PASS", "fallback_price": 130,
        "type": "金融金控", "life_cycle": "金融資產股、ROE與股利主導估值",
        "features": {"ROE": "穩定", "FCF": "金融業不適用", "EPS CAGR": "中", "負債": "金融業特殊結構", "股利特徵": "重要估值因子"},
        "model_scores": {"PB-ROE": 96, "Residual Income": 91, "Dividend Yield": 85, "PE": 66, "DCF-FCFF": 10},
        "valuation": {
            "PB-ROE": {"bear": 112, "base": 132, "bull": 150},
            "Residual Income": {"bear": 108, "base": 128, "bull": 146},
            "Dividend Yield": {"bear": 105, "base": 122, "bull": 140},
        },
    },
    # 第二批：先蒐集資料與模型池，尚未校準估值
    "6215 和椿": {
        "ticker": "6215.TWO", "symbol": "6215.TWO", "status": "待校準", "fallback_price": 85,
        "type": "AI Robot / 自動化", "life_cycle": "機器人題材、設備景氣循環",
        "features": {"ROE": "待蒐集", "FCF": "待蒐集", "EPS CAGR": "待蒐集", "負債": "待蒐集", "股利特徵": "待蒐集"},
        "model_scores": {"Robot Growth": 88, "Automation PE": 82, "EV/Sales": 76, "DCF-FCFF": 65, "PB-ROE": 50},
        "valuation": None,
    },
    "5347 世界先進": {
        "ticker": "5347.TWO", "symbol": "5347.TWO", "status": "待校準", "fallback_price": 120,
        "type": "成熟製程晶圓代工", "life_cycle": "成熟製程、景氣循環、特殊製程需求",
        "features": {"ROE": "待蒐集", "FCF": "待蒐集", "EPS CAGR": "待蒐集", "負債": "待蒐集", "股利特徵": "待蒐集"},
        "model_scores": {"DCF-FCFF": 86, "EVA": 82, "EBO": 78, "PB-ROE": 72, "EV/EBITDA": 70},
        "valuation": None,
    },
    "2303 聯電": {
        "ticker": "2303.TW", "symbol": "2303.TW", "status": "待校準", "fallback_price": 48,
        "type": "成熟製程晶圓代工", "life_cycle": "成熟製程、景氣循環、股利與淨值支撐",
        "features": {"ROE": "待蒐集", "FCF": "待蒐集", "EPS CAGR": "待蒐集", "負債": "待蒐集", "股利特徵": "待蒐集"},
        "model_scores": {"PB-ROE": 84, "Dividend Yield": 78, "DCF-FCFF": 76, "EBO": 72, "EV/EBITDA": 70},
        "valuation": None,
    },
    "2383 台光電": {
        "ticker": "2383.TW", "symbol": "2383.TW", "status": "待校準", "fallback_price": 1300,
        "type": "AI PCB / 高階CCL", "life_cycle": "AI伺服器高速材料、成長溢價",
        "features": {"ROE": "待蒐集", "FCF": "待蒐集", "EPS CAGR": "待蒐集", "負債": "待蒐集", "股利特徵": "待蒐集"},
        "model_scores": {"AI Premium": 90, "Quality Compounder": 84, "DCF-FCFF": 78, "EV/EBITDA": 76, "EVA": 72},
        "valuation": None,
    },
}

# ------------------------------------------------------------
# Sidebar calibration center
# ------------------------------------------------------------
st.sidebar.header("Calibration Center")
pass_count = sum(1 for c in companies.values() if c.get("status") == "PASS")
watch_count = sum(1 for c in companies.values() if c.get("status") == "WATCH")
pending_count = sum(1 for c in companies.values() if c.get("status") == "待校準")
total_count = len(companies)
calibrated_rate = pass_count / total_count * 100 if total_count else 0

st.sidebar.metric("總公司數", total_count)
st.sidebar.metric("已校準 PASS", pass_count)
st.sidebar.metric("待校準", pending_count)
st.sidebar.metric("校準率", f"{calibrated_rate:.1f}%")
st.sidebar.caption("V5.2：先擴充第二批資料池，不對未校準公司硬給合理價。")

status_filter = st.sidebar.radio("顯示篩選", ["全部", "PASS", "待校準"])
options = list(companies.keys())
if status_filter != "全部":
    options = [k for k, v in companies.items() if v.get("status") == status_filter]

stock = st.selectbox("選擇公司", options)
company = companies[stock]
price, price_source = get_price(company)
valuation_result, weights = weighted_valuation(company, top_n=3)
cal_status, gap = calibration_result(price, valuation_result)

st.divider()

# ------------------------------------------------------------
# Main display
# ------------------------------------------------------------
st.header("一、公司定位")
c1, c2, c3, c4 = st.columns(4)
c1.metric("股票代號", company["symbol"])
c2.metric("公司類型", company["type"])
c3.metric("生命週期", company["life_cycle"])
c4.metric("校準狀態", company.get("status", "待校準"))

st.header("二、現價更新")
p1, p2 = st.columns(2)
p1.metric("現價", "N/A" if price is None else f"{price:,.2f}")
p2.metric("現價來源", price_source)

st.header("三、公司特徵")
feature_cols = st.columns(len(company["features"]))
for col, (k, v) in zip(feature_cols, company["features"].items()):
    col.metric(k, v)

st.header("四、模型適配分數")
score_df = pd.DataFrame([
    {"模型": m, "適配分數": s, "評級": rating(s)}
    for m, s in sorted(company["model_scores"].items(), key=lambda x: x[1], reverse=True)
])
st.dataframe(score_df, use_container_width=True)

st.header("五、保留 Top 模型")
if weights:
    cols = st.columns(len(weights))
    for col, (m, s, w) in zip(cols, weights):
        col.success(f"{m}\n\n分數 {s}｜權重 {w:.1%}")
else:
    top_candidates = list(sorted(company["model_scores"].items(), key=lambda x: x[1], reverse=True))[:3]
    cols = st.columns(len(top_candidates))
    for col, (m, s) in zip(cols, top_candidates):
        col.warning(f"{m}\n\n分數 {s}｜待校準")

st.header("六、估值區間")
if valuation_result:
    v1, v2, v3, v4 = st.columns(4)
    v1.metric("Bear 保守價", f"{valuation_result['bear']:,.0f}")
    v2.metric("Base 合理價", f"{valuation_result['base']:,.0f}")
    v3.metric("Bull 樂觀價", f"{valuation_result['bull']:,.0f}")
    v4.metric("校準結果", cal_status)

    verdict = judge_price(price, valuation_result)
    st.subheader(f"價格判斷：{verdict}")
    if gap is not None:
        st.write(f"Base 合理價相對現價差距：{gap:.1f}%")
    if cal_status == "PASS":
        st.success("校準通過：合理價與現價差距在可接受範圍內。")
    elif cal_status == "WATCH":
        st.warning("觀察：合理價與現價略有偏離，後續需微調權重。")
    else:
        st.error("FAIL：合理價與現價偏離過大，需要重新校準。")

    valuation_rows = []
    for m, v in company.get("valuation", {}).items():
        valuation_rows.append({
            "模型": m,
            "適配分數": company["model_scores"].get(m, 0),
            "Bear": v["bear"],
            "Base": v["base"],
            "Bull": v["bull"],
            "是否納入": "是" if any(m == x[0] for x in weights) else "否",
        })
    st.dataframe(pd.DataFrame(valuation_rows), use_container_width=True)
else:
    st.warning("此公司目前為『待校準』：已建立模型池與現價蒐集，但尚未建立 Bear/Base/Bull 估值區間。")

st.header("七、校準總表")
summary_rows = []
for name, comp in companies.items():
    p, src = get_price(comp)
    fair, ws = weighted_valuation(comp, top_n=3)
    status, g = calibration_result(p, fair)
    summary_rows.append({
        "公司": name,
        "代號": comp["symbol"],
        "類型": comp["type"],
        "資料狀態": comp.get("status", "待校準"),
        "現價": None if p is None else round(p, 2),
        "Base合理價": None if fair is None else round(fair["base"], 2),
        "偏離%": None if g is None else round(g, 1),
        "校準結果": status,
        "現價來源": src,
    })
st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)

st.header("八、匯出給主平台 JSON")
export_data = {}
for name, comp in companies.items():
    p, src = get_price(comp)
    fair, ws = weighted_valuation(comp, top_n=3)
    export_data[comp["symbol"]] = {
        "name": name,
        "type": comp["type"],
        "status": comp.get("status", "待校準"),
        "selected_models": [m for m, _, _ in ws] if ws else [m for m, _ in sorted(comp["model_scores"].items(), key=lambda x: x[1], reverse=True)[:3]],
        "weights": {m: round(w, 4) for m, _, w in ws} if ws else None,
        "valuation": {
            "bear": round(fair["bear"], 2),
            "base": round(fair["base"], 2),
            "bull": round(fair["bull"], 2),
        } if fair else None,
        "current_price": p,
        "price_source": src,
        "judgement": judge_price(p, fair) if fair else "待校準",
    }
st.code(json.dumps(export_data, ensure_ascii=False, indent=2), language="json")

st.caption(f"最後更新時間：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}")
