
import json
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

try:
    import yfinance as yf
except Exception:
    yf = None


st.set_page_config(page_title="Enterprise Valuation Lab V12.5", page_icon="🏛️", layout="wide")

st.title("🏛️ Enterprise Valuation Lab")
st.subheader("V12.5｜CID Pilot：Company Identity Database 試驗版")
st.info(
    "本版重點：先蒐集財報/市場因子，建立公司身份辨識系統 CID。"
    "目的不是直接估值，而是判斷公司目前更像哪一種身份，並輸出身份分布、信心度與人工檢查清單。"
)


# ============================================================
# Helpers
# ============================================================

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


@st.cache_data(ttl=3600)
def fetch_yfinance_financials(symbol):
    """嘗試從 yfinance 抓財報。若台股資料缺漏，回傳空資料，由 fallback 補足。"""
    if yf is None:
        return {}, "yfinance 未安裝"

    candidates = []
    if symbol.endswith(".TW") or symbol.endswith(".TWO"):
        candidates.append(symbol)
        base = symbol.split(".")[0]
        candidates.append(base + (".TWO" if symbol.endswith(".TW") else ".TW"))
    else:
        candidates += [symbol + ".TW", symbol + ".TWO"]

    for ticker in candidates:
        try:
            t = yf.Ticker(ticker)
            income = t.financials
            balance = t.balance_sheet
            cashflow = t.cashflow

            if income is None or income.empty:
                continue

            data = {}
            # yfinance rows vary by company. Try common rows.
            def get_latest(df, rows):
                if df is None or df.empty:
                    return None
                for r in rows:
                    if r in df.index:
                        s = df.loc[r].dropna()
                        if len(s) > 0:
                            return float(s.iloc[0])
                return None

            data["Revenue"] = get_latest(income, ["Total Revenue", "Operating Revenue"])
            data["Net_Income"] = get_latest(income, ["Net Income", "Net Income Common Stockholders"])
            data["Operating_Income"] = get_latest(income, ["Operating Income"])
            data["Total_Assets"] = get_latest(balance, ["Total Assets"])
            data["Equity"] = get_latest(balance, ["Stockholders Equity", "Total Equity Gross Minority Interest"])
            data["Total_Liabilities"] = get_latest(balance, ["Total Liabilities Net Minority Interest", "Total Liabilities"])
            data["Operating_Cash_Flow"] = get_latest(cashflow, ["Operating Cash Flow", "Total Cash From Operating Activities"])
            data["Capex"] = get_latest(cashflow, ["Capital Expenditure", "Capital Expenditures"])

            valid = {k: v for k, v in data.items() if v is not None}
            if len(valid) >= 4:
                return valid, f"yfinance 財報：{ticker}"
        except Exception:
            pass

    return {}, "yfinance 財報缺漏"


def completeness(fin):
    fields = [
        "Revenue", "Net_Income", "Operating_Income", "Total_Assets", "Equity",
        "Total_Liabilities", "Operating_Cash_Flow", "Capex",
        "Revenue_CAGR", "EPS_CAGR", "ROIC", "ROE", "FCF_Margin",
        "VDF_Exposure", "Cycle_Score", "Capex_Direction", "Market_Multiple"
    ]
    ok = 0
    missing = []
    for f in fields:
        if fin.get(f) is not None:
            ok += 1
        else:
            missing.append(f)
    return round(ok / len(fields) * 100, 1), missing


def normalize_scores(raw):
    total = sum(max(0, v) for v in raw.values())
    if total <= 0:
        return {}
    scores = {k: round(max(0, v) / total * 100, 1) for k, v in raw.items()}
    diff = round(100 - sum(scores.values()), 1)
    if scores and abs(diff) >= 0.1:
        best = max(scores, key=scores.get)
        scores[best] = round(scores[best] + diff, 1)
    return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))


