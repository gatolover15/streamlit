import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# --------------------------
# CONFIGURACIÓN INICIAL
# --------------------------
st.set_page_config(page_title="📊 Análisis Financiero", layout="wide")

# --------------------------
# SISTEMA DE AUTENTICACIÓN
# --------------------------
# Credenciales hardcodeadas (cambiar por un sistema más seguro en producción)
USUARIOS = {
    "jorgevidea": "jorgevidea10"
}

# Inicializar session_state
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "link_sheets" not in st.session_state:
    st.session_state.link_sheets = ""

# --------------------------
# FUNCIÓN PARA CARGAR DATOS
# --------------------------
@st.cache_data
def cargar_datos_google_public(link_hoja):
    """Carga un Google Sheet público (link normal o CSV export)"""
    try:
        if "export?format=csv" not in link_hoja:
            sheet_id = link_hoja.split("/d/")[1].split("/")[0]
            gid = "0"
            if "gid=" in link_hoja:
                gid = link_hoja.split("gid=")[1].split("&")[0]
            link_hoja = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        data = pd.read_csv(link_hoja)
        return data
    except Exception as e:
        st.error(f"❌ Error cargando los datos: {e}")
        return pd.DataFrame()

# --------------------------
# FUNCIÓN PARA NORMALIZAR TEXTO (sin tildes)
# --------------------------
def normalizar_texto(texto):
    """Elimina tildes y convierte a minúsculas"""
    import unicodedata
    if pd.isna(texto):
        return ""
    texto = str(texto).lower()
    # Normaliza y elimina tildes
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(char for char in texto if unicodedata.category(char) != 'Mn')
    return texto

# --------------------------
# FUNCIÓN PARA FILTRAR DATOS
# --------------------------
def filtrar_datos(df, start_date, end_date, razon, excluir, mes, año):
    df_filtered = df.copy()

    if año != "Todos":
        df_filtered = df_filtered[df_filtered["Fecha"].dt.year == int(año)]
    if mes != "Todos":
        df_filtered = df_filtered[df_filtered["MesNombre"] == mes]
    if start_date:
        df_filtered = df_filtered[df_filtered["Fecha"] >= pd.to_datetime(start_date)]
    if end_date:
        df_filtered = df_filtered[df_filtered["Fecha"] <= pd.to_datetime(end_date)]
    if razon:
        # Normalizar el texto de búsqueda
        razon_normalizada = normalizar_texto(razon)
        # Crear columna temporal normalizada para comparación
        df_filtered = df_filtered[df_filtered["Concepto"].apply(normalizar_texto).str.contains(razon_normalizada, na=False)]
    if excluir:
        palabras_excluir = [x.strip() for x in excluir.split(",") if x.strip()]
        if palabras_excluir:
            # Normalizar cada palabra a excluir
            palabras_excluir_normalizadas = [normalizar_texto(palabra) for palabra in palabras_excluir]
            patron = "|".join(palabras_excluir_normalizadas)
            df_filtered = df_filtered[~df_filtered["Concepto"].apply(normalizar_texto).str.contains(patron, na=False)]

    return df_filtered

# --------------------------
# FUNCIÓN PARA EXTRAER URL EDITABLE
# --------------------------
def obtener_url_editable(link_csv):
    """Extrae la URL editable del Google Sheet desde el link de exportación CSV"""
    try:
        if "/d/" in link_csv:
            sheet_id = link_csv.split("/d/")[1].split("/")[0]
            gid = "0"
            if "gid=" in link_csv:
                gid = link_csv.split("gid=")[1].split("&")[0]
            return f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit#gid={gid}"
        return None
    except:
        return None

