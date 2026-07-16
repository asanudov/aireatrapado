import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from fpdf import FPDF
import os
from scipy.signal import find_peaks
import google.generativeai as genai # 1. Importación necesaria

# --- CONFIGURACIÓN API IA ---
# Configura Gemini (Toma el secreto de Streamlit automáticamente)
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error("Error al configurar la IA. Asegúrate de definir GOOGLE_API_KEY en los secrets.")

def generar_conclusion_ia(nombre, q, d, longitud, total_crestas, total_intermedias, v_real, umbral_h):
    """Función que genera la conclusión técnica mediante IA."""
    prompt = f"""
    Eres un experto Ingeniero Hidráulico. Redacta una conclusión técnica profesional, 
    concisa y objetiva para un reporte de aire en acueductos.
    
    Datos del proyecto:
    - Nombre del Acueducto: {nombre}
    - Caudal: {q} m3/s, Diámetro: {d} m, Longitud: {longitud} m
    - Puntos altos (crestas) detectados: {total_crestas}
    - Válvulas intermedias anticolapso requeridas: {total_intermedias}
    - Velocidad real del flujo: {v_real} m/s
    - Umbral de descompresión (Hohai): {umbral_h} m
    
    Instrucciones de redacción:
    1. Menciona brevemente que el análisis sigue criterios de AWWA y CONAGUA.
    2. Si 'total_intermedias' > 0, explica el riesgo de colapso secundario y la necesidad de válvulas.
    3. Si 'total_intermedias' == 0, enfatiza que el sistema opera con estabilidad.
    4. Usa un tono técnico, formal y directo.
    5. Máximo 150 palabras. No incluyas frases de introducción como "Aquí está la conclusión".
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception:
        return "El análisis del acueducto se realizó bajo criterios AWWA/CONAGUA. Se detectaron puntos altos y riesgos de descompresión que requieren atención técnica según los cálculos presentados."

# --- CONFIGURACIÓN DE PÁGINA Y ESTILOS ---
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
        if os.path.exists("logo.png"):
            self.image("logo.png", x=12, y=6, w=48)
        self.ln(24)

    def footer(self):
        self.set_y(-20)
        self.set_draw_color(220, 220, 220)
        self.line(12, self.get_y(), 198, self.get_y())
        self.set_font("Arial", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 5, f"Disenado por M.I. Alan Sanudo | Fecha: {datetime.now().strftime('%d/%m/%Y')}", align="L")
        self.cell(0, 5, f"Pagina {self.page_no()}", align="R")

# --- INTERFAZ ---
st.sidebar.title("Analizador de Aire Atrapado")
# ... (Tu lógica de carga de archivo se mantiene igual) ...
uploaded_file = st.sidebar.file_uploader("Carga tu perfil", type=["xlsx", "csv"])

nombre_acueducto = st.sidebar.text_input("Nombre del Acueducto", value="Línea Troncal Norte")
q_input = st.sidebar.text_input("Caudal (m³/s)", value="0.075")
d_input = st.sidebar.text_input("Diámetro Interno (m)", value="0.305")

# --- PROCESAMIENTO ---
if uploaded_file:
    # ... (Tus cálculos de pandas, find_peaks, etc. se mantienen igual hasta la parte de conclusión) ...
    # (Asumimos que aquí ya tienes las variables: nombre_acueducto, q_m3s, d_m, longitud_total, total_crestas, total_intermedias, v_real, UMBRAL_DELTA_H_CRITICO)
    
    # [AQUÍ VA EL BLOQUE QUE REEMPLAZAMOS]
    st.subheader("Conclusión General del Sistema")
    
    # 2. LLAMADA A LA IA
    with st.spinner("La IA está redactando la conclusión técnica profesional..."):
        texto_conclusion = generar_conclusion_ia(
            nombre_acueducto, 
            q_m3s, 
            d_m, 
            longitud_total, 
            len(df[df['es_cresta']]), 
            len(df[df['valvula_anticolapso']]), 
            v_real, 
            10.8 # UMBRAL_DELTA_H_CRITICO
        )
    
    st.info(texto_conclusion) # Muestra en pantalla

    # --- COMPILACIÓN DEL PDF ---
    if st.button("📄 Generar y Descargar Reporte PDF Institucional", use_container_width=True):
        # ... (Tu código de creación de imagen y PDF se mantiene igual) ...
        # Solo asegúrate de que al pasar el texto al PDF usas la variable 'texto_conclusion':
        # pdf.multi_cell(0, 5, texto_conclusion)
        
        # [PDF generation code here...]
        pass

# --- FOOTER ---
st.markdown("""
<div class="discreet-note">
    Fuentes técnicas: Instituto de Ingeniería UNAM, IWA Publishing, Journal of Fluid Mechanics.
</div>
""", unsafe_allow_html=True)
