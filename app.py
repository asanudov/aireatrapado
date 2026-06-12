import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from fpdf import FPDF
import os

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

# CLASE GENERADORA DE PDF CON ESTILO INSTITUCIONAL (Basado en tu reporte de referencia)
class ReportePDF(FPDF):
    def header(self):
        # Header institucional
        if os.path.exists("logo.png"):
            self.image("logo.png", x=12, y=10, w=45)
        
        self.set_font("Arial", "B", 14)
        self.set_text_color(30, 58, 138) # Azul Oscuro Principal
        self.cell(0, 8, "Aquestia México", ln=1, align="R")
        
        self.set_font("Arial", "", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, "Reporte Técnico de Optimización Hidráulica", ln=1, align="R")
        
        # Línea divisoria elegante
        self.set_draw_color(220, 220, 220)
        self.set_line_width(0.5)
        self.line(12, 28, 198, 28)
        self.ln(12)

    def footer(self):
        # Pie de página
        self.set_y(-20)
        self.set_draw_color(220, 220, 220)
        self.set_line_width(0.5)
        self.line(12, self.get_y(), 198, self.get_y())
        self.ln(3)
        
        self.set_font("Arial", "I", 8)
        self.set_text_color(120, 120, 120)
        fecha_hoy = datetime.now().strftime("%d/%m/%Y")
        self.cell(0, 5, f"Diseñado por M.I. Alan Sañudo  |  Fecha de creación: {fecha_hoy}", ln=0, align="L")
        self.cell(0, 5, f"Página {self.page_no()}", ln=0, align="R")

# 2. BARRA LATERAL (SIDEBAR)
st.sidebar.title("Analizador de Aire Atrapado en Conductos a Presión")

if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = "file_uploader_v1"

uploaded_file = st.sidebar.file_uploader("Carga tu perfil en Excel o CSV", type=["xlsx", "csv"], key=st.session_state["uploader_key"])

if uploaded_file is not None:
    st.markdown("<div class='file-uploaded-active'></div>", unsafe_allow_html=True)
    if st.sidebar.button("🔄 Carga un archivo diferente", use_container_width=True):
        st.session_state["uploader_key"] = f"file_uploader_{np.random.randint(1000, 9999)}"
        st.rerun()

