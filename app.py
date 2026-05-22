import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS BASE
st.set_page_config(page_title="Analizador de Aire Atrapado y Transitorios", layout="wide")

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
st.sidebar.title("Analizador Hidráulico y de Protección de Conductos")

# Inicializamos una clave en el estado de la sesión si no existe para controlar el refresco limpio
if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = "file_uploader_v1"

# A. Cargador de archivos en la parte superior
uploaded_file = st.sidebar.file_uploader(
    "Carga tu perfil en Excel o CSV", 
    type=["xlsx", "csv"],
    key=st.session_state["uploader_key"]
)

# LÓGICA DE INTERFAZ CONTROLADA POR PYTHON:
if uploaded_file is not None:
    st.markdown("<div class='file-uploaded-active'></div>", unsafe_allow_html=True)
    if st.sidebar.button("🔄 Carga un archivo diferente", use_container_width=True):
        st.session_state["uploader_key"] = f"file_uploader_{np.random.randint(1000, 9999)}"
        st.rerun()

st.sidebar.markdown("---")

# B. Parámetros Hidráulicos Estacionarios
q_input = st.sidebar.text_input("Caudal de Diseño Q (m³/s)", value="0.075")
d_input = st.sidebar.text_input("Diámetro Interno D (m)", value="0.305")

st.sidebar.markdown("---")

# C. NUEVA SECCIÓN ADAPTADA: ANÁLISIS DE VÁLVULAS INTERMEDIAS ANTICOLAPSO
st.sidebar.markdown("**Análisis de válvulas intermedias anticolapso**")
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
        st.sidebar.error("Valores numéricos inválidos para el análisis anticolapso.")

limite_critico_vertical = dh_d + h_res

st.sidebar.markdown("---")

