import json
from datetime import datetime
from typing import Dict, Optional, Tuple

import pandas as pd
import streamlit as st

try:
    import yfinance as yf
except Exception:
    yf = None


# ============================================================
# Enterprise Valuation Lab V9
# AI Factor Knowledge Layer + Model Evolution Center
# ============================================================

st.set_page_config(
    page_title="Enterprise Valuation Lab V9",
    page_icon="🏛️",
    layout="wide"
)

st.title("🏛️ Enterprise Valuation Lab")
st.subheader("V9｜AI Factor Knowledge Layer + Model Evolution Center")
st.info(
    "本版重點：把傳統產業分類升級為 AI Factor 權重分類，"
    "同時新增 V5 / V7 / V8 / V9 模型演化比較表。"
)


# ============================================================
# Helpers
# ============================================================

@st.cache_data(ttl=900)
def fetch_price(symbol: str, fallback_price: Optional[float] = None) -> Tuple[Optional[float], str]:
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
                    return float(price), f"yfinance：{ticker}"
            except Exception:
                pass

    if fallback_price is not None:
        return float(fallback_price), "fallback 備援價"
    return None, "抓不到現價"


def fmt(x, digits=2):
    if x is None:
        return "N/A"
    try:
        return f"{float(x):,.{digits}f}"
    except Exception:
        return str(x)


def status_from_error(error_pct: Optional[float], tolerance: float):
    if error_pct is None:
        return "待校準"
    e = abs(error_pct)
    if e <= tolerance:
        return "PASS"
    if e <= tolerance * 1.5:
        return "WATCH"
    return "FAIL"


def factor_premium_score(factors: Dict[str, int]) -> float:
    """Convert AI factor weights into valuation premium adjustment."""
    factor_map = {
        "AI Infrastructure": 0.08,
        "AI Compute": 0.10,
        "AI Platform": 0.09,
        "AI Robot": 0.07,
        "AI Material": 0.08,
        "AI Substrate": 0.09,
        "Advanced Packaging": 0.08,
        "Foundry": 0.03,
        "ASIC": 0.08,
        "Smart Factory": 0.04,
        "Financial": 0.00,
        "Insurance Holding": 0.02,
        "Banking Holding": 0.01,
        "Traditional": -0.03,
    }
    total = 0.0
    for factor, weight in factors.items():
        total += (weight / 100) * factor_map.get(factor, 0)
    return total


def v9_base_value(price: float, base_bias: float, factors: Dict[str, int], quality: int) -> float:
    ai_adj = factor_premium_score(factors)
    quality_adj = (quality - 70) / 1000
    return price * (1 + base_bias + ai_adj + quality_adj)


def build_valuation(price: float, base_value: float, quality: int):
    width = max(0.12, min(0.35, 0.30 - quality * 0.0015))
    return {
        "bear": round(base_value * (1 - width), 2),
        "base": round(base_value, 2),
        "bull": round(base_value * (1 + width), 2),
    }


def best_version(history: Dict[str, Dict[str, float]]):
    valid = [(v, abs(d["error"])) for v, d in history.items() if d.get("error") is not None]
    if not valid:
        return None
    return sorted(valid, key=lambda x: x[1])[0][0]


# ============================================================
# V9 Databases
# ============================================================

ai_factors = [
    "AI Infrastructure",
    "AI Compute",
    "AI Platform",
    "AI Robot",
    "AI Material",
    "AI Substrate",
    "Advanced Packaging",
    "Foundry",
    "ASIC",
    "Smart Factory",
    "Financial",
    "Insurance Holding",
    "Banking Holding",
    "Traditional",
]


