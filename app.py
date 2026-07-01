import json
from datetime import datetime
import pandas as pd
import streamlit as st

try:
    import yfinance as yf
except Exception:
    yf = None

st.set_page_config(page_title="Enterprise Valuation Lab V15.1A", page_icon="🏛️", layout="wide")
st.title("🏛️ Enterprise Valuation Lab")
st.subheader("V15.1A｜Leader Premium Prototype 龍頭溢價試作版")
st.info("只測試公司層級 Leader Premium：不改 CID、不改 Model Selector、不改產業倍率。")

COMPANIES = [
    {"公司":"2330 台積電","代號":"2330.TW","現價備援":2505,"CID":"AI Infrastructure","Stage":"Leader","Leader_Level":"Global Leader","EPS":65.46,"BVPS":206.5,"ROE":31.7,"ROIC":46.7,"FCF_Margin":26.05,"Revenue_CAGR":18.94,"EPS_Growth":19.57,"Dividend":15,"Industry_Health":92},
    {"公司":"2454 聯發科","代號":"2454.TW","現價備援":4335,"CID":"AI Platform","Stage":"Leader","Leader_Level":"Global Leader","EPS":65.98,"BVPS":250.99,"ROE":26.29,"ROIC":59.58,"FCF_Margin":23.05,"Revenue_CAGR":2.79,"EPS_Growth":-3.76,"Dividend":75,"Industry_Health":88},
    {"公司":"2383 台光電","代號":"2383.TW","現價備援":5535,"CID":"Advanced Materials","Stage":"Growth","Leader_Level":"Global Leader","EPS":40.88,"BVPS":140.81,"ROE":29.03,"ROIC":29.7,"FCF_Margin":2.22,"Revenue_CAGR":34.58,"EPS_Growth":42.4,"Dividend":40,"Industry_Health":90},
    {"公司":"2382 廣達","代號":"2382.TW","現價備援":372,"CID":"AI Server Platform","Stage":"Growth","Leader_Level":"Regional Leader","EPS":18.92,"BVPS":53.83,"ROE":36.84,"ROIC":21.36,"FCF_Margin":-1.2,"Revenue_CAGR":18.37,"EPS_Growth":37.32,"Dividend":6,"Industry_Health":88},
    {"公司":"3017 奇鋐","代號":"3017.TW","現價備援":2620,"CID":"Thermal Solution","Stage":"Growth","Leader_Level":"Global Leader","EPS":60.1,"BVPS":115.16,"ROE":61.69,"ROIC":100.96,"FCF_Margin":22.75,"Revenue_CAGR":35.59,"EPS_Growth":66.43,"Dividend":12,"Industry_Health":86},
    {"公司":"6215 和椿","代號":"6215.TWO","現價備援":108,"CID":"Intelligent Automation","Stage":"Growth","Leader_Level":"Growth Company","EPS":4.2,"BVPS":32,"ROE":12,"ROIC":14,"FCF_Margin":8,"Revenue_CAGR":18,"EPS_Growth":20,"Dividend":1.2,"Industry_Health":78},
    {"公司":"2408 南亞科","代號":"2408.TW","現價備援":421,"CID":"Memory Cycle","Stage":"Cycle","Leader_Level":"Cycle","EPS":10.81,"BVPS":62.25,"ROE":19.39,"ROIC":5.22,"FCF_Margin":7.34,"Revenue_CAGR":5.35,"EPS_Growth":-54.76,"Dividend":0.5,"Industry_Health":82},
    {"公司":"2881 富邦金","代號":"2881.TW","現價備援":122.5,"CID":"Financial Franchise","Stage":"Stable","Leader_Level":"Regional Leader","EPS":8.37,"BVPS":71.61,"ROE":18.73,"ROIC":10,"FCF_Margin":1.52,"Revenue_CAGR":14.15,"EPS_Growth":37.11,"Dividend":5,"Industry_Health":80},
    {"公司":"2603 長榮","代號":"2603.TW","現價備援":185.5,"CID":"Shipping Cycle","Stage":"Cycle","Leader_Level":"Cycle","EPS":31.64,"BVPS":268.71,"ROE":8.22,"ROIC":13.41,"FCF_Margin":20.89,"Revenue_CAGR":-15.46,"EPS_Growth":-41.02,"Dividend":12,"Industry_Health":78},
    {"公司":"2412 中華電","代號":"2412.TW","現價備援":141.5,"CID":"Telecom Infrastructure","Stage":"Stable","Leader_Level":"Regional Leader","EPS":5.02,"BVPS":51.09,"ROE":9.99,"ROIC":10.59,"FCF_Margin":21.13,"Revenue_CAGR":2.86,"EPS_Growth":2.11,"Dividend":4.7,"Industry_Health":85},
]

