import pandas as pd
import streamlit as st

from src.database import get_analytics_data
from src.data_processing import (
    calcular_media_faixa,
    classificar_faixa_antiga,
    map_renda_to_macro_faixa,
)


st.set_page_config(layout="wide", page_title="Teste de Tratamentos")
st.logo("assets/logoBrain.png")


@st.cache_data(ttl=1800)
def load_data() -> pd.DataFrame:
    df = get_analytics_data()
    if df.empty:
        return df
    if "data_pesquisa" in df.columns:
        df["data_pesquisa"] = pd.to_datetime(df["data_pesquisa"], errors="coerce")
    return df


@st.cache_data
def convert_df_to_csv(df_to_convert: pd.DataFrame) -> bytes:
    return df_to_convert.to_csv(index=False).encode("utf-8")


def compare_series(a: pd.Series, b: pd.Series) -> pd.Series:
    a_norm = a.astype("string").str.strip().str.replace(r"\.0+$", "", regex=True)
    b_norm = b.astype("string").str.strip().str.replace(r"\.0+$", "", regex=True)
    return a_norm.fillna("<NA>") == b_norm.fillna("<NA>")


st.title("Teste de Tratamentos")
st.markdown(
    "Auditoria dos tratamentos de renda para validar se o pipeline esta extraindo e classificando corretamente."
)

if st.sidebar.button("Atualizar dados desta pagina"):
    st.cache_data.clear()
    st.rerun()

df = load_data()
if df.empty:
    st.error("Sem dados na tabela de analise. Execute a pipeline na pagina de Manutencao e Admin.")
    st.stop()

if "data_pesquisa" not in df.columns:
    st.error("A coluna 'data_pesquisa' nao existe na base de analise.")
    st.stop()

years_available = (
    df["data_pesquisa"].dropna().dt.year.astype(int).sort_values().unique().tolist()
)
default_years = [2025] if 2025 in years_available else years_available

st.markdown("---")
st.header("1. Filtros da Auditoria")
col_f1, col_f2 = st.columns(2)

with col_f1:
    selected_years = st.multiselect(
        "Ano(s) para auditoria",
        options=years_available,
        default=default_years,
    )
    if not selected_years:
        selected_years = years_available

with col_f2:
    max_rows_preview = st.number_input(
        "Maximo de linhas na previa de divergencias",
        min_value=20,
        max_value=2000,
        value=200,
        step=20,
    )

df_filtered = df[df["data_pesquisa"].dt.year.isin(selected_years)].copy()
if df_filtered.empty:
    st.warning("Nenhum registro encontrado para o(s) ano(s) selecionado(s).")
    st.stop()

expected_cols = [
    "renda_texto_original",
    "renda_valor_estimado",
    "renda_faixa_padronizada",
    "renda_macro_faixa",
    "renda_classe_agregada",
    "renda_classe_detalhada",
]
missing_cols = [c for c in expected_cols if c not in df_filtered.columns]
if missing_cols:
    st.error(
        f"A base nao tem todas as colunas esperadas para auditoria de renda. Faltando: {', '.join(missing_cols)}."
    )
    st.stop()

# Recalculo das regras de renda
df_filtered["renda_valor_estimado_recalc"] = df_filtered["renda_texto_original"].apply(
    calcular_media_faixa
)
df_filtered["renda_faixa_padronizada_recalc"] = df_filtered["renda_valor_estimado_recalc"].apply(
    classificar_faixa_antiga
)
df_filtered["renda_macro_faixa_recalc"] = df_filtered["renda_faixa_padronizada_recalc"].apply(
    map_renda_to_macro_faixa
)

match_estimado = compare_series(
    df_filtered["renda_valor_estimado"], df_filtered["renda_valor_estimado_recalc"]
)
match_faixa = compare_series(
    df_filtered["renda_faixa_padronizada"], df_filtered["renda_faixa_padronizada_recalc"]
)
match_macro = compare_series(
    df_filtered["renda_macro_faixa"], df_filtered["renda_macro_faixa_recalc"]
)

df_filtered["match_estimado"] = match_estimado
df_filtered["match_faixa"] = match_faixa
df_filtered["match_macro"] = match_macro
df_filtered["match_geral_renda"] = (
    df_filtered["match_estimado"] & df_filtered["match_faixa"] & df_filtered["match_macro"]
)

st.markdown("---")
st.header("2. Resumo da Qualidade de Tratamento")
col_k1, col_k2, col_k3, col_k4 = st.columns(4)
total = len(df_filtered)
divergencias = (~df_filtered["match_geral_renda"]).sum()
col_k1.metric("Registros analisados", f"{total:,}")
col_k2.metric("Match valor estimado", f"{(match_estimado.mean() * 100):.2f}%")
col_k3.metric("Match faixa padronizada", f"{(match_faixa.mean() * 100):.2f}%")
col_k4.metric("Match macro faixa", f"{(match_macro.mean() * 100):.2f}%")

if divergencias > 0:
    st.warning(f"Foram encontrados {divergencias:,} registros com alguma divergencia de renda.")
else:
    st.success("Nenhuma divergencia de renda encontrada para os filtros atuais.")

with st.expander("Distribuicao das colunas de renda"):
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Faixa padronizada (atual)**")
        st.dataframe(
            df_filtered["renda_faixa_padronizada"].value_counts(dropna=False).to_frame(
                "contagem"
            ),
            width="stretch",
        )
    with c2:
        st.markdown("**Macro faixa (atual)**")
        st.dataframe(
            df_filtered["renda_macro_faixa"].value_counts(dropna=False).to_frame("contagem"),
            width="stretch",
        )
    with c3:
        st.markdown("**Classe social agregada (atual)**")
        st.dataframe(
            df_filtered["renda_classe_agregada"].value_counts(dropna=False).to_frame(
                "contagem"
            ),
            width="stretch",
        )

st.subheader("Matriz de validacao: faixa atual x faixa recalculada")
matriz_faixa = pd.crosstab(
    df_filtered["renda_faixa_padronizada"].fillna("NA"),
    df_filtered["renda_faixa_padronizada_recalc"].fillna("NA"),
)
st.dataframe(matriz_faixa, width="stretch")

st.markdown("---")
st.header("3. Casos com Divergencia")
div_df = df_filtered[~df_filtered["match_geral_renda"]].copy()
cols_div = [
    "respondent_id",
    "survey_id",
    "research_name",
    "data_pesquisa",
    "renda_texto_original",
    "renda_valor_estimado",
    "renda_valor_estimado_recalc",
    "renda_faixa_padronizada",
    "renda_faixa_padronizada_recalc",
    "renda_macro_faixa",
    "renda_macro_faixa_recalc",
    "renda_classe_agregada",
    "renda_classe_detalhada",
    "match_estimado",
    "match_faixa",
    "match_macro",
]
cols_div = [c for c in cols_div if c in div_df.columns]

if div_df.empty:
    st.info("Sem divergencias para exibir.")
else:
    st.dataframe(div_df[cols_div].head(int(max_rows_preview)), width="stretch")
    st.download_button(
        label=f"Baixar divergencias ({len(div_df)} linhas)",
        data=convert_df_to_csv(div_df[cols_div]),
        file_name="teste_tratamentos_divergencias_renda.csv",
        mime="text/csv",
    )
