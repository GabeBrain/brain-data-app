# src/data_ingestion.py

import streamlit as st
import requests
import pandas as pd
import io
import numpy as np 

@st.cache_data(ttl=3600)
def fetch_data_from_api(api_url: str) -> list | None:
    """
    Tenta buscar dados de uma URL de API que retorna CSV/TSV.
    Não exibe mensagens no Streamlit diretamente.

    Returns:
        list: Lista de dicionários com os dados.
        []: Se a API retornar um arquivo vazio ou malformado.
        None: Se houver um erro grave na requisição (rede, status HTTP ruim).
    """
    try:
        response = requests.get(api_url)
        response.raise_for_status()

        csv_data = io.StringIO(response.text)

        # ETAPA 1: Leitura correta do arquivo usando o separador de tabulação.
        df = pd.read_csv(csv_data, sep='\t')

        # ETAPA 2: Sanitização dos dados.
        # Substitui todos os valores NaN (nativos do numpy/pandas) por None (nativo do Python).
        # O 'None' do Python será corretamente convertido para 'null' no JSON.
        df = df.replace({np.nan: None})

        return df.to_dict(orient='records')

    except requests.exceptions.RequestException:
        return None # Erro de requisição
    except pd.errors.EmptyDataError:
        return [] # CSV vazio
    except Exception:
        return None # Outro erro ao processar CSV