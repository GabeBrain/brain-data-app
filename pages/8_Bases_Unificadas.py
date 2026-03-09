import pandas as pd
import streamlit as st
from datetime import date
from io import BytesIO
import numpy as np
import re
import unicodedata

from src.database import (
    get_analytics_data,
    get_consolidated_data_for_surveys,
)
from src.data_processing import (
    APAC_AREAS_COLS,
    AREA_COMUM_CATEGORIAS_ALVO,
    CODIGOS_PARA_TEXTO_ORIGINAL,
    categorizar_area_comum,
    perguntas_alvo_codigos,
)

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False


st.set_page_config(layout="wide", page_title="Bases Unificadas")
st.logo("assets/logoBrain.png")


@st.cache_data(ttl=1800, show_spinner="Preparando bases unificadas...")
def load_analytics_data() -> pd.DataFrame:
    df = get_analytics_data()
    if df.empty:
        return df

    if "data_pesquisa" in df.columns:
        df["data_pesquisa"] = pd.to_datetime(df["data_pesquisa"], errors="coerce")
    return df


@st.cache_data(ttl=1800, show_spinner="Preparando bases unificadas...")
def load_consolidated_data_for_surveys(survey_ids: tuple[int, ...]) -> pd.DataFrame:
    if not survey_ids:
        return pd.DataFrame()
    return get_consolidated_data_for_surveys(list(survey_ids))


