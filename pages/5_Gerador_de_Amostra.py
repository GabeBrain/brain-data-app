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
        periodo_coleta = col_f1.date_input("Período de coleta:",
                                           value=(min_date, max_date),
                                           min_value=min_date,
                                           max_value=max_date)
        if isinstance(periodo_coleta, (tuple, list)):
            if len(periodo_coleta) == 2:
                start_date, end_date = periodo_coleta
            elif len(periodo_coleta) == 1:
                start_date = end_date = periodo_coleta[0]
            else:
                start_date, end_date = min_date, max_date
        else:
            start_date = end_date = periodo_coleta
    else:
        start_date, end_date = None, None
        col_f1.warning("Não há dados de data para filtrar.")
    idade_range = col_f2.slider("Faixa Etária desejada:", 18, 100, (21, 71))
    
    # --- NOVA SEÇÃO: FILTROS DE PROJETO ---
    st.subheader("Filtros de Projeto (Prioridade 0)")
    lista_projetos = sorted(df_analytics['research_name'].unique())
    
    col_p0_1, col_p0_2 = st.columns(2)
    with col_p0_1:
        projetos_incluir = st.multiselect(
            "Garantir Inclusão (Amostra-Core):",
            options=lista_projetos,
            default=[],
            help="Respondentes destes projetos SERÃO incluídos, furando a hierarquia. O restante da amostra será construído ao redor deles."
        )
    with col_p0_2:
        projetos_excluir = st.multiselect(
            "Garantir Exclusão:",
            options=lista_projetos,
            default=[],
            help="Respondentes destes projetos NUNCA serão incluídos na amostra."
        )
    # --- FIM DA NOVA SEÇÃO ---
    projetos_incluir_set = set(projetos_incluir)
    projetos_excluir_set = set(projetos_excluir)
    conflitos_projetos = projetos_incluir_set.intersection(projetos_excluir_set)
    if conflitos_projetos:
        st.warning(f"Projetos selecionados tanto para Inclusao quanto para Exclusao: {', '.join(conflitos_projetos)}. Dando prioridade a Inclusao e removendo-os da exclusao.")
        projetos_excluir_set -= conflitos_projetos
    
    st.subheader("Ponderação da Amostra (%)")
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        st.write("**Região**")
        regiao_pesos = {
            'Sudeste': st.slider("Região Sudeste (%)", 0, 100, 30, 5),
            'Nordeste': st.slider("Nordeste (%)", 0, 100, 30, 5),
            'Sul': st.slider("Sul (%)", 0, 100, 25, 5),
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
        with st.spinner("Analisando e gerando amostra hierárquica..."):
            
            # --- Etapa 1: Filtragem Inicial (com Exclusao) ---
            mask_data = pd.Series(True, index=df_analytics.index)
            if start_date and end_date:
                mask_data = (
                    (df_analytics['data_pesquisa'].dt.date >= start_date) &
                    (df_analytics['data_pesquisa'].dt.date <= end_date))
            mask_idade = pd.Series(True, index=df_analytics.index)
            mask_idade = mask_idade & (
                (df_analytics['idade_numerica'] >= idade_range[0]) &
                (df_analytics['idade_numerica'] <= idade_range[1]))
            mask_excluir = (~df_analytics['research_name'].isin(projetos_excluir_set))
            core_mask = df_analytics['research_name'].isin(projetos_incluir_set)
            df_core_sample = df_analytics[core_mask]
            indices_core = set(df_core_sample.index)
            df_pool_base = df_analytics[mask_data & mask_idade & mask_excluir].copy()
            df_pool_para_amostra = df_pool_base.drop(indices_core, errors="ignore")
            df_para_relatorio = pd.concat([df_core_sample, df_pool_para_amostra])
            if df_para_relatorio.empty:
                st.warning("Nenhum dado encontrado apos aplicar filtros e prioridades de projeto.")
                st.session_state.analysis_report = None
            else:
                # --- Etapa 2: Analise de Viabilidade (sobre o pool filtrado) ---
                analysis_results = []
                for param_name, (col_name, weights) in {
                        'Região': ('regiao', regiao_pesos),
                        'Faixa de Renda': ('renda_macro_faixa', renda_faixas_macro),
                        'Localidade': ('localidade', localidade_pesos)
                }.items():
                    for category, pct in weights.items():
                        target_n = int(sample_size * (pct / 100.0))
                        available_n = len(df_para_relatorio[df_para_relatorio[col_name] == category])
                        analysis_results.append({
                            "Parâmetro": param_name,
                            "Categoria": category,
                            "N Desejado": target_n,
                            "N Disponível": available_n
                        })
                report_df = pd.DataFrame(analysis_results)

                # --- NOVA LÓGICA DE AMOSTRAGEM HIERÁRQUICA COM AMOSTRA-CORE ---

                
                n_total_necessario = sample_size
                n_core = len(indices_core)
                n_solicitado_hierarquico = max(0, n_total_necessario - n_core)

                indices_hierarquicos = set()

                if n_solicitado_hierarquico > 0 and not df_pool_para_amostra.empty:
                    # --- Etapa 5: Rodar Amostragem Hierárquica no Pool Restante ---
                    
                    # ESTÁGIO 5.1: Garantir cotas de RENDA primeiro (no pool)
                    df_restante_pool = df_pool_para_amostra.copy()

                    for renda, pct in renda_faixas_macro.items():
                        if pct > 0:
                            # Calcula o target para o N restante
                            target_n_renda = int(round(n_solicitado_hierarquico * (pct / 100.0)))
                            disponiveis_na_faixa = df_restante_pool[df_restante_pool['renda_macro_faixa'] == renda]
                            n_a_pegar = min(target_n_renda, len(disponiveis_na_faixa))

                            if n_a_pegar > 0:
                                sub_amostra_indices = set()
                                # Tenta balancear por Região/Localidade dentro da cota de renda
                                for regiao, pct_regiao in regiao_pesos.items():
                                    for local, pct_local in localidade_pesos.items():
                                        sub_target_n = int(round(n_a_pegar * (pct_regiao / 100) * (pct_local / 100)))
                                        sub_disponiveis = disponiveis_na_faixa[
                                            (disponiveis_na_faixa['regiao'] == regiao) &
                                            (disponiveis_na_faixa['localidade'] == local)
                                        ]
                                        sub_take_n = min(sub_target_n, len(sub_disponiveis))
                                        if sub_take_n > 0:
                                            selecionados = np.random.choice(sub_disponiveis.index, sub_take_n, replace=False)
                                            sub_amostra_indices.update(selecionados)
                                
                                # Preenche o restante para a cota de renda (shortfall interno)
                                sub_shortfall = n_a_pegar - len(sub_amostra_indices)
                                if sub_shortfall > 0:
                                    sub_restantes = disponiveis_na_faixa.index.difference(sub_amostra_indices)
                                    n_to_fill_sub = min(sub_shortfall, len(sub_restantes))
                                    if n_to_fill_sub > 0:
                                        sub_amostra_indices.update(np.random.choice(sub_restantes, n_to_fill_sub, replace=False))
                                
                                indices_hierarquicos.update(sub_amostra_indices)
                                df_restante_pool = df_restante_pool.drop(sub_amostra_indices) # Remove os já selecionados do pool

                    # ESTÁGIO 5.2: Preencher o shortfall GERAL (no pool)
                    shortfall_geral = n_solicitado_hierarquico - len(indices_hierarquicos)
                    if shortfall_geral > 0 and not df_restante_pool.empty:
                        n_to_fill_geral = min(shortfall_geral, len(df_restante_pool))
                        if n_to_fill_geral > 0:
                            indices_hierarquicos.update(
                                np.random.choice(df_restante_pool.index, n_to_fill_geral, replace=False)
                            )

                elif n_core >= n_total_necessario:
                    st.warning(f"A 'Amostra-Core' selecionada ({n_core} respondentes) ja atinge ou supera o N Solicitado ({n_total_necessario}). A amostra final contera apenas o grupo 'core'.")
                    # Se o core for maior, podemos truncar para o N exato
                    if n_core > n_total_necessario:
                        indices_core = set(np.random.choice(list(indices_core), n_total_necessario, replace=False))



                # --- Etapa 6: União da Amostra Final ---
                indices_finais = indices_core.union(indices_hierarquicos)
                amostra_final_df = df_para_relatorio.loc[list(indices_finais)].copy()
                
                # --- Lógica da Amostra Proporcional (não muda) ---
                # Ela roda sobre a base consolidada (core + pool filtrado) para o relat?rio de coleta
                strata_combinations = list(itertools.product(regiao_pesos.keys(), renda_faixas_macro.keys(), localidade_pesos.keys()))
                strata_plan = []
                n_base_proporcional = sample_size # Usamos o sample_size original para o plano ideal
                
                for combo in strata_combinations:
                    target_pct = (regiao_pesos[combo[0]] / 100) * (renda_faixas_macro[combo[1]] / 100) * (localidade_pesos[combo[2]] / 100)
                    mask = (df_para_relatorio['regiao'] == combo[0]) & \
                           (df_para_relatorio['renda_macro_faixa'] == combo[1]) & \
                           (df_para_relatorio['localidade'] == combo[2])
                    available_n = mask.sum()
                    strata_plan.append({
                        "combo": combo,
                        "target_n": target_pct * n_base_proporcional,
                        "available_n": available_n,
                        "ratio": available_n / (target_pct * n_base_proporcional) if target_pct > 0 else 1.0,
                        "mask": mask
                    })
                
                min_ratio = min([s['ratio'] for s in strata_plan if s['target_n'] > 0] + [1.0])
                sampled_indices_prop = []
                for plan in strata_plan:
                    n_to_sample = int(round(plan['target_n'] * min_ratio))
                    if n_to_sample > 0:
                        available_indices = df_para_relatorio[plan['mask']].index
                        n_to_sample = min(n_to_sample, len(available_indices)) # Garante que não tente pegar mais do que o disponível
                        sampled_indices_prop.extend(
                            np.random.choice(available_indices, n_to_sample, replace=False)
                        )
                amostra_proporcional_df = df_para_relatorio.loc[list(set(sampled_indices_prop))].copy()

                # Salva os resultados no estado da sessão
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
    coletas_necessarias = [{
        'Região':
        p['combo'][0],
        'Faixa de Renda':
        p['combo'][1],
        'Localidade':
        p['combo'][2],
        'Coletas Faltantes':
        math.ceil(p['target_n'] - p['available_n'])
    } for p in strata_plan if (p['target_n'] - p['available_n']) > 0]

    if coletas_necessarias:
        plano_coleta_df = pd.DataFrame(coletas_necessarias)
        total_geral_faltante = plano_coleta_df['Coletas Faltantes'].sum()

        st.metric(label="Total Geral de Coletas Adicionais Necessárias",
                  value=f"{total_geral_faltante:.0f}")
        st.markdown(
            "Use as abas abaixo para analisar onde os esforços de coleta são mais necessários."
        )

        # Cria as abas para cada localidade + visão geral
        tab_capital, tab_interior, tab_geral = st.tabs([
            "🎯 Prioridades na Capital", "🎯 Prioridades no Interior",
            "Visão Geral Consolidada"
        ])

        with tab_capital:
            df_capital = plano_coleta_df[plano_coleta_df['Localidade'] ==
                                         'Capital']
            if not df_capital.empty:
                total_capital = df_capital['Coletas Faltantes'].sum()
                st.info(
                    f"Total de coletas faltantes em Capitais: **{total_capital:.0f}**"
                )

                matriz_capital = pd.pivot_table(df_capital,
                                                values='Coletas Faltantes',
                                                index='Faixa de Renda',
                                                columns='Região',
                                                aggfunc='sum',
                                                fill_value=0)
                st.dataframe(matriz_capital.style.background_gradient(
                    cmap='Reds').format("{:.0f}"),
                             use_container_width=True)
            else:
                st.success(
                    "Nenhuma coleta adicional necessária nas capitais para este plano."
                )

        with tab_interior:
            df_interior = plano_coleta_df[plano_coleta_df['Localidade'] ==
                                          'Interior']
            if not df_interior.empty:
                total_interior = df_interior['Coletas Faltantes'].sum()
                st.info(
                    f"Total de coletas faltantes no Interior: **{total_interior:.0f}**"
                )

                matriz_interior = pd.pivot_table(df_interior,
                                                 values='Coletas Faltantes',
                                                 index='Faixa de Renda',
                                                 columns='Região',
                                                 aggfunc='sum',
                                                 fill_value=0)
                st.dataframe(matriz_interior.style.background_gradient(
                    cmap='Reds').format("{:.0f}"),
                             use_container_width=True)
            else:
                st.success(
                    "Nenhuma coleta adicional necessária no interior para este plano."
                )

        with tab_geral:
            st.markdown("Resumos e Matriz consolidada (Capital + Interior).")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("###### Por Região")
                st.dataframe(
                    plano_coleta_df.groupby('Região')
                    ['Coletas Faltantes'].sum().sort_values(ascending=False))
            with col2:
                st.markdown("###### Por Faixa de Renda")
                st.dataframe(
                    plano_coleta_df.groupby('Faixa de Renda')
                    ['Coletas Faltantes'].sum().sort_values(ascending=False))

            st.markdown("###### Matriz de Prioridades Consolidada")
            matriz_prioridade = pd.pivot_table(plano_coleta_df,
                                               values='Coletas Faltantes',
                                               index='Faixa de Renda',
                                               columns='Região',
                                               aggfunc='sum',
                                               fill_value=0)
            st.dataframe(matriz_prioridade.style.background_gradient(
                cmap='Reds').format("{:.0f}"),
                         use_container_width=True)
    else:
        st.success(
            "🎉 Plano de Coleta Concluído! A base de dados atual já possui todos os perfis necessários para a amostra ideal."
        )

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