# --------------------------
# PANTALLA DE LOGIN
# --------------------------
if not st.session_state.autenticado:
    st.title("🔐 Análisis Financiero - Inicio de Sesión")
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("👤 Iniciar sesión con credenciales")
        usuario = st.text_input("Usuario", key="login_usuario")
        contraseña = st.text_input("Contraseña", type="password", key="login_password")
        
        if st.button("🔓 Iniciar Sesión", use_container_width=True):
            if usuario in USUARIOS and USUARIOS[usuario] == contraseña:
                st.session_state.autenticado = True
                st.session_state.link_sheets = "https://docs.google.com/spreadsheets/d/1_uuGxB-YyKL9vEsiXt_GrHtRTERIQGWnfjY1QeXjacw/export?format=csv&id=1_uuGxB-YyKL9vEsiXt_GrHtRTERIQGWnfjY1QeXjacw&gid=0"
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos")
    
    with col2:
        st.subheader("📊 Acceso directo con enlace")
        link_directo = st.text_input("Pega el enlace de tu Google Sheet", key="link_directo")
        
        if st.button("🔗 Acceder con enlace", use_container_width=True):
            if link_directo:
                st.session_state.autenticado = True
                st.session_state.link_sheets = link_directo
                st.rerun()
            else:
                st.error("❌ Por favor ingresa un enlace válido")
    
    st.markdown("---")
    st.info("💡 **Nota:** Puedes iniciar sesión con usuario y contraseña, o directamente con el enlace de tu Google Sheet público.")
    st.stop()

# --------------------------
# MENÚ PRINCIPAL (USUARIO AUTENTICADO)
# --------------------------
st.title("📊 Análisis Financiero desde Google Sheets")

# Botón de cerrar sesión en la barra lateral
with st.sidebar:
    st.markdown("### 👤 Sesión activa")
    if st.button("🚪 Cerrar sesión", use_container_width=True):
        st.session_state.autenticado = False
        st.session_state.link_sheets = ""
        st.rerun()
    
    st.markdown("---")
    st.markdown("### ⚙️ Opciones")

# Campo para cambiar el enlace si es necesario
link = st.text_input("🔗 Enlace de Google Sheet:", value=st.session_state.link_sheets)

if st.button("🔄 Actualizar datos desde Google Sheets"):
    st.cache_data.clear()
    st.session_state.link_sheets = link
    st.success("✅ Datos actualizados correctamente.")
    st.rerun()

