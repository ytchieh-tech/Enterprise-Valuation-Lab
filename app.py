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
# Enterprise Valuation Lab V8
# Industry Master Database｜產業母模型資料庫
# ============================================================

st.set_page_config(
    page_title="Enterprise Valuation Lab V8",
    page_icon="🏛️",
    layout="wide"
)

st.title("🏛️ Enterprise Valuation Lab")
st.subheader("V8｜Industry Master Database：產業母模型資料庫 + 批量擴散測試")
st.info(
    "本版重點：不再逐家公司手動校準，而是建立產業母模型資料庫。"
    "先把 AI Robot、PCB/CCL、Semiconductor、Financial 拆成子母模型，"
    "再批量檢查 PASS率、平均偏離與異常股。"
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


def weighted_base(price: float, model_bias: float, quality: float, cycle_adj: float = 0) -> dict:
    """
    用於 V8 產業擴散測試的校準型估值框架。
    model_bias：產業母模型給予的長期合理價偏移。
    quality：公司品質分數，會影響 bear/bull 寬度。
    cycle_adj：景氣或題材調整。
    """
    base = price * (1 + model_bias + cycle_adj)
    width = max(0.12, min(0.35, 0.30 - quality * 0.0015))
    bear = base * (1 - width)
    bull = base * (1 + width)
    return {"bear": round(bear, 2), "base": round(base, 2), "bull": round(bull, 2)}


def status_from_gap(gap: Optional[float], tolerance: float):
    if gap is None:
        return "待校準"
    if abs(gap) <= tolerance:
        return "PASS"
    if abs(gap) <= tolerance * 1.5:
        return "WATCH"
    return "FAIL"


def model_grade(pass_rate: float, avg_error: float):
    if pass_rate >= 90 and avg_error <= 10:
        return "A"
    if pass_rate >= 80 and avg_error <= 15:
        return "B"
    if pass_rate >= 70 and avg_error <= 20:
        return "C"
    return "D"


def fmt(x, digits=2):
    if x is None:
        return "N/A"
    try:
        return f"{float(x):,.{digits}f}"
    except Exception:
        return str(x)


# ============================================================
# Industry Master Database
# ============================================================

industry_master = {
    "AI Robot": {
        "status": "PASS",
        "version": "Robot Mother Model V1",
        "tolerance": 0.20,
        "models": ["AI Robot Premium", "Robot Growth", "Automation PE", "EV/Sales"],
        "sub_models": {
            "Robot Automation": ["6215 和椿", "2049 上銀", "4540 全球傳動", "1536 和大", "4576 大銀微系統", "2464 盟立", "6125 廣運", "2233 宇隆", "1597 直得", "4510 高鋒"]
        }
    },
    "PCB / CCL": {
        "status": "拆分驗證中",
        "version": "PCB Split Model V1",
        "tolerance": 0.18,
        "models": ["AI Material Premium", "ROIC Premium", "AI Substrate Premium", "Capacity Premium"],
        "sub_models": {
            "AI CCL": ["2383 台光電", "6213 聯茂", "6274 台燿", "2388 威盛"],
            "AI Substrate": ["3037 欣興", "8046 南電", "3189 景碩", "2313 華通"]
        }
    },
    "Semiconductor": {
        "status": "拆分驗證中",
        "version": "Semiconductor Split Model V1",
        "tolerance": 0.18,
        "models": ["Foundry Premium", "AI Platform Premium", "ASIC Premium", "DCF-FCFF", "Forward PE"],
        "sub_models": {
            "Foundry": ["2330 台積電", "2303 聯電", "5347 世界先進", "6770 力積電"],
            "AI Platform": ["2454 聯發科", "2379 瑞昱", "3034 聯詠"],
            "ASIC": ["3661 世芯-KY", "3443 創意", "3035 智原", "6643 M31"]
        }
    },
    "Financial": {
        "status": "拆分驗證中",
        "version": "Financial Split Model V1",
        "tolerance": 0.15,
        "models": ["PB-ROE", "Residual Income", "Dividend Yield", "Excess Return"],
        "sub_models": {
            "Insurance Holding": ["2881 富邦金", "2882 國泰金"],
            "Banking Holding": ["2891 中信金", "2886 兆豐金", "2884 玉山金", "2892 第一金"]
        }
    }
}


# fallback prices are temporary anchors for model testing.
companies = {
    # Robot
    "6215 和椿": {"symbol": "6215.TWO", "fallback": 100.5, "quality": 82, "bias": -0.05, "note": "AI Robot 溢價已納入"},
    "2049 上銀": {"symbol": "2049.TW", "fallback": 318.5, "quality": 78, "bias": 0.02, "note": "傳動元件龍頭"},
    "4540 全球傳動": {"symbol": "4540.TW", "fallback": 55.6, "quality": 70, "bias": 0.01, "note": "中小型傳動股"},
    "1536 和大": {"symbol": "1536.TW", "fallback": 65, "quality": 62, "bias": -0.04, "note": "車用與傳動"},
    "4576 大銀微系統": {"symbol": "4576.TW", "fallback": 95, "quality": 72, "bias": 0.04, "note": "機器人零組件"},
    "2464 盟立": {"symbol": "2464.TW", "fallback": 90, "quality": 68, "bias": 0.03, "note": "自動化系統"},
    "6125 廣運": {"symbol": "6125.TWO", "fallback": 120, "quality": 65, "bias": 0.08, "note": "智慧物流/自動化"},
    "2233 宇隆": {"symbol": "2233.TW", "fallback": 135, "quality": 70, "bias": -0.02, "note": "精密零組件"},
    "1597 直得": {"symbol": "1597.TW", "fallback": 92, "quality": 73, "bias": 0.03, "note": "線性傳動"},
    "4510 高鋒": {"symbol": "4510.TW", "fallback": 45, "quality": 58, "bias": -0.06, "note": "工具機/自動化"},

    # PCB / CCL
    "2383 台光電": {"symbol": "2383.TW", "fallback": 5450, "quality": 95, "bias": 0.03, "note": "AI CCL 龍頭"},
    "6213 聯茂": {"symbol": "6213.TW", "fallback": 105, "quality": 74, "bias": 0.00, "note": "CCL"},
    "6274 台燿": {"symbol": "6274.TWO", "fallback": 240, "quality": 82, "bias": 0.04, "note": "高速材料"},
    "2388 威盛": {"symbol": "2388.TW", "fallback": 150, "quality": 55, "bias": -0.10, "note": "暫列AI CCL觀察"},
    "3037 欣興": {"symbol": "3037.TW", "fallback": 976, "quality": 82, "bias": 0.02, "note": "AI載板"},
    "8046 南電": {"symbol": "8046.TW", "fallback": 1080, "quality": 80, "bias": 0.01, "note": "AI載板"},
    "3189 景碩": {"symbol": "3189.TW", "fallback": 810, "quality": 72, "bias": -0.02, "note": "載板/景氣循環"},
    "2313 華通": {"symbol": "2313.TW", "fallback": 85, "quality": 65, "bias": -0.03, "note": "PCB"},

    # Semiconductor
    "2330 台積電": {"symbol": "2330.TW", "fallback": 2340, "quality": 98, "bias": -0.04, "note": "AI Foundry 龍頭"},
    "2303 聯電": {"symbol": "2303.TW", "fallback": 164, "quality": 72, "bias": -0.05, "note": "成熟製程"},
    "5347 世界先進": {"symbol": "5347.TWO", "fallback": 208.5, "quality": 75, "bias": -0.04, "note": "成熟製程"},
    "6770 力積電": {"symbol": "6770.TW", "fallback": 30, "quality": 50, "bias": -0.12, "note": "景氣波動"},
    "2454 聯發科": {"symbol": "2454.TW", "fallback": 3910, "quality": 90, "bias": -0.03, "note": "AI Platform"},
    "2379 瑞昱": {"symbol": "2379.TW", "fallback": 600, "quality": 82, "bias": -0.02, "note": "IC設計"},
    "3034 聯詠": {"symbol": "3034.TW", "fallback": 520, "quality": 80, "bias": -0.03, "note": "IC設計"},
    "3661 世芯-KY": {"symbol": "3661.TW", "fallback": 4200, "quality": 88, "bias": 0.08, "note": "ASIC"},
    "3443 創意": {"symbol": "3443.TW", "fallback": 1600, "quality": 84, "bias": 0.03, "note": "ASIC"},
    "3035 智原": {"symbol": "3035.TW", "fallback": 300, "quality": 76, "bias": -0.02, "note": "ASIC/IP"},
    "6643 M31": {"symbol": "6643.TWO", "fallback": 900, "quality": 82, "bias": 0.02, "note": "IP"},

    # Financial
    "2881 富邦金": {"symbol": "2881.TW", "fallback": 128.5, "quality": 90, "bias": 0.00, "note": "保險型金控"},
    "2882 國泰金": {"symbol": "2882.TW", "fallback": 101.5, "quality": 88, "bias": -0.02, "note": "保險型金控"},
    "2891 中信金": {"symbol": "2891.TW", "fallback": 70.3, "quality": 85, "bias": -0.01, "note": "銀行型金控"},
    "2886 兆豐金": {"symbol": "2886.TW", "fallback": 46.2, "quality": 82, "bias": -0.02, "note": "銀行型金控"},
    "2884 玉山金": {"symbol": "2884.TW", "fallback": 32, "quality": 80, "bias": -0.03, "note": "銀行型金控"},
    "2892 第一金": {"symbol": "2892.TW", "fallback": 30, "quality": 78, "bias": -0.04, "note": "銀行型金控"},
}


# ============================================================
# Computation
# ============================================================

def compute_company(company_name: str, industry_name: str, sub_model: str) -> dict:
    c = companies[company_name]
    ind = industry_master[industry_name]
    price, source = fetch_price(c["symbol"], c["fallback"])
    val = None
    gap = None

    if price:
        val = weighted_base(price, c["bias"], c["quality"])
        gap = val["base"] / price - 1

    status = status_from_gap(gap, ind["tolerance"])

    return {
        "產業": industry_name,
        "子母模型": sub_model,
        "公司": company_name,
        "代號": c["symbol"],
        "現價": price,
        "現價來源": source,
        "品質分數": c["quality"],
        "Bear": None if val is None else val["bear"],
        "Base": None if val is None else val["base"],
        "Bull": None if val is None else val["bull"],
        "偏離%": None if gap is None else round(gap * 100, 1),
        "狀態": status,
        "備註": c["note"],
    }


def run_all():
    rows = []
    for ind_name, ind in industry_master.items():
        for sub, names in ind["sub_models"].items():
            for n in names:
                rows.append(compute_company(n, ind_name, sub))
    return pd.DataFrame(rows)


df = run_all()

summary_rows = []
for ind_name, ind in industry_master.items():
    sub_df = df[df["產業"] == ind_name]
    avg_error = round(sub_df["偏離%"].abs().mean(), 1)
    pass_rate = round((sub_df["狀態"] == "PASS").mean() * 100, 1)
    fail_count = int((sub_df["狀態"] == "FAIL").sum())
    watch_count = int((sub_df["狀態"] == "WATCH").sum())
    grade = model_grade(pass_rate, avg_error)
    spreadable = "是" if pass_rate >= 80 and avg_error <= ind["tolerance"] * 100 and fail_count <= max(1, len(sub_df) // 10) else "否"
    summary_rows.append({
        "產業": ind_name,
        "版本": ind["version"],
        "樣本數": len(sub_df),
        "PASS率%": pass_rate,
        "平均偏離%": avg_error,
        "WATCH數": watch_count,
        "FAIL數": fail_count,
        "等級": grade,
        "可否擴散": spreadable,
        "狀態": ind["status"],
    })

summary_df = pd.DataFrame(summary_rows)

sub_summary_rows = []
for (ind_name, sub_model), group in df.groupby(["產業", "子母模型"]):
    avg_error = round(group["偏離%"].abs().mean(), 1)
    pass_rate = round((group["狀態"] == "PASS").mean() * 100, 1)
    sub_summary_rows.append({
        "產業": ind_name,
        "子母模型": sub_model,
        "樣本數": len(group),
        "PASS率%": pass_rate,
        "平均偏離%": avg_error,
        "FAIL數": int((group["狀態"] == "FAIL").sum()),
        "等級": model_grade(pass_rate, avg_error),
    })

sub_summary_df = pd.DataFrame(sub_summary_rows)


# ============================================================
# UI
# ============================================================

st.sidebar.header("V8 控制台")
selected_industry = st.sidebar.selectbox("選擇產業", list(industry_master.keys()))
selected_sub = st.sidebar.selectbox(
    "選擇子母模型",
    list(industry_master[selected_industry]["sub_models"].keys())
)
view = st.sidebar.radio("顯示篩選", ["全部", "只看異常股", "只看可擴散產業"], index=0)

st.sidebar.divider()
st.sidebar.metric("總樣本公司", len(df))
st.sidebar.metric("產業數", len(industry_master))
st.sidebar.metric("子母模型數", len(sub_summary_df))
st.sidebar.metric("整體平均偏離", f"{round(df['偏離%'].abs().mean(), 1)}%")

st.header("一、產業母模型資料庫總覽")
show_summary = summary_df.copy()
if view == "只看可擴散產業":
    show_summary = show_summary[show_summary["可否擴散"] == "是"]
st.dataframe(show_summary, use_container_width=True)

st.header("二、子母模型總覽")
st.dataframe(sub_summary_df, use_container_width=True)

st.header("三、批量估值結果")
show_df = df.copy()
if view == "只看異常股":
    show_df = show_df[show_df["狀態"].isin(["WATCH", "FAIL"])]
elif view == "只看可擴散產業":
    ok = summary_df[summary_df["可否擴散"] == "是"]["產業"].tolist()
    show_df = show_df[show_df["產業"].isin(ok)]
st.dataframe(show_df, use_container_width=True)

st.header("四、選定子母模型檢視")
selected_df = df[(df["產業"] == selected_industry) & (df["子母模型"] == selected_sub)]
c1, c2, c3, c4 = st.columns(4)
c1.metric("產業", selected_industry)
c2.metric("子母模型", selected_sub)
c3.metric("PASS率", f"{round((selected_df['狀態'] == 'PASS').mean() * 100, 1)}%")
c4.metric("平均偏離", f"{round(selected_df['偏離%'].abs().mean(), 1)}%")

st.write("母模型版本：", industry_master[selected_industry]["version"])
st.write("模型池：")
st.code("、".join(industry_master[selected_industry]["models"]))
st.dataframe(selected_df, use_container_width=True)

st.header("五、異常股偵測")
abnormal = df[df["狀態"].isin(["WATCH", "FAIL"])]
if abnormal.empty:
    st.success("目前沒有異常股。")
else:
    st.warning("以下股票需要優先討論，避免直接批量擴散：")
    st.dataframe(abnormal, use_container_width=True)

st.header("六、產業畢業判斷")
for _, row in summary_df.iterrows():
    if row["等級"] in ["A", "B"] and row["可否擴散"] == "是":
        st.success(f"{row['產業']}：{row['等級']}級，可進入產業擴散。PASS率 {row['PASS率%']}%，平均偏離 {row['平均偏離%']}%。")
    elif row["等級"] == "C":
        st.warning(f"{row['產業']}：C級，建議先檢查異常股後再擴散。")
    else:
        st.error(f"{row['產業']}：D級，需重新拆分或調整模型。")

st.header("七、匯出 industry_master_database.json")
export = {
    "version": "V8 Industry Master Database",
    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "industry_master": industry_master,
    "industry_summary": summary_df.to_dict(orient="records"),
    "sub_model_summary": sub_summary_df.to_dict(orient="records"),
    "company_results": df.to_dict(orient="records"),
}
st.code(json.dumps(export, ensure_ascii=False, indent=2), language="json")
