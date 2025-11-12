import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# --------------------------
# CONFIGURACIÓN INICIAL
# --------------------------
st.set_page_config(page_title="📊 Dashboard Financiero", layout="wide", initial_sidebar_state="collapsed")
# Forzar tema oscuro con CSS mínimo
st.markdown(
    """
    <style>
    body { background-color:#0e1117; color:#e6e6e6; }
    .stButton>button { background-color:#121212; color:#e6e6e6; }
    .stDownloadButton>button { background-color:#121212; color:#e6e6e6; }
    .stMetricValue { color: #00FFAA; }
    .css-1d391kg { background-color: #0e1117; }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("📊 Dashboard Financiero — Móvil (tema oscuro)")

# --------------------------
# CACHING Y CARGA DE GOOGLE SHEETS
# --------------------------
@st.cache_data(ttl=3600)
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
# FILTRADO
# --------------------------
def filtrar_datos(df, start_date, end_date, razon, excluir, mes, año):
    df_filtered = df.copy()

    # Filtrar por año y mes (usamos MesNombre para evitar locale)
    if año != "Todos":
        df_filtered = df_filtered[df_filtered["Fecha"].dt.year == int(año)]
    if mes != "Todos":
        df_filtered = df_filtered[df_filtered["MesNombre"] == mes]

    # Fechas (aplican siempre, en combinación)
    if start_date:
        df_filtered = df_filtered[df_filtered["Fecha"] >= pd.to_datetime(start_date)]
    if end_date:
        df_filtered = df_filtered[df_filtered["Fecha"] <= pd.to_datetime(end_date)]

    # Filtro por texto
    if razon:
        df_filtered = df_filtered[df_filtered["Compra"].str.contains(razon, case=False, na=False)]

    # Excluir palabras
    if excluir:
        palabras_excluir = [x.strip() for x in excluir.split(",") if x.strip()]
        if palabras_excluir:
            patron = "|".join(palabras_excluir)
            df_filtered = df_filtered[~df_filtered["Compra"].str.contains(patron, case=False, na=False)]

    return df_filtered

# --------------------------
# INPUT: ENLACE
# --------------------------
link = st.text_input("🔗 Pega aquí el enlace de tu Google Sheet (público o CSV):")

if not link:
    st.info("Ingresa el enlace del Google Sheet para comenzar.")
else:
    df = cargar_datos_google_public(link)

    if df.empty:
        st.warning("No se cargaron datos. Revisa el enlace o el formato del archivo.")
    else:
        # Validar columnas
        columnas_requeridas = {"Fecha", "Compra", "Cantidad"}
        if not columnas_requeridas.issubset(df.columns):
            st.error("El archivo debe contener las columnas: Fecha, Compra, Cantidad.")
        else:
            # --------------------------
            # LIMPIEZA Y PREPARACIÓN
            # --------------------------
            df["Fecha"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")
            df["Cantidad"] = df["Cantidad"].astype(str).str.replace(",", ".").astype(float)
            df = df.dropna(subset=["Fecha", "Cantidad"]).copy()

            # Meses en español (map desde número)
            meses_dict = {
                1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
                5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
                9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
            }
            df["MesNombre"] = df["Fecha"].dt.month.map(meses_dict)
            df["Año"] = df["Fecha"].dt.year.astype(str)

            # --------------------------
            # INTERFAZ: filtros dentro de un expander para móviles
            # --------------------------
            with st.expander("🔎 Filtros (fechas / mes / año / búsqueda / excluir)", expanded=True):
                col_a, col_b, col_c, col_d = st.columns(4)
                with col_a:
                    start_date = st.date_input("Fecha inicial", value=None)
                with col_b:
                    end_date = st.date_input("Fecha final", value=None)
                with col_c:
                    mes = st.selectbox("Mes", ["Todos"] + sorted(df["MesNombre"].dropna().unique().tolist()))
                with col_d:
                    año = st.selectbox("Año", ["Todos"] + sorted(df["Año"].dropna().unique().tolist()))
                razon = st.text_input("Buscar por razón / concepto (ej: oxxo, super, farmacia)")
                excluir = st.text_input("Excluir (coma separadas) (ej: renta, gym)")

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
                st.info("ℹ️ Mostrando todos los movimientos (desde la fecha más antigua hasta la más reciente).")
                df_final = df.sort_values("Fecha").reset_index(drop=True)
            else:
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
                    st.success("✅ Filtros aplicados:")
                    st.markdown("- " + "\n- ".join(filtros_texto))

                if df_filtered.empty:
                    st.warning("⚠️ No hay movimientos que coincidan con esos filtros.")
                    df_final = pd.DataFrame()  # vacío
                else:
                    df_final = df_filtered.sort_values("Fecha").reset_index(drop=True)

            # --------------------------
            # COLUMNAS: Tipo y Balance Neto
            # --------------------------
            if not df_final.empty:
                df_final["Tipo"] = np.where(df_final["Cantidad"] >= 0, "Ingreso", "Gasto")
                # Balance Neto: cumsum que inicia con el primer valor real del periodo
                df_final["Balance Neto"] = df_final["Cantidad"].cumsum()

            # --------------------------
            # TABLA: mostrar filtros desglosados y la tabla (sin índice)
            # --------------------------
            st.markdown("### 📄 Tabla de movimientos")
            if df_final.empty:
                st.info("No hay datos para mostrar según los filtros seleccionados.")
            else:
                # Mostrar tabla con columnas ordenadas (Fecha, Compra, Cantidad, Tipo, Balance Neto)
                tabla_mostrar = df_final[["Fecha", "Compra", "Cantidad", "Tipo", "Balance Neto"]].copy()
                tabla_mostrar["Fecha"] = tabla_mostrar["Fecha"].dt.strftime("%Y-%m-%d")
                st.dataframe(tabla_mostrar.reset_index(drop=True), use_container_width=True)

            # --------------------------
            # MÉTRICAS PRINCIPALES
            # --------------------------
            if not df_final.empty:
                total_ingresos = df_final[df_final["Cantidad"] > 0]["Cantidad"].sum()
                total_gastos = df_final[df_final["Cantidad"] < 0]["Cantidad"].sum()
                balance = total_ingresos + total_gastos

                st.markdown("### 🔢 Resumen")
                c1, c2, c3 = st.columns(3)
                c1.metric("💰 Ingresos", f"${total_ingresos:,.2f}")
                c2.metric("📉 Gastos", f"${total_gastos:,.2f}")
                c3.metric("🧾 Balance", f"${balance:,.2f}")

                # Botón para descargar datos filtrados
                st.download_button(
                    "📥 Descargar datos filtrados (CSV)",
                    df_final.to_csv(index=False).encode("utf-8"),
                    "datos_filtrados.csv",
                    "text/csv"
                )

                # --------------------------
                # GRÁFICOS: Tabs para móviles
                # --------------------------
                st.markdown("### 📈 Visualizaciones")
                tab1, tab2, tab3 = st.tabs(["Movimientos", "Balance", "Distribución"])

                with tab1:
                    # Scatter con separación temporal para evitar solapamientos
                    df_plot = df_final.copy()
                    df_plot["ValorVisual"] = df_plot["Cantidad"].abs()
                    df_plot["FechaVisual"] = df_plot["Fecha"] + pd.to_timedelta(
                        np.random.uniform(-6, 6, len(df_plot)), unit="h"
                    )
                    fig_scatter = px.scatter(
                        df_plot,
                        x="FechaVisual",
                        y="ValorVisual",
                        color="Tipo",
                        color_discrete_map={"Ingreso": "#2ECC71", "Gasto": "#E74C3C"},
                        size="ValorVisual",
                        size_max=25,
                        hover_data=["Compra", "Cantidad", "Balance Neto"],
                        title="Movimientos individuales"
                    )
                    fig_scatter.update_layout(template="plotly_dark", xaxis_title="Fecha", yaxis_title="Monto ($)")
                    st.plotly_chart(fig_scatter, use_container_width=True)

                with tab2:
                    fig_line = px.line(
                        df_final,
                        x="Fecha",
                        y="Balance Neto",
                        title="Balance Neto acumulado",
                        markers=True,
                        color_discrete_sequence=["#3498DB"]
                    )
                    fig_line.update_layout(template="plotly_dark", xaxis_title="Fecha", yaxis_title="Balance Neto ($)")
                    st.plotly_chart(fig_line, use_container_width=True)

                with tab3:
                    # Pie chart: proporción de ingresos vs gastos (valores absolutos)
                    summary = df_final.groupby("Tipo")["Cantidad"].sum().abs().reset_index()
                    if summary["Cantidad"].sum() == 0:
                        st.info("No hay montos para mostrar en el pie chart.")
                    else:
                        fig_pie = px.pie(
                            summary,
                            names="Tipo",
                            values="Cantidad",
                            title="Distribución Ingresos vs Gastos",
                            hole=0.45
                        )
                        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
                        fig_pie.update_layout(template="plotly_dark")
                        st.plotly_chart(fig_pie, use_container_width=True)

                # --------------------------
                # TOP 10 GASTOS
                # --------------------------
                st.markdown("### 🏆 Top 10 gastos (filtrados)")
                top_gastos = (
                    df_final[df_final["Cantidad"] < 0]
                    .assign(Compra_Normalizada=lambda x: x["Compra"].str.lower().str.extract(r'(\b\w+)')[0])
                    .groupby("Compra_Normalizada")["Cantidad"]
                    .sum()
                    .abs()
                    .sort_values(ascending=False)
                    .head(10)
                    .reset_index()
                )
                if not top_gastos.empty:
                    fig_top = px.bar(
                        top_gastos,
                        x="Cantidad",
                        y="Compra_Normalizada",
                        orientation="h",
                        title="Top 10 gastos",
                        text="Cantidad"
                    )
                    fig_top.update_layout(template="plotly_dark", yaxis={'categoryorder': 'total descending'})
                    st.plotly_chart(fig_top, use_container_width=True)
                else:
                    st.info("No hay gastos para mostrar en el Top 10.")

            else:
                st.warning("No hay métricas ni visualizaciones porque no hay datos en el periodo seleccionado.")
