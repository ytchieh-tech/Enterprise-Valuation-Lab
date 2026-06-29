import streamlit as st
import pandas as pd
import json

st.set_page_config(
    page_title="Enterprise Valuation Lab V4",
    page_icon="🏛️",
    layout="wide"
)

st.title("🏛️ Enterprise Valuation Lab")
st.subheader("V4.1｜模型適配 + 市場校準估值區間 Bear / Base / Bull")
st.info("V4.1 先校準四家公司：修正現價、加入市場校準係數，驗證估值區間是否能貼近現實。")

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
        "type": "AI Infrastructure Compounder / 電源與資料中心基建",
        "life_cycle": "AI資料中心電源、散熱與工業自動化高品質複利企業",
        "features": {
            "ROE": "高且穩定",
            "FCF": "穩定",
            "EPS CAGR": "中高",
            "負債": "低",
            "股利特徵": "穩定配息"
        },
        "model_scores": {
            "Quality Compounder": 96,
            "AI Infrastructure Premium": 94,
            "EVA": 88,
            "DCF-FCFF": 82,
            "Residual Income": 72,
            "PB-ROE": 58,
            "AI Premium": 55,
            "Cycle PE": 10,
            "EV/EBITDA": 60
        },
        "valuation": {
            "Quality Compounder": {"bear": 1650, "base": 1900, "bull": 2250},
            "AI Infrastructure Premium": {"bear": 1700, "base": 2000, "bull": 2400},
            "EVA": {"bear": 1350, "base": 1650, "bull": 2050},
            "DCF-FCFF": {"bear": 1250, "base": 1550, "bull": 1900},
            "Residual Income": {"bear": 1100, "base": 1400, "bull": 1700},
            "PB-ROE": {"bear": 900, "base": 1150, "bull": 1400}
        },
        "current_price": 1900
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
            "EV/EBITDA": {"bear": 150, "base": 195, "bull": 250},
            "Cycle PE": {"bear": 145, "base": 185, "bull": 235},
            "FCF Yield": {"bear": 140, "base": 180, "bull": 225},
            "Asset Value": {"bear": 135, "base": 170, "bull": 215}
        },
        "current_price": 182
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
            "PB-ROE": {"bear": 110, "base": 132, "bull": 155},
            "Residual Income": {"bear": 105, "base": 128, "bull": 150},
            "Dividend Yield": {"bear": 100, "base": 122, "bull": 145},
            "PE": {"bear": 98, "base": 118, "bull": 140}
        },
        "current_price": 130
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

    abs_gap = abs(gap)
    if abs_gap <= 15:
        st.success("校準結果：PASS｜Base合理價與現價差距在 ±15% 內。")
    elif abs_gap <= 30:
        st.warning("校準結果：WATCH｜差距在 ±15%～30%，需觀察權重或景氣位置。")
    else:
        st.error("校準結果：FAIL｜差距超過 ±30%，需重新檢查模型權重或估值基準。")

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
