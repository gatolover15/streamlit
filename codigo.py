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

# Mapeo de cuentas -> nombre de la hoja en Google Sheets
HOJAS_CUENTAS = {
    "Banorte": "Hoja1",
    "BBVA": "Hoja 3",
    "Nu": "Hoja 5",
}

# Inicializar session_state
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "link_sheets" not in st.session_state:
    st.session_state.link_sheets = ""

# --------------------------
# FUNCIONES PARA CONSTRUIR URLS
# --------------------------
def extraer_sheet_id(link_hoja):
    """Extrae el ID del documento de Google Sheets a partir de cualquier link"""
    try:
        if "/d/" in link_hoja:
            return link_hoja.split("/d/")[1].split("/")[0]
        return None
    except Exception:
        return None


def construir_url_hoja_por_nombre(sheet_id, nombre_hoja):
    """Arma la URL de exportación CSV de una pestaña específica por su nombre"""
    from urllib.parse import quote
    nombre_codificado = quote(nombre_hoja)
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_codificado}"


def obtener_url_editable_hoja(sheet_id, nombre_hoja=None, gid="0"):
    """Genera el link editable del Google Sheet (a la hoja indicada si se conoce el gid, si no al doc general)"""
    if not sheet_id:
        return None
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"


# --------------------------
# FUNCIÓN PARA CARGAR DATOS (una sola hoja)
# --------------------------
COLUMNAS_REQUERIDAS = {"Fecha", "Cantidad", "Ingreso /Egreso", "Concepto"}


def _parece_html(data):
    """Detecta si lo que regresó pd.read_csv en realidad fue una página de error/HTML de Google"""
    columnas_texto = " ".join(str(c) for c in data.columns).lower()
    return "html" in columnas_texto or "doctype" in columnas_texto or data.shape[1] <= 1


@st.cache_data
def cargar_datos_google_public(sheet_id, nombre_hoja):
    """Carga una pestaña específica de un Google Sheet público por su nombre.
    Regresa (DataFrame, mensaje_error). Si mensaje_error no es None, la carga falló."""
    try:
        url = construir_url_hoja_por_nombre(sheet_id, nombre_hoja)
        data = pd.read_csv(url)

        if _parece_html(data):
            return pd.DataFrame(), (
                f"La pestaña '{nombre_hoja}' no regresó datos válidos (parece que Google mandó una "
                f"página de error en vez del CSV). Revisa que el nombre de la pestaña sea EXACTO "
                f"(mayúsculas/espacios) y que el documento esté compartido como "
                f"'Cualquiera con el enlace puede ver'."
            )

        columnas_faltantes = COLUMNAS_REQUERIDAS - set(data.columns)
        if columnas_faltantes:
            return pd.DataFrame(), (
                f"La pestaña '{nombre_hoja}' se cargó, pero le faltan columnas: {', '.join(columnas_faltantes)}. "
                f"Columnas encontradas: {', '.join(str(c) for c in data.columns)}."
            )

        return data, None
    except Exception as e:
        return pd.DataFrame(), f"Error cargando la pestaña '{nombre_hoja}': {e}"


@st.cache_data
def cargar_todas_las_cuentas(sheet_id, hojas_cuentas):
    """Carga todas las hojas configuradas y las junta en un solo DataFrame con columna 'Cuenta'.
    Regresa (df_combinado, lista_de_errores). Las hojas que fallan se omiten pero no tumban la app."""
    dfs = []
    errores = []
    for cuenta, nombre_hoja in hojas_cuentas.items():
        df_hoja, error = cargar_datos_google_public(sheet_id, nombre_hoja)
        if error:
            errores.append(error)
            continue
        df_hoja = df_hoja.copy()
        df_hoja["Cuenta"] = cuenta
        dfs.append(df_hoja)

    if dfs:
        return pd.concat(dfs, ignore_index=True), errores
    return pd.DataFrame(), errores


