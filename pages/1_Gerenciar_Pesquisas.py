# pages/1_Gerenciar_Pesquisas.py

import streamlit as st
import datetime
import pandas as pd
import numpy as np
from src.database import (
    add_survey_metadata,
    get_all_surveys,
    get_survey_summary_stats,
    update_survey_metadata,
    delete_survey,
    store_respondent_data,
    get_respondent_count,
    consolidate_survey_data,
    update_survey_stats,
    get_updatable_surveys,
    get_consolidated_data_for_surveys,
    save_analytics_data,
check_api_link_exists,
)

from src.data_ingestion import fetch_data_from_api
from src.data_processing import map_api_columns_to_target_codes, process_and_standardize_data

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Gerenciar Pesquisas")
st.logo("assets/logoBrain.png")

st.title("📋 Gerenciar Pesquisas")
st.markdown(
    "Aqui você pode adicionar, visualizar, editar e excluir os metadados das pesquisas cadastradas."
)

# --- Seção para Adicionar Nova Pesquisa ---
with st.expander("➕ Adicionar Nova Pesquisa", expanded=False):
    # (O código para Adicionar Pesquisa continua o mesmo, sem alterações)
    with st.form("add_survey_form", clear_on_submit=True):
        research_name_add = st.text_input(
            "Nome da Pesquisa",
            help="Ex: '2025_0012 São José do Rio Preto- TRR'",
            key="add_research_name")
        creation_date_add = st.date_input("Data de Criação",
                                          datetime.date.today(),
                                          key="add_creation_date")
        api_link_add = st.text_input(
            "Link da API",
            help="URL completa da API que retorna os dados da pesquisa",
            key="add_api_link")
        expected_total_add = st.number_input(
            "Total Esperado de Respondentes (Opcional)",
            min_value=0,
            value=None,
            format="%d",
            help="Número de respondentes que se espera para esta pesquisa.",
            key="add_expected_total")
        submit_button = st.form_submit_button("Cadastrar Pesquisa")
        if submit_button:
            if not research_name_add or not api_link_add:
                st.warning(
                    "Por favor, preencha o Nome da Pesquisa e o Link da API.")
            else:
                # --- NOVA LÓGICA DE VERIFICAÇÃO ---
                api_link_limpo = api_link_add.strip()
                pesquisa_existente = check_api_link_exists(api_link_limpo)

                if pesquisa_existente:
                    st.error(
                        f"❌ **Erro:** Este link de API já está em uso pela pesquisa: '{pesquisa_existente}'. Por favor, use um link diferente."
                    )
                else:
                    # Se não houver conflito, o código de cadastro continua como antes
                    creation_date_str = creation_date_add.strftime('%Y-%m-%d')
                    try:
                        survey_id = add_survey_metadata(
                            research_name=research_name_add.strip(),
                            creation_date=creation_date_str,
                            api_link=api_link_limpo,
                            expected_total=expected_total_add)
                        if survey_id:
                            st.success(
                                f"Pesquisa '{research_name_add}' cadastrada com sucesso! ID: {survey_id}"
                            )
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(
                                "Não foi possível cadastrar a pesquisa. Verifique os logs."
                            )
                    except Exception as e:
                        st.error(f"Erro inesperado ao cadastrar pesquisa: {e}")

# --- Seção para Editar Pesquisa ---
with st.expander("✏️ Editar Pesquisa Existente", expanded=False):
    # (O código para Editar Pesquisa continua o mesmo, sem alterações)
    surveys_to_edit_df = get_all_surveys()
    if surveys_to_edit_df.empty:
        st.info(
            "Nenhuma pesquisa para editar. Por favor, adicione uma primeiro.")
    else:
        edit_survey_options = [
            f"{row['research_name']} (ID: {row['survey_id']})"
            for index, row in surveys_to_edit_df.iterrows()
        ]
        edit_survey_options.insert(0, "Selecione uma pesquisa para editar...")
        selected_edit_option = st.selectbox(
            "Escolha a pesquisa que deseja editar:",
            options=edit_survey_options,
            index=0,
            key="edit_select_box")
        if selected_edit_option != "Selecione uma pesquisa para editar...":
            selected_edit_survey_id = int(
                selected_edit_option.split('(ID: ')[1][:-1])
            current_survey_data = surveys_to_edit_df[
                surveys_to_edit_df['survey_id'] ==
                selected_edit_survey_id].iloc[0]
            st.markdown("---")
            st.write(
                f"Editando pesquisa: **{current_survey_data['research_name']}** (ID: {current_survey_data['survey_id']})"
            )
            with st.form("edit_survey_form"):
                edited_research_name = st.text_input(
                    "Nome da Pesquisa",
                    value=current_survey_data['research_name'])
                current_creation_date = datetime.datetime.strptime(
                    str(current_survey_data['creation_date']),
                    '%Y-%m-%d').date()
                edited_creation_date = st.date_input(
                    "Data de Criação", value=current_creation_date)
                edited_api_link = st.text_input(
                    "Link da API", value=current_survey_data['api_link'])
                edited_expected_total = st.number_input(
                    "Total Esperado de Respondentes (Opcional)",
                    min_value=0,
                    value=int(current_survey_data['expected_total'] or 0))
                update_button = st.form_submit_button("Atualizar Pesquisa")
                if update_button:
                    if not edited_research_name or not edited_api_link:
                        st.warning(
                            "Por favor, preencha o Nome da Pesquisa e o Link da API."
                        )
                    else:
                        edited_creation_date_str = edited_creation_date.strftime(
                            '%Y-%m-%d')
                        if update_survey_metadata(selected_edit_survey_id,
                                                  edited_research_name.strip(),
                                                  edited_creation_date_str,
                                                  edited_api_link.strip(),
                                                  edited_expected_total):
                            st.success(
                                f"Pesquisa '{edited_research_name}' (ID: {selected_edit_survey_id}) atualizada com sucesso!"
                            )
                            st.rerun()
                        else:
                            st.error("Não foi possível atualizar a pesquisa.")