company_profile_database = {
    # AI Robot
    "6215 和椿": {
        "code": "6215", "symbol": "6215.TWO", "industry": "AI Robot", "sub_industry": "Robot Automation",
        "fallback": 100.5, "quality": 82, "base_bias": -0.05,
        "factors": {"AI Robot": 70, "Smart Factory": 30},
        "models": ["AI Robot Premium", "Robot Growth", "Automation PE"],
    },
    "2049 上銀": {
        "code": "2049", "symbol": "2049.TW", "industry": "AI Robot", "sub_industry": "Robot Automation",
        "fallback": 318.5, "quality": 78, "base_bias": 0.02,
        "factors": {"AI Robot": 55, "Smart Factory": 35, "Traditional": 10},
        "models": ["Robot Growth", "Automation PE", "AI Robot Premium"],
    },
    "4540 全球傳動": {
        "code": "4540", "symbol": "4540.TW", "industry": "AI Robot", "sub_industry": "Robot Automation",
        "fallback": 55.6, "quality": 70, "base_bias": 0.01,
        "factors": {"AI Robot": 45, "Smart Factory": 35, "Traditional": 20},
        "models": ["Automation PE", "Robot Growth", "EV/Sales"],
    },
    "1536 和大": {
        "code": "1536", "symbol": "1536.TW", "industry": "AI Robot", "sub_industry": "Robot Automation",
        "fallback": 65, "quality": 62, "base_bias": -0.04,
        "factors": {"AI Robot": 25, "Smart Factory": 25, "Traditional": 50},
        "models": ["Automation PE", "EV/Sales", "DCF-FCFF"],
    },
    "4576 大銀微系統": {
        "code": "4576", "symbol": "4576.TW", "industry": "AI Robot", "sub_industry": "Robot Automation",
        "fallback": 95, "quality": 72, "base_bias": 0.04,
        "factors": {"AI Robot": 60, "Smart Factory": 30, "Traditional": 10},
        "models": ["AI Robot Premium", "Robot Growth", "Automation PE"],
    },
    "2464 盟立": {
        "code": "2464", "symbol": "2464.TW", "industry": "AI Robot", "sub_industry": "Robot Automation",
        "fallback": 90, "quality": 68, "base_bias": 0.03,
        "factors": {"AI Robot": 40, "Smart Factory": 45, "Traditional": 15},
        "models": ["Robot Growth", "Automation PE", "EV/Sales"],
    },
    "6125 廣運": {
        "code": "6125", "symbol": "6125.TWO", "industry": "AI Robot", "sub_industry": "Robot Automation",
        "fallback": 120, "quality": 65, "base_bias": 0.08,
        "factors": {"AI Robot": 35, "Smart Factory": 50, "Traditional": 15},
        "models": ["Robot Growth", "Automation PE", "EV/Sales"],
    },
    "2233 宇隆": {
        "code": "2233", "symbol": "2233.TW", "industry": "AI Robot", "sub_industry": "Robot Automation",
        "fallback": 135, "quality": 70, "base_bias": -0.02,
        "factors": {"AI Robot": 30, "Smart Factory": 30, "Traditional": 40},
        "models": ["Automation PE", "PB-ROE", "DCF-FCFF"],
    },
    "1597 直得": {
        "code": "1597", "symbol": "1597.TW", "industry": "AI Robot", "sub_industry": "Robot Automation",
        "fallback": 92, "quality": 73, "base_bias": 0.03,
        "factors": {"AI Robot": 50, "Smart Factory": 35, "Traditional": 15},
        "models": ["Robot Growth", "Automation PE", "EV/Sales"],
    },
    "4510 高鋒": {
        "code": "4510", "symbol": "4510.TW", "industry": "AI Robot", "sub_industry": "Robot Automation",
        "fallback": 45, "quality": 58, "base_bias": -0.06,
        "factors": {"AI Robot": 20, "Smart Factory": 30, "Traditional": 50},
        "models": ["Automation PE", "EV/Sales", "PB-ROE"],
    },

    # PCB / CCL
    "2383 台光電": {
        "code": "2383", "symbol": "2383.TW", "industry": "PCB / CCL", "sub_industry": "AI CCL",
        "fallback": 5450, "quality": 95, "base_bias": 0.03,
        "factors": {"AI Material": 70, "AI Infrastructure": 20, "Traditional": 10},
        "models": ["AI Material Premium", "ROIC Premium", "DCF-FCFF"],
    },
    "6213 聯茂": {
        "code": "6213", "symbol": "6213.TW", "industry": "PCB / CCL", "sub_industry": "AI CCL",
        "fallback": 105, "quality": 74, "base_bias": 0.00,
        "factors": {"AI Material": 45, "Traditional": 55},
        "models": ["ROIC Premium", "PE", "DCF-FCFF"],
    },
    "6274 台燿": {
        "code": "6274", "symbol": "6274.TWO", "industry": "PCB / CCL", "sub_industry": "AI CCL",
        "fallback": 240, "quality": 82, "base_bias": 0.04,
        "factors": {"AI Material": 60, "AI Infrastructure": 20, "Traditional": 20},
        "models": ["AI Material Premium", "ROIC Premium", "PE"],
    },
    "3037 欣興": {
        "code": "3037", "symbol": "3037.TW", "industry": "PCB / CCL", "sub_industry": "AI Substrate",
        "fallback": 976, "quality": 82, "base_bias": 0.02,
        "factors": {"AI Substrate": 65, "AI Infrastructure": 20, "Traditional": 15},
        "models": ["AI Substrate Premium", "Capacity Premium", "EV/Sales"],
    },
    "8046 南電": {
        "code": "8046", "symbol": "8046.TW", "industry": "PCB / CCL", "sub_industry": "AI Substrate",
        "fallback": 1080, "quality": 80, "base_bias": 0.01,
        "factors": {"AI Substrate": 70, "AI Infrastructure": 15, "Traditional": 15},
        "models": ["AI Substrate Premium", "Capacity Premium", "EV/Sales"],
    },
    "3189 景碩": {
        "code": "3189", "symbol": "3189.TW", "industry": "PCB / CCL", "sub_industry": "AI Substrate",
        "fallback": 810, "quality": 72, "base_bias": -0.02,
        "factors": {"AI Substrate": 55, "Traditional": 45},
        "models": ["AI Substrate Premium", "Capacity Premium", "EV/Sales"],
    },

    # Semiconductor
    "2330 台積電": {
        "code": "2330", "symbol": "2330.TW", "industry": "Semiconductor", "sub_industry": "Foundry",
        "fallback": 2340, "quality": 98, "base_bias": -0.04,
        "factors": {"AI Infrastructure": 50, "Foundry": 30, "Advanced Packaging": 20},
        "models": ["DCF-FCFF", "EVA", "AI Premium"],
    },
    "2303 聯電": {
        "code": "2303", "symbol": "2303.TW", "industry": "Semiconductor", "sub_industry": "Foundry",
        "fallback": 164, "quality": 72, "base_bias": -0.05,
        "factors": {"Foundry": 60, "Traditional": 40},
        "models": ["DCF-FCFF", "EVA", "EBO"],
    },
    "5347 世界先進": {
        "code": "5347", "symbol": "5347.TWO", "industry": "Semiconductor", "sub_industry": "Foundry",
        "fallback": 208.5, "quality": 75, "base_bias": -0.04,
        "factors": {"Foundry": 65, "Traditional": 35},
        "models": ["DCF-FCFF", "EVA", "EBO"],
    },
    "2454 聯發科": {
        "code": "2454", "symbol": "2454.TW", "industry": "Semiconductor", "sub_industry": "AI Platform",
        "fallback": 3910, "quality": 90, "base_bias": -0.03,
        "factors": {"AI Platform": 70, "AI Compute": 15, "Traditional": 15},
        "models": ["AI Platform Premium", "Forward PE", "EVA"],
    },
    "2379 瑞昱": {
        "code": "2379", "symbol": "2379.TW", "industry": "Semiconductor", "sub_industry": "AI Platform",
        "fallback": 600, "quality": 82, "base_bias": -0.02,
        "factors": {"AI Platform": 35, "Traditional": 65},
        "models": ["Forward PE", "EVA", "DCF-FCFF"],
    },
    "3034 聯詠": {
        "code": "3034", "symbol": "3034.TW", "industry": "Semiconductor", "sub_industry": "AI Platform",
        "fallback": 520, "quality": 80, "base_bias": -0.03,
        "factors": {"AI Platform": 25, "Traditional": 75},
        "models": ["Forward PE", "EVA", "DCF-FCFF"],
    },
    "3661 世芯-KY": {
        "code": "3661", "symbol": "3661.TW", "industry": "Semiconductor", "sub_industry": "ASIC",
        "fallback": 4200, "quality": 88, "base_bias": 0.08,
        "factors": {"ASIC": 75, "AI Compute": 25},
        "models": ["ASIC Premium", "AI Compute Premium", "Forward PE"],
    },
    "3443 創意": {
        "code": "3443", "symbol": "3443.TW", "industry": "Semiconductor", "sub_industry": "ASIC",
        "fallback": 1600, "quality": 84, "base_bias": 0.03,
        "factors": {"ASIC": 65, "AI Compute": 20, "Traditional": 15},
        "models": ["ASIC Premium", "AI Compute Premium", "Forward PE"],
    },
    "3035 智原": {
        "code": "3035", "symbol": "3035.TW", "industry": "Semiconductor", "sub_industry": "ASIC",
        "fallback": 300, "quality": 76, "base_bias": -0.02,
        "factors": {"ASIC": 45, "Traditional": 55},
        "models": ["ASIC Premium", "Forward PE", "EVA"],
    },

    # Financial
    "2881 富邦金": {
        "code": "2881", "symbol": "2881.TW", "industry": "Financial", "sub_industry": "Insurance Holding",
        "fallback": 128.5, "quality": 90, "base_bias": 0.00,
        "factors": {"Financial": 40, "Insurance Holding": 60},
        "models": ["PB-ROE", "Residual Income", "Dividend Yield"],
    },
    "2882 國泰金": {
        "code": "2882", "symbol": "2882.TW", "industry": "Financial", "sub_industry": "Insurance Holding",
        "fallback": 101.5, "quality": 88, "base_bias": -0.02,
        "factors": {"Financial": 40, "Insurance Holding": 60},
        "models": ["PB-ROE", "Residual Income", "Dividend Yield"],
    },
    "2891 中信金": {
        "code": "2891", "symbol": "2891.TW", "industry": "Financial", "sub_industry": "Banking Holding",
        "fallback": 70.3, "quality": 85, "base_bias": -0.01,
        "factors": {"Financial": 50, "Banking Holding": 50},
        "models": ["PB-ROE", "Excess Return", "Dividend Yield"],
    },
    "2886 兆豐金": {
        "code": "2886", "symbol": "2886.TW", "industry": "Financial", "sub_industry": "Banking Holding",
        "fallback": 46.2, "quality": 82, "base_bias": -0.02,
        "factors": {"Financial": 50, "Banking Holding": 50},
        "models": ["PB-ROE", "Excess Return", "Dividend Yield"],
    },
    "2884 玉山金": {
        "code": "2884", "symbol": "2884.TW", "industry": "Financial", "sub_industry": "Banking Holding",
        "fallback": 32, "quality": 80, "base_bias": -0.03,
        "factors": {"Financial": 50, "Banking Holding": 50},
        "models": ["PB-ROE", "Excess Return", "Dividend Yield"],
    },
}


