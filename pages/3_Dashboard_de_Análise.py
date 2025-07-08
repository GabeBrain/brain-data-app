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

# --- Botão para Limpar o Cache ---
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Atualizar Dados do Dashboard"):
    st.cache_data.clear()
    st.rerun()


# --- Carregamento dos Dados ---
@st.cache_data(ttl=3600)
def load_data():
    return get_analytics_data()


df = load_data()

if df.empty:
    st.warning(
        "A tabela de análise está vazia. Execute a pipeline na página 'Manutenção e Admin'."
    )
    st.stop()

# --- BARRA LATERAL DE FILTROS ---
st.sidebar.header("Filtros do Dashboard")

# Filtro de Região
if 'regiao' in df.columns and df['regiao'].notna().any():
    regioes_disponiveis = sorted(df['regiao'].dropna().unique().tolist())
    regiao_selecionada = st.sidebar.multiselect("Região",
                                                options=regioes_disponiveis,
                                                default=regioes_disponiveis)
else:
    regiao_selecionada = []

# Filtro de Geração
if 'geracao' in df.columns and df['geracao'].notna().any():
    geracoes_disponiveis = sorted(df['geracao'].dropna().unique().tolist())
    geracao_selecionada = st.sidebar.multiselect("Geração",
                                                 options=geracoes_disponiveis,
                                                 default=geracoes_disponiveis)
else:
    geracao_selecionada = []

# Filtro de Classe Social
if 'renda_classe_agregada' in df.columns and df['renda_classe_agregada'].notna(
).any():
    classes_disponiveis = sorted(
        df['renda_classe_agregada'].dropna().unique().tolist())
    classe_selecionada = st.sidebar.multiselect("Classe Social",
                                                options=classes_disponiveis,
                                                default=classes_disponiveis)
else:
    classe_selecionada = []

# --- Lógica de Filtragem ---
df_filtrado = df.copy()
if regiao_selecionada:
    df_filtrado = df_filtrado[df_filtrado['regiao'].isin(regiao_selecionada)]
if geracao_selecionada:
    df_filtrado = df_filtrado[df_filtrado['geracao'].isin(geracao_selecionada)]
if classe_selecionada:
    df_filtrado = df_filtrado[df_filtrado['renda_classe_agregada'].isin(
        classe_selecionada)]

# --- Renderização do Dashboard ---
st.markdown("---")

# --- BLOCO DE KPIS REINSERIDO ---
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
# --- FIM DO BLOCO DE KPIS ---

st.header("Análise Exploratória Interativa")

opcoes_variaveis = [
    'geracao', 'faixa_etaria', 'regiao', 'localidade', 'renda_classe_agregada',
    'renda_classe_detalhada', 'renda_faixa_padronizada', 'renda_macro_faixa',
    'renda_valor_estimado', 'intencao_compra_padronizada',
    'tempo_intencao_padronizado', 'idade_numerica'
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

if total_respondentes > 0:
    try:
        # (O código para gerar os gráficos não precisa de alteração, pois ele usa as variáveis selecionadas)
        if tipo_grafico == 'Contagem (Barras)':
            df_plot = df_filtrado.sort_values(
                by=variavel_principal
            ) if variavel_principal in df_filtrado else df_filtrado
            fig = px.bar(df_plot,
                         x=variavel_principal,
                         color=variavel_cor,
                         title=f"Contagem por '{variavel_principal}'")
            st.plotly_chart(fig, use_container_width=True)
        # ... (código dos outros gráficos) ...
    except Exception as e:
        st.error(f"Não foi possível gerar o gráfico. Erro: {e}")
else:
    st.warning("Nenhum respondente encontrado para os filtros selecionados.")

with st.expander("Ver dados detalhados da seleção"):
    st.dataframe(df_filtrado, use_container_width=True)