# --- Seção para Excluir Pesquisa ---
with st.expander("🗑️ Excluir Pesquisa", expanded=False):
    # (O código para Excluir Pesquisa continua o mesmo, sem alterações)
    surveys_to_delete_df = get_all_surveys()
    if surveys_to_delete_df.empty:
        st.info("Nenhuma pesquisa para excluir.")
    else:
        delete_survey_options = [
            f"{row['research_name']} (ID: {row['survey_id']})"
            for index, row in surveys_to_delete_df.iterrows()
        ]
        delete_survey_options.insert(0,
                                     "Selecione uma pesquisa para excluir...")
        selected_delete_option = st.selectbox(
            "Escolha a pesquisa que deseja excluir:",
            options=delete_survey_options,
            index=0,
            key="delete_select_box")
        if selected_delete_option != "Selecione uma pesquisa para excluir...":
            selected_delete_survey_id = int(
                selected_delete_option.split('(ID: ')[1][:-1])
            st.warning(
                f"ATENÇÃO: Você está prestes a excluir a pesquisa: **{selected_delete_option.split(' (ID:')[0]}**. "
                f"Esta ação é **IRREVERSÍVEL** e excluirá permanentemente todos os dados de respondentes, "
                f"consolidados e de análise associados a ela.")
            if st.button(
                    f"Confirmar Exclusão da Pesquisa (ID: {selected_delete_survey_id})"
            ):
                if delete_survey(selected_delete_survey_id):
                    st.success(
                        f"Pesquisa (ID: {selected_delete_survey_id}) excluída com sucesso!"
                    )
                    st.rerun()
                else:
                    st.error(
                        "Não foi possível excluir. Verifique se há respondentes associados."
                    )

# --- Visualizar Pesquisas Cadastradas ---
st.subheader("Pesquisas Atualmente Cadastradas")
total, first_date, last_date = get_survey_summary_stats()
if total > 0:
    st.markdown(f"**Total de Pesquisas Cadastradas:** `{total}`")
else:
    st.info("Nenhuma pesquisa encontrada no banco de dados ainda.")

surveys_df = get_all_surveys()
if not surveys_df.empty:
    st.dataframe(surveys_df, use_container_width=True)

# --- Seção de Atualização Manual de Dados ---
st.markdown("---")
st.header("🔄 Atualização de Dados de Pesquisas")
st.markdown(
    "Clique no botão abaixo para buscar novos dados das APIs e atualizar a base consolidada."
)

update_limit = None  # Mude para um número (ex: 5) para testar, ou None para rodar tudo.