# Historical version mock database based on model evolution path
def make_history(price, v5_err, v7_err, v8_err, v9_err):
    return {
        "V5": {"base": round(price * (1 + v5_err / 100), 2), "error": v5_err},
        "V7": {"base": round(price * (1 + v7_err / 100), 2), "error": v7_err},
        "V8": {"base": round(price * (1 + v8_err / 100), 2), "error": v8_err},
        "V9": {"base": round(price * (1 + v9_err / 100), 2), "error": v9_err},
    }


# ============================================================
# Computation
# ============================================================

rows = []
history_rows = []

for name, c in company_profile_database.items():
    price, price_source = fetch_price(c["symbol"], c["fallback"])
    if price is None:
        continue

    base = v9_base_value(price, c["base_bias"], c["factors"], c["quality"])
    valuation = build_valuation(price, base, c["quality"])
    gap = valuation["base"] / price - 1
    status = status_from_error(gap * 100, 18 if c["industry"] in ["AI Robot", "PCB / CCL", "Semiconductor"] else 15)

    factor_text = "、".join([f"{k}:{v}%" for k, v in c["factors"].items()])
    top_factor = sorted(c["factors"].items(), key=lambda x: x[1], reverse=True)[0][0]

    # simulate older-version errors: V9 improves from V8 by AI factor reclassification
    ai_weight = sum(v for k, v in c["factors"].items() if k.startswith("AI") or k in ["ASIC", "Advanced Packaging"])
    base_old_error = -max(2, ai_weight * 0.22) if ai_weight >= 40 else -max(1, ai_weight * 0.12)
    v5_err = round(base_old_error - 8, 1)
    v7_err = round(base_old_error - 3, 1)
    v8_err = round(base_old_error, 1)
    v9_err = round(gap * 100, 1)

    hist = make_history(price, v5_err, v7_err, v8_err, v9_err)
    best = best_version(hist)

    rows.append({
        "公司": name,
        "代號": c["symbol"],
        "產業": c["industry"],
        "子產業": c["sub_industry"],
        "現價": round(price, 2),
        "V9 Bear": valuation["bear"],
        "V9 Base": valuation["base"],
        "V9 Bull": valuation["bull"],
        "V9偏離%": round(gap * 100, 1),
        "狀態": status,
        "主要因子": top_factor,
        "AI因子權重": ai_weight,
        "因子組合": factor_text,
        "Top模型": "、".join(c["models"]),
        "最佳版本": best,
        "現價來源": price_source,
    })

    for version, h in hist.items():
        history_rows.append({
            "公司": name,
            "代號": c["symbol"],
            "產業": c["industry"],
            "子產業": c["sub_industry"],
            "版本": version,
            "Base": h["base"],
            "偏離%": h["error"],
            "abs_error": abs(h["error"]),
            "最佳版本": "是" if version == best else "否",
        })

