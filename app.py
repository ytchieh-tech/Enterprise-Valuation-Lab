import streamlit as st
import pandas as pd
import json

st.set_page_config(
    page_title="Enterprise Valuation Lab",
    page_icon="🏛️",
    layout="wide"
)

st.title("🏛️ Enterprise Valuation Lab")
st.subheader("Model Selection Engine V3｜企業分類器 + 模型適配器")
st.info("V3 先用四家公司測試：先判斷企業類型，再依企業特徵挑選 Top 3 模型。")

# =========================
# 1. 測試公司資料
# =========================
companies = {
    "2330 台積電": {
        "type": "AI半導體龍頭",
        "industry": "Semiconductor",
        "ROE": 22,
        "FCF": 1200,
        "Growth": 18,
        "Debt": 12,
        "Cycle": "低",
        "Dividend": "中",
        "Quality": "高",
        "note": "高ROE、高FCF、高成長、低負債，屬AI半導體核心資產。"
    },
    "2308 台達電": {
        "type": "Quality Compounder",
        "industry": "Industrial / Power / Automation",
        "ROE": 16,
        "FCF": 450,
        "Growth": 10,
        "Debt": 15,
        "Cycle": "中低",
        "Dividend": "中",
        "Quality": "高",
        "note": "穩定現金流、品質複利、工業自動化與資料中心電源受惠。"
    },
    "2603 長榮": {
        "type": "景氣循環股",
        "industry": "Shipping",
        "ROE": 12,
        "FCF": -300,
        "Growth": 5,
        "Debt": 40,
        "Cycle": "高",
        "Dividend": "高波動",
        "Quality": "循環",
        "note": "航運獲利高度循環，EPS/ROE容易失真，優先採循環與EV/EBITDA模型。"
    },
    "2881 富邦金": {
        "type": "金融控股",
        "industry": "Financial",
        "ROE": 11,
        "FCF": 0,
        "Growth": 8,
        "Debt": 0,
        "Cycle": "金融循環",
        "Dividend": "穩定",
        "Quality": "穩定",
        "note": "金融業FCF與EV/EBITDA不適用，以PB-ROE、剩餘收益、股利模型為主。"
    }
}

# =========================
# 2. 模型池
# =========================
all_models = [
    "DCF-FCFF",
    "DCF-FCFE",
    "EVA",
    "EBO",
    "PB-ROE",
    "Residual Income",
    "EV/EBITDA",
    "Dividend Yield",
    "Cycle PE",
    "Asset Value",
    "Quality Compounder",
    "AI Premium"
]

# 企業類型模型基礎權重：先決定「哪些模型應該參賽」
type_model_weight = {
    "AI半導體龍頭": {
        "DCF-FCFF": 35,
        "EVA": 30,
        "EBO": 25,
        "AI Premium": 18,
        "EV/EBITDA": 12,
        "DCF-FCFE": 10,
        "PB-ROE": -10,
        "Dividend Yield": -20,
        "Cycle PE": -30,
    },
    "Quality Compounder": {
        "EVA": 35,
        "Quality Compounder": 32,
        "DCF-FCFF": 26,
        "Residual Income": 22,
        "PB-ROE": 18,
        "EBO": 15,
        "DCF-FCFE": 8,
        "Cycle PE": -25,
        "AI Premium": -10,
    },
    "景氣循環股": {
        "EV/EBITDA": 35,
        "Cycle PE": 32,
        "FCF Yield": 25,  # 顯示用，稍後會轉入模型池外加
        "Asset Value": 20,
        "DCF-FCFF": 5,
        "PB-ROE": -25,
        "Residual Income": -25,
        "EVA": -20,
        "EBO": -20,
        "AI Premium": -40,
    },
    "金融控股": {
        "PB-ROE": 40,
        "Residual Income": 35,
        "Dividend Yield": 28,
        "EBO": 10,
        "DCF-FCFF": -40,
        "DCF-FCFE": -35,
        "EV/EBITDA": -40,
        "AI Premium": -50,
        "Cycle PE": -25,
    }
}

# 確保 Cycle 類模型有 FCF Yield
if "FCF Yield" not in all_models:
    all_models.append("FCF Yield")

