# 📊 Análisis de Activos Financieros con Fallback Inteligente

Esta aplicación de Streamlit permite analizar múltiples activos financieros (acciones, criptomonedas, ETFs) y calcular:

- Precio mínimo histórico (en un rango elegido)
- Precio máximo histórico
- Precio actual
- % de subida al máximo

Funciona incluso si los datos no están disponibles en la fuente principal (`yfinance`), gracias al uso de múltiples fuentes alternativas como CoinGecko e Investpy.

---

## 🚀 ¿Qué hace?

🔍 Intenta encontrar información del activo usando:

1. Yahoo Finance (`yfinance`)
2. CoinGecko (`pycoingecko`) – solo para criptomonedas como BTC, ETH, SOL, ADA
3. Investing.com (`investpy`) – fallback para acciones internacionales, con soporte de países como Brasil, México, Argentina, etc.

---

## 📥 Cómo usar

### Requisitos

```bash
pip install -r requirements.txt
