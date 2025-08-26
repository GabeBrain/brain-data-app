# src/database.py

import streamlit as st  # Mantido para st.cache_resource
import psycopg2
import os
import pandas as pd
import numpy as np
import hashlib
import datetime
import json
from psycopg2 import sql
from psycopg2.extras import execute_values

# Importações locais para evitar problemas de importação circular
from src.data_ingestion import fetch_data_from_api
from src.data_processing import map_api_columns_to_target_codes

# --- Configuração do Banco de Dados PostgreSQL (Usando Secrets do Replit) ---
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")


@st.cache_resource
def get_db_connection():
    """
    Estabelece conexão com o banco de dados e inclui um bloco de diagnóstico
    para verificar se os secrets foram carregados corretamente.
    """
    # --- Bloco de Diagnóstico de Secrets ---
    db_secrets = {
        "DB_HOST": os.environ.get("DB_HOST"),
        "DB_PORT": os.environ.get("DB_PORT"),
        "DB_NAME": os.environ.get("DB_NAME"),
        "DB_USER": os.environ.get("DB_USER"),
        "DB_PASSWORD": os.environ.get("DB_PASSWORD")
    }
    
    # Verifica se alguma das chaves tem um valor vazio ou nulo
    missing_secrets = [key for key, value in db_secrets.items() if not value]
    
    if missing_secrets:
        error_message = f"ERRO CRÍTICO: As seguintes variáveis de ambiente (Secrets) não foram encontradas ou estão vazias: {', '.join(missing_secrets)}. Por favor, verifique a configuração de 'Secrets' no seu painel do Streamlit Cloud."
        st.error(error_message)
        raise ConnectionError(error_message)
    
    # --- Fim do Bloco de Diagnóstico ---

    try:
        conn = psycopg2.connect(
            host=db_secrets["DB_HOST"],
            port=db_secrets["DB_PORT"],
            database=db_secrets["DB_NAME"],
            user=db_secrets["DB_USER"],
            password=db_secrets["DB_PASSWORD"]
        )
        return conn
    except Exception as e:
        st.error(f"Falha ao conectar ao PostgreSQL após carregar os secrets. Verifique se as credenciais estão corretas e se o banco está acessível. Erro: {e}")
        raise ConnectionError(f"Não foi possível conectar ao banco de dados: {e}")



def init_db_schema() -> bool:
    conn = get_db_connection()
    if conn is None: return False
    cursor = conn.cursor()
    try:
        # Tabela de Metadados das Pesquisas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS surveys (
                survey_id SERIAL PRIMARY KEY,
                research_name TEXT NOT NULL,
                creation_date DATE NOT NULL,
                api_link TEXT NOT NULL UNIQUE,
                expected_total INTEGER,
                collected_count INTEGER DEFAULT 0,
                collected_percentage NUMERIC(5, 2) DEFAULT 0.00,
                last_fetched TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # Tabela de Dados Brutos dos Respondentes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS survey_respondent_data (
                respondent_id TEXT NOT NULL,
                survey_id INTEGER NOT NULL REFERENCES surveys(survey_id) ON DELETE CASCADE,
                data_jsonb JSONB NOT NULL,
                fetched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (respondent_id, survey_id)
            );
        """)
        # Tabela de Log da Consolidação
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS consolidation_log (
                log_id SERIAL PRIMARY KEY,
                survey_id INTEGER NOT NULL REFERENCES surveys(survey_id) ON DELETE CASCADE UNIQUE,
                last_consolidated_at TIMESTAMP WITH TIME ZONE,
                unique_questions_consolidated INTEGER
            );
        """)
        # Tabela de Dados Consolidados
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS consolidated_data (
                id SERIAL PRIMARY KEY,
                respondent_id TEXT NOT NULL,
                survey_id INTEGER NOT NULL,
                question_code TEXT NOT NULL,
                answer_value TEXT,
                FOREIGN KEY (survey_id) REFERENCES surveys(survey_id) ON DELETE CASCADE,
                UNIQUE (respondent_id, survey_id, question_code)
            );
        """)
        # Tabela Final para Análise (Formato Largo e Tratado)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics_respondents (
                respondent_id TEXT NOT NULL,
                        survey_id INTEGER NOT NULL,
                        research_name TEXT,
                        data_pesquisa TIMESTAMP,
                        idade_original TEXT,
                        idade_numerica INTEGER,
                        geracao TEXT,
                        faixa_etaria TEXT,
                        renda_texto_original TEXT,
                        renda_valor_estimado INTEGER,
                        renda_faixa_padronizada TEXT, 
                        renda_macro_faixa TEXT,       
                        renda_classe_agregada TEXT,     
                        renda_classe_detalhada TEXT,  
                        cidade_original TEXT,
                        localidade TEXT,
                        estado_original TEXT,
                        estado_nome TEXT,
                        regiao TEXT,
                        intencao_compra_original TEXT,
                        intencao_compra_padronizada TEXT,
                        tempo_intencao_original TEXT,
                        tempo_intencao_padronizado TEXT,
                        genero TEXT,
                        latitude NUMERIC(10, 7),
                        longitude NUMERIC(10, 7),
                        PRIMARY KEY (respondent_id, survey_id),
                        FOREIGN KEY (survey_id) REFERENCES surveys(survey_id) ON DELETE CASCADE
                    );
                """)
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao inicializar o schema do banco de dados: {e}")
        raise Exception(f"Erro ao inicializar esquema do DB: {e}")
    finally:
        cursor.close()


