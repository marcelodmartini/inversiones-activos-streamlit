# helpers/byma.py
import requests
from bs4 import BeautifulSoup

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