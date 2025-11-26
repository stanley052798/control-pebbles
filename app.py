import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# Configuración de la página
st.set_page_config(page_title="Control Pebbles", layout="wide", page_icon="🏗️")

# Nombre del archivo de base de datos
DB_FILE = 'avance_pebbles.csv'

# --- FUNCIÓN DE CARGA DE DATOS ---
def load_data():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    else:
        # Estructura inicial por defecto si no existe el archivo
        items_mecanicos = [f'Faja Transportadora {i+1}' for i in range(8)] + \
                          ['Estructuras Metálicas', 'Chancadora Pebbles 01', 'Chancadora Pebbles 02', 'Zaranda Vibratoria']
        items_civiles = ['Excavaciones', 'Solado', 'Encofrado', 'Vaciado de Concreto', 'Desencofrado']
        
        data = []
        for item in items_mecanicos:
            data.append({'Área': 'Mecánica/Estructural', 'Partida': item, 'Total (Ton)': 100.0, 'Ejecutado (Ton)': 0.0})
        for item in items_civiles:
            data.append({'Área': 'Obras Civiles', 'Partida': item, 'Total (Ton)': 100.0, 'Ejecutado (Ton)': 0.0})
        
        df_new = pd.DataFrame(data)
        df_new.to_csv(DB_FILE, index=False)
        return df_new

# --- FUNCIÓN DE GUARDADO ---
def save_data(df):
    df.to_csv(DB_FILE, index=False)

# Cargar datos al inicio
if 'df' not in st.session_state:
    st.session_state.df = load_data()

# Recargar variable local para manipulación
df = st.session_state.df

# --- SIDEBAR ---
st.sidebar.title("🏗️ Planta Pebbles")
st.sidebar.markdown("---")
opcion = st.sidebar.radio("Menú", ["Dashboard", "Reporte Diario", "Config. Metas"])

# --- CÁLCULO DE AVANCE ---
def calcular_progreso(row):
    if row['Total (Ton)'] == 0: return 0
    val = (row['Ejecutado (Ton)'] / row['Total (Ton)']) * 100
    return min(val, 100.0) # Cap al 100%

df['% Avance'] = df.apply(calcular_progreso, axis=1)

# --- VISTAS ---

# 1. CONFIGURACIÓN (METAS)
if opcion == "Config. Metas":
    st.header("⚙️ Configuración de Presupuesto (Metas)")
    st.warning("Edita los pesos totales (Ton) según el expediente técnico.")
    
    edited_df = st.data_editor(
        df, 
        column_config={
            "Total (Ton)": st.column_config.NumberColumn("Meta (Ton)", min_value=0, format="%.2f"),
            "Ejecutado (Ton)": st.column_config.NumberColumn(disabled=True),
            "% Avance": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
        },
        disabled=["Área", "Partida"],
        use_container_width=True,
        hide_index=True
    )
    
    if st.button("💾 Guardar Cambios en Metas"):
        st.session_state.df = edited_df
        save_data(edited_df)
        st.success("¡Metas actualizadas y guardadas!")
        st.rerun()

# 2. REPORTE DIARIO
elif opcion == "Reporte Diario":
    st.header("📝 Ingreso de Avance")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        area_sel = st.selectbox("Área", df['Área'].unique())
        # Filtramos partidas del área seleccionada
        items_area = df[df['Área'] == area_sel]['Partida'].tolist()
        partida_sel = st.selectbox("Partida", items_area)
    
    # Datos de la partida seleccionada
    idx = df[df['Partida'] == partida_sel].index[0]
    total = df.at[idx, 'Total (Ton)']
    ejecutado = df.at[idx, 'Ejecutado (Ton)']
    pendiente = total - ejecutado
    
    with col2:
        st.info(f"**Estado Actual: {partida_sel}**")
        c1, c2, c3 = st.columns(3)
        c1.metric("Meta", f"{total:,.1f}")
        c2.metric("Acumulado", f"{ejecutado:,.1f}")
        c3.metric("Pendiente", f"{pendiente:,.1f}")
    
    st.markdown("### Reportar Producción del Día")
    avance_input = st.number_input("Toneladas ejecutadas hoy:", min_value=0.0, step=0.5)
    
    if st.button("✅ Registrar Avance"):
        # Actualizar DF
        st.session_state.df.at[idx, 'Ejecutado (Ton)'] = ejecutado + avance_input
        # Guardar en CSV
        save_data(st.session_state.df)
        st.success(f"Registrado. Nuevo acumulado: {ejecutado + avance_input} Ton")
        st.rerun()

# 3. DASHBOARD
elif opcion == "Dashboard":
    st.title("📊 Tablero de Control")
    
    # KPIs
    tot = df['Total (Ton)'].sum()
    exe = df['Ejecutado (Ton)'].sum()
    av_gen = (exe/tot)*100 if tot > 0 else 0
    
    k1, k2, k3 = st.columns(3)
    k1.metric("Peso Total Proyecto", f"{tot:,.0f} Ton")
    k2.metric("Ejecutado Total", f"{exe:,.0f} Ton", delta=f"{av_gen:.1f}% Avance")
    k3.progress(av_gen/100)
    
    st.markdown("---")
    
    c_chart1, c_chart2 = st.columns(2)
    
    with c_chart1:
        st.subheader("Avance por Disciplina")
        # Agrupar por área
        df_area = df.groupby('Área')[['Total (Ton)', 'Ejecutado (Ton)']].sum().reset_index()
        df_area['%'] = (df_area['Ejecutado (Ton)'] / df_area['Total (Ton)'] * 100)
        
        fig = px.bar(df_area, x='Área', y=['Ejecutado (Ton)', 'Total (Ton)'], barmode='overlay', title="Comparativo Meta vs Ejecutado")
        st.plotly_chart(fig, use_container_width=True)
        
    with c_chart2:
        st.subheader("Detalle Crítico")
        # Filtrar solo lo que tiene avance pero no está terminado
        df_active = df[(df['Ejecutado (Ton)'] > 0) & (df['Ejecutado (Ton)'] < df['Total (Ton)'])]
        if not df_active.empty:
            fig2 = px.funnel(df_active, x='Ejecutado (Ton)', y='Partida', title="Partidas en Ejecución")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No hay partidas en proceso intermedio actualmente.")

    with st.expander("Ver Tabla Completa de Datos"):
        st.dataframe(df.style.background_gradient(subset=['% Avance'], cmap='Greens'))
