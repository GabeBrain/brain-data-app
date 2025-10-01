# pages/7_Fluxo_Quanti.py

import streamlit as st
import streamlit.components.v1 as components
import os
import base64  # <-- Nova importação necessária

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Fluxos de Trabalho")
st.logo("assets/logoBrain.png")

# --- Título e Descrição ---
st.title("🌊 Fluxos de Trabalho e Documentos")
st.markdown("Representações visuais dos processos, cronogramas e documentos de referência da área.")

# --- Funções Auxiliares ---

def render_html(file_name: str, height: int):
    """Lê um arquivo HTML e o renderiza no Streamlit."""
    try:
        path_to_html = os.path.join(os.path.dirname(__file__), '..', file_name)
        with open(path_to_html, 'r', encoding='utf-8') as f:
            html_content = f.read()
        components.html(html_content, height=height, scrolling=True)
    except FileNotFoundError:
        st.error(f"O arquivo '{file_name}' não foi encontrado na pasta raiz do projeto.")
    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar '{file_name}': {e}")

def render_pdf(file_name: str):
    """Lê um arquivo PDF e o renderiza de forma embutida na página."""
    try:
        path_to_pdf = os.path.join(os.path.dirname(__file__), '..', file_name)
        with open(path_to_pdf, "rb") as f:
            # Codifica o arquivo PDF em Base64
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        
        # Cria um HTML com um visualizador de PDF embutido
        pdf_display = f'<embed src="data:application/pdf;base64,{base64_pdf}" width="100%" height="1000" type="application/pdf">'
        
        # Exibe o PDF na página
        st.markdown(pdf_display, unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"O arquivo '{file_name}' não foi encontrado na pasta raiz do projeto.")
    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar o PDF '{file_name}': {e}")


# --- Criação das 4 Abas ---
tab1, tab2, tab3, tab4 = st.tabs([
    "Fluxo de Projeto (Kanban)",
    "Fluxo de Projeto (Timeline)",
    "Cronograma Jotform",
    "Apresentação MKT (PDF)"  
])

# Aba 1: Kanban com Filtros
with tab1:
    st.subheader("Visão Geral do Fluxo por Fases com Filtro de Responsáveis")
    render_html(file_name="fluxo_quanti_filtro.html", height=1200)

# Aba 2: Timeline Horizontal
with tab2:
    st.subheader("Linha do Tempo Horizontal do Projeto")
    render_html(file_name="fluxo_quanti.html", height=800)

# Aba 3: Cronograma Jotform
with tab3:
    st.subheader("Cronograma de Atividades: Implementação de Ferramentas de Coleta")
    render_html(file_name="fluxo_jotform.html", height=800)

# Aba 4: Renderização do PDF
with tab4:
    st.subheader("Documento de Referência: Apresentação de Marketing")
    # Chama a nova função para renderizar o PDF
    render_pdf(file_name="mkt.pdf")