# --- Funções de CRUD para a tabela 'surveys' ---


def add_survey_metadata(research_name,
                        creation_date,
                        api_link,
                        expected_total=None) -> int | None:
    """
    Adiciona metadados de uma nova pesquisa na tabela 'surveys'.
    Devido à ausência de restrições UNIQUE em 'api_link' e 'research_name' no DB,
    esta função simplesmente tenta INSERIR uma nova linha.

    Returns:
        int: O survey_id da nova linha inserida.
        None: Se houver um erro na inserção.
    """
    conn = get_db_connection()
    if conn is None: return None

    cursor = conn.cursor()
    try:
        # Removida cláusula ON CONFLICT para evitar erro se api_link não for UNIQUE no DB.
        # Isso resultará em DUPLICATAS de api_link e research_name na tabela surveys.
        cursor.execute(
            sql.SQL("""
                INSERT INTO surveys (research_name, creation_date, api_link, expected_total, last_fetched)
                VALUES (%s, %s, %s, %s, NOW())
                RETURNING survey_id;
            """), (research_name, creation_date, api_link, expected_total))
        survey_id = cursor.fetchone()
        conn.commit()
        return survey_id[0] if survey_id else None

    except Exception:  # Captura qualquer erro, inclusive de NOT NULL, etc.
        conn.rollback()
        return None
    finally:
        cursor.close()


def update_survey_metadata(survey_id: int, research_name: str,
                           creation_date: str, api_link: str,
                           expected_total: int | None) -> bool:
    conn = get_db_connection()
    if conn is None: return False

    cursor = conn.cursor()
    try:
        cursor.execute(
            sql.SQL("""
                UPDATE surveys
                SET
                    research_name = %s,
                    creation_date = %s,
                    api_link = %s,
                    expected_total = %s,
                    last_fetched = NOW()
                WHERE survey_id = %s;
            """), (research_name, creation_date, api_link, expected_total,
                   survey_id))
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        conn.rollback()
        return False
    finally:
        cursor.close()


