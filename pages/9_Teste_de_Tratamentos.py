import pandas as pd
import streamlit as st

from src.database import get_analytics_data, get_consolidated_data_for_surveys
from src.data_processing import (
    APAC_AREAS_COLS,
    AREA_COMUM_CATEGORIAS_ALVO,
    categorizar_area_comum,
)


st.set_page_config(layout="wide", page_title="Teste de Tratamentos")
st.logo("assets/logoBrain.png")


@st.cache_data(ttl=1800)
def load_analytics() -> pd.DataFrame:
    df = get_analytics_data()
    if df.empty:
        return df
    if "data_pesquisa" in df.columns:
        df["data_pesquisa"] = pd.to_datetime(df["data_pesquisa"], errors="coerce")
    return df


@st.cache_data(ttl=1800)
def load_apac_long_by_surveys(survey_ids: tuple[int, ...]) -> pd.DataFrame:
    if not survey_ids:
        return pd.DataFrame()
    df = get_consolidated_data_for_surveys(list(survey_ids))
    if df.empty:
        return df
    if "question_code" not in df.columns:
        return pd.DataFrame()
    return df[df["question_code"].isin(APAC_AREAS_COLS)].copy()


@st.cache_data
def convert_df_to_csv(df_to_convert: pd.DataFrame) -> bytes:
    return df_to_convert.to_csv(index=False).encode("utf-8")


def normalize_key_series(series: pd.Series) -> pd.Series:
    normalized = series.astype("string").str.strip()
    normalized = normalized.str.replace(r"\.0$", "", regex=True)
    return normalized


st.title("Teste de Tratamentos")
st.markdown(
    "Auditoria de tratamento das áreas comuns (APAC9P85_1..5), com foco na categorização antes de levar para exportação da Bases Unificadas."
)

if st.sidebar.button("Atualizar dados desta pagina"):
    st.cache_data.clear()
    st.rerun()

df_analytics = load_analytics()
if df_analytics.empty:
    st.error("Sem dados na tabela de analise. Execute a pipeline na pagina de Manutencao e Admin.")
    st.stop()

if "data_pesquisa" not in df_analytics.columns:
    st.error("A coluna 'data_pesquisa' nao existe na base de analise.")
    st.stop()

years_available = (
    df_analytics["data_pesquisa"].dropna().dt.year.astype(int).sort_values().unique().tolist()
)
default_years = [2025] if 2025 in years_available else years_available

st.markdown("---")
st.header("1. Recorte da Auditoria")
with st.form("areas_tratamento_form"):
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        selected_years = st.multiselect(
            "Ano(s) para auditoria das áreas",
            options=years_available,
            default=default_years,
        )
        if not selected_years:
            selected_years = years_available

    with col_f2:
        max_rows_outros = st.number_input(
            "Maximo de linhas para tabela de 'Outros'",
            min_value=20,
            max_value=5000,
            value=300,
            step=20,
        )

    apply_clicked = st.form_submit_button("Aplicar recorte de areas", type="primary")

if apply_clicked:
    st.session_state["areas_selected_years"] = selected_years
    st.session_state["areas_max_rows_outros"] = int(max_rows_outros)

selected_years = st.session_state.get("areas_selected_years", default_years)
max_rows_outros = st.session_state.get("areas_max_rows_outros", 300)

if not selected_years:
    st.info("Selecione ao menos um ano para carregar os dados.")
    st.stop()

df_meta = df_analytics[df_analytics["data_pesquisa"].dt.year.isin(selected_years)].copy()
if df_meta.empty:
    st.warning("Nenhum registro encontrado para o(s) ano(s) selecionado(s).")
    st.stop()

meta_cols = [
    c
    for c in [
        "respondent_id",
        "survey_id",
        "research_name",
        "data_pesquisa",
        "regiao",
        "localidade",
        "renda_macro_faixa",
    ]
    if c in df_meta.columns
]

if "respondent_id" not in meta_cols or "survey_id" not in meta_cols:
    st.error("A base de analise nao possui as chaves respondent_id/survey_id.")
    st.stop()

df_meta = df_meta[meta_cols].drop_duplicates(subset=["respondent_id", "survey_id"])
survey_ids = pd.to_numeric(df_meta["survey_id"], errors="coerce").dropna().astype(int).unique().tolist()
apac_long = load_apac_long_by_surveys(tuple(sorted(survey_ids)))

