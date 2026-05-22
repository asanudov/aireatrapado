import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
st.set_page_config(page_title="Analizador de Aire Atrapado", layout="wide")

# CSS personalizado para reducir espacios, ajustar tamaños de título y notas discretas
st.markdown("""
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 1rem; }
    h1 { font-size: 2.2rem !important; margin-bottom: 0 !important; padding-bottom: 0 !important; }
    .discreet-note { font-size: 11px; color: #888; margin-top: 40px; border-top: 1px solid #eee; padding-top: 10px; }
    </style>
""", unsafe_allow_html=True)

# 2. BARRA LATERAL (SIDEBAR)
st.sidebar.title("Configuración")

# Inputs de parámetros
q_m3s = st.sidebar.number_input("Caudal (m³/s)", min_value=0.001, value=0.150, format="%.3f")
d_m = st.sidebar.number_input("Diámetro Interno (m)", min_value=0.01, value=0.400, format="%.3f")

st.sidebar.markdown("---")
uploaded_file = st.sidebar.file_uploader("Carga tu perfil en Excel o CSV", type=["xlsx", "csv"])

st.sidebar.info("""
**Instrucciones del archivo:**
Debe contener dos columnas (no importa el orden):
- Distancia, cadenamiento o x (m)
- Elevación, z o y (m)
""")

st.sidebar.markdown("---")
st.sidebar.write("**Desarrollado por: Ing. Alan Sanudo**")

# 3. CUERPO PRINCIPAL
st.title("Analizador de Aire Atrapado en Conductos a Presión")
st.markdown("Detección de puntos críticos por acumulación geométrica e insuficiencia de arrastre hidráulico.")

if uploaded_file:
    # Leer datos según la extensión
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        # Normalizar nombres de columnas a minúsculas
        df.columns = [c.lower().strip() for c in df.columns]
        
        # Identificar columnas dinámicamente
        col_x = next((c for c in df.columns if c in ['cadenamiento', 'distancia', 'x']), None)
        col_z = next((c for c in df.columns if c in ['elevación', 'elevacion', 'y', 'z']), None)

        if col_x and col_z:
            # 4. CÁLCULOS HIDRÁULICOS
            area = np.pi * (d_m**2) / 4
            v_real = q_m3s / area
            g = 9.81

            # Detectar crestas (Z actual mayor que el anterior y mayor que el siguiente)
            df['es_cresta'] = (df[col_z] > df[col_z].shift(1)) & (df[col_z] > df[col_z].shift(-1))
            
            # Calcular pendientes y Velocidad Crítica (Ecuación de Wisner)
            df['dx'] = df[col_x].diff()
            df['dz'] = df[col_z].diff()
            
            # Evitar división por cero
            df['dx'] = df['dx'].replace(0, np.nan)
            df['pendiente'] = df['dz'] / df['dx']
            df['angulo_rad'] = np.arctan(np.abs(df['pendiente']))
            
            # Vc = sqrt(g*D) * (0.25 + sqrt(sin(theta)))
            df['v_critica'] = np.sqrt(g * d_m) * (0.25 + np.sqrt(np.sin(df['angulo_rad'].fillna(0))))
            
            # Detectar tramos con riesgo (Pendiente descendente y V_real < V_critica)
            df['riesgo_hidraulico'] = (df['pendiente'] < 0) & (v_real < df['v_critica'])

            # 5. GRÁFICO DE PERFIL (PLOTLY)
            st.subheader("Perfil Longitudinal del Acueducto")
            fig = go.Figure()

            # Trazar tubería principal
            fig.add_trace(go.Scatter(
                x=df[col_x], y=df[col_z], 
                mode='lines+markers', 
                name='Perfil de Tubería', 
                line=dict(color='#005088', width=2),
                marker=dict(size=4)
            ))

            # Resaltar Crestas (Trampas geométricas)
            crestas = df[df['es_cresta']]
            fig.add_trace(go.Scatter(
                x=crestas[col_x], y=crestas[col_z], 
                mode='markers', 
                marker=dict(color='#FF9F1C', size=14, symbol='triangle-up', line=dict(color='black', width=1)),
                name='Cresta Local (Acumulación Geométrica)'
            ))

            # Resaltar Tramos Críticos (Arrastre insuficiente)
            for i in range(1, len(df)):
                if df.loc[i, 'riesgo_hidraulico']:
                    fig.add_trace(go.Scatter(
                        x=[df.loc[i-1, col_x], df.loc[i, col_x]], 
                        y=[df.loc[i-1, col_z], df.loc[i, col_z]],
                        mode='lines', 
                        line=dict(color='#E71D36', width=5),
                        name='Arrastre Insuficiente' if i == df['riesgo_hidraulico'].idxmax() else "", # Solo mostrar en leyenda una vez
                        showlegend=(i == df['riesgo_hidraulico'].idxmax())
                    ))

            fig.update_layout(
                xaxis_title="Distancia (m)", 
                yaxis_title="Elevación (m)", 
                height=500,
                margin=dict(l=20, r=20, t=30, b=20),
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)

            # 6. TABLA DE RESULTADOS
            st.subheader("Reporte de Puntos Críticos")
            
            # Filtrar solo los puntos que tienen algún riesgo
            res_table = df[(df['es_cresta']) | (df['riesgo_hidraulico'])].copy()
            
            if not res_table.empty:
                res_table['Tipo de Riesgo'] = np.where(res_table['es_cresta'], "Geométrico (Cresta)", "Hidráulico (Falta de Arrastre)")
                res_table['V. Flujo (m/s)'] = round(v_real, 3)
                res_table['V. Crítica (m/s)'] = round(res_table['v_critica'], 3)
                
                output_cols = [col_x, col_z, 'Tipo de Riesgo', 'V. Flujo (m/s)', 'V. Crítica (m/s)']
                
                # Renombrar para presentación
                res_table = res_table[output_cols].rename(columns={col_x: "Cadenamiento (m)", col_z: "Elevación (m)"})
                
                st.dataframe(res_table, use_container_width=True)
            else:
                st.success("No se detectaron puntos críticos geométricos ni hidráulicos con la configuración actual.")

        else:
            st.error("No se detectaron las columnas requeridas. Asegúrate de que los encabezados sean 'x', 'distancia' o 'cadenamiento' para la longitud, y 'y', 'z' o 'elevacion' para la altura.")
            
    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")

else:
    st.info("👈 Sube un archivo de Excel o CSV en el menú lateral para comenzar el análisis.")

# 7. FUENTES Y NOTA DISCRETA
st.markdown("""
<div class="discreet-note">
    <strong>Bibliografía de referencia:</strong><br>
    • Wisner, P. E. (1965). <em>Sur le rôle du critère de Froude dans l’étude de l’entraînement de l’air par les courants a grande vitesse.</em><br>
    • Escarameia, M., & Swaffield, J. A. (2000). <em>Air in pressurized water pipelines: a review of the state of the art.</em>
</div>
""", unsafe_allow_html=True)