import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime
from pycoingecko import CoinGeckoAPI
import investpy

st.title("Análisis de Activos Financieros con Fallback Inteligente")

st.write("Subí un archivo CSV con una columna llamada 'Ticker' (ej: AAPL, BTC, GLEN.L, PETR4.SA, etc.)")

col1, col2 = st.columns(2)
with col1:
    fecha_inicio = st.date_input("Fecha de inicio", value=datetime(2010, 1, 1))
with col2:
    fecha_fin = st.date_input("Fecha de fin", value=datetime.today())

uploaded_file = st.file_uploader("Cargar archivo CSV", type=["csv"])

cg = CoinGeckoAPI()

# Funciones auxiliares

def analizar_con_yfinance(ticker):
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

    for raw_ticker in df_input['Ticker']:
        raw_ticker = str(raw_ticker).strip()
        resultado = analizar_con_yfinance(raw_ticker)

        if not resultado and raw_ticker.lower() in ['btc', 'eth', 'bnb', 'sol', 'ada']:
            resultado = analizar_con_coingecko(raw_ticker.lower())

        if not resultado:
            resultado = analizar_con_investpy(raw_ticker.upper(), 'brazil')  # ejemplo con Brasil como fallback

        if resultado:
            resultados.append(resultado)
        else:
            resultados.append({"Ticker": raw_ticker, "Error": "No se encontró información en ninguna fuente"})

    df_result = pd.DataFrame(resultados)
    st.dataframe(df_result)
    csv = df_result.to_csv(index=False).encode('utf-8')
    st.download_button("Descargar resultados en CSV", data=csv, file_name="analisis_completo_activos.csv")
