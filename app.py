import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS BASE
st.set_page_config(page_title="Analizador de Aire Atrapado", layout="wide")

# CSS personalizado: Máxima amplitud horizontal y optimización vertical del sidebar
st.markdown("""
    <style>
    /* Optimización del contenedor principal */
    .block-container { padding-top: 1.5rem; padding-bottom: 0rem; padding-left: 2rem; padding-right: 2rem; }
    h1 { font-size: 1.8rem !important; font-weight: 700; color: #1E3A8A; }
    .discreet-note { font-size: 11px; color: #888; margin-top: 30px; border-top: 1px solid #eee; padding-top: 10px; }
    
    /* ---- OPTIMIZACIÓN VERTICAL ULTRA-COMPACTA DEL SIDEBAR ---- */
    [data-testid="stSidebar"] h1 { font-size: 1.2rem !important; line-height: 1.3; margin-bottom: 0.1rem !important; }
    
    /* Reducir el espaciado superior interno del sidebar */
    [data-testid="stSidebarUserContent"] { padding-top: 0.8rem !important; padding-bottom: 0.3rem !important; }
    
    /* Eliminar gaps por defecto entre los bloques del sidebar */
    [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] > div > [data-testid="stVerticalBlock"] {
        gap: 0.1rem !important;
    }
    
    /* Compactar la separación entre cada widget */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div {
        padding-bottom: 0.05rem !important;
        padding-top: 0.05rem !important;
    }
    
    /* Forzar márgenes mínimos en las etiquetas de los inputs */
    [data-testid="stSidebar"] .stTextInput label {
        margin-bottom: 0.05rem !important;
    }
    
    /* Ajustar las líneas divisorias */
    [data-testid="stSidebar"] hr {
        margin-top: 0.3rem !important;
        margin-bottom: 0.3rem !important;
    }

    /* ---- OCULTAR EL CONTENEDOR DE ARCHIVOS SI YA ESTÁ CARGADO ---- */
    .file-uploaded-active [data-testid="stFileUploaderDropzone"] div {
        display: none !important;
    }
    .file-uploaded-active [data-testid="stFileUploaderDropzone"] + div {
        display: none !important;
    }
    .file-uploaded-active [data-testid="stFileUploaderDropzone"] {
        display: none !important;
    }
    </style>
""", unsafe_allow_html=True)

# 2. BARRA LATERAL (SIDEBAR) - Estructura Visual
st.sidebar.title("Analizador de Aire Atrapado en Conductos a Presión")

if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = "file_uploader_v1"

# A. Cargador de archivos en la parte superior
uploaded_file = st.sidebar.file_uploader(
    "Carga tu perfil en Excel o CSV", 
    type=["xlsx", "csv"],
    key=st.session_state["uploader_key"]
)

if uploaded_file is not None:
    st.markdown("<div class='file-uploaded-active'></div>", unsafe_allow_html=True)
    
    if st.sidebar.button("🔄 Carga un archivo diferente", use_container_width=True):
        st.session_state["uploader_key"] = f"file_uploader_{np.random.randint(1000, 9999)}"
        st.rerun()

st.sidebar.markdown("---")

# B. Entradas numéricas abajo de la carga
q_input = st.sidebar.text_input("Caudal (m³/s)", value="0.075")
d_input = st.sidebar.text_input("Diámetro Interno (m)", value="0.305")

try:
    q_m3s = float(q_input) if q_input else 0.000
    d_m = float(d_input) if d_input else 0.010
except ValueError:
    st.sidebar.error("Por favor, introduce valores numéricos válidos para Caudal y Diámetro.")
    q_m3s, d_m = 0.075, 0.305

st.sidebar.markdown("---")

# C. Instrucciones de formato para el archivo
st.sidebar.info("""
**Instrucciones de formato del archivo:**
1. Debe contener dos columnas.
2. Cada una con un encabezado.
3. Para la primera columna, el encabezado debe decir "Cadenamiento", "Distancia" o "X".
4. Para la segunda columna, debe decir "Elevación" o "Y".
5. Los números deben ser metros.
""")

st.sidebar.markdown("---")
st.sidebar.write("**Desarrollado por: M.I. Alan Sañudo**")

