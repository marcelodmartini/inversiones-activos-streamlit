import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime
from pycoingecko import CoinGeckoAPI
import investpy
import os
from alpha_vantage.timeseries import TimeSeries
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import re
import warnings
from datetime import datetime, time

st.title("Análisis de Activos Financieros con Fallback Inteligente y Múltiples Fuentes")
st.write("Subí un archivo CSV con una columna llamada 'Ticker' (ej: AAPL, BTC, AL30D, etc.)")

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

if not ALPHA_VANTAGE_API_KEY:
    st.warning("⚠️ No se encontró la clave de Alpha Vantage en `st.secrets`.")
if not FINNHUB_API_KEY:
    st.warning("⚠️ No se encontró la clave de Finnhub en `st.secrets`.")
if not FMP_API_KEY:
    st.warning("⚠️ No se encontró la clave de FMP en `st.secrets`.")


def es_bono_argentino(ticker):
    return bool(re.match(r"^(AL|GD|TX|TV|AE|TB)[0-9]+[D]?$", ticker.upper()))

# FUNCIONES IAMC/BYMA ------------------------
def obtener_precio_bono_iamc(ticker):
    # Esta función simula lectura desde un archivo CSV descargado manualmente de IAMC
    # Podés automatizar esto con pandas.read_csv desde un path local o remoto
    try:
        iamc_path = "./iamc_cotizaciones.csv"  # debe existir con columnas: 'Ticker', 'Precio'
        df = pd.read_csv(iamc_path)
        row = df[df['Ticker'].str.upper() == ticker.upper()]
        if row.empty:
            return None
        current_price = float(row.iloc[0]['Precio'])
        return {
            "Ticker": ticker,
            "Actual": round(current_price, 2),
            "Fuente": "IAMC (archivo local)"
        }
    except Exception as e:
        errores_conexion.append(f"[IAMC] {ticker}: {e}")
        print(f"[ERROR] IAMC falló para {ticker} - {e}")
        return None

def obtener_precio_bono_byma(ticker):
    try:
        url = f"https://www.byma.com.ar/mercado/cotizaciones"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            errores_conexion.append(f"[BYMA] {ticker}: status {r.status_code}")
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        tablas = soup.find_all("table")
        for tabla in tablas:
            if ticker.upper() in tabla.text.upper():
                rows = tabla.find_all("tr")
                for row in rows:
                    if ticker.upper() in row.text.upper():
                        cols = row.find_all("td")
                        if len(cols) >= 2:
                            try:
                                precio = float(cols[1].text.strip().replace("$", "").replace(",", "."))
                                return {
                                    "Ticker": ticker,
                                    "Actual": round(precio, 2),
                                    "Fuente": "BYMA (scraping web)"
                                }
                            except:
                                continue
        errores_conexion.append(f"[BYMA] {ticker}: no se encontró en tablas")
        return None
    except Exception as e:
        errores_conexion.append(f"[BYMA] {ticker}: {e}")
        print(f"[ERROR] BYMA falló para {ticker} - {e}")
        return None

def obtener_precio_bono_rava(ticker):
    global errores_conexion
    try:
        t.sleep(1.5)
        url = f"https://www.rava.com/perfil/{ticker}/historial"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/113.0.0.0"
        }
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200 or "Forbidden" in r.text:
            errores_conexion.append(f"[Rava] {ticker}: {r.status_code} - Acceso denegado")
            return obtener_precio_bono_iamc(ticker) or obtener_precio_bono_byma(ticker)
        soup = BeautifulSoup(r.text, 'html.parser')
        tabla = soup.find("table")
        if not tabla:
            errores_conexion.append(f"[Rava] {ticker}: tabla no encontrada")
            return obtener_precio_bono_iamc(ticker) or obtener_precio_bono_byma(ticker)
        rows = tabla.find_all("tr")[1:]
        precios = []
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 5:
                try:
                    cierre = float(cols[4].text.strip().replace("$", "").replace(",", "."))
                    precios.append(cierre)
                except:
                    continue
        if not precios:
            errores_conexion.append(f"[Rava] {ticker}: no se extrajo ningún precio")
            return obtener_precio_bono_iamc(ticker) or obtener_precio_bono_byma(ticker)
        min_price = min(precios)
        max_price = max(precios)
        current_price = precios[-1]
        subida = (max_price - current_price) / current_price * 100
        return {
            "Ticker": ticker,
            "Actual": round(current_price, 2),
            "Mínimo": round(min_price, 2),
            "Máximo": round(max_price, 2),
            "% Subida a Máx": round(subida, 2),
            "Fuente": "Rava Bursátil (Historial)"
        }
    except Exception as e:
        errores_conexion.append(f"[Rava] {ticker}: {e}")
        print(f"[ERROR] Rava falló para {ticker} - {e}")
        st.text(f"DEBUG: Rava falló para {ticker} - {e}")
        return obtener_precio_bono_iamc(ticker) or obtener_precio_bono_byma(ticker)


