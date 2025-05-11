import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime

st.title("Análisis de Activos Financieros")

st.write("Subí un archivo CSV con una columna llamada 'Ticker' (ej: AAPL, TSLA, GLEN.L, etc.)")

# Inputs de fecha
col1, col2 = st.columns(2)
with col1:
    fecha_inicio = st.date_input("Fecha de inicio", value=datetime(2010, 1, 1))
with col2:
    fecha_fin = st.date_input("Fecha de fin", value=datetime.today())

uploaded_file = st.file_uploader("Cargar archivo CSV", type=["csv"])

if uploaded_file:
    df_input = pd.read_csv(uploaded_file)
    resultados = []

    for ticker in df_input['Ticker']:
        try:
            data = yf.Ticker(ticker)
            hist = data.history(start=fecha_inicio, end=fecha_fin)

            if hist.empty:
                resultados.append({
                    "Ticker": ticker,
                    "Error": "No hay datos en el rango elegido"
                })
                continue

            min_price = hist['Close'].min()
            max_price = hist['Close'].max()
            current_price = hist['Close'][-1]
            subida = (max_price - current_price) / current_price * 100

            resultados.append({
                "Ticker": ticker,
                "Mínimo en rango": round(min_price, 2),
                "Máximo en rango": round(max_price, 2),
                "Precio actual": round(current_price, 2),
                "% subida hasta máx": round(subida, 2)
            })
        except Exception as e:
            resultados.append({
                "Ticker": ticker,
                "Error": str(e)
            })

    df_result = pd.DataFrame(resultados)
    st.dataframe(df_result)

    csv = df_result.to_csv(index=False).encode('utf-8')
    st.download_button("Descargar resultados en CSV", data=csv, file_name="analisis_activos_rango.csv")
