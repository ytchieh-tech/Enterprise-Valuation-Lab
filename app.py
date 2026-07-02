
import json
from datetime import datetime
import numpy as np
import pandas as pd
import streamlit as st

try:
    import yfinance as yf
except Exception:
    yf = None

st.set_page_config(page_title="Enterprise Valuation Lab V16.0 GHE", page_icon="🏛️", layout="wide")
st.title("🏛️ Enterprise Valuation Lab")
st.subheader("V16.0｜Growth Horizon Engine 未來成長年限引擎")
st.info("本版保留 V15 Intrinsic Fair Value，新增 Growth Horizon Engine：依 CID 的市場預期年限，產生 Expected Fair Value。不是再調倍率，而是測試市場是否正在折現未來數年成長。")

BENCHMARK = [
    # AI Infrastructure
    {"公司":"2330 台積電","代號":"2330.TW","CID":"AI Infrastructure","Stage":"Leader","fallback_price":2505,"fallback":{"EPS":65.46,"BVPS":206.5,"ROE":31.7,"ROIC":46.7,"FCF_Margin":26.05,"Revenue_CAGR":18.94,"EPS_Growth":19.57,"Dividend":15,"Industry_Health":92}},
    {"公司":"3661 世芯-KY","代號":"3661.TW","CID":"AI Infrastructure","Stage":"Growth","fallback_price":3200,"fallback":{"EPS":62,"BVPS":170,"ROE":36,"ROIC":32,"FCF_Margin":18,"Revenue_CAGR":35,"EPS_Growth":38,"Dividend":12,"Industry_Health":88}},
    {"公司":"3443 創意","代號":"3443.TW","CID":"AI Infrastructure","Stage":"Growth","fallback_price":1200,"fallback":{"EPS":32,"BVPS":92,"ROE":34,"ROIC":30,"FCF_Margin":16,"Revenue_CAGR":24,"EPS_Growth":26,"Dividend":8,"Industry_Health":86}},

    # AI Platform
    {"公司":"2454 聯發科","代號":"2454.TW","CID":"AI Platform","Stage":"Leader","fallback_price":4335,"fallback":{"EPS":65.98,"BVPS":250.99,"ROE":26.29,"ROIC":59.58,"FCF_Margin":23.05,"Revenue_CAGR":2.79,"EPS_Growth":-3.76,"Dividend":75,"Industry_Health":88}},
    {"公司":"2379 瑞昱","代號":"2379.TW","CID":"AI Platform","Stage":"Leader","fallback_price":580,"fallback":{"EPS":26,"BVPS":115,"ROE":22,"ROIC":28,"FCF_Margin":18,"Revenue_CAGR":8,"EPS_Growth":10,"Dividend":16,"Industry_Health":82}},
    {"公司":"3034 聯詠","代號":"3034.TW","CID":"AI Platform","Stage":"Leader","fallback_price":520,"fallback":{"EPS":34,"BVPS":160,"ROE":22,"ROIC":28,"FCF_Margin":20,"Revenue_CAGR":5,"EPS_Growth":6,"Dividend":28,"Industry_Health":78}},

    # AI Server
    {"公司":"2382 廣達","代號":"2382.TW","CID":"AI Server Platform","Stage":"Growth","fallback_price":372,"fallback":{"EPS":18.92,"BVPS":53.83,"ROE":36.84,"ROIC":21.36,"FCF_Margin":-1.2,"Revenue_CAGR":18.37,"EPS_Growth":37.32,"Dividend":6,"Industry_Health":88}},
    {"公司":"3231 緯創","代號":"3231.TW","CID":"AI Server Platform","Stage":"Growth","fallback_price":145,"fallback":{"EPS":8.5,"BVPS":42,"ROE":20,"ROIC":13,"FCF_Margin":4,"Revenue_CAGR":16,"EPS_Growth":22,"Dividend":3,"Industry_Health":84}},
    {"公司":"6669 緯穎","代號":"6669.TW","CID":"AI Server Platform","Stage":"Growth","fallback_price":2800,"fallback":{"EPS":95,"BVPS":360,"ROE":28,"ROIC":22,"FCF_Margin":8,"Revenue_CAGR":20,"EPS_Growth":24,"Dividend":40,"Industry_Health":86}},

    # Advanced Materials
    {"公司":"2383 台光電","代號":"2383.TW","CID":"Advanced Materials","Stage":"Growth","fallback_price":5535,"fallback":{"EPS":40.88,"BVPS":140.81,"ROE":29.03,"ROIC":29.7,"FCF_Margin":2.22,"Revenue_CAGR":34.58,"EPS_Growth":42.4,"Dividend":40,"Industry_Health":90}},
    {"公司":"6274 台燿","代號":"6274.TWO","CID":"Advanced Materials","Stage":"Growth","fallback_price":210,"fallback":{"EPS":8.5,"BVPS":55,"ROE":16,"ROIC":14,"FCF_Margin":6,"Revenue_CAGR":20,"EPS_Growth":28,"Dividend":4,"Industry_Health":86}},
    {"公司":"2368 金像電","代號":"2368.TW","CID":"Advanced Materials","Stage":"Growth","fallback_price":320,"fallback":{"EPS":14,"BVPS":62,"ROE":23,"ROIC":19,"FCF_Margin":10,"Revenue_CAGR":22,"EPS_Growth":30,"Dividend":5,"Industry_Health":86}},

    # Thermal
    {"公司":"3017 奇鋐","代號":"3017.TW","CID":"Thermal Solution","Stage":"Growth","fallback_price":2620,"fallback":{"EPS":60.1,"BVPS":115.16,"ROE":61.69,"ROIC":100.96,"FCF_Margin":22.75,"Revenue_CAGR":35.59,"EPS_Growth":66.43,"Dividend":12,"Industry_Health":86}},
    {"公司":"3324 雙鴻","代號":"3324.TWO","CID":"Thermal Solution","Stage":"Growth","fallback_price":950,"fallback":{"EPS":30,"BVPS":115,"ROE":28,"ROIC":24,"FCF_Margin":12,"Revenue_CAGR":24,"EPS_Growth":35,"Dividend":8,"Industry_Health":84}},
    {"公司":"3653 健策","代號":"3653.TW","CID":"Thermal Solution","Stage":"Leader","fallback_price":1350,"fallback":{"EPS":32,"BVPS":160,"ROE":22,"ROIC":20,"FCF_Margin":15,"Revenue_CAGR":18,"EPS_Growth":20,"Dividend":8,"Industry_Health":80}},

    # Automation
    {"公司":"6215 和椿","代號":"6215.TWO","CID":"Intelligent Automation","Stage":"Growth","fallback_price":108,"fallback":{"EPS":4.2,"BVPS":32,"ROE":12,"ROIC":14,"FCF_Margin":8,"Revenue_CAGR":18,"EPS_Growth":20,"Dividend":1.2,"Industry_Health":78}},
    {"公司":"2049 上銀","代號":"2049.TW","CID":"Intelligent Automation","Stage":"Growth","fallback_price":350,"fallback":{"EPS":7.5,"BVPS":92,"ROE":8,"ROIC":7,"FCF_Margin":5,"Revenue_CAGR":8,"EPS_Growth":10,"Dividend":4,"Industry_Health":72}},
    {"公司":"2359 所羅門","代號":"2359.TW","CID":"Intelligent Automation","Stage":"Growth","fallback_price":165,"fallback":{"EPS":5,"BVPS":38,"ROE":13,"ROIC":12,"FCF_Margin":6,"Revenue_CAGR":20,"EPS_Growth":28,"Dividend":2,"Industry_Health":78}},

    # Memory
    {"公司":"2408 南亞科","代號":"2408.TW","CID":"Memory Cycle","Stage":"Cycle","fallback_price":421,"fallback":{"EPS":10.81,"BVPS":62.25,"ROE":19.39,"ROIC":5.22,"FCF_Margin":7.34,"Revenue_CAGR":5.35,"EPS_Growth":-54.76,"Dividend":0.5,"Industry_Health":82}},
    {"公司":"2344 華邦電","代號":"2344.TW","CID":"Memory Cycle","Stage":"Cycle","fallback_price":30,"fallback":{"EPS":0.6,"BVPS":22,"ROE":3,"ROIC":2,"FCF_Margin":-3,"Revenue_CAGR":4,"EPS_Growth":-20,"Dividend":0.2,"Industry_Health":76}},
    {"公司":"2337 旺宏","代號":"2337.TW","CID":"Memory Cycle","Stage":"Cycle","fallback_price":28,"fallback":{"EPS":0.5,"BVPS":25,"ROE":2,"ROIC":1,"FCF_Margin":-5,"Revenue_CAGR":-3,"EPS_Growth":-30,"Dividend":0.1,"Industry_Health":72}},

    # Financial
    {"公司":"2881 富邦金","代號":"2881.TW","CID":"Financial Franchise","Stage":"Stable","fallback_price":122.5,"fallback":{"EPS":8.37,"BVPS":71.61,"ROE":18.73,"ROIC":10,"FCF_Margin":1.52,"Revenue_CAGR":14.15,"EPS_Growth":37.11,"Dividend":5,"Industry_Health":80}},
    {"公司":"2882 國泰金","代號":"2882.TW","CID":"Financial Franchise","Stage":"Stable","fallback_price":70,"fallback":{"EPS":5.5,"BVPS":58,"ROE":11,"ROIC":8,"FCF_Margin":2,"Revenue_CAGR":8,"EPS_Growth":12,"Dividend":3,"Industry_Health":78}},
    {"公司":"2891 中信金","代號":"2891.TW","CID":"Financial Franchise","Stage":"Stable","fallback_price":45,"fallback":{"EPS":3.6,"BVPS":28,"ROE":13,"ROIC":8,"FCF_Margin":2,"Revenue_CAGR":8,"EPS_Growth":12,"Dividend":2,"Industry_Health":78}},

    # Shipping
    {"公司":"2603 長榮","代號":"2603.TW","CID":"Shipping Cycle","Stage":"Cycle","fallback_price":185.5,"fallback":{"EPS":31.64,"BVPS":268.71,"ROE":8.22,"ROIC":13.41,"FCF_Margin":20.89,"Revenue_CAGR":-15.46,"EPS_Growth":-41.02,"Dividend":12,"Industry_Health":78}},
    {"公司":"2609 陽明","代號":"2609.TW","CID":"Shipping Cycle","Stage":"Cycle","fallback_price":78,"fallback":{"EPS":11,"BVPS":88,"ROE":12,"ROIC":10,"FCF_Margin":18,"Revenue_CAGR":-12,"EPS_Growth":-35,"Dividend":5,"Industry_Health":76}},
    {"公司":"2615 萬海","代號":"2615.TW","CID":"Shipping Cycle","Stage":"Cycle","fallback_price":95,"fallback":{"EPS":6,"BVPS":65,"ROE":9,"ROIC":8,"FCF_Margin":14,"Revenue_CAGR":-10,"EPS_Growth":-28,"Dividend":3,"Industry_Health":74}},

    # Telecom
    {"公司":"2412 中華電","代號":"2412.TW","CID":"Telecom Infrastructure","Stage":"Stable","fallback_price":141.5,"fallback":{"EPS":5.02,"BVPS":51.09,"ROE":9.99,"ROIC":10.59,"FCF_Margin":21.13,"Revenue_CAGR":2.86,"EPS_Growth":2.11,"Dividend":4.7,"Industry_Health":85}},
    {"公司":"3045 台灣大","代號":"3045.TW","CID":"Telecom Infrastructure","Stage":"Stable","fallback_price":120,"fallback":{"EPS":4.5,"BVPS":38,"ROE":12,"ROIC":9,"FCF_Margin":18,"Revenue_CAGR":3,"EPS_Growth":3,"Dividend":4.3,"Industry_Health":82}},
    {"公司":"4904 遠傳","代號":"4904.TW","CID":"Telecom Infrastructure","Stage":"Stable","fallback_price":90,"fallback":{"EPS":3.6,"BVPS":30,"ROE":12,"ROIC":9,"FCF_Margin":17,"Revenue_CAGR":3,"EPS_Growth":4,"Dividend":3.2,"Industry_Health":82}},
]