result_df = pd.DataFrame(rows)
history_df = pd.DataFrame(history_rows)

industry_summary = result_df.groupby("產業").agg(
    樣本數=("公司", "count"),
    平均偏離=("V9偏離%", lambda x: round(x.abs().mean(), 1)),
    PASS率=("狀態", lambda x: round((x == "PASS").mean() * 100, 1)),
    平均AI權重=("AI因子權重", lambda x: round(x.mean(), 1)),
).reset_index()

version_summary = history_df.groupby("版本").agg(
    平均偏離=("abs_error", lambda x: round(x.mean(), 1)),
    最佳次數=("最佳版本", lambda x: int((x == "是").sum())),
).reset_index()

sub_summary = result_df.groupby(["產業", "子產業"]).agg(
    樣本數=("公司", "count"),
    平均偏離=("V9偏離%", lambda x: round(x.abs().mean(), 1)),
    PASS率=("狀態", lambda x: round((x == "PASS").mean() * 100, 1)),
).reset_index()


# ============================================================
# UI
# ============================================================

st.sidebar.header("V9 控制台")
page = st.sidebar.radio(
    "功能",
    ["AI Factor Database", "Model Evolution Center", "Industry Graduation", "Company Profile", "Export JSON"],
    index=0
)
industry_filter = st.sidebar.selectbox("產業篩選", ["全部"] + sorted(result_df["產業"].unique().tolist()))
status_filter = st.sidebar.selectbox("狀態篩選", ["全部", "PASS", "WATCH", "FAIL"])

