import pandas as pd
import streamlit as st

from src.database import get_all_consolidated_data, get_analytics_data


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
def load_consolidated_data() -> pd.DataFrame:
    return get_all_consolidated_data()


@st.cache_data
def convert_df_to_csv(df_to_convert: pd.DataFrame) -> bytes:
    return df_to_convert.to_csv(index=False).encode("utf-8")


def get_filter_options(df: pd.DataFrame, column: str) -> list[str]:
    if column not in df.columns:
        return []
    return sorted(df[column].dropna().astype(str).unique().tolist())


def apply_base_filters(
    df: pd.DataFrame,
    start_date,
    end_date,
    selected_years: list[int],
    selected_projects: list[str],
    selected_regions: list[str],
    selected_income: list[str],
    selected_localidade: list[str],
    selected_gender: list[str],
) -> pd.DataFrame:
    filtered = df.copy()

    if "data_pesquisa" in filtered.columns and start_date and end_date:
        date_mask = (
            (filtered["data_pesquisa"].dt.date >= start_date)
            & (filtered["data_pesquisa"].dt.date <= end_date)
        )
        filtered = filtered[date_mask]

    if selected_years and "data_pesquisa" in filtered.columns:
        filtered = filtered[filtered["data_pesquisa"].dt.year.isin(selected_years)]

    if selected_projects and "research_name" in filtered.columns:
        filtered = filtered[filtered["research_name"].isin(selected_projects)]

    if selected_regions and "regiao" in filtered.columns:
        filtered = filtered[filtered["regiao"].isin(selected_regions)]

    if selected_income and "renda_macro_faixa" in filtered.columns:
        filtered = filtered[filtered["renda_macro_faixa"].isin(selected_income)]

    if selected_localidade and "localidade" in filtered.columns:
        filtered = filtered[filtered["localidade"].isin(selected_localidade)]

    if selected_gender and "genero" in filtered.columns:
        filtered = filtered[filtered["genero"].isin(selected_gender)]

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

default_start = None
default_end = None
if not valid_dates.empty:
    default_start = valid_dates.min().date()
    default_end = valid_dates.max().date()

with st.container(border=True):
    col_f1, col_f2, col_f3 = st.columns(3)

    with col_f1:
        if default_start and default_end:
            periodo = st.date_input(
                "Periodo de coleta",
                value=(default_start, default_end),
                min_value=default_start,
                max_value=default_end,
            )

            if isinstance(periodo, (tuple, list)):
                if len(periodo) == 2:
                    start_date, end_date = periodo
                elif len(periodo) == 1:
                    start_date = end_date = periodo[0]
                else:
                    start_date, end_date = default_start, default_end
            else:
                start_date = end_date = periodo
        else:
            start_date, end_date = None, None
            st.info("Sem datas validas na base.")

    with col_f2:
        years_available = []
        if "data_pesquisa" in df_analytics.columns:
            years_available = (
                df_analytics["data_pesquisa"]
                .dropna()
                .dt.year.astype(int)
                .sort_values()
                .unique()
                .tolist()
            )
        selected_years = st.multiselect(
            "Ano(s)",
            options=years_available,
            default=years_available,
            help="Use para recortes como 2021-2025 ou apenas 2025.",
        )

    with col_f3:
        output_format = st.selectbox(
            "Formato da base exportada",
            options=[
                "Largo (1 linha por respondente)",
                "Longo (1 linha por resposta)",
            ],
        )

    col_f4, col_f5, col_f6 = st.columns(3)
    with col_f4:
        selected_projects = st.multiselect(
            "Pesquisa(s)",
            options=get_filter_options(df_analytics, "research_name"),
            default=[],
        )
    with col_f5:
        selected_regions = st.multiselect(
            "Regiao(oes)",
            options=get_filter_options(df_analytics, "regiao"),
            default=[],
        )
    with col_f6:
        selected_income = st.multiselect(
            "Renda(s) macro",
            options=get_filter_options(df_analytics, "renda_macro_faixa"),
            default=[],
        )

    col_f7, col_f8 = st.columns(2)
    with col_f7:
        selected_localidade = st.multiselect(
            "Localidade(s)",
            options=get_filter_options(df_analytics, "localidade"),
            default=[],
        )
    with col_f8:
        selected_gender = st.multiselect(
            "Genero(s)",
            options=get_filter_options(df_analytics, "genero"),
            default=[],
        )

    if st.button("Gerar base unificada", type="primary"):
        with st.spinner("Aplicando filtros e montando base unificada..."):
            filtered_analytics = apply_base_filters(
                df=df_analytics,
                start_date=start_date,
                end_date=end_date,
                selected_years=selected_years,
                selected_projects=selected_projects,
                selected_regions=selected_regions,
                selected_income=selected_income,
                selected_localidade=selected_localidade,
                selected_gender=selected_gender,
            )

            filtered_analytics = filtered_analytics.drop_duplicates(
                subset=["respondent_id", "survey_id"]
            )

            if filtered_analytics.empty:
                st.session_state["bases_unificadas_result"] = None
                st.warning("Nenhum registro encontrado para os filtros escolhidos.")
            else:
                df_consolidated = load_consolidated_data()

                if df_consolidated.empty:
                    st.session_state["bases_unificadas_result"] = None
                    st.warning("A tabela consolidated_data esta vazia.")
                else:
                    req_cons_cols = {
                        "respondent_id",
                        "survey_id",
                        "question_code",
                        "answer_value",
                    }
                    if not req_cons_cols.issubset(df_consolidated.columns):
                        st.session_state["bases_unificadas_result"] = None
                        st.error(
                            "A tabela consolidated_data nao possui as colunas necessarias para unificacao."
                        )
                    else:
                        keys = filtered_analytics[
                            ["respondent_id", "survey_id"]
                        ].drop_duplicates()
                        base_long = df_consolidated.merge(
                            keys,
                            on=["respondent_id", "survey_id"],
                            how="inner",
                        )

                        if output_format == "Largo (1 linha por respondente)":
                            output_wide = (
                                base_long.pivot_table(
                                    index=["respondent_id", "survey_id"],
                                    columns="question_code",
                                    values="answer_value",
                                    aggfunc="first",
                                )
                                .reset_index()
                            )
                            final_df = output_wide.merge(
                                filtered_analytics,
                                on=["respondent_id", "survey_id"],
                                how="left",
                            )
                        else:
                            final_df = base_long.merge(
                                filtered_analytics,
                                on=["respondent_id", "survey_id"],
                                how="left",
                            )

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
                        ordered_cols = [
                            c for c in metadata_priority if c in final_df.columns
                        ] + [c for c in final_df.columns if c not in metadata_priority]
                        final_df = final_df[ordered_cols]

                        st.session_state["bases_unificadas_result"] = {
                            "df": final_df,
                            "filtered_analytics": filtered_analytics,
                            "base_long": base_long,
                            "format": output_format,
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

    st.caption(f"Formato atual: {result['format']}")

    with st.expander("Ver previa da base final"):
        st.dataframe(final_df.head(1000), use_container_width=True)

    st.download_button(
        label=f"Baixar base unificada ({len(final_df)} linhas)",
        data=convert_df_to_csv(final_df),
        file_name="base_unificada_filtrada.csv",
        mime="text/csv",
        type="primary",
    )