def cid_identity_scores(company, fin):
    """
    CID identity scoring:
    營收來源/產業標籤 40%、Capex方向 20%、VDF 20%、市場估值特徵 20%
    此試驗版用 fallback 財報因子與市場因子模擬實際權重。
    """
    industry_tag = company["base_identity"]
    vdf = fin.get("VDF_Exposure", 0)
    cycle = fin.get("Cycle_Score", 0)
    capex = fin.get("Capex_Direction", 0)
    multiple = fin.get("Market_Multiple", 0)
    growth = fin.get("Revenue_CAGR", 0)
    roic = fin.get("ROIC", 0)
    fcf = fin.get("FCF_Margin", 0)

    raw = {}

    # Start with base identity: objective revenue/industry source.
    for identity, weight in industry_tag.items():
        raw[identity] = raw.get(identity, 0) + weight * 0.40

    # Capex direction
    if capex >= 75:
        raw["AI Infrastructure"] = raw.get("AI Infrastructure", 0) + 18
        raw["AI Server Platform"] = raw.get("AI Server Platform", 0) + 8
    elif capex >= 55:
        raw["Advanced Manufacturing"] = raw.get("Advanced Manufacturing", 0) + 10
        raw["Advanced Materials"] = raw.get("Advanced Materials", 0) + 8
    else:
        raw["Traditional Industry"] = raw.get("Traditional Industry", 0) + 5

    # VDF / value driver
    if vdf >= 80:
        raw["AI Infrastructure"] = raw.get("AI Infrastructure", 0) + 12
        raw["Compute Infrastructure"] = raw.get("Compute Infrastructure", 0) + 8
    elif vdf >= 65:
        raw["Intelligent Automation"] = raw.get("Intelligent Automation", 0) + 8
        raw["AI Platform"] = raw.get("AI Platform", 0) + 6
    elif vdf <= 10 and company["sector"] == "Financial":
        raw["Financial Franchise"] = raw.get("Financial Franchise", 0) + 18

    # Multiple / market perception
    if multiple >= 80 and growth >= 20:
        raw["Growth Re-rating"] = raw.get("Growth Re-rating", 0) + 12
    if cycle >= 80:
        raw["Memory Cycle"] = raw.get("Memory Cycle", 0) + 18
        raw["Super Cycle"] = raw.get("Super Cycle", 0) + 10
    if roic >= 25 and fcf >= 15:
        raw["Structural Compounder"] = raw.get("Structural Compounder", 0) + 16
    if company["sector"] == "Financial":
        raw["Financial Franchise"] = raw.get("Financial Franchise", 0) + 12

    return normalize_scores(raw)


def confidence_from_identity(scores):
    vals = list(scores.values())
    if not vals:
        return 0, "需人工確認"
    top = vals[0]
    second = vals[1] if len(vals) > 1 else 0
    spread = top - second
    confidence = round(min(100, max(0, top * 0.7 + spread * 0.6)), 1)

    if confidence >= 80:
        label = "身份明確"
    elif confidence >= 60:
        label = "身份偏明確"
    elif confidence >= 40:
        label = "轉型中 / 多重身份"
    else:
        label = "需人工確認"
    return confidence, label


def drift_direction(company):
    drift = company.get("identity_drift", {})
    if not drift:
        return "暫無歷史"
    years = sorted(drift.keys())
    first = drift[years[0]]
    last = drift[years[-1]]
    first_top = max(first, key=first.get)
    last_top = max(last, key=last.get)
    if first_top != last_top:
        return f"{first_top} → {last_top}"
    return f"{last_top} 穩定"


# ============================================================
# 12-stock CID Pilot sample
# fallback_financials: 將來可替換成財報狗 / MOPS 自動計算結果
# ============================================================

