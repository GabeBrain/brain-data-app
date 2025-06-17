# pages/4_Dashboard_de_Controle.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import pydeck as pdk
import time
from src.database import get_analytics_data, get_all_surveys

st.set_page_config(layout="wide", page_title="Dashboard de Controle")
st.logo("assets/logoBrain.png")

st.title("🛰️ Dashboard de Monitoramento de Campo")
st.markdown(
    "Acompanhe a performance de coleta e a distribuição geográfica dos respondentes."
)


# --- 1. Carregamento dos Dados ---
@st.cache_data(ttl=600)
def load_data():
    df = get_analytics_data()
    df_surveys = get_all_surveys()
    if 'data_pesquisa' in df.columns:
        df['data_pesquisa'] = pd.to_datetime(df['data_pesquisa'],
                                             errors='coerce')
    return df, df_surveys


df_respondents, df_surveys = load_data()

# --- Botão para Limpar o Cache ---
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Atualizar Dados do Dashboard"):
    st.cache_data.clear()
    st.rerun()

if df_respondents.empty or 'data_pesquisa' not in df_respondents.columns or df_respondents[
        'data_pesquisa'].isna().all():
    st.warning("Não há dados suficientes para exibir o dashboard.")
    st.stop()

# --- 2. Barra Lateral de Filtros ---
st.sidebar.header("Filtros do Dashboard")
df_respondents.dropna(subset=['data_pesquisa'], inplace=True)
min_date = df_respondents['data_pesquisa'].min().date()
max_date = df_respondents['data_pesquisa'].max().date()
tipo_filtro_data = st.sidebar.radio("Filtrar por:",
                                    ("Intervalo de Datas", "Seleção de Mês"))
start_date, end_date = None, None
if tipo_filtro_data == "Intervalo de Datas":
    start_date, end_date = st.sidebar.slider("Selecione o período:",
                                             min_value=min_date,
                                             max_value=max_date,
                                             value=(min_date, max_date),
                                             format="DD/MM/YYYY")
else:
    df_respondents['mes_ano'] = df_respondents['data_pesquisa'].dt.to_period(
        'M').astype(str)
    meses_disponiveis = sorted(df_respondents['mes_ano'].unique())
    meses_selecionados = st.sidebar.multiselect("Selecione os meses:",
                                                options=meses_disponiveis,
                                                default=meses_disponiveis)
    if meses_selecionados:
        start_date = pd.to_datetime(min(meses_selecionados)).date()
        end_date = (pd.to_datetime(max(meses_selecionados)) +
                    pd.offsets.MonthEnd(1)).date()

# --- 3. Lógica de Filtragem ---
df_filtrado = pd.DataFrame()
df_surveys_filtrado = pd.DataFrame()
if start_date and end_date:
    df_filtrado = df_respondents[
        (df_respondents['data_pesquisa'].dt.date >= start_date)
        & (df_respondents['data_pesquisa'].dt.date <= end_date)]
    surveys_no_periodo = df_filtrado['survey_id'].unique()
    df_surveys_filtrado = df_surveys[df_surveys['survey_id'].isin(
        surveys_no_periodo)]

# --- 4. ESTRUTURA DE CARREGAMENTO COM PLACEHOLDERS E PROGRESSO ---
st.markdown("---")

# 4A. Criar os placeholders vazios para o layout
placeholder_kpis = st.empty()
placeholder_mapa = st.empty()
placeholder_timeline = st.empty()
placeholder_tabela = st.empty()

# 4B. Barra de progresso e processamento "nos bastidores"
progress_text = "Gerando dashboard com a seleção atual..."
progress_bar = st.progress(0, text=progress_text)
time.sleep(0.3)

# Etapa 1: Calcular KPIs
progress_bar.progress(25, text="Calculando métricas de resumo...")
total_coletas = len(df_filtrado)
total_pesquisas = len(df_surveys_filtrado)
media_pct_coleta = (
    df_surveys_filtrado['collected_count'].sum() /
    df_surveys_filtrado['expected_total'].sum()
) * 100 if df_surveys_filtrado['expected_total'].sum() > 0 else 0
time.sleep(0.3)

