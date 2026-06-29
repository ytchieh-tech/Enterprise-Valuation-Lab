import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Enterprise Valuation Lab",
    page_icon="🏛️",
    layout="wide"
)

st.title("🏛️ Enterprise Valuation Lab")
st.subheader("Model Selection Engine V2")

st.info("依據企業特徵自動篩選最適合的估值模型")

companies = {
    "2330 台積電":{
        "ROE":22,
        "FCF":1200,
        "Growth":18,
        "Debt":12,
        "Industry":"Semiconductor"
    },

    "2308 台達電":{
        "ROE":16,
        "FCF":450,
        "Growth":10,
        "Debt":15,
        "Industry":"Industrial"
    },

    "2603 長榮":{
        "ROE":12,
        "FCF":-300,
        "Growth":5,
        "Debt":40,
        "Industry":"Shipping"
    },

    "2881 富邦金":{
        "ROE":11,
        "FCF":0,
        "Growth":8,
        "Debt":0,
        "Industry":"Financial"
    }
}

stock = st.selectbox(
    "選擇公司",
    list(companies.keys())
)

data = companies[stock]
st.divider()

st.header("公司特徵")

c1,c2,c3,c4 = st.columns(4)

with c1:
    st.metric("ROE",data["ROE"])

with c2:
    st.metric("FCF",data["FCF"])

with c3:
    st.metric("Growth",data["Growth"])

with c4:
    st.metric("Debt",data["Debt"])

st.divider()

score = {}

all_models = [
    "DCF-FCFF",
    "DCF-FCFE",
    "EVA",
    "EBO",
    "PB-ROE",
    "Residual Income",
    "EV/EBITDA",
    "Dividend Yield",
    "Cycle PE"
]

for m in all_models:
    score[m] = 0

# ROE

if data["ROE"] >= 20:
    score["DCF-FCFF"] += 3
    score["EVA"] += 3
    score["EBO"] += 3

elif data["ROE"] >= 10:
    score["PB-ROE"] += 3
    score["Residual Income"] += 3

# FCF

if data["FCF"] > 0:
    score["DCF-FCFF"] += 3
    score["DCF-FCFE"] += 3

else:
    score["EV/EBITDA"] += 3

# Growth

if data["Growth"] >= 15:
    score["DCF-FCFF"] += 2
    score["EVA"] += 2

elif data["Growth"] <= 5:
    score["Cycle PE"] += 2

# Debt

if data["Debt"] >= 40:
    score["EV/EBITDA"] += 2

# Industry

if data["Industry"] == "Financial":
    score["PB-ROE"] += 5
    score["Residual Income"] += 5
    score["Dividend Yield"] += 5

top_models = sorted(
    score.items(),
    key=lambda x:x[1],
    reverse=True
)

selected = top_models[:3]

st.header("推薦模型")

for m,s in selected:
    st.success(f"{m}  (適配分數 {s})")

st.header("模型排名")

ranking = pd.DataFrame(
    top_models,
    columns=["Model","Score"]
)

st.dataframe(
    ranking,
    use_container_width=True
)