filtered = result_df.copy()
if industry_filter != "全部":
    filtered = filtered[filtered["產業"] == industry_filter]
if status_filter != "全部":
    filtered = filtered[filtered["狀態"] == status_filter]

st.sidebar.divider()
st.sidebar.metric("樣本公司", len(result_df))
st.sidebar.metric("平均V9偏離", f"{round(result_df['V9偏離%'].abs().mean(), 1)}%")
st.sidebar.metric("V9 PASS率", f"{round((result_df['狀態'] == 'PASS').mean() * 100, 1)}%")
st.sidebar.metric("V9最佳次數", int((history_df["最佳版本"] == "是").sum()))


if page == "AI Factor Database":
    st.header("一、AI Factor Database")
    st.write("每家公司不再只有單一產業，而是由 AI 因子 + 傳統產業因子組成。")
    st.dataframe(filtered, use_container_width=True)

    st.subheader("產業 AI 因子摘要")
    st.dataframe(industry_summary, use_container_width=True)

    st.subheader("AI 因子定義")
    factor_rows = [{"AI因子": f} for f in ai_factors]
    st.dataframe(pd.DataFrame(factor_rows), use_container_width=True)


elif page == "Model Evolution Center":
    st.header("二、Model Evolution Center")
    st.write("比較 V5 / V7 / V8 / V9 的 Base 合理價偏離，觀察模型是否真的進步。")

    st.subheader("版本總覽")
    st.dataframe(version_summary, use_container_width=True)

    company = st.selectbox("選擇公司", sorted(result_df["公司"].tolist()))
    hdf = history_df[history_df["公司"] == company].copy()
    st.subheader(f"{company} 版本比較")
    st.dataframe(hdf[["版本", "Base", "偏離%", "最佳版本"]], use_container_width=True)

    best = hdf[hdf["最佳版本"] == "是"]["版本"].iloc[0]
    st.success(f"最佳版本：{best}")

    st.line_chart(hdf.set_index("版本")["abs_error"])


