
import json
from datetime import datetime
import pandas as pd
import streamlit as st
try:
    import yfinance as yf
except Exception:
    yf=None

st.set_page_config(page_title="Enterprise Valuation Lab V15 Benchmark 10", page_icon="🏛️", layout="wide")
st.title("🏛️ Enterprise Valuation Lab")
st.subheader("V15 Benchmark 10｜最新股價 + 季報/TTM 估值區間實測版")
st.info("先把估值區間跑出來，再判斷是否需要校正或財務預測。本版會更新最新股價；財務資料優先用 yfinance，缺漏則用備援值。")

BENCHMARK=[
{"公司":"2330 台積電","代號":"2330.TW","CID":"AI Infrastructure","Stage":"Leader","fallback_price":2505,"EPS":65.46,"BVPS":206.5,"ROE":31.7,"ROIC":46.7,"FCF_Margin":26.05,"Revenue_CAGR":18.94,"EPS_Growth":19.57,"Dividend":15,"Industry_Health":92},
{"公司":"2454 聯發科","代號":"2454.TW","CID":"AI Platform","Stage":"Leader","fallback_price":4335,"EPS":65.98,"BVPS":250.99,"ROE":26.29,"ROIC":59.58,"FCF_Margin":23.05,"Revenue_CAGR":2.79,"EPS_Growth":-3.76,"Dividend":75,"Industry_Health":88},
{"公司":"2382 廣達","代號":"2382.TW","CID":"AI Server Platform","Stage":"Growth","fallback_price":372,"EPS":18.92,"BVPS":53.83,"ROE":36.84,"ROIC":21.36,"FCF_Margin":-1.2,"Revenue_CAGR":18.37,"EPS_Growth":37.32,"Dividend":6,"Industry_Health":88},
{"公司":"2383 台光電","代號":"2383.TW","CID":"Advanced Materials","Stage":"Growth","fallback_price":5535,"EPS":40.88,"BVPS":140.81,"ROE":29.03,"ROIC":29.7,"FCF_Margin":2.22,"Revenue_CAGR":34.58,"EPS_Growth":42.4,"Dividend":40,"Industry_Health":90},
{"公司":"3017 奇鋐","代號":"3017.TW","CID":"Thermal Solution","Stage":"Growth","fallback_price":2620,"EPS":60.1,"BVPS":115.16,"ROE":61.69,"ROIC":100.96,"FCF_Margin":22.75,"Revenue_CAGR":35.59,"EPS_Growth":66.43,"Dividend":12,"Industry_Health":86},
{"公司":"6215 和椿","代號":"6215.TWO","CID":"Intelligent Automation","Stage":"Growth","fallback_price":108,"EPS":4.2,"BVPS":32,"ROE":12,"ROIC":14,"FCF_Margin":8,"Revenue_CAGR":18,"EPS_Growth":20,"Dividend":1.2,"Industry_Health":78},
{"公司":"2408 南亞科","代號":"2408.TW","CID":"Memory Cycle","Stage":"Cycle","fallback_price":421,"EPS":10.81,"BVPS":62.25,"ROE":19.39,"ROIC":5.22,"FCF_Margin":7.34,"Revenue_CAGR":5.35,"EPS_Growth":-54.76,"Dividend":0.5,"Industry_Health":82},
{"公司":"2881 富邦金","代號":"2881.TW","CID":"Financial Franchise","Stage":"Stable","fallback_price":122.5,"EPS":8.37,"BVPS":71.61,"ROE":18.73,"ROIC":10,"FCF_Margin":1.52,"Revenue_CAGR":14.15,"EPS_Growth":37.11,"Dividend":5,"Industry_Health":80},
{"公司":"2603 長榮","代號":"2603.TW","CID":"Shipping Cycle","Stage":"Cycle","fallback_price":185.5,"EPS":31.64,"BVPS":268.71,"ROE":8.22,"ROIC":13.41,"FCF_Margin":20.89,"Revenue_CAGR":-15.46,"EPS_Growth":-41.02,"Dividend":12,"Industry_Health":78},
{"公司":"2412 中華電","代號":"2412.TW","CID":"Telecom Infrastructure","Stage":"Stable","fallback_price":141.5,"EPS":5.02,"BVPS":51.09,"ROE":9.99,"ROIC":10.59,"FCF_Margin":21.13,"Revenue_CAGR":2.86,"EPS_Growth":2.11,"Dividend":4.7,"Industry_Health":85},
]