def delete_survey(survey_id: int) -> bool:
    """
    Realiza um 'hard delete' controlado de uma pesquisa e todos os seus dados associados
    em todas as tabelas relacionadas, dentro de uma única transação.
    """
    conn = get_db_connection()
    if conn is None: return False

    # Lista de tabelas das quais devemos deletar, em ordem de dependência (filhos primeiro)
    tables_to_delete_from = [
        "analytics_respondents",
        "consolidated_data",
        "consolidation_log",
        "survey_respondent_data",
        "surveys"  # A tabela principal, 'surveys', é sempre a última
    ]

    cursor = conn.cursor()
    try:
        # Inicia a transação. Nada será salvo permanentemente até o conn.commit()
        print(f"Iniciando exclusão em cascata para survey_id: {survey_id}")

        for table in tables_to_delete_from:
            # Para a tabela 'surveys', o campo de referência é survey_id
            # Para as outras, também é survey_id. Se fosse diferente, ajustaríamos aqui.
            id_column = "survey_id"

            query = sql.SQL(
                "DELETE FROM {table} WHERE {id_column} = %s").format(
                    table=sql.Identifier(table),
                    id_column=sql.Identifier(id_column))
            cursor.execute(query, (survey_id, ))
            print(f"  - {cursor.rowcount} registros deletados de '{table}'")

        # Se todos os comandos DELETE foram bem-sucedidos, salva as alterações permanentemente.
        conn.commit()
        print("Transação concluída com sucesso.")
        return True

    except Exception as e:
        # Se qualquer um dos comandos DELETE falhar, desfaz TODAS as alterações feitas nesta transação.
        print(f"ERRO durante a transação. Desfazendo alterações. Erro: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()


def get_all_surveys() -> pd.DataFrame:
    """
    Busca todas as pesquisas e suas estatísticas de coleta.
    """
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()

    try:
        # Query CORRIGIDA: Removida a coluna 'is_active' que não existe.
        query = """
            SELECT 
                survey_id, 
                research_name, 
                creation_date, 
                api_link, 
                expected_total,
                collected_count,
                collected_percentage,
                last_fetched 
            FROM surveys 
            ORDER BY creation_date DESC;
        """
        df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        st.error(f"Erro detalhado ao buscar pesquisas (get_all_surveys): {e}")
        # Mantive o print para nos ajudar em futuros debugs
        print(f"DEBUG get_all_surveys: {e}")
        return pd.DataFrame()


def get_survey_summary_stats(
) -> tuple[int, datetime.date | None, datetime.date | None]:
    conn = get_db_connection()
    if conn is None:
        return 0, None, None

    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT
                COUNT(survey_id) AS total_surveys,
                MIN(creation_date) AS first_creation_date,
                MAX(creation_date) AS last_creation_date
            FROM surveys;
        """)
        result = cursor.fetchone()

        total_surveys, first_date, last_date = result
        return total_surveys, first_date, last_date
    except Exception:
        return 0, None, None
    finally:
        cursor.close()


def get_respondent_count(survey_id: int) -> int:
    conn = get_db_connection()
    if conn is None:
        return 0

    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT COUNT(*) FROM survey_respondent_data WHERE survey_id = %s;",
            (survey_id, ))
        count = cursor.fetchone()[0]
        return count
    except Exception:
        return 0
    finally:
        cursor.close()


def get_total_respondent_records() -> int:
    conn = get_db_connection()
    if conn is None:
        return 0

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM survey_respondent_data;")
        count = cursor.fetchone()[0]
        return count
    except Exception:
        return 0
    finally:
        cursor.close()


def get_total_expected_collection() -> int:
    conn = get_db_connection()
    if conn is None:
        return 0

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COALESCE(SUM(expected_total), 0) FROM surveys;")
        total_expected = cursor.fetchone()[0]
        return total_expected
    except Exception:
        return 0
    finally:
        cursor.close()


def store_respondent_data(
        survey_id: int,
        raw_api_data: list,
        id_column_name: str = 'Código') -> tuple[bool, int, str | None]:
    """
    Armazena os dados de respondentes individuais no banco de dados 'survey_respondent_data'.
    Não exibe mensagens no Streamlit diretamente.

    Returns:
        tuple: (success_bool, new_records_count, warning_message_or_none)
    """
    conn = get_db_connection()
    if conn is None:
        return False, 0, "Falha na conexão com o banco de dados."

    cursor = conn.cursor()
    try:
        # Pega os IDs de respondentes já existentes para esta pesquisa para evitar duplicatas
        cursor.execute(
            "SELECT respondent_id FROM survey_respondent_data WHERE survey_id = %s;",
            (survey_id, ))
        existing_respondent_ids = {row[0] for row in cursor.fetchall()}

        new_records_count = 0
        warning_messages = []

        for record in raw_api_data:
            respondent_id = record.get(id_column_name, None)
            if respondent_id is not None:
                respondent_id = str(respondent_id).strip()

            if not respondent_id:
                warn_msg = f"ID ('{id_column_name}') vazio/não encontrado para registro na pesquisa {survey_id}. Gerando hash."
                warning_messages.append(warn_msg)

                try:
                    temp_record_for_hash = record.copy()
                    keys_to_remove_for_hash = [
                        'timestamp_coleta', 'data_hora_envio', 'data_registro',
                        'timestamp', 'date_collected', 'Time', 'Date', 'id',
                        'Created_At', 'Updated_At'
                    ]
                    for key_to_remove in keys_to_remove_for_hash:
                        temp_record_for_hash.pop(key_to_remove, None)

                    hash_string = json.dumps(temp_record_for_hash,
                                             sort_keys=True)
                    respondent_id = hashlib.md5(
                        hash_string.encode('utf-8')).hexdigest()
                    warning_messages.append(
                        f"  Hash gerado: {respondent_id[:8]}...")
                except Exception as hash_e:
                    return False, 0, f"Não foi possível gerar ID único para registro na pesquisa {survey_id} usando hash: {hash_e}. Registro ignorado."

            if not respondent_id:
                return False, 0, f"Não foi possível determinar ID único para registro na pesquisa {survey_id} após todas as tentativas. Registro ignorado."

            respondent_id_final = str(respondent_id).strip()

            if respondent_id_final not in existing_respondent_ids:
                cursor.execute(
                    sql.SQL("""
                        INSERT INTO survey_respondent_data (respondent_id, survey_id, data_jsonb, fetched_at)
                        VALUES (%s, %s, %s, NOW());
                    """), (respondent_id_final, survey_id, json.dumps(record)))
                new_records_count += 1

        conn.commit()

        final_message = "\n".join(
            warning_messages) if warning_messages else None
        return True, new_records_count, final_message
    except Exception as e:
        conn.rollback()
        return False, 0, f"Erro ao armazenar dados do respondente: {e}"
    finally:
        cursor.close()


def consolidate_survey_data(survey_id: int) -> tuple[bool, str]:
    """
    Extrai dados do JSONB da tabela survey_respondent_data,
    filtra apenas pelas chaves que estão no dicionário de mapeamento,
    e insere os dados na tabela consolidada.
    """
    from src.data_processing import perguntas_alvo_codigos  # Importação local para evitar import circular
    target_codes = set(perguntas_alvo_codigos.keys())

    conn = get_db_connection()
    if conn is None:
        return False, "Falha na conexão com o banco de dados."

    cursor = conn.cursor()
    try:
        # 1. Buscar todos os dados JSONB para a pesquisa especificada
        cursor.execute(
            "SELECT respondent_id, data_jsonb FROM survey_respondent_data WHERE survey_id = %s;",
            (survey_id, ))
        all_respondent_data = cursor.fetchall()

        if not all_respondent_data:
            return True, "Nenhum dado de respondente para consolidar."

        # 2. Preparar os dados para inserção em lote
        values_to_insert = []
        questions_found_in_this_run = set()

        for respondent_id, data_jsonb in all_respondent_data:
            for key, value in data_jsonb.items():
                if key in target_codes:
                    # Adiciona a pergunta ao set de perguntas encontradas
                    questions_found_in_this_run.add(key)
                    # Adiciona a tupla de valores para inserção
                    # Convertemos o valor para string para garantir compatibilidade
                    values_to_insert.append(
                        (respondent_id, survey_id, key,
                         str(value) if value is not None else None))

        if not values_to_insert:
            return True, "Nenhuma pergunta mapeada encontrada nos dados dos respondentes."

        # 3. Inserir os dados na tabela consolidada usando ON CONFLICT
        # Isso garante que se o processo for executado novamente, ele não criará duplicatas, apenas atualizará os dados existentes.
        query = sql.SQL("""
            INSERT INTO consolidated_data (respondent_id, survey_id, question_code, answer_value)
            VALUES %s
            ON CONFLICT (respondent_id, survey_id, question_code)
            DO UPDATE SET answer_value = EXCLUDED.answer_value;
        """)

        # psycopg2.extras.execute_values é otimizado para inserções em lote
        execute_values(cursor, query, values_to_insert)

        # 4. Atualizar a tabela de log com as métricas
        log_query = sql.SQL("""
            INSERT INTO consolidation_log (survey_id, last_consolidated_at, unique_questions_consolidated)
            VALUES (%s, NOW(), %s)
            ON CONFLICT (survey_id)
            DO UPDATE SET 
                last_consolidated_at = NOW(),
                unique_questions_consolidated = EXCLUDED.unique_questions_consolidated;
        """)
        cursor.execute(log_query,
                       (survey_id, len(questions_found_in_this_run)))

        conn.commit()
        return True, f"Consolidação bem-sucedida. {len(values_to_insert)} registros processados. {len(questions_found_in_this_run)} perguntas únicas."

    except Exception as e:
        conn.rollback()
        return False, f"Erro durante a consolidação: {e}"
    finally:
        cursor.close()


def get_consolidation_log() -> pd.DataFrame:
    """
    Busca os dados de log da consolidação e junta com o nome da pesquisa para exibição.
    """
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()

    query = """
        SELECT 
            s.survey_id,
            s.research_name,
            cl.last_consolidated_at,
            cl.unique_questions_consolidated
        FROM surveys s
        LEFT JOIN consolidation_log cl ON s.survey_id = cl.survey_id
        ORDER BY s.creation_date DESC;
    """
    try:
        df = pd.read_sql_query(query, conn)
        return df
    except Exception:
        return pd.DataFrame()


def get_consolidated_data(limit: int = 1000) -> pd.DataFrame:
    """
    Busca os dados da tabela consolidada, com um limite de linhas.
    """
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()

    # A cláusula LIMIT torna a busca muito mais rápida e eficiente para uma visualização inicial.
    query = "SELECT * FROM consolidated_data ORDER BY id DESC LIMIT %s;"

    try:
        df = pd.read_sql_query(query, conn, params=(limit, ))
        return df
    except Exception as e:
        st.error(f"Erro ao buscar dados consolidados: {e}")
        return pd.DataFrame()


def update_survey_stats(survey_id: int, collected_count: int,
                        expected_total: int) -> bool:
    """
    Atualiza as estatísticas de coleta (contagem e percentual) na tabela 'surveys'.
    """
    conn = get_db_connection()
    if conn is None: return False

    # Calcula o percentual, tratando o caso de divisão por zero
    percentage = 0
    if expected_total and expected_total > 0:
        percentage = (collected_count / expected_total) * 100

    cursor = conn.cursor()
    try:
        cursor.execute(
            sql.SQL("""
                UPDATE surveys
                SET
                    collected_count = %s,
                    collected_percentage = %s,
                    last_fetched = NOW()
                WHERE survey_id = %s;
            """), (collected_count, percentage, survey_id))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Erro em update_survey_stats: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()


def get_all_consolidated_data() -> pd.DataFrame:
    """
    Busca TODOS os dados da tabela consolidada.
    """
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()

    query = "SELECT * FROM consolidated_data ORDER BY id;"

    try:
        df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        st.error(f"Erro ao buscar todos os dados consolidados: {e}")
        return pd.DataFrame()


def get_surveys_with_recent_new_data(limit_surveys: int = 5) -> list:
    """
    Busca os IDs das pesquisas com os dados de respondentes mais recentes,
    indicando atividade de coleta recente.
    """
    conn = get_db_connection()
    if conn is None: return []

    # Esta query agrupa os respondentes por pesquisa, encontra a data mais recente
    # de coleta para cada uma, e ordena para pegar as pesquisas mais ativas.
    query = """
        SELECT survey_id
        FROM survey_respondent_data
        GROUP BY survey_id
        ORDER BY MAX(fetched_at) DESC
        LIMIT %s;
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query, (limit_surveys, ))
        survey_ids = [row[0] for row in cursor.fetchall()]
        return survey_ids
    except Exception as e:
        print(f"Erro ao buscar pesquisas com dados recentes: {e}")
        return []
    finally:
        if 'cursor' in locals() and not cursor.closed:
            cursor.close()


