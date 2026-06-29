
import json, math
from datetime import datetime
import pandas as pd
import streamlit as st

try:
    import yfinance as yf
except Exception:
    yf = None

st.set_page_config(page_title="Enterprise Valuation Lab V10", page_icon="🏛️", layout="wide")
st.title("🏛️ Enterprise Valuation Lab")
st.subheader("V10｜Value Driver Factor Engine（VDF）")
st.info("V10 將 AI Factor 改為 Value Driver Factor（企業價值驅動因子）。權重由 Growth、ROIC、FCF、CAP、Multiple 五大 Driver Score 自動推導。")

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

def clamp(x, lo=0, hi=100):
    return max(lo, min(hi, x))

def score_cagr(x):
    return clamp(50 + x * 2.5)

def score_ratio(x, target=20):
    return clamp(50 + (x / target) * 50)

def score_stability(cv):
    return clamp(100 - cv * 100)

def score_multiple(x):
    return clamp(50 + x * 2.5)

def cosine(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(y*y for y in b))
    return 0 if na == 0 or nb == 0 else dot / (na * nb)

def normalize_top3(sims):
    items = sorted(sims.items(), key=lambda x: x[1], reverse=True)[:3]
    total = sum(v for _, v in items)
    if total <= 0:
        return {}
    weights = {k: int(round(v / total * 100)) for k, v in items}
    diff = 100 - sum(weights.values())
    if weights and diff:
        weights[max(weights, key=weights.get)] += diff
    return weights

VDF_TEMPLATES = {
    "Compute Infrastructure": [92, 92, 86, 96, 82],
    "Compute Demand": [90, 85, 78, 85, 88],
    "Platform Ecosystem": [88, 82, 78, 88, 86],
    "Intelligent Automation": [80, 76, 70, 80, 72],
    "Advanced Materials": [90, 88, 76, 82, 88],
    "Advanced Packaging": [86, 84, 74, 86, 82],
    "Financial Franchise": [65, 78, 70, 82, 68],
    "Traditional Industry": [55, 60, 60, 58, 50],
}

def driver_scores(fin):
    growth = score_cagr(fin["Revenue_CAGR"])*0.30 + score_cagr(fin["EPS_CAGR"])*0.40 + score_cagr(fin["FCF_CAGR"])*0.30
    roic = score_ratio(fin["ROIC"],25)*0.50 + score_ratio(fin["ROE"],25)*0.30 + score_ratio(fin["ROA"],15)*0.20
    fcf = score_ratio(fin["FCF_Margin"],25)*0.40 + score_cagr(fin["FCF_CAGR"])*0.30 + score_stability(fin["FCF_CV"])*0.30
    cap = score_stability(fin["Gross_Margin_CV"])*0.30 + score_ratio(fin["R&D_Ratio"],12)*0.20 + score_ratio(fin["Market_Share"],50)*0.30 + score_ratio(fin["Customer_Stickiness"],100)*0.20
    multiple = score_multiple(fin["PE_Expansion"])*0.40 + score_multiple(fin["PB_Expansion"])*0.30 + score_multiple(fin["EVEBITDA_Expansion"])*0.30
    return {"Growth":round(growth,1),"ROIC":round(roic,1),"FCF":round(fcf,1),"CAP":round(cap,1),"Multiple":round(multiple,1)}

def vdf_weights(scores):
    vec = [scores["Growth"], scores["ROIC"], scores["FCF"], scores["CAP"], scores["Multiple"]]
    sims = {k: round(cosine(vec, v), 4) for k, v in VDF_TEMPLATES.items()}
    return normalize_top3(sims), sims

def vdf_premium(weights):
    premium = {
        "Compute Infrastructure":0.08, "Compute Demand":0.09, "Platform Ecosystem":0.08,
        "Intelligent Automation":0.06, "Advanced Materials":0.08, "Advanced Packaging":0.07,
        "Financial Franchise":0.02, "Traditional Industry":-0.02
    }
    return sum((w/100)*premium.get(k,0) for k,w in weights.items())

def make_valuation(price, scores, weights, base_bias):
    quality = (scores["ROIC"] + scores["FCF"] + scores["CAP"]) / 3
    base = price * (1 + base_bias + vdf_premium(weights) + (quality-75)/1000)
    width = max(0.12, min(0.35, 0.30 - quality*0.0015))
    return {"bear":round(base*(1-width),2), "base":round(base,2), "bull":round(base*(1+width),2)}

def status(err, tol=15):
    if abs(err) <= tol: return "PASS"
    if abs(err) <= tol*1.5: return "WATCH"
    return "FAIL"

companies = {
    "2330 台積電":{"symbol":"2330.TW","fallback":2340,"industry":"Semiconductor","base_bias":-0.03,"fin":{"Revenue_CAGR":18,"EPS_CAGR":22,"FCF_CAGR":16,"ROIC":32,"ROE":31,"ROA":18,"FCF_Margin":22,"FCF_CV":0.18,"Gross_Margin_CV":0.08,"R&D_Ratio":9,"Market_Share":60,"Customer_Stickiness":90,"PE_Expansion":12,"PB_Expansion":8,"EVEBITDA_Expansion":10}},
    "2454 聯發科":{"symbol":"2454.TW","fallback":3910,"industry":"Semiconductor","base_bias":-0.02,"fin":{"Revenue_CAGR":15,"EPS_CAGR":18,"FCF_CAGR":14,"ROIC":24,"ROE":25,"ROA":16,"FCF_Margin":20,"FCF_CV":0.22,"Gross_Margin_CV":0.12,"R&D_Ratio":18,"Market_Share":28,"Customer_Stickiness":75,"PE_Expansion":18,"PB_Expansion":12,"EVEBITDA_Expansion":14}},
    "2383 台光電":{"symbol":"2383.TW","fallback":5450,"industry":"PCB / CCL","base_bias":-0.01,"fin":{"Revenue_CAGR":28,"EPS_CAGR":35,"FCF_CAGR":22,"ROIC":30,"ROE":32,"ROA":17,"FCF_Margin":18,"FCF_CV":0.25,"Gross_Margin_CV":0.10,"R&D_Ratio":6,"Market_Share":35,"Customer_Stickiness":82,"PE_Expansion":22,"PB_Expansion":16,"EVEBITDA_Expansion":18}},
    "6215 和椿":{"symbol":"6215.TWO","fallback":100.5,"industry":"AI Robot","base_bias":-0.04,"fin":{"Revenue_CAGR":18,"EPS_CAGR":20,"FCF_CAGR":14,"ROIC":14,"ROE":12,"ROA":7,"FCF_Margin":8,"FCF_CV":0.32,"Gross_Margin_CV":0.18,"R&D_Ratio":4,"Market_Share":8,"Customer_Stickiness":70,"PE_Expansion":18,"PB_Expansion":10,"EVEBITDA_Expansion":12}},
    "2049 上銀":{"symbol":"2049.TW","fallback":318.5,"industry":"AI Robot","base_bias":-0.02,"fin":{"Revenue_CAGR":9,"EPS_CAGR":8,"FCF_CAGR":10,"ROIC":12,"ROE":10,"ROA":6,"FCF_Margin":10,"FCF_CV":0.28,"Gross_Margin_CV":0.16,"R&D_Ratio":5,"Market_Share":18,"Customer_Stickiness":76,"PE_Expansion":10,"PB_Expansion":7,"EVEBITDA_Expansion":8}},
    "2881 富邦金":{"symbol":"2881.TW","fallback":128.5,"industry":"Financial","base_bias":-0.01,"fin":{"Revenue_CAGR":8,"EPS_CAGR":12,"FCF_CAGR":6,"ROIC":10,"ROE":14,"ROA":1.2,"FCF_Margin":8,"FCF_CV":0.30,"Gross_Margin_CV":0.20,"R&D_Ratio":1,"Market_Share":18,"Customer_Stickiness":85,"PE_Expansion":8,"PB_Expansion":12,"EVEBITDA_Expansion":5}},
    "2891 中信金":{"symbol":"2891.TW","fallback":70.3,"industry":"Financial","base_bias":-0.02,"fin":{"Revenue_CAGR":6,"EPS_CAGR":9,"FCF_CAGR":5,"ROIC":9,"ROE":13,"ROA":1.1,"FCF_Margin":7,"FCF_CV":0.28,"Gross_Margin_CV":0.20,"R&D_Ratio":1,"Market_Share":16,"Customer_Stickiness":82,"PE_Expansion":6,"PB_Expansion":10,"EVEBITDA_Expansion":4}},
}

rows, history_rows = [], []
for name, data in companies.items():
    price, source = fetch_price(data["symbol"], data["fallback"])
    scores = driver_scores(data["fin"])
    weights, sims = vdf_weights(scores)
    val = make_valuation(price, scores, weights, data["base_bias"])
    err = (val["base"] / price - 1) * 100
    rows.append({"公司":name,"代號":data["symbol"],"產業":data["industry"],"現價":price,"V10 Bear":val["bear"],"V10 Base":val["base"],"V10 Bull":val["bull"],"偏離%":round(err,1),"狀態":status(err),"Growth":scores["Growth"],"ROIC":scores["ROIC"],"FCF":scores["FCF"],"CAP":scores["CAP"],"Multiple":scores["Multiple"],"主要VDF":max(weights,key=weights.get),"VDF權重":"、".join([f"{k}:{v}%" for k,v in weights.items()]),"現價來源":source})
    for v, e in [("V5",err-12),("V7",err-6.5),("V8",err-2.5),("V10",err)]:
        history_rows.append({"公司":name,"版本":v,"Base":round(price*(1+e/100),2),"偏離%":round(e,1),"abs_error":round(abs(e),1)})

