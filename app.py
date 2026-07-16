import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from fpdf import FPDF
import os
from scipy.signal import find_peaks

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Analizador de Aire Atrapado", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; padding-bottom: 0rem; padding-left: 2rem; padding-right: 2rem; }
    h1 { font-size: 1.8rem !important; font-weight: 700; color: #1E3A8A; }
    .discreet-note { font-size: 11px; color: #888; margin-top: 30px; border-top: 1px solid #eee; padding-top: 10px; }
    </style>
""", unsafe_allow_html=True)

# CLASE GENERADORA DE PDF
class ReportePDF(FPDF):
    def header(self):
        self.set_fill_color(30, 58, 138)
        self.rect(0, 0, 210, 32, "F")
        self.ln(24)

    def footer(self):
        self.set_y(-20)
        self.set_font("Arial", "I", 8)
        self.cell(0, 5, f"Generado: {datetime.now().strftime('%d/%m/%Y')}", align="C")

# 2. BARRA LATERAL
st.sidebar.title("Configuración")

# Selector de archivos
uploaded_file = st.sidebar.file_uploader("Carga tu perfil en Excel o CSV", type=["xlsx", "csv"])

# --- NOTA SOBRE EL FORMATO (SOLICITUD INTEGRADA) ---
st.sidebar.markdown("""
<div style="background-color: #eef2f7; padding: 12px; border-radius: 5px; font-size: 0.85rem; border: 1px solid #d1d9e6;">
    <strong>ℹ️ Instrucciones del archivo:</strong><br>
    Tu archivo debe tener dos columnas:<br>
    1. <code>x</code>: Distancia (cadenamiento).<br>
    2. <code>y</code>: Elevación (cota).<br><br>
    * Asegúrate de usar punto (.) como separador decimal.
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
nombre_acueducto = st.sidebar.text_input("Nombre del Acueducto", value="Línea Troncal")
q_input = st.sidebar.text_input("Caudal (m³/s)", value="0.075")
d_input = st.sidebar.text_input("Diámetro Interno (m)", value="0.305")

try:
    q_m3s = float(q_input)
    d_m = float(d_input)
except:
    q_m3s, d_m = 0.075, 0.305

# 3. LÓGICA PRINCIPAL
st.title("Analizador de Aire Atrapado")

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        df.columns = [c.lower().strip() for c in df.columns]
        # Identificar columnas automáticamente
        col_x = next((c for c in df.columns if c in ['cadenamiento', 'distancia', 'x']), None)
        col_z = next((c for c in df.columns if c in ['elevación', 'elevacion', 'y']), None)

        if col_x and col_z:
            df = df.sort_values(by=col_x).reset_index(drop=True)
            g = 9.81
            
            # FILTRO TOPOGRÁFICO: Prominencia > Diámetro (Criterio estricto)
            picos_idx, _ = find_peaks(df[col_z], prominence=d_m)
            df['es_cresta'] = False
            df.loc[picos_idx, 'es_cresta'] = True

            # CÁLCULOS HIDRÁULICOS
            df['dx'] = df[col_x].diff()
            df['dz'] = df[col_z].diff()
            df['S'] = -df['dz'] / df['dx'].replace(0, np.nan)
            
            parametro_sistema_sq = (q_m3s**2) / (g * (d_m**5))
            df['parametro_critico'] = np.where(df['S'] > 0, 0.35 * df['S'].fillna(0) + 0.18, 0.0)
            df['riesgo_hidraulico'] = (df['S'] > 0) & (parametro_sistema_sq < df['parametro_critico'])
            
            # --- CORRECCIÓN ROBUSTA PARA KEYERROR ---
            df['grupo_riesgo'] = (df['riesgo_hidraulico'] != df['riesgo_hidraulico'].shift()).cumsum()
            df_sub_riesgo = df[df['riesgo_hidraulico']].copy()
            
            df['valvula_anticolapso'] = False
            UMBRAL_DELTA_H = 10.8
            
            if not df_sub_riesgo.empty:
                for grupo_id, data_grupo in df_sub_riesgo.groupby('grupo_riesgo'):
                    if abs(data_grupo[col_z].max() - data_grupo[col_z].min()) > UMBRAL_DELTA_H:
                        idx_centro = data_grupo.index[len(data_grupo) // 2]
                        df.loc[idx_centro, 'valvula_anticolapso'] = True

            # GRÁFICA
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df[col_x], y=df[col_z], mode='lines', name='Perfil'))
            fig.add_trace(go.Scatter(x=df[df['es_cresta']][col_x], y=df[df['es_cresta']][col_z], mode='markers', name='Crestas'))
            st.plotly_chart(fig, use_container_width=True)

            # TABLA
            res_table = df[(df['es_cresta']) | (df['valvula_anticolapso'])].copy()
            st.dataframe(res_table[[col_x, col_z, 'es_cresta', 'valvula_anticolapso']])
            
            if st.button("Generar Reporte PDF"):
                st.info("Función de PDF lista para integrar.")
        else:
            st.error("No se encontraron columnas válidas 'x' o 'y'.")
            
    except Exception as e:
        st.error(f"Error procesando archivo: {e}")
else:
    st.info("👈 Por favor, carga un archivo para comenzar.")
