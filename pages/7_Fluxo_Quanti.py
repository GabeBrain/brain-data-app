# pages/7_Fluxo_Quanti.py

import streamlit as st
import streamlit.components.v1 as components
import os

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Fluxos de Trabalho")
st.logo("assets/logoBrain.png")

# --- Título e Descrição ---
st.title("🌊 Fluxos de Trabalho da Área Quantitativa")
st.markdown(
    "Representações visuais dos processos e cronogramas da área."
)

# --- Função auxiliar para carregar e renderizar os arquivos HTML ---
def render_html(file_name: str, height: int):
    """
    Lê um arquivo HTML da raiz do projeto e o renderiza em um componente do Streamlit.
    """
    try:
        # Constrói o caminho para o arquivo HTML na pasta raiz do projeto
        path_to_html = os.path.join(os.path.dirname(__file__), '..', file_name)
        
        # Lê o conteúdo do arquivo
        with open(path_to_html, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        # Exibe o componente no Streamlit
        components.html(html_content, height=height, scrolling=True)

    except FileNotFoundError:
        st.error(
            f"O arquivo '{file_name}' não foi encontrado. "
            f"Certifique-se de que ele está na pasta raiz do projeto."
        )
    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar a visualização '{file_name}': {e}")


# --- Criação das 3 Abas para cada Visualização ---
tab1, tab2, tab3 = st.tabs([
    "Fluxo de Projeto (Kanban)", 
    "Cronograma Jotform", 
    "Fluxo de Projeto (Timeline)"
])

# --- Conteúdo da Aba 1: Fluxo Kanban com Filtros ---
with tab1:
    st.subheader("Visão Geral do Fluxo por Fases com Filtro de Responsáveis")
    # Chama a função para renderizar o arquivo HTML correspondente
    render_html(file_name="fluxo_quanti_filtro.html", height=1200)

# --- Conteúdo da Aba 2: Cronograma de Implementação Jotform ---
with tab2:
    st.subheader("Cronograma de Atividades: Implementação de Ferramentas de Coleta (Jotform)")
    # Chama a função para renderizar o novo arquivo HTML
    render_html(file_name="fluxo_jotform.html", height=800)

# --- Conteúdo da Aba 3: Fluxo Horizontal (Timeline) ---
with tab3:
    st.subheader("Linha do Tempo Vertical do Projeto")
    # Chama a função para renderizar o arquivo HTML original
    # Nota: O seu código original chamava esta de "Linha do Tempo Vertical", corrigi o título.
    render_html(file_name="fluxo_quanti.html", height=800)