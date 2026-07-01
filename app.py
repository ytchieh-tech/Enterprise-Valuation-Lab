import json
from datetime import datetime
import numpy as np
import pandas as pd
import streamlit as st

try:
    import yfinance as yf
except Exception:
    yf = None

st.set_page_config(page_title="Enterprise Valuation Lab V14.1", page_icon="🏛️", layout="wide")
st.title("🏛️ Enterprise Valuation Lab")
st.subheader("V14.1｜Real Financial Engine 真實財報引擎")
st.info("V14.1 將 V14.0 的示意財務數字改成 Real Financial Data Layer。系統會優先從 yfinance 抓取財報資料；若欄位不足，才使用 fallback 備援值，並顯示資料完整度。")

COMPANIES = [
    {"公司":"2330 台積電","代號":"2330.TW","fallback_price":2370,"CID":"AI Infrastructure","Stage":"Leader","Industry_Health":92,"fallback":{"EPS":85,"BVPS":220,"ROE":31,"ROIC":30,"FCF_Margin":22,"Revenue_CAGR":18,"EPS_Growth":22,"Dividend":15}},
    {"公司":"2454 聯發科","代號":"2454.TW","fallback_price":4335,"CID":"AI Platform","Stage":"Leader","Industry_Health":88,"fallback":{"EPS":125,"BVPS":520,"ROE":25,"ROIC":24,"FCF_Margin":20,"Revenue_CAGR":15,"EPS_Growth":18,"Dividend":75}},
    {"公司":"2383 台光電","代號":"2383.TW","fallback_price":5535,"CID":"Advanced Materials","Stage":"Growth","Industry_Health":90,"fallback":{"EPS":135,"BVPS":430,"ROE":32,"ROIC":30,"FCF_Margin":18,"Revenue_CAGR":28,"EPS_Growth":35,"Dividend":40}},
    {"公司":"2382 廣達","代號":"2382.TW","fallback_price":310,"CID":"AI Server Platform","Stage":"Growth","Industry_Health":88,"fallback":{"EPS":18,"BVPS":80,"ROE":22,"ROIC":18,"FCF_Margin":8,"Revenue_CAGR":22,"EPS_Growth":25,"Dividend":6}},
    {"公司":"3017 奇鋐","代號":"3017.TW","fallback_price":980,"CID":"Thermal Solution","Stage":"Growth","Industry_Health":86,"fallback":{"EPS":45,"BVPS":150,"ROE":28,"ROIC":24,"FCF_Margin":13,"Revenue_CAGR":25,"EPS_Growth":30,"Dividend":12}},
    {"公司":"6215 和椿","代號":"6215.TWO","fallback_price":108,"CID":"Intelligent Automation","Stage":"Growth","Industry_Health":78,"fallback":{"EPS":4.2,"BVPS":32,"ROE":12,"ROIC":14,"FCF_Margin":8,"Revenue_CAGR":18,"EPS_Growth":20,"Dividend":1.2}},
    {"公司":"2408 南亞科","代號":"2408.TW","fallback_price":95,"CID":"Memory Cycle","Stage":"Cycle","Industry_Health":82,"fallback":{"EPS":3.8,"BVPS":58,"ROE":8,"ROIC":7,"FCF_Margin":-3,"Revenue_CAGR":35,"EPS_Growth":45,"Dividend":0.5}},
    {"公司":"2881 富邦金","代號":"2881.TW","fallback_price":128.5,"CID":"Financial Franchise","Stage":"Stable","Industry_Health":80,"fallback":{"EPS":9.5,"BVPS":85,"ROE":14,"ROIC":10,"FCF_Margin":8,"Revenue_CAGR":8,"EPS_Growth":12,"Dividend":5.0}},
    {"公司":"2603 長榮","代號":"2603.TW","fallback_price":230,"CID":"Shipping Cycle","Stage":"Cycle","Industry_Health":78,"fallback":{"EPS":18,"BVPS":175,"ROE":20,"ROIC":18,"FCF_Margin":15,"Revenue_CAGR":-8,"EPS_Growth":-15,"Dividend":12}},
    {"公司":"2412 中華電","代號":"2412.TW","fallback_price":130,"CID":"Telecom Infrastructure","Stage":"Stable","Industry_Health":85,"fallback":{"EPS":4.8,"BVPS":42,"ROE":10,"ROIC":10,"FCF_Margin":16,"Revenue_CAGR":3,"EPS_Growth":4,"Dividend":4.7}},
]


def safe_number(x):
    try:
        if x is None or pd.isna(x): return None
        return float(x)
    except Exception:
        return None


