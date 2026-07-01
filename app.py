
import json
from datetime import datetime
import numpy as np
import pandas as pd
import streamlit as st

try:
    import yfinance as yf
except Exception:
    yf = None

st.set_page_config(page_title="Enterprise Valuation Lab V14.2", page_icon="🏛️", layout="wide")

st.title("🏛️ Enterprise Valuation Lab")
st.subheader("V14.2｜Market Calibration Engine 市場倍率校正引擎")
st.info("V14.2重點：用真實市場價格反推各CID/產業目前願付倍率，建立校正後的 Bear / Base / Bull 區間。")

# ============================================================
# Base Universe
# ============================================================

COMPANIES = [
    {"公司":"2330 台積電","代號":"2330.TW","fallback_price":2505,"CID":"AI Infrastructure","Stage":"Leader","Industry_Health":92,"fallback":{"EPS":65.46,"BVPS":206.5,"ROE":31.7,"ROIC":46.7,"FCF_Margin":26.05,"Revenue_CAGR":18.94,"EPS_Growth":19.57,"Dividend":15}},
    {"公司":"2454 聯發科","代號":"2454.TW","fallback_price":4335,"CID":"AI Platform","Stage":"Leader","Industry_Health":88,"fallback":{"EPS":65.98,"BVPS":250.99,"ROE":26.29,"ROIC":59.58,"FCF_Margin":23.05,"Revenue_CAGR":2.79,"EPS_Growth":-3.76,"Dividend":75}},
    {"公司":"2383 台光電","代號":"2383.TW","fallback_price":5535,"CID":"Advanced Materials","Stage":"Growth","Industry_Health":90,"fallback":{"EPS":40.88,"BVPS":140.81,"ROE":29.03,"ROIC":29.7,"FCF_Margin":2.22,"Revenue_CAGR":34.58,"EPS_Growth":42.4,"Dividend":40}},
    {"公司":"2382 廣達","代號":"2382.TW","fallback_price":372,"CID":"AI Server Platform","Stage":"Growth","Industry_Health":88,"fallback":{"EPS":18.92,"BVPS":53.83,"ROE":36.84,"ROIC":21.36,"FCF_Margin":-1.2,"Revenue_CAGR":18.37,"EPS_Growth":37.32,"Dividend":6}},
    {"公司":"3017 奇鋐","代號":"3017.TW","fallback_price":2620,"CID":"Thermal Solution","Stage":"Growth","Industry_Health":86,"fallback":{"EPS":60.1,"BVPS":115.16,"ROE":61.69,"ROIC":100.96,"FCF_Margin":22.75,"Revenue_CAGR":35.59,"EPS_Growth":66.43,"Dividend":12}},
    {"公司":"6215 和椿","代號":"6215.TWO","fallback_price":108,"CID":"Intelligent Automation","Stage":"Growth","Industry_Health":78,"fallback":{"EPS":4.2,"BVPS":32,"ROE":12,"ROIC":14,"FCF_Margin":8,"Revenue_CAGR":18,"EPS_Growth":20,"Dividend":1.2}},
    {"公司":"2408 南亞科","代號":"2408.TW","fallback_price":421,"CID":"Memory Cycle","Stage":"Cycle","Industry_Health":82,"fallback":{"EPS":10.81,"BVPS":62.25,"ROE":19.39,"ROIC":5.22,"FCF_Margin":7.34,"Revenue_CAGR":5.35,"EPS_Growth":-54.76,"Dividend":0.5}},
    {"公司":"2881 富邦金","代號":"2881.TW","fallback_price":122.5,"CID":"Financial Franchise","Stage":"Stable","Industry_Health":80,"fallback":{"EPS":8.37,"BVPS":71.61,"ROE":18.73,"ROIC":10,"FCF_Margin":1.52,"Revenue_CAGR":14.15,"EPS_Growth":37.11,"Dividend":5}},
    {"公司":"2603 長榮","代號":"2603.TW","fallback_price":185.5,"CID":"Shipping Cycle","Stage":"Cycle","Industry_Health":78,"fallback":{"EPS":31.64,"BVPS":268.71,"ROE":8.22,"ROIC":13.41,"FCF_Margin":20.89,"Revenue_CAGR":-15.46,"EPS_Growth":-41.02,"Dividend":12}},
    {"公司":"2412 中華電","代號":"2412.TW","fallback_price":141.5,"CID":"Telecom Infrastructure","Stage":"Stable","Industry_Health":85,"fallback":{"EPS":5.02,"BVPS":51.09,"ROE":9.99,"ROIC":10.59,"FCF_Margin":21.13,"Revenue_CAGR":2.86,"EPS_Growth":2.11,"Dividend":4.7}},
]

