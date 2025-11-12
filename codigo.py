import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# --------------------------
# CONFIGURACIÓN INICIAL
# --------------------------
st.set_page_config(page_title="📊 Análisis Financiero", layout="wide")
st.title("📊 Análisis Financiero desde Google Sheets")

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
        df_filtered = df_filtered[df_filtered["Concepto"].str.contains(razon, case=False, na=False)]
    if excluir:
        palabras_excluir = [x.strip() for x in excluir.split(",") if x.strip()]
        if palabras_excluir:
            patron = "|".join(palabras_excluir)
            df_filtered = df_filtered[~df_filtered["Concepto"].str.contains(patron, case=False, na=False)]

    return df_filtered

# --------------------------
# CARGA DE DATOS
# --------------------------
link = st.text_input("Pega aquí el enlace de tu Google Sheet (puede ser normal o .csv):")

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

        st.subheader("📋 Vista previa de los datos")
        st.dataframe(df.head())

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

        # --- Pie chart 1: Ingresos vs Gastos ---
        col_pie1, col_pie2 = st.columns(2)
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

        # --- Pie chart 2: Distribución de gastos ---
        with col_pie2:
            st.markdown("### 🛒 Distribución de gastos por concepto")
            gastos_filtrados = df_final[df_final["Cantidad"] < 0]
            if not gastos_filtrados.empty:
                resumen_gastos = (
                    gastos_filtrados.assign(Concepto=lambda x: x["Concepto"].fillna("Sin descripción").str.strip().str.lower())
                    .groupby("Concepto", as_index=False)["Cantidad"]
                    .sum()
                    .sort_values(by="Cantidad")
                )
                resumen_gastos["Cantidad"] = resumen_gastos["Cantidad"].abs()
                fig_pie_gastos = px.pie(
                    resumen_gastos,
                    names="Concepto",
                    values="Cantidad",
                    title="Distribución de gastos por concepto",
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

        # --- Top 10 gastos ---
        st.markdown("### 🏆 Top 10 gastos filtrados")
        top_gastos = (
            gastos_filtrados.assign(Concepto=lambda x: x["Concepto"].fillna("Sin descripción").str.lower().str.strip())
            .groupby("Concepto", as_index=False)["Cantidad"]
            .sum()
            .sort_values(by="Cantidad")
            .head(10)
        )
        if not top_gastos.empty:
            fig_top = px.bar(
                top_gastos,
                x="Cantidad",
                y="Concepto",
                orientation="h",
                color="Cantidad",
                color_continuous_scale=["#E74C3C", "#C0392B"],
                tit
