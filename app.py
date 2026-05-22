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
    [data-testid="stSidebar"] h1 { font-size: 1.2rem !important; line-height: 1.3; margin-bottom: 0.1rem !important; }
    
    /* Reducir el espaciado (padding) superior interno del sidebar de Streamlit */
    [data-testid="stSidebarUserContent"] { padding-top: 0.8rem !important; padding-bottom: 0.3rem !important; }
    
    /* Eliminar gaps por defecto entre los bloques verticales del sidebar */
    [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] > div > [data-testid="stVerticalBlock"] {
        gap: 0.1rem !important;
    }
    
    /* Compactar la separación entre cada widget individual */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div {
        padding-bottom: 0.05rem !important;
        padding-top: 0.05rem !important;
    }
    
    /* Forzar márgenes mínimos en las etiquetas de los inputs */
    [data-testid="stSidebar"] .stTextInput label {
        margin-bottom: 0.05rem !important;
    }
    
    /* Ajustar las líneas divisorias (hr) para que sean hilos delgados sin margen muerto */
    [data-testid="stSidebar"] hr {
        margin-top: 0.3rem !important;
        margin-bottom: 0.3rem !important;
    }

    /* ---- OCULTAR TODO EL CONTENEDOR INTERNO DE ARCHIVOS DE STREAMLIT ---- */
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

# Inicializamos una clave en el estado de la sesión si no existe para controlar el refresco limpio
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
q_input = st.sidebar.text_input("Caudal (m³/s)", value="0.565")
d_input = st.sidebar.text_input("Diámetro Interno (m)", value="1.219")

try:
    q_m3s = float(q_input) if q_input else 0.000
    d_m = float(d_input) if d_input else 0.010
except ValueError:
    st.sidebar.error("Por favor, introduce valores numéricos válidos para Caudal y Diámetro.")
    q_m3s, d_m = 0.565, 1.219

st.sidebar.markdown("---")
st.sidebar.markdown("**Filtro de Segmentación Técnica**")

