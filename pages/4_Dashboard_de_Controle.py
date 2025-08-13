# pages/4_Dashboard_de_Controle.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap
import time
from src.database import get_analytics_data, get_all_surveys

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Dashboard de Controle")
st.logo("assets/logoBrain.png")

# --- Título e Descrição ---
st.title("🛰️ Dashboard de Monitoramento de Campo")
st.markdown("Acompanhe a performance de coleta e a distribuição geográfica dos respondentes.")

# --- 1. Carregamento e Preparação dos Dados ---
@st.cache_data(ttl=600)
def load_data():
    df_resp = get_analytics_data()
    df_surv = get_all_surveys()

    # Conversões e pré-processamento
    if not df_resp.empty:
        df_resp['data_pesquisa'] = pd.to_datetime(df_resp['data_pesquisa'], errors='coerce')
        # GARANTE O TIPO CORRETO DA CHAVE DE JUNÇÃO
        df_resp['survey_id'] = pd.to_numeric(df_resp['survey_id'], errors='coerce')

    if not df_surv.empty:
        df_surv['status'] = np.where(df_surv['collected_percentage'] >= 98, 'Finalizada', 'Em Campo')
        # GARANTE O TIPO CORRETO DA CHAVE DE JUNÇÃO
        df_surv['survey_id'] = pd.to_numeric(df_surv['survey_id'], errors='coerce')
    else:
        df_surv['status'] = 'Indefinido'
        
    return df_resp, df_surv

df_respondents, df_surveys = load_data()

# --- Barra Lateral ---
st.sidebar.header("Filtros do Dashboard")
if st.sidebar.button("🔄 Atualizar Dados do Dashboard"):
    st.cache_data.clear()
    st.rerun()

# --- Verificação de Dados Mínimos ---
if df_respondents.empty or 'data_pesquisa' not in df_respondents.columns or df_respondents['data_pesquisa'].isna().all():
    st.warning("Não há dados de respondentes suficientes para exibir o dashboard.")
    st.stop()

# --- 2. LÓGICA DE FILTROS SEQUENCIAL E CORRIGIDA ---
# Começamos com os dataframes completos
df_surveys_filtrado = df_surveys.copy()
df_respondents_filtrado = df_respondents.copy()

# Filtro 1: Status do Projeto
status_options = ['Todos'] + df_surveys['status'].unique().tolist()
status_selecionado = st.sidebar.selectbox("Filtrar por Status do Projeto:", options=status_options)

if status_selecionado != 'Todos':
    df_surveys_filtrado = df_surveys_filtrado[df_surveys_filtrado['status'] == status_selecionado]

# Filtro 2: Pesquisa Específica (baseado no resultado do filtro de status)
project_options = ["Todos os Projetos"] + df_surveys_filtrado['research_name'].tolist()
projeto_selecionado = st.sidebar.selectbox("Selecione um Projeto Específico:", options=project_options)

if projeto_selecionado != "Todos os Projetos":
    df_surveys_filtrado = df_surveys_filtrado[df_surveys_filtrado['research_name'] == projeto_selecionado]

# AGORA, filtramos os respondentes com base nas pesquisas que sobraram
ids_pesquisas_selecionadas = df_surveys_filtrado['survey_id'].unique()
df_respondents_filtrado = df_respondents_filtrado[df_respondents_filtrado['survey_id'].isin(ids_pesquisas_selecionadas)]

# Filtro 3: Intervalo de Datas (baseado nos respondentes já filtrados)
st.sidebar.markdown("---")
st.sidebar.write("**Filtrar por Período de Coleta:**")

df_respondents_com_data = df_respondents_filtrado.dropna(subset=['data_pesquisa'])

