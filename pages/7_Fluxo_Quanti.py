import streamlit as st
import streamlit.components.v1 as components
import os

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Fluxo Quanti")
st.logo("assets/logoBrain.png")

# --- Título e Descrição ---
st.title("🌊 Fluxo de Trabalho de Projetos Quantitativos")
st.markdown(
    "Esta é uma representação visual do fluxo de trabalho padrão para projetos quantitativos, "
    "desde a proposta inicial até a entrega final."
)

# --- Carregamento e Exibição do Componente HTML ---
try:
    # O caminho para o arquivo HTML. '..' significa voltar um diretório (de 'pages' para a raiz)
    path_to_html = os.path.join(os.path.dirname(__file__), '..', 'fluxo_quanti.html')

    # Abrir e ler o arquivo HTML
    with open(path_to_html, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Exibir o componente HTML no Streamlit
    components.html(
        html_content,
        height=800,  # Altura inicial do frame, ajuste conforme necessário
        scrolling=True # Permite a rolagem dentro do componente
    )

except FileNotFoundError:
    st.error(
        "O arquivo 'fluxo_quanti.html' não foi encontrado. "
        "Certifique-se de que ele está na pasta raiz do projeto."
    )
except Exception as e:
    st.error(f"Ocorreu um erro ao carregar a visualização: {e}")