
import json
from datetime import datetime

import pandas as pd
import streamlit as st

try:
    import yfinance as yf
except Exception:
    yf = None


st.set_page_config(page_title="Enterprise Valuation Lab V12.1", page_icon="🏛️", layout="wide")

st.title("🏛️ Enterprise Valuation Lab")
st.subheader("V12.1｜Winner Analysis Center")
st.info(
    "本版重點：不再繼續堆疊新模型，而是比較 V8、V10、V12 哪個版本最適合每家公司，"
    "並建立 Adaptive Recommendation Engine。"
)


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


companies = {
    "2330 台積電": {
        "symbol": "2330.TW", "fallback": 2370, "industry": "Semiconductor", "type": "Compute Infrastructure",
        "dna": {"ROIC": 32, "Growth": 18, "FCF": 22, "VDF": 85, "Cycle": 72},
        "errors": {"V8": 5.2, "V10": 3.0, "V12": 4.2},
        "reason": "ROIC高、CAP高、Compute Infrastructure受惠明確，V10較能反映價值驅動。",
    },
    "2454 聯發科": {
        "symbol": "2454.TW", "fallback": 3910, "industry": "Semiconductor", "type": "AI Platform",
        "dna": {"ROIC": 24, "Growth": 15, "FCF": 20, "VDF": 82, "Cycle": 70},
        "errors": {"V8": 8.5, "V10": 7.5, "V12": 6.2},
        "reason": "AI Platform與市場倍數變化明顯，需同時看VDF與狀態切換，V12較佳。",
    },
    "2383 台光電": {
        "symbol": "2383.TW", "fallback": 5450, "industry": "PCB / CCL", "type": "Advanced Materials",
        "dna": {"ROIC": 30, "Growth": 28, "FCF": 18, "VDF": 88, "Cycle": 86},
        "errors": {"V8": 4.0, "V10": 8.6, "V12": 7.8},
        "reason": "產業母模型已能很好捕捉AI材料溢價，V8暫時最穩。",
    },
    "6215 和椿": {
        "symbol": "6215.TWO", "fallback": 100.5, "industry": "AI Robot", "type": "Intelligent Automation",
        "dna": {"ROIC": 14, "Growth": 18, "FCF": 8, "VDF": 72, "Cycle": 65},
        "errors": {"V8": 5.4, "V10": 4.2, "V12": 4.9},
        "reason": "VDF重新分類能修正傳統自動化低估問題，V10目前較佳。",
    },
    "2049 上銀": {
        "symbol": "2049.TW", "fallback": 318.5, "industry": "AI Robot", "type": "Intelligent Automation",
        "dna": {"ROIC": 12, "Growth": 9, "FCF": 10, "VDF": 55, "Cycle": 55},
        "errors": {"V8": 3.5, "V10": 5.2, "V12": 4.3},
        "reason": "AI曝險不如和椿，產業母模型仍較穩，V8勝。",
    },
    "2408 南亞科": {
        "symbol": "2408.TW", "fallback": 95, "industry": "Memory", "type": "Super Cycle",
        "dna": {"ROIC": 7, "Growth": 35, "FCF": -3, "VDF": 45, "Cycle": 88},
        "errors": {"V8": 18.0, "V10": 12.0, "V12": 7.0},
        "reason": "記憶體需依景氣循環切換模型，V12狀態機較能處理Super Cycle。",
    },
    "2303 聯電": {
        "symbol": "2303.TW", "fallback": 164, "industry": "Semiconductor", "type": "Mature Foundry",
        "dna": {"ROIC": 13, "Growth": 6, "FCF": 15, "VDF": 35, "Cycle": 58},
        "errors": {"V8": 4.8, "V10": 5.5, "V12": 4.2},
        "reason": "成熟製程需保留產業估值，但狀態微調有幫助，V12略勝。",
    },
    "2881 富邦金": {
        "symbol": "2881.TW", "fallback": 128.5, "industry": "Financial", "type": "Insurance Holding",
        "dna": {"ROIC": 10, "Growth": 8, "FCF": 8, "VDF": 5, "Cycle": 55},
        "errors": {"V8": 2.5, "V10": 6.5, "V12": 3.2},
        "reason": "金融股仍以PB-ROE與股利折現較穩，V8勝。",
    },
    "2891 中信金": {
        "symbol": "2891.TW", "fallback": 70.3, "industry": "Financial", "type": "Banking Holding",
        "dna": {"ROIC": 9, "Growth": 6, "FCF": 7, "VDF": 5, "Cycle": 52},
        "errors": {"V8": 2.0, "V10": 4.7, "V12": 3.0},
        "reason": "銀行型金控估值仍偏向PB-ROE、Excess Return與Dividend，V8勝。",
    },
}

rows = []
for name, data in companies.items():
    price, source = fetch_price(data["symbol"], data["fallback"])
    errors = data["errors"]
    winner = min(errors, key=errors.get)
    confidence = max(60, round(100 - errors[winner] * 6, 1))
    rows.append({
        "公司": name,
        "代號": data["symbol"],
        "產業": data["industry"],
        "公司DNA": data["type"],
        "現價": round(price, 2) if price else None,
        "V8偏離": errors["V8"],
        "V10偏離": errors["V10"],
        "V12偏離": errors["V12"],
        "Winner": winner,
        "推薦模型": winner,
        "信心度": confidence,
        "ROIC": data["dna"]["ROIC"],
        "Growth": data["dna"]["Growth"],
        "FCF": data["dna"]["FCF"],
        "VDF": data["dna"]["VDF"],
        "Cycle": data["dna"]["Cycle"],
        "推薦原因": data["reason"],
        "現價來源": source,
    })