start_date, end_date = None, None
if not df_respondents_com_data.empty:
    min_date = df_respondents_com_data['data_pesquisa'].min().date()
    max_date = df_respondents_com_data['data_pesquisa'].max().date()

    datas_selecionadas = st.sidebar.date_input(
        "Selecione o início e o fim do período:",
        value=(min_date, max_date), min_value=min_date, max_value=max_date, format="DD/MM/YYYY"
    )

    if len(datas_selecionadas) == 2:
        start_date, end_date = datas_selecionadas
        # Aplicamos o filtro final de data
        df_respondents_filtrado = df_respondents_filtrado[
            (df_respondents_filtrado['data_pesquisa'].dt.date >= start_date) &
            (df_respondents_filtrado['data_pesquisa'].dt.date <= end_date)
        ]
        # Garantimos que a lista de surveys reflita apenas as que têm dados no período de data selecionado
        surveys_no_periodo = df_respondents_filtrado['survey_id'].unique()
        df_surveys_filtrado = df_surveys_filtrado[df_surveys_filtrado['survey_id'].isin(surveys_no_periodo)]
else:
    st.sidebar.info("Nenhum dado de coleta para o projeto e status selecionados.")
    # Se não houver dados, zeramos os dataframes para o dashboard não quebrar
    df_respondents_filtrado = pd.DataFrame(columns=df_respondents.columns)
    df_surveys_filtrado = pd.DataFrame(columns=df_surveys.columns)

# --- 3. Renderização do Dashboard ---
st.markdown("---")

# KPIs
total_coletas = len(df_respondents_filtrado)
total_pesquisas = len(df_surveys_filtrado)
if not df_surveys_filtrado.empty and df_surveys_filtrado['expected_total'].sum() > 0:
    media_pct_coleta = (df_surveys_filtrado['collected_count'].sum() / df_surveys_filtrado['expected_total'].sum()) * 100
else:
    media_pct_coleta = 0

col1, col2, col3 = st.columns(3)
col1.metric("Total de Pesquisas na Seleção", f"{total_pesquisas}")
col2.metric("Total de Coletas no Período", f"{total_coletas:,}")
col3.metric("Média Ponderada de Coleta (%)", f"{media_pct_coleta:.2f}%")

st.markdown("---")

# Linha do Tempo
st.subheader("📅 Coletas Realizadas ao Longo do Tempo no Período")
if not df_respondents_filtrado.empty:
    contagem_diaria = df_respondents_filtrado.resample('D', on='data_pesquisa').size().reset_index(name='contagem')
    contagem_diaria = contagem_diaria[contagem_diaria['contagem'] > 0]
    if not contagem_diaria.empty:
        st.bar_chart(contagem_diaria.set_index('data_pesquisa'))
    else:
        st.info("Nenhuma coleta encontrada para a seleção atual.")
else:
    st.info("Nenhuma coleta encontrada para a seleção atual.")

# Detalhamento das Pesquisas
st.markdown("---")
st.header("Detalhamento das Pesquisas na Seleção")
if not df_surveys_filtrado.empty:
    st.dataframe(df_surveys_filtrado[['research_name', 'collected_count', 'expected_total', 'collected_percentage', 'status']],
                 use_container_width=True, hide_index=True,
                 column_config={"collected_percentage": st.column_config.ProgressColumn(
                     "Percentual Coletado", format="%.2f%%", min_value=0, max_value=100)})
else:
    st.info("Nenhuma pesquisa encontrada para os filtros selecionados.")


# --- NOVO: MAPA DENTRO DE UM EXPANDER ---
st.markdown("---")
with st.expander("📍 Ver Densidade Geográfica de Respondentes"):
    df_mapa = df_filtrado.dropna(subset=['latitude', 'longitude'])
    
    if not df_mapa.empty:
        with st.spinner('Renderizando mapa de calor...'):
            # Cria um mapa base centrado no Brasil
            map_center = [-14.2350, -51.9253]
            m = folium.Map(location=map_center, zoom_start=4, tiles="cartodbpositron")

            # Prepara os dados para o HeatMap: uma lista de listas [lat, lon]
            heat_data = df_mapa[['latitude', 'longitude']].values.tolist()
            
            # Adiciona a camada de mapa de calor
            HeatMap(heat_data, radius=15).add_to(m)

            # Renderiza o mapa no Streamlit
            st_folium(m, use_container_width=True, height=500)
    else:
        st.info("Nenhum dado de geolocalização disponível para a seleção atual.")