def get_row_value(df, possible_names):
    if df is None or df.empty: return None
    idx = {str(i).lower(): i for i in df.index}
    for name in possible_names:
        if name.lower() in idx:
            row = df.loc[idx[name.lower()]]
            if isinstance(row, pd.Series):
                for v in row:
                    n = safe_number(v)
                    if n is not None: return n
            return safe_number(row)
    return None


def cagr_from_series(values):
    vals = [safe_number(v) for v in values if safe_number(v) is not None and safe_number(v) > 0]
    if len(vals) < 2: return None
    oldest, newest, years = vals[-1], vals[0], len(vals)-1
    if oldest <= 0 or years <= 0: return None
    return (newest / oldest) ** (1 / years) - 1


@st.cache_data(ttl=1800)
def fetch_real_financials(symbol, fallback_price, fallback):
    result = {"price": fallback_price, "price_source":"fallback 備援價", "financial_source":"fallback", "fields_from_real":0, "fields_total":8, "notes":[]}
    data = dict(fallback)
    if yf is None:
        result.update(data); result["Data_Completeness"] = 0; result["notes"].append("yfinance 未安裝，使用 fallback。")
        return result
    try:
        ticker = yf.Ticker(symbol)
        fast = getattr(ticker, "fast_info", {}) or {}
        price = fast.get("last_price") or fast.get("lastPrice")
        if price is None:
            hist = ticker.history(period="5d", interval="1d")
            if not hist.empty: price = float(hist["Close"].dropna().iloc[-1])
        if price and price > 0:
            result["price"] = round(float(price), 2); result["price_source"] = f"yfinance：{symbol}"
        try: info = ticker.info or {}
        except Exception: info = {}
        income, balance, cashflow = ticker.financials, ticker.balance_sheet, ticker.cashflow
        shares = safe_number(info.get("sharesOutstanding")) or safe_number(fast.get("shares"))
        trailing_eps = safe_number(info.get("trailingEps"))
        book_value = safe_number(info.get("bookValue"))
        roe_info = safe_number(info.get("returnOnEquity"))
        dividend_rate = safe_number(info.get("dividendRate"))
        total_revenue = get_row_value(income, ["Total Revenue", "Operating Revenue"])
        net_income = get_row_value(income, ["Net Income", "Net Income Common Stockholders"])
        ebit = get_row_value(income, ["EBIT", "Operating Income"])
        tax_expense = get_row_value(income, ["Tax Provision", "Income Tax Expense"])
        pretax_income = get_row_value(income, ["Pretax Income", "Income Before Tax"])
        equity = get_row_value(balance, ["Stockholders Equity", "Total Equity Gross Minority Interest", "Common Stock Equity"])
        total_debt = get_row_value(balance, ["Total Debt", "Long Term Debt", "Short Long Term Debt Total"])
        cash = get_row_value(balance, ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"])
        operating_cf = get_row_value(cashflow, ["Operating Cash Flow", "Total Cash From Operating Activities"])
        capex = get_row_value(cashflow, ["Capital Expenditure", "Capital Expenditures"])
        revenue_cagr = None; eps_growth = None
        if income is not None and not income.empty:
            for nm in ["Total Revenue", "Operating Revenue"]:
                if nm in income.index:
                    revenue_cagr = cagr_from_series(income.loc[nm].values); break
            for nm in ["Net Income", "Net Income Common Stockholders"]:
                if nm in income.index:
                    eps_growth = cagr_from_series(income.loc[nm].values); break
        eps = trailing_eps
        if eps is None and net_income is not None and shares and shares > 0: eps = net_income / shares
        bvps = book_value
        if bvps is None and equity is not None and shares and shares > 0: bvps = equity / shares
        roe = roe_info * 100 if roe_info is not None and abs(roe_info) < 1 else roe_info
        if roe is None and net_income is not None and equity and equity > 0: roe = net_income / equity * 100
        tax_rate = 0.20
        if tax_expense is not None and pretax_income and pretax_income > 0: tax_rate = min(0.35, max(0.05, tax_expense / pretax_income))
        invested = equity + (total_debt or 0) - (cash or 0) if equity is not None else None
        roic = None
        if ebit is not None and invested and invested > 0: roic = ebit * (1-tax_rate) / invested * 100
        fcf_margin = None
        if operating_cf is not None and capex is not None and total_revenue and total_revenue > 0:
            fcf_margin = (operating_cf + capex) / total_revenue * 100
        extracted = {"EPS":eps, "BVPS":bvps, "ROE":roe, "ROIC":roic, "FCF_Margin":fcf_margin, "Revenue_CAGR":revenue_cagr*100 if revenue_cagr is not None else None, "EPS_Growth":eps_growth*100 if eps_growth is not None else None, "Dividend":dividend_rate}
        real_count = 0
        for k, v in extracted.items():
            if v is not None and np.isfinite(v):
                data[k] = round(float(v), 2); real_count += 1
        result["fields_from_real"] = real_count
        result["financial_source"] = "yfinance 財報" if real_count == result["fields_total"] else "yfinance 財報 + fallback 混合"
        result["Data_Completeness"] = round(real_count/result["fields_total"]*100, 1)
        missing = [k for k, v in extracted.items() if v is None or not np.isfinite(v)]
        if missing: result["notes"].append("缺少欄位使用 fallback：" + "、".join(missing))
    except Exception as e:
        result["Data_Completeness"] = 0; result["notes"].append(f"財報抓取失敗：{e}")
    result.update(data)
    return result


def industry_multiplier(health): return round(0.75 + (health / 100) * 0.50, 3)
def dcf_value(eps, growth, stage): return max(0, eps * (12 + min(20, max(-10, growth)*0.45) + (4 if stage in ["Growth","Leader"] else 1.6)))
def roic_premium_value(eps, roic, fcf): return max(0, eps * 18 * (1 + max(0, roic-10)*0.025 + max(0, fcf)*0.01))
def cap_premium_value(eps, stage, cid): return max(0, eps * (18 + (8 if stage=="Leader" else 0) + (5 if "AI" in cid else 0) + (3 if "Infrastructure" in cid else 0)))
def vdf_premium_value(eps, growth, health): return max(0, eps * (16 + min(22, max(-10, growth)*0.55) + (health-50)*0.08))
def pb_roe_value(bvps, roe): return max(0, bvps * (0.7 + max(0, roe)*0.055))
def residual_income_value(bvps, roe, coe=9): return max(0, bvps * (1 + max(-5, roe-coe)*0.08))
def dividend_yield_value(dividend, target): return dividend / target if target > 0 and dividend > 0 else 0
def cycle_pe_value(eps, cycle, base_pe): return max(0, eps * base_pe * (0.75 + cycle/100*0.55))
def ev_ebitda_proxy(eps, mult): return max(0, eps * mult * 1.15)
def asset_value(bvps, stage, cid): return max(0, bvps * (1 + (0.15 if stage=="Cycle" else 0) + (0.15 if "Shipping" in cid else 0) + (0.05 if "Memory" in cid else 0)))

def model_selector(cid, stage):
    if cid == "AI Infrastructure": return {"主模型":"DCF + ROIC + CAP", "權重":{"DCF":.50,"ROIC Premium":.30,"CAP Premium":.20}}
    if cid in ["AI Platform","Advanced Materials","AI Server Platform","Thermal Solution"]: return {"主模型":"VDF + DCF + ROIC", "權重":{"VDF Premium":.45,"DCF":.35,"ROIC Premium":.20}}
    if cid == "Intelligent Automation": return {"主模型":"Automation Blend", "權重":{"VDF Premium":.40,"DCF":.35,"PB-ROE":.25}}
    if cid == "Memory Cycle": return {"主模型":"Cycle PE + PB + Asset", "權重":{"Cycle PE":.45,"PB-ROE":.25,"Asset Value":.30}}
    if cid == "Financial Franchise": return {"主模型":"PB-ROE + RI + Dividend", "權重":{"PB-ROE":.50,"Residual Income":.30,"Dividend Yield":.20}}
    if cid == "Shipping Cycle": return {"主模型":"Cycle PE + EV/EBITDA + Asset", "權重":{"Cycle PE":.40,"EV/EBITDA":.40,"Asset Value":.20}}
    if cid == "Telecom Infrastructure": return {"主模型":"DCF + Dividend + RI", "權重":{"DCF":.40,"Dividend Yield":.35,"Residual Income":.25}}
    return {"主模型":"Hybrid", "權重":{"DCF":.50,"PB-ROE":.30,"VDF Premium":.20}}

def default_base_pe(cid):
    if "Memory" in cid: return 22
    if "Shipping" in cid: return 8
    if "Financial" in cid: return 13
    if "Telecom" in cid: return 25
    if "AI" in cid or "Advanced" in cid: return 28
    return 20

def default_ev_ebitda(cid):
    if "Shipping" in cid: return 6
    if "Memory" in cid: return 9
    if "Telecom" in cid: return 12
    return 15

def valuation_components(row):
    comps = {
        "DCF": dcf_value(row["EPS"], row["EPS_Growth"], row["Stage"]),
        "ROIC Premium": roic_premium_value(row["EPS"], row["ROIC"], row["FCF_Margin"]),
        "CAP Premium": cap_premium_value(row["EPS"], row["Stage"], row["CID"]),
        "VDF Premium": vdf_premium_value(row["EPS"], row["EPS_Growth"], row["Industry_Health"]),
        "PB-ROE": pb_roe_value(row["BVPS"], row["ROE"]),
        "Residual Income": residual_income_value(row["BVPS"], row["ROE"]),
        "Dividend Yield": dividend_yield_value(row["Dividend"], .04 if row["Stage"]=="Stable" else .05),
        "Cycle PE": cycle_pe_value(row["EPS"], row["Cycle"], default_base_pe(row["CID"])),
        "EV/EBITDA": ev_ebitda_proxy(row["EPS"], default_ev_ebitda(row["CID"])),
        "Asset Value": asset_value(row["BVPS"], row["Stage"], row["CID"]),
    }
    return {k: round(v, 2) for k, v in comps.items()}

def final_valuation(row):
    selector = model_selector(row["CID"], row["Stage"]); comps = valuation_components(row); weights = selector["權重"]
    base0 = sum(comps[k]*w for k, w in weights.items()); mult = industry_multiplier(row["Industry_Health"]); base = base0 * mult
    if row["Stage"] == "Cycle": bear, bull = .70, 1.45
    elif row["Stage"] == "Growth": bear, bull = .78, 1.35
    elif row["Stage"] == "Leader": bear, bull = .82, 1.28
    else: bear, bull = .85, 1.18
    return {"Model Family":selector["主模型"], "Model Weights":" / ".join([f"{k}:{int(v*100)}%" for k,v in weights.items()]), "Base Value Before Industry":round(base0,2), "Industry Multiplier":mult, "Bear":round(base*bear,2), "Base":round(base,2), "Bull":round(base*bull,2), "Components":comps}

rows, financial_rows, component_rows = [], [], []
for c in COMPANIES:
    fin = fetch_real_financials(c["代號"], c["fallback_price"], c["fallback"])
    row = {**c, **fin}; row["Cycle"] = 92 if row["Stage"]=="Cycle" else 35 if row["Stage"]=="Stable" else 58
    val = final_valuation(row); price = fin["price"]
    upside = (val["Base"]/price - 1)*100 if price and price > 0 else None
    status = "合理偏低" if upside is not None and upside > 15 else "合理偏高" if upside is not None and upside < -15 else "合理區間"
    rows.append({"公司":c["公司"],"代號":c["代號"],"現價":price,"CID":c["CID"],"Stage":c["Stage"],"EPS":row["EPS"],"BVPS":row["BVPS"],"ROE":row["ROE"],"ROIC":row["ROIC"],"FCF_Margin":row["FCF_Margin"],"Revenue_CAGR":row["Revenue_CAGR"],"EPS_Growth":row["EPS_Growth"],"Dividend":row["Dividend"],"Industry_Health":c["Industry_Health"],"Data_Completeness":fin["Data_Completeness"],"Financial Source":fin["financial_source"],"Price Source":fin["price_source"],"Model Family":val["Model Family"],"Model Weights":val["Model Weights"],"Base Value Before Industry":val["Base Value Before Industry"],"Industry Multiplier":val["Industry Multiplier"],"Bear":val["Bear"],"Base":val["Base"],"Bull":val["Bull"],"Upside%":round(upside,1) if upside is not None else None,"價格判斷":status,"Notes":"；".join(fin["notes"])})
    for k in ["EPS","BVPS","ROE","ROIC","FCF_Margin","Revenue_CAGR","EPS_Growth","Dividend"]:
        financial_rows.append({"公司":c["公司"],"財務欄位":k,"數值":row[k],"資料來源":fin["financial_source"]})
    for k, v in val["Components"].items():
        component_rows.append({"公司":c["公司"],"估值模型":k,"模型估值":v,"CID":c["CID"],"Stage":c["Stage"]})

df = pd.DataFrame(rows); financial_df = pd.DataFrame(financial_rows); component_df = pd.DataFrame(component_rows)
summary = pd.DataFrame([
    {"項目":"樣本公司數","結果":len(df)},
    {"項目":"平均Data Completeness","結果":f"{round(df['Data_Completeness'].mean(),1)}%"},
    {"項目":"平均Industry Health","結果":f"{round(df['Industry_Health'].mean(),1)}%"},
    {"項目":"平均Industry Multiplier","結果":round(df["Industry Multiplier"].mean(),3)},
    {"項目":"平均Upside","結果":f"{round(df['Upside%'].mean(),1)}%"},
    {"項目":"合理偏低公司數","結果":int((df["價格判斷"]=="合理偏低").sum())},
    {"項目":"合理偏高公司數","結果":int((df["價格判斷"]=="合理偏高").sum())},
])

st.sidebar.header("V14.1 Real Financial Engine 控制台")
page = st.sidebar.radio("功能", ["Real Financial Overview", "Financial Data Layer", "Valuation Results", "Company Financial Card", "Model Components", "Data Quality Monitor", "Export JSON"])
selected_company = st.sidebar.selectbox("選擇公司", df["公司"].tolist())
st.sidebar.divider(); st.sidebar.metric("樣本公司", len(df)); st.sidebar.metric("平均資料完整度", f"{round(df['Data_Completeness'].mean(),1)}%"); st.sidebar.metric("平均Upside", f"{round(df['Upside%'].mean(),1)}%")

if page == "Real Financial Overview":
    st.header("一、Real Financial Overview"); st.write("V14.1 以真實財報資料為優先，fallback 僅作欄位缺漏時的備援。")
    st.dataframe(summary, use_container_width=True)
    cols = ["公司","代號","現價","CID","Stage","EPS","BVPS","ROE","ROIC","FCF_Margin","Revenue_CAGR","EPS_Growth","Data_Completeness","Financial Source","Model Family","Bear","Base","Bull","Upside%","價格判斷"]
    st.subheader("估值總表"); st.dataframe(df[cols], use_container_width=True)
elif page == "Financial Data Layer":
    st.header("二、Financial Data Layer"); st.write("所有估值模型共用的標準化財務資料層。"); st.dataframe(financial_df, use_container_width=True)
elif page == "Valuation Results":
    st.header("三、Valuation Results"); st.write("CID → Stage → Model Selector → Real Financial Valuation")
    cols = ["公司","CID","Stage","Model Family","Model Weights","Base Value Before Industry","Industry Multiplier","Bear","Base","Bull","Upside%"]
    st.dataframe(df[cols], use_container_width=True); st.bar_chart(df.set_index("公司")["Upside%"])
elif page == "Company Financial Card":
    st.header("四、Company Financial Card"); row = df[df["公司"]==selected_company].iloc[0]
    comps = component_df[component_df["公司"]==selected_company]; fdata = financial_df[financial_df["公司"]==selected_company]
    c1,c2,c3,c4 = st.columns(4); c1.metric("現價", f"{row['現價']:,.2f}"); c2.metric("Base合理價", f"{row['Base']:,.2f}", f"{row['Upside%']}%"); c3.metric("資料完整度", f"{row['Data_Completeness']}%"); c4.metric("價格判斷", row["價格判斷"])
    card = pd.DataFrame([{"項目":"CID","內容":row["CID"]},{"項目":"Stage","內容":row["Stage"]},{"項目":"Model Family","內容":row["Model Family"]},{"項目":"Model Weights","內容":row["Model Weights"]},{"項目":"Financial Source","內容":row["Financial Source"]},{"項目":"Notes","內容":row["Notes"]}])
    st.subheader("公司身份與模型"); st.dataframe(card, use_container_width=True)
    st.subheader("標準化財務欄位"); st.dataframe(fdata, use_container_width=True)
    st.subheader("估值模型拆解"); st.dataframe(comps, use_container_width=True); st.bar_chart(comps.set_index("估值模型")["模型估值"])
elif page == "Model Components":
    st.header("五、Model Components"); st.dataframe(component_df, use_container_width=True)
elif page == "Data Quality Monitor":
    st.header("六、Data Quality Monitor"); st.write("資料完整度越低，代表估值結果越依賴 fallback，需要人工檢查。")
    q = df[["公司","Data_Completeness","Financial Source","Notes"]].sort_values("Data_Completeness")
    st.dataframe(q, use_container_width=True); st.bar_chart(df.set_index("公司")["Data_Completeness"])
elif page == "Export JSON":
    st.header("七、Export JSON")
    export = {"version":"V14.1 Real Financial Engine","updated_at":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"purpose":"Real financial data layer connected to V14 valuation core.","valuation_results":df.to_dict(orient="records"),"financial_data_layer":financial_df.to_dict(orient="records"),"valuation_components":component_df.to_dict(orient="records"),"summary":summary.to_dict(orient="records")}
    st.code(json.dumps(export, ensure_ascii=False, indent=2), language="json")
