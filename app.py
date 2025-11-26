import streamlit as st
import pandas as pd
import plotly.express as px
import os

# Configuración de la página
st.set_page_config(page_title="Control Pebbles v3", layout="wide", page_icon="🏗️")

DB_FILE = 'avance_pebbles_v3.csv'

# --- DEFINICIÓN DE JERARQUÍA Y UNIDADES ---
# Diccionario de predecesoras: 'Actividad': 'Su_Predecesora'
JERARQUIA_CIVIL = {
    'Excavaciones': None,            # Es la primera
    'Solado': 'Excavaciones',
    'Encofrado': 'Solado',
    'Vaciado de Concreto': 'Encofrado',
    'Desencofrado': 'Vaciado de Concreto'
}

UNIDADES_CIVIL = {
    'Excavaciones': 'm³',
    'Solado': 'Und',
    'Encofrado': 'Und',
    'Vaciado de Concreto': 'm³',
    'Desencofrado': 'Und'
}

# --- FUNCIÓN DE CARGA DE DATOS ---
def load_data():
    # Estructura Mecánica (Igual que antes)
    items_mecanicos = [f'Faja Transportadora {i+1}' for i in range(8)] + \
                        ['Estructuras Metálicas', 'Chancadora Pebbles 01', 'Chancadora Pebbles 02', 'Zaranda Vibratoria']
    
    # Estructura Civil (Basada en tu jerarquía)
    items_civiles = list(JERARQUIA_CIVIL.keys())

    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        df = df.fillna('')
        # Asegurar columna unidad si viene de versión anterior
        if 'Unidad' not in df.columns:
            df['Unidad'] = 'Ton' 
        return df
    else:
        data = []
        # Mecánica
        for item in items_mecanicos:
            data.append({
                'Disciplina': 'Mecánica/Estructural', 
                'Partida': item, 
                'Unidad': 'Ton',
                'Total': 100.0, 
                'Ejecutado': 0.0, 
                'Imagen URL': ''
            })
        # Civil
        for item in items_civiles:
            data.append({
                'Disciplina': 'Obras Civiles', 
                'Partida': item, 
                'Unidad': UNIDADES_CIVIL[item], # Asignamos la unidad correcta
                'Total': 100.0, 
                'Ejecutado': 0.0, 
                'Imagen URL': ''
            })
        
        df_new = pd.DataFrame(data)
        df_new.to_csv(DB_FILE, index=False)
        return df_new

def save_data(df):
    df.to_csv(DB_FILE, index=False)

# Cargar estado
if 'df_v3' not in st.session_state:
    st.session_state.df_v3 = load_data()

df = st.session_state.df_v3.copy()

# Cálculo de avance porcentual
def get_progress(row):
    if row['Total'] <= 0: return 0
    return min((row['Ejecutado'] / row['Total']) * 100, 100.0)

df['% Avance'] = df.apply(get_progress, axis=1)

# --- SIDEBAR ---
with st.sidebar:
    st.title("🏗️ Control Pebbles")
    st.caption("v3.0 Lógica Constructiva")
    st.markdown("---")
    opcion = st.radio("Menú", ["Dashboard General", "Reportar Avance", "Configuración"])

# --- VISTAS ---