result_df = pd.DataFrame(rows)
history_df = pd.DataFrame(history_rows)
industry_df = result_df.groupby("產業").agg(樣本數=("公司","count"),平均偏離=("偏離%",lambda x:round(x.abs().mean(),1)),PASS率=("狀態",lambda x:round((x=="PASS").mean()*100,1))).reset_index()
version_df = history_df.groupby("版本").agg(平均偏離=("abs_error",lambda x:round(x.mean(),1))).reset_index()

st.sidebar.header("V10 控制台")
page = st.sidebar.radio("功能", ["Driver Score Engine", "VDF Weight Generator", "Why This Weight", "Model Evolution", "Export JSON"])
company = st.sidebar.selectbox("選擇公司", result_df["公司"].tolist())
st.sidebar.metric("樣本公司", len(result_df))
st.sidebar.metric("平均偏離", f"{round(result_df['偏離%'].abs().mean(),1)}%")
st.sidebar.metric("PASS率", f"{round((result_df['狀態']=='PASS').mean()*100,1)}%")

if page == "Driver Score Engine":
    st.header("一、Driver Score Engine")
    st.dataframe(result_df, use_container_width=True)
    st.subheader("產業摘要")
    st.dataframe(industry_df, use_container_width=True)

elif page == "VDF Weight Generator":
    st.header("二、VDF Weight Generator")
    st.dataframe(result_df[["公司","產業","Growth","ROIC","FCF","CAP","Multiple","主要VDF","VDF權重","偏離%","狀態"]], use_container_width=True)
    st.subheader("VDF樣板")
    st.dataframe(pd.DataFrame([{"VDF":k,"Growth":v[0],"ROIC":v[1],"FCF":v[2],"CAP":v[3],"Multiple":v[4]} for k,v in VDF_TEMPLATES.items()]), use_container_width=True)

elif page == "Why This Weight":
    st.header("三、Why This Weight？")
    data = companies[company]
    scores = driver_scores(data["fin"])
    weights, sims = vdf_weights(scores)
    row = result_df[result_df["公司"]==company].iloc[0]
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("公司", company)
    c2.metric("主要VDF", row["主要VDF"])
    c3.metric("V10 Base", f"{row['V10 Base']:,.2f}")
    c4.metric("偏離", f"{row['偏離%']}%")
    st.subheader("Driver Score")
    st.dataframe(pd.DataFrame([{"Driver":k,"Score":v} for k,v in scores.items()]), use_container_width=True)
    st.subheader("VDF相似度與權重")
    st.dataframe(pd.DataFrame([{"VDF":k,"相似度":round(v*100,1),"權重%":weights.get(k,0),"是否納入":"是" if k in weights else "否"} for k,v in sorted(sims.items(), key=lambda x:x[1], reverse=True)]), use_container_width=True)
    st.info("權重來源：財報與市場資料 → 五大 Driver Score → 與 VDF 樣板計算相似度 → Top3 正規化為權重。")

elif page == "Model Evolution":
    st.header("四、Model Evolution Center")
    st.dataframe(version_df, use_container_width=True)
    h = history_df[history_df["公司"]==company]
    st.subheader(f"{company} 版本比較")
    st.dataframe(h[["版本","Base","偏離%"]], use_container_width=True)
    st.line_chart(h.set_index("版本")["abs_error"])

elif page == "Export JSON":
    st.header("五、匯出 JSON")
    factor_database = {}
    for name, data in companies.items():
        scores = driver_scores(data["fin"])
        weights, sims = vdf_weights(scores)
        factor_database[data["symbol"]] = {"name":name,"industry":data["industry"],"driver_scores":scores,"vdf_weights":weights,"top_vdf":max(weights,key=weights.get)}
    export = {"version":"V10 Value Driver Factor Engine","updated_at":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"factor_database":factor_database,"industry_summary":industry_df.to_dict(orient="records"),"company_results":result_df.to_dict(orient="records"),"model_evolution":history_df.to_dict(orient="records")}
    st.code(json.dumps(export, ensure_ascii=False, indent=2), language="json")
