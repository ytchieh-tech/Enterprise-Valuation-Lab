import streamlit as st

st.set_page_config(
    page_title="Enterprise Valuation Lab",
    page_icon="🏛",
    layout="wide"
)

st.title("🏛 Enterprise Valuation Lab")
st.subheader("企業評價模型研究院")

st.info("這個平台專門負責模型驗證與淘汰，不影響主平台速度。")

menu = st.sidebar.radio(
    "功能",
    [
        "首頁",
        "財報資料庫",
        "模型競技場",
        "模型淘汰中心",
        "模型池資料庫"
    ]
)

if menu == "首頁":
    st.success("Valuation Lab 啟動成功")

elif menu == "財報資料庫":
    st.write("財報中心")

elif menu == "模型競技場":
    st.write("31模型競技場")

elif menu == "模型淘汰中心":
    st.write("Model Elimination Engine")

elif menu == "模型池資料庫":
    st.write("Model Survival Database")
