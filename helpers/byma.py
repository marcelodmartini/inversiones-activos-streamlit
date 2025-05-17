# helpers/byma.py
import requests
from bs4 import BeautifulSoup

def obtener_precio_bono_bymadata(symbol):
    """Consulta la API pública BYMA Open Data sin autenticación."""
    try:
        url = f"https://api.bymadata.com.ar/v1/mercados/bonos/{symbol.upper()}"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()

        actual = float(data.get("ultimoPrecio", 0))
        minimo = float(data.get("precioMinimo", 0))
        maximo = float(data.get("precioMaximo", 0))
        subida = round((maximo - actual) / actual * 100, 2) if actual > 0 else None

        return {
            "Ticker": symbol.upper(),
            "Actual": round(actual, 2),
            "Mínimo": round(minimo, 2),
            "Máximo": round(maximo, 2),
            "% Subida a Máx": subida,
            "Fuente": "BYMA Open Data API pública"
        }
    except Exception as e:
        print(f"[BYMA API] Error con {symbol}: {e}")
        return None

def obtener_precio_bono_scraping(symbol):
    """Fallback con scraping clásico de la web de BYMA."""
    try:
        url = "https://www.byma.com.ar/mercado/cotizaciones"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)

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
                                    "Fuente": "BYMA (scraping web)"
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
    """Consulta con fallback: API pública -> Scraping clásico."""
    print(f"[BYMA] 🔍 Buscando datos para {symbol}")
    resultado = obtener_precio_bono_bymadata(symbol)
    if resultado:
        return resultado

    print(f"[BYMA] ⚠️ Fallback a scraping web para {symbol}")
    return obtener_precio_bono_scraping(symbol)