st.markdown("---")
st.header("2. Diagnostico da Origem")
col_d1, col_d2, col_d3 = st.columns(3)
col_d1.metric("Respondentes no recorte", f"{len(df_meta):,}")
col_d2.metric("Surveys no recorte", f"{len(survey_ids):,}")
col_d3.metric("Respostas APAC longas", f"{len(apac_long):,}")

if apac_long.empty:
    st.warning(
        "Nenhuma resposta APAC9P85_1..5 encontrada na consolidated_data para as surveys do recorte."
    )
    st.stop()

apac_wide = (
    apac_long.pivot_table(
        index=["respondent_id", "survey_id"],
        columns="question_code",
        values="answer_value",
        aggfunc="first",
    )
    .reset_index()
)

apac_wide["respondent_id_norm"] = normalize_key_series(apac_wide["respondent_id"])
apac_wide["survey_id_norm"] = normalize_key_series(apac_wide["survey_id"])
df_meta["respondent_id_norm"] = normalize_key_series(df_meta["respondent_id"])
df_meta["survey_id_norm"] = normalize_key_series(df_meta["survey_id"])

df_base = apac_wide.merge(
    df_meta,
    on=["respondent_id_norm", "survey_id_norm"],
    how="left",
    suffixes=("", "_meta"),
)

for col in ["respondent_id_meta", "survey_id_meta", "respondent_id_norm", "survey_id_norm"]:
    if col in df_base.columns:
        df_base = df_base.drop(columns=col)

area_cols_present = [c for c in APAC_AREAS_COLS if c in df_base.columns]
if not area_cols_present:
    st.warning("As colunas APAC9P85_1..5 nao apareceram no pivot da consolidated_data.")
    st.stop()

id_cols = [
    c
    for c in [
        "respondent_id",
        "survey_id",
        "research_name",
        "data_pesquisa",
        "regiao",
        "localidade",
        "renda_macro_faixa",
    ]
    if c in df_base.columns
]

area_long = df_base[id_cols + area_cols_present].melt(
    id_vars=id_cols,
    value_vars=area_cols_present,
    var_name="pergunta_area",
    value_name="area_resposta_original",
)
area_long["area_resposta_original"] = area_long["area_resposta_original"].astype("string").str.strip()
area_long["categoria_area_comum"] = area_long["area_resposta_original"].apply(categorizar_area_comum)

st.markdown("---")
st.header("3. Qualidade da Categorizacao")
total_linhas = len(area_long)
sem_resposta = (area_long["categoria_area_comum"] == "Sem resposta").sum()
outros = (area_long["categoria_area_comum"] == "Outros").sum()
base_valida = max(total_linhas - sem_resposta, 1)
categorizadas = total_linhas - sem_resposta - outros
cobertura = categorizadas / base_valida * 100

c_a1, c_a2, c_a3, c_a4 = st.columns(4)
c_a1.metric("Respostas APAC analisadas", f"{total_linhas:,}")
c_a2.metric("Classificadas", f"{categorizadas:,}")
c_a3.metric("Outros", f"{outros:,}")
c_a4.metric("Cobertura (sem vazios)", f"{cobertura:.2f}%")

st.caption("Categorias-alvo")
st.write(" | ".join(AREA_COMUM_CATEGORIAS_ALVO))

col_t1, col_t2 = st.columns(2)
with col_t1:
    dist_geral = (
        area_long["categoria_area_comum"]
        .value_counts(dropna=False)
        .rename_axis("categoria")
        .to_frame("contagem")
    )
    st.markdown("**Distribuicao geral por categoria**")
    st.dataframe(dist_geral, width="stretch")

with col_t2:
    dist_por_pergunta = pd.crosstab(
        area_long["pergunta_area"], area_long["categoria_area_comum"]
    )
    st.markdown("**Distribuicao por pergunta (APAC9P85_1..5)**")
    st.dataframe(dist_por_pergunta, width="stretch")

st.subheader("Top respostas originais nao mapeadas (Outros)")
outros_df = (
    area_long[area_long["categoria_area_comum"] == "Outros"]["area_resposta_original"]
    .value_counts()
    .reset_index()
)
if outros_df.empty:
    st.success("Nenhuma resposta caiu em 'Outros'.")
else:
    outros_df.columns = ["area_resposta_original", "contagem"]
    st.dataframe(outros_df.head(int(max_rows_outros)), width="stretch")

with st.expander("Ver base longa de areas classificadas"):
    st.dataframe(area_long.head(1000), width="stretch")

st.download_button(
    label=f"Baixar auditoria de areas ({len(area_long)} linhas)",
    data=convert_df_to_csv(area_long),
    file_name="teste_tratamentos_areas_classificadas.csv",
    mime="text/csv",
)