PEER_MULTIPLES = {
    "AI Infrastructure": {"method":"PE","bear":32,"base":38,"bull":46},
    "AI Platform": {"method":"PE","bear":42,"base":55,"bull":70},
    "Advanced Materials": {"method":"PE","bear":80,"base":105,"bull":135},
    "AI Server Platform": {"method":"PE","bear":20,"base":28,"bull":38},
    "Thermal Solution": {"method":"PE","bear":34,"base":44,"bull":58},
    "Intelligent Automation": {"method":"PE","bear":22,"base":28,"bull":38},
    "Memory Cycle": {"method":"PB","bear":1.2,"base":1.7,"bull":2.3},
    "Financial Franchise": {"method":"PB","bear":1.4,"base":1.8,"bull":2.2},
    "Shipping Cycle": {"method":"PB","bear":0.55,"base":0.8,"bull":1.1},
    "Telecom Infrastructure": {"method":"Dividend","bear":0.045,"base":0.038,"bull":0.032},
}

def safe(x):
    try:
        if x is None or pd.isna(x): return None
        return float(x)
    except Exception:
        return None

@st.cache_data(ttl=900)
def fetch_price(symbol, fallback):
    if yf:
        try:
            t = yf.Ticker(symbol)
            fast = getattr(t, "fast_info", {}) or {}
            p = fast.get("last_price") or fast.get("lastPrice")
            if p is None:
                hist = t.history(period="5d")
                if not hist.empty:
                    p = float(hist["Close"].dropna().iloc[-1])
            if p and p > 0:
                return round(float(p),2), f"yfinance:{symbol}"
        except Exception:
            pass
    return fallback, "fallback"

def market_multiple(row):
    if row["EPS"] and row["EPS"] > 0:
        pe = row["現價"]/row["EPS"]
    else:
        pe = np.nan
    pb = row["現價"]/row["BVPS"] if row["BVPS"] and row["BVPS"] > 0 else np.nan
    dy = row["Dividend"]/row["現價"] if row["現價"] and row["現價"] > 0 else np.nan
    return pe, pb, dy

def calibrated_value(row):
    cid = row["CID"]
    cfg = PEER_MULTIPLES[cid]
    method = cfg["method"]
    eps, bvps, div = row["EPS"], row["BVPS"], row["Dividend"]

    if method == "PE":
        raw_bear, raw_base, raw_bull = eps*cfg["bear"], eps*cfg["base"], eps*cfg["bull"]
    elif method == "PB":
        raw_bear, raw_base, raw_bull = bvps*cfg["bear"], bvps*cfg["base"], bvps*cfg["bull"]
    else:
        raw_bear, raw_base, raw_bull = div/cfg["bear"], div/cfg["base"], div/cfg["bull"]

    # Industry health只做微調，不再大幅拉動
    adj = 0.90 + (row["Industry_Health"]/100)*0.20
    bear, base, bull = raw_bear*adj, raw_base*adj, raw_bull*adj
    return round(bear,2), round(base,2), round(bull,2), method, cfg

rows=[]
for c in COMPANIES:
    p, ps = fetch_price(c["代號"], c["fallback_price"])
    r = {**c, **c["fallback"], "現價":p, "Price Source":ps}
    pe,pb,dy = market_multiple(r)
    bear,base,bull,method,cfg = calibrated_value(r)
    upside = (base/p-1)*100 if p else None
    status = "合理偏低" if upside is not None and upside > 15 else "合理偏高" if upside is not None and upside < -15 else "合理區間"
    rows.append({
        "公司":c["公司"],"代號":c["代號"],"現價":p,"CID":c["CID"],"Stage":c["Stage"],
        "EPS":r["EPS"],"BVPS":r["BVPS"],"Dividend":r["Dividend"],"ROE":r["ROE"],"ROIC":r["ROIC"],
        "Market PE":round(pe,2) if not pd.isna(pe) else None,
        "Market PB":round(pb,2) if not pd.isna(pb) else None,
        "Dividend Yield%":round(dy*100,2) if not pd.isna(dy) else None,
        "Calibration Method":method,
        "Bear Multiple":cfg["bear"],"Base Multiple":cfg["base"],"Bull Multiple":cfg["bull"],
        "Industry_Health":c["Industry_Health"],
        "Bear":bear,"Base":base,"Bull":bull,
        "Upside%":round(upside,1) if upside is not None else None,
        "價格判斷":status,
    })

df = pd.DataFrame(rows)

cid_cal = df.groupby("CID").agg(
    公司數=("公司","count"),
    平均Market_PE=("Market PE","mean"),
    平均Market_PB=("Market PB","mean"),
    平均Upside=("Upside%","mean")
).reset_index().round(2)

