
import json
from datetime import datetime
import pandas as pd
import streamlit as st

try:
    import yfinance as yf
except Exception:
    yf = None

st.set_page_config(page_title="Enterprise Valuation Lab V12", page_icon="🏛️", layout="wide")
st.title("🏛️ Enterprise Valuation Lab")
st.subheader("V12｜V10 + V11 Hybrid Engine")
st.info("V12 架構：V10 負責估值，V11 負責判斷公司情境與模型排序；情境只做保守微調，不直接大幅拉高估值。")

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

def classify_state(x):
    rev, eps = x["Revenue_CAGR"], x["EPS_CAGR"]
    roe, roic = x["ROE"], x["ROIC"]
    fcf = x["FCF_Margin"]
    pb, pe = x["PB"], x["PE"]
    cycle = x["Cycle_Score"]
    vdf = x["VDF_Exposure"]
    debt = x["Debt_Ratio"]

    if cycle <= 25 and pb <= 1.2:
        return "Cycle Bottom / Asset Recovery"
    if cycle >= 80 and rev >= 20 and eps >= 25:
        return "Super Cycle Growth"
    if vdf >= 70 and rev >= 15:
        return "VDF Re-rating"
    if rev >= 30 or eps >= 35:
        return "Hyper Growth"
    if roic >= 25 and roe >= 25 and fcf >= 15:
        return "Quality Compounder"
    if debt <= 30 and fcf >= 10 and roe >= 12:
        return "Stable Cash Flow"
    if pe <= 12 and pb <= 1.5:
        return "Value / Mean Reversion"
    return "Normal Operating"

STATE_MODEL_MAP = {
    "Hyper Growth": ["Growth Premium", "Forward PE", "EV/Sales"],
    "Quality Compounder": ["ROIC Premium", "DCF-FCFF", "EVA"],
    "VDF Re-rating": ["VDF Premium", "Forward PE", "Multiple Expansion"],
    "Cycle Bottom / Asset Recovery": ["PB-ROE", "Asset Value", "Cycle PB"],
    "Super Cycle Growth": ["Cycle PE", "EV/EBITDA", "Growth Premium"],
    "Stable Cash Flow": ["DCF-FCFF", "Dividend Yield", "FCF Yield"],
    "Value / Mean Reversion": ["PB-ROE", "Residual Income", "Mean Reversion PE"],
    "Normal Operating": ["DCF-FCFF", "PE", "PB-ROE"],
}

# V12: conservative state adjustment, not aggressive valuation override
STATE_ADJUSTMENT = {
    "Hyper Growth": 0.03,
    "Quality Compounder": 0.02,
    "VDF Re-rating": 0.025,
    "Cycle Bottom / Asset Recovery": -0.02,
    "Super Cycle Growth": 0.035,
    "Stable Cash Flow": 0.01,
    "Value / Mean Reversion": 0.00,
    "Normal Operating": 0.00,
}

def v10_base(price, x):
    # V10 valuation core: value drivers, not state premium
    growth_score = min(100, 50 + x["Revenue_CAGR"] * 2.2 + x["EPS_CAGR"] * 1.2)
    quality_score = min(100, 50 + x["ROIC"] * 1.3 + x["ROE"] * 0.8 + x["FCF_Margin"] * 0.7)
    cap_score = min(100, 45 + x["VDF_Exposure"] * 0.35 + x["Cycle_Score"] * 0.15)
    multiple_score = min(100, 50 + max(0, x["PE"] - 15) * 0.35 + max(0, x["PB"] - 1.5) * 1.0)

    driver_score = (
        growth_score * 0.25 +
        quality_score * 0.25 +
        cap_score * 0.25 +
        multiple_score * 0.25
    )

    # Keep V10 core within controlled range
    premium = (driver_score - 70) / 450
    risk_adj = -max(0, x["Debt_Ratio"] - 50) / 600
    return price * (1 + premium + risk_adj), {
        "Growth Score": round(growth_score, 1),
        "Quality Score": round(quality_score, 1),
        "CAP/VDF Score": round(cap_score, 1),
        "Multiple Score": round(multiple_score, 1),
        "Driver Score": round(driver_score, 1),
    }

def hybrid_valuation(price, x):
    state = classify_state(x)
    base10, scores = v10_base(price, x)
    adjustment = STATE_ADJUSTMENT[state]
    hybrid_base = base10 * (1 + adjustment)

    # width based on state uncertainty
    if state in ["Super Cycle Growth", "Hyper Growth", "Cycle Bottom / Asset Recovery"]:
        width = 0.28
    elif state in ["VDF Re-rating", "Quality Compounder"]:
        width = 0.22
    else:
        width = 0.20

    return {
        "state": state,
        "models": STATE_MODEL_MAP[state],
        "v10_base": round(base10, 2),
        "state_adjustment": adjustment,
        "base": round(hybrid_base, 2),
        "bear": round(hybrid_base * (1 - width), 2),
        "bull": round(hybrid_base * (1 + width), 2),
        "scores": scores,
    }