CAL = {
    "AI Infrastructure": {"Base":1.25,"Growth":1.10,"ROIC":1.20,"CAP":1.15},
    "AI Platform": {"Base":1.35,"Growth":1.10,"ROIC":1.20,"CAP":1.15},
    "Advanced Materials": {"Base":1.75,"Growth":1.35,"ROIC":1.10,"CAP":1.20},
    "AI Server Platform": {"Base":1.10,"Growth":1.05,"ROIC":1.05,"CAP":1.05},
    "Thermal Solution": {"Base":1.30,"Growth":1.20,"ROIC":1.15,"CAP":1.10},
    "Intelligent Automation": {"Base":1.20,"Growth":1.10,"ROIC":1.05,"CAP":1.05},
    "Memory Cycle": {"Base":1.00,"Growth":1.00,"ROIC":1.00,"CAP":1.00},
    "Financial Franchise": {"Base":1.00,"Growth":1.00,"ROIC":1.00,"CAP":1.00},
    "Shipping Cycle": {"Base":1.00,"Growth":1.00,"ROIC":1.00,"CAP":1.00},
    "Telecom Infrastructure": {"Base":1.00,"Growth":1.00,"ROIC":1.00,"CAP":1.00},
}
LEADER = {"Global Leader":1.15,"Regional Leader":1.08,"Growth Company":1.05,"Stable":1.00,"Cycle":1.00}
WEIGHTS = {
    "AI Infrastructure":{"DCF":0.25,"FCFF":0.20,"ROIC Premium":0.25,"CAP":0.30},
    "AI Platform":{"DCF":0.25,"FCFE":0.20,"ROIC Premium":0.25,"CAP":0.30},
    "Advanced Materials":{"DCF":0.20,"FCFF":0.20,"ROIC Premium":0.25,"CAP":0.35},
    "AI Server Platform":{"DCF":0.25,"FCFF":0.25,"ROIC Premium":0.20,"CAP":0.30},
    "Thermal Solution":{"DCF":0.25,"FCFF":0.20,"ROIC Premium":0.30,"CAP":0.25},
    "Intelligent Automation":{"DCF":0.25,"FCFF":0.20,"EVA":0.20,"ROIC Premium":0.20,"CAP":0.15},
    "Memory Cycle":{"Cycle PE":0.35,"EV/EBITDA":0.25,"Asset Value":0.30,"EBO":0.10},
    "Financial Franchise":{"PB Asset":0.30,"EBO":0.30,"Dividend":0.25,"EVA":0.15},
    "Shipping Cycle":{"Cycle PE":0.30,"EV/EBITDA":0.30,"Asset Value":0.30,"Dividend":0.10},
    "Telecom Infrastructure":{"DCF":0.25,"FCFE":0.15,"EBO":0.20,"Dividend":0.40},
}

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

def dcf(r):
    g=max(-5,min(25,r["EPS_Growth"])); q=1+max(0,r["FCF_Margin"])*0.008; pe=14+g*0.35
    if r["Stage"]=="Leader": pe+=6
    elif r["Stage"]=="Growth": pe+=4
    elif r["Stage"]=="Stable": pe+=2
    return max(0,r["EPS"]*pe*q)
def fcff(r): return max(0,r["EPS"]*(13+max(-5,min(20,r["Revenue_CAGR"]))*0.25+max(0,r["FCF_Margin"])*0.18))
def fcfe(r): return max(0,r["EPS"]*(11+max(0,r["ROE"]-8)*0.35)*(1+min(.25,max(0,r["Dividend"]/max(r["EPS"],.01))*0.10)))
def eva(r): return max(0,r["BVPS"]*(1+(r["ROE"]-(10.5 if r["Stage"]=="Growth" else 9))*0.08))
def ebo(r): return max(0,r["BVPS"]+r["BVPS"]*((r["ROE"]-9.5)/100)*5+r["EPS"]*max(0,max(-3,min(15,r["EPS_Growth"])))*0.25)
def roic(r): return max(0,r["EPS"]*(16+max(0,r["ROIC"]-10)*0.30+max(0,r["FCF_Margin"])*0.12))
def cap(r):
    y=10 if r["Stage"]=="Leader" else 8 if r["Stage"]=="Growth" else 6
    if "AI" in r["CID"]: y+=2
    return max(0,r["EPS"]*(14+y*1.6))