@st.cache_data(show_spinner=False)
def convert_df_to_excel(df_to_convert: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_to_convert.to_excel(writer, index=False, sheet_name="Base_Unificada")
    return output.getvalue()


def get_filter_options(df: pd.DataFrame, column: str) -> list[str]:
    if column not in df.columns:
        return []
    return sorted(df[column].dropna().astype(str).unique().tolist())


def normalize_key_series(series: pd.Series) -> pd.Series:
    normalized = series.astype(str).str.strip()
    normalized = normalized.str.replace(r"\.0$", "", regex=True)
    normalized = normalized.replace(
        {"nan": pd.NA, "None": pd.NA, "NaT": pd.NA, "": pd.NA}
    )
    return normalized


def natural_code_sort_key(value: str) -> tuple:
    parts = re.split(r"(\d+)", str(value))
    key = []
    for part in parts:
        if part.isdigit():
            key.append((0, int(part)))
        else:
            key.append((1, part.lower()))
    return tuple(key)


def question_code_bucket(code: str) -> int:
    c = str(code).upper()
    if c.startswith("FE"):
        return 1
    if c.startswith("PS"):
        return 2
    if c.startswith("IC"):
        return 3
    if c.startswith("LOC"):
        return 4
    if c.startswith("IIA"):
        return 5
    if c.startswith("IA"):
        return 6
    if c.startswith("APAC"):
        return 7
    if c.startswith("SPP"):
        return 8
    if c.startswith("CNM"):
        return 9
    return 99


def build_canonical_question_order(available_codes: list[str]) -> list[str]:
    if not available_codes:
        return []

    available_set = set(available_codes)
    ordered: list[str] = []

    for code in perguntas_alvo_codigos.keys():
        if code in available_set and code not in ordered:
            ordered.append(code)

    for code in CODIGOS_PARA_TEXTO_ORIGINAL.keys():
        if code in available_set and code not in ordered:
            ordered.append(code)

    leftovers = [c for c in available_codes if c not in ordered]
    leftovers = sorted(
        leftovers,
        key=lambda x: (question_code_bucket(x), natural_code_sort_key(x)),
    )
    ordered.extend(leftovers)
    return ordered


def get_question_text_for_code(code: str) -> str:
    if not isinstance(code, str):
        return ""

    if code.endswith("_categorizadas"):
        base_code = code[: -len("_categorizadas")]
        base_text = get_question_text_for_code(base_code)
        if base_text:
            return f"[CATEGORIA] {base_text}"
        return f"[CATEGORIA] {base_code}"

    mapped_text = CODIGOS_PARA_TEXTO_ORIGINAL.get(code)
    if isinstance(mapped_text, str) and mapped_text.strip():
        return mapped_text.strip()

    aliases = perguntas_alvo_codigos.get(code, [])
    for alias in aliases:
        if isinstance(alias, str):
            alias_clean = alias.strip()
            if alias_clean and alias_clean != code:
                return alias_clean

    return code


def build_exportable_df_with_question_row(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    first_row = {col: get_question_text_for_code(col) for col in df.columns}
    first_row_df = pd.DataFrame([first_row])
    export_df = pd.concat([first_row_df, df], ignore_index=True)
    export_df = export_df.astype("object").where(pd.notna(export_df), "-")
    export_df = export_df.replace(r"^\s*$", "-", regex=True)
    return export_df


def build_normalized_keys(df: pd.DataFrame) -> pd.DataFrame:
    keys = df[["respondent_id", "survey_id"]].copy()
    keys["respondent_id_norm"] = normalize_key_series(keys["respondent_id"])
    keys["survey_id_norm"] = normalize_key_series(keys["survey_id"])
    keys = keys.dropna(subset=["respondent_id_norm", "survey_id_norm"]).drop_duplicates()
    return keys


def get_filtered_survey_ids(df: pd.DataFrame) -> list[int]:
    if "survey_id" not in df.columns:
        return []
    survey_ids = pd.to_numeric(df["survey_id"], errors="coerce").dropna().astype(int)
    return sorted(survey_ids.unique().tolist())


def clamp_date_range(
    start_date: date | None,
    end_date: date | None,
    min_date: date | None,
    max_date: date | None,
) -> tuple[date | None, date | None]:
    if start_date is None or end_date is None:
        return start_date, end_date

    if min_date is not None and start_date < min_date:
        start_date = min_date
    if max_date is not None and end_date > max_date:
        end_date = max_date

    if start_date > end_date:
        start_date = end_date

    return start_date, end_date


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


def get_area_category_prototypes() -> dict[str, str]:
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


def categorize_area_series_with_semantic_fallback(
    area_series: pd.Series,
    min_score: float = 0.12,
) -> pd.Series:
    categorized = area_series.apply(categorizar_area_comum)

    if not SKLEARN_AVAILABLE:
        return categorized

    mask_outros = categorized == "Outros"
    if not mask_outros.any():
        return categorized

    outros_text = area_series[mask_outros].astype("string").fillna("")
    outros_norm = outros_text.apply(normalize_semantic_text)
    unique_norm = outros_norm[outros_norm != ""].dropna().drop_duplicates()
    if unique_norm.empty:
        return categorized

    prototypes = get_area_category_prototypes()
    categorias_alvo = set(AREA_COMUM_CATEGORIAS_ALVO)
    categorias_semanticas = [c for c in prototypes.keys() if c in categorias_alvo]
    if not categorias_semanticas:
        return categorized

    prototype_texts = [normalize_semantic_text(prototypes[c]) for c in categorias_semanticas]
    vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        min_df=1,
        max_features=12000,
    )
    vectorizer.fit(unique_norm.tolist() + prototype_texts)
    text_matrix = vectorizer.transform(unique_norm.tolist())
    proto_matrix = vectorizer.transform(prototype_texts)
    similarity = cosine_similarity(text_matrix, proto_matrix)
    best_idx = similarity.argmax(axis=1)
    best_score = similarity.max(axis=1)

    semantic_map = pd.DataFrame(
        {
            "texto_norm_sem": unique_norm.tolist(),
            "categoria_semantica_sugerida": [categorias_semanticas[i] for i in best_idx],
            "score_semantico": best_score,
        }
    ).set_index("texto_norm_sem")

    outros_df = pd.DataFrame({"texto_norm_sem": outros_norm})
    outros_df = outros_df.join(semantic_map, on="texto_norm_sem")
    aceita_auto = (
        (outros_df["score_semantico"] >= float(min_score))
        & outros_df["categoria_semantica_sugerida"].isin(categorias_alvo)
    )

    categorized.loc[outros_df.index] = np.where(
        aceita_auto,
        outros_df["categoria_semantica_sugerida"],
        "Outros",
    )
    return categorized


def build_unified_dataframe(
    filtered_analytics: pd.DataFrame,
    df_consolidated: pd.DataFrame,
    max_keys: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, str | None, str | None]:
    req_cons_cols = {"respondent_id", "survey_id", "question_code", "answer_value"}
    if not req_cons_cols.issubset(df_consolidated.columns):
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            "A tabela consolidated_data nao possui as colunas necessarias para unificacao.",
            None,
        )

    if filtered_analytics.empty:
        return pd.DataFrame(), pd.DataFrame(), None, None

    filtered_keys = build_normalized_keys(filtered_analytics)
    if max_keys and max_keys > 0:
        filtered_keys = filtered_keys.head(max_keys)

    consolidated_keys = build_normalized_keys(df_consolidated)

    matched_keys = (
        filtered_keys[["respondent_id_norm", "survey_id_norm"]]
        .drop_duplicates()
        .merge(
            consolidated_keys[["respondent_id_norm", "survey_id_norm"]].drop_duplicates(),
            on=["respondent_id_norm", "survey_id_norm"],
            how="inner",
        )
    )

    if matched_keys.empty:
        survey_ids_filtered = set(filtered_keys["survey_id_norm"].dropna().tolist())
        survey_ids_consolidated = set(
            consolidated_keys["survey_id_norm"].dropna().tolist()
        )
        common_surveys = survey_ids_filtered.intersection(survey_ids_consolidated)

        info_msg = (
            "Nenhuma chave respondent_id+survey_id da selecao foi encontrada em consolidated_data. "
            f"Respondentes filtrados: {len(filtered_keys):,}. "
            f"Surveys filtradas: {len(survey_ids_filtered):,}. "
            f"Surveys em comum com consolidated_data: {len(common_surveys):,}."
        )
        return pd.DataFrame(), pd.DataFrame(), None, info_msg

    matched_raw_keys = (
        consolidated_keys.merge(
            matched_keys,
            on=["respondent_id_norm", "survey_id_norm"],
            how="inner",
        )[["respondent_id", "survey_id"]]
        .drop_duplicates()
    )

    base_long = df_consolidated.merge(
        matched_raw_keys,
        on=["respondent_id", "survey_id"],
        how="inner",
    )

    if base_long.empty:
        return pd.DataFrame(), base_long, None, None

    output_wide = (
        base_long.pivot_table(
            index=["respondent_id", "survey_id"],
            columns="question_code",
            values="answer_value",
            aggfunc="first",
        )
        .reset_index()
    )
    question_cols_from_pivot = [
        c for c in output_wide.columns if c not in {"respondent_id", "survey_id"}
    ]

    output_wide["respondent_id_norm"] = normalize_key_series(output_wide["respondent_id"])
    output_wide["survey_id_norm"] = normalize_key_series(output_wide["survey_id"])

    filtered_meta = filtered_analytics.copy()
    filtered_meta["respondent_id_norm"] = normalize_key_series(filtered_meta["respondent_id"])
    filtered_meta["survey_id_norm"] = normalize_key_series(filtered_meta["survey_id"])
    filtered_meta = filtered_meta.dropna(
        subset=["respondent_id_norm", "survey_id_norm"]
    ).drop_duplicates(subset=["respondent_id_norm", "survey_id_norm"])

    final_df = output_wide.merge(
        filtered_meta,
        on=["respondent_id_norm", "survey_id_norm"],
        how="left",
        suffixes=("", "_meta"),
    )

    # Garante a presença do texto original de renda na base unificada.
    # Se a coluna tratada não existir/estiver nula, usa FE2P10 como fallback.
    if "renda_texto_original" not in final_df.columns and "FE2P10" in final_df.columns:
        final_df["renda_texto_original"] = final_df["FE2P10"]
    elif "renda_texto_original" in final_df.columns and "FE2P10" in final_df.columns:
        final_df["renda_texto_original"] = final_df["renda_texto_original"].fillna(
            final_df["FE2P10"]
        )

    # Mantem colunas APAC originais e adiciona colunas categorizadas com fallback semantico.
    area_cols_present = [col for col in APAC_AREAS_COLS if col in final_df.columns]
    for area_col in area_cols_present:
        final_df[f"{area_col}_categorizadas"] = categorize_area_series_with_semantic_fallback(
            final_df[area_col]
        )

    drop_cols = [
        c
        for c in ["respondent_id_norm", "survey_id_norm", "respondent_id_meta", "survey_id_meta"]
        if c in final_df.columns
    ]
    if drop_cols:
        final_df = final_df.drop(columns=drop_cols)

    metadata_priority = [
        "respondent_id",
        "survey_id",
        "research_name",
        "data_pesquisa",
        "renda_texto_original",
        "regiao",
        "localidade",
        "renda_macro_faixa",
        "genero",
        "faixa_etaria",
    ]
    ordered_priority = [c for c in metadata_priority if c in final_df.columns]
    ordered_cols = ordered_priority.copy()
    consumed_cols = set(ordered_priority)
    area_cols_set = set(APAC_AREAS_COLS)

    canonical_question_cols = build_canonical_question_order(question_cols_from_pivot)
    for qcol in canonical_question_cols:
        if qcol in final_df.columns and qcol not in consumed_cols:
            ordered_cols.append(qcol)
            consumed_cols.add(qcol)

            if qcol in area_cols_set:
                cat_col = f"{qcol}_categorizadas"
                if cat_col in final_df.columns and cat_col not in consumed_cols:
                    ordered_cols.append(cat_col)
                    consumed_cols.add(cat_col)

    for col in final_df.columns:
        if col in consumed_cols:
            continue

        if col.endswith("_categorizadas"):
            base_col = col[: -len("_categorizadas")]
            if base_col in area_cols_set and base_col in final_df.columns:
                continue

        ordered_cols.append(col)
        consumed_cols.add(col)

    final_df = final_df[ordered_cols]

    return final_df, base_long, None, None