st.sidebar.markdown("---")
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

            if d_m < 0.100:
                st.warning("⚠️ **Nota técnica:** El diámetro ingresado es menor a 100 mm.")

            # CÁLCULOS HIDRÁULICOS
            parametro_sistema_sq = (q_m3s**2) / (g * (d_m**5)) if d_m > 0 else 0
            df['es_cresta'] = (df[col_z] > df[col_z].shift(1)) & (df[col_z] > df[col_z].shift(-1))
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
            df_sub_riesgo = df[df['riesgo_hidraulico']]
            UMBRAL_DELTA_H_CRITICO = 10.8

            if not df_sub_riesgo.empty:
                for grupo_id, data_grupo in df_sub_riesgo.groupby('grupo_riesgo'):
                    if data_grupo.index[0] < data_grupo.index[-1]:
                        delta_h_real = abs(data_grupo[col_z].max() - data_grupo[col_z].min())
                        if delta_h_real > UMBRAL_DELTA_H_CRITICO:
                            idx_centro = data_grupo.index[len(data_grupo) // 2]
                            df.loc[idx_centro, 'valvula_anticolapso'] = True

            # GRÁFICO PLOTLY
            st.subheader("Perfil Longitudinal del Acueducto")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df[col_x], y=df[col_z], mode='lines', name='Perfil de Tubería', line=dict(color='#1E40AF', width=2.5)))
            
            crestas = df[df['es_cresta']]
            fig.add_trace(go.Scatter(x=crestas[col_x], y=crestas[col_z], mode='markers', marker=dict(color='#F59E0B', size=11, symbol='triangle-up', line=dict(color='black', width=0.5)), name='Punto Alto Geométrico'))
            
            for i in range(1, len(df)):
                if df.loc[i, 'riesgo_hidraulico']:
                    fig.add_trace(go.Scatter(x=[df.loc[i-1, col_x], df.loc[i, col_x]], y=[df.loc[i-1, col_z], df.loc[i, col_z]], mode='lines', line=dict(color='#DC2626', width=4), showlegend=False))
            
            valvulas_activas = df[df['valvula_anticolapso']]
            if not valvulas_activas.empty:
                fig.add_trace(go.Scatter(x=valvulas_activas[col_x], y=valvulas_activas[col_z], mode='markers', marker=dict(color='#D946EF', size=7, symbol='square', line=dict(color='black', width=0.5)), name='Válvula Intermedia Anticolapso'))

            fig.update_layout(xaxis_title="Distancia (m)", yaxis_title="Elevación (m)", height=450, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"))
            st.plotly_chart(fig, use_container_width=True)

            # TABLA DE RESULTADOS FILTRADA
            st.subheader("Reporte General de Dispositivos de Aire Propuestos")
            res_table = df[(df['es_cresta']) | (df['valvula_anticolapso'])].copy()
            
            if not res_table.empty:
                condiciones = [res_table['valvula_anticolapso'], res_table['es_cresta']]
                elecciones = ["Válvula intermedia anticolapso", "Punto Alto Geométrico"]
                res_table['Diagnóstico del Aire'] = np.select(condiciones, elecciones, default="Dispositivo")
                res_table['V. Flujo (m/s)'] = round(v_real, 3)
                res_table['V. Mínima Barrido (m/s)'] = np.where(res_table['S'] > 0, round(res_table['v_critica'], 3), 0.000)
                res_table['Pendiente (S)'] = round(res_table['S'].fillna(0), 4)
                
                res_table = res_table.sort_values(by=col_x).reset_index(drop=True)
                res_table['No. de Válvula'] = res_table.index + 1
                
                res_table_renamed = res_table.rename(columns={col_x: "Distancia (m)", col_z: "Elevación (m)"})
                output_cols = ['No. de Válvula', 'Distancia (m)', 'Elevación (m)', 'Pendiente (S)', 'Diagnóstico del Aire', 'V. Flujo (m/s)', 'V. Mínima Barrido (m/s)']
                
                st.dataframe(res_table_renamed[output_cols], use_container_width=True, hide_index=True)
                
                # ---- CONCLUSIÓN GENERAL ----
                st.subheader("Conclusión General del Sistema")
                total_crestas = len(crestas)
                total_intermedias = len(valvulas_activas)
                
                texto_conclusion = f"""El análisis del perfil revela la existencia de {total_crestas} punto(s) alto(s) geométrico(s) principales donde es mandatoria la instalación de purgadores por flotación natural. Con respecto a los tramos de pendiente descendente crítica evaluados mediante el criterio cinético de la UNAM, se identificó riesgo latente de acumulación y bolsas atrapadas debido a que la velocidad real de operación ({v_real:.3f} m/s) se encuentra por debajo de la velocidad mínima de barrido calculada. Aplicando el filtro de deformación por descompresión de Hohai University, únicamente {total_intermedias} de los tramos críticos superan el umbral de delta H de {UMBRAL_DELTA_H_CRITICO} m, requiriendo de manera estricta una válvula de aire intermedia para mitigar el riesgo de colapso secundario por ruptura."""
                st.write(texto_conclusion)

                # =========================================================
                # BOOTSTRAP DEL BOTÓN DE GENERACIÓN DE REPORTE PDF
                # =========================================================
                st.markdown("---")
                if st.button("📄 Generar y Descargar Reporte PDF Institucional", use_container_width=True):
                    with st.spinner("Compilando reporte vectorial..."):
                        # 1. Exportar gráfico dinámicamente como imagen temporal
                        fig.update_layout(height=400, width=800)
                        fig.write_image("temp_perfil.png", engine="kaleido")
                        
                        # 2. Inicializar PDF
                        pdf = ReportePDF(orientation='P', unit='mm', format='A4')
                        pdf.set_margins(12, 12, 12)
                        pdf.add_page()
                        
                        # Título del Reporte
                        pdf.set_font("Arial", "B", 15)
                        pdf.set_text_color(40, 40, 40)
                        pdf.cell(0, 10, "REPORTE DE DIMENSIONAMIENTO Y DISPOSITIVOS DE AIRE", ln=1)
                        pdf.ln(2)
                        
                        # Tabla resumida de Datos de Entrada (Igual al estilo Dorot adjunto)
                        pdf.set_font("Arial", "B", 11)
                        pdf.set_fill_color(240, 243, 248) # Gris azulado claro institucional
                        pdf.set_text_color(30, 58, 138)
                        pdf.cell(0, 7, " 1. Parámetros Generales de Diseño", ln=1, fill=True)
                        pdf.ln(2)
                        
                        pdf.set_font("Arial", "", 10)
                        pdf.set_text_color(50, 50, 50)
                        pdf.cell(60, 6, "Caudal de diseño (Q):", border="B")
                        pdf.cell(40, 6, f"{q_m3s:.3f} m³/s", border="B", ln=1)
                        pdf.cell(60, 6, "Diámetro interno de conducción:", border="B")
                        pdf.cell(40, 6, f"{d_m:.3f} m", border="B", ln=1)
                        pdf.cell(60, 6, "Velocidad media del flujo:", border="B")
                        pdf.cell(40, 6, f"{v_real:.3f} m/s", border="B", ln=1)
                        pdf.cell(60, 6, "Parámetro adimensional [Q²/(g·D⁵)]:", border="B")
                        pdf.cell(40, 6, f"{parametro_sistema_sq:.5f}", border="B", ln=1)
                        pdf.ln(6)
                        
                        # Sección de Gráfico
                        pdf.set_font("Arial", "B", 11)
                        pdf.cell(0, 7, " 2. Perfil Longitudinal y Ubicación de Dispositivos", ln=1, fill=True)
                        pdf.ln(2)
                        if os.path.exists("temp_perfil.png"):
                            pdf.image("temp_perfil.png", x=15, w=180)
                            pdf.ln(5)
                        
                        # Sección de Tabla Resumen
                        pdf.set_font("Arial", "B", 11)
                        pdf.cell(0, 7, " 3. Tabla Resumen de Dispositivos de Aire Propuestos", ln=1, fill=True)
                        pdf.ln(3)
                        
                        # Encabezados de Tabla Física
                        pdf.set_font("Arial", "B", 8.5)
                        pdf.set_text_color(255, 255, 255)
                        pdf.set_fill_color(30, 58, 138) # Encabezado azul oscuro
                        
                        headers = ["No.", "Dist. (m)", "Elev. (m)", "Pend. (S)", "Diagnóstico", "V. Real", "V. Barrido"]
                        widths = [10, 20, 20, 20, 68, 22, 22]
                        
                        for h, w in zip(headers, widths):
                            pdf.cell(w, 7, h, border=1, align="C", fill=True)
                        pdf.ln()
                        
                        # Filas de la Tabla
                        pdf.set_font("Arial", "", 8)
                        pdf.set_text_color(50, 50, 50)
                        
                        for _, row in res_table_renamed.iterrows():
                            pdf.cell(10, 6, str(int(row['No. de Válvula'])), border=1, align="C")
                            pdf.cell(20, 6, f"{row['Distancia (m)']:.1f}", border=1, align="R")
                            pdf.cell(20, 6, f"{row['Elevación (m)']:.2f}", border=1, align="R")
                            pdf.cell(20, 6, f"{row['Pendiente (S)']:.4f}", border=1, align="R")
                            pdf.cell(68, 6, f" {row['Diagnóstico del Aire']}", border=1, align="L")
                            pdf.cell(22, 6, f"{row['V. Flujo (m/s)']:.2f}", border=1, align="C")
                            pdf.cell(22, 6, f"{row['V. Mínima Barrido (m/s)']:.2f}", border=1, align="C", ln=1)
                        
                        pdf.ln(6)
                        
                        # Sección de Conclusiones
                        pdf.set_font("Arial", "B", 11)
                        pdf.set_text_color(30, 58, 138)
                        pdf.cell(0, 7, " 4. Conclusiones y Recomendaciones Técnicas", ln=1, fill=True)
                        pdf.ln(2)
                        pdf.set_font("Arial", "", 9.5)
                        pdf.set_text_color(40, 40, 40)
                        pdf.multi_cell(0, 5, texto_conclusion)
                        
                        # Guardar archivo en disco temporal
                        pdf_filename = f"Reporte_Valvulas_Aire_{datetime.now().strftime('%Y%m%d')}.pdf"
                        pdf.output(pdf_filename)
                        
                        # Leer archivo para entregarlo al botón de Streamlit
                        with open(pdf_filename, "rb") as f:
                            st.download_button(
                                label="💾 ¡PDF Listo! Da clic aquí para descargar tu archivo",
                                data=f,
                                file_name=pdf_filename,
                                mime="application/pdf",
                                use_container_width=True
                            )
                        
                        # Limpieza de archivos temporales de imagen
                        if os.path.exists("temp_perfil.png"):
                            os.remove("temp_perfil.png")

            else:
                st.success("✅ El sistema opera con estabilidad. No hay datos que exportar.")

        else:
            st.error("❌ Formato inválido.")
    except Exception as e:
        st.error(f"Error al procesar: {e}")