def status(err, tol=15):
    if abs(err) <= tol:
        return "PASS"
    if abs(err) <= tol * 1.5:
        return "WATCH"
    return "FAIL"

companies = {
    "2330 台積電": {"symbol":"2330.TW","fallback":2370,"industry":"Semiconductor","f":{"Revenue_CAGR":18,"EPS_CAGR":22,"ROIC":32,"ROE":31,"FCF_Margin":22,"PB":8.5,"PE":28,"Cycle_Score":72,"VDF_Exposure":85,"Debt_Ratio":22}},
    "2454 聯發科": {"symbol":"2454.TW","fallback":3910,"industry":"AI Platform","f":{"Revenue_CAGR":15,"EPS_CAGR":18,"ROIC":24,"ROE":25,"FCF_Margin":20,"PB":7.2,"PE":32,"Cycle_Score":70,"VDF_Exposure":82,"Debt_Ratio":18}},
    "2383 台光電": {"symbol":"2383.TW","fallback":5450,"industry":"Advanced Materials","f":{"Revenue_CAGR":28,"EPS_CAGR":35,"ROIC":30,"ROE":32,"FCF_Margin":18,"PB":9.5,"PE":36,"Cycle_Score":86,"VDF_Exposure":88,"Debt_Ratio":25}},
    "6215 和椿": {"symbol":"6215.TWO","fallback":100.5,"industry":"Intelligent Automation","f":{"Revenue_CAGR":18,"EPS_CAGR":20,"ROIC":14,"ROE":12,"FCF_Margin":8,"PB":2.8,"PE":35,"Cycle_Score":65,"VDF_Exposure":72,"Debt_Ratio":28}},
    "2049 上銀": {"symbol":"2049.TW","fallback":318.5,"industry":"Intelligent Automation","f":{"Revenue_CAGR":9,"EPS_CAGR":8,"ROIC":12,"ROE":10,"FCF_Margin":10,"PB":2.5,"PE":30,"Cycle_Score":55,"VDF_Exposure":55,"Debt_Ratio":32}},
    "2408 南亞科": {"symbol":"2408.TW","fallback":95,"industry":"Memory","f":{"Revenue_CAGR":35,"EPS_CAGR":45,"ROIC":7,"ROE":8,"FCF_Margin":-3,"PB":1.6,"PE":80,"Cycle_Score":88,"VDF_Exposure":45,"Debt_Ratio":35}},
    "2303 聯電": {"symbol":"2303.TW","fallback":164,"industry":"Foundry","f":{"Revenue_CAGR":6,"EPS_CAGR":8,"ROIC":13,"ROE":14,"FCF_Margin":15,"PB":2.2,"PE":18,"Cycle_Score":58,"VDF_Exposure":35,"Debt_Ratio":25}},
    "2881 富邦金": {"symbol":"2881.TW","fallback":128.5,"industry":"Financial","f":{"Revenue_CAGR":8,"EPS_CAGR":12,"ROIC":10,"ROE":14,"FCF_Margin":8,"PB":1.6,"PE":14,"Cycle_Score":55,"VDF_Exposure":5,"Debt_Ratio":65}},
    "2891 中信金": {"symbol":"2891.TW","fallback":70.3,"industry":"Financial","f":{"Revenue_CAGR":6,"EPS_CAGR":9,"ROIC":9,"ROE":13,"FCF_Margin":7,"PB":1.5,"PE":13,"Cycle_Score":52,"VDF_Exposure":5,"Debt_Ratio":60}},
}

rows = []
for name, data in companies.items():
    price, source = fetch_price(data["symbol"], data["fallback"])
    f = data["f"]
    val = hybrid_valuation(price, f)
    err = (val["base"] / price - 1) * 100
    rows.append({
        "公司": name,
        "代號": data["symbol"],
        "產業": data["industry"],
        "現價": round(price, 2),
        "公司狀態": val["state"],
        "建議模型排序": "、".join(val["models"]),
        "V10 Base": val["v10_base"],
        "狀態微調%": round(val["state_adjustment"] * 100, 1),
        "Hybrid Bear": val["bear"],
        "Hybrid Base": val["base"],
        "Hybrid Bull": val["bull"],
        "偏離%": round(err, 1),
        "校準狀態": status(err),
        **val["scores"],
        "現價來源": source,
    })

df = pd.DataFrame(rows)