STRUCTURAL_CAL = {
    "AI Infrastructure":{"Base":1.25,"Growth":1.10,"ROIC":1.20,"CAP":1.15,"Confidence":"High","Status":"Stable"},
    "AI Platform":{"Base":1.35,"Growth":1.10,"ROIC":1.20,"CAP":1.15,"Confidence":"Medium","Status":"Observe"},
    "AI Server Platform":{"Base":1.10,"Growth":1.05,"ROIC":1.05,"CAP":1.05,"Confidence":"Medium","Status":"Observe"},
    "Advanced Materials":{"Base":1.75,"Growth":1.35,"ROIC":1.10,"CAP":1.20,"Confidence":"Low","Status":"Research Needed"},
    "Thermal Solution":{"Base":1.30,"Growth":1.20,"ROIC":1.15,"CAP":1.10,"Confidence":"High","Status":"Stable"},
    "Intelligent Automation":{"Base":1.20,"Growth":1.10,"ROIC":1.05,"CAP":1.05,"Confidence":"Medium","Status":"Observe"},
    "Memory Cycle":{"Base":1.00,"Growth":1.00,"ROIC":1.00,"CAP":1.00,"Confidence":"Medium","Status":"Cycle"},
    "Financial Franchise":{"Base":1.00,"Growth":1.00,"ROIC":1.00,"CAP":1.00,"Confidence":"High","Status":"Stable"},
    "Shipping Cycle":{"Base":1.00,"Growth":1.00,"ROIC":1.00,"CAP":1.00,"Confidence":"Medium","Status":"Cycle"},
    "Telecom Infrastructure":{"Base":1.00,"Growth":1.00,"ROIC":1.00,"CAP":1.00,"Confidence":"High","Status":"Stable"},
}

