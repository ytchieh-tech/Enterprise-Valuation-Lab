import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Enterprise Valuation Lab",
    page_icon="🏛️",
    layout="wide"
)

st.title("🏛️ Enterprise Valuation Lab")
st.subheader("Model Fit Engine V1")

st.info("先驗證公司特徵是否能正確選出適用模型")

companies = {
    "2330 台積電": {
        "ROE":"高",
        "FCF":"強",
        "EPS_CAGR":"高",
        "Debt":"低",
        "models":[
            "DCF-FCFF",
            "EVA",
            "EBO"
        ]
    },

    "2308 台達電": {
        "ROE":"高",
        "FCF":"穩定",
        "EPS_CAGR":"中高",
        "Debt":"低",
        "models":[
            "EVA",
            "PB-ROE",
            "Quality Compounder"
        ]
    },

    "2603 長榮": {
        "ROE":"波動",
        "FCF":"波動",
        "EPS_CAGR":"循環",
        "Debt":"中",
        "models":[
            "EV/EBITDA",
            "FCF Yield",
            "Cycle PE"
        ]
    },

    "2881 富邦金": {
        "ROE":"穩定",
        "FCF":"失真",
        "EPS_CAGR":"中",
        "Debt":"金融業",
        "models":[
            "PB-ROE",
            "Dividend Yield",
            "Residual Income"
        ]
    }
}

stock = st.selectbox(
    "選擇測試公司",
    list(companies.keys())
)

data = companies[stock]

st.header("公司特徵")

col1,col2,col3,col4 = st.columns(4)

col1.metric("ROE",data["ROE"])
col2.metric("FCF",data["FCF"])
col3.metric("EPS CAGR",data["EPS_CAGR"])
col4.metric("負債",data["Debt"])

st.header("適用模型")

for model in data["models"]:
    st.success(f"✓ {model}")

st.header("淘汰模型")

all_models = [
    "DCF-FCFF",
    "DCF-FCFE",
    "EVA",
    "EBO",
    "PB-ROE",
    "Dividend Yield",
    "Residual Income",
    "EV/EBITDA",
    "FCF Yield",
    "Cycle PE",
    "AI Premium"
]

removed = [x for x in all_models if x not in data["models"]]

for model in removed:
    st.error(f"✗ {model}")