companies = {
    "2330 台積電": {
        "symbol": "2330.TW", "fallback_price": 2370, "sector": "Semiconductor",
        "base_identity": {"Semiconductor": 40, "Advanced Manufacturing": 35, "Foundry": 25},
        "fallback_financials": {
            "Revenue_CAGR": 18, "EPS_CAGR": 22, "ROIC": 32, "ROE": 31, "FCF_Margin": 22,
            "VDF_Exposure": 85, "Cycle_Score": 72, "Capex_Direction": 90, "Market_Multiple": 78,
            "Revenue": 3000000, "Net_Income": 1100000, "Operating_Income": 1350000,
            "Total_Assets": 6500000, "Equity": 4100000, "Total_Liabilities": 2400000,
            "Operating_Cash_Flow": 1550000, "Capex": 900000,
        },
        "identity_drift": {
            "2022": {"Foundry": 55, "Semiconductor": 30, "Advanced Packaging": 15},
            "2024": {"Advanced Manufacturing": 45, "Foundry": 35, "AI Infrastructure": 20},
            "2026": {"AI Infrastructure": 55, "Advanced Manufacturing": 30, "Foundry": 15},
        },
    },
    "2383 台光電": {
        "symbol": "2383.TW", "fallback_price": 5450, "sector": "PCB / CCL",
        "base_identity": {"Advanced Materials": 50, "PCB/CCL": 35, "AI Infrastructure Material": 15},
        "fallback_financials": {
            "Revenue_CAGR": 28, "EPS_CAGR": 35, "ROIC": 30, "ROE": 32, "FCF_Margin": 18,
            "VDF_Exposure": 88, "Cycle_Score": 86, "Capex_Direction": 70, "Market_Multiple": 88,
            "Revenue": 95000, "Net_Income": 22000, "Operating_Income": 28000,
            "Total_Assets": 165000, "Equity": 72000, "Total_Liabilities": 93000,
            "Operating_Cash_Flow": 26000, "Capex": 9000,
        },
        "identity_drift": {
            "2022": {"PCB/CCL": 60, "Advanced Materials": 30, "AI Infrastructure Material": 10},
            "2024": {"Advanced Materials": 50, "PCB/CCL": 30, "AI Infrastructure Material": 20},
            "2026": {"Advanced Materials": 60, "AI Infrastructure Material": 30, "PCB/CCL": 10},
        },
    },
    "3017 奇鋐": {
        "symbol": "3017.TW", "fallback_price": 980, "sector": "Thermal",
        "base_identity": {"Thermal Solution": 45, "AI Infrastructure": 35, "Advanced Manufacturing": 20},
        "fallback_financials": {
            "Revenue_CAGR": 25, "EPS_CAGR": 30, "ROIC": 24, "ROE": 28, "FCF_Margin": 13,
            "VDF_Exposure": 82, "Cycle_Score": 78, "Capex_Direction": 75, "Market_Multiple": 86,
            "Revenue": 85000, "Net_Income": 12000, "Operating_Income": 15000,
            "Total_Assets": 90000, "Equity": 42000, "Total_Liabilities": 48000,
            "Operating_Cash_Flow": 14000, "Capex": 6000,
        },
        "identity_drift": {
            "2022": {"Thermal Solution": 70, "Industrial Component": 30},
            "2024": {"Thermal Solution": 55, "AI Infrastructure": 35, "Industrial Component": 10},
            "2026": {"AI Infrastructure": 55, "Thermal Solution": 35, "Advanced Manufacturing": 10},
        },
    },
    "2454 聯發科": {
        "symbol": "2454.TW", "fallback_price": 3910, "sector": "Semiconductor",
        "base_identity": {"AI Platform": 45, "Semiconductor": 30, "Edge AI": 25},
        "fallback_financials": {
            "Revenue_CAGR": 15, "EPS_CAGR": 18, "ROIC": 24, "ROE": 25, "FCF_Margin": 20,
            "VDF_Exposure": 82, "Cycle_Score": 70, "Capex_Direction": 45, "Market_Multiple": 85,
            "Revenue": 560000, "Net_Income": 110000, "Operating_Income": 130000,
            "Total_Assets": 820000, "Equity": 560000, "Total_Liabilities": 260000,
            "Operating_Cash_Flow": 130000, "Capex": 25000,
        },
        "identity_drift": {
            "2022": {"Mobile SoC": 60, "Semiconductor": 30, "AI Platform": 10},
            "2024": {"Mobile SoC": 40, "AI Platform": 35, "Semiconductor": 25},
            "2026": {"AI Platform": 60, "Edge AI": 25, "Semiconductor": 15},
        },
    },
    "2382 廣達": {
        "symbol": "2382.TW", "fallback_price": 310, "sector": "ODM",
        "base_identity": {"AI Server Platform": 45, "ODM": 35, "Cloud Infrastructure": 20},
        "fallback_financials": {
            "Revenue_CAGR": 20, "EPS_CAGR": 25, "ROIC": 18, "ROE": 22, "FCF_Margin": 8,
            "VDF_Exposure": 80, "Cycle_Score": 78, "Capex_Direction": 80, "Market_Multiple": 82,
            "Revenue": 1300000, "Net_Income": 55000, "Operating_Income": 70000,
            "Total_Assets": 900000, "Equity": 300000, "Total_Liabilities": 600000,
            "Operating_Cash_Flow": 65000, "Capex": 28000,
        },
        "identity_drift": {
            "2022": {"Notebook ODM": 80, "Server ODM": 20},
            "2024": {"Notebook ODM": 50, "AI Server Platform": 40, "ODM": 10},
            "2026": {"AI Server Platform": 60, "Cloud Infrastructure": 25, "ODM": 15},
        },
    },
    "3231 緯創": {
        "symbol": "3231.TW", "fallback_price": 145, "sector": "ODM",
        "base_identity": {"AI Server Platform": 40, "ODM": 40, "Cloud Infrastructure": 20},
        "fallback_financials": {
            "Revenue_CAGR": 18, "EPS_CAGR": 28, "ROIC": 16, "ROE": 20, "FCF_Margin": 6,
            "VDF_Exposure": 76, "Cycle_Score": 75, "Capex_Direction": 78, "Market_Multiple": 80,
            "Revenue": 1050000, "Net_Income": 42000, "Operating_Income": 52000,
            "Total_Assets": 760000, "Equity": 260000, "Total_Liabilities": 500000,
            "Operating_Cash_Flow": 46000, "Capex": 22000,
        },
        "identity_drift": {
            "2022": {"Notebook ODM": 70, "Server ODM": 30},
            "2024": {"AI Server Platform": 45, "Notebook ODM": 40, "ODM": 15},
            "2026": {"AI Server Platform": 58, "ODM": 25, "Cloud Infrastructure": 17},
        },
    },
    "6215 和椿": {
        "symbol": "6215.TWO", "fallback_price": 100.5, "sector": "Automation",
        "base_identity": {"Intelligent Automation": 45, "Robot Integrator": 35, "Industrial Equipment": 20},
        "fallback_financials": {
            "Revenue_CAGR": 18, "EPS_CAGR": 20, "ROIC": 14, "ROE": 12, "FCF_Margin": 8,
            "VDF_Exposure": 72, "Cycle_Score": 65, "Capex_Direction": 55, "Market_Multiple": 78,
            "Revenue": 6200, "Net_Income": 360, "Operating_Income": 520,
            "Total_Assets": 7800, "Equity": 4100, "Total_Liabilities": 3700,
            "Operating_Cash_Flow": 420, "Capex": 240,
        },
        "identity_drift": {
            "2022": {"Industrial Equipment": 60, "Automation": 40},
            "2024": {"Intelligent Automation": 40, "Industrial Equipment": 35, "Robot Integrator": 25},
            "2026": {"Intelligent Automation": 55, "Robot Integrator": 30, "Industrial Equipment": 15},
        },
    },
    "2049 上銀": {
        "symbol": "2049.TW", "fallback_price": 318.5, "sector": "Automation",
        "base_identity": {"Intelligent Automation": 35, "Robot Component": 35, "Industrial Equipment": 30},
        "fallback_financials": {
            "Revenue_CAGR": 9, "EPS_CAGR": 8, "ROIC": 12, "ROE": 10, "FCF_Margin": 10,
            "VDF_Exposure": 55, "Cycle_Score": 55, "Capex_Direction": 45, "Market_Multiple": 60,
            "Revenue": 28000, "Net_Income": 2400, "Operating_Income": 3600,
            "Total_Assets": 78000, "Equity": 36000, "Total_Liabilities": 42000,
            "Operating_Cash_Flow": 3900, "Capex": 1700,
        },
        "identity_drift": {
            "2022": {"Industrial Equipment": 55, "Robot Component": 35, "Intelligent Automation": 10},
            "2024": {"Robot Component": 40, "Industrial Equipment": 35, "Intelligent Automation": 25},
            "2026": {"Robot Component": 40, "Intelligent Automation": 35, "Industrial Equipment": 25},
        },
    },
    "4540 全球傳動": {
        "symbol": "4540.TW", "fallback_price": 55.6, "sector": "Automation",
        "base_identity": {"Robot Component": 40, "Industrial Equipment": 35, "Intelligent Automation": 25},
        "fallback_financials": {
            "Revenue_CAGR": 10, "EPS_CAGR": 8, "ROIC": 8, "ROE": 7, "FCF_Margin": 7,
            "VDF_Exposure": 45, "Cycle_Score": 58, "Capex_Direction": 40, "Market_Multiple": 55,
            "Revenue": 4200, "Net_Income": 150, "Operating_Income": 260,
            "Total_Assets": 7600, "Equity": 3000, "Total_Liabilities": 4600,
            "Operating_Cash_Flow": 280, "Capex": 160,
        },
        "identity_drift": {
            "2022": {"Industrial Equipment": 60, "Robot Component": 30, "Intelligent Automation": 10},
            "2024": {"Robot Component": 40, "Industrial Equipment": 40, "Intelligent Automation": 20},
            "2026": {"Robot Component": 45, "Intelligent Automation": 30, "Industrial Equipment": 25},
        },
    },
    "2408 南亞科": {
        "symbol": "2408.TW", "fallback_price": 95, "sector": "Memory",
        "base_identity": {"Memory Cycle": 70, "Semiconductor": 20, "Commodity Tech": 10},
        "fallback_financials": {
            "Revenue_CAGR": 35, "EPS_CAGR": 45, "ROIC": 7, "ROE": 8, "FCF_Margin": -3,
            "VDF_Exposure": 45, "Cycle_Score": 88, "Capex_Direction": 65, "Market_Multiple": 82,
            "Revenue": 70000, "Net_Income": 5000, "Operating_Income": 7000,
            "Total_Assets": 220000, "Equity": 140000, "Total_Liabilities": 80000,
            "Operating_Cash_Flow": 12000, "Capex": 20000,
        },
        "identity_drift": {
            "2022": {"Memory Cycle": 80, "Semiconductor": 20},
            "2024": {"Memory Cycle": 75, "Commodity Tech": 15, "Semiconductor": 10},
            "2026": {"Memory Cycle": 65, "Super Cycle": 25, "Semiconductor": 10},
        },
    },
    "2344 華邦電": {
        "symbol": "2344.TW", "fallback_price": 30, "sector": "Memory",
        "base_identity": {"Memory Cycle": 60, "Specialty Memory": 25, "Commodity Tech": 15},
        "fallback_financials": {
            "Revenue_CAGR": 20, "EPS_CAGR": 30, "ROIC": 6, "ROE": 7, "FCF_Margin": -5,
            "VDF_Exposure": 35, "Cycle_Score": 82, "Capex_Direction": 55, "Market_Multiple": 75,
            "Revenue": 85000, "Net_Income": 4000, "Operating_Income": 6000,
            "Total_Assets": 250000, "Equity": 130000, "Total_Liabilities": 120000,
            "Operating_Cash_Flow": 10000, "Capex": 18000,
        },
        "identity_drift": {
            "2022": {"Memory Cycle": 70, "Specialty Memory": 20, "Commodity Tech": 10},
            "2024": {"Memory Cycle": 65, "Specialty Memory": 25, "Commodity Tech": 10},
            "2026": {"Memory Cycle": 60, "Specialty Memory": 25, "Super Cycle": 15},
        },
    },
    "2881 富邦金": {
        "symbol": "2881.TW", "fallback_price": 128.5, "sector": "Financial",
        "base_identity": {"Financial Franchise": 60, "Insurance Holding": 30, "Banking Holding": 10},
        "fallback_financials": {
            "Revenue_CAGR": 8, "EPS_CAGR": 12, "ROIC": 10, "ROE": 14, "FCF_Margin": 8,
            "VDF_Exposure": 5, "Cycle_Score": 55, "Capex_Direction": 10, "Market_Multiple": 50,
            "Revenue": 900000, "Net_Income": 120000, "Operating_Income": 150000,
            "Total_Assets": 12000000, "Equity": 900000, "Total_Liabilities": 11100000,
            "Operating_Cash_Flow": 0, "Capex": 0,
        },
        "identity_drift": {
            "2022": {"Financial Franchise": 60, "Insurance Holding": 30, "Banking Holding": 10},
            "2024": {"Financial Franchise": 62, "Insurance Holding": 28, "Banking Holding": 10},
            "2026": {"Financial Franchise": 60, "Insurance Holding": 30, "Banking Holding": 10},
        },
    },
    "2891 中信金": {
        "symbol": "2891.TW", "fallback_price": 70.3, "sector": "Financial",
        "base_identity": {"Financial Franchise": 55, "Banking Holding": 35, "Insurance Holding": 10},
        "fallback_financials": {
            "Revenue_CAGR": 6, "EPS_CAGR": 9, "ROIC": 9, "ROE": 13, "FCF_Margin": 7,
            "VDF_Exposure": 5, "Cycle_Score": 52, "Capex_Direction": 10, "Market_Multiple": 48,
            "Revenue": 430000, "Net_Income": 70000, "Operating_Income": 90000,
            "Total_Assets": 8800000, "Equity": 520000, "Total_Liabilities": 8280000,
            "Operating_Cash_Flow": 0, "Capex": 0,
        },
        "identity_drift": {
            "2022": {"Financial Franchise": 55, "Banking Holding": 35, "Insurance Holding": 10},
            "2024": {"Financial Franchise": 56, "Banking Holding": 34, "Insurance Holding": 10},
            "2026": {"Financial Franchise": 55, "Banking Holding": 35, "Insurance Holding": 10},
        },
    },
}