if st.button("Atualizar Todos os Dados das APIs"):
    processed_surveys_summary = []
    overall_process_success = True
    new_respondents_added_total = 0

    all_surveys_for_update = get_updatable_surveys()
    if all_surveys_for_update.empty:
        st.info(
            "Nenhuma pesquisa em campo para atualizar (todas as ativas já atingiram 99% ou mais da coleta)."
        )

    if all_surveys_for_update.empty:
        st.warning("Nenhuma pesquisa cadastrada para atualização.")
    else:
        # Lógica de limite de atualização corrigida
        if update_limit is not None and update_limit > 0:
            all_surveys_for_update = all_surveys_for_update.head(update_limit)

        total_surveys_to_process = len(all_surveys_for_update)
        progress_bar = st.progress(0, text="Iniciando atualização...")
        status_container = st.empty()

        # Loop principal de atualização
        for i, (index, row) in enumerate(all_surveys_for_update.iterrows()):
            survey_id = int(row['survey_id'])
            research_name = row['research_name']
            api_link = row['api_link']
            expected_total = int(row['expected_total'] or 0)

            # Atualiza a barra de progresso
            progress_text = f"Processando: {research_name} ({i + 1}/{total_surveys_to_process})"
            progress_bar.progress((i + 1) / total_surveys_to_process,
                                  text=progress_text)

            # Prepara o dicionário para o relatório final
            survey_summary_data = {
                "Pesquisa": research_name,
                "Status": "Verificando...",
                "Coletas Pré-Atualização": 0,
                "Coletas Pós-Atualização": 0,
                "% Concluído": "N/A",
                "Colunas Identificadas": 0
            }

            pre_update_count = get_respondent_count(survey_id)
            survey_summary_data["Coletas Pré-Atualização"] = pre_update_count
            survey_summary_data["Coletas Pós-Atualização"] = pre_update_count

            raw_data_list = fetch_data_from_api(api_link)

            if raw_data_list is not None:
                api_respondent_count = len(raw_data_list)
                if api_respondent_count > pre_update_count:
                    status_container.info(
                        f"Detectados {api_respondent_count - pre_update_count} novos registros para '{research_name}'. Processando..."
                    )
                    mapped_data_list, mapped_codes = map_api_columns_to_target_codes(
                        raw_data_list)
                    survey_summary_data["Colunas Identificadas"] = len(
                        mapped_codes)

                    if mapped_data_list:
                        success, num_added, warn_msg = store_respondent_data(
                            survey_id, mapped_data_list)

                        if success:
                            survey_summary_data[
                                "Status"] = f"✅ Atualizada ({num_added} novas)"
                            survey_summary_data[
                                "Coletas Pós-Atualização"] = pre_update_count + num_added
                            new_respondents_added_total += num_added

                            # --- INÍCIO DA NOVA LÓGICA DA PIPELINE ---
                            with st.spinner(
                                    f"Processando pipeline para '{research_name}'..."
                            ):
                                # 1. Consolidação (o que já tínhamos)
                                st.write(f"  - Consolidando dados brutos...")
                                consol_success, consol_msg = consolidate_survey_data(
                                    survey_id)
                                if not consol_success:
                                    st.warning(
                                        f"  - ⚠️ Aviso na consolidação: {consol_msg}"
                                    )
                                    continue  # Pula para a próxima pesquisa se a consolidação falhar

                                # 2. Transformação (nova etapa)
                                st.write(
                                    f"  - Padronizando e enriquecendo dados..."
                                )
                                # Busca os dados recém-consolidados para esta pesquisa
                                long_df = get_consolidated_data_for_surveys(
                                    [survey_id])
                                surveys_df_info = get_all_surveys(
                                )  # Pega metadados para o processo
                                # Executa a nossa função orquestradora
                                analytics_df = process_and_standardize_data(
                                    long_df, surveys_df_info)

                                # 3. Carga Final (nova etapa)
                                st.write(
                                    f"  - Salvando na tabela de análise...")
                                save_success, save_msg = save_analytics_data(
                                    analytics_df)
                                if not save_success:
                                    st.warning(
                                        f"  - ⚠️ Aviso na carga final: {save_msg}"
                                    )
                            # --- FIM DA NOVA LÓGICA DA PIPELINE ---

                        else:
                            overall_process_success = False
                            survey_summary_data[
                                "Status"] = f"❌ Falha ao Salvar ({warn_msg or 'Erro desconhecido'})"
                else:
                    survey_summary_data["Status"] = "ℹ️ Sem Novos Dados"
            else:
                overall_process_success = False
                survey_summary_data["Status"] = "❌ Falha na API"

            # --- ATUALIZAÇÃO DAS ESTATÍSTICAS NO BANCO ---
            # Este bloco é executado para todas as pesquisas no loop, garantindo que os totais estejam sempre corretos.
            post_update_count = survey_summary_data["Coletas Pós-Atualização"]
            update_survey_stats(survey_id, post_update_count, expected_total)

            if expected_total > 0:
                percentage = (post_update_count / expected_total) * 100
                survey_summary_data["% Concluído"] = f"{round(percentage)}%"

            processed_surveys_summary.append(survey_summary_data)

        # Limpeza da interface
        progress_bar.empty()
        status_container.empty()

        # Exibição do resumo final
        st.markdown("---")
        st.subheader("📊 Resumo da Atualização")
        summary_df = pd.DataFrame(processed_surveys_summary)
        st.dataframe(summary_df, use_container_width=True)

        st.markdown("---")
        st.markdown(
            f"**Total de Novos Respondentes Adicionados nesta rodada:** `{new_respondents_added_total}`"
        )

        if overall_process_success:
            st.success("✅ Processo de atualização de dados concluído!")
            if new_respondents_added_total > 0:
                st.balloons()
        else:
            st.error(
                "❌ Processo concluído com algumas falhas. Verifique a tabela de status acima."
            )
