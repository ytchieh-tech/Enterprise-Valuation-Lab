import json
from datetime import datetime
import pandas as pd
import streamlit as st
try:
    import yfinance as yf
except Exception:
    yf = None

st.set_page_config(page_title='Enterprise Valuation Lab V12.9', page_icon='🏛️', layout='wide')
st.title('🏛️ Enterprise Valuation Lab')
st.subheader('V12.9｜CID Profile Engine')
st.info('V12.9 將 Identity Confidence、Identity Coherence、Identity Drift 拆開並列，不再硬壓成單一分數。')

@st.cache_data(ttl=900)
def fetch_price(symbol, fallback=None):
    candidates=[symbol]
    if symbol.endswith('.TW'): candidates.append(symbol.split('.')[0]+'.TWO')
    if symbol.endswith('.TWO'): candidates.append(symbol.split('.')[0]+'.TW')
    if yf:
        for tkr in candidates:
            try:
                t=yf.Ticker(tkr); fast=getattr(t,'fast_info',{}) or {}
                p=fast.get('last_price') or fast.get('lastPrice')
                if p is None:
                    h=t.history(period='5d', interval='1d')
                    if not h.empty: p=float(h['Close'].dropna().iloc[-1])
                if p and p>0: return float(p), f'yfinance：{tkr}'
            except Exception: pass
    return fallback, 'fallback 備援價'

IDENTITY_TREE={
 'AI Infrastructure Family':['AI Infrastructure','Compute Infrastructure','AI Server Platform','Cloud Infrastructure','AI Infrastructure Material','Thermal Solution'],
 'Semiconductor Family':['Semiconductor','Foundry','Advanced Manufacturing','Advanced Packaging','AI Platform','Edge AI','Mobile SoC'],
 'Advanced Materials Family':['Advanced Materials','PCB/CCL','AI Infrastructure Material'],
 'Automation Family':['Intelligent Automation','Robot Integrator','Robot Component','Industrial Equipment','Automation'],
 'Memory Cycle Family':['Memory Cycle','Super Cycle','Specialty Memory','Commodity Tech'],
 'Financial Family':['Financial Franchise','Insurance Holding','Banking Holding'],
 'Traditional Family':['Traditional Industry','ODM','Notebook ODM','Server ODM','Industrial Component'],
 'Growth Family':['Growth Re-rating','Structural Compounder']}
I2T={i:t for t,ids in IDENTITY_TREE.items() for i in ids}
def tree_of(i): return I2T.get(i,'Other Family')
REL={('AI Infrastructure','Semiconductor'):90,('AI Infrastructure','Foundry'):92,('AI Infrastructure','Advanced Manufacturing'):95,('AI Server Platform','Cloud Infrastructure'):88,('AI Server Platform','ODM'):70,('Advanced Materials','PCB/CCL'):92,('Advanced Materials','AI Infrastructure Material'):95,('Advanced Materials','Memory Cycle'):35,('AI Platform','Semiconductor'):85,('AI Platform','Edge AI'):92,('Intelligent Automation','Robot Integrator'):92,('Intelligent Automation','Robot Component'):88,('Robot Component','Industrial Equipment'):82,('Memory Cycle','Super Cycle'):92,('Memory Cycle','Specialty Memory'):88,('Financial Franchise','Insurance Holding'):90,('Financial Franchise','Banking Holding'):90,('ODM','Notebook ODM'):88,('Cloud Infrastructure','ODM'):65,('Structural Compounder','AI Infrastructure'):85,('Structural Compounder','Advanced Materials'):88}
def rel(a,b):
    if a==b: return 100
    if (a,b) in REL: return REL[(a,b)]
    if (b,a) in REL: return REL[(b,a)]
    return 78 if tree_of(a)==tree_of(b) else 42

def norm(raw):
    total=sum(max(0,v) for v in raw.values())
    if total<=0: return {}
    out={k:round(max(0,v)/total*100,1) for k,v in raw.items()}
    diff=round(100-sum(out.values()),1)
    if out and abs(diff)>=.1: out[max(out,key=out.get)]=round(out[max(out,key=out.get)]+diff,1)
    return dict(sorted(out.items(),key=lambda x:x[1],reverse=True))
def tree_scores(ids):
    raw={}
    for i,s in ids.items(): raw[tree_of(i)]=raw.get(tree_of(i),0)+s
    return dict(sorted(raw.items(),key=lambda x:x[1],reverse=True))
