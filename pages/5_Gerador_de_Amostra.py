# pages/5_Gerador_de_Amostra.py

import streamlit as st
import pandas as pd
import numpy as np
import itertools
import math
from src.database import get_analytics_data, get_all_consolidated_data
from src.data_processing import map_renda_to_macro_faixa

st.set_page_config(layout="wide", page_title="Gerador de Amostra")
st.logo("assets/logoBrain.png")


# --- Funções de Carregamento e Auxiliares ---
@st.cache_data(ttl=3600)
def load_base_data():
    df = get_analytics_data()
    if not df.empty:
        if 'renda_faixa_padronizada' in df.columns:
            df['renda_macro_faixa'] = df['renda_faixa_padronizada'].apply(
                map_renda_to_macro_faixa)
        if 'data_pesquisa' in df.columns:
            df['data_pesquisa'] = pd.to_datetime(df['data_pesquisa'],
                                                 errors='coerce')
    return df


@st.cache_data
def convert_df_to_csv(df_to_convert):
    return df_to_convert.to_csv(index=False).encode('utf-8')


# --- Interface Principal ---
st.title("🔬 Gerador e Planejador de Amostra")
st.markdown(
    "Use esta ferramenta para analisar a viabilidade, gerar um plano de coleta, auditar e extrair a amostra final."
)

df_analytics = load_base_data()

if df_analytics.empty:
    st.error(
        "A tabela de análise está vazia. Execute a pipeline na página de Manutenção."
    )
    st.stop()
required_cols = [
    'research_name', 'regiao', 'localidade', 'renda_macro_faixa',
    'idade_numerica', 'data_pesquisa', 'genero', 'faixa_etaria',
    'intencao_compra_padronizada', 'respondent_id', 'survey_id'
]
missing_cols = [
    col for col in required_cols if col not in df_analytics.columns
]
if missing_cols:
    st.error(
        f"Erro Crítico: Sua tabela de análise está sem as seguintes colunas essenciais: `{', '.join(missing_cols)}`. Por favor, vá para a página 'Manutenção e Admin' e execute a 'Pipeline de Transformação Completa'."
    )
    st.stop()