def cycle_pe(r): return max(0,r["EPS"]*((7 if r["CID"]=="Shipping Cycle" else 18 if r["CID"]=="Memory Cycle" else 14))*(0.80+r["Industry_Health"]/100*0.45))
def ev_ebitda(r): return max(0,r["EPS"]*((6.5 if r["CID"]=="Shipping Cycle" else 9 if r["CID"]=="Memory Cycle" else 12))*1.12)
def asset(r): return max(0,r["BVPS"]*((.85 if r["CID"]=="Shipping Cycle" else 1.5 if r["CID"]=="Memory Cycle" else 1.7 if r["CID"]=="Financial Franchise" else 1)))
def divval(r):
    y=.038 if r["CID"]=="Telecom Infrastructure" else .045 if r["CID"]=="Financial Franchise" else .07 if r["CID"]=="Shipping Cycle" else .05
    return r["Dividend"]/y if r["Dividend"]>0 else 0

def raw_components(r):
    return {"DCF":dcf(r),"FCFF":fcff(r),"FCFE":fcfe(r),"EVA":eva(r),"EBO":ebo(r),"ROIC Premium":roic(r),"CAP":cap(r),"Cycle PE":cycle_pe(r),"EV/EBITDA":ev_ebitda(r),"Asset Value":asset(r),"PB Asset":asset(r),"Dividend":divval(r)}
def calibrated_components(r):
    out={}; cal=CAL[r["CID"]]
    for k,v in raw_components(r).items():
        f=cal["Base"]
        if k in ["DCF","FCFF","FCFE"]: f*=cal["Growth"]
        if k=="ROIC Premium": f*=cal["ROIC"]
        if k=="CAP": f*=cal["CAP"]
        out[k]=v*f
    return out

def composite(r, leader=False):
    comps=calibrated_components(r); base=sum(comps[k]*w for k,w in WEIGHTS[r["CID"]].items())
    if leader: base*=LEADER[r["Leader_Level"]]
    if r["Stage"]=="Cycle": bear,bull=base*.70,base*1.45
    elif r["Stage"]=="Growth": bear,bull=base*.78,base*1.38
    elif r["Stage"]=="Leader": bear,bull=base*.82,base*1.30
    else: bear,bull=base*.85,base*1.18
    return round(bear,2),round(base,2),round(bull,2),comps

def status(price,value):
    gap=(price/value-1)*100 if value and value>0 else None
    if gap is None: return "N/A",None
    ag=abs(gap); s="Fair Zone" if ag<=15 else "Mild Divergence" if ag<=30 else "Strong Divergence" if ag<=50 else "Extreme Divergence"
    return s,round(gap,1)

rows=[]; comps=[]
for c in COMPANIES:
    price,src=fetch_price(c["代號"],c["現價備援"]); r={**c,"現價":price,"Price Source":src}
    cb,cv,cu,cc=composite(r,False); lb,lv,lu,lc=composite(r,True)
    cs,cg=status(price,cv); ls,lg=status(price,lv)
    rows.append({"公司":c["公司"],"代號":c["代號"],"現價":price,"CID":c["CID"],"Stage":c["Stage"],"Leader_Level":c["Leader_Level"],"Leader Premium":LEADER[c["Leader_Level"]],"Calibrated Base":cv,"Calibrated Gap%":cg,"Calibrated Status":cs,"Leader Final Bear":lb,"Leader Final Base":lv,"Leader Final Bull":lu,"Leader Final Gap%":lg,"Leader Final Status":ls,"Gap改善":"Yes" if abs(lg)<abs(cg) else "No","Intrinsic Weights":" / ".join([f"{k}:{int(v*100)}%" for k,v in WEIGHTS[c["CID"]].items()]),"Price Source":src})
    for k,v in cc.items(): comps.append({"公司":c["公司"],"CID":c["CID"],"模型":k,"Calibrated模型值":round(v,2),"Leader後模型值":round(v*LEADER[c["Leader_Level"]],2),"是否使用":"Yes" if k in WEIGHTS[c["CID"]] else "No","權重":WEIGHTS[c["CID"]].get(k,0)})
