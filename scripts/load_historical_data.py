# scripts/load_historical_data.py
import pandas as pd
import psycopg2
import sys
import numpy as np
import datetime
from psycopg2.extras import execute_values
from pathlib import Path

# Adiciona o diretório raiz ao path para que possamos importar 'src'
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))
from src.data_processing import (  # noqa: E402
    categorize_generation, reclassificar_idade, classify_cidade,
    map_estado_to_regiao, map_uf_to_estado_nome, padronizar_resposta,
    calcular_media_faixa, classificar_faixa_antiga, map_renda_to_macro_faixa,
    load_classification_rules, classify_income_by_rules, 
    MAPA_INTENCAO_COMPRA, MAPA_TEMPO_INTENCAO
)
# Carregue suas credenciais (pode ser de um .env ou direto aqui para este script único)
DB_HOST = "aws-0-us-east-2.pooler.supabase.com"
DB_PORT = "6543"
DB_NAME = "postgres"
DB_USER = "postgres.nscdlmklgfbkiqfakptp"
DB_PASSWORD = "qI1guAb7RUvggOtv"

# --- NOVA FUNÇÃO DE PARSING DE DATA ---
def parse_flexible_date(date_obj):
    """
    Tenta converter um objeto para data de forma flexível.
    Lida com strings, NaNs, e o texto '-'.
    """
    if pd.isna(date_obj):
        return pd.NaT
    
    # Converte para string e limpa espaços extras
    date_str = str(date_obj).strip()
    
    if date_str in ('-', '', 'nan'):
        return pd.NaT
        
    # Tenta o formato DD/MM/YYYY (comum no Brasil)
    try:
        return datetime.datetime.strptime(date_str, '%d/%m/%Y')
    except ValueError:
        pass
        
    # Tenta o formato MM/DD/YYYY (comum nos EUA)
    try:
        return datetime.datetime.strptime(date_str, '%m/%d/%Y')
    except ValueError:
        pass
        
    # Tenta deixar o Pandas inferir (pega formatos como YYYY-MM-DD)
    try:
        return pd.to_datetime(date_str)
    except (ValueError, TypeError):
        pass
        
    # Se nada funcionar, retorna Nulo
    return pd.NaT