# 1. CONFIGURACIÓN
if opcion == "Configuración":
    st.header("⚙️ Configuración del Expediente")
    st.info("Define los metrados totales para cada disciplina.")
    
    # Separamos en dos tabs para orden
    tab_mec, tab_civ = st.tabs(["🔩 Mecánica (Ton)", "🧱 Obras Civiles (Mix)"])
    
    with tab_mec:
        df_mec = df[df['Disciplina'] == 'Mecánica/Estructural']
        edited_mec = st.data_editor(
            df_mec,
            column_config={
                "Total": st.column_config.NumberColumn("Meta (Ton)", min_value=0.1, format="%.2f"),
                "Unidad": st.column_config.TextColumn(disabled=True),
                "Ejecutado": st.column_config.NumberColumn(disabled=True),
                "Imagen URL": st.column_config.LinkColumn("Foto Ref.")
            },
            disabled=["Disciplina", "Partida"],
            hide_index=True,
            use_container_width=True,
            key="edit_mec"
        )
    
    with tab_civ:
        df_civ = df[df['Disciplina'] == 'Obras Civiles']
        edited_civ = st.data_editor(
            df_civ,
            column_config={
                "Total": st.column_config.NumberColumn("Meta Total", min_value=0.1, format="%.2f"),
                "Unidad": st.column_config.TextColumn("Unidad", disabled=True), # Unidad fija por lógica
                "Ejecutado": st.column_config.NumberColumn(disabled=True),
                "Imagen URL": st.column_config.LinkColumn("Foto Ref.")
            },
            disabled=["Disciplina", "Partida", "Unidad"], # Bloqueamos unidad para no romper lógica
            hide_index=True,
            use_container_width=True,
            key="edit_civ"
        )

    if st.button("💾 Guardar Cambios"):
        # Combinar los dataframes editados y guardar
        # Nota: Pandas update logic simplificada
        df_final = pd.concat([edited_mec, edited_civ])
        # Aseguramos el orden original si es necesario, pero concat funciona bien aquí
        st.session_state.df_v3 = df_final
        save_data(df_final)
        st.success("Metrados actualizados correctamente.")
        st.rerun()

# 2. REPORTAR AVANCE (CON VALIDACIÓN)
elif opcion == "Reportar Avance":
    st.header("📝 Registro de Campo")
    
    tipo_trabajo = st.selectbox("Disciplina", ["Obras Civiles", "Mecánica/Estructural"])
    
    df_filtrado = df[df['Disciplina'] == tipo_trabajo]
    partida_sel = st.selectbox("Actividad / Elemento", df_filtrado['Partida'].tolist())
    
    # Datos actuales
    idx = df[df['Partida'] == partida_sel].index[0] # Buscar en DF original
    row = df.loc[idx]
    
    # --- VISUALIZACIÓN ---
    c1, c2 = st.columns([1, 2])
    with c1:
        if row['Imagen URL']:
            st.image(row['Imagen URL'], use_column_width=True)
        else:
            st.info("Sin imagen de referencia")
            
    with c2:
        st.metric(f"Meta ({row['Unidad']})", f"{row['Total']:,.2f}")
        st.metric(f"Ejecutado ({row['Unidad']})", f"{row['Ejecutado']:,.2f}", delta=f"{row['% Avance']:.1f}%")
        
    st.divider()
    
    # --- LÓGICA DE VALIDACIÓN (PREDECESORAS) ---
    bloqueado = False
    mensaje_bloqueo = ""
    
    if tipo_trabajo == "Obras Civiles":
        predecesora = JERARQUIA_CIVIL.get(partida_sel)
        
        if predecesora:
            # Buscar datos de la predecesora
            row_pred = df[(df['Disciplina']=='Obras Civiles') & (df['Partida']==predecesora)].iloc[0]
            avance_pred = get_progress(row_pred)
            avance_actual = row['% Avance']
            
            # REGLA: No puedes tener más % de avance en la actual que en la predecesora
            # (Asumiendo linealidad S-Curve para control simple)
            st.caption(f"🔗 Dependencia: Esta actividad requiere **{predecesora}** (Avance actual: {avance_pred:.1f}%)")
            
            if avance_actual >= avance_pred and avance_pred < 100:
                # Caso borde: Si ya igualaste el porcentaje, no puedes avanzar más hasta que la otra avance
                # O un chequeo simple: Si predecesora es 0%, actual no puede moverse.
                if avance_pred == 0:
                    bloqueado = True
                    mensaje_bloqueo = f"⛔ NO INICIADO: La actividad predecesora '{predecesora}' tiene 0% de avance."
            
            # Calculamos límite teórico de toneladas/unidades que se pueden reportar hoy
            # (Opcional: podrías permitir desfases, pero seremos estrictos según tu pedido)
            max_posible_pct = avance_pred
            max_posible_qty = (max_posible_pct / 100) * row['Total']
            
            # Si quieres ser MUY estricto (Actual no puede superar a Predecesora):
            qty_restante_logico = max_posible_qty - row['Ejecutado']
            
            if qty_restante_logico <= 0 and avance_pred < 100:
                st.warning(f"⚠️ Alerta de Secuencia: El avance de {partida_sel} ({avance_actual:.1f}%) ya alcanzó al de {predecesora}. Debe avanzar la predecesora primero.")

    # Input de datos
    pendiente_fisico = row['Total'] - row['Ejecutado']
    
    if bloqueado:
        st.error(mensaje_bloqueo)
    else:
        nuevo_avance = st.number_input(
            f"Ingresar cantidad ejecutada hoy ({row['Unidad']}):", 
            min_value=0.0, 
            max_value=float(pendiente_fisico) + 0.1, # Tolerancia pequeña
            step=1.0
        )
        
        if st.button("Registrar Producción"):
            # Validación final antes de guardar
            es_valido = True
            
            # Re-verificación de lógica civil al guardar (para evitar bypass)
            if tipo_trabajo == "Obras Civiles" and predecesora:
                pct_futuro = ((row['Ejecutado'] + nuevo_avance) / row['Total']) * 100
                row_pred = df[(df['Disciplina']=='Obras Civiles') & (df['Partida']==predecesora)].iloc[0]
                pct_pred = get_progress(row_pred)
                
                # Tolerancia del 5% para permitir traslapes lógicos en obra
                if pct_futuro > (pct_pred + 5): 
                    st.toast(f"🚫 Error Lógico: {partida_sel} no puede superar significativamente a {predecesora}", icon="❌")
                    es_valido = False

            if es_valido and nuevo_avance > 0:
                st.session_state.df_v3.at[idx, 'Ejecutado'] += nuevo_avance
                save_data(st.session_state.df_v3)
                st.success("✅ Avance registrado correctamente")
                st.rerun()

