# pages/3_Dashboard_de_Análise.py

import streamlit as st
import pandas as pd
import plotly.express as px

from src.database import get_analytics_data

st.set_page_config(layout="wide", page_title="Dashboard de Análise")
st.logo("assets/logoBrain.png")

st.title("💡 Dashboard de Análise de Respondentes")
st.markdown(
    "Use os filtros na barra lateral para explorar os dados dos respondentes de forma interativa."
)


@st.cache_data(ttl=3600)
def load_data():

    return get_analytics_data()


df = load_data()

if df.empty:
    st.warning("A tabela de análise está vazia. Execute a pipeline na página de 'Manutenção e Admin'.")
    st.stop()


st.sidebar.header("Filtros do Dashboard")
if st.sidebar.button("🔄 Atualizar Dados do Dashboard"):
    st.cache_data.clear()
    st.rerun()

# --- LÓGICA DE FILTROS CORRIGIDA ---
if 'regiao' in df.columns and df['regiao'].notna().any():
    regioes_disponiveis = sorted(df['regiao'].dropna().unique().tolist())
    # ALTERADO: O padrão agora é 'None' (vazio), para não filtrar nada inicialmente.
    regiao_selecionada = st.sidebar.multiselect("Região", options=regioes_disponiveis, default=None)
else:
    regiao_selecionada = []

if 'geracao' in df.columns and df['geracao'].notna().any():
    geracoes_disponiveis = sorted(df['geracao'].dropna().unique().tolist())
    # ALTERADO: O padrão agora é 'None' (vazio).
    geracao_selecionada = st.sidebar.multiselect("Geração", options=geracoes_disponiveis, default=None)
else:
    geracao_selecionada = []

if 'renda_classe_agregada' in df.columns and df['renda_classe_agregada'].notna().any():
    classes_disponiveis = sorted(df['renda_classe_agregada'].dropna().unique().tolist())
    # ALTERADO: O padrão agora é 'None' (vazio).
    classe_selecionada = st.sidebar.multiselect("Classe Social", options=classes_disponiveis, default=None)
else:
    classe_selecionada = []

# A lógica de filtragem em si continua a mesma e funcionará corretamente agora.
df_filtrado = df.copy()
if regiao_selecionada:
    df_filtrado = df_filtrado[df_filtrado['regiao'].isin(regiao_selecionada)]
if geracao_selecionada:
    df_filtrado = df_filtrado[df_filtrado['geracao'].isin(geracao_selecionada)]
if classe_selecionada:
    df_filtrado = df_filtrado[df_filtrado['renda_classe_agregada'].isin(classe_selecionada)]

# --- 3. Lógica de Filtragem do DataFrame ---
df_filtrado = df.copy()
if regiao_selecionada:
    df_filtrado = df_filtrado[df_filtrado['regiao'].isin(regiao_selecionada)]
if geracao_selecionada:
    df_filtrado = df_filtrado[df_filtrado['geracao'].isin(geracao_selecionada)]
if classe_selecionada:
    df_filtrado = df_filtrado[df_filtrado['renda_classe_agregada'].isin(
        classe_selecionada)]

# --- 4. Renderização do Dashboard ---
st.markdown("---")

# KPIs
total_respondentes = len(df_filtrado)
renda_media = df_filtrado['renda_valor_estimado'].mean(
) if total_respondentes > 0 and 'renda_valor_estimado' in df_filtrado else 0
idade_media = df_filtrado['idade_numerica'].mean(
) if total_respondentes > 0 and 'idade_numerica' in df_filtrado else 0

col1, col2, col3 = st.columns(3)
col1.metric("Total de Respondentes na Seleção", f"{total_respondentes:,}")
col2.metric("Renda Média Estimada", f"R$ {renda_media:,.2f}")
col3.metric("Idade Média", f"{idade_media:.1f} anos")

st.markdown("---")
st.header("Análise Exploratória Interativa")

opcoes_variaveis = [
    'geracao', 'faixa_etaria', 'regiao', 'localidade', 'renda_classe_agregada',
    'renda_classe_detalhada', 'renda_faixa_padronizada', 'renda_macro_faixa',
    'intencao_compra_padronizada', 'tempo_intencao_padronizado',
    'idade_numerica', 'renda_valor_estimado'
]
opcoes_disponiveis = [
    opt for opt in opcoes_variaveis if opt in df_filtrado.columns
]