# =========================
# 3. 適配分數函數
# =========================
def calculate_scores(data):
    score = {m: 0 for m in all_models}

    # Step A：企業類型基礎權重
    base = type_model_weight.get(data["type"], {})
    for m, w in base.items():
        if m in score:
            score[m] += w

    # Step B：財務特徵修正
    roe = data["ROE"]
    fcf = data["FCF"]
    growth = data["Growth"]
    debt = data["Debt"]
    company_type = data["type"]

    # ROE：高品質企業加 EVA / RI / PB-ROE
    if roe >= 15:
        score["EVA"] += 8
        score["Residual Income"] += 6
        score["PB-ROE"] += 4
    elif roe < 8:
        score["PB-ROE"] -= 8
        score["EVA"] -= 8

    # FCF：現金流穩定才提高DCF；循環股不讓DCF過度勝出
    if fcf > 0:
        score["DCF-FCFF"] += 8
        score["DCF-FCFE"] += 4
        if company_type == "Quality Compounder":
            score["Quality Compounder"] += 6
    else:
        score["DCF-FCFF"] -= 8
        score["DCF-FCFE"] -= 8
        score["EV/EBITDA"] += 6
        score["Cycle PE"] += 4

    # 成長：高成長提高 DCF/EVA，但金融與航運不採AI Premium
    if growth >= 15:
        score["DCF-FCFF"] += 6
        score["EVA"] += 6
        if company_type == "AI半導體龍頭":
            score["AI Premium"] += 10
    elif growth <= 5:
        score["Cycle PE"] += 8
        score["EV/EBITDA"] += 4

    # 負債：高負債或循環產業提高 EV/EBITDA、Asset Value
    if debt >= 35:
        score["EV/EBITDA"] += 8
        score["Asset Value"] += 5
        score["DCF-FCFE"] -= 8

    # Step C：硬性排除／懲罰，避免不適用模型混入Top3
    if company_type == "金融控股":
        for m in ["DCF-FCFF", "DCF-FCFE", "EV/EBITDA", "AI Premium", "Cycle PE"]:
            score[m] -= 80

    if company_type == "景氣循環股":
        for m in ["PB-ROE", "Residual Income", "EVA", "EBO", "AI Premium", "Quality Compounder"]:
            score[m] -= 50

    if company_type == "Quality Compounder":
        for m in ["AI Premium", "Cycle PE", "Asset Value"]:
            score[m] -= 30

    if company_type == "AI半導體龍頭":
        for m in ["Cycle PE", "Asset Value", "Dividend Yield"]:
            score[m] -= 40

    return dict(sorted(score.items(), key=lambda x: x[1], reverse=True))


def status(score):
    if score >= 40:
        return "核心模型"
    if score >= 25:
        return "可用模型"
    if score >= 10:
        return "觀察模型"
    return "淘汰/不適用"

# =========================
# 4. UI
# =========================
stock = st.selectbox("選擇測試公司", list(companies.keys()))
data = companies[stock]

st.divider()
st.header("一、企業分類")

c1, c2, c3 = st.columns(3)
c1.metric("企業類型", data["type"])
c2.metric("產業", data["industry"])
c3.metric("品質特徵", data["Quality"])
st.caption(data["note"])

st.header("二、公司核心特徵")

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("ROE", data["ROE"])
c2.metric("FCF", data["FCF"])
c3.metric("Growth", data["Growth"])
c4.metric("Debt", data["Debt"])
c5.metric("Cycle", data["Cycle"])
c6.metric("Dividend", data["Dividend"])

scores = calculate_scores(data)
ranking = pd.DataFrame([
    {"模型": m, "適配分數": s, "狀態": status(s)}
    for m, s in scores.items()
])

selected = ranking[ranking["適配分數"] >= 25].head(3)
if len(selected) < 3:
    selected = ranking.head(3)

st.header("三、推薦 Top 3 模型")
for _, row in selected.iterrows():
    st.success(f"✓ {row['模型']}｜適配分數 {row['適配分數']}｜{row['狀態']}")

st.header("四、完整模型排名")
st.dataframe(ranking, use_container_width=True)

st.header("五、匯出給主平台的模型池")
export_data = {
    stock.split()[0]: {
        "company": stock,
        "type": data["type"],
        "selected_models": selected["模型"].tolist(),
        "scores": {row["模型"]: int(row["適配分數"]) for _, row in ranking.iterrows()},
        "note": data["note"]
    }
}

st.json(export_data)

st.caption("V3 Beta：目前先驗證四家公司；確認模型選擇合理後，再加入估值區間與更多公司。")
