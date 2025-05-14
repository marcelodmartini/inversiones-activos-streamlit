import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime
from pycoingecko import CoinGeckoAPI
import investpy
import os
from alpha_vantage.timeseries import TimeSeries
import requests
from deep_translator import GoogleTranslator

st.title("Análisis de Activos Financieros con Fallback Inteligente y Múltiples Fuentes.")
st.write("Subí un archivo CSV con una columna llamada 'Ticker' (ej: AAPL, BTC, GLEN.L, PETR4.SA, etc.)")

col1, col2 = st.columns(2)
with col1:
    fecha_inicio = st.date_input("Fecha de inicio", value=datetime(2010, 1, 1))
with col2:
    fecha_fin = st.date_input("Fecha de fin", value=datetime.today())

uploaded_file = st.file_uploader("Cargar archivo CSV", type=["csv"])
cg = CoinGeckoAPI()

ES_CLOUD = os.environ.get("STREAMLIT_SERVER_HEADLESS", "") == "1"
ALPHA_VANTAGE_API_KEY = st.secrets.get("ALPHA_VANTAGE_API_KEY", "")
FINNHUB_API_KEY = st.secrets.get("FINNHUB_API_KEY", "")
FMP_API_KEY = st.secrets.get("FMP_API_KEY", "")

pais_por_ticker = {
    "SUPV": "argentina", "BBAR": "argentina", "PAMP": "argentina",
    "YPFD": "argentina", "TGSU2": "argentina", "FALABELLA": "chile",
    "CEMEXCPO": "mexico", "EC": "colombia", "EMBR3": "brazil"
}

ticker_map = {
    "YPFD": "YPF.BA", "TGSU2": "TGSU2.BA", "MIRG": "MIRG.BA", "VISTA": "VIST",
    "FALABELLA": "FALABELLA.CL", "CEMEXCPO": "CEMEXCPO.MX", "OM:STIL": "STIL.ST", "HLSE:ETTE": "ETTE.HE"
}

def calcular_score(resultado):
    score = 0
    try:
        beta = resultado.get("Beta") or 0
        debt_equity = resultado.get("Debt/Equity") or 999
        ev_ebitda = resultado.get("EV/EBITDA") or 999
        roe = resultado.get("ROE") or 0
        roic = resultado.get("ROIC") or 0
        peg = resultado.get("PEG Ratio") or 999
        fcf_yield = resultado.get("FCF Yield") or 0
        pe = resultado.get("P/E Ratio") or 999
        pb = resultado.get("P/B Ratio") or 999
        dividend_yield = resultado.get("Dividend Yield") or 0

        if beta <= 1: score += 1
        if debt_equity < 1: score += 1
        if ev_ebitda < 15: score += 1
        if roe > 0.1: score += 1
        if roic > 0.08: score += 1
        if peg < 1.5: score += 1
        if fcf_yield > 5: score += 1
        if pe < 20: score += 1
        if pb < 3: score += 1
        if dividend_yield and dividend_yield > 0.02: score += 1

        if score >= 9: return "⭐⭐⭐⭐⭐ (5/5 - Excelente)", 5
        elif score >= 7: return "⭐⭐⭐⭐ (4/5 - Muy Bueno)", 4
        elif score >= 5: return "⭐⭐⭐ (3/5 - Aceptable)", 3
        elif score >= 3: return "⭐⭐ (2/5 - Riesgoso)", 2
        else: return "⭐ (1/5 - Débil)", 1
    except:
        return "N/A", 0