def get_consolidated_data_for_surveys(survey_ids: list) -> pd.DataFrame:
    """
    Busca todos os dados consolidados para uma lista específica de survey_ids.
    """
    conn = get_db_connection()
    if conn is None or not survey_ids:
        return pd.DataFrame()

    # A cláusula "WHERE survey_id = ANY(%s)" é uma forma eficiente de buscar múltiplos IDs
    query = "SELECT * FROM consolidated_data WHERE survey_id = ANY(%s) ORDER BY id DESC;"

    try:
        # Passamos a lista de IDs como um único parâmetro
        df = pd.read_sql_query(query, conn, params=(survey_ids, ))
        return df
    except Exception as e:
        st.error(f"Erro ao buscar dados consolidados por pesquisa: {e}")
        return pd.DataFrame()


def get_updatable_surveys() -> pd.DataFrame:
    """
    Busca apenas as pesquisas que são consideradas "em campo",
    excluindo aquelas que já atingiram 99% ou mais da meta de coleta.
    """
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()

    try:
        # Query CORRIGIDA: Removida a coluna e o filtro 'is_active'.
        query = """
            SELECT 
                survey_id, 
                research_name, 
                creation_date, 
                api_link, 
                expected_total,
                collected_count,
                collected_percentage,
                last_fetched
            FROM surveys 
            WHERE 
                (collected_percentage < 99.00 OR collected_percentage IS NULL)
            ORDER BY creation_date DESC;
        """
        df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        st.error(f"Erro detalhado ao buscar pesquisas atualizáveis: {e}")
        return pd.DataFrame()


