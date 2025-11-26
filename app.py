import streamlit as st
import pandas as pd
import plotly.express as px
import os
import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Control Pebbles Histórico", layout="wide", page_icon="📅")

FILE_CATALOGO = 'pebbles_catalogo.csv'   # Guarda las Metas, Unidades, Fotos
FILE_HISTORIAL = 'pebbles_historial.csv' # Guarda CADA avance reportado con fecha

# --- LÓGICA DE OBRAS CIVILES (Predecesoras) ---
JERARQUIA_CIVIL = {
    'Excavaciones': None,
    'Solado': 'Excavaciones',
    'Encofrado': 'Solado',
    'Vaciado de Concreto': 'Encofrado',
    'Desencofrado': 'Vaciado de Concreto'
}

# --- FUNCIONES DE BASE DE DATOS ---

def init_db():
    # 1. Inicializar Catálogo (Si no existe)
    if not os.path.exists(FILE_CATALOGO):
        items_mecanicos = [f'Faja Transportadora {i+1}' for i in range(8)] + \
                          ['Estructuras Metálicas', 'Chancadora 01', 'Chancadora 02', 'Zaranda']
        items_civiles = list(JERARQUIA_CIVIL.keys())
        
        data = []
        for it in items_mecanicos:
            data.append({'Disciplina': 'Mecánica', 'Partida': it, 'Unidad': 'Ton', 'Meta': 100.0, 'Img': ''})
        for it in items_civiles:
            uni = 'm³' if it in ['Excavaciones','Vaciado de Concreto'] else 'Und'
            data.append({'Disciplina': 'Civil', 'Partida': it, 'Unidad': uni, 'Meta': 100.0, 'Img': ''})
            
        pd.DataFrame(data).to_csv(FILE_CATALOGO, index=False)

    # 2. Inicializar Historial (Vacío al principio)
    if not os.path.exists(FILE_HISTORIAL):
        df_hist = pd.DataFrame(columns=['Fecha', 'Disciplina', 'Partida', 'Cantidad', 'Nota'])
        df_hist.to_csv(FILE_HISTORIAL, index=False)

def load_data():
    cat = pd.read_csv(FILE_CATALOGO)
    hist = pd.read_csv(FILE_HISTORIAL)
    # Convertir columna fecha a datetime
    if not hist.empty:
        hist['Fecha'] = pd.to_datetime(hist['Fecha']).dt.date
    return cat, hist

def get_acumulados(df_cat, df_hist):
    # Sumariza el historial para saber cuánto llevamos acumulado por partida
    if df_hist.empty:
        df_cat['Ejecutado'] = 0.0
    else:
        resumen = df_hist.groupby('Partida')['Cantidad'].sum().reset_index()
        df_cat = pd.merge(df_cat, resumen, on='Partida', how='left').fillna(0)
        df_cat.rename(columns={'Cantidad': 'Ejecutado'}, inplace=True)
    
    # Calcular %
    df_cat['% Avance'] = (df_cat['Ejecutado'] / df_cat['Meta']) * 100
    df_cat['% Avance'] = df_cat['% Avance'].clip(upper=100) # Tope visual 100%
    return df_cat

# Inicialización
init_db()
df_cat_raw, df_hist_raw = load_data()
df_master = get_acumulados(df_cat_raw.copy(), df_hist_raw.copy()) # Master tiene Metas + Acumulados

# --- INTERFAZ ---
st.sidebar.title("🏗️ Gestión Temporal")
menu = st.sidebar.radio("Navegación", ["Panel de Control (Dashboard)", "Reportar Avance Diario", "Configuración Metas"])

# ==============================================================================
# 1. CONFIGURACIÓN (Metas y Fotos)
# ==============================================================================
if menu == "Configuración Metas":
    st.header("⚙️ Configuración del Expediente Técnico")
    st.info("Edita aquí las Metas Totales y enlaces a Fotos.")
    
    edited_cat = st.data_editor(
        df_cat_raw,
        column_config={
            "Meta": st.column_config.NumberColumn(min_value=0.1, format="%.2f"),
            "Img": st.column_config.LinkColumn("Foto URL"),
            "Disciplina": st.column_config.TextColumn(disabled=True),
            "Partida": st.column_config.TextColumn(disabled=True),
            "Unidad": st.column_config.TextColumn(disabled=True)
        },
        use_container_width=True,
        hide_index=True
    )
    
    if st.button("💾 Guardar Cambios en Catálogo"):
        edited_cat.to_csv(FILE_CATALOGO, index=False)
        st.success("Catálogo actualizado.")
        st.rerun()

# ==============================================================================
# 2. REPORTAR AVANCE (Inputs con Fecha)
# ==============================================================================
elif menu == "Reportar Avance Diario":
    st.header("📝 Registro de Actividad")
    
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        disc_sel = st.selectbox("Disciplina", df_master['Disciplina'].unique())
        # Filtrar partidas de esa disciplina
        partidas_disp = df_master[df_master['Disciplina'] == disc_sel]['Partida'].unique()
        partida_sel = st.selectbox("Partida / Elemento", partidas_disp)
    
    # Obtener datos actuales del Master
    row = df_master[df_master['Partida'] == partida_sel].iloc[0]
    pendiente = row['Meta'] - row['Ejecutado']
    
    with col_sel2:
        # Visualizar foto si existe
        if pd.notna(row['Img']) and str(row['Img']).startswith('http'):
            st.image(row['Img'], caption=f"Ref: {partida_sel}", width=200)
    
    st.divider()
    
    # FORMULARIO DE INGRESO
    col_inp1, col_inp2, col_inp3 = st.columns(3)
    
    with col_inp1:
        fecha_input = st.date_input("Fecha de Ejecución", datetime.date.today())
    
    with col_inp2:
        qty_input = st.number_input(f"Cantidad Avanzada ({row['Unidad']})", min_value=0.0, step=1.0)
        
    with col_inp3:
        nota_input = st.text_input("Nota / Comentario (Opcional)", placeholder="Ej. Turno noche, Sector B")

    # VALIDACIÓN DE LÓGICA CIVIL (PREDECESORAS)
    bloqueo_logico = False
    
    if disc_sel == "Civil":
        predecesor = JERARQUIA_CIVIL.get(partida_sel)
        if predecesor:
