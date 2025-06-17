# pages/4_Dashboard_de_Análise.py

import streamlit as st
import pandas as pd
import plotly.express as px
import time
from src.database import get_analytics_data

st.set_page_config(layout="wide", page_title="Dashboard de Análise")
st.logo("assets/logoBrain.png")

st.title("💡 Dashboard de Análise de Respondentes")
st.markdown(
    "Use os filtros na barra lateral para explorar os dados dos respondentes de forma interativa."
)

# --- Botão para Limpar o Cache e Forçar a Atualização ---
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Atualizar Dados do Dashboard"):
    st.cache_data.clear()
    st.rerun()


# --- 1. Carregamento dos Dados ---
@st.cache_data(ttl=3600)
def load_data():
    """Carrega os dados da tabela de análise e os armazena em cache."""
    return get_analytics_data()


df = load_data()

if df.empty:
    st.warning(
        "A tabela de análise ('analytics_respondents') está vazia. Execute a pipeline na página de 'Manutenção e Admin' para populá-la."
    )
    st.stop()

# --- 2. Barra Lateral de Filtros ---
st.sidebar.header("Filtros do Dashboard")
regioes = sorted(df['regiao'].dropna().unique().tolist())
regiao_selecionada = st.sidebar.multiselect("Região",
                                            options=regioes,
                                            default=regioes)

geracoes = sorted(df['geracao'].dropna().unique().tolist())
geracao_selecionada = st.sidebar.multiselect("Geração",
                                             options=geracoes,
                                             default=geracoes)

# Lida com o caso de a coluna de renda ser nula para evitar erros
if df['renda_valor_estimado'].notna().any():
    min_renda, max_renda = int(df['renda_valor_estimado'].min()), int(
        df['renda_valor_estimado'].max())
    renda_selecionada = st.sidebar.slider("Faixa de Renda Estimada (R$)",
                                          min_value=min_renda,
                                          max_value=max_renda,
                                          value=(min_renda, max_renda))
else:
    # Se não houver dados de renda, desabilita o slider
    renda_selecionada = (0, 0)
    st.sidebar.slider("Faixa de Renda Estimada (R$)", 0, 0, disabled=True)

# --- 3. Lógica de Filtragem do DataFrame ---
df_filtrado = df[(df['regiao'].isin(regiao_selecionada))
                 & (df['geracao'].isin(geracao_selecionada)) &
                 (df['renda_valor_estimado'] >= renda_selecionada[0]) &
                 (df['renda_valor_estimado'] <= renda_selecionada[1])]

# --- 4. Renderização do Dashboard ---
st.markdown("---")

# KPIs
total_respondentes = len(df_filtrado)
renda_media = df_filtrado['renda_valor_estimado'].mean(
) if total_respondentes > 0 else 0
idade_media = df_filtrado['idade_numerica'].mean(
) if total_respondentes > 0 else 0

col1, col2, col3 = st.columns(3)
col1.metric("Total de Respondentes na Seleção", f"{total_respondentes:,}")
col2.metric("Renda Média Estimada", f"R$ {renda_media:,.2f}")
col3.metric("Idade Média", f"{idade_media:.1f} anos")

st.markdown("---")
st.header("Análise Exploratória Interativa")

opcoes_variaveis = [
    'geracao', 'faixa_etaria', 'regiao', 'localidade',
    'renda_faixa_padronizada', 'intencao_compra_padronizada',
    'tempo_intencao_padronizado', 'idade_numerica', 'renda_valor_estimado'
]

c1, c2 = st.columns(2)
variavel_principal = c1.selectbox(
    "Selecione a variável principal para análise:",
    options=opcoes_variaveis,
    index=2)
tipo_grafico = c2.selectbox("Selecione o tipo de gráfico:",
                            options=[
                                'Contagem (Barras)', 'Proporção (Pizza)',
                                'Distribuição (Histograma)',
                                '100% Empilhado (Ranking)',
                                'Série Temporal (Linha)'
                            ])

variavel_cor = None
if tipo_grafico in ['Contagem (Barras)', '100% Empilhado (Ranking)']:
    opcoes_cor = ["Nenhuma"] + [
        col for col in opcoes_variaveis if pd.api.types.is_string_dtype(
            df_filtrado[col]) and col != variavel_principal
    ]
    variavel_cor = st.selectbox("Agrupar por cor (opcional):",
                                options=opcoes_cor)
    if variavel_cor == "Nenhuma":
        variavel_cor = None

st.subheader(f"Visualização: {variavel_principal}")

if total_respondentes > 0:
    try:
        if tipo_grafico == 'Contagem (Barras)':
            df_plot = df_filtrado.sort_values(by=variavel_principal)
            fig = px.bar(df_plot,
                         x=variavel_principal,
                         color=variavel_cor,
                         title=f"Contagem por '{variavel_principal}'")
            st.plotly_chart(fig, use_container_width=True)

        elif tipo_grafico == 'Proporção (Pizza)':
            counts = df_filtrado[variavel_principal].value_counts()
            fig = px.pie(counts,
                         values=counts.values,
                         names=counts.index,
                         hole=.3,
                         title=f"Proporção por '{variavel_principal}'")
            st.plotly_chart(fig, use_container_width=True)

        elif tipo_grafico == 'Distribuição (Histograma)':
            if pd.api.types.is_numeric_dtype(df_filtrado[variavel_principal]):
                fig = px.histogram(
                    df_filtrado,
                    x=variavel_principal,
                    nbins=50,
                    title=f"Distribuição de '{variavel_principal}'")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(
                    f"Histogramas são adequados apenas para variáveis numéricas. '{variavel_principal}' não é numérica."
                )

        elif tipo_grafico == '100% Empilhado (Ranking)':
            if variavel_cor:
                cross_tab = pd.crosstab(df_filtrado[variavel_principal],
                                        df_filtrado[variavel_cor])
                cross_tab_pct = cross_tab.div(cross_tab.sum(axis=1),
                                              axis=0).apply(lambda x: x * 100)
                fig = px.bar(
                    cross_tab_pct,
                    orientation='h',
                    text_auto='.1f',
                    title=
                    f"Composição Percentual de '{variavel_cor}' por '{variavel_principal}'"
                )
                fig.update_layout(barmode='stack',
                                  yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(
                    "Para o gráfico '100% Empilhado', você precisa selecionar uma variável de 'Agrupar por cor'."
                )

        elif tipo_grafico == 'Série Temporal (Linha)':
            if 'data_pesquisa' in df_filtrado.columns and pd.to_datetime(df_filtrado['data_pesquisa'], errors='coerce').notna().any():
    
                # --- Controles Adicionais para Série Temporal ---
                st.markdown("##### Opções da Análise Temporal")
    
                col_ts1, col_ts2 = st.columns(2)
    
                # Seletor para o que será analisado no eixo Y
                metrica_ts = col_ts1.selectbox(
                    "Selecione a métrica para analisar no tempo:",
                    ["Contagem de Respostas", "Média de uma Coluna Numérica", "Distribuição de uma Categoria"]
                )
    
                # Seletor para o agrupamento do tempo
                agrupamento_temporal = col_ts2.selectbox(
                    "Agrupar dados por:",
                    ["Dia", "Semana", "Mês"],
                    index=2 # Padrão para Mês
                )
                map_agrupamento = {"Dia": "D", "Semana": "W", "Mês": "M"}
    
                # Converte a coluna de data, tratando possíveis erros
                df_ts = df_filtrado.copy()
                df_ts['data_pesquisa'] = pd.to_datetime(df_ts['data_pesquisa'], errors='coerce')
                df_ts.dropna(subset=['data_pesquisa'], inplace=True)
    
                # --- Lógica de Geração do Gráfico ---
                if metrica_ts == "Contagem de Respostas":
                    serie_temporal = df_ts.resample(map_agrupamento[agrupamento_temporal], on='data_pesquisa').size().reset_index(name='contagem')
                    fig = px.line(serie_temporal, x='data_pesquisa', y='contagem', title="Respostas ao Longo do Tempo")
                    st.plotly_chart(fig, use_container_width=True)
    
                elif metrica_ts == "Média de uma Coluna Numérica":
                    col_num_opts = [col for col in df_ts.columns if pd.api.types.is_numeric_dtype(df_ts[col]) and col not in ['survey_id']]
                    coluna_numerica = st.selectbox("Selecione a coluna numérica:", col_num_opts)
                    if coluna_numerica:
                        serie_temporal = df_ts.resample(map_agrupamento[agrupamento_temporal], on='data_pesquisa')[coluna_numerica].mean().reset_index()
                        fig = px.line(serie_temporal, x='data_pesquisa', y=coluna_numerica, title=f"Média de '{coluna_numerica}' ao Longo do Tempo")
                        st.plotly_chart(fig, use_container_width=True)
    
                elif metrica_ts == "Distribuição de uma Categoria":
                    col_cat_opts = [col for col in df_ts.columns if pd.api.types.is_string_dtype(df_ts[col]) and df_ts[col].nunique() < 30 and col not in ['respondent_id']]
                    coluna_categorica = st.selectbox("Selecione a coluna categórica:", col_cat_opts)
                    if coluna_categorica:
                        # Agrupa por período de tempo E pela categoria, depois conta e reestrutura
                        serie_temporal = df_ts.groupby([pd.Grouper(key='data_pesquisa', freq=map_agrupamento[agrupamento_temporal]), coluna_categorica]).size().unstack(fill_value=0)
                        fig = px.line(serie_temporal, title=f"Distribuição de '{coluna_categorica}' ao Longo do Tempo")
                        st.plotly_chart(fig, use_container_width=True)
    
        else:
            st.warning("A coluna 'data_pesquisa' com dados válidos é necessária para gráficos de série temporal.")

    except Exception as e:
        st.error(f"Não foi possível gerar o gráfico. Erro: {e}")
else:
    st.warning("Nenhum respondente encontrado para os filtros selecionados.")

with st.expander("Ver dados detalhados da seleção"):
    st.dataframe(df_filtrado, use_container_width=True)