summary = pd.DataFrame([
    {"項目":"樣本公司數","結果":len(df)},
    {"項目":"平均Market PE","結果":round(df["Market PE"].dropna().mean(),2)},
    {"項目":"平均Market PB","結果":round(df["Market PB"].dropna().mean(),2)},
    {"項目":"平均Upside","結果":f"{round(df['Upside%'].mean(),1)}%"},
    {"項目":"合理區間公司數","結果":int((df["價格判斷"]=="合理區間").sum())},
    {"項目":"合理偏低公司數","結果":int((df["價格判斷"]=="合理偏低").sum())},
    {"項目":"合理偏高公司數","結果":int((df["價格判斷"]=="合理偏高").sum())},
])

st.sidebar.header("V14.2 Market Calibration 控制台")
page = st.sidebar.radio("功能", ["Calibration Overview","Market Multiple Table","Calibrated Valuation","CID Calibration Map","Company Card","Export JSON"])
selected = st.sidebar.selectbox("選擇公司", df["公司"].tolist())
st.sidebar.divider()
st.sidebar.metric("樣本公司", len(df))
st.sidebar.metric("平均Upside", f"{round(df['Upside%'].mean(),1)}%")
st.sidebar.metric("合理區間", int((df["價格判斷"]=="合理區間").sum()))

if page == "Calibration Overview":
    st.header("一、Calibration Overview")
    st.write("V14.2 先用市場實際倍率校正 V14.1 的估值偏離。")
    st.dataframe(summary, use_container_width=True)
    st.subheader("校正後估值總表")
    st.dataframe(df[["公司","現價","CID","EPS","BVPS","Market PE","Market PB","Calibration Method","Bear","Base","Bull","Upside%","價格判斷"]], use_container_width=True)

elif page == "Market Multiple Table":
    st.header("二、Market Multiple Table")
    st.write("市場實際願付倍率 = 現價 / EPS 或 現價 / BVPS。")
    st.dataframe(df[["公司","CID","現價","EPS","BVPS","Dividend","Market PE","Market PB","Dividend Yield%"]], use_container_width=True)

elif page == "Calibrated Valuation":
    st.header("三、Calibrated Valuation")
    st.write("依 CID 對應 PE/PB/Dividend Yield 倍率資料庫重新估值。")
    st.dataframe(df[["公司","CID","Calibration Method","Bear Multiple","Base Multiple","Bull Multiple","Industry_Health","Bear","Base","Bull","Upside%"]], use_container_width=True)
    st.bar_chart(df.set_index("公司")["Upside%"])

elif page == "CID Calibration Map":
    st.header("四、CID Calibration Map")
    st.write("不同CID使用不同市場倍率族群。")
    st.dataframe(cid_cal, use_container_width=True)
    st.subheader("內建校正倍率資料庫")
    cal_table = []
    for cid,cfg in PEER_MULTIPLES.items():
        cal_table.append({"CID":cid, "Method":cfg["method"], "Bear":cfg["bear"], "Base":cfg["base"], "Bull":cfg["bull"]})
    st.dataframe(pd.DataFrame(cal_table), use_container_width=True)

elif page == "Company Card":
    st.header("五、Company Card")
    row = df[df["公司"]==selected].iloc[0]
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("現價", f"{row['現價']:,.2f}")
    c2.metric("Base", f"{row['Base']:,.2f}", f"{row['Upside%']}%")
    c3.metric("Market PE", row["Market PE"])
    c4.metric("價格判斷", row["價格判斷"])
    detail = pd.DataFrame([
        {"項目":"CID","內容":row["CID"]},
        {"項目":"Stage","內容":row["Stage"]},
        {"項目":"校正方法","內容":row["Calibration Method"]},
        {"項目":"Bear Multiple","內容":row["Bear Multiple"]},
        {"項目":"Base Multiple","內容":row["Base Multiple"]},
        {"項目":"Bull Multiple","內容":row["Bull Multiple"]},
        {"項目":"Market PE","內容":row["Market PE"]},
        {"項目":"Market PB","內容":row["Market PB"]},
        {"項目":"Dividend Yield%","內容":row["Dividend Yield%"]},
    ])
    st.dataframe(detail, use_container_width=True)

elif page == "Export JSON":
    st.header("六、Export JSON")
    export = {
        "version":"V14.2 Market Calibration Engine",
        "updated_at":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "purpose":"Use market-implied multiples by CID to calibrate valuation ranges.",
        "results":df.to_dict(orient="records"),
        "cid_calibration":cid_cal.to_dict(orient="records"),
        "multiple_database":PEER_MULTIPLES,
        "summary":summary.to_dict(orient="records"),
    }
    st.code(json.dumps(export, ensure_ascii=False, indent=2), language="json")
