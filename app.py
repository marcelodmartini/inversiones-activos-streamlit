import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime
from pycoingecko import CoinGeckoAPI
import investpy
import os
from alpha_vantage.timeseries import TimeSeries

st.title("Análisis de Activos Financieros con Fallback Inteligente y Múltiples Fuentes")

st.write("Subí un archivo CSV con una columna llamada 'Ticker' (ej: AAPL, BTC, GLEN.L, PETR4.SA, etc.)")

col1, col2 = st.columns(2)
with col1:
    fecha_inicio = st.date_input("Fecha de inicio", value=datetime(2010, 1, 1))
with col2:
    fecha_fin = st.date_input("Fecha de fin", value=datetime.today())

uploaded_file = st.file_uploader("Cargar archivo CSV", type=["csv"])

cg = CoinGeckoAPI()

# Detectar si estamos en Streamlit Cloud
ES_CLOUD = os.environ.get("STREAMLIT_SERVER_HEADLESS", "") == "1"

# Obtener API Key de Alpha Vantage desde secrets (o hardcoded para entorno local)
ALPHA_VANTAGE_API_KEY = st.secrets["ALPHA_VANTAGE_API_KEY"] if "ALPHA_VANTAGE_API_KEY" in st.secrets else os.getenv("ALPHA_VANTAGE_API_KEY", "")

# Mapeo de tickers a países para Investpy
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

# Funciones auxiliares

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
        resultado = None

        # Usar yfinance solo si NO estamos en la nube
        if not ES_CLOUD:
            resultado = analizar_con_yfinance(raw_ticker)

        # Si falla y tenemos Alpha Vantage Key, intentar
        if not resultado and ALPHA_VANTAGE_API_KEY and not ES_CLOUD:
            resultado = analizar_con_alphavantage(raw_ticker)

        # Si es una cripto disponible en CoinGecko
        if not resultado and raw_ticker.lower() in criptos_disponibles:
            resultado = analizar_con_coingecko(raw_ticker.lower())

        # Si todo falla, intentar con Investpy según país mapeado
        if not resultado:
            pais = pais_por_ticker.get(raw_ticker.upper(), 'brazil')
            resultado = analizar_con_investpy(raw_ticker.upper(), pais)

        if resultado:
            resultados.append(resultado)
        else:
            resultados.append({"Ticker": raw_ticker, "Error": "No se encontró información en ninguna fuente"})

    df_result = pd.DataFrame(resultados)
    st.dataframe(df_result)
    csv = df_result.to_csv(index=False).encode('utf-8')
    st.download_button("Descargar resultados en CSV", data=csv, file_name="analisis_completo_activos.csv")
