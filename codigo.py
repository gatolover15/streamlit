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
        df_filtered = df_filtered[df_filtered["Compra"].str.contains(razon, case=False, na=False)]

    if excluir:
        palabras_excluir = [x.strip() for x in excluir.split(",") if x.strip()]
        if palabras_excluir:
            patron = "|".join(palabras_excluir)
            df_filtered = df_filtered[~df_filtered["Compra"].str.contains(patron, case=False, na=False)]

    return df_filtered

# --------------------------
# CARGA DE DATOS
# --------------------------
link = st.text_input("Pega aquí el enlace de tu Google Sheet (puede ser normal o .csv):")

if link:
    df = cargar_datos_google_public(link)

    if not df.empty:
        columnas_requeridas = {"Fecha", "Compra", "Cantidad"}
        if not columnas_requeridas.issubset(df.columns):
            st.error("❌ El archivo no contiene las columnas necesarias: Fecha, Compra, Cantidad.")
            st.stop()

        # Normalizar datos
        df["Fecha"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")
        df["Cantidad"] = df["Cantidad"].astype(str).str.replace(",", ".").astype(float)
        df.dropna(subset=["Fecha", "Cantidad"], inplace=True)

        # Diccionario de meses en español
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

        filtros_activos = any([
            start_date, end_date,
            razon, excluir,
            mes != "Todos", año != "Todos"
        ])

        if not filtros_activos:
            st.info("ℹ️ No hay filtros aplicados — mostrando todos los movimientos desde la fecha más antigua hasta la más reciente.")
            df_final = df.sort_values("Fecha")
        else:
            st.success("✅ Se aplicaron los siguientes filtros:")
            filtros_texto = []
            if mes != "Todos":
                filtros_texto.append(f"Mes: **{mes}**")
            if año != "Todos":
                filtros_texto.append(f"Año: **{año}**")
            if start_date:
                filtros_texto.append(f"Desde: **{start_date}**")
            if end_date:
                filtros_texto.append(f"Hasta: **{end_date}**")
            if razon:
                filtros_texto.append(f"Razón contiene: **{razon}**")
            if excluir:
                filtros_texto.append(f"Excluye: **{excluir}**")

            if filtros_texto:
                st.markdown("- " + "\n- ".join(filtros_texto))

            if df_filtered.empty:
                st.warning("⚠️ No hay movimientos registrados que coincidan con los filtros seleccionados.")
                df_final = pd.DataFrame()
            else:
                df_final = df_filtered.sort_values("Fecha")

        # --------------------------
        # AGREGAR COLUMNAS "TIPO" Y "BALANCE NETO"
        # --------------------------
        if not df_final.empty:
            df_final["Tipo"] = np.where(df_final["Cantidad"] >= 0, "Ingreso", "Gasto")
            df_final["Balance Neto"] = df_final["Cantidad"].cumsum()
            df_final["Balance Neto"] = df_final["Balance Neto"] - df_final["Balance Neto"].iloc[0] + df_final["Cantidad"].iloc[0]

        # --------------------------
        # TABLA DE RESULTADOS
        # --------------------------
        st.markdown("### 📄 Tabla de movimientos")
        if not df_final.empty:
            st.dataframe(df_final, use_container_width=True)

        # --------------------------
        # MÉTRICAS
        # --------------------------
        if not df_final.empty:
            total_ingresos = df_final[df_final["Cantidad"] > 0]["Cantidad"].sum()
            total_gastos = df_final[df_final["Cantidad"] < 0]["Cantidad"].sum()
            balance = total_ingresos + total_gastos

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("💰 Ingresos filtrados", f"${total_ingresos:,.2f}")
            with col2:
                st.metric("📉 Gastos filtrados", f"${total_gastos:,.2f}")
            with col3:
                st.metric("🧾 Balance filtrado", f"${balance:,.2f}")

            # --------------------------
            # VISUALIZACIONES
            # --------------------------
            st.markdown("## 📈 Visualizaciones Interactivas")

            # --- BALANCE ACUMULADO ---
            st.markdown("### 📊 Evolución del balance acumulado")
            fig_balance = px.line(
                df_final,
                x="Fecha",
                y="Balance Neto",
                title="📈 Balance acumulado en el tiempo",
                markers=True,
                color_discrete_sequence=["#3498DB"],
            )

            # 🔹 Línea de tendencia suavizada
            df_trend = df_final.copy()
            df_trend["Tendencia"] = df_trend["Balance Neto"].rolling(window=5, min_periods=1).mean()
            fig_balance.add_scatter(
                x=df_trend["Fecha"], y=df_trend["Tendencia"],
                mode="lines", name="Tendencia (suavizada)",
                line=dict(color="#E67E22", width=3, dash="dot")
            )

            fig_balance.update_traces(line=dict(width=3))
            fig_balance.update_layout(
                xaxis_title="Fecha",
                yaxis_title="Balance Neto ($)",
                hovermode="x unified",
                template="plotly_dark"
            )
            st.plotly_chart(fig_balance, use_container_width=True)

            # --- TOP 10 GASTOS ---
            st.markdown("### 🏆 Top 10 gastos filtrados")
            top_gastos = (
                df_final[df_final["Cantidad"] < 0]
                .assign(Compra_Normalizada=lambda x: x["Compra"].str.lower().str.extract(r'(\b\w+)')[0])
                .groupby("Compra_Normalizada")["Cantidad"]
                .sum()
                .sort_values()
                .head(10)
                .reset_index()
            )

            if not top_gastos.empty:
                fig_top = px.bar(
                    top_gastos,
                    x="Cantidad",
                    y="Compra_Normalizada",
                    orientation="h",
                    color="Cantidad",
                    color_continuous_scale=["#E74C3C", "#C0392B"],
                    title="🏆 Top 10 gastos filtrados",
                    text="Cantidad",
                )
                fig_top.update_layout(
                    yaxis={'categoryorder': 'total ascending'},
                    template="plotly_dark"
                )
                st.plotly_chart(fig_top, use_container_width=True)

            # --------------------------
            # PIE CHARTS
            # --------------------------
            st.markdown("## 🥧 Gráficos de distribución")

            col_pie1, col_pie2 = st.columns(2)

            with col_pie1:
                st.markdown("### 💸 Distribución de ingresos vs gastos")
                resumen = df_final.groupby("Tipo")["Cantidad"].sum().reset_index()
                if not resumen.empty:
                    fig_pie_tipo = px.pie(
                        resumen,
                        names="Tipo",
                        values="Cantidad",
                        color="Tipo",
                        color_discrete_map={"Ingreso": "#2ECC71", "Gasto": "#E74C3C"},
                        title="Ingresos vs Gastos",
                        hole=0.4
                    )
                    fig_pie_tipo.update_traces(textposition="inside", textinfo="percent+label")
                    fig_pie_tipo.update_layout(template="plotly_dark")
                    st.plotly_chart(fig_pie_tipo, use_container_width=True)
                else:
                    st.info("No hay datos suficientes para mostrar el gráfico de ingresos vs gastos.")

            with col_pie2:
                st.markdown("### 🛒 Distribución de gastos por compra (según filtro)")
                gastos_filtrados = df_final[df_final["Cantidad"] < 0]
                if not gastos_filtrados.empty:
                    resumen_gastos = (
                        gastos_filtrados.groupby("Compra")["Cantidad"]
                        .sum()
                        .sort_values()
                        .reset_index()
                    )
                    resumen_gastos["Cantidad"] = resumen_gastos["Cantidad"].abs()

                    fig_pie_gastos = px.pie(
                        resumen_gastos,
                        names="Compra",
                        values="Cantidad",
                        title="Distribución de gastos por compra",
                        color_discrete_sequence=px.colors.sequential.Magma_r,
                        hole=0.4
                    )
                    fig_pie_gastos.update_traces(textposition="inside", textinfo="percent+label")
                    fig_pie_gastos.update_layout(template="plotly_dark")
                    st.plotly_chart(fig_pie_gastos, use_container_width=True)
                else:
                    st.info("No hay gastos filtrados para mostrar en el gráfico de compras.")
