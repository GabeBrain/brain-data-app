# pages/2_Análise_Consolidada.py

import streamlit as st
import pandas as pd
import numpy as np
from src.database import (get_consolidation_log, consolidate_survey_data,
                          get_all_surveys, get_all_consolidated_data,
                          get_surveys_with_recent_new_data,
                          get_consolidated_data_for_surveys)
from src.data_processing import CODIGOS_PARA_TEXTO_ORIGINAL

st.set_page_config(layout="wide", page_title="Análise Consolidada")
st.logo("assets/logoBrain.png")

st.title("📊 Análise e Saúde da Consolidação")
st.markdown("""
Esta página monitora a saúde do nosso banco de dados consolidado e permite a exploração interativa dos dados.
""")

# --- Visualização da Métrica de Consolidação (sem alterações) ---
st.header("📈 Acompanhamento de Perguntas Consolidadas por Pesquisa")
log_df = get_consolidation_log()
if log_df.empty:
    st.info("Ainda não há dados de consolidação.")
else:
    # (Lógica do gráfico de barras continua a mesma)
    log_df.rename(columns={
        'research_name': 'Pesquisa',
        'unique_questions_consolidated': 'Nº de Perguntas Mapeadas'
    },
                  inplace=True)
    chart_df = log_df[['Pesquisa', 'Nº de Perguntas Mapeadas']].copy()
    chart_df['Nº de Perguntas Mapeadas'].fillna(0, inplace=True)
    chart_df.set_index('Pesquisa', inplace=True)
    st.write(
        "O gráfico abaixo mostra o número de colunas (perguntas) que foram corretamente mapeadas."
    )
    st.bar_chart(chart_df, height=500)
    with st.expander("Ver tabela de dados detalhada do log"):
        st.dataframe(log_df, use_container_width=True)

# --- Bloco Refatorado: Explorador de Dados Interativo ---
st.header("🔬 Explorador de Dados Consolidados")
st.markdown(
    "Selecione um conjunto de dados para carregar e analisar em detalhe.")

# --- Controles Interativos ---
all_surveys_df = get_all_surveys()
all_surveys_options = {
    row['research_name']: row['survey_id']
    for index, row in all_surveys_df.iterrows()
}
id_to_name_map = {v: k for k, v in all_surveys_options.items()}

option = st.selectbox(
    "Quais dados você gostaria de analisar?",
    ("Últimas 5 Pesquisas Ativas", "Selecionar uma Pesquisa Específica",
     "Carregar TUDO (Lento)"),
    key="data_explorer_option")

selected_survey_id = None
if option == "Selecionar uma Pesquisa Específica":
    selected_survey_name = st.selectbox("Escolha a pesquisa",
                                        options=all_surveys_options.keys())
    selected_survey_id = all_surveys_options[selected_survey_name]

# Inicializa as variáveis no estado da sessão para guardar os dados e o rótulo
if 'loaded_data' not in st.session_state:
    st.session_state['loaded_data'] = pd.DataFrame()
if 'loaded_data_label' not in st.session_state:
    st.session_state['loaded_data_label'] = "Nenhum dado carregado."

# Botão para acionar o carregamento
if st.button("Carregar Dados para Análise"):
    with st.spinner("Buscando dados no banco... Isso pode levar um momento."):
        df_to_load = pd.DataFrame()
        label_to_set = "Nenhum dado encontrado para a seleção."

        if option == "Últimas 5 Pesquisas Ativas":
            # Usando a nova função mais inteligente
            latest_ids = get_surveys_with_recent_new_data(limit_surveys=5)
            if latest_ids:
                df_to_load = get_consolidated_data_for_surveys(latest_ids)
                latest_names = [
                    id_to_name_map.get(sid, f"ID {sid}") for sid in latest_ids
                ]
                label_to_set = f"Últimas Pesquisas Ativas: {', '.join(latest_names)}"

        elif option == "Selecionar uma Pesquisa Específica":
            if selected_survey_id:
                df_to_load = get_consolidated_data_for_surveys(
                    [selected_survey_id])
                label_to_set = f"Dados da Pesquisa: {id_to_name_map.get(selected_survey_id)}"

        elif option == "Carregar TUDO (Lento)":
            df_to_load = get_all_consolidated_data()
            label_to_set = "Dados de Todas as Pesquisas"

        st.session_state['loaded_data'] = df_to_load
        st.session_state['loaded_data_label'] = label_to_set

# --- Seção de Análise (Usa os dados carregados do st.session_state) ---
df_loaded = st.session_state['loaded_data']
data_label = st.session_state['loaded_data_label']

if df_loaded.empty:
    st.info(
        "Nenhum dado carregado. Selecione uma opção e clique no botão acima para começar."
    )
else:
    st.success(
        f"Analisando {len(df_loaded['respondent_id'].unique())} respondentes únicos."
    )

    # O expander agora usa o rótulo dinâmico
    with st.expander(f"Ver registros de: {data_label}"):
        st.dataframe(df_loaded, use_container_width=True)

    st.subheader("Análise de Respostas por Pergunta")

    unique_codes_in_df = set(df_loaded['question_code'].unique())

    for question_code in CODIGOS_PARA_TEXTO_ORIGINAL.keys():
        if question_code in unique_codes_in_df:
            question_text = CODIGOS_PARA_TEXTO_ORIGINAL.get(
                question_code, "Texto não encontrado")

            with st.expander(f"**{question_code}**: {question_text}"):
                question_df = df_loaded[df_loaded['question_code'] ==
                                        question_code]
                value_counts = question_df['answer_value'].value_counts(
                ).reset_index()
                value_counts.columns = ['Resposta', 'Contagem']
                st.markdown(
                    f"A pergunta **'{question_code}'** teve **{len(value_counts)}** respostas diferentes nesta amostra."
                )

                col1, col2 = st.columns([1, 2])
                with col1:
                    st.write("Tabela de Frequência:")
                    st.dataframe(value_counts,
                                 use_container_width=True,
                                 height=300)
                with col2:
                    st.write("Gráfico das Respostas Mais Comuns:")
                    chart_data = value_counts.set_index('Resposta')
                    st.bar_chart(chart_data.head(15))