def obtener_info_fundamental(ticker):
    resultado = {
        "País": None, "PEG Ratio": None, "P/E Ratio": None, "P/B Ratio": None,
        "ROE": None, "ROIC": None, "FCF Yield": None, "Debt/Equity": None,
        "EV/EBITDA": None, "Dividend Yield": None, "Beta": None,
        "Contexto": None, "Semáforo Riesgo": "ROJO"
    }
    try:
        tkr = yf.Ticker(ticker)
        if hasattr(tkr, "info") and isinstance(tkr.info, dict):
            info = tkr.info
            resultado.update({
                "País": info.get("country"),
                "PEG Ratio": info.get("pegRatio"),  # inicial
                "P/E Ratio": info.get("trailingPE"),
                "P/B Ratio": info.get("priceToBook"),
                "ROE": info.get("returnOnEquity"),
                "ROIC": info.get("returnOnAssets"),
                "Debt/Equity": info.get("debtToEquity"),
                "EV/EBITDA": info.get("enterpriseToEbitda"),
                "Dividend Yield": info.get("dividendYield"),
                "Beta": info.get("beta"),
                "Contexto": info.get("longBusinessSummary"),
            })

            # Calcular PEG Ratio si no vino
            if resultado.get("PEG Ratio") is None:
                pe = info.get("trailingPE")
                growth = info.get("earningsQuarterlyGrowth") or info.get("earningsGrowth")
                if pe and growth and growth != 0:
                    resultado["PEG Ratio"] = round(pe / (growth * 100), 2)

            # Calcular FCF Yield si no vino
            if resultado.get("FCF Yield") is None:
                fcf = info.get("freeCashflow")
                market_cap = info.get("marketCap")
                if fcf and market_cap and market_cap > 0:
                    resultado["FCF Yield"] = round(fcf / market_cap * 100, 2)

            beta = resultado["Beta"] or 0
            resultado["Semáforo Riesgo"] = "ROJO" if beta > 1.5 else ("AMARILLO" if beta > 1 else "VERDE")

    except Exception as e:
        print(f"[yfinance] {ticker} -> {e}")

    try:
        if FINNHUB_API_KEY:
            r = requests.get(f"https://finnhub.io/api/v1/stock/metric?symbol={ticker}&metric=all&token={FINNHUB_API_KEY}")
            data = r.json().get("metric", {})
            resultado.update({
                "FCF Yield": data.get("freeCashFlowYieldAnnual") or resultado["FCF Yield"],
            })
    except Exception as e:
        print(f"[finnhub] {ticker} -> {e}")

    try:
        if FMP_API_KEY:
            r = requests.get(f"https://financialmodelingprep.com/api/v3/key-metrics-ttm/{ticker}?apikey={FMP_API_KEY}")
            if r.status_code == 200:
                data = r.json()[0] if isinstance(r.json(), list) and r.json() else {}
                resultado.update({
                    "EV/EBITDA": data.get("evToEbitda") or resultado["EV/EBITDA"],
                    "Debt/Equity": data.get("debtEquityRatio") or resultado["Debt/Equity"],
                    "ROE": data.get("roe") or resultado["ROE"],
                    "ROIC": data.get("roic") or resultado["ROIC"],
                    "FCF Yield": data.get("freeCashFlowYield") or resultado["FCF Yield"],
                })
    except Exception as e:
        print(f"[fmp] {ticker} -> {e}")

    # Traducir contexto si existe
    if resultado.get("Contexto"):
        try:
            resultado["Contexto"] = GoogleTranslator(source='auto', target='es').translate(resultado["Contexto"])
        except Exception as e:
            print(f"[traducción] {ticker} -> {e}")

    return resultado


def analizar_con_yfinance(ticker):
    try:
        data = yf.Ticker(ticker)
        hist = data.history(start=fecha_inicio, end=fecha_fin)
        if hist.empty:
            return None
        min_price = hist['Close'].min()
        max_price = hist['Close'].max()
        current_price = hist['Close'][-1]
        subida = (max_price - current_price) / current_price * 100
        return {
            "Ticker": ticker, "Fuente": "Yahoo Finance",
            "Mínimo": round(min_price, 2), "Máximo": round(max_price, 2),
            "Actual": round(current_price, 2), "% Subida a Máx": round(subida, 2)
        }
    except:
        return None

def analizar_con_alphavantage(ticker):
    try:
        ts = TimeSeries(key=ALPHA_VANTAGE_API_KEY, output_format='pandas')
        data, meta = ts.get_daily_adjusted(symbol=ticker, outputsize='full')
        data = data.sort_index()
        data = data[(data.index >= pd.to_datetime(fecha_inicio)) & (data.index <= pd.to_datetime(fecha_fin))]
        if data.empty:
            return None
        min_price = data['4. close'].min()
        max_price = data['4. close'].max()
        current_price = data['4. close'][-1]
        subida = (max_price - current_price) / current_price * 100
        return {
            "Ticker": ticker, "Fuente": "Alpha Vantage",
            "Mínimo": round(min_price, 2), "Máximo": round(max_price, 2),
            "Actual": round(current_price, 2), "% Subida a Máx": round(subida, 2)
        }
    except:
        return None