def apply_base_filters(
    df: pd.DataFrame,
    exact_start_date,
    exact_end_date,
    selected_years: list[int],
    selected_regions: list[str],
    selected_income: list[str],
    selected_localidade: list[str],
) -> pd.DataFrame:
    filtered = df.copy()

    if "data_pesquisa" in filtered.columns and selected_years:
        filtered = filtered[filtered["data_pesquisa"].dt.year.isin(selected_years)]

    if "data_pesquisa" in filtered.columns and exact_start_date and exact_end_date:
        date_mask = (
            (filtered["data_pesquisa"].dt.date >= exact_start_date)
            & (filtered["data_pesquisa"].dt.date <= exact_end_date)
        )
        filtered = filtered[date_mask]

    if selected_regions and "regiao" in filtered.columns:
        filtered = filtered[filtered["regiao"].isin(selected_regions)]

    if selected_income and "renda_macro_faixa" in filtered.columns:
        filtered = filtered[filtered["renda_macro_faixa"].isin(selected_income)]

    if selected_localidade and "localidade" in filtered.columns:
        filtered = filtered[filtered["localidade"].isin(selected_localidade)]

    return filtered


st.title("Bases Unificadas")
st.markdown(
    "Extraia uma base unificada sem amostragem. Tudo que passar pelos filtros entra no arquivo final."
)

