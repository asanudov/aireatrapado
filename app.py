import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS BASE
st.set_page_config(page_title="Analizador de Aire Atrapado", layout="wide")

# CSS personalizado: Máxima amplitud horizontal y optimización vertical agresiva del sidebar
st.markdown("""
    <style>
    /* Optimización del contenedor principal */
    .block-container { padding-top: 1.5rem; padding-bottom: 0rem; padding-left: 2rem; padding-right: 2rem; }
    h1 { font-size: 1.8rem !important; font-weight: 700; color: #1E3A8A; }
    .discreet-note { font-size: 11px; color: #888; margin-top: 30px; border-top: 1px solid #eee; padding-top: 10px; }
    
    /* ---- OPTIMIZACIÓN VERTICAL ULTRA-COMPACTA DEL SIDEBAR ---- */
    [data-testid="stSidebar"] h1 { font-size: 1.2rem !important; line-height: 1.3; margin-bottom: 0.2rem !important; }
    
    /* Reducir el espaciado (padding) superior interno del sidebar de Streamlit */
    [data-testid="stSidebarUserContent"] { padding-top: 1.0rem !important; padding-bottom: 0.5rem !important; }
    
    /* Eliminar gaps por defecto entre los bloques verticales del sidebar */
    [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] > div > [data-testid="stVerticalBlock"] {
        gap: 0.2rem !important;
    }
    
    /* Compactar la separación entre cada widget individual */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div {
        padding-bottom: 0.1rem !important;
        padding-top: 0.1rem !important;
    }
    
    /* Forzar márgenes mínimos en las etiquetas de los inputs */
    [data-testid="stSidebar"] .stTextInput label {
        margin-bottom: 0.1rem !important;
    }
    
    /* Ajustar las líneas divisorias (hr) para que sean hilos delgados sin margen muerto */
    [data-testid="stSidebar"] hr {
        margin-top: 0.4rem !important;
        margin-bottom: 0.4rem !important;
    }

    /* ---- ELIMINAR SUBTEXTO DE METADATOS DEL ARCHIVO (Bloque Gris/Rojo) ---- */
    [data-testid="stFileUploaderDropzone"] + div {
        display: none !important;
    }
    </style>
""", unsafe_allow_html=True)

# 2. BARRA LATERAL (SIDEBAR) - Estructura Visual
st.sidebar.title("Analizador de Aire Atrapado en Conductos a Presión")

# A. Cargador de archivos en la parte superior
uploaded_file = st.sidebar.file_uploader("Carga tu perfil en Excel o CSV", type=["xlsx", "csv"])

# LÓGICA DINÁMICA DE INTERFAZ: Inyectar CSS para cambiar el '+' SOLO cuando ya existe un archivo cargado
if uploaded_file is not None:
    st.markdown("""
        <style>
        /* Modifica el botón de reemplazo (+) únicamente si el archivo está en memoria */
        [data-testid="stFileUploaderDropzone"] button::before {
            content: "Carga un archivo diferente";
            font-size: 13px;
            color: #1E40AF;
            font-weight: 600;
        }
        [data-testid="stFileUploaderDropzone"] button svg {
            display: none !important; /* Oculta el signo + nativo */
        }
        [data-testid="stFileUploaderDropzone"] button {
            width: 100% !important;
            background-color: #f0f4f8 !important;
            border: 1px dashed #1E40AF !important;
            padding: 6px 12px !important;
            height: auto !important;
            margin-top: 4px !important;
        }
        </style>
    """, unsafe_allow_html=True)

st.sidebar.markdown("---")

# B. Entradas numéricas abajo de la carga (Campos de texto limpios sin botones + / -)
q_input = st.sidebar.text_input("Caudal (m³/s)", value="0.075")
d_input = st.sidebar.text_input("Diámetro Interno (m)", value="0.305")

