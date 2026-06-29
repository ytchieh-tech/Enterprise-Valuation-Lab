import streamlit as st
import pandas as pd
import json

st.set_page_config(
    page_title="Enterprise Valuation Lab V4",
    page_icon="🏛️",
    layout="wide"
)

st.title("🏛️ Enterprise Valuation Lab")
st.subheader("V4｜模型適配 + 綜合估值區間 Bear / Base / Bull")
st.info("先用四家公司驗證：台積電、台達電、長榮、富邦金。重點是先確認模型選擇與估值區間是否合理。")

companies = {
    "2330 台積電": {
        "symbol": "2330.TW",
        "type": "AI半導體 / 晶圓代工龍頭",
        "life_cycle": "高資本支出、高ROIC、AI成長溢價",
        "features": {
            "ROE": "高",
            "FCF": "強但受資本支出影響",
            "EPS CAGR": "高",
            "負債": "低",
            "股利特徵": "穩定但非高殖利率"
        },
        "model_scores": {
            "DCF-FCFF": 94,
            "EVA": 90,
            "AI Premium": 86,
            "EBO": 78,
            "EV/EBITDA": 74,
            "PB-ROE": 48,
            "Dividend Yield": 35,
            "Cycle PE": 20
        },
        "valuation": {
            "DCF-FCFF": {"bear": 1750, "base": 2100, "bull": 2450},
            "EVA": {"bear": 1650, "base": 2050, "bull": 2400},
            "AI Premium": {"bear": 2050, "base": 2480, "bull": 2850},
            "EBO": {"bear": 1550, "base": 1900, "bull": 2250},
            "EV/EBITDA": {"bear": 1700, "base": 2150, "bull": 2550}
        },
        "current_price": 2340
    },
    "2308 台達電": {
        "symbol": "2308.TW",
        "type": "Quality Compounder / 電源與工業自動化",
        "life_cycle": "穩定成長、高品質複利企業",
        "features": {
            "ROE": "高且穩定",
            "FCF": "穩定",
            "EPS CAGR": "中高",
            "負債": "低",
            "股利特徵": "穩定配息"
        },
        "model_scores": {
            "EVA": 93,
            "Quality Compounder": 89,
            "DCF-FCFF": 82,
            "Residual Income": 76,
            "PB-ROE": 68,
            "AI Premium": 42,
            "Cycle PE": 18,
            "EV/EBITDA": 55
        },
        "valuation": {
            "EVA": {"bear": 390, "base": 460, "bull": 540},
            "Quality Compounder": {"bear": 410, "base": 490, "bull": 580},
            "DCF-FCFF": {"bear": 370, "base": 445, "bull": 520},
            "Residual Income": {"bear": 360, "base": 430, "bull": 500},
            "PB-ROE": {"bear": 340, "base": 410, "bull": 480}
        },
        "current_price": 430
    },
    "2603 長榮": {
        "symbol": "2603.TW",
        "type": "航運循環股",
        "life_cycle": "景氣循環、獲利波動、運價敏感",
        "features": {
            "ROE": "波動",
            "FCF": "波動",
            "EPS CAGR": "循環",
            "負債": "中",
            "股利特徵": "高波動股利"
        },
        "model_scores": {
            "EV/EBITDA": 94,
            "Cycle PE": 90,
            "FCF Yield": 82,
            "Asset Value": 76,
            "PB-ROE": 35,
            "Residual Income": 32,
            "DCF-FCFF": 28,
            "AI Premium": 5
        },
        "valuation": {
            "EV/EBITDA": {"bear": 180, "base": 240, "bull": 320},
            "Cycle PE": {"bear": 170, "base": 230, "bull": 300},
            "FCF Yield": {"bear": 160, "base": 220, "bull": 290},
            "Asset Value": {"bear": 150, "base": 210, "bull": 280}
        },
        "current_price": 220
    },
    "2881 富邦金": {
        "symbol": "2881.TW",
        "type": "金融金控",
        "life_cycle": "金融資產股、ROE與股利主導估值",
        "features": {
            "ROE": "穩定",
            "FCF": "金融業不適用",
            "EPS CAGR": "中",
            "負債": "金融業特殊結構",
            "股利特徵": "重要估值因子"
        },
        "model_scores": {
            "PB-ROE": 96,
            "Residual Income": 91,
            "Dividend Yield": 85,
            "PE": 66,
            "DCF-FCFF": 10,
            "EV/EBITDA": 5,
            "AI Premium": 0,
            "Cycle PE": 20
        },
        "valuation": {
            "PB-ROE": {"bear": 82, "base": 98, "bull": 115},
            "Residual Income": {"bear": 80, "base": 95, "bull": 112},
            "Dividend Yield": {"bear": 75, "base": 90, "bull": 105},
            "PE": {"bear": 78, "base": 92, "bull": 108}
        },
        "current_price": 95
    }
}


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
    scores = company["model_scores"]
    vals = company["valuation"]
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
    if fair is None:
        return "無法判斷"
    bear, base, bull = fair["bear"], fair["base"], fair["bull"]
    if price < bear:
        return "低估區"
    if price <= bull:
        return "合理區間"
    return "高估區"