if st.sidebar.button("Atualizar dados desta pagina"):
    st.cache_data.clear()
    st.rerun()

df_analytics = load_analytics_data()

if df_analytics.empty:
    st.error(
        "A tabela de analise esta vazia. Execute a pipeline na pagina de Manutencao e Admin."
    )
    st.stop()

required_cols = ["respondent_id", "survey_id"]
missing_cols = [col for col in required_cols if col not in df_analytics.columns]
if missing_cols:
    st.error(
        f"Erro critico: faltam colunas essenciais na base de analise: {', '.join(missing_cols)}."
    )
    st.stop()

st.markdown("---")
st.header("1. Defina os filtros da base unificada")

date_col = df_analytics.get("data_pesquisa")
valid_dates = date_col.dropna() if isinstance(date_col, pd.Series) else pd.Series(dtype="datetime64[ns]")

global_min_date = None
global_max_date = None
years_available: list[int] = []
if not valid_dates.empty:
    global_min_date = valid_dates.min().date()
    global_max_date = valid_dates.max().date()
    years_available = (
        valid_dates.dt.year.astype(int)
        .sort_values()
        .unique()
        .tolist()
    )

with st.container(border=True):
    years_options = years_available
    regions_options = get_filter_options(df_analytics, "regiao")
    income_options = get_filter_options(df_analytics, "renda_macro_faixa")
    localidade_options = get_filter_options(df_analytics, "localidade")

    default_filter_state = {
        "selected_years": years_options,
        "selected_regions": regions_options,
        "selected_income": income_options,
        "selected_localidade": localidade_options,
        "use_exact_range": False,
        "exact_start_date": None,
        "exact_end_date": None,
    }
    if "bases_unificadas_applied_filters" not in st.session_state:
        st.session_state["bases_unificadas_applied_filters"] = default_filter_state

    applied_filters = st.session_state["bases_unificadas_applied_filters"]
    pre_selected_years = [
        y for y in applied_filters.get("selected_years", years_options)
        if y in years_options
    ] or years_options
    pre_selected_regions = [
        r for r in applied_filters.get("selected_regions", regions_options)
        if r in regions_options
    ] or regions_options
    pre_selected_income = [
        r for r in applied_filters.get("selected_income", income_options)
        if r in income_options
    ] or income_options
    pre_selected_localidade = [
        l for l in applied_filters.get("selected_localidade", localidade_options)
        if l in localidade_options
    ] or localidade_options

    with st.form("bases_unificadas_filters_form"):
        col_year, col_region, col_income, col_localidade = st.columns(4)

        with col_year:
            selected_years_input = st.multiselect(
                "Ano(s) - filtro principal",
                options=years_options,
                default=pre_selected_years,
                help="Exemplo: selecionar 2025 usa automaticamente de 01/01/2025 a 31/12/2025.",
            )
            selected_years_for_display = (
                selected_years_input if selected_years_input else years_options
            )
            if selected_years_for_display:
                anos_ordenados = sorted(selected_years_for_display)
                periodo_principal_inicio = date(min(anos_ordenados), 1, 1)
                periodo_principal_fim = date(max(anos_ordenados), 12, 31)
                st.caption(
                    f"Periodo principal por Ano(s): {periodo_principal_inicio.strftime('%d/%m/%Y')} a {periodo_principal_fim.strftime('%d/%m/%Y')}"
                )
            else:
                st.info("Sem datas validas na base.")

            use_exact_range_input = bool(applied_filters.get("use_exact_range", False))
            faixa_exata_input = None
            default_exact_start = None
            default_exact_end = None

            with st.popover("Faixa exata (opcional)"):
                if selected_years_for_display:
                    min_selected = min(selected_years_for_display)
                    max_selected = max(selected_years_for_display)
                    default_exact_start = date(min_selected, 1, 1)
                    default_exact_end = date(max_selected, 12, 31)
                else:
                    default_exact_start = global_min_date
                    default_exact_end = global_max_date

                default_exact_start, default_exact_end = clamp_date_range(
                    default_exact_start,
                    default_exact_end,
                    global_min_date,
                    global_max_date,
                )

                if default_exact_start is not None and default_exact_end is not None:
                    saved_start = applied_filters.get("exact_start_date")
                    saved_end = applied_filters.get("exact_end_date")
                    if use_exact_range_input and saved_start and saved_end:
                        default_exact_start, default_exact_end = clamp_date_range(
                            saved_start,
                            saved_end,
                            global_min_date,
                            global_max_date,
                        )

                    faixa_exata_input = st.date_input(
                        "Escolha a faixa exata",
                        value=(default_exact_start, default_exact_end),
                        min_value=global_min_date,
                        max_value=global_max_date,
                        format="DD/MM/YYYY",
                    )

                    use_exact_range_input = st.checkbox(
                        "Aplicar faixa exata",
                        value=use_exact_range_input,
                        help="Opcional. Refina o recorte de Ano(s).",
                    )
                else:
                    st.info("Sem datas validas para aplicar faixa exata.")

        with col_region:
            selected_regions_input = st.multiselect(
                "Regiao(oes)",
                options=regions_options,
                default=pre_selected_regions,
            )
        with col_income:
            selected_income_input = st.multiselect(
                "Renda(s) macro",
                options=income_options,
                default=pre_selected_income,
            )
        with col_localidade:
            selected_localidade_input = st.multiselect(
                "Localidade(s)",
                options=localidade_options,
                default=pre_selected_localidade,
            )

        apply_filters_clicked = st.form_submit_button(
            "Aplicar filtros",
            type="primary",
        )

    if apply_filters_clicked:
        selected_years = selected_years_input if selected_years_input else years_options
        selected_regions = selected_regions_input if selected_regions_input else regions_options
        selected_income = selected_income_input if selected_income_input else income_options
        selected_localidade = (
            selected_localidade_input if selected_localidade_input else localidade_options
        )

        exact_start_date = None
        exact_end_date = None
        if use_exact_range_input and faixa_exata_input is not None:
            if isinstance(faixa_exata_input, (tuple, list)):
                if len(faixa_exata_input) == 2:
                    temp_start_date, temp_end_date = faixa_exata_input
                elif len(faixa_exata_input) == 1:
                    temp_start_date = temp_end_date = faixa_exata_input[0]
                else:
                    temp_start_date, temp_end_date = default_exact_start, default_exact_end
            else:
                temp_start_date = temp_end_date = faixa_exata_input

            temp_start_date, temp_end_date = clamp_date_range(
                temp_start_date,
                temp_end_date,
                global_min_date,
                global_max_date,
            )
            if temp_start_date and temp_end_date:
                exact_start_date, exact_end_date = temp_start_date, temp_end_date

        st.session_state["bases_unificadas_applied_filters"] = {
            "selected_years": selected_years,
            "selected_regions": selected_regions,
            "selected_income": selected_income,
            "selected_localidade": selected_localidade,
            "use_exact_range": use_exact_range_input,
            "exact_start_date": exact_start_date,
            "exact_end_date": exact_end_date,
        }
        st.session_state["bases_unificadas_export_payload"] = None

        filtered_preview = apply_base_filters(
            df=df_analytics,
            exact_start_date=exact_start_date,
            exact_end_date=exact_end_date,
            selected_years=selected_years,
            selected_regions=selected_regions,
            selected_income=selected_income,
            selected_localidade=selected_localidade,
        ).drop_duplicates(subset=["respondent_id", "survey_id"])

        preview_payload = {
            "filtered_count": len(filtered_preview),
            "status": "info",
            "message": "Nenhuma linha consolidada encontrada para os filtros atuais.",
            "preview_head": pd.DataFrame(),
            "preview_total_rows": 0,
            "preview_total_cols": 0,
            "preview_limited": len(filtered_preview) > 500,
        }
        export_payload = {
            "status": "info",
            "message": "Nenhuma linha consolidada encontrada para os filtros atuais.",
            "export_df": pd.DataFrame(),
            "interviews_count": 0,
        }
        if filtered_preview.empty:
            preview_payload["message"] = "Nenhum registro encontrado para os filtros aplicados."
            export_payload["message"] = "Nenhum registro encontrado para os filtros aplicados."
        else:
            survey_ids_preview = get_filtered_survey_ids(filtered_preview)
            df_consolidated_preview = load_consolidated_data_for_surveys(
                tuple(survey_ids_preview)
            )
            if df_consolidated_preview.empty:
                preview_payload["status"] = "warning"
                preview_payload["message"] = (
                    "Nenhum dado consolidado encontrado para as surveys da selecao atual."
                )
                export_payload["status"] = "warning"
                export_payload["message"] = preview_payload["message"]
            else:
                preview_df, _, preview_error, preview_info = build_unified_dataframe(
                    filtered_analytics=filtered_preview,
                    df_consolidated=df_consolidated_preview,
                    max_keys=500,
                )
                if preview_error:
                    preview_payload["status"] = "error"
                    preview_payload["message"] = preview_error
                elif preview_info:
                    preview_payload["status"] = "warning"
                    preview_payload["message"] = preview_info
                elif preview_df.empty:
                    preview_payload["status"] = "info"
                    preview_payload["message"] = (
                        "Nenhuma linha consolidada encontrada para os filtros atuais."
                    )
                else:
                    preview_payload["status"] = "ok"
                    preview_payload["message"] = ""
                    preview_payload["preview_head"] = preview_df.head(30)
                    preview_payload["preview_total_rows"] = len(preview_df)
                    preview_payload["preview_total_cols"] = preview_df.shape[1]

                full_df, _, full_error, full_info = build_unified_dataframe(
                    filtered_analytics=filtered_preview,
                    df_consolidated=df_consolidated_preview,
                )
                if full_error:
                    export_payload["status"] = "error"
                    export_payload["message"] = full_error
                elif full_info:
                    export_payload["status"] = "warning"
                    export_payload["message"] = full_info
                elif full_df.empty:
                    export_payload["status"] = "info"
                    export_payload["message"] = (
                        "Nenhuma linha consolidada encontrada para os filtros atuais."
                    )
                else:
                    export_payload["status"] = "ok"
                    export_payload["message"] = ""
                    export_payload["interviews_count"] = len(full_df)
                    export_payload["export_df"] = build_exportable_df_with_question_row(full_df)

        st.session_state["bases_unificadas_preview_payload"] = preview_payload
        st.session_state["bases_unificadas_export_payload"] = export_payload

    st.markdown("##### Previa da base unificada")
    preview_payload = st.session_state.get("bases_unificadas_preview_payload")
    if not preview_payload:
        st.info("Ajuste os filtros e clique em 'Aplicar filtros' para carregar a previa.")
    else:
        st.caption(
            f"Respondentes unicos na selecao atual: {preview_payload.get('filtered_count', 0):,}"
        )
        status = preview_payload.get("status")
        message = preview_payload.get("message", "")
        if status == "error":
            st.error(message)
        elif status == "warning":
            st.warning(message)
        elif status == "info" and message:
            st.info(message)
        elif status == "ok":
            st.caption(
                f"Linhas da base unificada atual: {preview_payload.get('preview_total_rows', 0):,}"
            )
            st.caption(
                f"Total de colunas na base unificada: {preview_payload.get('preview_total_cols', 0):,}"
            )
            if preview_payload.get("preview_limited"):
                st.caption(
                    "Previa calculada com ate 500 respondentes da selecao para manter performance."
                )
            st.caption(
                "Dica: role horizontalmente na tabela para visualizar todas as colunas."
            )
            st.dataframe(preview_payload.get("preview_head", pd.DataFrame()), width="stretch")

    export_payload = st.session_state.get("bases_unificadas_export_payload")
    if not export_payload:
        st.info("Clique em 'Aplicar filtros' para habilitar o download da base.")
    else:
        export_status = export_payload.get("status")
        export_message = export_payload.get("message", "")
        if export_status == "error":
            st.error(export_message)
        elif export_status == "warning":
            st.warning(export_message)
        elif export_status == "info" and export_message:
            st.info(export_message)
        elif export_status == "ok":
            export_df = export_payload.get("export_df", pd.DataFrame())
            interviews_count = int(export_payload.get("interviews_count", 0))
            st.download_button(
                label=f"Baixar base unificada ({interviews_count:,} entrevistas)",
                data=convert_df_to_excel(export_df),
                file_name="base_unificada_filtrada.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
            )