# D. Instrucciones de formato para el archivo
st.sidebar.info("""
**Instrucciones de formato del archivo:**
1. Debe contener dos columnas (X, Y) con encabezados claros.
2. Eje X: "Cadenamiento", "Distancia" o "X" (m).
3. Eje Y: "Elevación", "Elevacion" o "Y" (m).
""")

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
        
        df.columns = [c.lower().strip() for c in df.columns]
        col_x = next((c for c in df.columns if c in ['cadenamiento', 'distancia', 'x']), None)
        col_z = next((c for c in df.columns if c in ['elevación', 'elevacion', 'y']), None)

        if col_x and col_z:
            g = 9.81
            
            if d_m < 0.100:
                st.warning("⚠️ **Nota técnica:** Diámetro menor a 100 mm. Los efectos capilares y de tensión superficial pueden diferir de los modelos cinemáticos de arrastre clásicos.")

            # ---- MOTOR DE CÁLCULO 1: HIDRÁULICA Y AIRE (II-UNAM / KALINSKE) ----
            pga_sistema = q_m3s / np.sqrt(g * (d_m**5)) if d_m > 0 else 0
            
            # Identificación de Crestas (Puntos Altos) y Valles (Puntos Bajos) para análisis macro
            df['es_cresta'] = (df[col_z] > df[col_z].shift(1)) & (df[col_z] > df[col_z].shift(-1))
            df['es_valle'] = (df[col_z] < df[col_z].shift(1)) & (df[col_z] < df[col_z].shift(-1))
            
            # Forzar extremos del perfil como hitos de control geométrico inicial/final
            df.loc[df.index[0], 'es_cresta'] = True
            df.loc[df.index[-1], 'es_valle'] = True
            
            df['dx'] = df[col_x].diff()
            df['dz'] = df[col_z].diff()
            df['S'] = -df['dz'] / df['dx'].replace(0, np.nan)
            
            df['riesgo_hidraulico'] = (df['S'] > 0) & (pga_sistema < np.sqrt(df['S'].fillna(0)))
            df['v_critica'] = 1.146 * np.sqrt(g * d_m * df['S']).fillna(0)
            
            area = np.pi * (d_m**2) / 4 if d_m > 0 else 1
            v_real = q_m3s / area

            # ---- MOTOR DE CÁLCULO 2: ANÁLISIS MACROSCÓPICO SUAVIZADO (WANG ET AL., 2023) ----
            df['critico_pendiente_larga'] = False
            
            if activar_anticolapso:
                # Extraemos únicamente los nodos de quiebre macro (Crestas y Valles) para limpiar el ruido topográfico
                df_macro = df[df['es_cresta'] | df['es_valle']].copy()
                df_macro = df_macro.sort_values(by=col_x).reset_index()
                
                # Buscamos pendientes largas acumuladas entre estos macro-nodos
                for idx in range(len(df_macro) - 1):
                    nodo_a = df_macro.loc[idx]
                    nodo_b = df_macro.loc[idx+1]
                    
                    z_alta = max(nodo_a[col_z], nodo_b[col_z])
                    z_baja = min(nodo_a[col_z], nodo_b[col_z])
                    diff_macro_vertical = z_alta - z_baja
                    
                    # Si la diferencia macro neta supera la tolerancia de vacío, se requiere válvula intermedia
                    if diff_macro_vertical > limite_critico_vertical:
                        # Calculamos cuántas válvulas intermedias se necesitan en esa pendiente larga
                        num_valvulas_necesarias = int(diff_macro_vertical // limite_critico_vertical)
                        
                        # Interpolamos la posición exacta en el perfil original para colocar la válvula de forma equidistante
                        idx_perfil_inicio = int(nodo_a['index'])
                        idx_perfil_fin = int(nodo_b['index'])
                        
                        for nv in range(1, num_valvulas_necesarias + 1):
                            fraccion = nv / (num_valvulas_necesarias + 1)
                            z_objetivo = nodo_a[col_z] + fraccion * (nodo_b[col_z] - nodo_a[col_z])
                            
                            # Encontramos el índice en el df original que más se aproxime a esa elevación calculada
                            rango_tramo = df.iloc[idx_perfil_inicio:idx_perfil_fin+1]
                            if not rango_tramo.empty:
                                idx_cercano = (rango_tramo[col_z] - z_objetivo).abs().idxmin()
                                df.loc[idx_cercano, 'critico_pendiente_larga'] = True

            # 4. COMPONENTE GRÁFICO AVANZADO
            st.subheader("Perfil Longitudinal del Acueducto e Hitos de Control")
            fig = go.Figure()

            # Trazado del perfil real del terreno/tubería
            fig.add_trace(go.Scatter(
                x=df[col_x], y=df[col_z], 
                mode='lines', 
                name='Perfil de Tubería', 
                line=dict(color='#1E40AF', width=2.5)
            ))

            # Hito 1: Puntos Altos Geométricos
            crestas = df[df['es_cresta'] & (df.index != df.index[0]) & (df.index != df.index[-1])]
            if not crestas.empty:
                fig.add_trace(go.Scatter(
                    x=crestas[col_x], y=crestas[col_z], 
                    mode='markers', 
                    marker=dict(color='#F59E0B', size=11, symbol='triangle-up', line=dict(color='black', width=1)),
                    name='Punto Alto Geométrico (Bolsa por Flotación)'
                ))

            # Hito 2: Tramos Críticos por Arrastre Insuficiente (UNAM/Kalinske) en Rojo grueso
            for i in range(1, len(df)):
                if df.loc[i, 'riesgo_hidraulico']:
                    fig.add_trace(go.Scatter(
                        x=[df.loc[i-1, col_x], df.loc[i, col_x]], 
                        y=[df.loc[i-1, col_z], df.loc[i, col_z]],
                        mode='lines', 
                        line=dict(color='#DC2626', width=4.5),
                        name='Tramo Crítico: Arrastre de Aire Insuficiente' if i == df['riesgo_hidraulico'].idxmax() else "",
                        showlegend=(i == df['riesgo_hidraulico'].idxmax())
                    ))

            # Hito 3: Puntos de colapso potencial en pendientes largas (Solo si está activo)
            if activar_anticolapso:
                p_largas = df[df['critico_pendiente_larga']]
                fig.add_trace(go.Scatter(
                    x=p_largas[col_x], y=p_largas[col_z], 
                    mode='markers', 
                    marker=dict(color='#D946EF', size=11, symbol='square', line=dict(color='black', width=1)),
                    name='Válvula Intermedia Propuesta (Macro-Suavizado Anticolapso)'
                ))

            # Ajustes de Layout e Inversión de Leyendas al eje inferior
            fig.update_layout(
                xaxis_title="Distancia / Cadenamiento (m)", 
                yaxis_title="Elevación (m)", 
                height=550,
                margin=dict(l=10, r=10, t=20, b=10),
                legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5),
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)

            # 5. MATRIZ DE RESULTADOS / REPORTES COMBINADOS
            st.subheader("Reporte General de Nodos Críticos Detectados")
            
            # Filtramos filas para el reporte final
            res_table = df[(df['es_cresta'] & (df.index != df.index[0])) | (df['riesgo_hidraulico']) | (df['critico_pendiente_larga'])].copy()
            
            if not res_table.empty:
                # Clasificación analítica exacta del diagnóstico
                condiciones = [
                    res_table['critico_pendiente_larga'],
                    res_table['es_cresta'],
                    res_table['riesgo_hidraulico']
                ]
                elecciones = [
                    "Válvula Intermedia Sugerida (Pendiente Larga Macroscópica)",
                    "Punto Alto Geométrico (Bolsa Permanente)",
                    "Aire Estacionario (Velocidad de Flujo Insuficiente)"
                ]
                res_table['Diagnóstico Técnico'] = np.select(condiciones, elecciones, default="Tramo de Atención Especial")
                
                res_table['V. Flujo (m/s)'] = round(v_real, 3)
                res_table['V. Mínima Barrido (m/s)'] = np.where(res_table['S'] > 0, round(res_table['v_critica'], 3), 0.000)
                res_table['Pendiente (S)'] = round(res_table['S'].fillna(0), 4)
                
                output_cols = [col_x, col_z, 'Pendiente (S)', 'Diagnóstico Técnico', 'V. Flujo (m/s)', 'V. Mínima Barrido (m/s)']
                st.dataframe(
                    res_table[output_cols].rename(columns={col_x: "Distancia (m)", col_z: "Elevación (m)"}), 
                    use_container_width=True
                )
                
                # Indicadores técnicos métricos de control de diseño
                c1, c2 = st.columns(2)
                with c1:
                    st.metric(label="Parámetro de Gasto Adimensional (PGA) Actual", value=f"{pga_sistema:.4f}")
                with c2:
                    if activar_anticolapso:
                        st.metric(label="Límite Vertical Macro Permitido (ΔH_D + h)", value=f"{limite_critico_vertical:.2f} m")
                    else:
                        st.metric(label="Análisis Anticolapso", value="Desactivado")
            else:
                st.success("✅ El sistema opera dentro de rangos óptimos. No se detectaron fallos cinemáticos ni riesgos estructurales.")

        else:
            st.error("❌ Formato inválido. Asegúrate de verificar los encabezados de las columnas en tu archivo.")
    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
else:
    st.info("👈 Ingresa tu archivo de perfil (.csv o .xlsx) y configura las variables en el menú lateral para iniciar la evaluación.")

# 6. BIBLIOGRAFÍA DE RESPALDO INSTITUCIONAL
st.markdown("""
<div class="discreet-note">
    <strong>Fuentes técnicas e internacionales de referencia:</strong><br>
    • <strong>Wang, Y., Zhang, J., et al. (2023).</strong> <em>Air valve arrangement criteria for preventing secondary pipe bursts in long-distance gravitational water supply systems.</em> AQUA - Water Infrastructure, Ecosystems and Society, 72(8), 1566.<br>
    • <strong>Instituto de Ingeniería, UNAM.</strong> <em>Manual de análisis de la problemática del aire atrapado en acueductos, para mejorar su eficiencia.</em> Serie Manuales, México.<br>
    • <strong>Kalinske, A. A., & Bliss, P. H. (1943).</strong> <em>Removal of air from pipe lines by flowing water.</em> Civil Engineering, 13(10).
</div>
""", unsafe_allow_html=True)