st.markdown("---")
st.header("1. Defina sua Amostra Ideal")
with st.container(border=True):
    # (O código dos parâmetros, como sliders e inputs, continua o mesmo)
    st.subheader("Filtros de Base (Prioridade 1 e 2)")
    col_f1, col_f2 = st.columns(2)
    df_analytics_dates = df_analytics.dropna(subset=['data_pesquisa'])
    if not df_analytics_dates.empty:
        min_date = df_analytics_dates['data_pesquisa'].min().date()
        max_date = df_analytics_dates['data_pesquisa'].max().date()
        start_date, end_date = col_f1.date_input("Período de coleta:",
                                                 value=(min_date, max_date),
                                                 min_value=min_date,
                                                 max_value=max_date)
    else:
        start_date, end_date = None, None
        col_f1.warning("Não há dados de data para filtrar.")
    idade_range = col_f2.slider("Faixa Etária desejada:", 18, 100, (21, 71))
    st.subheader("Ponderação da Amostra (%)")
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        st.write("**Região**")
        regiao_pesos = {
            'Sudeste': st.slider("Região Sudeste (%)", 0, 100, 40, 5),
            'Nordeste': st.slider("Nordeste (%)", 0, 100, 25, 5),
            'Sul': st.slider("Sul (%)", 0, 100, 20, 5),
            'Centro-Oeste': st.slider("Centro-Oeste (%)", 0, 100, 10, 5),
            'Norte': st.slider("Norte (%)", 0, 100, 5, 5)
        }
        soma_regiao = sum(regiao_pesos.values())
        if soma_regiao == 100: st.success(f"Total Região: {soma_regiao}%")
        else: st.error(f"Total Região: {soma_regiao}% (deve ser 100%)")
    with col_p2:
        st.write("**Faixa de Renda (R$ mil)**")
        renda_faixas_macro = {
            "1. Menor que R$ 2,5 mil":
            st.slider("Menor que 2.5k (%)", 0, 100, 0, 5),
            "2. R$ 2,5 a R$ 5 mil":
            st.slider("2.5k - 5k (%)", 0, 100, 30, 5),
            "3. R$ 5 a R$ 10 mil":
            st.slider("5k - 10k (%)", 0, 100, 30, 5),
            "4. R$ 10 a R$ 20 mil":
            st.slider("10k - 20k (%)", 0, 100, 20, 5),
            "5. Acima de R$ 20 mil":
            st.slider("20k+ (%)", 0, 100, 20, 5)
        }
        soma_renda = sum(renda_faixas_macro.values())
        if soma_renda == 100: st.success(f"Total Renda: {soma_renda}%")
        else: st.error(f"Total Renda: {soma_renda}% (deve ser 100%)")
    with col_p3:
        st.write("**Localidade**")
        capital_pct = st.slider("Capital (%)", 0, 100, 60, 5)
        localidade_pesos = {
            'Capital': capital_pct,
            'Interior': 100 - capital_pct
        }
    st.subheader("Tamanho da Amostra Final")
    sample_size = st.number_input("Quantidade de Respondentes Desejada", 100,
                                  10000, 1200)
    parametros_validos = (abs(soma_regiao - 100)
                          < 0.1) and (abs(soma_renda - 100) < 0.1)
    if not parametros_validos:
        st.warning("Ajuste as porcentagens para que a soma seja 100%.")
    if 'analysis_report' not in st.session_state:
        st.session_state.analysis_report = None

    if st.button("🔍 Analisar Viabilidade e Gerar Amostras",
                 disabled=not parametros_validos):
        # (A lógica de geração das amostras dentro do botão continua a mesma)
        with st.spinner("Analisando e gerando amostras..."):
            df_base_filtrada = pd.DataFrame()
            if start_date and end_date:
                df_base_filtrada = df_analytics[
                    (df_analytics['data_pesquisa'].dt.date >= start_date)
                    & (df_analytics['data_pesquisa'].dt.date <= end_date) &
                    (df_analytics['idade_numerica'] >= idade_range[0]) &
                    (df_analytics['idade_numerica'] <= idade_range[1])].copy()
            if df_base_filtrada.empty:
                st.warning("Nenhum dado encontrado para os filtros de base.")
                st.session_state.analysis_report = None
            else:
                analysis_results = []
                for param_name, (col_name, weights) in {
                        'Região': ('regiao', regiao_pesos),
                        'Faixa de Renda':
                    ('renda_macro_faixa', renda_faixas_macro),
                        'Localidade': ('localidade', localidade_pesos)
                }.items():
                    for category, pct in weights.items():
                        target_n = int(sample_size * (pct / 100.0))
                        available_n = len(df_base_filtrada[
                            df_base_filtrada[col_name] == category])
                        analysis_results.append({
                            "Parâmetro": param_name,
                            "Categoria": category,
                            "N Desejado": target_n,
                            "N Disponível": available_n
                        })
                report_df = pd.DataFrame(analysis_results)
                n_solicitado = min(sample_size, len(df_base_filtrada))
                strata_combinations = list(
                    itertools.product(regiao_pesos.keys(),
                                      renda_faixas_macro.keys(),
                                      localidade_pesos.keys()))
                strata_plan = []
                for combo in strata_combinations:
                    target_pct = (regiao_pesos[combo[0]] / 100) * (
                        renda_faixas_macro[combo[1]] /
                        100) * (localidade_pesos[combo[2]] / 100)
                    mask = (df_base_filtrada['regiao'] == combo[0]) & (
                        df_base_filtrada['renda_macro_faixa'] == combo[1]) & (
                            df_base_filtrada['localidade'] == combo[2])
                    available_n = mask.sum()
                    strata_plan.append({
                        "combo":
                        combo,
                        "target_n":
                        target_pct * n_solicitado,
                        "available_n":
                        available_n,
                        "ratio":
                        available_n /
                        (target_pct * n_solicitado) if target_pct > 0 else 1.0,
                        "mask":
                        mask
                    })
                sampled_indices_forced = set()
                for plan in strata_plan:
                    if plan['target_n'] > 0:
                        take_n = min(int(round(plan['target_n'])),
                                     plan['available_n'])
                        if take_n > 0:
                            sampled_indices_forced.update(
                                np.random.choice(
                                    df_base_filtrada[plan['mask']].index,
                                    take_n,
                                    replace=False))
                shortfall = n_solicitado - len(sampled_indices_forced)
                if shortfall > 0:
                    remaining_indices = df_base_filtrada.index.difference(
                        sampled_indices_forced)
                    n_to_fill = min(shortfall, len(remaining_indices))
                    if n_to_fill > 0:
                        sampled_indices_forced.update(
                            np.random.choice(remaining_indices,
                                             n_to_fill,
                                             replace=False))
                amostra_final_df = df_base_filtrada.loc[list(
                    sampled_indices_forced)].copy()
                min_ratio = min(
                    [s['ratio']
                     for s in strata_plan if s['target_n'] > 0] + [1.0])
                sampled_indices_prop = []
                for plan in strata_plan:
                    n_to_sample = int(round(plan['target_n'] * min_ratio))
                    if n_to_sample > 0:
                        sampled_indices_prop.extend(
                            df_base_filtrada[plan['mask']].sample(
                                n=n_to_sample, random_state=42).index.tolist())
                amostra_proporcional_df = df_base_filtrada.loc[
                    sampled_indices_prop].copy()
                st.session_state.analysis_report = {
                    "amostra_df": amostra_final_df,
                    "amostra_proporcional_df": amostra_proporcional_df,
                    "report_df": report_df,
                    "strata_plan": strata_plan,
                    "requested_size": sample_size
                }
        st.rerun()