# Función de cálculo de score

def calcular_score(resultado):
    if resultado.get("Tipo") == "Bono":
        return "N/A", 0

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

# Mapeo de países y tickers

pais_por_ticker = {
    "SUPV": "argentina", "BBAR": "argentina", "PAMP": "argentina",
    "YPFD": "argentina", "TGSU2": "argentina", "FALABELLA": "chile",
    "CEMEXCPO": "mexico", "EC": "colombia", "EMBR3": "brazil"
}

ticker_map = {
    "YPFD": "YPF.BA", "TGSU2": "TGSU2.BA", "MIRG": "MIRG.BA", "VISTA": "VIST",
    "FALABELLA": "FALABELLA.CL", "CEMEXCPO": "CEMEXCPO.MX", "OM:STIL": "STIL.ST", "HLSE:ETTE": "ETTE.HE"
}

# Función de obtención de info fundamental

def obtener_info_fundamental(ticker):
    es_bono = es_bono_argentino(ticker)
    resultado = {
        "País": None, "PEG Ratio": None, "P/E Ratio": None, "P/B Ratio": None,
        "ROE": None, "ROIC": None, "FCF Yield": None, "Debt/Equity": None,
        "EV/EBITDA": None, "Dividend Yield": None, "Beta": None,
        "Contexto": None, "Semáforo Riesgo": "ROJO", "Tipo": "Bono" if es_bono else "Acción"
    }

    try:
        tkr = yf.Ticker(ticker)
        if hasattr(tkr, "info") and isinstance(tkr.info, dict):
            info = tkr.info
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
                "Contexto": info.get("longBusinessSummary")
            })
            if resultado.get("PEG Ratio") is None:
                pe = info.get("trailingPE")
                growth = info.get("earningsQuarterlyGrowth") or info.get("earningsGrowth")
                if pe and growth and growth != 0:
                    resultado["PEG Ratio"] = round(pe / (growth * 100), 2)
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
            resultado["FCF Yield"] = data.get("freeCashFlowYieldAnnual") or resultado["FCF Yield"]
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
                    "FCF Yield": data.get("freeCashFlowYield") or resultado["FCF Yield"]
                })
    except Exception as e:
        print(f"[fmp] {ticker} -> {e}")

    if resultado.get("Contexto"):
        try:
            resultado["Contexto"] = GoogleTranslator(source='auto', target='es').translate(resultado["Contexto"])
        except Exception as e:
            print(f"[traducción] {ticker} -> {e}")

    indicadores_clave = ["PEG Ratio", "P/E Ratio", "P/B Ratio", "ROE", "FCF Yield", "Beta"]
    completos = sum([1 for k in indicadores_clave if resultado.get(k) is not None])
    resultado["Cobertura"] = f"{completos}/{len(indicadores_clave)}"

    if resultado["Tipo"] == "Bono":
        indicadores_clave = ["Dividend Yield", "Beta", "P/B Ratio"]
        completos = sum([1 for k in indicadores_clave if resultado.get(k) is not None])
        resultado["Cobertura"] = f"{completos}/{len(indicadores_clave)}"
    if completos == 0:
        resultado["Advertencia"] = "⚠️ Solo precio disponible, sin métricas fundamentales"
    return resultado

def analizar_con_yfinance(ticker):
    global errores_conexion
    try:
        data = yf.Ticker(ticker)
        hist = data.history(start=fecha_inicio, end=fecha_fin)
        if hist.empty:
            return None
        min_price = hist['Close'].min()
        max_price = hist['Close'].max()
        current_price = hist['Close'].iloc[-1]
        subida = (max_price - current_price) / current_price * 100
        return {
            "Ticker": ticker, "Fuente": "Yahoo Finance",
            "Mínimo": round(min_price, 2), "Máximo": round(max_price, 2),
            "Actual": round(current_price, 2), "% Subida a Máx": round(subida, 2)
        }
    except Exception as e:
        errores_conexion.append(f"[Yahoo Finance] {ticker}: {e}")
        print(f"[ERROR] Yahoo Finance falló para {ticker} - {e}")
        warnings.warn(f"DEBUG: Yahoo Finance falló para {ticker} - {e}")
        st.text(f"DEBUG: Yahoo Finance falló para {ticker} - {e}")


