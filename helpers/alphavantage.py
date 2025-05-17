from alpha_vantage.timeseries import TimeSeries
from datetime import datetime, time
import pandas as pd
from config import ALPHA_VANTAGE_API_KEY
import warnings


def analizar_con_alphavantage(ticker, fecha_inicio, fecha_fin):
    global errores_conexion
    try:
        ts = TimeSeries(key=ALPHA_VANTAGE_API_KEY, output_format='pandas')

        fecha_inicio_dt = datetime.combine(fecha_inicio, time.min)
        fecha_fin_dt = datetime.combine(fecha_fin, time.min)

        data, meta = ts.get_daily_adjusted(symbol=ticker, outputsize='full')
        data = data.sort_index()
        data = data[(data.index >= pd.to_datetime(fecha_inicio_dt)) & (data.index <= pd.to_datetime(fecha_fin_dt))]

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
    except Exception as e:
        print(f"[Alpha Vantage] {ticker}: {e}")
        print(f"[ERROR] Alpha Vantage falló para {ticker} - {e}")
        warnings.warn(f"DEBUG: Alpha Vantage falló para {ticker} - {e}")