c1, c2 = st.columns(2)
variavel_principal = c1.selectbox(
    "Selecione a variável principal para análise:",
    options=opcoes_disponiveis,
    index=opcoes_disponiveis.index('regiao')
    if 'regiao' in opcoes_disponiveis else 0)
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
        col for col in opcoes_disponiveis if pd.api.types.is_string_dtype(
            df_filtrado[col]) and col != variavel_principal
    ]
    variavel_cor = st.selectbox("Agrupar por cor (opcional):",
                                options=opcoes_cor)
    if variavel_cor == "Nenhuma":
        variavel_cor = None

st.subheader(f"Visualização: {variavel_principal}")

# --- LÓGICA DE PLOTAGEM COMPLETA ---
if total_respondentes > 0:
    try:
        if tipo_grafico == 'Contagem (Barras)':
            df_plot = df_filtrado.sort_values(
                by=variavel_principal
            ) if variavel_principal in df_filtrado else df_filtrado
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
            # --- INÍCIO DO NOVO BLOCO DE CÓDIGO ---
            if 'data_pesquisa' not in df_filtrado.columns or df_filtrado['data_pesquisa'].isna().all():
                st.warning("A coluna 'data_pesquisa' com dados válidos é necessária para gráficos de série temporal.")
            else:
                st.markdown("---")
                st.subheader("Configurações da Análise Temporal")

                # --- 1. Controles da Análise ---
                col1, col2, col3 = st.columns(3)

                # Controle da Métrica
                metricas_disponiveis = {
                    'Contagem de Respondentes': ('respondent_id', 'count'),
                    'Média de Renda Estimada': ('renda_valor_estimado', 'mean'),
                    'Média de Idade': ('idade_numerica', 'mean')
                }
                metrica_selecionada = col1.selectbox("Selecione a Métrica:", options=metricas_disponiveis.keys())

                # Controle da Granularidade
                granularidades = {
                    'Diário': 'D',
                    'Semanal': 'W-Mon',
                    'Mensal': 'ME',
                    'Trimestral': 'QE'
                }
                granularidade_selecionada = col2.selectbox("Agrupar por Período:", options=granularidades.keys())
                
                # Controle da Dimensão de Comparação
                opcoes_dimensao = ['Nenhuma'] + [
                    col for col in ['regiao', 'geracao', 'localidade', 'faixa_etaria', 'renda_classe_agregada'] 
                    if col in df_filtrado.columns and df_filtrado[col].nunique() > 1
                ]
                dimensao_selecionada = col3.selectbox("Comparar por Dimensão (opcional):", options=opcoes_dimensao)

                # --- 2. Lógica de Processamento de Dados ---
                df_ts = df_filtrado.copy()
                df_ts['data_pesquisa'] = pd.to_datetime(df_ts['data_pesquisa'])
                
                coluna_metrica, agg_func = metricas_disponiveis[metrica_selecionada]

                # Remove nulos da coluna da métrica para evitar erros de cálculo
                if coluna_metrica != 'respondent_id':
                    df_ts.dropna(subset=[coluna_metrica], inplace=True)

                if df_ts.empty:
                    st.warning("Nenhum dado válido para a métrica selecionada neste período.")
                else:
                    # Define o índice como a data para o resample
                    df_ts = df_ts.set_index('data_pesquisa')
                    
                    # Agrupa e faz o resample
                    resample_rule = granularidades[granularidade_selecionada]
                    
                    if dimensao_selecionada == 'Nenhuma':
                        # Cenário 1: Sem dimensão, apenas uma linha
                        df_plot = df_ts.resample(resample_rule)[coluna_metrica].agg(agg_func)
                        titulo = f"{metrica_selecionada} ({granularidade_selecionada})"
                    else:
                        # Cenário 2: Com dimensão, múltiplas linhas
                        df_plot = df_ts.groupby(dimensao_selecionada).resample(resample_rule)[coluna_metrica].agg(agg_func)
                        df_plot = df_plot.unstack(level=0) # Transforma a dimensão em colunas
                        titulo = f"{metrica_selecionada} por {dimensao_selecionada} ({granularidade_selecionada})"
                    
                    # --- 3. Renderização do Gráfico ---
                    if df_plot.empty:
                        st.info("Nenhum dado para exibir com as configurações atuais.")
                    else:
                        fig = px.line(df_plot, title=titulo)
                        fig.update_layout(legend_title_text=dimensao_selecionada.replace('_', ' ').title())
                        st.plotly_chart(fig, use_container_width=True)

            # --- FIM DO NOVO BLOCO DE CÓDIGO ---

    except Exception as e:
        st.error(f"Não foi possível gerar o gráfico. Erro: {e}")
else:
    st.warning("Nenhum respondente encontrado para os filtros selecionados.")

with st.expander("Ver dados detalhados da seleção"):
    st.dataframe(df_filtrado, use_container_width=True)