# Conversión segura de cadenas a flotantes para evitar quiebres en ejecución
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
            
            # Alerta preventiva por criterios de capilaridad (Zukoski)
            if d_m < 0.100:
                st.warning("⚠️ **Nota técnica:** El diámetro ingresado es menor a 100 mm (4 pulgadas). En tuberías pequeñas, los efectos de tensión superficial y capilaridad pueden alterar el comportamiento del aire respecto al modelo matemático de arrastre hidráulico por gravedad.")

            # ---- MOTOR DE CÁLCULO: METODOLOGÍA MANUAL II-UNAM ----
            # 1. Gasto Adimensional (PGA) del flujo constante del sistema
            pga_sistema = q_m3s / np.sqrt(g * (d_m**5)) if d_m > 0 else 0
            
            # 2. Análisis geométrico de picos (Crestas locales de acumulación por flotación)
            df['es_cresta'] = (df[col_z] > df[col_z].shift(1)) & (df[col_z] > df[col_z].shift(-1))
            
            # 3. Análisis cinemático de diferenciales por tramo
            df['dx'] = df[col_x].diff()
            df['dz'] = df[col_z].diff()
            
            # Pendiente geométrica S (Definida positiva para tramos descendentes en el manual de la UNAM)
            df['S'] = -df['dz'] / df['dx'].replace(0, np.nan)
            
            # 4. Evaluación de la Capacidad de Arrastre (Condición Crítica: Tramo descendente y PGA insuficiente)
            df['riesgo_hidraulico'] = (df['S'] > 0) & (pga_sistema < np.sqrt(df['S'].fillna(0)))
            
            # Velocidad Crítica límite para el reporte (Ecuación analítica de Kalinske y Bliss)
            df['v_critica'] = 1.146 * np.sqrt(g * d_m * df['S'])
            df['v_critica'] = df['v_critica'].fillna(0)
            
            # Velocidad cinemática real en el conducto
            area = np.pi * (d_m**2) / 4 if d_m > 0 else 1
            v_real = q_m3s / area

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

            # Marcadores geométricos de Puntos Altos (Simbología exacta solicitada)
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

            # Layout optimizado: Forzado de leyendas al eje inferior (y=-0.18) para liberar la horizontal
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

            # 5. MATRIZ DE RESULTADOS / REPORTES
            st.subheader("Reporte General de Puntos Críticos")
            res_table = df[(df['es_cresta']) | (df['riesgo_hidraulico'])].copy()
            
            if not res_table.empty:
                res_table['Diagnóstico del Aire'] = np.where(
                    res_table['es_cresta'], 
                    "Punto Alto Geométrico (Bolsa Permanente)", 
                    "Aire Estacionario (Falta de Arrastre en Pendiente)"
                )
                res_table['V. Flujo (m/s)'] = round(v_real, 3)
                res_table['V. Mínima Barrido (m/s)'] = round(res_table['v_critica'], 3)
                res_table['Pendiente (S)'] = round(res_table['S'], 4)
                
                output_cols = [col_x, col_z, 'Pendiente (S)', 'Diagnóstico del Aire', 'V. Flujo (m/s)', 'V. Mínima Barrido (m/s)']
                st.dataframe(
                    res_table[output_cols].rename(columns={col_x: "Distancia (m)", col_z: "Elevación (m)"}), 
                    use_container_width=True
                )
                
                st.metric(label="Parámetro de Gasto Adimensional (PGA) del Sistema", value=f"{pga_sistema:.4f}")
            else:
                st.success("✅ El sistema opera con estabilidad. No se detectaron puntos altos ni tramos con insuficiencia de arrastre.")

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
    • Kalinske, A. A., & Bliss, P. H. (1943). <em>Removal of air from pipe lines by flowing water.</em> Civil Engineering, 13(10).<br>
    • Zukoski, E. E. (1966). <em>Influence of viscosity, surface tension and inclination on motion of long bubbles in closed tubes.</em> Journal of Fluid Mechanics.
</div>
""", unsafe_allow_html=True)