# ============================================================
# Data mode
# ============================================================

st.sidebar.header("V12.5 CID 控制台")
data_mode = st.sidebar.radio("財報資料模式", ["fallback 內建財報", "貼上財報狗/MOPS JSON"], index=0)

external_financials = {}
if data_mode == "貼上財報狗/MOPS JSON":
    raw_json = st.sidebar.text_area(
        "以股票代號為 key，例如 2330",
        height=220,
        placeholder='{"2330":{"Revenue_CAGR":18,"EPS_CAGR":22,"ROIC":32,"ROE":31,"FCF_Margin":22,"VDF_Exposure":85,"Cycle_Score":72}}'
    )
    try:
        if raw_json.strip():
            external_financials = json.loads(raw_json)
    except Exception:
        st.sidebar.error("JSON格式錯誤，請檢查。")


def get_financials(name, company):
    fin = company["fallback_financials"].copy()
    source = "fallback 內建財報"
    code = company["symbol"].split(".")[0]
    if external_financials and code in external_financials:
        fin.update(external_financials[code])
        source = "外部 JSON 財報"
    yf_fin, yf_source = fetch_yfinance_financials(company["symbol"])
    if data_mode == "fallback 內建財報" and yf_fin:
        # Only fill objective statement fields, not synthetic CAGR/identity fields.
        for k, v in yf_fin.items():
            if k in fin and v is not None:
                fin[k] = v
        source = f"{source} + {yf_source}"
    return fin, source