def concentration(scores):
    v=list(scores.values());
    if not v: return 0
    top=v[0]; second=v[1] if len(v)>1 else 0; third=v[2] if len(v)>2 else 0
    return round(max(0,min(100,top*.75+(top-second)*.45-third*.15)),1)
def coherence(ids):
    items=list(ids.items())[:5]
    if len(items)<=1: return 90
    sw=tw=0
    for i in range(len(items)):
        for j in range(i+1,len(items)):
            a,wa=items[i]; b,wb=items[j]; w=wa*wb
            sw+=rel(a,b)*w; tw+=w
    return round(sw/tw,1) if tw else 60
def drift_score(c):
    d=c.get('identity_drift',{})
    if not d: return 60,'暫無歷史'
    yrs=sorted(d); first=d[yrs[0]]; last=d[yrs[-1]]
    ft=max(first,key=first.get); lt=max(last,key=last.get)
    if ft==lt: return 88,f'{lt} 穩定'
    if tree_of(ft)==tree_of(lt): return 78,f'{ft} → {lt}（同樹系轉移）'
    if last[lt]>=55: return 68,f'{ft} → {lt}（跨樹系轉型）'
    return 50,f'{ft} → {lt}（多重身份轉型）'
def completeness(fin):
    fields=['Revenue_CAGR','EPS_CAGR','ROIC','ROE','FCF_Margin','VDF_Exposure','Cycle_Score','Capex_Direction','Market_Multiple']
    return round(sum(fin.get(f) is not None for f in fields)/len(fields)*100,1)
def cid_scores(c,fin):
    raw={}
    for i,w in c['base_identity'].items(): raw[i]=raw.get(i,0)+w*.4
    vdf=fin.get('VDF_Exposure',0); cyc=fin.get('Cycle_Score',0); cap=fin.get('Capex_Direction',0); mul=fin.get('Market_Multiple',0); g=fin.get('Revenue_CAGR',0); roic=fin.get('ROIC',0); fcf=fin.get('FCF_Margin',0)
    if cap>=75: raw['AI Infrastructure']=raw.get('AI Infrastructure',0)+18; raw['AI Server Platform']=raw.get('AI Server Platform',0)+8
    elif cap>=55: raw['Advanced Manufacturing']=raw.get('Advanced Manufacturing',0)+10; raw['Advanced Materials']=raw.get('Advanced Materials',0)+8
    else: raw['Traditional Industry']=raw.get('Traditional Industry',0)+5
    if vdf>=80: raw['AI Infrastructure']=raw.get('AI Infrastructure',0)+12; raw['Compute Infrastructure']=raw.get('Compute Infrastructure',0)+8
    elif vdf>=65: raw['Intelligent Automation']=raw.get('Intelligent Automation',0)+8; raw['AI Platform']=raw.get('AI Platform',0)+6
    elif vdf<=10 and c['sector']=='Financial': raw['Financial Franchise']=raw.get('Financial Franchise',0)+18
    if mul>=80 and g>=20: raw['Growth Re-rating']=raw.get('Growth Re-rating',0)+12
    if cyc>=80: raw['Memory Cycle']=raw.get('Memory Cycle',0)+18; raw['Super Cycle']=raw.get('Super Cycle',0)+10
    if roic>=25 and fcf>=15: raw['Structural Compounder']=raw.get('Structural Compounder',0)+16
    if c['sector']=='Financial': raw['Financial Franchise']=raw.get('Financial Franchise',0)+12
    return norm(raw)
def maturity(conf,coh,drift,cycle):
    if conf>=65 and coh>=82 and drift>=72 and cycle<80: return 'Mature Leader'
    if conf>=55 and coh>=75 and drift>=60: return 'Emerging Leader'
    if cycle>=80: return 'Cycle Driven'
    if drift<60: return 'Transitioning'
    if coh<55: return 'Conglomerate / Multi-Identity'
    return 'Mixed Profile'
def model_suggest(main,mat,sector):
    if sector=='Financial' or 'Financial' in main: return 'V8：PB-ROE / Residual Income / Dividend Yield'
    if 'Memory' in main or mat=='Cycle Driven': return 'V12：Cycle PE / EV-EBITDA / PB-ROE'
    if mat=='Mature Leader': return 'V10：DCF-FCFF / ROIC Premium / CAP Premium'
    if mat=='Emerging Leader': return 'V12：VDF Premium + State Adjustment'
    if mat=='Transitioning': return 'V12.2：Winner Learning + 人工確認'
    return 'V12：Hybrid Engine'