# --------------------------
# FUNCIÓN PARA NORMALIZAR TEXTO (sin tildes)
# --------------------------
def normalizar_texto(texto):
    """Elimina tildes y convierte a minúsculas"""
    import unicodedata
    if pd.isna(texto):
        return ""
    texto = str(texto).lower()
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
        razon_normalizada = normalizar_texto(razon)
        df_filtered = df_filtered[df_filtered["Concepto"].apply(normalizar_texto).str.contains(razon_normalizada, na=False)]
    if excluir:
        palabras_excluir = [x.strip() for x in excluir.split(",") if x.strip()]
        if palabras_excluir:
            palabras_excluir_normalizadas = [normalizar_texto(palabra) for palabra in palabras_excluir]
            patron = "|".join(palabras_excluir_normalizadas)
            df_filtered = df_filtered[~df_filtered["Concepto"].apply(normalizar_texto).str.contains(patron, na=False)]

    return df_filtered


# --------------------------
# FUNCIÓN PARA AGRUPAR CONCEPTOS SIMILARES
# --------------------------
def agrupar_concepto(concepto):
    concepto_lower = normalizar_texto(concepto)
    if "oxxo" in concepto_lower:
        return "OXXO"
    elif ("agua" in concepto_lower or "luz" in concepto_lower or "cfe" in concepto_lower or
          "internet" in concepto_lower or
          ("gas" in concepto_lower and "gasolina" not in concepto_lower and "combustible" not in concepto_lower)):
        return "Servicios Depa"
    elif "super" in concepto_lower or "soriana" in concepto_lower or "walmart" in concepto_lower or "heb" in concepto_lower:
        return "Supermercado"
    elif "gasolina" in concepto_lower or "combustible" in concepto_lower:
        return "Gasolina"
    elif "farmacia" in concepto_lower or "medicamento" in concepto_lower:
        return "Farmacia"
    elif "restaurante" in concepto_lower or "comida" in concepto_lower or "restaurant" in concepto_lower:
        return "Restaurante"
    elif "uber" in concepto_lower or "taxi" in concepto_lower or "transporte" in concepto_lower:
        return "Transporte"
    elif "netflix" in concepto_lower or "spotify" in concepto_lower or "suscripcion" in concepto_lower:
        return "Suscripciones"
    elif "renta" in concepto_lower or "alquiler" in concepto_lower:
        return "Renta"
    else:
        return concepto.strip().title()


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
                st.session_state.link_sheets = "https://docs.google.com/spreadsheets/d/1_uuGxB-YyKL9vEsiXt_GrHtRTERIQGWnfjY1QeXjacw/edit"
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
# CARGA DE DATOS (todas las cuentas)
# --------------------------
if link:
    sheet_id = extraer_sheet_id(link)

    if not sheet_id:
        st.error("❌ No se pudo extraer el ID del documento a partir del enlace proporcionado.")
        st.stop()

    df, errores_carga = cargar_todas_las_cuentas(sheet_id, HOJAS_CUENTAS)

    if errores_carga:
        for err in errores_carga:
            st.warning(f"⚠️ {err}")

    if not df.empty:
        # Normalización de datos - Mejorado para manejar diferentes formatos de fecha
        df["Fecha_Original"] = df["Fecha"].astype(str)
        df["Fecha"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")

        fechas_invalidas_mask = df["Fecha"].isna()
        if fechas_invalidas_mask.any():
            for idx in df[fechas_invalidas_mask].index:
                fecha_str = str(df.loc[idx, "Fecha_Original"]).strip()
                try:
                    if "-" in fecha_str:
                        partes = fecha_str.split("-")
                    elif "/" in fecha_str:
                        partes = fecha_str.split("/")
                    else:
                        continue

                    if len(partes) == 3:
                        dia, mes_p, año_p = partes
                        if len(año_p) == 2:
                            año_p = "20" + año_p
                        fecha_corregida = f"{dia}-{mes_p}-{año_p}"
                        df.loc[idx, "Fecha"] = pd.to_datetime(fecha_corregida, format="%d-%m-%Y", errors="coerce")
                except Exception:
                    continue

        df.drop(columns=["Fecha_Original"], inplace=True)

        fechas_invalidas = df[df["Fecha"].isna()]
        if not fechas_invalidas.empty:
            st.warning(f"⚠️ Se encontraron {len(fechas_invalidas)} filas con fechas inválidas después del procesamiento. Revisa el formato en tu Google Sheet.")
            with st.expander("Ver filas con fechas inválidas"):
                st.dataframe(fechas_invalidas)

        df["Cantidad"] = df["Cantidad"].astype(str).str.replace(",", ".").astype(float)
        df.dropna(subset=["Fecha", "Cantidad"], inplace=True)

        meses_dict = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        df["MesNombre"] = df["Fecha"].dt.month.map(meses_dict)

        # --------------------------
        # SELECTOR DE CUENTA (Total / Banorte / BBVA / Nu)
        # --------------------------
        st.markdown("## 🏦 Selecciona la cuenta a analizar")
        opciones_cuenta = ["Total (todas las cuentas)"] + list(HOJAS_CUENTAS.keys())
        cuenta_seleccionada = st.radio(
            "Ver cuenta:",
            options=opciones_cuenta,
            horizontal=True,
            key="selector_cuenta"
        )

        if cuenta_seleccionada == "Total (todas las cuentas)":
            df_cuenta = df.copy()
        else:
            df_cuenta = df[df["Cuenta"] == cuenta_seleccionada].copy()

        if df_cuenta.empty:
            st.warning(f"⚠️ No hay datos para la cuenta '{cuenta_seleccionada}'.")
            st.stop()

        # Vista previa (últimos 5 registros más recientes)
        st.subheader(f"📋 Vista previa de los últimos 5 registros ({cuenta_seleccionada})")
        df_sorted = df_cuenta.sort_values("Fecha", ascending=False)

        col_preview, col_button = st.columns([4, 1])
        with col_preview:
            columnas_preview = ["Fecha", "Cantidad", "Ingreso /Egreso", "Concepto", "Cuenta"]
            st.dataframe(df_sorted[columnas_preview].head(5), use_container_width=True)

        with col_button:
            url_editable = obtener_url_editable_hoja(sheet_id)
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
            mes = st.selectbox("Filtrar por mes", ["Todos"] + sorted(df_cuenta["MesNombre"].dropna().unique().tolist()))
        with col4:
            año = st.selectbox("Filtrar por año", ["Todos"] + sorted(df_cuenta["Fecha"].dt.year.dropna().unique().astype(str).tolist()))

        razon = st.text_input("Filtrar por razón / concepto (ejemplo: oxxo, super, farmacia)")
        excluir = st.text_input("Excluir gastos que contengan (ejemplo: renta, gym)")

        # --------------------------
        # APLICAR FILTROS
        # --------------------------
        df_filtered = filtrar_datos(df_cuenta, start_date, end_date, razon, excluir, mes, año)

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
        columnas_mostrar = ["Fecha", "Cantidad", "Ingreso /Egreso", "Concepto", "Cuenta", "Balance Neto"]
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
        # DESGLOSE POR CUENTA (solo visible en vista Total)
        # --------------------------
        if cuenta_seleccionada == "Total (todas las cuentas)":
            st.markdown("### 🏦 Desglose por cuenta")
            resumen_cuentas = df_final.groupby("Cuenta").agg(
                Ingresos=("Cantidad", lambda x: x[x > 0].sum()),
                Gastos=("Cantidad", lambda x: x[x < 0].sum())
            ).reset_index()
            resumen_cuentas["Balance"] = resumen_cuentas["Ingresos"] + resumen_cuentas["Gastos"]

            cols_cuentas = st.columns(len(resumen_cuentas))
            for i, row in resumen_cuentas.iterrows():
                with cols_cuentas[i]:
                    st.metric(f"🏦 {row['Cuenta']}", f"${row['Balance']:,.2f}",
                              delta=f"Ing: ${row['Ingresos']:,.2f} | Gas: ${row['Gastos']:,.2f}")

            fig_cuentas = px.bar(
                df_final.groupby("Cuenta", as_index=False)["Cantidad"].sum(),
                x="Cuenta", y="Cantidad",
                title="Balance neto por cuenta",
                color="Cuenta",
                text="Cantidad"
            )
            fig_cuentas.update_layout(template="plotly_dark")
            st.plotly_chart(fig_cuentas, use_container_width=True)

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
                gastos_con_categoria = gastos_filtrados.copy()
                gastos_con_categoria["ConceptoAgrupado"] = gastos_con_categoria["Concepto"].fillna("Sin descripción").apply(agrupar_concepto)

                resumen_gastos = (
                    gastos_con_categoria
                    .groupby("ConceptoAgrupado", as_index=False)["Cantidad"]
                    .sum()
                    .sort_values(by="Cantidad")
                    .head(10)
                )
                resumen_gastos["Cantidad"] = resumen_gastos["Cantidad"].abs()
                fig_pie_gastos = px.pie(
                    resumen_gastos,
                    names="ConceptoAgrupado",
                    values="Cantidad",
                    title="Top 10 gastos por concepto (click para ver desglose)",
                    color_discrete_sequence=px.colors.sequential.Magma_r,
                    hole=0.4
                )
                fig_pie_gastos.update_traces(textinfo="percent+label")
                fig_pie_gastos.update_layout(template="plotly_dark")
                st.plotly_chart(fig_pie_gastos, use_container_width=True, key="pie_chart")

                categoria_seleccionada = st.selectbox(
                    "🔍 Ver desglose de:",
                    options=["Selecciona una categoría..."] + resumen_gastos["ConceptoAgrupado"].tolist(),
                    key="selector_pie"
                )

                if categoria_seleccionada != "Selecciona una categoría...":
                    desglose = gastos_con_categoria[gastos_con_categoria["ConceptoAgrupado"] == categoria_seleccionada].copy()
                    desglose["Cantidad"] = desglose["Cantidad"].abs()
                    desglose_agrupado = desglose.groupby("Concepto", as_index=False).agg({
                        "Cantidad": "sum",
                        "Fecha": "count"
                    }).rename(columns={"Fecha": "Número de veces"})
                    desglose_agrupado = desglose_agrupado.sort_values("Cantidad", ascending=False)

                    st.markdown(f"#### 📋 Desglose de: **{categoria_seleccionada}**")
                    st.markdown(f"**Total: ${desglose_agrupado['Cantidad'].sum():,.2f}**")
                    st.dataframe(desglose_agrupado, use_container_width=True, hide_index=True)

                    conceptos_con_multiples = desglose_agrupado[desglose_agrupado["Número de veces"] > 1]["Concepto"].tolist()
                    if conceptos_con_multiples:
                        st.markdown("---")
                        concepto_detalle = st.selectbox(
                            "🔎 Ver transacciones individuales de:",
                            options=["Selecciona un concepto..."] + conceptos_con_multiples,
                            key="selector_detalle_pie"
                        )

                        if concepto_detalle != "Selecciona un concepto...":
                            transacciones_individuales = desglose[desglose["Concepto"] == concepto_detalle][["Fecha", "Cantidad", "Ingreso /Egreso", "Cuenta"]].copy()
                            transacciones_individuales = transacciones_individuales.sort_values("Fecha", ascending=False)
                            st.markdown(f"##### 🧾 Transacciones de: **{concepto_detalle}**")
                            st.dataframe(transacciones_individuales, use_container_width=True, hide_index=True)
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
            hover_data=["Concepto", "Ingreso /Egreso", "Cantidad", "Cuenta"],
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
            gastos_con_categoria_barras = gastos_filtrados.copy()
            gastos_con_categoria_barras["ConceptoAgrupado"] = gastos_con_categoria_barras["Concepto"].fillna("Sin descripción").apply(agrupar_concepto)

            resumen_gastos_barras = (
                gastos_con_categoria_barras
                .groupby("ConceptoAgrupado", as_index=False)["Cantidad"]
                .sum()
                .sort_values(by="Cantidad")
                .head(10)
            )
            resumen_gastos_barras["Cantidad"] = resumen_gastos_barras["Cantidad"].abs()

            fig_barras = px.bar(
                resumen_gastos_barras,
                x="Cantidad",
                y="ConceptoAgrupado",
                orientation="h",
                text="Cantidad",
                color="Cantidad",
                color_continuous_scale=px.colors.sequential.Magma_r,
                title="Top 10 gastos filtrados (click para ver desglose)",
            )
            fig_barras.update_layout(template="plotly_dark", yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_barras, use_container_width=True, key="bar_chart")

            categoria_seleccionada_barras = st.selectbox(
                "🔍 Ver desglose de:",
                options=["Selecciona una categoría..."] + resumen_gastos_barras.sort_values("Cantidad", ascending=False)["ConceptoAgrupado"].tolist(),
                key="selector_barras"
            )

            if categoria_seleccionada_barras != "Selecciona una categoría...":
                desglose_barras = gastos_con_categoria_barras[gastos_con_categoria_barras["ConceptoAgrupado"] == categoria_seleccionada_barras].copy()
                desglose_barras["Cantidad"] = desglose_barras["Cantidad"].abs()
                desglose_agrupado_barras = desglose_barras.groupby("Concepto", as_index=False).agg({
                    "Cantidad": "sum",
                    "Fecha": "count"
                }).rename(columns={"Fecha": "Número de veces"})
                desglose_agrupado_barras = desglose_agrupado_barras.sort_values("Cantidad", ascending=False)

                st.markdown(f"#### 📋 Desglose de: **{categoria_seleccionada_barras}**")
                st.markdown(f"**Total: ${desglose_agrupado_barras['Cantidad'].sum():,.2f}**")
                st.dataframe(desglose_agrupado_barras, use_container_width=True, hide_index=True)

                conceptos_con_multiples_barras = desglose_agrupado_barras[desglose_agrupado_barras["Número de veces"] > 1]["Concepto"].tolist()
                if conceptos_con_multiples_barras:
                    st.markdown("---")
                    concepto_detalle_barras = st.selectbox(
                        "🔎 Ver transacciones individuales de:",
                        options=["Selecciona un concepto..."] + conceptos_con_multiples_barras,
                        key="selector_detalle_barras"
                    )

                    if concepto_detalle_barras != "Selecciona un concepto...":
                        transacciones_individuales_barras = desglose_barras[desglose_barras["Concepto"] == concepto_detalle_barras][["Fecha", "Cantidad", "Ingreso /Egreso", "Cuenta"]].copy()
                        transacciones_individuales_barras = transacciones_individuales_barras.sort_values("Fecha", ascending=False)
                        st.markdown(f"##### 🧾 Transacciones de: **{concepto_detalle_barras}**")
                        st.dataframe(transacciones_individuales_barras, use_container_width=True, hide_index=True)
        else:
            st.info("⚠️ No hay gastos para mostrar en la gráfica de barras.")
    else:
        st.error("❌ No se pudo cargar información de ninguna de las hojas configuradas (Hoja1, Hoja 3, Hoja 5). Revisa que existan y sean públicas.")
else:
    st.warning("⚠️ Por favor ingresa un enlace válido de Google Sheets para comenzar.")