rows = []
drift_rows = []
for name, company in companies.items():
    price, price_source = fetch_price(company["symbol"], company["fallback_price"])
    fin, fin_source = get_financials(name, company)
    comp, missing = completeness(fin)
    ids = cid_identity_scores(company, fin)
    confidence, confidence_label = confidence_from_identity(ids)
    main_identity = max(ids, key=ids.get) if ids else "N/A"
    second_identity = list(ids.keys())[1] if len(ids) > 1 else ""
    second_score = ids.get(second_identity, 0) if second_identity else 0

    rows.append({
        "公司": name,
        "代號": company["symbol"],
        "現價": price,
        "主身份": main_identity,
        "主身份分數": ids.get(main_identity, 0) if ids else 0,
        "副身份": second_identity,
        "副身份分數": second_score,
        "Confidence": confidence,
        "信心分級": confidence_label,
        "Identity Drift": drift_direction(company),
        "財報完整度": comp,
        "財報來源": fin_source,
        "現價來源": price_source,
        "身份分布": "、".join([f"{k}:{v}%" for k, v in ids.items()]),
        "Revenue CAGR": fin.get("Revenue_CAGR"),
        "EPS CAGR": fin.get("EPS_CAGR"),
        "ROIC": fin.get("ROIC"),
        "ROE": fin.get("ROE"),
        "FCF Margin": fin.get("FCF_Margin"),
        "VDF Exposure": fin.get("VDF_Exposure"),
        "Cycle Score": fin.get("Cycle_Score"),
        "Capex Direction": fin.get("Capex_Direction"),
        "Market Multiple": fin.get("Market_Multiple"),
        "缺漏欄位": ", ".join(missing),
    })

    for year, dist in company.get("identity_drift", {}).items():
        for identity, score in dist.items():
            drift_rows.append({
                "公司": name,
                "年份": year,
                "Identity": identity,
                "Score": score,
            })

