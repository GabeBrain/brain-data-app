# scripts/extract_full_dataset.py
import pandas as pd
import psycopg2
from pathlib import Path

# ATENÇÃO: Preencha suas credenciais do Supabase aqui
DB_HOST = "aws-0-us-east-2.pooler.supabase.com"
DB_PORT = "6543"
DB_NAME = "postgres"
DB_USER = "postgres.nscdlmklgfbkiqfakptp"
DB_PASSWORD = "qI1guAb7RUvggOtv" # <-- COLOQUE SUA SENHA AQUI

# Define o nome do arquivo de saída
OUTPUT_FILENAME = "full_dataset_2021_2025.csv"
OUTPUT_PATH = Path(__file__).parent.parent / OUTPUT_FILENAME

def extract_data():
    """
    Conecta ao banco de dados, extrai os dados unificados e salva como CSV.
    """
    print("Iniciando extração de dados do banco de dados...")
    
    conn = None
    try:
        # --- 1. Conectar ao Banco ---
        print("   - Conectando ao Supabase...")
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        print("   - Conexão bem-sucedida.")

        # --- 2. Definir a Query ---
        # A mesma query que une os dados de 2025 (live) com os dados históricos
        query = """
            SELECT * FROM analytics_respondents
            UNION ALL
            SELECT * FROM analytics_respondents_historical;
        """
        print("   - Executando a query de união...")
        
        # --- 3. Executar a Query e Carregar no Pandas ---
        df = pd.read_sql_query(query, conn)
        print(f"   - Consulta concluída. {len(df)} registros encontrados.")

        # --- 4. Salvar o Arquivo CSV ---
        print(f"   - Salvando dados no arquivo: {OUTPUT_FILENAME}...")
        df.to_csv(OUTPUT_PATH, index=False, encoding='utf-8-sig')
        print(f"\n✅ Sucesso! O arquivo '{OUTPUT_FILENAME}' foi criado na pasta raiz do seu projeto.")

    except psycopg2.OperationalError as e:
        print("\n❌ ERRO DE CONEXÃO: Não foi possível conectar ao banco de dados. Verifique suas credenciais.")
        print(f"   - Detalhe: {e}")
    except Exception as e:
        print(f"\n❌ Ocorreu um erro inesperado: {e}")
    finally:
        if conn:
            conn.close()
            print("\n   - Conexão com o banco de dados fechada.")

if __name__ == "__main__":
    extract_data()