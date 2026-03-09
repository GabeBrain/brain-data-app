import pandas as pd
import streamlit as st
import numpy as np
import re
import unicodedata

from src.database import get_analytics_data, get_consolidated_data_for_surveys
from src.data_processing import (
    APAC_AREAS_COLS,
    AREA_COMUM_CATEGORIAS_ALVO,
    categorizar_area_comum,
)

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False


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


def normalize_semantic_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    ).lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def get_category_prototypes() -> dict[str, str]:
    return {
        "Áreas Aquáticas | Piscinas": "piscina adulto infantil deck raia solario",
        "Atividade Física | Academias": "academia fitness musculacao pilates treino",
        "Serviço": "lavanderia coworking minimercado minimarket mini market restaurante bar bar molhado mercado autonomo pub portaria espaco delivery espaco beleza lounge louge car wash",
        "Convivência | Ambientes fechados": "salao de festas espaco gourmet sala de jogos brinquedoteca",
        "Infraestrutura Pet": "pet place pet care dog wash espaco pet",
        "Áreas Infantis & Familiares": "playground parquinho praca infantil familia criancas",
        "Convivência | Churrasqueiras": "churrasqueira grill barbecue espaco churrasco",
        "Atividade Física | Quadras": "quadra poliesportiva beach tenis tenis futsal",
        "Atividade Física | Caminhada e Ciclovia": "pista caminhada ciclovia corrida cooper bicicletario",
        "Convivência | Ambientes abertos": "rooftop praca de eventos ambiente externo jardim redario",
        "Áreas Aquáticas | Sauna e SPA": "sauna spa hidromassagem ofuro relaxamento",
    }


def run_semantic_matching_outros(
    outros_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if outros_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    base = outros_df.copy()
    base["texto_norm_sem"] = base["area_resposta_original"].apply(normalize_semantic_text)
    base = base[base["texto_norm_sem"] != ""]
    if base.empty:
        return pd.DataFrame(), pd.DataFrame()

    unique_texts = (
        base.groupby("texto_norm_sem")
        .agg(
            area_resposta_exemplo=("area_resposta_original", "first"),
            qtd_linhas=("area_resposta_original", "size"),
        )
        .reset_index()
    )

    if len(unique_texts) < 1:
        return pd.DataFrame(), pd.DataFrame()

    prototypes = get_category_prototypes()
    cat_names = list(prototypes.keys())

    prototype_texts = [normalize_semantic_text(prototypes[c]) for c in cat_names]
    corpus_fit = unique_texts["texto_norm_sem"].tolist() + prototype_texts
    vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        min_df=1,
        max_features=12000,
    )
    vectorizer.fit(corpus_fit)
    text_matrix = vectorizer.transform(unique_texts["texto_norm_sem"].tolist())
    proto_matrix = vectorizer.transform(prototype_texts)
    sim = cosine_similarity(text_matrix, proto_matrix)
    best_idx = sim.argmax(axis=1)
    best_score = sim.max(axis=1)

    unique_texts["categoria_semantica_sugerida"] = [cat_names[i] for i in best_idx]
    unique_texts["score_semantico"] = best_score

    summary = (
        unique_texts.groupby("categoria_semantica_sugerida", as_index=False)
        .agg(
            qtd_linhas=("qtd_linhas", "sum"),
            qtd_textos_unicos=("texto_norm_sem", "count"),
            score_medio=("score_semantico", "mean"),
            exemplos=("area_resposta_exemplo", lambda s: ", ".join(s.head(5).tolist())),
        )
        .sort_values("qtd_linhas", ascending=False)
    )
    return unique_texts, summary


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

st.markdown("---")
st.header("4. Classificacao Semantica dos 'Outros'")
st.markdown(
    "Compara cada resposta em 'Outros' diretamente com as categorias-alvo (sem clusters). "
    "Se o score nao atingir o minimo, permanece em 'Outros'."
)

