# pages/4_Dashboard_de_Controle.py

import streamlit as st
import pandas as pd
import numpy as np
import time
from src.database import get_analytics_data, get_all_surveys
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Dashboard de Controle")
st.logo("assets/logoBrain.png")

# --- Título e Descrição ---
st.title("🛰️ Dashboard de Monitoramento de Campo")
st.markdown(
    "Acompanhe a performance de coleta e a distribuição geográfica dos respondentes."
)


# --- 1. Carregamento e Preparação Inicial dos Dados ---
@st.cache_data(ttl=600)
def load_data():
    """Carrega os dados e já pré-processa as colunas de data e status."""
    df_resp = get_analytics_data()
    df_surv = get_all_surveys()

    # Converte a coluna de data dos respondentes
    if 'data_pesquisa' in df_resp.columns:
        df_resp['data_pesquisa'] = pd.to_datetime(df_resp['data_pesquisa'],
                                                  errors='coerce')

    # Adiciona a coluna de status às pesquisas
    if not df_surv.empty and 'collected_percentage' in df_surv.columns:
        df_surv['status'] = np.where(df_surv['collected_percentage'] >= 98,
                                     'Finalizada', 'Em Campo')
    else:
        df_surv['status'] = 'Indefinido'

    return df_resp, df_surv


df_respondents, df_surveys = load_data()

# --- Botão para Limpar o Cache ---
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Atualizar Dados do Dashboard"):
    with st.spinner("Limpando cache e recarregando dados..."):
        st.cache_data.clear()
        st.rerun()

# --- Verificação de Dados Mínimos ---
if df_respondents.empty or 'data_pesquisa' not in df_respondents.columns or df_respondents[
        'data_pesquisa'].isna().all():
    st.warning(
        "Não há dados de respondentes suficientes para exibir o dashboard.")
    st.stop()

# --- 2. Barra Lateral de Filtros (LÓGICA TOTALMENTE REFEITA) ---
st.sidebar.header("Filtros do Dashboard")

# Filtro 1: Status do Projeto
status_options = ['Todos'] + df_surveys['status'].unique().tolist()
status_selecionado = st.sidebar.selectbox("Filtrar por Status do Projeto:",
                                          options=status_options)

# Filtra as pesquisas com base no status selecionado
if status_selecionado == 'Todos':
    surveys_disponiveis = df_surveys
else:
    surveys_disponiveis = df_surveys[df_surveys['status'] ==
                                     status_selecionado]

# Filtro 2: Pesquisa Específica
project_options = ["Todos os Projetos"
                   ] + surveys_disponiveis['research_name'].tolist()
projeto_selecionado = st.sidebar.selectbox("Selecione um Projeto Específico:",
                                           options=project_options)

# Filtra as pesquisas novamente com base no projeto selecionado
if projeto_selecionado == "Todos os Projetos":
    df_surveys_filtrado_pre = surveys_disponiveis
else:
    df_surveys_filtrado_pre = surveys_disponiveis[
        surveys_disponiveis['research_name'] == projeto_selecionado]

# Filtro 3: Intervalo de Datas (usando o novo date_input)
st.sidebar.markdown("---")
st.sidebar.write("**Filtrar por Período de Coleta:**")

# Pré-filtra os respondentes com base nos projetos já selecionados
ids_pesquisas_selecionadas = df_surveys_filtrado_pre['survey_id'].unique()
df_respondents_para_datas = df_respondents[df_respondents['survey_id'].isin(
    ids_pesquisas_selecionadas)].dropna(subset=['data_pesquisa'])

start_date, end_date = None, None
if not df_respondents_para_datas.empty:
    min_date = df_respondents_para_datas['data_pesquisa'].min().date()
    max_date = df_respondents_para_datas['data_pesquisa'].max().date()

    # NOVO SELETOR DE CALENDÁRIO
    datas_selecionadas = st.sidebar.date_input(
        "Selecione o início e o fim do período:",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        format="DD/MM/YYYY")

    # Garante que temos um início e um fim
    if len(datas_selecionadas) == 2:
        start_date, end_date = datas_selecionadas
else:
    st.sidebar.info(
        "Nenhum dado de coleta para o projeto e status selecionados.")

# --- 3. Lógica de Filtragem Final ---
df_filtrado = pd.DataFrame()
df_surveys_filtrado = df_surveys_filtrado_pre  # O filtro de status/projeto já foi aplicado