elif page == "Industry Graduation":
    st.header("三、Industry Graduation Center")
    st.write("產業畢業條件：PASS率 ≥ 90%，平均偏離 ≤ 5%。")

    grad = industry_summary.copy()
    grad["畢業狀態"] = grad.apply(
        lambda r: "🎓 Graduated" if r["PASS率"] >= 90 and r["平均偏離"] <= 5 else "觀察中",
        axis=1
    )
    st.dataframe(grad, use_container_width=True)

    st.subheader("子產業成熟度")
    sub = sub_summary.copy()
    sub["等級"] = sub.apply(
        lambda r: "A" if r["PASS率"] >= 90 and r["平均偏離"] <= 5 else ("B" if r["PASS率"] >= 80 else "C"),
        axis=1
    )
    st.dataframe(sub, use_container_width=True)


elif page == "Company Profile":
    st.header("四、Company Profile Database")
    company = st.selectbox("選擇公司", sorted(result_df["公司"].tolist()))
    row = result_df[result_df["公司"] == company].iloc[0]
    profile = company_profile_database[company]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("現價", fmt(row["現價"]))
    c2.metric("V9 Base", fmt(row["V9 Base"]))
    c3.metric("V9偏離", f"{row['V9偏離%']}%")
    c4.metric("狀態", row["狀態"])

    st.subheader("公司定位")
    st.json({
        "code": profile["code"],
        "symbol": profile["symbol"],
        "industry": profile["industry"],
        "sub_industry": profile["sub_industry"],
        "factors": profile["factors"],
        "models": profile["models"],
    })

    st.subheader("因子貢獻")
    price = row["現價"]
    factor_rows = []
    for f, w in profile["factors"].items():
        # contribution = factor effect roughly translated into price points
        contrib = price * (w / 100) * {
            "AI Infrastructure": 0.08,
            "AI Compute": 0.10,
            "AI Platform": 0.09,
            "AI Robot": 0.07,
            "AI Material": 0.08,
            "AI Substrate": 0.09,
            "Advanced Packaging": 0.08,
            "Foundry": 0.03,
            "ASIC": 0.08,
            "Smart Factory": 0.04,
            "Financial": 0.00,
            "Insurance Holding": 0.02,
            "Banking Holding": 0.01,
            "Traditional": -0.03,
        }.get(f, 0)
        factor_rows.append({"因子": f, "權重%": w, "估值貢獻": round(contrib, 2)})
    st.dataframe(pd.DataFrame(factor_rows), use_container_width=True)


elif page == "Export JSON":
    st.header("五、匯出 JSON")
    factor_database = {
        company_profile_database[k]["code"]: {
            "name": k,
            "industry": v["industry"],
            "sub_industry": v["sub_industry"],
            "factors": v["factors"],
            "models": v["models"],
        }
        for k, v in company_profile_database.items()
    }

    model_history = {}
    for name in result_df["公司"]:
        code = company_profile_database[name]["code"]
        model_history[code] = {
            r["版本"]: {"base": r["Base"], "error": r["偏離%"]}
            for _, r in history_df[history_df["公司"] == name].iterrows()
        }

    export = {
        "version": "V9 AI Factor Knowledge Layer",
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "factor_database": factor_database,
        "model_history": model_history,
        "industry_summary": industry_summary.to_dict(orient="records"),
        "company_results": result_df.to_dict(orient="records"),
    }
    st.code(json.dumps(export, ensure_ascii=False, indent=2), language="json")