# 3. CUERPO PRINCIPAL DE LA APLICACIÓN
st.title("Analizador de Aire Atrapado en Conductos a Presión")

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        # Normalización estricta de nombres de columnas
        df.columns = [c.lower().strip() for c in df.columns]
        
        # Mapeo por prioridades de los encabezados válidos
        col_x = next((c for c in df.columns if c in ['cadenamiento', 'distancia', 'x']), None)
        col_z = next((c for c in df.columns if c in ['elevación', 'elevacion', 'y']), None)

        if col_x and col_z:
            g = 9.81
            
            # Asegurar ordenamiento físico por distancia
            df[col_x] = pd.to_numeric(df[col_x])
            df[col_z] = pd.to_numeric(df[col_z])
            df = df.sort_values(by=col_x).reset_index(drop=True)

            if d_m < 0.100:
                st.warning("⚠️ **Nota técnica:** El diámetro ingresado es menor a 100 mm (4 pulgadas). En tuberías pequeñas, los efectos de tensión superficial y capilaridad pueden alterar el comportamiento del aire respecto al modelo matemático de arrastre hidráulico por gravedad.")

            # ---- MOTOR DE CÁLCULO: METODOLOGÍA GRAFICA II-UNAM [Q²/(g*D⁵)] ----
            parametro_sistema_sq = (q_m3s**2) / (g * (d_m**5)) if d_m > 0 else 0
            
            df['es_cresta'] = (df[col_z] > df[col_z].shift(1)) & (df[col_z] > df[col_z].shift(-1))
            
            df['dx'] = df[col_x].diff()
            df['dz'] = df[col_z].diff()
            df['S'] = -df['dz'] / df['dx'].replace(0, np.nan)
            
            df['parametro_critico'] = np.where(df['S'] > 0, 0.35 * df['S'].fillna(0) + 0.18, 0.0)
            df['riesgo_hidraulico'] = (df['S'] > 0) & (parametro_sistema_sq < df['parametro_critico'])
            
            df['v_critica'] = np.where(
                df['S'] > 0,
                (4 / np.pi) * np.sqrt((0.35 * df['S'].fillna(0) + 0.18) * g * d_m),
                0.0
            )
            
            area = np.pi * (d_m**2) / 4 if d_m > 0 else 1
            v_real = q_m3s / area

            # ---- CRITERIO HOHAI UNIVERSITY: EVALUACIÓN DEL DELTA H MÁXIMO EN EL TRAMO ----
            df['valvula_anticolapso'] = False
            
            # Agrupación de bloques contiguos de riesgo
            df['grupo_riesgo'] = (df['riesgo_hidraulico'] != df['riesgo_hidraulico'].shift()).cumsum()
            df_sub_riesgo = df[df['riesgo_hidraulico']]
            
            # Constantes físicas del artículo (Vacío de vaporización HD + presión residual del suelo h)
            UMBRAL_DELTA_H_CRITICO = 10.8  # metros (10.33m + 0.5m)

            if not df_sub_riesgo.empty:
                for grupo_id, data_grupo in df_sub_riesgo.groupby('grupo_riesgo'):
                    idx_inicio = data_grupo.index[0]
                    idx_fin = data_grupo.index[-1]
                    
                    if idx_inicio < idx_fin:
                        # Calcular la diferencia de elevación máxima absoluta dentro de este tramo específico
                        z_max_tramo = data_grupo[col_z].max()
                        z_min_tramo = data_grupo[col_z].min()
                        delta_h_real = abs(z_max_tramo - z_min_tramo)
                        
                        # FILTRO FÍSICO: Solo proponer válvula si el desnivel real supera el umbral de cavitación/colapso
                        if delta_h_real > UMBRAL_DELTA_H_CRITICO:
                            idx_centro = data_grupo.index[len(data_grupo) // 2]
                            df.loc[idx_centro, 'valvula_anticolapso'] = True

            # 4. COMPONENTE GRÁFICO (MÁXIMA AMPLITUD HORIZONTAL)
            st.subheader("Perfil Longitudinal del Acueducto")
            fig = go.Figure()

            # Trazado base de la tubería
            fig.add_trace(go.Scatter(
                x=df[col_x], y=df[col_z], 
                mode='lines', 
                name='Perfil de Tubería', 
                line=dict(color='#1E40AF', width=2.5)
            ))

            # Marcadores geométricos de Puntos Altos
            crestas = df[df['es_cresta']]
            fig.add_trace(go.Scatter(
                x=crestas[col_x], y=crestas[col_z], 
                mode='markers', 
                marker=dict(color='#F59E0B', size=12, symbol='triangle-up', line=dict(color='black', width=1)),
                name='Punto alto, acumulación por flotación'
            ))

            # Resaltar en rojo grueso para los tramos con arrastre insuficiente
            for i in range(1, len(df)):
                if df.loc[i, 'riesgo_hidraulico']:
                    fig.add_trace(go.Scatter(
                        x=[df.loc[i-1, col_x], df.loc[i, col_x]], 
                        y=[df.loc[i-1, col_z], df.loc[i, col_z]],
                        mode='lines', 
                        line=dict(color='#DC2626', width=4.5),
                        name='Tramo Crítico: Arrastre Insuficiente' if i == df['riesgo_hidraulico'].idxmax() else "",
                        showlegend=(i == df['riesgo_hidraulico'].idxmax())
                    ))

            # Añadir las válvulas intermedias que pasaron el filtro (Cuadrado fucsia, tamaño 5)
            valvulas_activas = df[df['valvula_anticolapso']]
            if not valvulas_activas.empty:
                fig.add_trace(go.Scatter(
                    x=valvulas_activas[col_x], y=valvulas_activas[col_z],
                    mode='markers',
                    marker=dict(color='#D946EF', size=5, symbol='square', line=dict(color='black', width=0.5)),
                    name='Válvula de aire intermedia para evitar colapso'
                ))

            # Layout optimizado: Forzado de leyendas al eje inferior
            fig.update_layout(
                xaxis_title="Distancia (m)", 
                yaxis_title="Elevación (m)", 
                height=550,
                margin=dict(l=10, r=10, t=20, b=10),
                legend=dict(
                    orientation="h",
                    yanchor="top",
                    y=-0.18, 
                    xanchor="center",
                    x=0.5
                ),
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)

            # 5. MATRIZ DE RESULTADOS / REPORTES (FILTRADA SOLO PARA MOSTRAR DISPOSITIVOS)
            st.subheader("Reporte General de Dispositivos de Aire Propuestos")
            
            # FILTRO EXCLUSIVO: Crestas o Válvulas Intermedias Anticolapso
            res_table = df[(df['es_cresta']) | (df['valvula_anticolapso'])].copy()
            
            if not res_table.empty:
                # Jerarquía para definir el diagnóstico
                condiciones = [
                    res_table['valvula_anticolapso'],
                    res_table['es_cresta']
                ]
                elecciones = [
                    "Válvula de aire intermedia para evitar colapso",
                    "Punto Alto Geométrico (Bolsa Permanente)"
                ]
                res_table['Diagnóstico del Aire'] = np.select(condiciones, elecciones, default="Dispositivo")

                res_table['V. Flujo (m/s)'] = round(v_real, 3)
                res_table['V. Mínima Barrido (m/s)'] = np.where(res_table['S'] > 0, round(res_table['v_critica'], 3), 0.000)
                res_table['Pendiente (S)'] = round(res_table['S'].fillna(0), 4)
                
                # ---- ASIGNACIÓN DE CONSECUTIVO SERIAL (1 a n) ----
                res_table = res_table.sort_values(by=col_x).reset_index(drop=True)
                res_table['No. de Válvula'] = res_table.index + 1
                
                # Reorganización final de columnas con renombrado limpio
                res_table = res_table.rename(columns={col_x: "Distancia (m)", col_z: "Elevación (m)"})
                output_cols = ['No. de Válvula', 'Distancia (m)', 'Elevación (m)', 'Pendiente (S)', 'Diagnóstico del Aire', 'V. Flujo (m/s)', 'V. Mínima Barrido (m/s)']
                
                st.dataframe(
                    res_table[output_cols], 
                    use_container_width=True,
                    hide_index=True  # Oculta los índices internos redundantes del DataFrame
                )
                
                st.metric(label="Parámetro de Gasto Adimensional [Q²/(g·D⁵)] del Sistema", value=f"{parametro_sistema_sq:.5f}")
            else:
                st.success("✅ El sistema opera con estabilidad. No se detectaron puntos altos ni tramos que requieran válvulas de aire.")

        else:
            st.error("❌ Formato inválido. Asegúrate de que las columnas del archivo sigan estrictamente las instrucciones de la barra lateral.")
    except Exception as e:
        st.error(f"Error al leer o procesar el archivo cargado: {e}")
else:
    st.info("👈 Por favor, ingresa tu archivo de perfil (.csv o .xlsx) y configura las variables en el menú lateral para iniciar el análisis hidráulico.")

# 6. BIBLIOGRAFÍA DE RESPALDO INSTITUCIONAL
st.markdown("""
<div class="discreet-note">
    <strong>Fuentes técnicas e institucionales de referencia:</strong><br>
    • Instituto de Ingeniería, UNAM. <em>Manual de análisis de la problemática del aire atrapado en acueductos, para mejorar su eficiencia.</em> Serie Manuales, México.<br>
    • Wang, Y., Zhang, J., et al. (2023). <em>Air valve arrangement criteria for preventing secondary pipe bursts in long-distance gravitational water supply systems.</em> AQUA - Water Infrastructure, Ecosystems and Society, Vol 72 No 8, 1566. IWA Publishing.<br>
    • Kalinske, A. A., & Bliss, P. H. (1943). <em>Removal of air from pipe lines by flowing water.</em> Civil Engineering, 13(10).<br>
    • Zukoski, E. E. (1966). <em>Influence of viscosity, surface tension and inclination on motion of long bubbles in closed tubes.</em> Journal of Fluid Mechanics.
</div>
""", unsafe_allow_html=True)