df=pd.DataFrame(rows); component_df=pd.DataFrame(comps)
summary=pd.DataFrame([
    {"項目":"樣本公司數","結果":len(df)},
    {"項目":"Calibrated Fair Zone","結果":int((df["Calibrated Status"]=="Fair Zone").sum())},
    {"項目":"Leader Final Fair Zone","結果":int((df["Leader Final Status"]=="Fair Zone").sum())},
    {"項目":"Calibrated平均絕對Gap","結果":f"{round(df['Calibrated Gap%'].abs().mean(),1)}%"},
    {"項目":"Leader Final平均絕對Gap","結果":f"{round(df['Leader Final Gap%'].abs().mean(),1)}%"},
    {"項目":"Gap改善公司數","結果":int((df["Gap改善"]=="Yes").sum())},
])
leader_summary=df.groupby("Leader_Level").agg(公司數=("公司","count"),平均CalibratedGap=("Calibrated Gap%","mean"),平均LeaderGap=("Leader Final Gap%","mean"),改善公司數=("Gap改善",lambda x:int((x=="Yes").sum())),FairZone數=("Leader Final Status",lambda x:int((x=="Fair Zone").sum()))).reset_index().round(1)

st.sidebar.header("V15.1A Leader Premium 控制台")
page=st.sidebar.radio("功能",["Leader Premium Overview","Before vs After","Leader Premium Center","Company Detail","Component Impact","Export JSON"])
selected=st.sidebar.selectbox("選擇公司",df["公司"].tolist())
st.sidebar.divider(); st.sidebar.metric("Calibrated Fair Zone",int((df["Calibrated Status"]=="Fair Zone").sum())); st.sidebar.metric("Leader Fair Zone",int((df["Leader Final Status"]=="Fair Zone").sum())); st.sidebar.metric("改善公司數",int((df["Gap改善"]=="Yes").sum()))

if page=="Leader Premium Overview":
    st.header("一、Leader Premium Overview"); st.dataframe(summary,use_container_width=True)
    st.dataframe(df[["公司","現價","CID","Leader_Level","Leader Premium","Calibrated Base","Calibrated Gap%","Calibrated Status","Leader Final Base","Leader Final Gap%","Leader Final Status","Gap改善"]],use_container_width=True)
elif page=="Before vs After":
    st.header("二、Before vs After"); st.dataframe(df[["公司","現價","Calibrated Base","Calibrated Gap%","Leader Final Base","Leader Final Gap%","Gap改善"]],use_container_width=True); st.bar_chart(df.set_index("公司")[["Calibrated Gap%","Leader Final Gap%"]])
elif page=="Leader Premium Center":
    st.header("三、Leader Premium Center"); st.dataframe(pd.DataFrame([{"Leader_Level":k,"Premium":v} for k,v in LEADER.items()]),use_container_width=True); st.subheader("分組結果"); st.dataframe(leader_summary,use_container_width=True)
elif page=="Company Detail":
    row=df[df["公司"]==selected].iloc[0]; cdf=component_df[component_df["公司"]==selected]
    st.header("四、Company Detail"); c1,c2,c3,c4=st.columns(4); c1.metric("現價",f"{row['現價']:,.2f}"); c2.metric("Calibrated Base",f"{row['Calibrated Base']:,.2f}",f"{row['Calibrated Gap%']}%"); c3.metric("Leader Final Base",f"{row['Leader Final Base']:,.2f}",f"{row['Leader Final Gap%']}%"); c4.metric("Gap改善",row["Gap改善"])
    st.dataframe(pd.DataFrame([{"項目":"CID","內容":row["CID"]},{"項目":"Stage","內容":row["Stage"]},{"項目":"Leader_Level","內容":row["Leader_Level"]},{"項目":"Leader Premium","內容":row["Leader Premium"]},{"項目":"Intrinsic Weights","內容":row["Intrinsic Weights"]}]),use_container_width=True)
    st.subheader("Component Impact"); st.dataframe(cdf,use_container_width=True); st.bar_chart(cdf[cdf["是否使用"]=="Yes"].set_index("模型")[["Calibrated模型值","Leader後模型值"]])
elif page=="Component Impact":
    st.header("五、Component Impact"); st.dataframe(component_df,use_container_width=True)
elif page=="Export JSON":
    st.header("六、Export JSON"); export={"version":"V15.1A Leader Premium Prototype","updated_at":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"purpose":"Test company-level Leader Premium after V15.0.1 CID calibration.","results":df.to_dict(orient="records"),"component_impact":component_df.to_dict(orient="records"),"leader_premium":LEADER,"summary":summary.to_dict(orient="records")}; st.code(json.dumps(export,ensure_ascii=False,indent=2),language="json")
