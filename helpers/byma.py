# helpers/byma.py
import requests
from bs4 import BeautifulSoup
import json
import os
import time
from playwright.sync_api import sync_playwright
import pandas as pd

CACHE_PATH = "/tmp/byma_cache"
CACHE_TTL = 600  # segundos (10 minutos)

os.makedirs(CACHE_PATH, exist_ok=True)

def obtener_cache(symbol):
    path = os.path.join(CACHE_PATH, f"{symbol.upper()}.json")
    if os.path.exists(path):
        mtime = os.path.getmtime(path)
        if time.time() - mtime < CACHE_TTL:
            with open(path, "r") as f:
                return json.load(f)
    return None

def guardar_cache(symbol, data):
    path = os.path.join(CACHE_PATH, f"{symbol.upper()}.json")
    with open(path, "w") as f:
        json.dump(data, f)

def obtener_precio_bono_bymadata(symbol):
    print(f"[INFO] Consulta la API pública BYMA Open Data sin autenticación.")
    try:
        cached = obtener_cache(symbol)
        if cached:
            print(f"[BYMA API] Usando cache local para {symbol}")
            return cached

        url = f"https://api.bymadata.com.ar/v1/marketdata/bonds/detail?symbol={symbol.upper()}"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10, verify=False)
        r.raise_for_status()
        data = r.json()

        precios = data.get("prices", {})
        actual = float(precios.get("last", 0))
        minimo = float(precios.get("min", 0))
        maximo = float(precios.get("max", 0))
        subida = round((maximo - actual) / actual * 100, 2) if actual > 0 else None

        result = {
            "Ticker": symbol.upper(),
            "Actual": round(actual, 2),
            "Mínimo": round(minimo, 2),
            "Máximo": round(maximo, 2),
            "% Subida a Máx": subida,
            "Fuente": "BYMA Open Data",
            "Hist": None  # No se provee histórico en esta API
        }

        guardar_cache(symbol, result)
        return result

    except Exception as e:
        print(f"[BYMA API] Error con {symbol}: {e}")
        return None

def obtener_precio_bono_playwright(symbol):
    print(f"[INFO] Fallback con Playwright desde open.bymadata.com.ar para {symbol}")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            page.goto(f"https://open.bymadata.com.ar/#/technical-detail-bond?symbol={symbol.upper()}&settlementType=2", timeout=30000)
            page.wait_for_selector("text=Precio Último", timeout=10000)

            precio_texto = page.locator("//div[contains(text(),'Precio Último')]/following-sibling::div").first.inner_text().strip().replace("$", "").replace(",", ".")
            precio = float(precio_texto)

            # Obtener histórico desde tabla
            rows = page.locator(".technical-detail__chart-container + div table tr").all()
            datos = []
            for row in rows[1:]:
                cols = row.locator("td").all()
                if len(cols) >= 2:
                    fecha = cols[0].inner_text().strip()
                    cierre = cols[1].inner_text().strip().replace("$", "").replace(",", ".")
                    try:
                        datos.append({"Fecha": fecha, "Close": float(cierre)})
                    except:
                        continue
            df_hist = pd.DataFrame(datos)
            df_hist["Fecha"] = pd.to_datetime(df_hist["Fecha"], dayfirst=True, errors='coerce')
            df_hist = df_hist.dropna().set_index("Fecha").sort_index()

            result = {
                "Ticker": symbol.upper(),
                "Actual": round(precio, 2),
                "Fuente": "BYMA (Playwright Web)",
                "Hist": df_hist.reset_index().to_dict(orient="list") if not df_hist.empty else None
            }
            browser.close()
            return result
    except Exception as e:
        print(f"[BYMA Playwright] Error para {symbol}: {e}")
        return None

def obtener_precio_bono_scraping(symbol):
    print(f"[INFO] Fallback con scraping clásico de la web de BYMA.")
    try:
        url = "https://www.byma.com.ar/mercado/cotizaciones"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10, verify=False)

        if r.status_code != 200:
            print(f"[BYMA Scraping] Error HTTP {r.status_code} para {symbol}")
            return None

        soup = BeautifulSoup(r.text, "html.parser")
        tablas = soup.find_all("table")

        for tabla in tablas:
            if symbol.upper() in tabla.text.upper():
                rows = tabla.find_all("tr")
                for row in rows:
                    if symbol.upper() in row.text.upper():
                        cols = row.find_all("td")
                        if len(cols) >= 2:
                            try:
                                precio_texto = cols[1].text.strip().replace("$", "").replace(",", ".")
                                precio = float(precio_texto)
                                return {
                                    "Ticker": symbol.upper(),
                                    "Actual": round(precio, 2),
                                    "Fuente": "BYMA (scraping web)",
                                    "Hist": hist  # 👉 agregado para el gráfico histórico
                                }
                            except Exception as e:
                                print(f"[BYMA Scraping] Error parsing {symbol}: {e}")
                                continue

        print(f"[BYMA Scraping] {symbol} no encontrado en tablas")
        return None

    except Exception as e:
        print(f"[BYMA Scraping] Excepción general para {symbol}: {e}")
        return None

def obtener_precio_bono_byma(symbol):
    """Consulta con fallback: API pública -> Playwright -> Scraping clásico."""
    print(f"[BYMA] 🔍 Buscando datos para {symbol}")
    resultado = obtener_precio_bono_bymadata(symbol)
    if resultado:
        return resultado

    print(f"[BYMA] ⚠️ Fallback a scraping con Playwright para {symbol}")
    resultado = obtener_precio_bono_playwright(symbol)
    if resultado:
        return resultado

    print(f"[BYMA] ⚠️ Fallback final a scraping web tradicional para {symbol}")
    return obtener_precio_bono_scraping(symbol)
