import streamlit as st
import pandas as pd
import plotly.express as px

# ==============================
# CONFIGURACIÓN GENERAL
# ==============================
st.set_page_config(
    page_title="Dashboard Financiero",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        body {
            background-color: #0E1117;
            color: #FAFAFA;
        }
        [data-testid="stSidebar"] {
            background-color: #1A1D23;
        }
        .stMetric {
            background-color: #1A1D23;
            border-radius: 12px;
            padding: 10px;
            color: #FAFAFA;
        }
        .css-1v0mbdj, .css-16idsys, .css-10trblm {
            color: #FAFAFA !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# ==============================
# CARGA DE DATOS
# ==============================
st.title("📊 Dashboard Financiero - Tema Oscuro")

archivo = st.file_uploader("📁 Sube tu archivo CSV", type=["csv"])
if archivo is not None:
    df = pd.read_csv(archivo)
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")

    # Columna de tipo (Ingreso/Egreso)
    df["Tipo"] = df["Monto"].apply(lambda x: "Ingreso" if x > 0 else "Egreso")

    # ==============================
    # FILTROS
    # ==============================
    st.sidebar.header("Filtros")

    años = sorted(df["Fecha"].dt.year.dropna().unique())
    año = st.sidebar.selectbox("Año", ["Todos"] + list(años))

    meses = sorted(df["Fecha"].dt.month_name(locale="es_MX").dropna().unique(), key=lambda m: df["Fecha"].dt.month[df["Fecha"].dt.month_name(locale="es_MX") == m].iloc[0])
    mes = st.sidebar.selectbox("Mes", ["Todos"] + list(meses))

    fecha_min = df["Fecha"].min()
    fecha_max = df["Fecha"].max()
    rango_fechas = st.sidebar.date_input("Rango de fechas", [fecha_min, fecha_max])

    df_filtrado = df.copy()

    if año != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Fecha"].dt.year == año]
    if mes != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Fecha"].dt.month_name(locale="es_MX") == mes]
    if len(rango_fechas) == 2:
        df_filtrado = df_filtrado[
            (df_filtrado["Fecha"] >= pd.to_datetime(rango_fechas[0])) &
            (df_filtrado["Fecha"] <= pd.to_datetime(rango_fechas[1]))
        ]

    # ==============================
    # CÁLCULOS
    # ==============================
    ingresos = df_filtrado[df_filtrado["Monto"] > 0]["Monto"].sum()
    egresos = df_filtrado[df_filtrado["Monto"] < 0]["Monto"].sum()
    balance = ingresos + egresos

    # ==============================
    # MÉTRICAS
    # ==============================
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Ingresos", f"${ingresos:,.2f}")
    col2.metric("💸 Egresos", f"${egresos:,.2f}")
    col3.metric("🧾 Balance Neto", f"${balance:,.2f}")

    # ==============================
    # TABLA DETALLADA
    # ==============================
    df_filtrado = df_filtrado.sort_values("Fecha")
    df_filtrado["Balance Neto"] = df_filtrado["Monto"].cumsum() + 8500
    st.dataframe(df_filtrado, use_container_width=True)

    # ==============================
    # GRÁFICO BALANCE MENSUAL (Barras + Línea)
    # ==============================
    df_mensual = df_filtrado.groupby(df_filtrado["Fecha"].dt.to_period("M"))["Monto"].sum().reset_index()
    df_mensual["Fecha"] = df_mensual["Fecha"].dt.to_timestamp()
    df_mensual["Balance Neto"] = df_mensual["Monto"].cumsum() + 8500

    fig_balance = px.bar(
        df_mensual,
        x="Fecha",
        y="Monto",
        title="📈 Balance Mensual con Línea de Tendencia",
        labels={"Monto": "Monto", "Fecha": "Fecha"},
        color_discrete_sequence=["#00CC96"]
    )
    fig_balance.add_scatter(
        x=df_mensual["Fecha"],
        y=df_mensual["Balance Neto"],
        mode="lines+markers",
        name="Tendencia Balance Neto",
        line=dict(color="#AB63FA", width=3),
    )
    fig_balance.update_layout(
        template="plotly_dark",
        title_x=0.5,
        height=400
    )
    st.plotly_chart(fig_balance, use_container_width=True)

    # ==============================
    # TOP 10 CATEGORÍAS
    # ==============================
    if "Categoría" in df_filtrado.columns:
        df_top = df_filtrado.groupby("Categoría")["Monto"].sum().nlargest(10).reset_index()
        fig_top = px.bar(
            df_top,
            x="Monto",
            y="Categoría",
            orientation="h",
            color="Monto",
            color_continuous_scale=["#EF553B", "#00CC96"],
            title="🏆 Top 10 Categorías",
        )
        fig_top.update_layout(template="plotly_dark", title_x=0.5, height=400)
        st.plotly_chart(fig_top, use_container_width=True)

    # ==============================
    # PIE CHART (Distribución Ingresos/Egresos)
    # ==============================
    fig_pie = px.pie(
        df_filtrado,
        names="Tipo",
        values="Monto",
        color="Tipo",
        color_discrete_map={"Ingreso": "#00CC96", "Egreso": "#EF553B"},
        title="🥧 Distribución de Ingresos vs Egresos",
    )
    fig_pie.update_layout(template="plotly_dark", title_x=0.5, height=400)
    st.plotly_chart(fig_pie, use_container_width=True)

else:
    st.info("👆 Sube un archivo CSV para comenzar.")