outros_base = area_long[area_long["categoria_area_comum"] == "Outros"].copy()
if outros_base.empty:
    st.success("Nao ha registros em 'Outros' para classificar semanticamente.")
else:
    if not SKLEARN_AVAILABLE:
        st.error(
            "Dependencia ausente: instale `scikit-learn` no ambiente para habilitar a classificacao semantica."
        )
    else:
        min_score_auto = st.slider(
            "Score minimo para aceitar sugestao automatica",
            min_value=0.0,
            max_value=1.0,
            value=0.12,
            step=0.01,
        )

        if st.button("Rodar classificacao semantica", type="primary"):
            with st.spinner("Executando comparacao semantica com categorias-alvo..."):
                map_df, semantic_summary = run_semantic_matching_outros(
                    outros_df=outros_base,
                )

                if map_df.empty:
                    st.warning("Nao foi possivel gerar sugestoes para os dados atuais.")
                else:
                    categorias_alvo = set(AREA_COMUM_CATEGORIAS_ALVO)
                    map_df["categoria_semantica_sugerida"] = map_df["categoria_semantica_sugerida"].where(
                        map_df["categoria_semantica_sugerida"].isin(categorias_alvo),
                        pd.NA,
                    )
                    map_df["aceita_auto"] = (
                        (map_df["score_semantico"] >= float(min_score_auto))
                        & map_df["categoria_semantica_sugerida"].isin(categorias_alvo)
                    )
                    map_df["categoria_semantica_aplicada"] = np.where(
                        map_df["aceita_auto"],
                        map_df["categoria_semantica_sugerida"],
                        "Outros",
                    )
                    mapping_for_join = map_df[
                        [
                            "texto_norm_sem",
                            "categoria_semantica_sugerida",
                            "score_semantico",
                            "aceita_auto",
                            "categoria_semantica_aplicada",
                        ]
                    ].drop_duplicates()

                    area_long_sem = area_long.copy()
                    area_long_sem["texto_norm_sem"] = area_long_sem["area_resposta_original"].apply(normalize_semantic_text)
                    area_long_sem = area_long_sem.merge(mapping_for_join, on="texto_norm_sem", how="left")
                    area_long_sem["categoria_area_comum_auto"] = np.where(
                        area_long_sem["categoria_area_comum"] != "Outros",
                        area_long_sem["categoria_area_comum"],
                        area_long_sem["categoria_semantica_aplicada"].fillna("Outros"),
                    )

                    dist_before = area_long_sem["categoria_area_comum"].value_counts(dropna=False).to_frame("antes")
                    dist_after = area_long_sem["categoria_area_comum_auto"].value_counts(dropna=False).to_frame("depois")
                    dist_compare = dist_before.join(dist_after, how="outer").fillna(0).astype(int)

                    st.subheader("Distribuicao por categoria: antes vs depois")
                    st.dataframe(dist_compare, width="stretch")

                    st.subheader("Resumo das sugestoes semanticas")
                    st.dataframe(semantic_summary, width="stretch")

                    with st.expander("Mapa de textos para categoria sugerida"):
                        st.dataframe(
                            map_df.sort_values(["qtd_linhas", "score_semantico"], ascending=[False, False]),
                            width="stretch",
                        )

                    with st.expander("Base com categoria automatica (amostra)"):
                        cols_show = [
                            c
                            for c in [
                                "respondent_id",
                                "survey_id",
                                "pergunta_area",
                                "area_resposta_original",
                                "categoria_area_comum",
                                "categoria_semantica_sugerida",
                                "score_semantico",
                                "categoria_area_comum_auto",
                            ]
                            if c in area_long_sem.columns
                        ]
                        st.dataframe(area_long_sem[cols_show].head(1500), width="stretch")

                    st.download_button(
                        label=f"Baixar resultado semantico ({len(area_long_sem)} linhas)",
                        data=convert_df_to_csv(area_long_sem),
                        file_name="teste_tratamentos_areas_semantico.csv",
                        mime="text/csv",
                    )
