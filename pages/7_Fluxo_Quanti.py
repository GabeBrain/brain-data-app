# pages/7_Fluxo_Quanti.py

import streamlit as st
import streamlit.components.v1 as components
import os

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Fluxo Quanti")
st.logo("assets/logoBrain.png")

# --- Título e Descrição ---
st.title("🌊 Fluxo de Trabalho de Projetos Quantitativos")
st.markdown(
    "Representações visuais do fluxo de trabalho padrão, desde a proposta inicial até a entrega final."
)

# --- Criação das Abas para cada Visualização ---
tab1, tab2 = st.tabs(["Visão Vertical (Kanban com Filtros)", "Visão Horizontal (Timeline)"])

# --- Conteúdo da Aba 1: Fluxo Vertical com Filtros ---
with tab1:
    st.subheader("Fluxo por Fases com Filtro de Responsáveis")
    try:
        # Caminho para o novo arquivo HTML com filtros
        path_to_html = os.path.join(os.path.dirname(__file__), '..', 'fluxo_quanti_filtro.html')

        with open(path_to_html, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # Exibe o componente HTML
        components.html(
            html_content,
            height=1200,  # Aumentamos a altura para acomodar o layout vertical
            scrolling=True
        )

    except FileNotFoundError:
        st.error(
            "O arquivo 'fluxo_quanti_filtro.html' não foi encontrado. "
            "Certifique-se de que ele está na pasta raiz do projeto."
        )
    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar a visualização vertical: {e}")


# --- Conteúdo da Aba 2: Fluxo Horizontal (Timeline) ---
with tab2:
    st.subheader("Linha do Tempo Horizontal do Projeto")
    try:
        # Caminho para o arquivo HTML original
        path_to_html = os.path.join(os.path.dirname(__file__), '..', 'fluxo_quanti.html')

        with open(path_to_html, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # Exibe o componente HTML
        components.html(
            html_content,
            height=800,
            scrolling=True
        )

    except FileNotFoundError:
        st.error(
            "O arquivo 'fluxo_quanti.html' não foi encontrado. "
            "Certifique-se de que ele está na pasta raiz do projeto."
        )
    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar a visualização horizontal: {e}")