df = pd.DataFrame(rows)

version_summary = pd.DataFrame([
    {"版本": "V8", "平均偏離": round(df["V8偏離"].mean(), 1), "勝出次數": int((df["Winner"] == "V8").sum())},
    {"版本": "V10", "平均偏離": round(df["V10偏離"].mean(), 1), "勝出次數": int((df["Winner"] == "V10").sum())},
    {"版本": "V12", "平均偏離": round(df["V12偏離"].mean(), 1), "勝出次數": int((df["Winner"] == "V12").sum())},
])

industry_winner = (
    df.groupby(["產業", "Winner"])
    .size()
    .reset_index(name="勝出次數")
    .pivot(index="產業", columns="Winner", values="勝出次數")
    .fillna(0)
    .reset_index()
)

for col in ["V8", "V10", "V12"]:
    if col not in industry_winner.columns:
        industry_winner[col] = 0

dna_rows = []
for feature, condition, label in [
    ("高ROIC", df["ROIC"] >= 25, "ROIC >= 25"),
    ("高成長", df["Growth"] >= 20, "Growth >= 20"),
    ("高FCF", df["FCF"] >= 15, "FCF >= 15"),
    ("高VDF曝險", df["VDF"] >= 70, "VDF >= 70"),
    ("高週期性", df["Cycle"] >= 80, "Cycle >= 80"),
    ("金融股", df["產業"] == "Financial", "Financial"),
]:
    subset = df[condition]
    if len(subset) == 0:
        continue
    winner_counts = subset["Winner"].value_counts()
    best = winner_counts.idxmax()
    dna_rows.append({
        "公司特徵": feature,
        "判斷條件": label,
        "樣本數": len(subset),
        "最佳版本": best,
        "V8勝": int(winner_counts.get("V8", 0)),
        "V10勝": int(winner_counts.get("V10", 0)),
        "V12勝": int(winner_counts.get("V12", 0)),
    })

dna_df = pd.DataFrame(dna_rows)

st.sidebar.header("V12.1 控制台")
page = st.sidebar.radio(
    "功能",
    ["Model Race Center", "Industry Winner Matrix", "Company DNA Analysis", "Adaptive Recommendation", "Model Evolution Dashboard", "Export JSON"]
)
selected_company = st.sidebar.selectbox("選擇公司", df["公司"].tolist())

st.sidebar.divider()
st.sidebar.metric("樣本公司", len(df))
st.sidebar.metric("最佳平均偏離", f"{round(df.apply(lambda r: min(r['V8偏離'], r['V10偏離'], r['V12偏離']), axis=1).mean(), 1)}%")
st.sidebar.metric("V12勝出", int((df["Winner"] == "V12").sum()))

if page == "Model Race Center":
    st.header("一、Model Race Center")
    st.write("每家公司比較 V8、V10、V12，Winner = 偏離最小版本。")
    st.dataframe(df, use_container_width=True)

elif page == "Industry Winner Matrix":
    st.header("二、Industry Winner Matrix")
    st.write("統計各產業較適合哪一版模型。")
    st.dataframe(industry_winner[["產業", "V8", "V10", "V12"]], use_container_width=True)

elif page == "Company DNA Analysis":
    st.header("三、Company DNA Analysis")
    st.write("不是只看產業，而是看公司特徵：高ROIC、高成長、高週期、高VDF曝險等。")
    st.dataframe(dna_df, use_container_width=True)

elif page == "Adaptive Recommendation":
    st.header("四、Adaptive Recommendation Engine")
    row = df[df["公司"] == selected_company].iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("推薦模型", row["推薦模型"])
    c2.metric("信心度", f"{row['信心度']}%")
    c3.metric("公司DNA", row["公司DNA"])
    c4.metric("現價", f"{row['現價']:,.2f}")

    st.subheader("模型競賽結果")
    race = pd.DataFrame([
        {"版本": "V8", "偏離": row["V8偏離"]},
        {"版本": "V10", "偏離": row["V10偏離"]},
        {"版本": "V12", "偏離": row["V12偏離"]},
    ])
    st.dataframe(race, use_container_width=True)
    st.bar_chart(race.set_index("版本")["偏離"])

    st.subheader("推薦原因")
    st.success(row["推薦原因"])

elif page == "Model Evolution Dashboard":
    st.header("五、Model Evolution Dashboard")
    st.write("避免『新版本一定更好』的錯誤假設，用數據比較每一版。")
    st.dataframe(version_summary, use_container_width=True)
    st.line_chart(version_summary.set_index("版本")["平均偏離"])

elif page == "Export JSON":
    st.header("六、匯出 JSON")
    export = {
        "version": "V12.1 Winner Analysis Center",
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model_race": df.to_dict(orient="records"),
        "version_summary": version_summary.to_dict(orient="records"),
        "industry_winner": industry_winner.to_dict(orient="records"),
        "company_dna_analysis": dna_df.to_dict(orient="records"),
    }
    st.code(json.dumps(export, ensure_ascii=False, indent=2), language="json")
