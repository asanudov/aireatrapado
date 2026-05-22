import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
st.set_page_config(page_title="Analizador de Aire Atrapado", layout="wide")

# CSS para maximizar el uso del espacio y ajustar tipografías
st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; padding-bottom: 0rem; padding-left: 2rem; padding-right: 2rem; }
    h1 { font-size: 1.8rem !important; font-weight: 700; color: #1E3A8A; }
    .stNumberInput label { font-weight: 600; }
    .discreet-note { font-size: 11px; color: #888; margin-top: 30px; border-top: 1px solid #eee; padding-top: 10px; }
    /* Ajuste para que la sidebar se vea más profesional */
    [data-testid="stSidebar"] h1 { font-size: 1.2rem !important; line-height: 1.3; }
    </style>
""", unsafe_allow_html=True)

# 2. BARRA LATERAL (SIDEBAR) - Actualizada según instrucciones
st.sidebar.title("Analizador de Aire Atrapado en Conductos a Presión")

# Inputs de parámetros técnicos
q_m3s = st.sidebar.number_input("Caudal (m³/s)", min_value=0.000, value=0.075, step=0.001, format="%.3f")
d_m = st.sidebar.number_input("Diámetro Interno (m)", min_value=0.010, value=0.305, step=0.001, format="%.3f")

st.sidebar.markdown("---")
uploaded_file = st.sidebar.file_uploader("Carga tu perfil en Excel o CSV", type=["xlsx", "csv"])

st.sidebar.info("""
**Instrucciones del archivo:**
Debe contener columnas:
- Cadenamiento o Distancia (m)
- Elevación o Z (m)
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
        
        # Normalizar nombres de columnas
        df.columns = [c.lower().strip() for c in df.columns]
        col_x = next((c for c in df.columns if c in ['cadenamiento', 'distancia', 'x']), None)
        col_z = next((c for c in df.columns if c in ['elevación', 'elevacion', 'y', 'z']), None)

        if col_x and col_z:
            # Cálculos Hidráulicos
            area = np.pi * (d_m**2) / 4
            v_real = q_m3s / area
            g = 9.81

            # Detección de puntos altos
            df['es_cresta'] = (df[col_z] > df[col_z].shift(1)) & (df[col_z] > df[col_z].shift(-1))
            
            # Cálculo de Pendiente y Vc
            df['dx'] = df[col_x].diff()
            df['dz'] = df[col_z].diff()
            df['pendiente'] = df['dz'] / df['dx'].replace(0, np.nan)
            df['angulo_rad'] = np.arctan(np.abs(df['pendiente']))
            df['v_critica'] = np.sqrt(g * d_m) * (0.25 + np.sqrt(np.sin(df['angulo_rad'].fillna(0))))
            
            # Riesgo hidráulico
            df['riesgo_hidraulico'] = (df['pendiente'] < 0) & (v_real < df['v_critica'])

            # 4. GRÁFICO DE PERFIL - OPTIMIZADO PARA ANCHO HORIZONTAL
            st.subheader("Perfil Longitudinal del Acueducto")
            fig = go.Figure()

            # Trazado de tubería
            fig.add_trace(go.Scatter(
                x=df[col_x], y=df[col_z], 
                mode='lines', 
                name='Perfil de Tubería', 
                line=dict(color='#1E40AF', width=2.5)
            ))

            # Puntos altos - Terminología actualizada
            crestas = df[df['es_cresta']]
            fig.add_trace(go.Scatter(
                x=crestas[col_x], y=crestas[col_z], 
                mode='markers', 
                marker=dict(color='#F59E0B', size=12, symbol='triangle-up', line=dict(color='black', width=1)),
                name='Punto alto, acumulación por flotación'
            ))

            # Tramos con riesgo (Rojo)
            for i in range(1, len(df)):
                if df.loc[i, 'riesgo_hidraulico']:
                    fig.add_trace(go.Scatter(
                        x=[df.loc[i-1, col_x], df.loc[i, col_x]], 
                        y=[df.loc[i-1, col_z], df.loc[i, col_z]],
                        mode='lines', 
                        line=dict(color='#DC2626', width=4),
                        name='Arrastre Insuficiente' if i == df['riesgo_hidraulico'].idxmax() else "",
                        showlegend=(i == df['riesgo_hidraulico'].idxmax())
                    ))

            # Layout optimizado: Leyenda abajo y reducción de márgenes
            fig.update_layout(
                xaxis_title="Distancia (m)", 
                yaxis_title="Elevación (m)", 
                height=550,
                # Quitar márgenes laterales para que use todo el ancho
                margin=dict(l=10, r=10, t=20, b=10),
                legend=dict(
                    orientation="h",
                    yanchor="top",
                    y=-0.2, # Desplazado abajo del eje X
                    xanchor="center",
                    x=0.5
                ),
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)

            # 5. TABLA DE RESULTADOS
            st.subheader("Reporte de Puntos Críticos")
            res_table = df[(df['es_cresta']) | (df['riesgo_hidraulico'])].copy()
            
            if not res_table.empty:
                res_table['Tipo de Riesgo'] = np.where(res_table['es_cresta'], "Punto Alto (Flotación)", "Crítico (Falta de Arrastre)")
                res_table['V. Flujo (m/s)'] = round(v_real, 3)
                res_table['V. Crítica (m/s)'] = round(res_table['v_critica'], 3)
                
                output_cols = [col_x, col_z, 'Tipo de Riesgo', 'V. Flujo (m/s)', 'V. Crítica (m/s)']
                st.dataframe(res_table[output_cols].rename(columns={col_x: "Distancia (m)", col_z: "Elevación (m)"}), use_container_width=True)
            else:
                st.success("No se detectaron puntos críticos con las condiciones actuales.")

        else:
            st.error("Columnas 'Distancia' y 'Elevación' no encontradas.")
    except Exception as e:
        st.error(f"Error de archivo: {e}")
else:
    st.info("👈 Sube un archivo en el menú lateral para iniciar.")

# 6. BIBLIOGRAFÍA NOTA DISCRETA
st.markdown("""
<div class="discreet-note">
    <strong>Fuentes técnicas:</strong><br>
    • Wisner, P. E. (1965). <em>Estudio del criterio de Froude en arrastre de aire.</em><br>
    • Escarameia, M. (2000). <em>Air in pressurized water pipelines.</em>
</div>
""", unsafe_allow_html=True)

**Principales cambios realizados:**
1.  **Sidebar:** Se actualizó el título y el nombre del desarrollador con los grados y caracteres correctos.
2.  **Visualización:** Se usó `margin=dict(l=10, r=10)` y `legend=dict(orientation="h", y=-0.2)` para que el gráfico use el 100% del ancho de la pantalla de forma efectiva, sin que la leyenda le reste espacio lateral.
3.  **Simbología:** Se renombró el marcador a "Punto alto, acumulación por flotación".
4.  **UX:** Se redujo el espacio muerto superior (padding) para que el gráfico sea lo primero que se vea al cargar los datos.

¡Tu Web App ya está lista para actualizarse en GitHub!