def resync_full_survey(survey_id: int, api_link: str) -> tuple[bool, str]:
    """
    Executa uma re-sincronização completa para uma única pesquisa.
    Isso envolve deletar todos os dados antigos e re-ingerir tudo do zero
    a partir da API. A operação inteira é feita em uma única transação.
    """

    conn = get_db_connection()
    if conn is None:
        return False, "Falha na conexão com o banco de dados."

    # Tabelas das quais os dados da pesquisa serão deletados, em ordem
    tables_to_delete_from = [
        "analytics_respondents",  # Se já estiver em uso
        "consolidated_data",
        "consolidation_log",
        "survey_respondent_data"
    ]

    cursor = conn.cursor()
    try:
        # --- PARTE 1: DELETAR DADOS ANTIGOS ---
        st.write(
            f"Iniciando re-sincronização para survey_id: {survey_id}. Removendo dados antigos..."
        )
        for table in tables_to_delete_from:
            try:
                query = sql.SQL("DELETE FROM {table} WHERE survey_id = %s"
                                ).format(table=sql.Identifier(table))
                cursor.execute(query, (survey_id, ))
                st.write(f"  - Registros de '{table}' removidos.")
            except psycopg2.errors.UndefinedTable:
                # Ignora o erro se a tabela ainda não existir (ex: analytics_respondents)
                st.write(f"  - Tabela '{table}' não encontrada, pulando.")
                pass

        # --- PARTE 2: RE-INGERIR E PROCESSAR NOVOS DADOS ---
        st.write("Buscando dados atualizados da API...")
        raw_data_list = fetch_data_from_api(api_link)
        if raw_data_list is None or not raw_data_list:
            raise ValueError(
                "Falha ao buscar dados da API ou a API não retornou dados.")

        st.write("Mapeando colunas e salvando novos dados dos respondentes...")
        mapped_data_list, _ = map_api_columns_to_target_codes(raw_data_list)
        success, num_added, warn_msg = store_respondent_data(
            survey_id, mapped_data_list)
        if not success:
            raise Exception(
                f"Falha ao armazenar dados dos respondentes: {warn_msg}")

        st.write("Consolidando dados...")
        consol_success, consol_msg = consolidate_survey_data(survey_id)
        if not consol_success:
            raise Exception(f"Falha ao consolidar dados: {consol_msg}")

        st.write("Atualizando estatísticas...")
        survey_df = get_all_surveys(
        )  # Pega os dados atualizados para o expected_total
        expected_total = survey_df.loc[survey_df['survey_id'] == survey_id,
                                       'expected_total'].iloc[0]
        update_survey_stats(survey_id, num_added, int(expected_total or 0))

        # Se tudo deu certo, salva a transação permanentemente
        conn.commit()
        return True, f"Re-sincronização da pesquisa (ID: {survey_id}) concluída com sucesso. {num_added} registros processados."

    except Exception as e:
        # Se qualquer passo falhar, desfaz todas as operações
        conn.rollback()
        return False, f"Falha na re-sincronização: {e}"
    finally:
        cursor.close()