df = pd.DataFrame(rows)
drift_df = pd.DataFrame(drift_rows)

cid_summary = pd.DataFrame([
    {"指標": "樣本公司數", "值": len(df)},
    {"指標": "平均Confidence", "值": f"{round(df['Confidence'].mean(), 1)}%"},
    {"指標": "身份明確數", "值": int((df["Confidence"] >= 80).sum())},
    {"指標": "轉型中/需檢查數", "值": int((df["Confidence"] < 60).sum())},
    {"指標": "平均財報完整度", "值": f"{round(df['財報完整度'].mean(), 1)}%"},
])

identity_matrix = (
    df.groupby(["主身份", "信心分級"])
    .size()
    .reset_index(name="公司數")
)

page = st.sidebar.radio(
    "功能",
    ["CID Overview", "Identity Distribution", "Identity Confidence", "Identity Drift", "Financial Data Check", "Company Detail", "Export JSON"]
)

selected_company = st.sidebar.selectbox("選擇公司", df["公司"].tolist())

st.sidebar.divider()
st.sidebar.metric("樣本公司", len(df))
st.sidebar.metric("平均Confidence", f"{round(df['Confidence'].mean(), 1)}%")
st.sidebar.metric("需人工檢查", int((df["Confidence"] < 60).sum()))