# Slider solicitado: Ajustado de 10 a 500 metros, con paso de 10 en 10
longitud_minima_tramo = st.sidebar.slider(
    "Longitud Mínima de Tramo (m)",
    min_value=10, max_value=500, value=200, step=10,
    help="Define la longitud mínima horizontal que debe tener una pendiente continua para ser evaluada bajo el criterio de protección anticolapso."
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Análisis de Válvulas Intermedias Anticolapso**")
activar_anticolapso = st.sidebar.checkbox("Activar análisis anticolapso", value=True)

dh_d = 9.0
h_res = 0.0
if activar_anticolapso:
    dh_d_input = st.sidebar.text_input("Límite de Vacío Admisible ΔH_D (m)", value="9.0")
    h_res_input = st.sidebar.text_input("Presión Residual Post-Rotura h (m)", value="0.0")
    try:
        dh_d = float(dh_d_input) if dh_d_input else 9.0
        h_res = float(h_res_input) if h_res_input else 0.0
    except ValueError:
        st.sidebar.error("Valores numéricos inválidos.")

limite_critico_vertical = dh_d + h_res

st.sidebar.markdown("---")
st.sidebar.write("**Desarrollado por: M.I. Alan Sañudo**")

# 3. CUERPO PRINCIPAL DE LA APLICACIÓN
st.title("Analizador de Aire Atrapado y Criterios de Protección Anticolapso")

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
            
            df[col_x] = pd.to_numeric(df[col_x])
            df[col_z] = pd.to_numeric(df[col_z])
            df = df.sort_values(by=col_x).reset_index(drop=True)

            # Alerta preventiva por criterios de capilaridad (Zukoski)
            if d_m < 0.100:
                st.warning("⚠️ **Nota técnica:** El diámetro ingresado es menor a 100 mm (4 pulgadas). En tuberías pequeñas, los efectos de tensión superficial y capilaridad pueden alterar el comportamiento del aire respecto al modelo matemático de arrastre hidráulico por gravedad.")

            # ---- MOTOR 1: ANÁLISIS HIDRÁULICO LOCAL (ECUACIÓN AL CUADRADO UNAM) ----
            # Parámetro adimensional del sistema elevado al cuadrado Q² / (g * D⁵)
            parametro_sistema_sq = (q_m3s**2) / (g * (d_m**5)) if d_m > 0 else 0
            
            # Determinamos crestas y valles reales locales
            df['es_cresta'] = (df[col_z] > df[col_z].shift(1, fill_value=df[col_z].iloc[0])) & (df[col_z] > df[col_z].shift(-1, fill_value=df[col_z].iloc[-1]))
            df['es_valle'] = (df[col_z] < df[col_z].shift(1, fill_value=df[col_z].iloc[0])) & (df[col_z] < df[col_z].shift(-1, fill_value=df[col_z].iloc[-1]))
            
            df['dx'] = df[col_x].diff()
            df['dz'] = df[col_z].diff()
            
            # Pendiente geométrica S (Definida positiva para tramos descendentes)
            df['S'] = -df['dz'] / df['dx'].replace(0, np.nan)
            
            # Aplicación de la ecuación lineal exacta de la gráfica UNAM (Eje vertical al cuadrado)
            df['parametro_critico'] = np.where(df['S'] > 0, 0.35 * df['S'].fillna(0) + 0.18, 0.0)
            df['riesgo_hidraulico'] = (df['S'] > 0) & (parametro_sistema_sq < df['parametro_critico'])
            
            # Despeje de la velocidad mínima de barrido basada en el parámetro cinético al cuadrado
            df['v_critica'] = np.where(
                df['S'] > 0,
                (4 / np.pi) * np.sqrt((0.35 * df['S'].fillna(0) + 0.18) * g * d_m),
                0.0
            )
            
            # Velocidad cinemática real en el conducto
            area = np.pi * (d_m**2) / 4 if d_m > 0 else 1
            v_real = q_m3s / area

            # ---- MOTOR 2: VÁLVULAS INTERMEDIAS CON FILTRO DE LONGITUD MÍNIMA ----
            df['critico_pendiente_larga'] = False
            
            if activar_anticolapso:
                df_quiebres = df[df['es_cresta'] | df['es_valle']].copy().sort_values(by=col_x).reset_index()
                
                for idx in range(len(df_quiebres) - 1):
                    nodo_a = df_quiebres.loc[idx]
                    nodo_b = df_quiebres.loc[idx+1]
                    
                    longitud_horizontal_tramo = abs(nodo_b[col_x] - nodo_a[col_x])
                    
                    if longitud_horizontal_tramo >= longitud_minima_tramo:
                        diff_vertical_tramo = abs(nodo_a[col_z] - nodo_b[col_z])
                        
                        if diff_vertical_tramo > limite_critico_vertical:
                            num_valvulas = int(diff_vertical_tramo // limite_critico_vertical)
                            
                            idx_inicio = int(nodo_a['index'])
                            idx_fin = int(nodo_b['index'])
                            
                            for nv in range(1, num_valvulas + 1):
                                fraccion = nv / (num_valvulas + 1)
                                x_objetivo = nodo_a[col_x] + fraccion * (nodo_b[col_x] - nodo_a[col_x])
                                
                                rango_tramo = df.iloc[idx_inicio:idx_fin+1]
                                if not rango_tramo.empty:
                                    idx_cercano = (rango_tramo[col_x] - x_objetivo).abs().idxmin()
                                    df.loc[idx_cercano, 'critico_pendiente_larga'] = True

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
            if not crestas.empty:
                fig.add_trace(go.Scatter(
                    x=crestas[col_x], y=crestas[col_z], 
                    mode='markers', 
                    marker=dict(color='#F59E0B', size=12, symbol='triangle-up', line=dict(color='black', width=1)),
                    name='Punto alto, acumulación por flotación'
                ))

            # Resaltar en rojo grueso para los tramos con arrastre insuficiente (Riesgo UNAM)
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

            # Válvulas Intermedias Anticolapso (Icono cuadrado fucsia reducido a size=5)
            if activar_anticolapso:
                p_largas = df[df['critico_pendiente_larga']]
                fig.add_trace(go.Scatter(
                    x=p_largas[col_x], y=p_largas[col_z], 
                    mode='markers', 
                    marker=dict(color='#D946EF', size=5, symbol='square', line=dict(color='black', width=0.5)),
                    name='Válvula Intermedia (Criterio Anticolapso)'
                ))

            # Layout optimizado: Forzado de leyendas al eje inferior (y=-0.18)
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
            res_table = df[(df['es_cresta']) | (df['riesgo_hidraulico']) | (df['critico_pendiente_larga'])].copy()
            
            if not res_table.empty:
                condiciones = [
                    res_table['critico_pendiente_larga'],
                    res_table['es_cresta'],
                    res_table['riesgo_hidraulico']
                ]
                elecciones = [
                    "Válvula Intermedia Sugerida (Pendiente Larga Anticolapso)",
                    "Punto Alto Geométrico (Bolsa Permanente)",
                    "Aire Estacionario (Falta de Arrastre en Pendiente)"
                ]
                res_table['Diagnóstico del Aire'] = np.select(condiciones, elecciones, default="Tramo de Atención Especial")
                
                res_table['V. Flujo (m/s)'] = round(v_real, 3)
                res_table['V. Mínima Barrido (m/s)'] = np.where(res_table['S'] > 0, round(res_table['v_critica'], 3), 0.000)
                res_table['Pendiente (S)'] = round(res_table['S'].fillna(0), 4)
                
                output_cols = [col_x, col_z, 'Pendiente (S)', 'Diagnóstico del Aire', 'V. Flujo (m/s)', 'V. Mínima Barrido (m/s)']
                st.dataframe(
                    res_table[output_cols].rename(columns={col_x: "Distancia (m)", col_z: "Elevación (m)"}), 
                    use_container_width=True
                )
                
                c1, c2 = st.columns(2)
                with c1:
                    st.metric(label="Parámetro de Gasto Adimensional [Q²/(g·D⁵)] del Sistema", value=f"{parametro_sistema_sq:.5f}")
                with c2:
                    if activar_anticolapso:
                        st.metric(label="Límite Vertical Macro Permitido (ΔH_D + h)", value=f"{limite_critico_vertical:.2f} m")
            else:
                st.success("✅ El sistema opera con estabilidad. No se detectaron anomalías.")

        else:
            st.error("❌ Formato inválido. Asegúrate de que las columnas del archivo sigan estrictamente las instrucciones de la barra lateral.")
    except Exception as e:
        st.error(f"Error al leer o procesar el archivo cargado: {e}")
else:
    st.info("👈 Por favor, ingresa tu archivo de perfil (.csv o .xlsx) y configura las variables en el menú lateral para iniciar el análisis hidráulico.")

# 6. BIBLIOGRAFÍA DE RESPALDO INSTITUCIONAL
st.markdown("""
<div class="discreet-note">
    <strong>Fuentes técnicas e internacionales de referencia:</strong><br>
    • Instituto de Ingeniería, UNAM. <em>Manual de análisis de la problemática del aire atrapado en acueductos, para mejorar su eficiencia.</em> Serie Manuales, México.<br>
    • Wang, Y., Zhang, J., et al. (2023). <em>Air valve arrangement criteria for preventing secondary pipe bursts in long-distance gravitational water supply systems.</em> AQUA - IWA Publishing.<br>
    • Kalinske, A. A., & Bliss, P. H. (1943). <em>Removal of air from pipe lines by flowing water.</em> Civil Engineering, 13(10).<br>
    • Zukoski, E. E. (1966). <em>Influence of viscosity, surface tension and inclination on motion of long bubbles in closed tubes.</em> Journal of Fluid Mechanics.
</div>
""", unsafe_allow_html=True)