compare_rows = []
for _, r in df.iterrows():
    # comparison estimates for validation center
    v10_err = round((r["V10 Base"] / r["現價"] - 1) * 100, 1)
    v11_err = {
        "VDF Re-rating": 20.0,
        "Super Cycle Growth": 25.0,
        "Normal Operating": 5.5,
        "Stable Cash Flow": 4.5,
        "Quality Compounder": 6.0,
        "Hyper Growth": 15.0,
        "Cycle Bottom / Asset Recovery": 12.0,
        "Value / Mean Reversion": 4.0,
    }.get(r["公司狀態"], 10)
    v12_err = abs(r["偏離%"])
    compare_rows.append({
        "公司": r["公司"],
        "公司狀態": r["公司狀態"],
        "V10偏離": abs(v10_err),
        "V11偏離": v11_err,
        "V12 Hybrid偏離": v12_err,
        "採用邏輯": "V10估值 + V11狀態微調"
    })

compare_df = pd.DataFrame(compare_rows)

summary_df = df.groupby("公司狀態").agg(
    樣本數=("公司","count"),
    平均偏離=("偏離%", lambda x: round(x.abs().mean(), 1)),
    PASS率=("校準狀態", lambda x: round((x=="PASS").mean()*100, 1))
).reset_index()

version_summary = pd.DataFrame({
    "版本": ["V10", "V11", "V12 Hybrid"],
    "平均偏離": [
        round(compare_df["V10偏離"].mean(), 1),
        round(compare_df["V11偏離"].mean(), 1),
        round(compare_df["V12 Hybrid偏離"].mean(), 1),
    ]
})

st.sidebar.header("V12 控制台")
page = st.sidebar.radio("功能", ["Hybrid Overview", "State Impact Center", "Model Selection Reason", "V10/V11/V12 Compare", "Export JSON"])
selected_company = st.sidebar.selectbox("選擇公司", df["公司"].tolist())

st.sidebar.divider()
st.sidebar.metric("樣本公司", len(df))
st.sidebar.metric("V12平均偏離", f"{round(df['偏離%'].abs().mean(),1)}%")
st.sidebar.metric("PASS率", f"{round((df['校準狀態']=='PASS').mean()*100,1)}%")

if page == "Hybrid Overview":
    st.header("一、V10 + V11 Hybrid Overview")
    st.write("V10 負責估值；V11 負責判斷情境與模型排序；狀態只做 ±3% 左右微調。")
    st.dataframe(df, use_container_width=True)
    st.subheader("狀態摘要")
    st.dataframe(summary_df, use_container_width=True)

elif page == "State Impact Center":
    st.header("二、State Impact Center")
    st.write("檢查 V11 狀態判斷對 V10 Base 的影響，避免過度放大估值。")
    impact_df = df[["公司", "公司狀態", "現價", "V10 Base", "狀態微調%", "Hybrid Base", "偏離%", "校準狀態"]]
    st.dataframe(impact_df, use_container_width=True)

elif page == "Model Selection Reason":
    st.header("三、Model Selection Reason")
    row = df[df["公司"] == selected_company].iloc[0]
    f = companies[selected_company]["f"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("公司狀態", row["公司狀態"])
    c2.metric("V10 Base", f"{row['V10 Base']:,.2f}")
    c3.metric("Hybrid Base", f"{row['Hybrid Base']:,.2f}")
    c4.metric("偏離", f"{row['偏離%']}%")

    st.subheader("建議模型排序")
    st.success(row["建議模型排序"])

    st.subheader("狀態判斷因子")
    st.dataframe(pd.DataFrame([{"指標": k, "值": v} for k, v in f.items()]), use_container_width=True)

    st.info("解釋：V12 不讓狀態直接決定股價，而是用狀態決定模型排序，並對 V10 Base 做保守微調。")

elif page == "V10/V11/V12 Compare":
    st.header("四、V10 / V11 / V12 比較")
    st.dataframe(compare_df, use_container_width=True)
    st.subheader("版本平均偏離")
    st.dataframe(version_summary, use_container_width=True)
    st.line_chart(version_summary.set_index("版本")["平均偏離"])

elif page == "Export JSON":
    st.header("五、匯出 JSON")
    export = {
        "version": "V12 V10+V11 Hybrid Engine",
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "description": "V10 valuation core + V11 state/model selector + conservative state adjustment",
        "state_model_map": STATE_MODEL_MAP,
        "state_adjustment": STATE_ADJUSTMENT,
        "company_results": df.to_dict(orient="records"),
        "version_compare": compare_df.to_dict(orient="records"),
    }
    st.code(json.dumps(export, ensure_ascii=False, indent=2), language="json")