# Etapa 2: Preparar dados do Mapa
progress_bar.progress(50, text="Preparando dados de geolocalização...")
df_mapa = df_filtrado.dropna(subset=['latitude', 'longitude'])
time.sleep(0.3)

# Etapa 3: Preparar dados da Linha do Tempo
progress_bar.progress(75, text="Preparando dados da linha do tempo...")
contagem_diaria = df_filtrado.resample(
    'D', on='data_pesquisa').size().reset_index(name='contagem')
contagem_diaria = contagem_diaria[contagem_diaria['contagem'] > 0]
time.sleep(0.3)

# Etapa Final: Renderizar tudo de uma vez
progress_bar.progress(100, text="Finalizando... Exibindo dashboard!")
time.sleep(0.3)
progress_bar.empty()

# 4C. Renderização final: preenchendo os placeholders
with placeholder_kpis.container():
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Pesquisas no Período", f"{total_pesquisas}")
    col2.metric("Total de Coletas no Período", f"{total_coletas:,}")
    col3.metric("Média Ponderada de Coleta (%)", f"{media_pct_coleta:.2f}%")
    st.markdown("---")

with placeholder_mapa.container():
    st.subheader("📍 Densidade Geográfica de Respondentes no Período")
    if not df_mapa.empty:
        view_state = pdk.ViewState(latitude=df_mapa['latitude'].mean(),
                                   longitude=df_mapa['longitude'].mean(),
                                   zoom=3.5,
                                   pitch=50)
        layer = pdk.Layer('HeatmapLayer',
                          data=df_mapa,
                          get_position='[longitude, latitude]',
                          opacity=0.9,
                          get_weight=1)
        st.pydeck_chart(
            pdk.Deck(map_style='mapbox://styles/mapbox/light-v9',
                     initial_view_state=view_state,
                     layers=[layer]))
    else:
        st.info(
            "Nenhum dado de geolocalização disponível para o período selecionado."
        )

with placeholder_timeline.container():
    st.markdown("---")
    st.subheader("📅 Coletas Realizadas ao Longo do Tempo no Período")
    if not contagem_diaria.empty:
        st.bar_chart(contagem_diaria.set_index('data_pesquisa'))
    else:
        st.info("Nenhuma coleta encontrada para o período selecionado.")

# --- 6. Detalhamento de Status das Pesquisas ---
st.markdown("---")
st.header("Detalhamento de Status das Pesquisas no Período")

if not df_surveys_filtrado.empty:
    # Cria a coluna 'status' com base na regra de negócio de 98%
    df_surveys_filtrado['status'] = np.where(
        df_surveys_filtrado['collected_percentage'] >= 98, 'Finalizada',
        'Em Campo')

    # Separa o DataFrame em dois, um para cada status
    df_em_campo = df_surveys_filtrado[df_surveys_filtrado['status'] ==
                                      'Em Campo']
    df_finalizadas = df_surveys_filtrado[df_surveys_filtrado['status'] ==
                                         'Finalizada']

    # Define as colunas que queremos exibir
    colunas_para_exibir = [
        'research_name', 'collected_count', 'expected_total',
        'collected_percentage'
    ]

    # Layout em duas colunas
    col1, col2 = st.columns(2)

    with col1:
        st.subheader(f"🌱 Em Campo ({len(df_em_campo)})")
        st.dataframe(df_em_campo[colunas_para_exibir],
                     use_container_width=True,
                     hide_index=True)

    with col2:
        st.subheader(f"🏁 Finalizadas ({len(df_finalizadas)})")
        st.dataframe(df_finalizadas[colunas_para_exibir],
                     use_container_width=True,
                     hide_index=True)
else:
    st.info("Nenhuma pesquisa encontrada para o período selecionado.")