def analizar_con_coingecko(coin_id):
    try:
        data = cg.get_coin_market_chart_range_by_id(
            id=coin_id, vs_currency='usd',
            from_timestamp=int(fecha_inicio.timestamp()),
            to_timestamp=int(fecha_fin.timestamp())
        )
        prices = [p[1] for p in data['prices']]
        if not prices:
            return None
        min_price = min(prices)
        max_price = max(prices)
        current_price = prices[-1]
        subida = (max_price - current_price) / current_price * 100
        return {
            "Ticker": coin_id, "Fuente": "CoinGecko",
            "Mínimo": round(min_price, 2), "Máximo": round(max_price, 2),
            "Actual": round(current_price, 2), "% Subida a Máx": round(subida, 2)
        }
    except:
        return None

def analizar_con_investpy(nombre, pais):
    try:
        df = investpy.get_stock_historical_data(
            stock=nombre, country=pais,
            from_date=fecha_inicio.strftime('%d/%m/%Y'),
            to_date=fecha_fin.strftime('%d/%m/%Y')
        )
        min_price = df['Close'].min()
        max_price = df['Close'].max()
        current_price = df['Close'][-1]
        subida = (max_price - current_price) / current_price * 100
        return {
            "Ticker": nombre, "Fuente": f"Investpy ({pais})",
            "Mínimo": round(min_price, 2), "Máximo": round(max_price, 2),
            "Actual": round(current_price, 2), "% Subida a Máx": round(subida, 2)
        }
    except:
        return None

if uploaded_file:
    df_input = pd.read_csv(uploaded_file)
    resultados = []
    criptos_disponibles = [c['id'] for c in cg.get_coins_list()]

    for raw_ticker in df_input['Ticker']:
        raw_ticker = str(raw_ticker).strip()
        ticker_real = ticker_map.get(raw_ticker.upper(), raw_ticker)
        ticker_clean = raw_ticker.upper()
        resultado = None

        if not ES_CLOUD:
            resultado = analizar_con_yfinance(ticker_real)
        if not resultado and ALPHA_VANTAGE_API_KEY and not ES_CLOUD:
            resultado = analizar_con_alphavantage(ticker_clean)
        if not resultado and raw_ticker.lower() in criptos_disponibles:
            resultado = analizar_con_coingecko(raw_ticker.lower())
        if not resultado:
            pais = pais_por_ticker.get(raw_ticker.upper(), 'brazil')
            resultado = analizar_con_investpy(ticker_clean, pais)

        info_fundamental = obtener_info_fundamental(ticker_clean)

        if resultado:
            resultado.update(info_fundamental)
        else:
            resultado = {"Ticker": raw_ticker, "Error": "No se encontró información en ninguna fuente"}
            resultado.update(info_fundamental)

        score_texto, score_numerico = calcular_score(resultado)
        resultado["Score Final"] = score_texto
        resultado["__orden_score"] = score_numerico

        resultados.append(resultado)

    df_result = pd.DataFrame(resultados)

    columnas = df_result.columns.tolist()
    for col in ["Score Final", "Semáforo Riesgo"]:
        if col in columnas:
            columnas.insert(0, columnas.pop(columnas.index(col)))
    df_result = df_result[columnas]

    df_result = df_result.sort_values("__orden_score", ascending=False).drop(columns="__orden_score")

    def resaltar_riesgo(val):
        color = {
            "VERDE": "#c8e6c9",
            "AMARILLO": "#fff9c4",
            "ROJO": "#ffcdd2"
        }.get(val, "#eeeeee")
        return f"background-color: {color}; font-weight: bold"

    styled_df = df_result.style.applymap(resaltar_riesgo, subset=["Semáforo Riesgo"])

    st.dataframe(styled_df, use_container_width=True)

    csv = df_result.to_csv(index=False).encode('utf-8')
    st.download_button("Descargar resultados en CSV", data=csv, file_name="analisis_completo_activos.csv")