stock = st.selectbox("選擇公司", list(companies.keys()))
company = companies[stock]

st.divider()

st.header("一、公司定位")
c1, c2, c3 = st.columns(3)
c1.metric("股票代號", company["symbol"])
c2.metric("公司類型", company["type"])
c3.metric("生命週期", company["life_cycle"])

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
valuation_result, weights = weighted_valuation(company, top_n=3)

if weights:
    cols = st.columns(len(weights))
    for col, (m, s, w) in zip(cols, weights):
        col.success(f"{m}\n\n分數 {s}｜權重 {w:.1%}")
else:
    st.error("目前沒有足夠適配模型可產生估值")

st.header("五、各模型估值區間")
valuation_rows = []
for m, v in company["valuation"].items():
    valuation_rows.append({
        "模型": m,
        "適配分數": company["model_scores"].get(m, 0),
        "Bear 保守價": v["bear"],
        "Base 合理價": v["base"],
        "Bull 樂觀價": v["bull"],
        "是否納入": "是" if any(m == x[0] for x in weights) else "否"
    })
st.dataframe(pd.DataFrame(valuation_rows), use_container_width=True)

st.header("六、綜合估值區間")
if valuation_result:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Bear 保守價", f"{valuation_result['bear']:.0f}")
    c2.metric("Base 合理價", f"{valuation_result['base']:.0f}")
    c3.metric("Bull 樂觀價", f"{valuation_result['bull']:.0f}")
    c4.metric("現價", f"{company['current_price']:.0f}")

    verdict = judge_price(company["current_price"], valuation_result)
    gap = (valuation_result["base"] / company["current_price"] - 1) * 100
    st.subheader(f"判斷：{verdict}")
    st.write(f"Base 合理價相對現價差距：{gap:.1f}%")

    if verdict == "低估區":
        st.success("現價低於保守價，屬於低估區。")
    elif verdict == "合理區間":
        st.info("現價落在 Bear～Bull 區間內，屬於合理區間。")
    else:
        st.warning("現價高於樂觀價，需留意估值偏高。")

st.header("七、匯出給主平台 JSON")
export_data = {
    company["symbol"]: {
        "name": stock,
        "type": company["type"],
        "selected_models": [m for m, _, _ in weights],
        "weights": {m: round(w, 4) for m, _, w in weights},
        "valuation": {
            "bear": round(valuation_result["bear"], 2) if valuation_result else None,
            "base": round(valuation_result["base"], 2) if valuation_result else None,
            "bull": round(valuation_result["bull"], 2) if valuation_result else None,
        } if valuation_result else None,
        "current_price": company["current_price"],
        "judgement": judge_price(company["current_price"], valuation_result) if valuation_result else None,
    }
}

st.code(json.dumps(export_data, ensure_ascii=False, indent=2), language="json")