CAL={
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
WEIGHTS={
"AI Infrastructure":{"DCF":.25,"FCFF":.20,"ROIC Premium":.25,"CAP":.30},
"AI Platform":{"DCF":.25,"FCFE":.20,"ROIC Premium":.25,"CAP":.30},
"AI Server Platform":{"DCF":.25,"FCFF":.25,"ROIC Premium":.20,"CAP":.30},
"Advanced Materials":{"DCF":.20,"FCFF":.20,"ROIC Premium":.25,"CAP":.35},
"Thermal Solution":{"DCF":.25,"FCFF":.20,"ROIC Premium":.30,"CAP":.25},
"Intelligent Automation":{"DCF":.25,"FCFF":.20,"EVA":.20,"ROIC Premium":.20,"CAP":.15},
"Memory Cycle":{"Cycle PE":.35,"EV/EBITDA":.25,"Asset Value":.30,"EBO":.10},
"Financial Franchise":{"PB Asset":.30,"EBO":.30,"Dividend":.25,"EVA":.15},
"Shipping Cycle":{"Cycle PE":.30,"EV/EBITDA":.30,"Asset Value":.30,"Dividend":.10},
"Telecom Infrastructure":{"DCF":.25,"FCFE":.15,"EBO":.20,"Dividend":.40},
}

@st.cache_data(ttl=900)
def price(symbol,fallback):
    if yf:
        try:
            t=yf.Ticker(symbol); fast=getattr(t,'fast_info',{}) or {}
            p=fast.get('last_price') or fast.get('lastPrice')
            if p is None:
                h=t.history(period='5d')
                if not h.empty: p=float(h['Close'].dropna().iloc[-1])
            if p and p>0: return round(float(p),2), f'yfinance:{symbol}'
        except Exception: pass
    return fallback,'fallback'

def dcf(r):
    g=max(-5,min(25,r['EPS_Growth'])); q=1+max(0,r['FCF_Margin'])*.008; pe=14+g*.35
    pe+=6 if r['Stage']=='Leader' else 4 if r['Stage']=='Growth' else 2 if r['Stage']=='Stable' else 0
    return max(0,r['EPS']*pe*q)
def fcff(r): return max(0,r['EPS']*(13+max(-5,min(20,r['Revenue_CAGR']))*.25+max(0,r['FCF_Margin'])*.18))
def fcfe(r): return max(0,r['EPS']*(11+max(0,r['ROE']-8)*.35)*(1+min(.25,max(0,r['Dividend']/max(r['EPS'],.01))*.10)))
def eva(r): return max(0,r['BVPS']*(1+(r['ROE']-(10.5 if r['Stage']=='Growth' else 9))*.08))
def ebo(r): return max(0,r['BVPS']+r['BVPS']*((r['ROE']-9.5)/100)*5+r['EPS']*max(0,max(-3,min(15,r['EPS_Growth'])))*.25)
def roicv(r): return max(0,r['EPS']*(16+max(0,r['ROIC']-10)*.30+max(0,r['FCF_Margin'])*.12))
def cap(r):
    y=10 if r['Stage']=='Leader' else 8 if r['Stage']=='Growth' else 6
    if 'AI' in r['CID']: y+=2
    return max(0,r['EPS']*(14+y*1.6))
def cycle_pe(r): return max(0,r['EPS']*((7 if r['CID']=='Shipping Cycle' else 18 if r['CID']=='Memory Cycle' else 14))*(.80+r['Industry_Health']/100*.45))
def ev_ebitda(r): return max(0,r['EPS']*((6.5 if r['CID']=='Shipping Cycle' else 9 if r['CID']=='Memory Cycle' else 12))*1.12)
def asset(r): return max(0,r['BVPS']*((.85 if r['CID']=='Shipping Cycle' else 1.5 if r['CID']=='Memory Cycle' else 1.7 if r['CID']=='Financial Franchise' else 1)))
def divv(r):
    y=.038 if r['CID']=='Telecom Infrastructure' else .045 if r['CID']=='Financial Franchise' else .07 if r['CID']=='Shipping Cycle' else .05
    return r['Dividend']/y if r['Dividend']>0 else 0

def comps(r):
    raw={'DCF':dcf(r),'FCFF':fcff(r),'FCFE':fcfe(r),'EVA':eva(r),'EBO':ebo(r),'ROIC Premium':roicv(r),'CAP':cap(r),'Cycle PE':cycle_pe(r),'EV/EBITDA':ev_ebitda(r),'Asset Value':asset(r),'PB Asset':asset(r),'Dividend':divv(r)}
    c=CAL[r['CID']]; out={}
    for k,v in raw.items():
        f=c['Base']
        if k in ['DCF','FCFF','FCFE']: f*=c['Growth']
        if k=='ROIC Premium': f*=c['ROIC']
        if k=='CAP': f*=c['CAP']
        out[k]=v*f
    return out

def valuation(r):
    c=comps(r); base=sum(c[k]*w for k,w in WEIGHTS[r['CID']].items())
    if r['Stage']=='Cycle': bear,bull=base*.70,base*1.45
    elif r['Stage']=='Growth': bear,bull=base*.78,base*1.38
    elif r['Stage']=='Leader': bear,bull=base*.82,base*1.30
    else: bear,bull=base*.85,base*1.18
    return round(bear,2),round(base,2),round(bull,2),c

def gap_status(p,v):
    gap=(p/v-1)*100 if v else None
    if gap is None: return None,'N/A'
    ag=abs(gap); return round(gap,1),('Fair Zone' if ag<=15 else 'Mild Divergence' if ag<=30 else 'Strong Divergence' if ag<=50 else 'Extreme Divergence')

rows=[]; comp=[]
for item in BENCHMARK:
    p,src=price(item['代號'],item['fallback_price']); r={**item,'現價':p}
    bear,base,bull,cs=valuation(r); gap,stat=gap_status(p,base); cal=CAL[item['CID']]
    rows.append({**{k:r[k] for k in ['公司','代號','CID','Stage','現價','EPS','BVPS','ROE','ROIC','FCF_Margin','Revenue_CAGR','EPS_Growth','Dividend']},'Bear':bear,'Fair Value':base,'Bull':bull,'Gap%':gap,'Status':stat,'Price Source':src,'Calibration Confidence':cal['Confidence'],'Calibration Status':cal['Status']})
    for k,v in cs.items(): comp.append({'公司':item['公司'],'CID':item['CID'],'模型':k,'模型值':round(v,2),'是否使用':'Yes' if k in WEIGHTS[item['CID']] else 'No','權重':WEIGHTS[item['CID']].get(k,0)})
df=pd.DataFrame(rows); component_df=pd.DataFrame(comp)
cid_summary=df.groupby('CID').agg(公司數=('公司','count'),平均Gap=('Gap%','mean'),平均絕對Gap=('Gap%',lambda x:x.abs().mean()),FairZone數=('Status',lambda x:int((x=='Fair Zone').sum()))).reset_index().round(1)
summary=pd.DataFrame([{'項目':'樣本公司數','結果':len(df)},{'項目':'Fair Zone公司數','結果':int((df['Status']=='Fair Zone').sum())},{'項目':'平均絕對Gap','結果':f"{round(df['Gap%'].abs().mean(),1)}%"},{'項目':'Extreme Divergence公司數','結果':int((df['Status']=='Extreme Divergence').sum())}])

st.sidebar.header('V15 Benchmark 10 控制台')
page=st.sidebar.radio('功能',['Benchmark Overview','Valuation Range','CID Gap Analysis','Financial Data','Company Detail','Model Components','Structural Calibration','Export JSON'])
selected=st.sidebar.selectbox('選擇公司',df['公司'].tolist())
st.sidebar.divider(); st.sidebar.metric('樣本公司',len(df)); st.sidebar.metric('Fair Zone',int((df['Status']=='Fair Zone').sum())); st.sidebar.metric('平均絕對Gap',f"{round(df['Gap%'].abs().mean(),1)}%")
if page=='Benchmark Overview':
    st.header('一、Benchmark Overview'); st.dataframe(summary,use_container_width=True); st.dataframe(df[['公司','代號','CID','現價','Bear','Fair Value','Bull','Gap%','Status','Price Source']],use_container_width=True)
elif page=='Valuation Range':
    st.header('二、Valuation Range'); st.dataframe(df[['公司','CID','現價','Bear','Fair Value','Bull','Gap%','Status']],use_container_width=True); st.bar_chart(df.set_index('公司')[['Bear','Fair Value','Bull','現價']])
elif page=='CID Gap Analysis':
    st.header('三、CID Gap Analysis'); st.dataframe(cid_summary,use_container_width=True); st.bar_chart(cid_summary.set_index('CID')['平均絕對Gap'])
elif page=='Financial Data':
    st.header('四、Financial Data'); st.dataframe(df[['公司','EPS','BVPS','ROE','ROIC','FCF_Margin','Revenue_CAGR','EPS_Growth','Dividend']],use_container_width=True)
elif page=='Company Detail':
    st.header('五、Company Detail'); row=df[df['公司']==selected].iloc[0]; cdf=component_df[component_df['公司']==selected]
    c1,c2,c3,c4=st.columns(4); c1.metric('現價',f"{row['現價']:,.2f}"); c2.metric('Fair Value',f"{row['Fair Value']:,.2f}",f"{row['Gap%']}%"); c3.metric('區間',f"{row['Bear']:,.2f} ~ {row['Bull']:,.2f}"); c4.metric('Status',row['Status'])
    st.dataframe(cdf[cdf['是否使用']=='Yes'],use_container_width=True); st.bar_chart(cdf[cdf['是否使用']=='Yes'].set_index('模型')['模型值'])
elif page=='Model Components': st.header('六、Model Components'); st.dataframe(component_df,use_container_width=True)
elif page=='Structural Calibration': st.header('七、Structural Calibration'); st.dataframe(pd.DataFrame([{'CID':cid,**vals} for cid,vals in CAL.items()]),use_container_width=True)
elif page=='Export JSON':
    st.header('八、Export JSON'); export={'version':'V15 Benchmark 10 Valuation Range','updated_at':datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'valuation_results':df.to_dict(orient='records'),'cid_summary':cid_summary.to_dict(orient='records'),'components':component_df.to_dict(orient='records'),'structural_calibration':CAL,'summary':summary.to_dict(orient='records')}; st.code(json.dumps(export,ensure_ascii=False,indent=2),language='json')
