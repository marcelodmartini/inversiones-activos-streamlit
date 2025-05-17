import matplotlib.pyplot as plt
import streamlit as st
import pandas as pd
import numpy as np


def graficar_precio_historico(nombre, df):
    if not isinstance(df, pd.DataFrame):
        st.warning(f"No hay datos válidos para {nombre}.")
        return

    if 'Close' not in df.columns or 'Fecha' not in df.columns:
        st.warning(f"Faltan columnas necesarias ('Close', 'Fecha') para {nombre}.")
        return

    if df.empty:
        st.warning(f"No hay datos disponibles para {nombre}.")
        return

    try:
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        df = df.dropna(subset=['Fecha']).set_index('Fecha').sort_index()
    except Exception as e:
        st.warning(f"Error procesando fechas para {nombre}: {e}")
        return

    st.line_chart(df[["Close"]])

    fig, ax = plt.subplots()
    df['Close'].plot(ax=ax, label='Precio Cierre', linewidth=2)
    ax.axhline(df['Close'].iloc[-1], color='red', linestyle='--', label='Precio Actual')
    ax.set_title(f'Histórico de precios: {nombre}')
    ax.set_xlabel('Fecha')
    ax.set_ylabel('Precio')
    ax.legend()
    st.pyplot(fig)


def graficar_radar_scores(nombre, scores_dict):
    if not scores_dict or not isinstance(scores_dict, dict):
        st.warning(f"No hay métricas suficientes para el radar financiero de {nombre}.")
        return

    labels = list(scores_dict.keys())
    values = [scores_dict.get(k, 0) for k in labels]
    num_vars = len(labels)

    if num_vars < 3:
        st.warning(f"Se requieren al menos 3 métricas para generar un radar financiero de {nombre}.")
        return

    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    values += values[:1]  # cerrar el gráfico
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.plot(angles, values, color='blue', linewidth=2)
    ax.fill(angles, values, color='skyblue', alpha=0.25)
    ax.set_yticklabels([])
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_title(f'Score Financiero: {nombre}')

    st.pyplot(fig)


def graficar_subida_maximo(nombre, actual, maximo):
    if actual is None or maximo is None:
        st.info(f"No hay datos para calcular la subida a máximo de {nombre}.")
        return
    try:
        actual = float(actual)
        maximo = float(maximo)
        if actual == 0:
            return
        subida = (maximo - actual) / actual * 100
        st.metric(label=f"% Subida a Máximo ({nombre})", value=f"{subida:.2f}%")
    except:
        st.warning(f"No se pudo calcular la subida a máximo para {nombre}.")