# --- Exibição dos Relatórios ---
if 'analysis_report' in st.session_state and st.session_state.analysis_report:
    report_data = st.session_state.analysis_report
    amostra_final_df = report_data['amostra_df']
    amostra_proporcional_df = report_data['amostra_proporcional_df']
    report_df = report_data['report_df']
    strata_plan = report_data['strata_plan']
    final_size = len(amostra_final_df)

    st.markdown("---")
    st.header("2. Resultados da Análise e Composição da Amostra")
    st.info(
        f"Relatório gerado com base na amostra de **{final_size}** respondentes."
    )

    # --- RELATÓRIO DE DESVIOS (COM EXPANDER DE EXPLICAÇÃO) ---
    st.subheader("Relatório de Desvios vs. Plano Ideal")

    def get_realizado(parametro, categoria):
        mapa_colunas = {
            'Região': 'regiao',
            'Faixa de Renda': 'renda_macro_faixa',
            'Localidade': 'localidade'
        }
        coluna_df = mapa_colunas.get(parametro)
        if coluna_df: return (amostra_final_df[coluna_df] == categoria).sum()
        return 0

    report_df['N Realizado'] = report_df.apply(
        lambda row: get_realizado(row['Parâmetro'], row['Categoria']), axis=1)
    report_df['Desvio'] = report_df['N Realizado'] - report_df['N Desejado']
    deficit_df = report_df[report_df['Desvio'] < 0]
    if not deficit_df.empty:
        st.warning(
            "Atenção: A base de dados não suporta o plano ideal. A amostra gerada preencheu as lacunas com perfis excedentes."
        )
    else:
        st.success(
            "🎉 Viabilidade Confirmada! A amostra gerada corresponde ao plano ideal."
        )

    def style_desvio(row):
        color = 'background-color: #FFD2D2' if row.Desvio < 0 else 'background-color: #D4EDDA' if row.Desvio > 0 else ''
        return [color] * len(row)

    df_to_display = report_df[[
        'Parâmetro', 'Categoria', 'N Desejado', 'N Disponível', 'N Realizado',
        'Desvio'
    ]]
    st.dataframe(df_to_display.style.apply(style_desvio, axis=1),
                 use_container_width=True,
                 hide_index=True)

    # --- NOVO: Explicação das colunas do relatório ---
    with st.expander("ⓘ Entenda as Colunas do Relatório de Desvios"):
        st.markdown("""
        - **Parâmetro:** A dimensão de análise (ex: Região, Faixa de Renda).
        - **Categoria:** O grupo específico dentro do parâmetro (ex: Nordeste, 2.5k - 5k).
        - **N Desejado:** O número de respondentes que este perfil deveria ter, de acordo com o tamanho da amostra e os pesos que você definiu.
        - **N Disponível:** O número total de respondentes deste perfil que existem na base de dados (após aplicar os filtros de base).
        - **N Realizado:** O número de respondentes deste perfil que foram efetivamente incluídos na amostra final gerada.
        - **Desvio:** A diferença entre o "N Realizado" e o "N Desejado". Um valor negativo (vermelho) indica que faltaram respondentes deste perfil; um valor positivo (verde) indica que foram usados mais respondentes deste perfil para compensar lacunas em outros.
        """)

    # --- PAINEL DE AÇÃO PARA COLETA (COM TOTAL) ---
    st.subheader("Painel de Ação para Coleta")
    coletas_necessarias = [{'Região': p['combo'][0], 'Faixa de Renda': p['combo'][1], 'Localidade': p['combo'][2], 'Coletas Faltantes': math.ceil(p['target_n'] - p['available_n'])} for p in strata_plan if (p['target_n'] - p['available_n']) > 0]

    if coletas_necessarias:
        plano_coleta_df = pd.DataFrame(coletas_necessarias)
        total_geral_faltante = plano_coleta_df['Coletas Faltantes'].sum()

        st.metric(label="Total Geral de Coletas Adicionais Necessárias", value=f"{total_geral_faltante:.0f}")
        st.markdown("Use as abas abaixo para analisar onde os esforços de coleta são mais necessários.")

        # Cria as abas para cada localidade + visão geral
        tab_capital, tab_interior, tab_geral = st.tabs(["🎯 Prioridades na Capital", "🎯 Prioridades no Interior", "Visão Geral Consolidada"])

        with tab_capital:
            df_capital = plano_coleta_df[plano_coleta_df['Localidade'] == 'Capital']
            if not df_capital.empty:
                total_capital = df_capital['Coletas Faltantes'].sum()
                st.info(f"Total de coletas faltantes em Capitais: **{total_capital:.0f}**")

                matriz_capital = pd.pivot_table(df_capital, values='Coletas Faltantes', index='Faixa de Renda', columns='Região', aggfunc='sum', fill_value=0)
                st.dataframe(matriz_capital.style.background_gradient(cmap='Reds').format("{:.0f}"), use_container_width=True)
            else:
                st.success("Nenhuma coleta adicional necessária nas capitais para este plano.")

        with tab_interior:
            df_interior = plano_coleta_df[plano_coleta_df['Localidade'] == 'Interior']
            if not df_interior.empty:
                total_interior = df_interior['Coletas Faltantes'].sum()
                st.info(f"Total de coletas faltantes no Interior: **{total_interior:.0f}**")

                matriz_interior = pd.pivot_table(df_interior, values='Coletas Faltantes', index='Faixa de Renda', columns='Região', aggfunc='sum', fill_value=0)
                st.dataframe(matriz_interior.style.background_gradient(cmap='Reds').format("{:.0f}"), use_container_width=True)
            else:
                st.success("Nenhuma coleta adicional necessária no interior para este plano.")

        with tab_geral:
            st.markdown("Resumos e Matriz consolidada (Capital + Interior).")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("###### Por Região")
                st.dataframe(plano_coleta_df.groupby('Região')['Coletas Faltantes'].sum().sort_values(ascending=False))
            with col2:
                st.markdown("###### Por Faixa de Renda")
                st.dataframe(plano_coleta_df.groupby('Faixa de Renda')['Coletas Faltantes'].sum().sort_values(ascending=False))

            st.markdown("###### Matriz de Prioridades Consolidada")
            matriz_prioridade = pd.pivot_table(plano_coleta_df, values='Coletas Faltantes', index='Faixa de Renda', columns='Região', aggfunc='sum', fill_value=0)
            st.dataframe(matriz_prioridade.style.background_gradient(cmap='Reds').format("{:.0f}"), use_container_width=True)
    else:
        st.success("🎉 Plano de Coleta Concluído! A base de dados atual já possui todos os perfis necessários para a amostra ideal.")


    # --- O restante do código (expanders de Perfil e Download) continua o mesmo ---
    with st.expander("Ver Perfil e Auditoria da Amostra Gerada"):
        st.subheader("Perfil da Amostra Gerada (N Forçado)")
        if not amostra_final_df.empty:
            cols_to_profile = {
                'Gênero': 'genero',
                'Faixa Etária': 'faixa_etaria',
                'Região': 'regiao',
                'Faixa de Renda': 'renda_macro_faixa',
                'Localidade': 'localidade',
                'Intenção de Compra': 'intencao_compra_padronizada'
            }
            profile_cols = st.columns(len(cols_to_profile))
            for i, (title, col_name) in enumerate(cols_to_profile.items()):
                with profile_cols[i]:
                    st.write(f"**{title}**")
                    counts = amostra_final_df[col_name].value_counts(
                        normalize=True).mul(100)
                    st.dataframe(
                        counts.to_frame(name='%').style.format('{:.1f}%'))

        st.subheader("Auditoria de Origem da Amostra")
        if not amostra_final_df.empty:
            source_summary = amostra_final_df.groupby(
                ['research_name', 'regiao',
                 'localidade']).size().reset_index(name='Nº de Respondentes')
            st.dataframe(source_summary.sort_values(by='Nº de Respondentes',
                                                    ascending=False),
                         use_container_width=True,
                         hide_index=True)
        else:
            st.info("Nenhuma amostra foi gerada para exibir a auditoria.")

    with st.expander("Extrair Arquivos de Amostra (.csv)"):
        cols_para_merge = [
            'respondent_id', 'survey_id', 'genero', 'faixa_etaria', 'regiao',
            'localidade', 'renda_macro_faixa', 'intencao_compra_padronizada',
            'research_name', 'data_pesquisa'
        ]
        st.subheader(
            f"Amostra com N Solicitado ({len(amostra_final_df)} respondentes)")
        if not amostra_final_df.empty:
            with st.spinner("Preparando arquivo..."):
                df_tratado_final = amostra_final_df[[
                    col for col in cols_para_merge
                    if col in amostra_final_df.columns
                ]]
                ids_para_buscar = df_tratado_final['respondent_id'].unique(
                ).tolist()
                full_consolidated_df = get_all_consolidated_data()
                if not full_consolidated_df.empty:
                    output_long_df = full_consolidated_df[full_consolidated_df[
                        'respondent_id'].isin(ids_para_buscar)]
                    output_wide_df = output_long_df.pivot_table(
                        index=['respondent_id', 'survey_id'],
                        columns='question_code',
                        values='answer_value',
                        aggfunc='first').reset_index()
                    df_final_para_download = pd.merge(
                        output_wide_df,
                        df_tratado_final.drop_duplicates(
                            subset=['respondent_id', 'survey_id']),
                        on=['respondent_id', 'survey_id'],
                        how='left')
                    st.download_button(
                        label=
                        f"📥 Baixar Amostra de {len(amostra_final_df)} Respondentes",
                        data=convert_df_to_csv(df_final_para_download),
                        file_name=
                        f'amostra_forcada_{len(amostra_final_df)}.csv',
                        mime='text/csv',
                        key='download_forced')

        st.markdown("---")

        st.subheader(
            f"Amostra Proporcional Ideal ({len(amostra_proporcional_df)} respondentes)"
        )
        if amostra_proporcional_df.empty:
            st.warning("Amostra Proporcional não pôde ser gerada.")
            st.markdown(
                "Isso ocorre porque um ou mais perfis essenciais para o plano **não possuem nenhum respondente** na base de dados (disponibilidade zero)."
            )
            perfis_criticos = [{
                'Região': p['combo'][0],
                'Faixa de Renda': p['combo'][1],
                'Localidade': p['combo'][2]
            } for p in strata_plan
                               if p['target_n'] > 0 and p['available_n'] == 0]
            if perfis_criticos:
                perfis_criticos_df = pd.DataFrame(perfis_criticos)
                st.markdown("###### Perfis 'Gargalo' (Capital vs Interior)")
                counts_localidade = perfis_criticos_df[
                    'Localidade'].value_counts()
                c1, c2 = st.columns(2)
                c1.metric("Gargalos em Capital",
                          counts_localidade.get('Capital', 0))
                c2.metric("Gargalos em Interior",
                          counts_localidade.get('Interior', 0))
                st.markdown("###### Matriz de Gargalos (Região vs. Renda)")
                matriz_gargalos = pd.pivot_table(perfis_criticos_df,
                                                 index='Faixa de Renda',
                                                 columns='Região',
                                                 aggfunc=len,
                                                 fill_value=0)
                st.dataframe(matriz_gargalos.style.background_gradient(
                    cmap='Reds').format("{:.0f}"),
                             use_container_width=True)
        else:
            with st.spinner("Preparando arquivo..."):
                df_tratado_prop = amostra_proporcional_df[[
                    col for col in cols_para_merge
                    if col in amostra_proporcional_df.columns
                ]]
                ids_para_buscar_prop = df_tratado_prop['respondent_id'].unique(
                ).tolist()
                full_consolidated_df_prop = get_all_consolidated_data()
                if not full_consolidated_df_prop.empty:
                    output_long_df_prop = full_consolidated_df_prop[
                        full_consolidated_df_prop['respondent_id'].isin(
                            ids_para_buscar_prop)]
                    output_wide_df_prop = output_long_df_prop.pivot_table(
                        index=['respondent_id', 'survey_id'],
                        columns='question_code',
                        values='answer_value',
                        aggfunc='first').reset_index()
                    df_final_para_download_prop = pd.merge(
                        output_wide_df_prop,
                        df_tratado_prop.drop_duplicates(
                            subset=['respondent_id', 'survey_id']),
                        on=['respondent_id', 'survey_id'],
                        how='left')
                    st.download_button(
                        label=
                        f"📥 Baixar Amostra Proporcional de {len(amostra_proporcional_df)}",
                        data=convert_df_to_csv(df_final_para_download_prop),
                        file_name=
                        f'amostra_proporcional_{len(amostra_proporcional_df)}.csv',
                        mime='text/csv',
                        key='download_proportional')