def prof_sum(main,mat):
    return {'Mature Leader':f'{main} 成熟龍頭，身份清楚且價值鏈一致。','Emerging Leader':f'{main} 成長型領先者，身份逐步明確。','Cycle Driven':f'{main} 週期驅動型公司，估值需看景氣位置。','Transitioning':f'{main} 轉型中，公司身份仍在移動。','Conglomerate / Multi-Identity':f'{main} 多重身份公司，需避免單一模型。'}.get(mat,f'{main} 混合型公司，需搭配模型選擇器。')

companies={
'2330 台積電':{'symbol':'2330.TW','fallback_price':2370,'sector':'Semiconductor','base_identity':{'Semiconductor':40,'Advanced Manufacturing':35,'Foundry':25},'fin':{'Revenue_CAGR':18,'EPS_CAGR':22,'ROIC':32,'ROE':31,'FCF_Margin':22,'VDF_Exposure':85,'Cycle_Score':72,'Capex_Direction':90,'Market_Multiple':78},'identity_drift':{'2022':{'Foundry':55,'Semiconductor':30,'Advanced Packaging':15},'2024':{'Advanced Manufacturing':45,'Foundry':35,'AI Infrastructure':20},'2026':{'AI Infrastructure':55,'Advanced Manufacturing':30,'Foundry':15}}},
'2383 台光電':{'symbol':'2383.TW','fallback_price':5450,'sector':'PCB / CCL','base_identity':{'Advanced Materials':50,'PCB/CCL':35,'AI Infrastructure Material':15},'fin':{'Revenue_CAGR':28,'EPS_CAGR':35,'ROIC':30,'ROE':32,'FCF_Margin':18,'VDF_Exposure':88,'Cycle_Score':86,'Capex_Direction':70,'Market_Multiple':88},'identity_drift':{'2022':{'PCB/CCL':60,'Advanced Materials':30,'AI Infrastructure Material':10},'2024':{'Advanced Materials':50,'PCB/CCL':30,'AI Infrastructure Material':20},'2026':{'Advanced Materials':60,'AI Infrastructure Material':30,'PCB/CCL':10}}},
'3017 奇鋐':{'symbol':'3017.TW','fallback_price':980,'sector':'Thermal','base_identity':{'Thermal Solution':45,'AI Infrastructure':35,'Advanced Manufacturing':20},'fin':{'Revenue_CAGR':25,'EPS_CAGR':30,'ROIC':24,'ROE':28,'FCF_Margin':13,'VDF_Exposure':82,'Cycle_Score':78,'Capex_Direction':75,'Market_Multiple':86},'identity_drift':{'2022':{'Thermal Solution':70,'Industrial Component':30},'2024':{'Thermal Solution':55,'AI Infrastructure':35,'Industrial Component':10},'2026':{'AI Infrastructure':55,'Thermal Solution':35,'Advanced Manufacturing':10}}},
'2454 聯發科':{'symbol':'2454.TW','fallback_price':3910,'sector':'Semiconductor','base_identity':{'AI Platform':45,'Semiconductor':30,'Edge AI':25},'fin':{'Revenue_CAGR':15,'EPS_CAGR':18,'ROIC':24,'ROE':25,'FCF_Margin':20,'VDF_Exposure':82,'Cycle_Score':70,'Capex_Direction':45,'Market_Multiple':85},'identity_drift':{'2022':{'Mobile SoC':60,'Semiconductor':30,'AI Platform':10},'2024':{'Mobile SoC':40,'AI Platform':35,'Semiconductor':25},'2026':{'AI Platform':60,'Edge AI':25,'Semiconductor':15}}},
'2382 廣達':{'symbol':'2382.TW','fallback_price':310,'sector':'ODM','base_identity':{'AI Server Platform':45,'ODM':35,'Cloud Infrastructure':20},'fin':{'Revenue_CAGR':20,'EPS_CAGR':25,'ROIC':18,'ROE':22,'FCF_Margin':8,'VDF_Exposure':80,'Cycle_Score':78,'Capex_Direction':80,'Market_Multiple':82},'identity_drift':{'2022':{'Notebook ODM':80,'Server ODM':20},'2024':{'Notebook ODM':50,'AI Server Platform':40,'ODM':10},'2026':{'AI Server Platform':60,'Cloud Infrastructure':25,'ODM':15}}},
'3231 緯創':{'symbol':'3231.TW','fallback_price':145,'sector':'ODM','base_identity':{'AI Server Platform':40,'ODM':40,'Cloud Infrastructure':20},'fin':{'Revenue_CAGR':18,'EPS_CAGR':28,'ROIC':16,'ROE':20,'FCF_Margin':6,'VDF_Exposure':76,'Cycle_Score':75,'Capex_Direction':78,'Market_Multiple':80},'identity_drift':{'2022':{'Notebook ODM':70,'Server ODM':30},'2024':{'AI Server Platform':45,'Notebook ODM':40,'ODM':15},'2026':{'AI Server Platform':58,'ODM':25,'Cloud Infrastructure':17}}},
'6215 和椿':{'symbol':'6215.TWO','fallback_price':100.5,'sector':'Automation','base_identity':{'Intelligent Automation':45,'Robot Integrator':35,'Industrial Equipment':20},'fin':{'Revenue_CAGR':18,'EPS_CAGR':20,'ROIC':14,'ROE':12,'FCF_Margin':8,'VDF_Exposure':72,'Cycle_Score':65,'Capex_Direction':55,'Market_Multiple':78},'identity_drift':{'2022':{'Industrial Equipment':60,'Automation':40},'2024':{'Intelligent Automation':40,'Industrial Equipment':35,'Robot Integrator':25},'2026':{'Intelligent Automation':55,'Robot Integrator':30,'Industrial Equipment':15}}},
'2049 上銀':{'symbol':'2049.TW','fallback_price':318.5,'sector':'Automation','base_identity':{'Intelligent Automation':35,'Robot Component':35,'Industrial Equipment':30},'fin':{'Revenue_CAGR':9,'EPS_CAGR':8,'ROIC':12,'ROE':10,'FCF_Margin':10,'VDF_Exposure':55,'Cycle_Score':55,'Capex_Direction':45,'Market_Multiple':60},'identity_drift':{'2022':{'Industrial Equipment':55,'Robot Component':35,'Intelligent Automation':10},'2024':{'Robot Component':40,'Industrial Equipment':35,'Intelligent Automation':25},'2026':{'Robot Component':40,'Intelligent Automation':35,'Industrial Equipment':25}}},
'4540 全球傳動':{'symbol':'4540.TW','fallback_price':55.6,'sector':'Automation','base_identity':{'Robot Component':40,'Industrial Equipment':35,'Intelligent Automation':25},'fin':{'Revenue_CAGR':10,'EPS_CAGR':8,'ROIC':8,'ROE':7,'FCF_Margin':7,'VDF_Exposure':45,'Cycle_Score':58,'Capex_Direction':40,'Market_Multiple':55},'identity_drift':{'2022':{'Industrial Equipment':60,'Robot Component':30,'Intelligent Automation':10},'2024':{'Robot Component':40,'Industrial Equipment':40,'Intelligent Automation':20},'2026':{'Robot Component':45,'Intelligent Automation':30,'Industrial Equipment':25}}},
'2408 南亞科':{'symbol':'2408.TW','fallback_price':95,'sector':'Memory','base_identity':{'Memory Cycle':70,'Semiconductor':20,'Commodity Tech':10},'fin':{'Revenue_CAGR':35,'EPS_CAGR':45,'ROIC':7,'ROE':8,'FCF_Margin':-3,'VDF_Exposure':45,'Cycle_Score':88,'Capex_Direction':65,'Market_Multiple':82},'identity_drift':{'2022':{'Memory Cycle':80,'Semiconductor':20},'2024':{'Memory Cycle':75,'Commodity Tech':15,'Semiconductor':10},'2026':{'Memory Cycle':65,'Super Cycle':25,'Semiconductor':10}}},
'2344 華邦電':{'symbol':'2344.TW','fallback_price':30,'sector':'Memory','base_identity':{'Memory Cycle':60,'Specialty Memory':25,'Commodity Tech':15},'fin':{'Revenue_CAGR':20,'EPS_CAGR':30,'ROIC':6,'ROE':7,'FCF_Margin':-5,'VDF_Exposure':35,'Cycle_Score':82,'Capex_Direction':55,'Market_Multiple':75},'identity_drift':{'2022':{'Memory Cycle':70,'Specialty Memory':20,'Commodity Tech':10},'2024':{'Memory Cycle':65,'Specialty Memory':25,'Commodity Tech':10},'2026':{'Memory Cycle':60,'Specialty Memory':25,'Super Cycle':15}}},
'2881 富邦金':{'symbol':'2881.TW','fallback_price':128.5,'sector':'Financial','base_identity':{'Financial Franchise':60,'Insurance Holding':30,'Banking Holding':10},'fin':{'Revenue_CAGR':8,'EPS_CAGR':12,'ROIC':10,'ROE':14,'FCF_Margin':8,'VDF_Exposure':5,'Cycle_Score':55,'Capex_Direction':10,'Market_Multiple':50},'identity_drift':{'2022':{'Financial Franchise':60,'Insurance Holding':30,'Banking Holding':10},'2024':{'Financial Franchise':62,'Insurance Holding':28,'Banking Holding':10},'2026':{'Financial Franchise':60,'Insurance Holding':30,'Banking Holding':10}}},
'2891 中信金':{'symbol':'2891.TW','fallback_price':70.3,'sector':'Financial','base_identity':{'Financial Franchise':55,'Banking Holding':35,'Insurance Holding':10},'fin':{'Revenue_CAGR':6,'EPS_CAGR':9,'ROIC':9,'ROE':13,'FCF_Margin':7,'VDF_Exposure':5,'Cycle_Score':52,'Capex_Direction':10,'Market_Multiple':48},'identity_drift':{'2022':{'Financial Franchise':55,'Banking Holding':35,'Insurance Holding':10},'2024':{'Financial Franchise':56,'Banking Holding':34,'Insurance Holding':10},'2026':{'Financial Franchise':55,'Banking Holding':35,'Insurance Holding':10}}}
}

