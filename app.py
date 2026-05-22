import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
st.set_page_config(page_title="Analizador de Aire Atrapado", layout="wide")

# CSS personalizado para maximizar ancho horizontal y ajustar títulos
st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; padding-bottom: 0rem; padding-left: 2rem; padding-right: 2rem; }
    h1 { font-size: 1.8rem !important; font-weight: 700; color: #1E3A8A; }
    .stNumberInput label { font-weight: 600; }
    .discreet-note { font-size: 11px; color: #888; margin-top: 30px; border-top: 1px solid #eee; padding-top: 10px; }
    [data-testid="stSidebar"] h1 { font-size: 1.2rem !important; line-height: 1.3; }
    </style>
""", unsafe_allow_html=True)

# 2. BARRA LATERAL (SIDEBAR) - Identidad de la App
st.sidebar.title("Analizador de Aire Atrapado en Conductos a Presión")

# Inputs de parámetros del sistema
q_m3s = st.sidebar.number_input("Caudal (m³/s)", min_value=0.000, value=0.075, step=0.001, format="%.3f")
d_m = st.sidebar.number_input("Diámetro Interno (m)", min_value=0.010, value=0.305, step=0.001, format="%.3f")

st.sidebar.markdown("---")
uploaded_file = st.sidebar.file_uploader("Carga tu perfil en Excel o CSV", type=["xlsx", "csv"])

# Instrucciones de formato del .csv estrictas tal como se solicitaron
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

# 3. CUERPO PRINCIPAL
st.title("Analizador de Aire Atrapado en Conductos a Presión")

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        # Normalizar nombres de columnas a minúsculas y quitar espacios libres
        df.columns = [c.lower().strip() for c in df.columns]
        
        # Mapeo dinámico de los encabezados solicitados
        col_x = next((c for c in df.columns if c in ['cadenamiento', 'distancia', 'x']), None)
        col_z = next((c for c in df.columns if c in ['elevación', 'elevacion', 'y']), None)

        if col_x and col_z:
            g = 9.81
            
            # Alerta técnica de Diámetro Crítico (Efecto de Capilaridad / Zukoski)
            if d_m < 0.100:
                st.warning("⚠️ **Nota técnica:** El diámetro ingresado es menor a 100 mm (4 pulgadas). En tuberías pequeñas, los efectos de tensión superficial y capilaridad pueden alterar el comportamiento del aire respecto al modelo matemático de arrastre hidráulico por gravedad.")

            # ---- LÓGICA DE CÁLCULO: MANUAL II-UNAM ----
            
            # 1. Gasto Adimensional (PGA) constante del sistema
            pga_sistema = q_m3s / np.sqrt(g * (d_m**5))
            
            # 2. Detección geométrica de puntos altos (Picos locales por flotación)
            df['es_cresta'] = (df[col_z] > df[col_z].shift(1)) & (df[col_z] > df[col_z].shift(-1))
            
            # 3. Análisis cinemático por tramos (Consecutivos)
            df['dx'] = df[col_x].diff()
            df['dz'] = df[col_z].diff()
            
            # Pendiente S (El manual la define positiva si el tramo es descendente: Y_anterior - Y_actual)
            df['S'] = -df['dz'] / df['dx'].replace(0, np.nan)
            
            # 4. Evaluación de la Capacidad de Arrastre
            # El aire se estaciona si el tramo es descendente (S > 0) y el PGA del flujo no supera a sqrt(S)
            df['riesgo_hidraulico'] = (df['S'] > 0) & (pga_sistema < np.sqrt(df['S'].fillna(0)))
            
            # Calcular la Velocidad Crítica de remoción (Kalinske y Bliss) para el reporte
            df['v_critica'] = 1.146 * np.sqrt(g * d_m * df['S'])
            df['v_critica'] = df['v_critica'].fillna(0)
            
            # Velocidad real del flujo
            area = np.pi * (d_m**2) / 4
            v_real = q_m3s / area

            # 4. GRÁFICO DE PERFIL LONGITUDINAL (OPTIMIZADO EN LA HORIZONTAL)
            st.subheader("Perfil Longitudinal del Acueducto")
            fig = go.Figure()

            # Trazado de la tubería
            fig.add_trace(go.Scatter(
                x=df[col_x], y=df[col_z], 
                mode='lines', 
                name='Perfil de Tubería', 
                line=dict(color='#1E40AF', width=2.5)
            ))

            # Marcadores de Puntos Altos (Terminología exacta solicitada)
            crestas = df[df['es_cresta']]
            fig.add_trace(go.Scatter(
                x=crestas[col_x], y=crestas[col_z], 
                mode='markers', 
                marker=dict(color='#F59E0B', size=12, symbol='triangle-up', line=dict(color='black', width=1)),
                name='Punto alto, acumulación por flotación'
            ))

            # Resaltar en rojo los tramos con arrastre insuficiente (Aire Estacionario)
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

            # Layout optimizado: Leyenda ABAJO para no restar espacio horizontal al perfil
            fig.update_layout(
                xaxis_title="Distancia (m)", 
                yaxis_title="Elevación (m)", 
                height=550,
                margin=dict(l=10, r=10, t=20, b=10), # Minimiza márgenes laterales para extender el eje X
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

            # 5. TABLA DE REPORTES / RESULTADOS
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
                
                # Filtrado y renombrado estricto de columnas para presentación profesional
                output_cols = [col_x, col_z, 'Pendiente (S)', 'Diagnóstico del Aire', 'V. Flujo (m/s)', 'V. Mínima Barrido (m/s)']
                st.dataframe(
                    res_table[output_cols].rename(columns={col_x: "Distancia (m)", col_z: "Elevación (m)"}), 
                    use_container_width=True
                )
                
                # Indicador de Parámetro de Gasto Adimensional constante
                st.metric(label="Parámetro de Gasto Adimensional (PGA) del Sistema", value=f"{pga_sistema:.4f}")
            else:
                st.success("✅ El sistema opera con estabilidad. No se detectaron puntos altos ni tramos con insuficiencia de arrastre para la combinación de Q y D configurada.")

        else:
            st.error("❌ Formato inválido. Asegúrate de que las columnas del archivo sigan estrictamente las instrucciones de la barra lateral (Cadenamiento/Distancia/X y Elevación/Y).")
    except Exception as e:
        st.error(f"Error al leer o procesar el archivo cargado: {e}")
else:
    st.info("👈 Por favor, configura las variables de diseño e ingresa tu archivo de perfil (.csv o .xlsx) en el menú lateral para iniciar el análisis hidráulico.")

# 6. FUENTES BIBLIOGRÁFICAS DISCRETAS (CONFORME A MANUAL II-UNAM)
st.markdown("""
<div class="discreet-note">
    <strong>Fuentes técnicas e institucionales de referencia:</strong><br>
    • Instituto de Ingeniería, UNAM. <em>Manual de análisis de la problemática del aire atrapado en acueductos, para mejorar su eficiencia.</em> Serie Manuales, México.<br>
    • Kalinske, A. A., & Bliss, P. H. (1943). <em>Removal of air from pipe lines by flowing water.</em> Civil Engineering, 13(10).<br>
    • Zukoski, E. E. (1966). <em>Influence of viscosity, surface tension and inclination on motion of long bubbles in closed tubes.</em> Journal of Fluid Mechanics.
</div>
""", unsafe_allow_html=True)
