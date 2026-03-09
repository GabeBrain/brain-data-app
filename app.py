# app.py

import streamlit as st
import logging
import sys
import traceback

# --- Bloco de Diagnóstico e Logging ---
# Configura o logging para imprimir no console (que aparece no log do Streamlit Cloud)
logging.basicConfig(
    level=logging.INFO, 
    stream=sys.stdout, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logging.info("--- INICIANDO EXECUÇÃO DO SCRIPT app.py ---")

# Importa as funções do banco de dados DEPOIS de configurar o logging
try:
    from src.database import init_db_schema
    logging.info("Importação de 'init_db_schema' bem-sucedida.")
except ImportError as e:
    logging.error(f"FALHA CRÍTICA na importação: {e}")
    st.error(f"Não foi possível importar funções essenciais. Verifique o arquivo src/database.py. Erro: {e}")
    st.stop() # Interrompe a execução se a importação falhar

# --- Inicialização do Banco de Dados com Captura de Erro ---
try:
    logging.info("Tentando inicializar o schema do banco de dados...")
    init_db_schema()
    logging.info("Verificação/Inicialização do schema do banco de dados concluída com sucesso.")
except Exception as e:
    # Se a inicialização do DB falhar, exibe o erro completo e interrompe
    logging.error("FALHA CRÍTICA ao inicializar o schema do banco de dados.")
    
    # Pega o traceback completo para depuração máxima
    tb_str = traceback.format_exc()
    logging.error(tb_str)
    
    st.error("Ocorreu um erro crítico durante a inicialização da conexão com o banco de dados.")
    st.error("Isso geralmente é causado por 'Secrets' (credenciais) incorretos ou problemas de rede.")
    st.code(tb_str) # Exibe o erro técnico completo na tela
    st.stop() # Interrompe a execução

# --- Conteúdo da Página Principal ---

st.set_page_config(
    layout="wide",
    page_title="Página Inicial | App de Análise de Pesquisas",
    page_icon="🧠"
)
st.logo("assets/logoBrain.png")

logging.info("Renderizando a página principal do Streamlit...")

st.title("🧠 Bem-vindo ao App de Análise de Pesquisas")
st.markdown("---")
st.header("Visão Geral do Projeto")
st.markdown("""
Esta aplicação foi desenvolvida para automatizar o ciclo de vida dos dados de pesquisas de mercado, desde a ingestão via API até a análise e geração de amostras estratégicas.

**Utilize o menu lateral para navegar entre as funcionalidades:**

- **`Gerenciar Pesquisas`**: Adicione, edite e atualize os dados de novas pesquisas.
- **`Análise Consolidada`**: Explore as respostas brutas e a saúde da consolidação dos dados.
- **`Dashboard de Análise`**: Visualize os dados de forma interativa com filtros dinâmicos.
- **`Dashboard de Controle`**: Monitore o andamento da coleta de campo.
- **`Gerador de Amostra`**: Crie planos de amostragem e extraia amostras otimizadas.
- **`Bases Unificadas`**: Exporte bases completas por filtros, sem amostragem.
- **`Manutenção e Admin`**: Ferramentas para administradores do sistema.
""")

logging.info("--- RENDERIZAÇÃO DA PÁGINA CONCLUÍDA ---")