WEIGHTS = {
    "AI Infrastructure":{"DCF":0.25,"FCFF":0.20,"ROIC Premium":0.25,"CAP":0.30},
    "AI Platform":{"DCF":0.25,"FCFE":0.20,"ROIC Premium":0.25,"CAP":0.30},
    "AI Server Platform":{"DCF":0.25,"FCFF":0.25,"ROIC Premium":0.20,"CAP":0.30},
    "Advanced Materials":{"DCF":0.20,"FCFF":0.20,"ROIC Premium":0.25,"CAP":0.35},
    "Thermal Solution":{"DCF":0.25,"FCFF":0.20,"ROIC Premium":0.30,"CAP":0.25},
    "Intelligent Automation":{"DCF":0.25,"FCFF":0.20,"EVA":0.20,"ROIC Premium":0.20,"CAP":0.15},
    "Memory Cycle":{"Cycle PE":0.35,"EV/EBITDA":0.25,"Asset Value":0.30,"EBO":0.10},
    "Financial Franchise":{"PB Asset":0.30,"EBO":0.30,"Dividend":0.25,"EVA":0.15},
    "Shipping Cycle":{"Cycle PE":0.30,"EV/EBITDA":0.30,"Asset Value":0.30,"Dividend":0.10},
    "Telecom Infrastructure":{"DCF":0.25,"FCFE":0.15,"EBO":0.20,"Dividend":0.40},
}


