# app.py (Versão de Teste Mínimo)

import streamlit as st
import pandas as pd # Adicionado para garantir que a biblioteca é importável

st.set_page_config(
    layout="wide",
    page_title="Teste de Deploy",
    page_icon="✅"
)

st.title("✅ Aplicação de Teste no Ar!")
st.success("Se você está vendo esta mensagem, a inicialização básica do Streamlit está funcionando perfeitamente.")
st.info(f"Versão do Pandas utilizada: {pd.__version__}")

st.balloons()