# Em src/database.py


def save_analytics_data(df: pd.DataFrame) -> tuple[bool, str]:
    """
    Versão final que lida com valores NaN antes de salvar na tabela de analytics.
    Usa 'ON CONFLICT' para atualizar registros existentes (UPSERT).
    """
    conn = get_db_connection()
    if conn is None: return False, "Falha na conexão com o banco de dados."
    if df.empty: return True, "Nenhum dado para salvar na tabela de analytics."

    # --- LINHA DE CORREÇÃO CRUCIAL ---
    # Converte todos os NaN (Not a Number) do Pandas para None do Python.
    # O Python None é corretamente traduzido para o NULL do SQL pela biblioteca do banco.
    # Isso resolve o erro 'integer out of range' que era causado pela má interpretação do NaN.
    df = df.astype(object).where(pd.notna(df), None)

    # O resto da função continua exatamente como antes
    cols = df.columns.tolist()
    conflict_cols = ['respondent_id', 'survey_id']
    update_cols = [col for col in cols if col not in conflict_cols]

    values = [tuple(row) for row in df.to_numpy()]

    query = sql.SQL("""
        INSERT INTO analytics_respondents ({fields})
        VALUES %s
        ON CONFLICT ({conflict_fields})
        DO UPDATE SET
            {update_fields};
    """).format(fields=sql.SQL(', ').join(map(sql.Identifier, cols)),
                conflict_fields=sql.SQL(', ').join(
                    map(sql.Identifier, conflict_cols)),
                update_fields=sql.SQL(', ').join(
                    sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(col),
                                                       sql.Identifier(col))
                    for col in update_cols))

    cursor = conn.cursor()
    try:
        execute_values(cursor, query, values)
        conn.commit()
        return True, f"{len(values)} registros salvos/atualizados na tabela de analytics."
    except Exception as e:
        conn.rollback()
        return False, f"Erro ao salvar na tabela de analytics: {e}"
    finally:
        cursor.close()


