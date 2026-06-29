
import json
from datetime import datetime

import pandas as pd
import streamlit as st

try:
    import yfinance as yf
except Exception:
    yf = None


st.set_page_config(page_title="Enterprise Valuation Lab V12.2", page_icon="🏛️", layout="wide")

st.title("🏛️ Enterprise Valuation Lab")
st.subheader("V12.2｜Winner Learning Engine")
st.info(
    "本版重點：從 V12.1 的 Winner 結果進一步學習，建立 Winner Probability，"
    "讓系統依照公司 DNA 自動判斷 V8 / V10 / V12 哪個版本較適合。"
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


# ------------------------------------------------------------
# V12.1 training sample：Winner Learning 的基礎資料
# ------------------------------------------------------------

companies = {
    "2330 台積電": {
        "symbol": "2330.TW", "fallback": 2370, "industry": "Semiconductor", "dna_type": "Compute Infrastructure",
        "dna": {"ROIC": 32, "Growth": 18, "FCF": 22, "VDF": 85, "Cycle": 72, "Financial": 0},
        "errors": {"V8": 5.2, "V10": 3.0, "V12": 4.2},
        "winner": "V10",
        "reason": "ROIC高、CAP高、Compute Infrastructure受惠明確，V10較能反映價值驅動。"
    },
    "2454 聯發科": {
        "symbol": "2454.TW", "fallback": 3910, "industry": "Semiconductor", "dna_type": "AI Platform",
        "dna": {"ROIC": 24, "Growth": 15, "FCF": 20, "VDF": 82, "Cycle": 70, "Financial": 0},
        "errors": {"V8": 8.5, "V10": 7.5, "V12": 6.2},
        "winner": "V12",
        "reason": "AI Platform與市場倍數變化明顯，需同時看VDF與狀態切換，V12較佳。"
    },
    "2383 台光電": {
        "symbol": "2383.TW", "fallback": 5450, "industry": "PCB / CCL", "dna_type": "Advanced Materials",
        "dna": {"ROIC": 30, "Growth": 28, "FCF": 18, "VDF": 88, "Cycle": 86, "Financial": 0},
        "errors": {"V8": 4.0, "V10": 8.6, "V12": 7.8},
        "winner": "V8",
        "reason": "產業母模型已能很好捕捉AI材料溢價，V8暫時最穩。"
    },
    "6215 和椿": {
        "symbol": "6215.TWO", "fallback": 100.5, "industry": "AI Robot", "dna_type": "Intelligent Automation",
        "dna": {"ROIC": 14, "Growth": 18, "FCF": 8, "VDF": 72, "Cycle": 65, "Financial": 0},
        "errors": {"V8": 5.4, "V10": 4.2, "V12": 4.9},
        "winner": "V10",
        "reason": "VDF重新分類能修正傳統自動化低估問題，V10目前較佳。"
    },
    "2049 上銀": {
        "symbol": "2049.TW", "fallback": 318.5, "industry": "AI Robot", "dna_type": "Intelligent Automation",
        "dna": {"ROIC": 12, "Growth": 9, "FCF": 10, "VDF": 55, "Cycle": 55, "Financial": 0},
        "errors": {"V8": 3.5, "V10": 5.2, "V12": 4.3},
        "winner": "V8",
        "reason": "AI曝險不如和椿，產業母模型仍較穩，V8勝。"
    },
    "2408 南亞科": {
        "symbol": "2408.TW", "fallback": 95, "industry": "Memory", "dna_type": "Super Cycle",
        "dna": {"ROIC": 7, "Growth": 35, "FCF": -3, "VDF": 45, "Cycle": 88, "Financial": 0},
        "errors": {"V8": 18.0, "V10": 12.0, "V12": 7.0},
        "winner": "V12",
        "reason": "記憶體需依景氣循環切換模型，V12狀態機較能處理Super Cycle。"
    },
    "2303 聯電": {
        "symbol": "2303.TW", "fallback": 164, "industry": "Semiconductor", "dna_type": "Mature Foundry",
        "dna": {"ROIC": 13, "Growth": 6, "FCF": 15, "VDF": 35, "Cycle": 58, "Financial": 0},
        "errors": {"V8": 4.8, "V10": 5.5, "V12": 4.2},
        "winner": "V12",
        "reason": "成熟製程需保留產業估值，但狀態微調有幫助，V12略勝。"
    },
    "2881 富邦金": {
        "symbol": "2881.TW", "fallback": 128.5, "industry": "Financial", "dna_type": "Insurance Holding",
        "dna": {"ROIC": 10, "Growth": 8, "FCF": 8, "VDF": 5, "Cycle": 55, "Financial": 1},
        "errors": {"V8": 2.5, "V10": 6.5, "V12": 3.2},
        "winner": "V8",
        "reason": "金融股仍以PB-ROE與股利折現較穩，V8勝。"
    },
    "2891 中信金": {
        "symbol": "2891.TW", "fallback": 70.3, "industry": "Financial", "dna_type": "Banking Holding",
        "dna": {"ROIC": 9, "Growth": 6, "FCF": 7, "VDF": 5, "Cycle": 52, "Financial": 1},
        "errors": {"V8": 2.0, "V10": 4.7, "V12": 3.0},
        "winner": "V8",
        "reason": "銀行型金控估值仍偏向PB-ROE、Excess Return與Dividend，V8勝。"
    },
}


# ------------------------------------------------------------
# Winner Learning rules
# ------------------------------------------------------------

def rule_scores(dna, industry, dna_type):
    """
    根據已知 Winner 分化規則，計算 V8/V10/V12 適配機率。
    注意：這不是股價估值，而是模型選擇機率。
    """
    score = {"V8": 0, "V10": 0, "V12": 0}

    roic = dna["ROIC"]
    growth = dna["Growth"]
    fcf = dna["FCF"]
    vdf = dna["VDF"]
    cycle = dna["Cycle"]
    financial = dna["Financial"]

    # Financial stocks: V8 dominant
    if financial == 1 or industry == "Financial":
        score["V8"] += 55
        score["V12"] += 20
        score["V10"] += 5

    # High ROIC + high VDF but not extreme cycle: V10
    if roic >= 25 and vdf >= 70:
        score["V10"] += 40
        score["V12"] += 20
        score["V8"] += 10

    # VDF exposure high but ROIC not high enough: V12 or V10 depending on state
    if vdf >= 70 and roic < 25:
        score["V12"] += 30
        score["V10"] += 25
        score["V8"] += 5

    # High cycle: V12
    if cycle >= 80:
        score["V12"] += 45
        score["V8"] += 15
        score["V10"] += 5

    # High growth and weak FCF: V12, because state/cycle matters
    if growth >= 25 and fcf < 10:
        score["V12"] += 45
        score["V10"] += 10

    # Stable FCF and moderate VDF: V8 usually stable
    if fcf >= 15 and vdf < 60:
        score["V8"] += 25
        score["V12"] += 20
        score["V10"] += 10

    # Industry-model-friendly cases
    if industry in ["PCB / CCL", "Financial"] and cycle < 90:
        score["V8"] += 20

    # Mature foundry: hybrid helps
    if dna_type == "Mature Foundry":
        score["V12"] += 30
        score["V8"] += 20

    # AI Platform tends to need hybrid
    if dna_type == "AI Platform":
        score["V12"] += 35
        score["V10"] += 20

    # Compute infrastructure: V10
    if dna_type == "Compute Infrastructure":
        score["V10"] += 35
        score["V12"] += 15

    # Intelligent automation split
    if dna_type == "Intelligent Automation":
        if vdf >= 70:
            score["V10"] += 30
            score["V12"] += 20
        else:
            score["V8"] += 30
            score["V12"] += 15

    # Baseline
    score["V8"] += 10
    score["V10"] += 10
    score["V12"] += 10

    total = sum(score.values())
    return {k: round(v / total * 100, 1) for k, v in score.items()}


rows = []
for name, data in companies.items():
    price, source = fetch_price(data["symbol"], data["fallback"])
    prob = rule_scores(data["dna"], data["industry"], data["dna_type"])
    predicted = max(prob, key=prob.get)
    actual = data["winner"]
    rows.append({
        "公司": name,
        "代號": data["symbol"],
        "產業": data["industry"],
        "公司DNA": data["dna_type"],
        "現價": round(price, 2) if price else None,
        "V8勝率%": prob["V8"],
        "V10勝率%": prob["V10"],
        "V12勝率%": prob["V12"],
        "系統推薦": predicted,
        "實際Winner": actual,
        "是否命中": "是" if predicted == actual else "否",
        "推薦信心": max(prob.values()),
        "V8偏離": data["errors"]["V8"],
        "V10偏離": data["errors"]["V10"],
        "V12偏離": data["errors"]["V12"],
        "ROIC": data["dna"]["ROIC"],
        "Growth": data["dna"]["Growth"],
        "FCF": data["dna"]["FCF"],
        "VDF": data["dna"]["VDF"],
        "Cycle": data["dna"]["Cycle"],
        "推薦原因": data["reason"],
        "現價來源": source,
    })

df = pd.DataFrame(rows)

winner_matrix = (
    df.groupby(["產業", "系統推薦"])
    .size()
    .reset_index(name="推薦次數")
    .pivot(index="產業", columns="系統推薦", values="推薦次數")
    .fillna(0)
    .reset_index()
)

for col in ["V8", "V10", "V12"]:
    if col not in winner_matrix.columns:
        winner_matrix[col] = 0

learning_summary = pd.DataFrame([
    {"指標": "樣本數", "值": len(df)},
    {"指標": "推薦命中率", "值": f"{round((df['是否命中'] == '是').mean() * 100, 1)}%"},
    {"指標": "平均推薦信心", "值": f"{round(df['推薦信心'].mean(), 1)}%"},
    {"指標": "V8推薦數", "值": int((df["系統推薦"] == "V8").sum())},
    {"指標": "V10推薦數", "值": int((df["系統推薦"] == "V10").sum())},
    {"指標": "V12推薦數", "值": int((df["系統推薦"] == "V12").sum())},
])

dna_rules = pd.DataFrame([
    {"公司DNA條件": "金融股 / 金控", "偏向模型": "V8", "理由": "PB-ROE、Residual Income、Dividend模型仍最穩"},
    {"公司DNA條件": "ROIC高 + VDF高", "偏向模型": "V10", "理由": "Value Driver能捕捉長期競爭優勢與價值創造"},
    {"公司DNA條件": "高週期 / Super Cycle", "偏向模型": "V12", "理由": "需要狀態機判斷週期切換"},
    {"公司DNA條件": "AI Platform", "偏向模型": "V12", "理由": "同時受VDF與市場倍數切換影響"},
    {"公司DNA條件": "高FCF、VDF中低", "偏向模型": "V8 / V12", "理由": "產業基準仍重要，狀態微調可輔助"},
    {"公司DNA條件": "Compute Infrastructure", "偏向模型": "V10", "理由": "ROIC、CAP、VDF長期驅動明確"},
])

st.sidebar.header("V12.2 控制台")
page = st.sidebar.radio(
    "功能",
    ["Winner Probability", "Learning Summary", "DNA Rule Book", "Industry Recommendation Matrix", "Company Recommendation", "Export JSON"]
)
selected_company = st.sidebar.selectbox("選擇公司", df["公司"].tolist())

st.sidebar.divider()
st.sidebar.metric("樣本公司", len(df))
st.sidebar.metric("推薦命中率", f"{round((df['是否命中'] == '是').mean() * 100, 1)}%")
st.sidebar.metric("平均信心", f"{round(df['推薦信心'].mean(), 1)}%")

if page == "Winner Probability":
    st.header("一、Winner Probability")
    st.write("系統依照公司 DNA，估計 V8 / V10 / V12 各自成為最佳模型的機率。")
    st.dataframe(df, use_container_width=True)

elif page == "Learning Summary":
    st.header("二、Learning Summary")
    st.write("檢查 Winner Learning Engine 是否能重現 V12.1 的 Winner 結果。")
    st.dataframe(learning_summary, use_container_width=True)

    st.subheader("推薦 vs 實際 Winner")
    st.dataframe(df[["公司", "系統推薦", "實際Winner", "是否命中", "推薦信心"]], use_container_width=True)

elif page == "DNA Rule Book":
    st.header("三、DNA Rule Book")
    st.write("把 V12.1 的 Winner 結果轉成可解釋規則。")
    st.dataframe(dna_rules, use_container_width=True)

elif page == "Industry Recommendation Matrix":
    st.header("四、Industry Recommendation Matrix")
    st.write("從產業角度觀察系統推薦模型分布。")
    st.dataframe(winner_matrix[["產業", "V8", "V10", "V12"]], use_container_width=True)

elif page == "Company Recommendation":
    st.header("五、Company Recommendation")
    row = df[df["公司"] == selected_company].iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("系統推薦", row["系統推薦"])
    c2.metric("推薦信心", f"{row['推薦信心']}%")
    c3.metric("實際Winner", row["實際Winner"])
    c4.metric("是否命中", row["是否命中"])

    st.subheader("Winner Probability")
    prob_df = pd.DataFrame([
        {"模型": "V8", "勝率%": row["V8勝率%"]},
        {"模型": "V10", "勝率%": row["V10勝率%"]},
        {"模型": "V12", "勝率%": row["V12勝率%"]},
    ])
    st.dataframe(prob_df, use_container_width=True)
    st.bar_chart(prob_df.set_index("模型")["勝率%"])

    st.subheader("公司DNA")
    dna_cols = ["ROIC", "Growth", "FCF", "VDF", "Cycle"]
    st.dataframe(pd.DataFrame([{"指標": c, "值": row[c]} for c in dna_cols]), use_container_width=True)

    st.subheader("推薦原因")
    st.success(row["推薦原因"])

elif page == "Export JSON":
    st.header("六、匯出 JSON")
    export = {
        "version": "V12.2 Winner Learning Engine",
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "winner_probability": df.to_dict(orient="records"),
        "learning_summary": learning_summary.to_dict(orient="records"),
        "dna_rules": dna_rules.to_dict(orient="records"),
        "industry_recommendation_matrix": winner_matrix.to_dict(orient="records"),
    }
    st.code(json.dumps(export, ensure_ascii=False, indent=2), language="json")