rows=[]; profile_rows=[]; radar_rows=[]; drift_rows=[]
for name,c in companies.items():
    price,ps=fetch_price(c['symbol'],c['fallback_price']); fin=c['fin']; ids=cid_scores(c,fin); trees=tree_scores(ids)
    conf=identity_confidence(ids); coh=coherence(ids); drift,dtxt=drift_score(c); comp=completeness(fin)
    main=max(ids,key=ids.get); second=list(ids.keys())[1] if len(ids)>1 else ''; third=list(ids.keys())[2] if len(ids)>2 else ''
    mat=maturity(conf,coh,drift,fin.get('Cycle_Score',0)); sugg=model_suggest(main,mat,c['sector']); summ=prof_sum(main,mat)
    rows.append({'公司':name,'代號':c['symbol'],'現價':price,'主身份':main,'副身份':second,'第三身份':third,'主樹系':max(trees,key=trees.get),'Identity Confidence':conf,'Identity Coherence':coh,'Identity Drift':drift,'Data Completeness':comp,'Growth Exposure':fin.get('Revenue_CAGR',0),'Cycle Exposure':fin.get('Cycle_Score',0),'VDF Exposure':fin.get('VDF_Exposure',0),'身份成熟度':mat,'建議模型':sugg,'CID總評':summ,'Drift方向':dtxt,'身份分布':'、'.join([f'{k}:{v}%' for k,v in ids.items()]),'樹系分布':'、'.join([f'{k}:{v:.1f}%' for k,v in trees.items()]),'現價來源':ps})
    for k,v in ids.items(): profile_rows.append({'公司':name,'項目':k,'類型':'Identity','Score':v,'Tree':tree_of(k)})
    for k,v in trees.items(): profile_rows.append({'公司':name,'項目':k,'類型':'Tree','Score':round(v,1),'Tree':k})
    for metric,value in {'Identity Confidence':conf,'Identity Coherence':coh,'Identity Drift':drift,'Growth Exposure':min(100,fin.get('Revenue_CAGR',0)*3),'Cycle Exposure':fin.get('Cycle_Score',0),'VDF Exposure':fin.get('VDF_Exposure',0)}.items(): radar_rows.append({'公司':name,'CID維度':metric,'Score':round(value,1)})
    for y,d in c.get('identity_drift',{}).items():
        for i,s in d.items(): drift_rows.append({'公司':name,'年份':y,'Identity':i,'Score':s})