# ============================================================
# V16.0 Growth Horizon Engine
# 市場不是只看TTM，而是依CID折現不同年限的未來成長。
# ============================================================

GROWTH_HORIZON = {
    "Financial Franchise": {"Years": 2, "Cap": 1.15, "Confidence": "High", "Mode": "Stable cash-flow"},
    "Telecom Infrastructure": {"Years": 2, "Cap": 1.20, "Confidence": "High", "Mode": "Dividend stability"},
    "Shipping Cycle": {"Years": 2, "Cap": 1.35, "Confidence": "Medium", "Mode": "Cycle earnings"},
    "AI Server Platform": {"Years": 3, "Cap": 1.60, "Confidence": "Medium", "Mode": "AI server growth"},
    "Thermal Solution": {"Years": 3, "Cap": 1.75, "Confidence": "Medium", "Mode": "Thermal growth"},
    "AI Platform": {"Years": 4, "Cap": 1.90, "Confidence": "Medium", "Mode": "AI edge/platform"},
    "AI Infrastructure": {"Years": 5, "Cap": 2.20, "Confidence": "Medium", "Mode": "AI compute infrastructure"},
    "Advanced Materials": {"Years": 5, "Cap": 2.50, "Confidence": "Low", "Mode": "AI material upgrade cycle"},
    "Intelligent Automation": {"Years": 6, "Cap": 2.80, "Confidence": "Low", "Mode": "AI robotics option value"},
    "Memory Cycle": {"Years": 4, "Cap": 3.00, "Confidence": "Low", "Mode": "Memory cycle forward pricing"},
}

def normalized_growth_rate(r):
    """
    Forward Growth Proxy：
    40% EPS Growth + 30% Revenue CAGR + 20% ROIC品質 + 10% FCF品質
    """
    eps_g = max(-10, min(60, r["EPS_Growth"])) / 100
    rev_g = max(-10, min(50, r["Revenue_CAGR"])) / 100
    roic_quality = max(0, min(40, r["ROIC"] - 8)) / 100
    fcf_quality = max(0, min(25, r["FCF_Margin"])) / 100
    g = eps_g * 0.40 + rev_g * 0.30 + roic_quality * 0.20 + fcf_quality * 0.10
    return max(-0.05, min(0.35, g))

def growth_horizon_multiplier(r):
    cfg = GROWTH_HORIZON[r["CID"]]
    g = normalized_growth_rate(r)
    years = cfg["Years"]
    raw = (1 + g) ** years
    capped = min(raw, cfg["Cap"])
    return round(capped, 3), round(g * 100, 1), years, cfg["Cap"], cfg["Confidence"], cfg["Mode"]

def safe_num(x):
    try:
        if x is None or pd.isna(x): return None
        return float(x)
    except Exception:
        return None

def get_row(df, names):
    if df is None or df.empty: return None
    idx = {str(i).lower(): i for i in df.index}
    for n in names:
        if n.lower() in idx:
            s = df.loc[idx[n.lower()]]
            if isinstance(s, pd.Series):
                for v in s:
                    val = safe_num(v)
                    if val is not None: return val
            return safe_num(s)
    return None

def cagr(vals):
    vals = [safe_num(v) for v in vals if safe_num(v) is not None and safe_num(v) > 0]
    if len(vals) < 2: return None
    newest, oldest, years = vals[0], vals[-1], len(vals)-1
    if oldest <= 0: return None
    return (newest/oldest)**(1/years)-1

