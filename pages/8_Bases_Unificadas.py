import pandas as pd
import streamlit as st
from datetime import date

from src.database import (
    get_analytics_data,
    get_consolidated_data_for_surveys,
)


st.set_page_config(layout="wide", page_title="Bases Unificadas")
st.logo("assets/logoBrain.png")


@st.cache_data(ttl=1800)
def load_analytics_data() -> pd.DataFrame:
    df = get_analytics_data()
    if df.empty:
        return df

    if "data_pesquisa" in df.columns:
        df["data_pesquisa"] = pd.to_datetime(df["data_pesquisa"], errors="coerce")
    return df


@st.cache_data(ttl=1800)
def load_consolidated_data_for_surveys(survey_ids: tuple[int, ...]) -> pd.DataFrame:
    if not survey_ids:
        return pd.DataFrame()
    return get_consolidated_data_for_surveys(list(survey_ids))


@st.cache_data
def convert_df_to_csv(df_to_convert: pd.DataFrame) -> bytes:
    return df_to_convert.to_csv(index=False).encode("utf-8")


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
        "regiao",
        "localidade",
        "renda_macro_faixa",
        "genero",
        "faixa_etaria",
    ]
    ordered_cols = [c for c in metadata_priority if c in final_df.columns] + [
        c for c in final_df.columns if c not in metadata_priority
    ]
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
        st.session_state["bases_unificadas_result"] = None

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
        if filtered_preview.empty:
            preview_payload["message"] = "Nenhum registro encontrado para os filtros aplicados."
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

        st.session_state["bases_unificadas_preview_payload"] = preview_payload

    st.markdown("##### Previa da base unificada (head 30)")
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

    if st.button("Gerar base unificada", type="primary"):
        applied = st.session_state.get("bases_unificadas_applied_filters")
        if not applied or "bases_unificadas_preview_payload" not in st.session_state:
            st.warning("Clique em 'Aplicar filtros' antes de gerar a base unificada.")
        else:
            with st.spinner("Aplicando filtros e montando base unificada..."):
                filtered_analytics = apply_base_filters(
                    df=df_analytics,
                    exact_start_date=applied.get("exact_start_date"),
                    exact_end_date=applied.get("exact_end_date"),
                    selected_years=applied.get("selected_years", years_options),
                    selected_regions=applied.get("selected_regions", regions_options),
                    selected_income=applied.get("selected_income", income_options),
                    selected_localidade=applied.get("selected_localidade", localidade_options),
                ).drop_duplicates(subset=["respondent_id", "survey_id"])

                if filtered_analytics.empty:
                    st.session_state["bases_unificadas_result"] = None
                    st.warning("Nenhum registro encontrado para os filtros escolhidos.")
                else:
                    survey_ids_selected = get_filtered_survey_ids(filtered_analytics)
                    df_consolidated = load_consolidated_data_for_surveys(
                        tuple(survey_ids_selected)
                    )

                    if df_consolidated.empty:
                        st.session_state["bases_unificadas_result"] = None
                        st.warning(
                            "Nenhum dado consolidado encontrado para as surveys dos filtros escolhidos."
                        )
                    else:
                        final_df, base_long, build_error, build_info = build_unified_dataframe(
                            filtered_analytics=filtered_analytics,
                            df_consolidated=df_consolidated,
                        )
                        if build_error:
                            st.session_state["bases_unificadas_result"] = None
                            st.error(build_error)
                        elif build_info:
                            st.session_state["bases_unificadas_result"] = None
                            st.warning(build_info)
                        elif final_df.empty:
                            st.session_state["bases_unificadas_result"] = None
                            st.warning(
                                "Nenhuma linha consolidada encontrada para os filtros escolhidos."
                            )
                        else:
                            st.session_state["bases_unificadas_result"] = {
                                "df": final_df,
                                "filtered_analytics": filtered_analytics,
                                "base_long": base_long,
                            }

if "bases_unificadas_result" in st.session_state and st.session_state["bases_unificadas_result"]:
    result = st.session_state["bases_unificadas_result"]
    final_df = result["df"]
    filtered_analytics = result["filtered_analytics"]
    base_long = result["base_long"]

    st.markdown("---")
    st.header("2. Resultado da unificacao")

    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    col_kpi1.metric(
        "Respondentes unicos",
        value=f"{filtered_analytics[['respondent_id', 'survey_id']].drop_duplicates().shape[0]:,}",
    )
    col_kpi2.metric("Respostas consolidadas", value=f"{len(base_long):,}")
    col_kpi3.metric("Linhas na base final", value=f"{len(final_df):,}")

    st.caption("Formato atual: Largo (1 linha por respondente)")

    with st.expander("Ver previa da base final"):
        st.dataframe(final_df.head(1000), width="stretch")

    st.download_button(
        label=f"Baixar base unificada ({len(final_df)} linhas)",
        data=convert_df_to_csv(final_df),
        file_name="base_unificada_filtrada.csv",
        mime="text/csv",
        type="primary",
    )