df=pd.DataFrame(rows); profile_df=pd.DataFrame(profile_rows); radar_df=pd.DataFrame(radar_rows); drift_df=pd.DataFrame(drift_rows)
summary_df=pd.DataFrame([{'指標':'樣本公司數','值':len(df)},{'指標':'平均Identity Confidence','值':f"{round(df['Identity Confidence'].mean(),1)}%"},{'指標':'平均Identity Coherence','值':f"{round(df['Identity Coherence'].mean(),1)}%"},{'指標':'平均Identity Drift','值':f"{round(df['Identity Drift'].mean(),1)}%"},{'指標':'Mature Leader數','值':int((df['身份成熟度']=='Mature Leader').sum())},{'指標':'Transitioning數','值':int((df['身份成熟度']=='Transitioning').sum())}])
maturity_summary=df.groupby('身份成熟度').size().reset_index(name='公司數').sort_values('公司數',ascending=False)

st.sidebar.header('V12.9 CID 控制台')
page=st.sidebar.radio('功能',['CID Profile Overview','Profile Card','CID Radar','Identity Distribution','Identity Drift','Model Suggestion','Export JSON'])
selected_company=st.sidebar.selectbox('選擇公司',df['公司'].tolist())
st.sidebar.divider(); st.sidebar.metric('樣本公司',len(df)); st.sidebar.metric('平均Confidence',f"{round(df['Identity Confidence'].mean(),1)}%"); st.sidebar.metric('平均Coherence',f"{round(df['Identity Coherence'].mean(),1)}%")
if page=='CID Profile Overview':
    st.header('一、CID Profile Overview'); st.write('V12.9 將 Confidence、Coherence、Drift 拆開並列，避免單一分數失真。'); st.dataframe(df,use_container_width=True); st.subheader('CID摘要'); st.dataframe(summary_df,use_container_width=True); st.subheader('身份成熟度分布'); st.dataframe(maturity_summary,use_container_width=True)