if page == "CID Overview":
    st.header("一、CID Overview")
    st.write("CID 用 Identity Score 取代單一產業分類，避免公司同時符合多個條件時系統混亂。")
    st.dataframe(df, use_container_width=True)

    st.subheader("CID 摘要")
    st.dataframe(cid_summary, use_container_width=True)

elif page == "Identity Distribution":
    st.header("二、Identity Distribution")
    st.write("每家公司不是只有單一身份，而是身份分布。")
    display_cols = ["公司", "主身份", "主身份分數", "副身份", "副身份分數", "Confidence", "身份分布"]
    st.dataframe(df[display_cols], use_container_width=True)

elif page == "Identity Confidence":
    st.header("三、Identity Confidence")
    st.write("Confidence 越低，代表轉型中或多重身份越明顯，未來不應直接套單一模型。")
    st.dataframe(df[["公司", "主身份", "副身份", "Confidence", "信心分級", "Identity Drift"]], use_container_width=True)

    st.subheader("主身份 × 信心分級")
    st.dataframe(identity_matrix, use_container_width=True)

elif page == "Identity Drift":
    st.header("四、Identity Drift")
    st.write("追蹤公司身份是否從傳統產業轉向新價值驅動角色。")
    if drift_df.empty:
        st.warning("目前沒有 drift 資料。")
    else:
        st.dataframe(drift_df, use_container_width=True)

        company_drift = drift_df[drift_df["公司"] == selected_company]
        if not company_drift.empty:
            pivot = company_drift.pivot_table(index="年份", columns="Identity", values="Score", fill_value=0)
            st.subheader(f"{selected_company} Identity Drift Chart")
            st.line_chart(pivot)

elif page == "Financial Data Check":
    st.header("五、Financial Data Check")
    st.write("檢查財報資料是否完整。若 yfinance 抓不到，系統會用 fallback 或外部 JSON。")
    st.dataframe(df[["公司", "代號", "財報完整度", "財報來源", "缺漏欄位"]], use_container_width=True)

elif page == "Company Detail":
    st.header("六、Company Detail")
    row = df[df["公司"] == selected_company].iloc[0]
    company = companies[selected_company]
    fin, fin_source = get_financials(selected_company, company)
    ids = cid_identity_scores(company, fin)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("主身份", row["主身份"])
    c2.metric("Confidence", f"{row['Confidence']}%")
    c3.metric("信心分級", row["信心分級"])
    c4.metric("現價", "N/A" if row["現價"] is None else f"{row['現價']:,.2f}")

    st.subheader("身份分布")
    id_df = pd.DataFrame([{"Identity": k, "Score": v} for k, v in ids.items()])
    st.dataframe(id_df, use_container_width=True)
    if not id_df.empty:
        st.bar_chart(id_df.set_index("Identity")["Score"])

    st.subheader("財報 / 市場因子")
    st.dataframe(pd.DataFrame([{"欄位": k, "值": v} for k, v in fin.items()]), use_container_width=True)

    st.info(
        "CID 判定來源：營收/產業基礎身份 40% + Capex方向 20% + VDF 20% + 市場估值特徵 20%。"
        "低信心公司代表轉型中或多重身份，後續需人工確認。"
    )

elif page == "Export JSON":
    st.header("七、Export JSON")
    export = {
        "version": "V12.5 CID Pilot",
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cid_results": df.to_dict(orient="records"),
        "identity_drift": drift_df.to_dict(orient="records"),
        "cid_summary": cid_summary.to_dict(orient="records"),
    }
    st.code(json.dumps(export, ensure_ascii=False, indent=2), language="json")
