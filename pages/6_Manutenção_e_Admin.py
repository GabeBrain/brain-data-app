# pages/5_Manutenção_e_Admin.py
import streamlit as st
import pandas as pd
import numpy as np
from src.database import (get_all_surveys, resync_full_survey,
                          consolidate_survey_data, get_all_consolidated_data,
                          save_analytics_data)
from src.data_processing import process_and_standardize_data

st.set_page_config(layout="wide", page_title="Administração")
st.logo("assets/logoBrain.png")

st.title("⚙️ Manutenção e Administração do Sistema")
st.warning(
    "As ferramentas nesta página executam operações pesadas e, em alguns casos, destrutivas. Use com cuidado e apenas quando necessário."
)

# --- FERRAMENTA 1: Re-sincronização de Pesquisa Única ---
with st.expander("🌀 Re-sincronização Completa de uma Pesquisa"):
    st.markdown(
        "**Use para:** Forçar uma nova leitura da API para uma pesquisa específica, apagando todos os seus dados antigos. Útil quando o link da API de uma pesquisa foi corrigido."
    )

    all_surveys_df_sync = get_all_surveys()
    if all_surveys_df_sync.empty:
        st.info("Nenhuma pesquisa ativa para selecionar.")
    else:
        survey_options = {
            row['research_name']: (row['survey_id'], row['api_link'])
            for index, row in all_surveys_df_sync.iterrows()
        }

        selected_survey_name_resync = st.selectbox(
            "Selecione a pesquisa para re-sincronizar:",
            options=survey_options.keys(),
            key="resync_selectbox"  # Usando uma chave única para o widget
        )

        # O botão agora apenas define uma variável booleana
        resync_button_clicked = st.button(
            "Forçar Re-sincronização Completa desta Pesquisa")

# --- A LÓGICA DE EXECUÇÃO AGORA FICA FORA DO EXPANDER ---
# Ela só será acionada se o botão, que está lá dentro, for clicado.
if resync_button_clicked:
    # Verificamos se uma pesquisa foi selecionada
    if 'selected_survey_name_resync' in locals(
    ) and selected_survey_name_resync:
        survey_id_to_resync, api_link_to_resync = survey_options[
            selected_survey_name_resync]

        # O st.status agora é criado no corpo principal da página, não aninhado.
        with st.status(
                f"Executando re-sincronização para '{selected_survey_name_resync}'...",
                expanded=True) as status:
            success, message = resync_full_survey(survey_id_to_resync,
                                                  api_link_to_resync)

            if success:
                status.update(label="Concluído!",
                              state="complete",
                              expanded=False)
                st.success(message)
                # Adicionamos um rerun para que a lista de pesquisas seja atualizada
                st.rerun()
            else:
                status.update(label="Falha!", state="error", expanded=True)
                st.error(message)

# --- FERRAMENTA 2: Re-consolidação Total ---
with st.expander("🔄 Forçar Re-consolidação de Dados Brutos"):
    st.markdown(
        "**Use para:** Re-processar todos os dados da `survey_respondent_data` (JSONB) para a `consolidated_data` (tabela longa). Útil se a lógica de extração de colunas mudar."
    )

    if st.button("Re-consolidar TODAS as Pesquisas"):
        with st.spinner("Iniciando re-consolidação de todos os dados..."):
            all_surveys_df_recon = get_all_surveys()
            success_count = 0
            error_count = 0
            progress_bar = st.progress(0, text="Iniciando...")

            for i, row in enumerate(all_surveys_df_recon.itertuples()):
                progress_text = f"Processando: {row.research_name} ({i+1}/{len(all_surveys_df_recon)})"
                progress_bar.progress((i + 1) / len(all_surveys_df_recon),
                                      text=progress_text)

                success, msg = consolidate_survey_data(row.survey_id)
                if success:
                    success_count += 1
                else:
                    error_count += 1
                    st.error(
                        f"Erro na re-consolidação de '{row.research_name}': {msg}"
                    )

            progress_bar.empty()
        st.success(
            f"Re-consolidação concluída! ✅ Sucessos: {success_count} | ❌ Falhas: {error_count}"
        )

# --- FERRAMENTA 3: Pipeline de Transformação Analítica ---
st.markdown("---")
st.header("🚀 Pipeline de Transformação Analítica")
with st.container(border=True):
    st.subheader(
        "Processar e Carregar Tabela de Análise (`analytics_respondents`)")
    st.markdown(
        "**Use para:** Processar todos os dados da `consolidated_data`, aplicar as regras de padronização e limpeza, e carregar o resultado na tabela final `analytics_respondents`. Execute isso após grandes mudanças ou para a carga inicial."
    )

    if st.button("Executar Pipeline de Transformação Completa"):
        with st.spinner(
                "Iniciando pipeline... Este processo pode ser demorado."):
            st.write("1. Buscando todos os dados consolidados e metadados...")
            long_df = get_all_consolidated_data()
            all_surveys_info = get_all_surveys()

            if not long_df.empty:
                st.write("2. Padronizando e enriquecendo os dados...")
                analytics_df = process_and_standardize_data(
                    long_df, all_surveys_info)

                if not analytics_df.empty:
                    st.write(
                        f"3. Salvando {len(analytics_df)} registros processados na tabela de análise..."
                    )
                    success, msg = save_analytics_data(analytics_df)

                    if success:
                        st.success(
                            f"✅ Pipeline de transformação concluída com sucesso! {msg}"
                        )
                        st.balloons()
                    else:
                        st.error(f"❌ Falha na etapa de salvamento: {msg}")
                else:
                    st.warning(
                        "O processamento não gerou dados para salvar. Verifique a lógica de transformação."
                    )
            else:
                st.warning(
                    "Tabela de dados consolidados está vazia. Nada a processar."
                )