elif page=='Profile Card':
    st.header('二、Identity Profile Card'); row=df[df['公司']==selected_company].iloc[0]
    c1,c2,c3,c4=st.columns(4); c1.metric('主身份',row['主身份']); c2.metric('副身份',row['副身份']); c3.metric('身份成熟度',row['身份成熟度']); c4.metric('現價','N/A' if row['現價'] is None else f"{row['現價']:,.2f}")
    score_card=pd.DataFrame([{'CID分數':'Identity Confidence','Score':row['Identity Confidence'],'說明':'主身份是否清楚'},{'CID分數':'Identity Coherence','Score':row['Identity Coherence'],'說明':'多個身份是否屬同一價值鏈'},{'CID分數':'Identity Drift','Score':row['Identity Drift'],'說明':'身份轉移是否穩定'},{'CID分數':'Data Completeness','Score':row['Data Completeness'],'說明':'資料完整度'}])
    st.subheader('CID 三大核心分數'); st.dataframe(score_card,use_container_width=True); st.subheader('CID總評'); st.success(row['CID總評']); st.subheader('建議模型'); st.info(row['建議模型'])
elif page=='CID Radar':
    st.header('三、CID Radar'); selected=radar_df[radar_df['公司']==selected_company]; st.dataframe(selected,use_container_width=True); st.bar_chart(selected.set_index('CID維度')['Score'])
elif page=='Identity Distribution':
    st.header('四、Identity Distribution'); selected=profile_df[profile_df['公司']==selected_company]; st.dataframe(selected,use_container_width=True); id_only=selected[selected['類型']=='Identity']; st.bar_chart(id_only.set_index('項目')['Score'])
elif page=='Identity Drift':
    st.header('五、Identity Drift'); st.dataframe(drift_df,use_container_width=True); selected=drift_df[drift_df['公司']==selected_company]
    if not selected.empty: st.line_chart(selected.pivot_table(index='年份',columns='Identity',values='Score',fill_value=0))
elif page=='Model Suggestion':
    st.header('六、Model Suggestion'); st.dataframe(df[['公司','主身份','身份成熟度','建議模型','CID總評']],use_container_width=True)
elif page=='Export JSON':
    st.header('七、Export JSON'); export={'version':'V12.9 CID Profile Engine','updated_at':datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'concept':'Identity Confidence, Coherence, and Drift are shown separately instead of being compressed into a single score.','cid_profiles':df.to_dict(orient='records'),'identity_distribution':profile_df.to_dict(orient='records'),'cid_radar':radar_df.to_dict(orient='records'),'identity_drift':drift_df.to_dict(orient='records'),'identity_tree':IDENTITY_TREE,'summary':summary_df.to_dict(orient='records')}; st.code(json.dumps(export,ensure_ascii=False,indent=2),language='json')
