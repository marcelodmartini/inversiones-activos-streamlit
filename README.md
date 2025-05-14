# Análisis de Activos Financieros con Fallback Inteligente y Score Unificado

Esta app desarrollada en Streamlit permite analizar acciones, criptomonedas y activos bursátiles de múltiples países y fuentes, generando una grilla con indicadores financieros clave, semáforo de riesgo y un **score final del 1 al 5** que evalúa la calidad de inversión de cada activo.

## 📥 ¿Cómo usar?
1. Subí un archivo `.csv` con una columna `Ticker` (ej: AAPL, BTC, GLEN.L, PETR4.SA).
2. Elegí la fecha de inicio y fin del análisis.
3. La app consultará automáticamente a las siguientes fuentes:
   - Yahoo Finance
   - Alpha Vantage
   - CoinGecko
   - Investpy
   - Finnhub
   - Financial Modeling Prep (FMP)

## 📊 Indicadores calculados
Para cada activo, la app obtiene y calcula los siguientes indicadores fundamentales:

- PEG Ratio
- P/E Ratio
- P/B Ratio
- ROE
- ROIC
- FCF Yield
- Debt/Equity
- EV/EBITDA
- Dividend Yield
- Beta
- País
- Contexto actual de la empresa (traducido al español)

## 🚦 Semáforo de Riesgo
Basado en el valor del **Beta**:

| Semáforo   | Condición         | Significado              |
|------------|-------------------|---------------------------|
| 🟢 VERDE   | Beta ≤ 1          | Riesgo bajo              |
| 🟡 AMARILLO| 1 < Beta ≤ 1.5     | Riesgo moderado          |
| 🔴 ROJO    | Beta > 1.5        | Riesgo alto              |

## 🧮 Score Financiero Final (1 a 5)
Un indicador compuesto que sintetiza la salud financiera del activo. Se calcula con 10 métricas clave. El puntaje se traduce así:

| Score | Nivel      | Descripción                        |
|--------|------------|------------------------------------|
| 5/5    | Excelente | Alta calidad, baja deuda, alto potencial de crecimiento
| 4/5    | Muy bueno | Muy buenos fundamentos, leve riesgo
| 3/5    | Aceptable | Correcto, pero con advertencias
| 2/5    | Riesgoso  | Débil en fundamentos o volátil
| 1/5    | Débil     | Mala calidad financiera

### 🎯 Fórmula de cálculo:
Por cada condición cumplida se suma 1 punto (máx 10 puntos):

- ✅ Beta ≤ 1
- ✅ Debt/Equity < 1
- ✅ EV/EBITDA < 15
- ✅ ROE > 10%
- ✅ ROIC > 8%
- ✅ PEG Ratio < 1.5
- ✅ FCF Yield > 5%
- ✅ P/E Ratio < 20
- ✅ P/B Ratio < 3
- ✅ Dividend Yield > 2%

Luego:
- **9–10 puntos → 5/5**
- **7–8 → 4/5**
- **5–6 → 3/5**
- **3–4 → 2/5**
- **0–2 → 1/5**

## 📤 Resultados
- Grilla interactiva con colores por riesgo.
- Score final visible.
- Botón para descargar CSV completo.

## 📦 Requisitos (`requirements.txt`)
```txt
streamlit
yfinance
pandas
investpy
requests
pycoingecko
alpha_vantage
deep-translator
```

## 🔐 Variables en `.streamlit/secrets.toml`
```toml
ALPHA_VANTAGE_API_KEY = "..."
FINNHUB_API_KEY = "..."
FMP_API_KEY = "..."
```

## 🧪 Opcional
Podés expandir el modelo para incluir:
- Inteligencia artificial sobre `Contexto`
- Ranking por sectores o países
- Históricos de evolución de score

---
Hecho con ❤️ y múltiples APIs por [marcelodmartini]