@st.cache_data(ttl=1800)
def fetch_market_and_financials(symbol, fallback_price, fallback):
    data = dict(fallback)
    meta = {"Price Source":"fallback", "Financial Source":"fallback", "Data Completeness":0, "Notes":[]}
    price = fallback_price
    if yf is None:
        meta["Notes"].append("yfinance未安裝，使用備援資料。")
        return price, data, meta
    try:
        t = yf.Ticker(symbol)
        fast = getattr(t, "fast_info", {}) or {}
        p = fast.get("last_price") or fast.get("lastPrice")
        if p is None:
            hist = t.history(period="5d")
            if not hist.empty: p = float(hist["Close"].dropna().iloc[-1])
        if p and p > 0:
            price = round(float(p), 2)
            meta["Price Source"] = f"yfinance:{symbol}"
        try: info = t.info or {}
        except Exception: info = {}
        income, balance, cashflow = t.financials, t.balance_sheet, t.cashflow
        shares = safe_num(info.get("sharesOutstanding")) or safe_num(fast.get("shares"))
        eps = safe_num(info.get("trailingEps")); bvps = safe_num(info.get("bookValue"))
        roe_info = safe_num(info.get("returnOnEquity")); div_rate = safe_num(info.get("dividendRate"))
        revenue = get_row(income, ["Total Revenue", "Operating Revenue"])
        net_income = get_row(income, ["Net Income", "Net Income Common Stockholders"])
        ebit = get_row(income, ["EBIT", "Operating Income"])
        tax_exp = get_row(income, ["Tax Provision", "Income Tax Expense"])
        pretax = get_row(income, ["Pretax Income", "Income Before Tax"])
        equity = get_row(balance, ["Stockholders Equity", "Total Equity Gross Minority Interest", "Common Stock Equity"])
        debt = get_row(balance, ["Total Debt", "Long Term Debt", "Short Long Term Debt Total"])
        cash = get_row(balance, ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"])
        ocf = get_row(cashflow, ["Operating Cash Flow", "Total Cash From Operating Activities"])
        capex = get_row(cashflow, ["Capital Expenditure", "Capital Expenditures"])
        rev_cagr = eps_growth = None
        if income is not None and not income.empty:
            for nm in ["Total Revenue", "Operating Revenue"]:
                if nm in income.index:
                    rev_cagr = cagr(income.loc[nm].values); break
            for nm in ["Net Income", "Net Income Common Stockholders"]:
                if nm in income.index:
                    eps_growth = cagr(income.loc[nm].values); break
        if eps is None and net_income is not None and shares and shares > 0: eps = net_income/shares
        if bvps is None and equity is not None and shares and shares > 0: bvps = equity/shares
        roe = None
        if roe_info is not None: roe = roe_info*100 if abs(roe_info)<1 else roe_info
        elif net_income is not None and equity and equity > 0: roe = net_income/equity*100
        tax_rate = 0.2
        if tax_exp is not None and pretax and pretax > 0: tax_rate = max(0.05, min(0.35, tax_exp/pretax))
        invested = equity + (debt or 0) - (cash or 0) if equity is not None else None
        roic = ebit*(1-tax_rate)/invested*100 if ebit is not None and invested and invested > 0 else None
        fcf_margin = (ocf+capex)/revenue*100 if ocf is not None and capex is not None and revenue and revenue > 0 else None
        extracted = {"EPS":eps, "BVPS":bvps, "ROE":roe, "ROIC":roic, "FCF_Margin":fcf_margin, "Revenue_CAGR":rev_cagr*100 if rev_cagr is not None else None, "EPS_Growth":eps_growth*100 if eps_growth is not None else None, "Dividend":div_rate}
        real_count = 0
        for k,v in extracted.items():
            if v is not None and np.isfinite(v):
                data[k] = round(float(v), 2); real_count += 1
        meta["Data Completeness"] = round(real_count/len(extracted)*100, 1)
        meta["Financial Source"] = "yfinance + fallback" if real_count < len(extracted) else "yfinance"
        missing = [k for k,v in extracted.items() if v is None or not np.isfinite(v)]
        if missing: meta["Notes"].append("Fallback欄位：" + "、".join(missing))
    except Exception as e:
        meta["Notes"].append(f"抓取失敗：{e}")
    return price, data, meta

def dcf(r):
    g=max(-5,min(25,r["EPS_Growth"])); q=1+max(0,r["FCF_Margin"])*.008; pe=14+g*.35
    if r["Stage"]=="Leader": pe+=6
    elif r["Stage"]=="Growth": pe+=4
    elif r["Stage"]=="Stable": pe+=2
    return max(0,r["EPS"]*pe*q)
def fcff(r): return max(0,r["EPS"]*(13+max(-5,min(20,r["Revenue_CAGR"]))*0.25+max(0,r["FCF_Margin"])*0.18))
def fcfe(r): return max(0,r["EPS"]*(11+max(0,r["ROE"]-8)*0.35)*(1+min(.25,max(0,r["Dividend"]/max(r["EPS"],.01))*0.10)))
def eva(r): return max(0,r["BVPS"]*(1+(r["ROE"]-(10.5 if r["Stage"]=="Growth" else 9))*0.08))
def ebo(r): return max(0,r["BVPS"]+r["BVPS"]*((r["ROE"]-9.5)/100)*5+r["EPS"]*max(0,max(-3,min(15,r["EPS_Growth"])))*0.25)
def roic_value(r): return max(0,r["EPS"]*(16+max(0,r["ROIC"]-10)*0.30+max(0,r["FCF_Margin"])*0.12))
def cap_value(r):
    y=10 if r["Stage"]=="Leader" else 8 if r["Stage"]=="Growth" else 6
    if "AI" in r["CID"]: y+=2
    return max(0,r["EPS"]*(14+y*1.6))
def cycle_pe(r): return max(0,r["EPS"]*(7 if r["CID"]=="Shipping Cycle" else 18 if r["CID"]=="Memory Cycle" else 14)*(0.80+r["Industry_Health"]/100*0.45))
def ev_ebitda(r): return max(0,r["EPS"]*(6.5 if r["CID"]=="Shipping Cycle" else 9 if r["CID"]=="Memory Cycle" else 12)*1.12)
def asset_value(r): return max(0,r["BVPS"]*(.85 if r["CID"]=="Shipping Cycle" else 1.5 if r["CID"]=="Memory Cycle" else 1.7 if r["CID"]=="Financial Franchise" else 1))
def div_value(r):
    y=.038 if r["CID"]=="Telecom Infrastructure" else .045 if r["CID"]=="Financial Franchise" else .07 if r["CID"]=="Shipping Cycle" else .05
    return r["Dividend"]/y if r["Dividend"] > 0 else 0

def components(r):
    raw = {"DCF":dcf(r),"FCFF":fcff(r),"FCFE":fcfe(r),"EVA":eva(r),"EBO":ebo(r),"ROIC Premium":roic_value(r),"CAP":cap_value(r),"Cycle PE":cycle_pe(r),"EV/EBITDA":ev_ebitda(r),"Asset Value":asset_value(r),"PB Asset":asset_value(r),"Dividend":div_value(r)}
    cal = STRUCTURAL_CAL[r["CID"]]; out = {}
    for k,v in raw.items():
        f=cal["Base"]
        if k in ["DCF","FCFF","FCFE"]: f*=cal["Growth"]
        if k=="ROIC Premium": f*=cal["ROIC"]
        if k=="CAP": f*=cal["CAP"]
        out[k]=v*f
    return out

def valuation(r):
    comps=components(r); weights=WEIGHTS[r["CID"]]; base=sum(comps[k]*w for k,w in weights.items())
    if r["Stage"]=="Cycle": bear,bull=base*.70,base*1.45
    elif r["Stage"]=="Growth": bear,bull=base*.78,base*1.38
    elif r["Stage"]=="Leader": bear,bull=base*.82,base*1.30
    else: bear,bull=base*.85,base*1.18
    return round(bear,2),round(base,2),round(bull,2),comps

def gap_status(price,value):
    if not value or value<=0: return None,"N/A"
    gap=(price/value-1)*100; ag=abs(gap)
    status="Fair Zone" if ag<=15 else "Mild Divergence" if ag<=30 else "Strong Divergence" if ag<=50 else "Extreme Divergence"
    return round(gap,1),status

rows=[]; comp_rows=[]
progress = st.sidebar.empty()
for i,item in enumerate(BENCHMARK, start=1):
    progress.caption(f"載入資料 {i}/{len(BENCHMARK)}：{item['公司']}")
    price, fin, meta = fetch_market_and_financials(item["代號"], item["fallback_price"], item["fallback"])
    r = {**item, **fin, "現價":price}
    bear, fair, bull, comps = valuation(r)
    gap, stat = gap_status(price, fair)
    ghe_mult, forward_g, horizon_years, horizon_cap, ghe_conf, ghe_mode = growth_horizon_multiplier(r)
    exp_bear = round(bear * ghe_mult, 2)
    exp_fair = round(fair * ghe_mult, 2)
    exp_bull = round(bull * ghe_mult, 2)
    exp_gap, exp_stat = gap_status(price, exp_fair)
    fef = round(price / fair, 3) if fair and fair > 0 else None
    cal = STRUCTURAL_CAL[item["CID"]]
    rows.append({"公司":item["公司"],"代號":item["代號"],"CID":item["CID"],"Stage":item["Stage"],"現價":price,
                 "Bear":bear,"Fair Value":fair,"Bull":bull,"Gap%":gap,"Status":stat,
                 "GHE Multiplier":ghe_mult,"Forward Growth Proxy%":forward_g,"Horizon Years":horizon_years,"Horizon Cap":horizon_cap,
                 "Expected Bear":exp_bear,"Expected Fair":exp_fair,"Expected Bull":exp_bull,"Expected Gap%":exp_gap,"Expected Status":exp_stat,
                 "Market FEF":fef,"GHE Confidence":ghe_conf,"GHE Mode":ghe_mode,
                 "EPS":r["EPS"],"BVPS":r["BVPS"],"ROE":r["ROE"],"ROIC":r["ROIC"],"FCF_Margin":r["FCF_Margin"],"Revenue_CAGR":r["Revenue_CAGR"],"EPS_Growth":r["EPS_Growth"],"Dividend":r["Dividend"],
                 "Data Completeness":meta["Data Completeness"],"Price Source":meta["Price Source"],"Financial Source":meta["Financial Source"],
                 "Calibration Confidence":cal["Confidence"],"Calibration Status":cal["Status"],"Notes":"；".join(meta["Notes"])})
    for k,v in comps.items(): comp_rows.append({"公司":item["公司"],"CID":item["CID"],"模型":k,"模型值":round(v,2),"是否使用":"Yes" if k in WEIGHTS[item["CID"]] else "No","權重":WEIGHTS[item["CID"]].get(k,0)})
progress.empty()

df=pd.DataFrame(rows); component_df=pd.DataFrame(comp_rows)
cid_summary=df.groupby("CID").agg(公司數=("公司","count"),平均Gap=("Gap%","mean"),中位數Gap=("Gap%","median"),平均絕對Gap=("Gap%",lambda x:x.abs().mean()),Expected平均Gap=("Expected Gap%","mean"),Expected平均絕對Gap=("Expected Gap%",lambda x:x.abs().mean()),FEF中位數=("Market FEF","median"),GHE倍率中位數=("GHE Multiplier","median"),Gap標準差=("Gap%","std"),FairZone數=("Status",lambda x:int((x=="Fair Zone").sum())),ExpectedFairZone數=("Expected Status",lambda x:int((x=="Fair Zone").sum())),平均資料完整度=("Data Completeness","mean")).reset_index().round(2)
def cid_grade(row):
    if row["公司數"] < 3: return "待補樣本"
    if row["平均絕對Gap"] <= 20 and row["Gap標準差"] <= 25: return "A級：可暫時凍結"
    if row["平均絕對Gap"] <= 40: return "B級：觀察"
    return "C級：需研究"
cid_summary["CID成熟度"] = cid_summary.apply(cid_grade, axis=1)
summary=pd.DataFrame([
    {"項目":"樣本公司數","結果":len(df)},
    {"項目":"CID數","結果":df["CID"].nunique()},
    {"項目":"Intrinsic Fair Zone公司數","結果":int((df["Status"]=="Fair Zone").sum())},
    {"項目":"Expected Fair Zone公司數","結果":int((df["Expected Status"]=="Fair Zone").sum())},
    {"項目":"Intrinsic平均絕對Gap","結果":f"{round(df['Gap%'].abs().mean(),1)}%"},
    {"項目":"Expected平均絕對Gap","結果":f"{round(df['Expected Gap%'].abs().mean(),1)}%"},
    {"項目":"平均資料完整度","結果":f"{round(df['Data Completeness'].mean(),1)}%"},
    {"項目":"C級CID數","結果":int((cid_summary["CID成熟度"].str.startswith("C級")).sum())},
])

st.sidebar.header("V16.0 GHE 控制台")
page=st.sidebar.radio("功能",["V16 Overview","Dual Valuation","Growth Horizon Dashboard","CID Gap Analysis","CID Maturity","Financial Data","Company Detail","Model Components","Structural Calibration","Export JSON"])
selected=st.sidebar.selectbox("選擇公司",df["公司"].tolist())
st.sidebar.divider(); st.sidebar.metric("樣本公司",len(df)); st.sidebar.metric("Intrinsic Fair",int((df["Status"]=="Fair Zone").sum())); st.sidebar.metric("Expected Fair",int((df["Expected Status"]=="Fair Zone").sum())); st.sidebar.metric("Expected平均Gap",f"{round(df['Expected Gap%'].abs().mean(),1)}%")

if page=="V16 Overview":
    st.header("一、V16 Overview")
    st.write("V16保留Intrinsic估值，新增Growth Horizon Engine，測試市場是否正在折現不同CID的未來成長年限。")
    st.dataframe(summary,use_container_width=True)
    st.subheader("V16 雙軌估值總表")
    st.dataframe(df[["公司","代號","CID","現價","Fair Value","Gap%","Status","GHE Multiplier","Expected Fair","Expected Gap%","Expected Status","Market FEF","Data Completeness","Price Source","Financial Source"]],use_container_width=True)
elif page=="Dual Valuation":
    st.header("二、Dual Valuation")
    st.dataframe(df[["公司","CID","現價","Bear","Fair Value","Bull","Gap%","Status","Expected Bear","Expected Fair","Expected Bull","Expected Gap%","Expected Status"]],use_container_width=True)
    st.bar_chart(df.set_index("公司")[["Fair Value","Expected Fair","現價"]])
elif page=="Growth Horizon Dashboard":
    st.header("三、Growth Horizon Dashboard")
    st.write("各CID的Growth Horizon年限、GHE倍率與市場FEF比較。")
    ghe_table = pd.DataFrame([{"CID":cid, **vals} for cid, vals in GROWTH_HORIZON.items()])
    st.subheader("GHE設定表")
    st.dataframe(ghe_table, use_container_width=True)
    st.subheader("CID實測FEF與GHE倍率")
    st.dataframe(cid_summary[["CID","公司數","FEF中位數","GHE倍率中位數","平均絕對Gap","Expected平均絕對Gap","FairZone數","ExpectedFairZone數"]], use_container_width=True)
    st.bar_chart(cid_summary.set_index("CID")[["FEF中位數","GHE倍率中位數"]])

elif page=="CID Gap Analysis":
    st.header("三、CID Gap Analysis")
    st.write("用CID平均Gap與標準差判斷：問題是個股還是整個類股。")
    st.dataframe(cid_summary,use_container_width=True)
    st.bar_chart(cid_summary.set_index("CID")[["平均絕對Gap","Gap標準差"]])
elif page=="CID Maturity":
    st.header("四、CID Maturity")
    st.write("A級可暫時凍結；B級觀察；C級才進一步研究修正。")
    st.dataframe(cid_summary[["CID","公司數","平均絕對Gap","Gap標準差","FairZone數","CID成熟度"]],use_container_width=True)
elif page=="Financial Data":
    st.header("五、Financial Data")
    st.dataframe(df[["公司","EPS","BVPS","ROE","ROIC","FCF_Margin","Revenue_CAGR","EPS_Growth","Dividend","Data Completeness","Notes"]],use_container_width=True)
elif page=="Company Detail":
    st.header("六、Company Detail")
    row=df[df["公司"]==selected].iloc[0]; comps=component_df[component_df["公司"]==selected]
    c1,c2,c3,c4=st.columns(4); c1.metric("現價",f"{row['現價']:,.2f}"); c2.metric("Intrinsic Fair",f"{row['Fair Value']:,.2f}",f"{row['Gap%']}%"); c3.metric("Expected Fair",f"{row['Expected Fair']:,.2f}",f"{row['Expected Gap%']}%"); c4.metric("GHE倍率",row["GHE Multiplier"])
    st.dataframe(pd.DataFrame([{"項目":"CID","內容":row["CID"]},{"項目":"Stage","內容":row["Stage"]},{"項目":"Calibration Confidence","內容":row["Calibration Confidence"]},{"項目":"Calibration Status","內容":row["Calibration Status"]},{"項目":"Growth Horizon Years","內容":row["Horizon Years"]},{"項目":"Forward Growth Proxy%","內容":row["Forward Growth Proxy%"]},{"項目":"GHE Mode","內容":row["GHE Mode"]},{"項目":"Data Completeness","內容":row["Data Completeness"]},{"項目":"Price Source","內容":row["Price Source"]},{"項目":"Financial Source","內容":row["Financial Source"]},{"項目":"Notes","內容":row["Notes"]}]),use_container_width=True)
    st.subheader("使用模型"); used=comps[comps["是否使用"]=="Yes"]; st.dataframe(used,use_container_width=True); st.bar_chart(used.set_index("模型")["模型值"])
elif page=="Model Components":
    st.header("七、Model Components"); st.dataframe(component_df,use_container_width=True)
elif page=="Structural Calibration":
    st.header("八、Structural Calibration")
    st.dataframe(pd.DataFrame([{"CID":cid,**vals} for cid,vals in STRUCTURAL_CAL.items()]),use_container_width=True)
elif page=="Export JSON":
    st.header("九、Export JSON")
    export={"version":"V16.0 Growth Horizon Engine","updated_at":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"purpose":"Keep V15 intrinsic valuation and add Growth Horizon Engine to estimate market expected fair value.","valuation_results":df.to_dict(orient="records"),"cid_summary":cid_summary.to_dict(orient="records"),"components":component_df.to_dict(orient="records"),"structural_calibration":STRUCTURAL_CAL,"growth_horizon":GROWTH_HORIZON,"summary":summary.to_dict(orient="records")}
    st.code(json.dumps(export,ensure_ascii=False,indent=2),language="json")