def check_api_link_exists(api_link: str) -> str | None:
    """
    Verifica se um link de API já existe na tabela 'surveys'.
    Retorna o nome da pesquisa conflitante se encontrar, caso contrário, retorna None.
    """
    conn = get_db_connection()
    if conn is None:
        # Se não há conexão com o DB, não podemos verificar, então permitimos a passagem
        # para não bloquear o usuário, mas logamos um erro.
        print(
            "AVISO: Não foi possível conectar ao DB para verificar a existência do link da API."
        )
        return None

    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT research_name FROM surveys WHERE api_link = %s LIMIT 1;",
            (api_link, ))
        result = cursor.fetchone()
        # Se encontrou um resultado, retorna o nome da pesquisa (result[0])
        return result[0] if result else None
    except Exception as e:
        print(f"Erro ao verificar link da API: {e}")
        return None  # Em caso de erro, permite a passagem para não bloquear o usuário.
    finally:
        cursor.close()


def get_analytics_data() -> pd.DataFrame:
    """
    Busca todos os dados da tabela final de análise 'analytics_respondents'.
    """
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()

    query = "SELECT * FROM analytics_respondents;"

    try:
        df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        # Se a tabela ainda não existir, não queremos que o app quebre
        if "relation \"analytics_respondents\" does not exist" in str(e):
            return pd.DataFrame()
        else:
            st.error(f"Erro ao buscar dados de análise: {e}")
            return pd.DataFrame()


# Fim
