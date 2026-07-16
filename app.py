import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from fpdf import FPDF
import os
from scipy.signal import find_peaks

# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS BASE
st.set_page_config(page_title="Analizador de Aire Atrapado", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; padding-bottom: 0rem; padding-left: 2rem; padding-right: 2rem; }
    h1 { font-size: 1.8rem !important; font-weight: 700; color: #1E3A8A; }
    .discreet-note { font-size: 11px; color: #888; margin-top: 30px; border-top: 1px solid #eee; padding-top: 10px; }
    
    /* SIDEBAR COMPACTO */
    [data-testid="stSidebar"] h1 { font-size: 1.2rem !important; line-height: 1.3; margin-bottom: 0.1rem !important; }
    [data-testid="stSidebarUserContent"] { padding-top: 0.8rem !important; padding-bottom: 0.3rem !important; }
    [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] > div > [data-testid="stVerticalBlock"] { gap: 0.1rem !important; }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div { padding-bottom: 0.05rem !important; padding-top: 0.05rem !important; }
    [data-testid="stSidebar"] .stTextInput label { margin-bottom: 0.05rem !important; }
    [data-testid="stSidebar"] hr { margin-top: 0.3rem !important; margin-bottom: 0.3rem !important; }

    /* OCULTAR UPLOADER AL CARGAR */
    .file-uploaded-active [data-testid="stFileUploaderDropzone"] { display: none !important; }
    </style>
""", unsafe_allow_html=True)

# CLASE GENERADORA DE PDF CON BANDA AZUL DE CONTRASTE PARA EL LOGO
class ReportePDF(FPDF):
    def header(self):
        # Dibujar una banda azul marino superior de fondo para albergar el logo blanco
        self.set_fill_color(30, 58, 138) # Azul Oscuro de Aquestia
        self.rect(0, 0, 210, 32, "F")
        
        # Colocar el logo blanco encima de la banda azul
        if os.path.exists("logo.png"):
            self.image("logo.png", x=12, y=6, w=48)
        
        self.ln(24) # Ajustar el cursor de dibujo abajo de la banda

    def footer(self):
        self.set_y(-20)
        self.set_draw_color(220, 220, 220)
        self.set_line_width(0.5)
        self.line(12, self.get_y(), 198, self.get_y())
        self.ln(3)
        
        self.set_font("Arial", "I", 8)
        self.set_text_color(120, 120, 120)
        fecha_hoy = datetime.now().strftime("%d/%m/%Y")
        self.cell(0, 5, f"Disenado por M.I. Alan Sanudo  |  Fecha de creacion: {fecha_hoy}", ln=0, align="L")
        self.cell(0, 5, f"Pagina {self.page_no()}", ln=0, align="R")

# 2. BARRA LATERAL (SIDEBAR)
st.sidebar.title("Analizador de Aire Atrapado en Conductos a Presión")

if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = "file_uploader_v1"

uploaded_file = st.sidebar.file_uploader("Carga tu perfil en Excel o CSV", type=["xlsx", "csv"], key=st.session_state["uploader_key"])

# --- CAMBIO 1: NOTA INFORMATIVA ---
st.sidebar.markdown("""
<div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; font-size: 0.8rem; border: 1px solid #d1d9e6;">
    <strong>ℹ️ Instrucciones del CSV:</strong><br>
    - Columnas: <code>x</code> (distancia), <code>y</code> (elevación).<br>
    - Separador: Coma (,).<br>
    - Decimal: Punto (.).
</div>
""", unsafe_allow_html=True)

if uploaded_file is not None:
    st.markdown("<div class='file-uploaded-active'></div>", unsafe_allow_html=True)
    if st.sidebar.button("🔄 Carga un archivo diferente", use_container_width=True):
        st.session_state["uploader_key"] = f"file_uploader_{np.random.randint(1000, 9999)}"
        st.rerun()

st.sidebar.markdown("---")
# Campos de entrada de datos generales
nombre_acueducto = st.sidebar.text_input("Nombre del Acueducto", value="Línea Troncal Norte")
q_input = st.sidebar.text_input("Caudal (m³/s)", value="0.075")
d_input = st.sidebar.text_input("Diámetro Interno (m)", value="0.305")

try:
    q_m3s = float(q_input) if q_input else 0.000
    d_m = float(d_input) if d_input else 0.010
except ValueError:
    st.sidebar.error("Valores numéricos inválidos.")
    q_m3s, d_m = 0.075, 0.305

st.sidebar.markdown("---")
st.sidebar.write("**Desarrollado por: M.I. Alan Sañudo**")

# 3. CUERPO PRINCIPAL
st.title("Analizador de Aire Atrapado en Conductos a Presión")

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        df.columns = [c.lower().strip() for c in df.columns]
        col_x = next((c for c in df.columns if c in ['cadenamiento', 'distancia', 'x']), None)
        col_z = next((c for c in df.columns if c in ['elevación', 'elevacion', 'y']), None)

        if col_x and col_z:
            g = 9.81
            df[col_x] = pd.to_numeric(df[col_x])
            df[col_z] = pd.to_numeric(df[col_z])
            df = df.sort_values(by=col_x).reset_index(drop=True)

            # Cómputo de la longitud total del acueducto basada en el trazo físico
            longitud_total = df[col_x].max() - df[col_x].min()

            if d_m < 0.100:
                st.warning("⚠️ **Nota técnica:** El diámetro ingresado es menor a 100 mm.")

            # CÁLCULOS HIDRÁULICOS
            parametro_sistema_sq = (q_m3s**2) / (g * (d_m**5)) if d_m > 0 else 0
            
            # --- CAMBIO 2: FILTRO DE CRESTAS POR PROMINENCIA ---
            picos_idx, _ = find_peaks(df[col_z], prominence=d_m)
            df['es_cresta'] = False
            df.loc[picos_idx, 'es_cresta'] = True
            
            df['dx'] = df[col_x].diff()
            df['dz'] = df[col_z].diff()
            df['S'] = -df['dz'] / df['dx'].replace(0, np.nan)
            
            df['parametro_critico'] = np.where(df['S'] > 0, 0.35 * df['S'].fillna(0) + 0.18, 0.0)
            df['riesgo_hidraulico'] = (df['S'] > 0) & (parametro_sistema_sq < df['parametro_critico'])
            df['v_critica'] = np.where(df['S'] > 0, (4 / np.pi) * np.sqrt((0.35 * df['S'].fillna(0) + 0.18) * g * d_m), 0.0)
            
            area = np.pi * (d_m**2) / 4 if d_m > 0 else 1
            v_real = q_m3s / area

            # CRITERIO FILTRO DINÁMICO (HOHAI)
            df['valvula_anticolapso'] = False
            df['grupo_riesgo'] = (df['riesgo_hidraulico'] != df['riesgo_hidraulico'].shift()).cumsum()
            df_sub_