if start_date and end_date:
    # Filtra os respondentes pela data final
    df_filtrado = df_respondents_para_datas[
        (df_respondents_para_datas['data_pesquisa'].dt.date >= start_date)
        & (df_respondents_para_datas['data_pesquisa'].dt.date <= end_date)]
    # Garante que os IDs das pesquisas no período correspondem aos respondentes filtrados
    surveys_no_periodo = df_filtrado['survey_id'].unique()
    df_surveys_filtrado = df_surveys_filtrado[
        df_surveys_filtrado['survey_id'].isin(surveys_no_periodo)]
else:
    # Se não houver data, os dataframes ficam vazios para o dashboard não quebrar
    df_filtrado = pd.DataFrame(columns=df_respondents.columns)
    df_surveys_filtrado = pd.DataFrame(columns=df_surveys.columns)

# --- 4. ESTRUTURA DE CARREGAMENTO COM PLACEHOLDERS E PROGRESSO ---
# (Esta seção permanece a mesma)
st.markdown("---")
placeholder_kpis = st.empty()
placeholder_mapa = st.empty()
placeholder_timeline = st.empty()
progress_bar = st.progress(0, text="Gerando dashboard com a seleção atual...")
time.sleep(0.3)
progress_bar.progress(25, text="Calculando métricas de resumo...")
total_coletas = len(df_filtrado)
total_pesquisas = len(df_surveys_filtrado)
media_pct_coleta = (
    df_surveys_filtrado['collected_count'].sum() /
    df_surveys_filtrado['expected_total'].sum() *
    100) if df_surveys_filtrado['expected_total'].sum() > 0 else 0
time.sleep(0.3)
progress_bar.progress(50, text="Preparando dados de geolocalização...")
df_mapa = df_filtrado.dropna(subset=['latitude', 'longitude'])
time.sleep(0.3)
progress_bar.progress(75, text="Preparando dados da linha do tempo...")
if not df_filtrado.empty:
    contagem_diaria = df_filtrado.resample(
        'D', on='data_pesquisa').size().reset_index(name='contagem')
    contagem_diaria = contagem_diaria[contagem_diaria['contagem'] > 0]
else:
    contagem_diaria = pd.DataFrame()
time.sleep(0.3)
progress_bar.progress(100, text="Finalizando... Exibindo dashboard!")
time.sleep(0.3)
progress_bar.empty()

# --- 5. Renderização dos Componentes do Dashboard ---
with placeholder_kpis.container():
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Pesquisas na Seleção", f"{total_pesquisas}")
    col2.metric("Total de Coletas no Período", f"{total_coletas:,}")
    col3.metric("Média Ponderada de Coleta (%)", f"{media_pct_coleta:.2f}%")
    st.markdown("---")

# Linha do Tempo de Coletas
st.subheader("📅 Coletas Realizadas ao Longo do Tempo no Período")
if not df_filtrado.empty and 'data_pesquisa' in df_filtrado.columns:
    # Garante que a coluna de data é do tipo datetime
    df_filtrado['data_pesquisa'] = pd.to_datetime(df_filtrado['data_pesquisa'], errors='coerce')
    df_para_grafico = df_filtrado.dropna(subset=['data_pesquisa'])

    if not df_para_grafico.empty:
        # ALTERADO: Agrupando por hora ('h') em vez de dia ('D')
        contagem_horaria = df_para_grafico.resample('h', on='data_pesquisa').size().reset_index(name='Coletas por Hora')
        contagem_horaria = contagem_horaria[contagem_horaria['Coletas por Hora'] > 0]
        
        if not contagem_horaria.empty:
            # ALTERADO: Usando st.area_chart para uma visualização de fluxo
            st.area_chart(contagem_horaria.set_index('data_pesquisa'))
        else:
            st.info("Nenhuma coleta encontrada para a seleção atual.")
    else:
        st.info("Nenhuma coleta encontrada para a seleção atual.")
else:
    st.info("Nenhuma coleta encontrada para a seleção atual.")


# Detalhamento das Pesquisas (Tabela)
st.markdown("---")
st.header("Detalhamento das Pesquisas na Seleção")
if not df_surveys_filtrado.empty:
    colunas_para_exibir = ['research_name', 'collected_count', 'expected_total', 'collected_percentage', 'status']
    st.dataframe(df_surveys_filtrado[colunas_para_exibir], use_container_width=True, hide_index=True,
                 column_config={"collected_percentage": st.column_config.ProgressColumn(
                     "Percentual Coletado", format="%.2f%%", min_value=0, max_value=100,
                 )})
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