def run_etl(load=True):
    print("Iniciando processo de ETL para dados históricos...")
    
    # --- EXTRACT ---
    print("1. Lendo o arquivo CSV...")
    df = pd.read_csv("scripts/base2124_v24abr - Base.csv")
    
    # --- TRANSFORM ---
    print("2. Transformando os dados...")

    # Mapeamento de colunas (de-para)
    print("   - Mapeando nomes de colunas...")
    column_mapping = {
        "Código": "respondent_id", "NomeEstudo": "research_name",
        "Fim": "data_pesquisa", "FE2P5": "idade_original",
        "FE2P10": "renda_texto_original", "Estado": "estado_original",
        "Município": "cidade_original", "FE2P3": "genero",
        "IC4P30": "intencao_compra_original",
        "IC4P32": "tempo_intencao_original"
    }
    df.rename(columns=column_mapping, inplace=True)

    # Criando 'survey_id' a partir do nome do estudo
    print("   - Gerando survey_id a partir do nome do estudo...")
    df['research_name'] = df['research_name'].astype('category')
    df['survey_id'] = df['research_name'].cat.codes + 1000

    # --- NOVA LÓGICA DE IMPUTAÇÃO (VERSÃO 3.0 - DISTRIBUIÇÃO MENSAL) ---
    print("   - Iniciando imputação com DISTRIBUIÇÃO MENSAL para registros de 2022...")
    
    mask_problema = (df['data_pesquisa'] == '-') & (df['ano_pesquisa'] == 2022)
    registros_para_imputar = df[mask_problema]
    num_registros = len(registros_para_imputar)
    
    if num_registros > 0:
        print(f"   - Encontrados {num_registros} registros de 2022 sem data para imputar.")
        
        # 1. Calcula a distribuição base por mês
        registros_por_mes = num_registros // 12
        registros_restantes = num_registros % 12
        
        datas_imputadas_final = []
        
        # 2. Itera sobre cada mês de 2022
        for mes in range(1, 13):
            # Adiciona 1 aos primeiros meses para distribuir o resto
            num_neste_mes = registros_por_mes + (1 if mes <= registros_restantes else 0)
            
            # Pega o primeiro e o último dia do mês
            primeiro_dia = datetime.date(2022, mes, 1)
            ultimo_dia_mes = (datetime.date(2022, mes % 12 + 1, 1) - datetime.timedelta(days=1)) if mes < 12 else datetime.date(2022, 12, 31)
            
            # Gera uma lista de dias úteis para aquele mês
            dias_uteis_no_mes = pd.bdate_range(start=primeiro_dia, end=ultimo_dia_mes)
            
            if not dias_uteis_no_mes.empty:
                # 3. Sorteia N datas dentro dos dias úteis do mês
                datas_sorteadas = np.random.choice(dias_uteis_no_mes, size=num_neste_mes, replace=True)
                datas_imputadas_final.extend(datas_sorteadas)

        # 4. Embaralha a lista final e atribui aos registros
        np.random.shuffle(datas_imputadas_final)
        df.loc[mask_problema, 'data_pesquisa'] = datas_imputadas_final

        print(f"   - Imputação de {len(datas_imputadas_final)} datas distribuídas mensalmente concluída.")

    else:
        print("   - Nenhum registro de 2022 com data ausente ('-') encontrado.")

    print("   - Processando e padronizando colunas...")
    # SUBSTITUÍDO: Usando a nova função de conversão robusta
    print("   - Convertendo datas com a nova função flexível...")
    df['data_pesquisa'] = df['data_pesquisa'].apply(parse_flexible_date)

    # Criando colunas derivadas (usando nossas funções existentes)
    print("   - Processando e padronizando colunas...")
    df['data_pesquisa'] = pd.to_datetime(df['data_pesquisa'], errors='coerce', format='%m/%d/%Y')
    df['idade_numerica'] = pd.to_numeric(df['idade_original'], errors='coerce')
    df['geracao'] = df['idade_numerica'].apply(categorize_generation)  # noqa: F405
    df['faixa_etaria'] = df['idade_numerica'].apply(reclassificar_idade)
    df['regiao'] = df['estado_original'].apply(map_estado_to_regiao)
    df['estado_nome'] = df['estado_original'].apply(map_uf_to_estado_nome)
    df['localidade'] = df['cidade_original'].apply(classify_cidade)

    # --- BLOCO DE TRANSFORMAÇÃO CORRIGIDO E COMPLETO ---

    # 1. Padrão de Intenção de Compra (que estava faltando)
    df['intencao_compra_padronizada'] = df['intencao_compra_original'].apply(lambda x: padronizar_resposta(x, MAPA_INTENCAO_COMPRA))
    df['tempo_intencao_padronizado'] = df['tempo_intencao_original'].apply(lambda x: padronizar_resposta(x, MAPA_TEMPO_INTENCAO))

    # 2. Padrão de Renda (agora incluindo TODAS as colunas)
    df['renda_valor_estimado'] = df['renda_texto_original'].apply(calcular_media_faixa)
    df['renda_faixa_padronizada'] = df['renda_valor_estimado'].apply(classificar_faixa_antiga)
    df['renda_macro_faixa'] = df['renda_faixa_padronizada'].apply(map_renda_to_macro_faixa)

    # Carrega as regras de classificação para usar na próxima etapa
    regras_de_renda = load_classification_rules()
    # Aplica a nova função de classificação baseada em regras e data
    resultados_renda = df.apply(lambda row: classify_income_by_rules(
        row['renda_valor_estimado'], row['data_pesquisa'], regras_de_renda),
        axis=1)
    df[['renda_classe_agregada', 'renda_classe_detalhada']] = pd.DataFrame(resultados_renda.tolist(), index=df.index)

    # 3. Preenchendo colunas restantes que não temos no CSV
    for col in ['latitude', 'longitude']:
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
    print("   - Transformação concluída.\n")

    print("\n--- RELATÓRIO DE QUALIDADE (Valores Nulos) ---")
    null_counts = df_final.isnull().sum()
    null_counts = null_counts[null_counts > 0].sort_values(ascending=False)
    
    if not null_counts.empty:
        print("   - Contagem de valores nulos por coluna (apenas colunas com nulos):")
        # Imprime o dataframe de nulos como uma string formatada
        print(null_counts.to_string())
    else:
        print("   - Ótima notícia! Nenhuma coluna possui valores nulos após a transformação.")


    print("\n--- RELATÓRIO DE DISTRIBUIÇÃO TEMPORAL ---")
    # Filtra apenas os registros que têm uma data válida após o processamento
    df_dates = df_final.dropna(subset=['data_pesquisa']).copy()
    
    if not df_dates.empty:
        df_dates['data_pesquisa'] = pd.to_datetime(df_dates['data_pesquisa'])
        
        print("\n   - Contagem de coletas por Ano:")
        yearly_counts = df_dates['data_pesquisa'].dt.year.value_counts().sort_index()
        print(yearly_counts.to_string())
        
        print("\n   - Contagem de coletas por Trimestre:")
        quarterly_counts = df_dates['data_pesquisa'].dt.to_period('Q').value_counts().sort_index()
        print(quarterly_counts.to_string())

        print("\n   - Contagem de coletas por Mês:")
        monthly_counts = df_dates['data_pesquisa'].dt.to_period('M').value_counts().sort_index()
        print(monthly_counts.to_string())
    else:
        print("   - Nenhuma data válida encontrada para gerar o relatório de distribuição.")



    print("\n--- FASE DE CARGA ---")
    if not load:
        print("\nInterrompida | Cenário de análise")
    
    else:
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