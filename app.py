import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS BASE
st.set_page_config(page_title="Analizador de Aire Atrapado y Transitorios", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; padding-bottom: 0rem; padding-left: 2rem; padding-right: 2rem; }
    h1 { font-size: 1.8rem !important; font-weight: 700; color: #1E3A8A; }
    .discreet-note { font-size: 11px; color: #888; margin-top: 30px; border-top: 1px solid #eee; padding-top: 10px; }
    
    /* SIDEBAR ULTRA-COMPACTO */
    [data-testid="stSidebar"] h1 { font-size: 1.2rem !important; line-height: 1.3; margin-bottom: 0.1rem !important; }
    [data-testid="stSidebarUserContent"] { padding-top: 0.8rem !important; padding-bottom: 0.3rem !important; }
    [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] > div > [data-testid="stVerticalBlock"] { gap: 0.1rem !important; }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div { padding-bottom: 0.05rem !important; padding-top: 0.05rem !important; }
    [data-testid="stSidebar"] .stTextInput label { margin-bottom: 0.05rem !important; }
    [data-testid="stSidebar"] hr { margin-top: 0.3rem !important; margin-bottom: 0.3rem !important; }

    /* ELIMINAR CONTENEDOR DE ARCHIVOS REDUNDANTE */
    .file-uploaded-active [data-testid="stFileUploaderDropzone"] { display: none !important; }
    </style>
""", unsafe_allow_html=True)

# 2. BARRA LATERAL (SIDEBAR)
st.sidebar.title("Analizador Hidráulico de Conducciones")

if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = "file_uploader_v1"

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

# Parámetros Hidráulicos de Entrada
q_input = st.sidebar.text_input("Caudal de Diseño Q (m³/s)", value="0.565")
d_input = st.sidebar.text_input("Diámetro Interno D (m)", value="1.219")

st.sidebar.markdown("---")
st.sidebar.markdown("**Filtro de Segmentación Técnica**")

# NUEVO SLIDER SOLICITADO: Ajustado de 10 a 500 metros, con paso de 10 en 10
longitud_minima_tramo = st.sidebar.slider(
    "Longitud Mínima de Tramo (m)",
    min_value=10, max_value=500, value=200, step=10,
    help="Define la longitud mínima horizontal que debe tener una pendiente continua para ser evaluada bajo el criterio de protección anticolapso."
)

st.sidebar.markdown("---")

# C. SECCIÓN: ANÁLISIS DE VÁLVULAS INTERMEDIAS ANTICOLAPSO
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
        st.sidebar.error("Valores numéricos inválidos.")

limite_critico_vertical = dh_d + h_res

st.sidebar.markdown("---")
st.sidebar.write("**Desarrollado por: M.I. Alan Sañudo**")

# 3. CUERPO PRINCIPAL
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
            df[col_x] = pd.to_numeric(df[col_x])
            df[col_z] = pd.to_numeric(df[col_z])
            df = df.sort_values(by=col_x).reset_index(drop=True)

            try:
                q_m3s = float(q_input) if q_input else 0.565
                d_m = float(d_input) if d_input else 1.219
            except ValueError:
                q_m3s, d_m = 0.565, 1.219

            # Como removimos la tolerancia de rectas, la geometría de diseño coincide directamente con el perfil real
            df['z_diseño'] = df[col_z]

            # Determinamos crestas y valles reales locales para ubicar los hitos geométricos base
            df['es_cresta'] = (df['z_diseño'] > df['z_diseño'].shift(1, fill_value=df['z_diseño'].iloc[0])) & (df['z_diseño'] > df['z_diseño'].shift(-1, fill_value=df['z_diseño'].iloc[-1]))
            df['es_valle'] = (df['z_diseño'] < df['z_diseño'].shift(1, fill_value=df['z_diseño'].iloc[0])) & (df['z_diseño'] < df['z_diseño'].shift(-1, fill_value=df['z_diseño'].iloc[-1]))

            # ---- MOTOR 1: ANÁLISIS HIDRÁULICO LOCAL RE-ESTABLECIDO (PGA / UNAM) ----
            pga_sistema = q_m3s / np.sqrt(g * (d_m**5)) if d_m > 0 else 0
            
            df['dx'] = df[col_x].diff()
            df['dz'] = df['z_diseño'].diff()
            df['S'] = -df['dz'] / df['dx'].replace(0, np.nan)
            
            df['riesgo_hidraulico'] = (df['S'] > 0) & (pga_sistema < np.sqrt(df['S'].fillna(0)))
            df['v_critica'] = 1.146 * np.sqrt(g * d_m * df['S']).fillna(0)
            
            area = np.pi * (d_m**2) / 4 if d_m > 0 else 1
            v_real = q_m3s / area

            # ---- MOTOR 2: ANÁLISIS ANTICOLAPSO EN PENDIENTES CONTINUAS POR LONGITUD ----
            df['critico_pendiente_larga'] = False
            
            if activar_anticolapso:
                # Identificamos los nodos que marcan un quiebre relevante (cambio de signo en la pendiente local)
                df_quiebres = df[df['es_cresta'] | df['es_valle']].copy().sort_values(by=col_x).reset_index()
                
                for idx in range(len(df_quiebres) - 1):
                    nodo_a = df_quiebres.loc[idx]
                    nodo_b = df_quiebres.loc[idx+1]
                    
                    longitud_horizontal_tramo = abs(nodo_b[col_x] - nodo_a[col_x])
                    
                    # FILTRO DE RELEVANCIA LONGITUDINAL SOLICITADO
                    if longitud_horizontal_tramo >= longitud_minima_tramo:
                        diff_vertical_tramo = abs(nodo_a['z_diseño'] - nodo_b['z_diseño'])
                        
                        # Si el desnivel acumulado supera el vacío crítico admisible en la bajada/subida macro
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

            # 4. COMPONENTE GRÁFICO ALTAMENTE PRECIOSO Y LIMPIO
            fig = go.Figure()

            # Perfil Real de la Conducción
            fig.add_trace(go.Scatter(
                x=df[col_x], y=df['z_diseño'], 
                mode='lines', 
                name='Perfil del Acueducto (El Realito)', 
                line=dict(color='#1E40AF', width=2)
            ))

            # Puntos Altos Geométricos principales
            p_altos = df[df['es_cresta']]
            if not p_altos.empty:
                fig.add_trace(go.Scatter(
                    x=p_altos[col_x], y=p_altos['z_diseño'], 
                    mode='markers', 
                    marker=dict(color='#F59E0B', size=8, symbol='triangle-up', line=dict(color='black', width=0.5)),
                    name='Punto Alto Geométrico'
                ))

            # Segmentos con Riesgo de Aire Atrapado (PGA) en Rojo
            for i in range(1, len(df)):
                if df.loc[i, 'riesgo_hidraulico']:
                    fig.add_trace(go.Scatter(
                        x=[df.loc[i-1, col_x], df.loc[i, col_x]], 
                        y=[df.loc[i-1, 'z_diseño'], df.loc[i, 'z_diseño']],
                        mode='lines', 
                        line=dict(color='#DC2626', width=4),
                        name='Riesgo PGA: Arrastre Insuficiente' if i == df['riesgo_hidraulico'].idxmax() else "",
                        showlegend=(i == df['riesgo_hidraulico'].idxmax())
                    ))

            # Válvulas Intermedias Anticolapso (Icono cuadrado muy pequeño size=5)
            if activar_anticolapso:
                p_largas = df[df['critico_pendiente_larga']]
                fig.add_trace(go.Scatter(
                    x=p_largas[col_x], y=p_largas['z_diseño'], 
                    mode='markers', 
                    marker=dict(color='#D946EF', size=5, symbol='square', line=dict(color='black', width=0.5)),
                    name='Válvula Intermedia (Criterio Anticolapso)'
                ))

            fig.update_layout(
                xaxis_title="Distancia / Cadenamiento (m)", 
                yaxis_title="Elevación (m)", 
                height=550,
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5),
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)

            # 5. MATRIZ DE RESULTADOS COMPLETAMENTE CORREGIDA
            st.subheader("Reporte General de Nodos Críticos Detectados")
            
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
                    "Tramo de Riesgo PGA (Arrastre Insuficiente)"
                ]
                res_table['Diagnóstico Técnico'] = np.select(condiciones, elecciones, default="Tramo de Atención Especial")
                
                res_table['V. Flujo (m/s)'] = round(v_real, 3)
                res_table['V. Mínima Barrido (m/s)'] = np.where(res_table['S'] > 0, round(res_table['v_critica'], 3), 0.000)
                res_table['Pendiente Local (S)'] = round(res_table['S'].fillna(0), 4)
                
                output_cols = [col_x, 'z_diseño', 'Pendiente Local (S)', 'Diagnóstico Técnico', 'V. Flujo (m/s)', 'V. Mínima Barrido (m/s)']
                st.dataframe(
                    res_table[output_cols].rename(columns={col_x: "Distancia (m)", 'z_diseño': "Elevación (m)"}), 
                    use_container_width=True
                )
                
                c1, c2 = st.columns(2)
                with c1:
                    st.metric(label="Parámetro de Gasto Adimensional (PGA) Actual del Acueducto", value=f"{pga_sistema:.4f}")
                with c2:
                    if activar_anticolapso:
                        st.metric(label="Límite Vertical Macro Permitido (ΔH_D + h)", value=f"{limite_critico_vertical:.2f} m")
            else:
                st.success("✅ Estabilidad confirmada bajo los parámetros actuales.")

        else:
            st.error("❌ Columnas del archivo no mapeadas.")
    except Exception as e:
        st.error(f"Error en el motor de cálculo: {e}")
else:
    st.info("👈 Carga el archivo de perfil para iniciar la simulación.")

# 6. BIBLIOGRAFÍA DE RESPALDO INSTITUCIONAL
st.markdown("""
<div class="discreet-note">
    <strong>Fuentes técnicas e internacionales de referencia:</strong><br>
    • <strong>Wang, Y., Zhang, J., et al. (2023).</strong> <em>Air valve arrangement criteria for preventing secondary pipe bursts in long-distance gravitational water supply systems.</em> AQUA - IWA Publishing.<br>
    • <strong>Instituto de Ingeniería, UNAM.</strong> <em>Manual de análisis de la problemática del aire atrapado en acueductos.</em> Serie Manuales, México.
</div>
""", unsafe_allow_html=True)
