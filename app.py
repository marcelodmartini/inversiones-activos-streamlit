import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime
from pycoingecko import CoinGeckoAPI
import investpy
import os
from alpha_vantage.timeseries import TimeSeries
import requests

st.title("Análisis de Activos Financieros con Fallback Inteligente y Múltiples Fuentes")

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
    "SUPV": "argentina",
    "BBAR": "argentina",
    "PAMP": "argentina",
    "YPFD": "argentina",
    "TGSU2": "argentina",
    "FALABELLA": "chile",
    "CEMEXCPO": "mexico",
    "EC": "colombia",
    "EMBR3": "brazil"
}

ticker_map = {
    "YPFD": "YPF.BA",
    "TGSU2": "TGSU2.BA",
    "MIRG": "MIRG.BA",
    "VISTA": "VIST",
    "FALABELLA": "FALABELLA.CL",
    "CEMEXCPO": "CEMEXCPO.MX",
    "OM:STIL": "STIL.ST",
    "HLSE:ETTE": "ETTE.HE"
}

def obtener_info_fundamental(ticker):
    resultado = {
        "País": None, "PEG Ratio": None, "P/E Ratio": None, "P/B Ratio": None,
        "ROE": None, "ROIC": None, "FCF Yield": None, "Debt/Equity": None,
        "EV/EBITDA": None, "Dividend Yield": None, "Beta": None,
        "Contexto": None, "Semáforo Riesgo": "ROJO"
    }
    try:
        info = yf.Ticker(ticker).info
        resultado.update({
            "País": info.get("country"),
            "PEG Ratio": info.get("pegRatio"),
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
        beta = resultado["Beta"] or 0
        resultado["Semáforo Riesgo"] = "ROJO" if beta > 1.5 else ("AMARILLO" if beta > 1 else "VERDE")
    except:
        pass

    try:
        if FINNHUB_API_KEY:
            r = requests.get(f"https://finnhub.io/api/v1/stock/metric?symbol={ticker}&metric=all&token={FINNHUB_API_KEY}")
            data = r.json().get("metric", {})
            resultado.update({
                "FCF Yield": data.get("freeCashFlowYieldAnnual") or resultado["FCF Yield"],
            })
    except:
        pass

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
    except:
        pass

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
            "Ticker": ticker,
            "Fuente": "Yahoo Finance",
            "Mínimo": round(min_price, 2),
            "Máximo": round(max_price, 2),
            "Actual": round(current_price, 2),
            "% Subida a Máx": round(subida, 2)
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
            "Ticker": ticker,
            "Fuente": "Alpha Vantage",
            "Mínimo": round(min_price, 2),
            "Máximo": round(max_price, 2),
            "Actual": round(current_price, 2),
            "% Subida a Máx": round(subida, 2)
        }
    except:
        return None

def analizar_con_coingecko(coin_id):
    try:
        data = cg.get_coin_market_chart_range_by_id(
            id=coin_id,
            vs_currency='usd',
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
            "Ticker": coin_id,
            "Fuente": "CoinGecko",
            "Mínimo": round(min_price, 2),
            "Máximo": round(max_price, 2),
            "Actual": round(current_price, 2),
            "% Subida a Máx": round(subida, 2)
        }
    except:
        return None

def analizar_con_investpy(nombre, pais):
    try:
        df = investpy.get_stock_historical_data(
            stock=nombre,
            country=pais,
            from_date=fecha_inicio.strftime('%d/%m/%Y'),
            to_date=fecha_fin.strftime('%d/%m/%Y')
        )
        min_price = df['Close'].min()
        max_price = df['Close'].max()
        current_price = df['Close'][-1]
        subida = (max_price - current_price) / current_price * 100
        return {
            "Ticker": nombre,
            "Fuente": f"Investpy ({pais})",
            "Mínimo": round(min_price, 2),
            "Máximo": round(max_price, 2),
            "Actual": round(current_price, 2),
            "% Subida a Máx": round(subida, 2)
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
        resultado = None

        if not ES_CLOUD:
            resultado = analizar_con_yfinance(ticker_real)

        if not resultado and ALPHA_VANTAGE_API_KEY and not ES_CLOUD:
            resultado = analizar_con_alphavantage(ticker_real)

        if not resultado and raw_ticker.lower() in criptos_disponibles:
            resultado = analizar_con_coingecko(raw_ticker.lower())

        if not resultado:
            pais = pais_por_ticker.get(raw_ticker.upper(), 'brazil')
            resultado = analizar_con_investpy(raw_ticker.upper(), pais)

        info_fundamental = obtener_info_fundamental(ticker_real)

        if resultado:
            resultado.update(info_fundamental)
            resultados.append(resultado)
        else:
            resultado = {"Ticker": raw_ticker, "Error": "No se encontró información en ninguna fuente"}
            resultado.update(info_fundamental)
            resultados.append(resultado)

    df_result = pd.DataFrame(resultados)
    st.dataframe(df_result)
    csv = df_result.to_csv(index=False).encode('utf-8')
    st.download_button("Descargar resultados en CSV", data=csv, file_name="analisis_completo_activos.csv")
