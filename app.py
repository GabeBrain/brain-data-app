# app.py

import streamlit as st
import os
from src.database import get_db_connection, init_db_schema  # Adiciona init_db_schema

# --- Configuração da Página Streamlit ---
st.set_page_config(layout="wide",
                   page_title="Brain | Controle de Coleta Quant",
                   page_icon="🧠")

# Adiciona a logo da Brain na barra lateral
st.logo("assets/logoBrain.png")

# Título principal da aplicação
st.title("Brain | Controle de Coleta Quant")

# --- Verificação de Credenciais e Conexão com o Banco de Dados ---
db_secrets_present = all([
    os.environ.get("DB_HOST"),
    os.environ.get("DB_PORT"),
    os.environ.get("DB_NAME"),
    os.environ.get("DB_USER"),
    os.environ.get("DB_PASSWORD")
])

if not db_secrets_present:
    st.error(
        "CRITICAL FAILURE: As credenciais do banco de dados não foram encontradas. Configure as 'Secrets' no ambiente de desenvolvimento."
    )
    st.stop()

# Tenta conectar ao banco de dados e exibe o status
try:
    # Apenas chama a função para forçar a conexão e o cache
    get_db_connection()
    # Inicializa o schema do DB, o que também valida a conexão
    init_db_schema()  #

    # MENSAGEM DE SUCESSO (Layout Padrão)
    st.success(
        "Conexão com o Data Warehouse estabelecida com sucesso. Sistema de monitoramento online e operacional.",
        icon="🌐")

    st.markdown("---")
    st.markdown("""
    Bem-vindo ao **Quanti Um**, a plataforma central de inteligência e controle de dados de pesquisa da Brain. \n
    Este sistema integra, processa e analisa dados de campo em tempo real, transformando informações brutas em dados consolidados e enriquecidos.

    Navegue pelo menu lateral para acessar os módulos do sistema.
    """)

    st.markdown("---")
    st.header("Módulos Operacionais")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📊 Análise & Dashboards")
        st.markdown("""
        - **Dashboard de Análise:** Explore interativamente os perfis dos respondentes com filtros dinâmicos e visualizações personalizadas.
        - **Dashboard de Controle:** Monitore a performance da coleta em campo com mapas de calor geoespaciais e cronogramas de produtividade.
        """)
    with col2:
        st.subheader("🛠️ Gestão & Estratégia")
        st.markdown("""
        - **Gerenciar Pesquisas:** Administre o ciclo de vida das pesquisas, desde o cadastro até a ingestão contínua de dados via API.
        - **Gerador de Amostra:** Planeje e extraia amostras estatísticas, com análise de viabilidade, relatórios de desvio e planos de coleta otimizados.
        - **Manutenção e Admin:** Execute pipelines de processamento e garanta a integridade e consistência do Data Warehouse.
        """)

    st.markdown("---")
    st.info(
        "Para iniciar, selecione um módulo no menu de navegação à esquerda.",
        icon="👈")

except Exception as e:
    # LAYOUT PARA FALHA DE CONEXÃO
    st.error(
        "Falha na Conexão com o Data Warehouse. A plataforma não pode ser iniciada.",
    )
    st.markdown("---")

    with st.container(border=True):
        st.subheader("Diagnóstico do Problema")
        st.markdown("""
        A aplicação não conseguiu estabelecer uma comunicação com o banco de dados. Isso geralmente ocorre por uma das seguintes razões, especialmente ao usar um provedor como o **Supabase**:
        """)

        st.markdown("""
        - **Projeto Pausado:** Projetos no plano gratuito do Supabase são pausados após um período de inatividade.
        - **Credenciais Incorretas:** As informações de Host, Porta, Usuário ou Senha nas 'Secrets' do ambiente podem estar erradas.
        - **Instabilidade no Provedor:** O serviço do Supabase pode estar passando por uma instabilidade momentânea.
        """)

        st.markdown("---")

        st.subheader("Ações Recomendadas")
        st.markdown("""
        1.  **Verifique seu Painel Supabase:** Acesse sua conta no [site do Supabase](https://supabase.com/) e verifique se o seu projeto está ativo ("Active") e não "Paused". Se estiver pausado, clique para reativá-lo.
        2.  **Valide as Credenciais:** Confirme se as `Secrets` no seu ambiente de desenvolvimento correspondem exatamente às credenciais de conexão do seu banco de dados no Supabase.
        3.  **Consulte o Status do Serviço:** Verifique a página de status oficial do Supabase ([status.supabase.com](https://status.supabase.com/)) para descartar uma interrupção geral do serviço.
        """)

        st.info(f"**Erro Técnico Detalhado:**\n`{e}`")

    st.stop()