# 3. DASHBOARD
elif opcion == "Dashboard General":
    st.title("📊 Tablero de Control")
    
    # KPIs Separados
    col1, col2 = st.columns(2)
    
    # KPI Mecánico
    df_mec = df[df['Disciplina'] == 'Mecánica/Estructural']
    tot_mec = df_mec['Total'].sum()
    exe_mec = df_mec['Ejecutado'].sum()
    av_mec = (exe_mec/tot_mec)*100 if tot_mec > 0 else 0
    
    with col1:
        st.markdown("### 🔩 Montaje Mecánico")
        st.metric("Peso Total", f"{tot_mec:,.0f} Ton")
        st.progress(av_mec/100)
        st.write(f"**{av_mec:.2f}%** Completado")

    # KPI Civil (Promedio ponderado es difícil con unidades mixtas, usamos % promedio de actividades)
    df_civ = df[df['Disciplina'] == 'Obras Civiles']
    # Calculamos avance promedio simple de las 5 actividades para tener una idea global
    av_civ = df_civ['% Avance'].mean()
    
    with col2:
        st.markdown("### 🧱 Obras Civiles")
        st.metric("Actividades Críticas", f"{len(df_civ)}")
        st.progress(av_civ/100)
        st.write(f"**{av_civ:.2f}%** Promedio Avance Físico")

    st.markdown("---")
    
    # Gráficos de Obras Civiles (Diagrama de Flujo visual)
    st.subheader("Estado del Flujo Civil")
    
    # Creamos un gráfico de barras ordenado por la jerarquía
    orden_civil = list(JERARQUIA_CIVIL.keys())
    df_civ_ordenado = df_civ.set_index('Partida').reindex(orden_civil).reset_index()
    
    fig_civ = px.bar(
        df_civ_ordenado, 
        x='Partida', 
        y='% Avance',
        color='% Avance',
        color_continuous_scale='RdYlGn',
        range_y=[0, 100],
        text_auto='.1f',
        title="Secuencia Constructiva (Validación de Predecesoras)"
    )
    # Agregamos flechas o líneas para denotar dependencia visualmente
    fig_civ.update_traces(marker_line_color='black', marker_line_width=1.5)
    st.plotly_chart(fig_civ, use_container_width=True)
    
    st.markdown("""
    > **Nota:** El gráfico debe mostrar una escalera descendente (o igualada). 
    > Si una barra a la derecha es más alta que su vecina izquierda, hay una inconsistencia en el reporte.
    """)

    st.subheader("Detalle Mecánico")
    st.dataframe(df_mec[['Partida', 'Total', 'Ejecutado', '% Avance', 'Unidad']], use_container_width=True)
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
