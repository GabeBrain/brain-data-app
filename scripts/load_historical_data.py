# scripts/load_historical_data.py
import pandas as pd
import psycopg2
import os
from psycopg2.extras import execute_values
from urllib.parse import urlparse
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path para que possamos importar 'src'
sys.path.append(str(Path(__file__).parent.parent))
from src.data_processing import (
    categorize_generation, reclassificar_idade, classify_cidade,
    map_estado_to_regiao, map_uf_to_estado_nome
)

# Carregue suas credenciais (pode ser de um .env ou direto aqui para este script único)
DB_HOST = "aws-0-us-east-2.pooler.supabase.com"
DB_PORT = "6543"
DB_NAME = "postgres"
DB_USER = "postgres.nscdlmklgfbkiqfakptp"
DB_PASSWORD = "qI1guAb7RUvggOtv"

def run_etl():
    print("Iniciando processo de ETL para dados históricos...")
    
    # --- EXTRACT ---
    print("1. Lendo o arquivo CSV...")
    df = pd.read_csv("scripts/base2124_v24abr - Base.csv")
    
    # --- TRANSFORM ---
    print("2. Transformando os dados...")
    
    # Mapeamento de colunas (de-para)
    column_mapping = {
        "Código": "respondent_id",
        "NomeEstudo": "research_name",
        "Fim": "data_pesquisa",
        "FE2P5": "idade_original",
        "FE2P10": "renda_texto_original",
        "Estado": "estado_original",
        "Município": "cidade_original",
        "FE2P3": "genero",
        # Adicione outros mapeamentos diretos aqui...
    }
    df.rename(columns=column_mapping, inplace=True)

    # Criando 'survey_id' a partir do nome do estudo
    df['research_name'] = df['research_name'].astype('category')
    df['survey_id'] = df['research_name'].cat.codes + 1000 # +1000 para não conflitar com IDs existentes

    # Criando colunas derivadas (usando nossas funções existentes)
    df['data_pesquisa'] = pd.to_datetime(df['data_pesquisa'], errors='coerce', format='%m/%d/%Y')
    df['idade_numerica'] = pd.to_numeric(df['idade_original'], errors='coerce')
    df['geracao'] = df['idade_numerica'].apply(categorize_generation)
    df['faixa_etaria'] = df['idade_numerica'].apply(reclassificar_idade)
    df['regiao'] = df['estado_original'].apply(map_estado_to_regiao)
    df['estado_nome'] = df['estado_original'].apply(map_uf_to_estado_nome)
    df['localidade'] = df['cidade_original'].apply(classify_cidade)
    # Deixando colunas que não temos como nulas
    for col in ['latitude', 'longitude', 'renda_valor_estimado', 'renda_faixa_padronizada', 'renda_macro_faixa', 'renda_classe_agregada', 'renda_classe_detalhada', 'intencao_compra_padronizada', 'tempo_intencao_padronizado', 'intencao_compra_original', 'tempo_intencao_original']:
        if col not in df.columns:
            df[col] = None

    # Selecionar e ordenar colunas para corresponder à tabela do DB
    final_cols = [
        'respondent_id', 'survey_id', 'research_name', 'data_pesquisa', 'idade_original', 'idade_numerica',
        'geracao', 'faixa_etaria', 'renda_texto_original', 'renda_valor_estimado', 'renda_faixa_padronizada',
        'renda_macro_faixa', 'renda_classe_agregada', 'renda_classe_detalhada', 'cidade_original', 'localidade',
        'estado_original', 'estado_nome', 'regiao', 'intencao_compra_original', 'intencao_compra_padronizada',
        'tempo_intencao_original', 'tempo_intencao_padronizado', 'genero', 'latitude', 'longitude'
    ]
    df_final = df[final_cols]
    
    # --- LOAD ---
    df_final = df_final.astype(object).where(pd.notna(df_final), None)

    print(f"3. Carregando {len(df_final)} registros para o banco de dados...")
    conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD)
    cursor = conn.cursor()
    
    try:
        # Usando execute_values para uma inserção em massa de alta performance
        values = [tuple(row) for row in df_final.to_numpy()]
        cols_sql = ','.join(f'"{c}"' for c in df_final.columns)
        
        query = f"INSERT INTO analytics_respondents_historical ({cols_sql}) VALUES %s"
        execute_values(cursor, query, values)
        
        conn.commit()
        print(f"✅ Sucesso! {cursor.rowcount} registros inseridos em 'analytics_respondents_historical'.")
    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao carregar dados: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_etl()