# --------------------------
# CARGA DE DATOS
# --------------------------
if link:
    df = cargar_datos_google_public(link)

    if not df.empty:
        columnas_requeridas = {"Fecha", "Cantidad", "Ingreso /Egreso", "Concepto"}
        if not columnas_requeridas.issubset(df.columns):
            st.error("❌ El archivo no contiene las columnas necesarias: Fecha, Cantidad, Ingreso /Egreso, Concepto.")
            st.stop()

        # Normalización de datos
        df["Fecha"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")
        df["Cantidad"] = df["Cantidad"].astype(str).str.replace(",", ".").astype(float)
        df.dropna(subset=["Fecha", "Cantidad"], inplace=True)

        meses_dict = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        df["MesNombre"] = df["Fecha"].dt.month.map(meses_dict)

        # Vista previa (últimos 5 registros más recientes)
        st.subheader("📋 Vista previa de los últimos 5 registros (más recientes)")
        df_sorted = df.sort_values("Fecha", ascending=False)
        
        col_preview, col_button = st.columns([4, 1])
        with col_preview:
            st.dataframe(df_sorted.head(5), use_container_width=True)
        
        with col_button:
            url_editable = obtener_url_editable(link)
            if url_editable:
                st.markdown(f'<a href="{url_editable}" target="_blank"><button style="background-color:#4CAF50;color:white;padding:10px 20px;border:none;border-radius:5px;cursor:pointer;width:100%;margin-top:10px;">✏️ Editar Registros</button></a>', unsafe_allow_html=True)
            else:
                st.warning("⚠️ No se pudo generar el enlace de edición")

        # --------------------------
        # FILTROS
        # --------------------------
        st.markdown("## 🔍 Filtros")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            start_date = st.date_input("Fecha inicial", value=None)
        with col2:
            end_date = st.date_input("Fecha final", value=None)
        with col3:
            mes = st.selectbox("Filtrar por mes", ["Todos"] + sorted(df["MesNombre"].dropna().unique().tolist()))
        with col4:
            año = st.selectbox("Filtrar por año", ["Todos"] + sorted(df["Fecha"].dt.year.dropna().unique().astype(str).tolist()))

        razon = st.text_input("Filtrar por razón / concepto (ejemplo: oxxo, super, farmacia)")
        excluir = st.text_input("Excluir gastos que contengan (ejemplo: renta, gym)")

        # --------------------------
        # APLICAR FILTROS
        # --------------------------
        df_filtered = filtrar_datos(df, start_date, end_date, razon, excluir, mes, año)

        if df_filtered.empty:
            st.warning("⚠️ No hay datos que coincidan con los filtros seleccionados.")
            st.stop()

        df_final = df_filtered.sort_values("Fecha")
        df_final["Tipo"] = np.where(df_final["Cantidad"] >= 0, "Ingreso", "Gasto")
        df_final["Balance Neto"] = df_final["Cantidad"].cumsum()

        # --------------------------
        # TABLA DE MOVIMIENTOS
        # --------------------------
        st.markdown("### 📄 Tabla de movimientos filtrados")
        columnas_mostrar = ["Fecha", "Cantidad", "Ingreso /Egreso", "Concepto", "Balance Neto"]
        df_mostrar = df_final[columnas_mostrar].copy()
        df_mostrar.rename(columns={"Balance Neto": "Balance Neto Filtrado"}, inplace=True)
        st.dataframe(df_mostrar, use_container_width=True)

        # --------------------------
        # MÉTRICAS GENERALES
        # --------------------------
        total_ingresos = df_final[df_final["Cantidad"] > 0]["Cantidad"].sum()
        total_gastos = df_final[df_final["Cantidad"] < 0]["Cantidad"].sum()
        balance = total_ingresos + total_gastos

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💰 Ingresos", f"${total_ingresos:,.2f}")
        with col2:
            st.metric("📉 Gastos", f"${total_gastos:,.2f}")
        with col3:
            st.metric("🧾 Balance neto", f"${balance:,.2f}")

        # --------------------------
        # VISUALIZACIONES
        # --------------------------
        st.markdown("## 📈 Visualizaciones Interactivas")
        col_pie1, col_pie2 = st.columns(2)

        # --- Pie chart 1: Ingresos vs Gastos ---
        with col_pie1:
            st.markdown("### 💸 Distribución de ingresos vs gastos")
            if total_ingresos != 0 or total_gastos != 0:
                df_pie = pd.DataFrame({
                    "Tipo": ["Ingresos", "Gastos"],
                    "Monto": [total_ingresos, abs(total_gastos)]
                })
                fig_pie = px.pie(
                    df_pie,
                    names="Tipo",
                    values="Monto",
                    color="Tipo",
                    color_discrete_map={"Ingresos": "#2ECC71", "Gastos": "#E74C3C"},
                    title="💹 Proporción de ingresos y gastos",
                    hole=0.4
                )
                fig_pie.update_traces(textinfo='percent+label', pull=[0.05, 0.05])
                fig_pie.update_layout(template="plotly_dark")
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("⚠️ No hay datos suficientes para mostrar este gráfico.")

        # --- Pie chart 2: Top 10 gastos ---
        with col_pie2:
            st.markdown("### 🛒 Top 10 gastos por concepto")
            gastos_filtrados = df_final[df_final["Cantidad"] < 0]
            if not gastos_filtrados.empty:
                resumen_gastos = (
                    gastos_filtrados.assign(
                        Concepto=lambda x: x["Concepto"].fillna("Sin descripción").str.strip().str.lower()
                    )
                    .groupby("Concepto", as_index=False)["Cantidad"]
                    .sum()
                    .sort_values(by="Cantidad")
                    .head(10)
                )
                resumen_gastos["Cantidad"] = resumen_gastos["Cantidad"].abs()
                fig_pie_gastos = px.pie(
                    resumen_gastos,
                    names="Concepto",
                    values="Cantidad",
                    title="Top 10 gastos por concepto",
                    color_discrete_sequence=px.colors.sequential.Magma_r,
                    hole=0.4
                )
                fig_pie_gastos.update_traces(textinfo="percent+label")
                fig_pie_gastos.update_layout(template="plotly_dark")
                st.plotly_chart(fig_pie_gastos, use_container_width=True)
            else:
                st.info("⚠️ No hay gastos para mostrar en el gráfico.")

        # --- Gráfico de balance acumulado ---
        st.markdown("### 📊 Evolución del balance acumulado")
        fig_balance = px.line(
            df_final,
            x="Fecha",
            y="Balance Neto",
            title="📈 Balance acumulado en el tiempo",
            markers=True,
            color_discrete_sequence=["#3498DB"]
        )
        df_trend = df_final.copy()
        df_trend["Tendencia"] = df_trend["Balance Neto"].rolling(window=5, min_periods=1).mean()
        fig_balance.add_scatter(
            x=df_trend["Fecha"], y=df_trend["Tendencia"],
            mode="lines", name="Tendencia (suavizada)",
            line=dict(color="#E67E22", width=3, dash="dot")
        )
        fig_balance.update_layout(template="plotly_dark", hovermode="x unified")
        st.plotly_chart(fig_balance, use_container_width=True)

        # --- Scatter de ingresos y gastos ---
        st.markdown("### 🟢🔴 Distribución de ingresos y gastos")
        df_final["MontoAbs"] = df_final["Cantidad"].abs()
        fig_scatter = px.scatter(
            df_final,
            x="Fecha",
            y="MontoAbs",
            color="Tipo",
            size=df_final["MontoAbs"],
            color_discrete_map={"Ingreso": "#2ECC71", "Gasto": "#E74C3C"},
            hover_data=["Concepto", "Ingreso /Egreso", "Cantidad"],
            title="🔵 Ingresos y Gastos (tamaño proporcional al monto)"
        )
        fig_scatter.update_traces(opacity=0.8)
        fig_scatter.update_layout(
            template="plotly_dark",
            xaxis_title="Fecha",
            yaxis_title="Monto ($)"
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
       
        # --- Gráfico de barras horizontales Top 10 gastos ---
        st.markdown("### 📊 Top 10 gastos filtrados (barras horizontales)")
        if not gastos_filtrados.empty:
            # Agrupamos por concepto y sumamos los gastos
            resumen_gastos_barras = (
                gastos_filtrados.assign(
                    Concepto=lambda x: x["Concepto"].fillna("Sin descripción").str.strip().str.lower()
                )
                .groupby("Concepto", as_index=False)["Cantidad"]
                .sum()
                .sort_values(by="Cantidad")
                .head(10)
            )
            resumen_gastos_barras["Cantidad"] = resumen_gastos_barras["Cantidad"].abs()

            # Crear gráfico de barras horizontales
            fig_barras = px.bar(
                resumen_gastos_barras,
                x="Cantidad",
                y="Concepto",
                orientation="h",
                text="Cantidad",
                color="Cantidad",
                color_continuous_scale=px.colors.sequential.Magma_r,
                title="Top 10 gastos filtrados",
            )
            fig_barras.update_layout(template="plotly_dark", yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_barras, use_container_width=True)
        else:
            st.info("⚠️ No hay gastos para mostrar en la gráfica de barras.")
else:
    st.warning("⚠️ Por favor ingresa un enlace válido de Google Sheets para comenzar.")