def analizar_con_alphavantage(ticker):
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
        errores_conexion.append(f"[Alpha Vantage] {ticker}: {e}")
        print(f"[ERROR] Alpha Vantage falló para {ticker} - {e}")
        warnings.warn(f"DEBUG: Alpha Vantage falló para {ticker} - {e}")
        st.text(f"DEBUG: Alpha Vantage falló para {ticker} - {e}")


def analizar_con_coingecko(coin_id):
    global errores_conexion
    try:
        # Convertir fecha_inicio y fecha_fin de date a datetime (para usar .timestamp)
        fecha_inicio_dt = datetime.combine(fecha_inicio, time.min)
        fecha_fin_dt = datetime.combine(fecha_fin, time.min)

        data = cg.get_coin_market_chart_range_by_id(
            id=coin_id,
            vs_currency='usd',
            from_timestamp=int(fecha_inicio_dt.timestamp()),
            to_timestamp=int(fecha_fin_dt.timestamp())
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
    except Exception as e:
        errores_conexion.append(f"[CoinGecko] {coin_id}: {e}")
        print(f"[ERROR] CoinGecko falló para {coin_id} - {e}")
        warnings.warn(f"DEBUG: CoinGecko falló para {coin_id} - {e}")
        st.text(f"DEBUG: CoinGecko falló para {coin_id} - {e}")



def analizar_con_investpy(nombre, pais):
    global errores_conexion
    try:
        fecha_inicio_dt = datetime.combine(fecha_inicio, time.min)
        fecha_fin_dt = datetime.combine(fecha_fin, time.min)

        df = investpy.get_stock_historical_data(
            stock=nombre,
            country=pais,
            from_date=fecha_inicio_dt.strftime('%d/%m/%Y'),
            to_date=fecha_fin_dt.strftime('%d/%m/%Y')
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
    except Exception as e:
        errores_conexion.append(f"[Investpy] {nombre}: {e}")
        print(f"[ERROR] Investpy falló para {nombre} - {e}")
        warnings.warn(f"DEBUG: Investpy falló para {nombre} - {e}")
        st.text(f"DEBUG: Investpy falló para {nombre} - {e}")




errores_conexion = []
if uploaded_file:
    df_input = pd.read_csv(uploaded_file)
    if 'Ticker' not in df_input.columns:
        st.error("El archivo CSV debe contener una columna llamada 'Ticker'")
        st.stop()

    resultados = []
    criptos_disponibles = [c['id'] for c in cg.get_coins_list()]

    with st.spinner("Analizando activos..."):
        for raw_ticker in df_input['Ticker']:
            if pd.isna(raw_ticker) or str(raw_ticker).strip() == "":
                continue
            fuentes_probadas = []
            print(f"\n🔎 Analizando: {raw_ticker}")
            raw_ticker = str(raw_ticker).strip()
            ticker_real = ticker_map.get(raw_ticker.upper(), raw_ticker)
            ticker_clean = raw_ticker.upper()
            es_bono = es_bono_argentino(ticker_clean)
            resultado = None

            if not ES_CLOUD:
                try:
                    print(f"[INFO] Intentando con Yahoo Finance: {ticker_real}")
                    fuentes_probadas.append("Yahoo Finance")
                    resultado = analizar_con_yfinance(ticker_real)
                except Exception as e:
                    errores_conexion.append(f"[Yahoo Finance] {ticker_clean}: {e}")
                    print(f"[ERROR] Yahoo Finance falló para {ticker_clean} - {e}")

            if not resultado and ALPHA_VANTAGE_API_KEY and not ES_CLOUD:
                try:
                    print(f"[INFO] Intentando con Alpha Vantage: {ticker_clean}")
                    fuentes_probadas.append("Alpha Vantage")
                    resultado = analizar_con_alphavantage(ticker_clean)
                except Exception as e:
                    errores_conexion.append(f"[Alpha Vantage] {ticker_clean}: {e}")
                    print(f"[ERROR] Alpha Vantage falló para {ticker_clean} - {e}")

            if not resultado and raw_ticker.lower() in criptos_disponibles:
                try:
                    print(f"[INFO] Intentando con CoinGecko: {raw_ticker.lower()}")
                    fuentes_probadas.append("CoinGecko")
                    resultado = analizar_con_coingecko(raw_ticker.lower())
                except Exception as e:
                    errores_conexion.append(f"[CoinGecko] {raw_ticker.lower()}: {e}")
                    print(f"[ERROR] CoinGecko falló para {raw_ticker.lower()} - {e}")
                    st.text(f"DEBUG: CoinGecko falló para {raw_ticker.lower()} - {e}")

            if not resultado:
                try:
                    pais = pais_por_ticker.get(raw_ticker.upper(), 'brazil')
                    print(f"[INFO] Intentando con Investpy ({pais}): {ticker_clean}")
                    fuentes_probadas.append(f"Investpy ({pais})")
                    resultado = analizar_con_investpy(ticker_clean, pais)
                except Exception as e:
                    errores_conexion.append(f"[Investpy] {ticker_clean}: {e}")
                    print(f"[ERROR] Investpy falló para {ticker_clean} - {e}")

            if not resultado and es_bono:
                try:
                    print(f"[INFO] Intentando scraping Rava para bono: {ticker_clean}")
                    fuentes_probadas.append("Rava")
                    precio_rava = obtener_precio_bono_rava(ticker_clean)
                    if precio_rava:
                        resultado = precio_rava
                        resultado["Tipo"] = "Bono"
                        resultado["Advertencia"] = "⚠️ Solo precio disponible, sin métricas fundamentales"
                except Exception as e:
                    errores_conexion.append(f"[Rava] {ticker_clean}: {e}")
                    print(f"[ERROR] Rava falló para {ticker_clean} - {e}")
                    warnings.warn(f"DEBUG: Rava falló para {ticker_clean} - {e}")
                    st.text(f"DEBUG: Rava falló para {ticker_clean} - {e}")


            if resultado:
                resultado["Fuente"] = resultado.get("Fuente", "No informada")
                resultado["Fuentes Probadas"] = ", ".join(fuentes_probadas)
            else:
                resultado = {"Ticker": raw_ticker, "Error": "❌ No se encontró información en ninguna fuente",
                            "Fuente": "Ninguna", "Fuentes Probadas": ", ".join(fuentes_probadas),
                            "Advertencia": "⚠️ No se encontró información", "Tipo": "Desconocido"}

            info_fundamental = obtener_info_fundamental(ticker_clean)

            if resultado:
                for k, v in info_fundamental.items():
                    if k not in ["Tipo", "Fuente", "Advertencia", "Error"] and (k not in resultado or resultado[k] is None):
                        resultado[k] = v
            else:
                resultado = info_fundamental
                resultado["Ticker"] = raw_ticker
                resultado["Error"] = "No se encontró información en ninguna fuente"


            score_texto, score_numerico = calcular_score(resultado)
            resultado["Score Final"] = score_texto
            resultado["__orden_score"] = score_numerico

            resultados.append(resultado)

    df_result = pd.DataFrame(resultados)

    columnas = df_result.columns.tolist()
    for col in ["Score Final", "Semáforo Riesgo"]:
        if col in columnas:
            columnas.insert(0, columnas.pop(columnas.index(col)))

    for extra_col in ["Tipo", "Advertencia", "Error", "Fuente", "Fuentes Probadas"]:
        if extra_col in columnas and extra_col not in columnas:
            columnas.append(extra_col)

    df_result = df_result[columnas]
    if "Advertencia" not in df_result.columns:
        df_result["Advertencia"] = ""
    else:
        df_result["Advertencia"] = df_result["Advertencia"].fillna("")


    df_result = df_result.sort_values("__orden_score", ascending=False).drop(columns="__orden_score")

    def resaltar_riesgo(val):
        if not val or not isinstance(val, str):
            return ""
        color = {
            "VERDE": "#c8e6c9",
            "AMARILLO": "#fff9c4",
            "ROJO": "#ffcdd2"
        }.get(val.upper(), "#eeeeee")
        return f"background-color: {color}; font-weight: bold"


    styled_df = df_result.style.applymap(resaltar_riesgo, subset=["Semáforo Riesgo"])
    st.dataframe(styled_df, use_container_width=True)

    if errores_conexion:
        st.warning("⚠️ Errores de conexión detectados:")
        for err in errores_conexion:
            st.text(err)



    csv = df_result.to_csv(index=False).encode('utf-8')
    st.download_button("Descargar resultados en CSV", data=csv, file_name="analisis_completo_activos.csv")

