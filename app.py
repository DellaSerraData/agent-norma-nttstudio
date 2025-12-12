import os
import streamlit as st
from dotenv import load_dotenv
from chain import get_chain

load_dotenv()

st.set_page_config(page_title="NTT Agents", page_icon=":speech_balloon:")

st.title("NTT Agents")

with st.sidebar:
    st.header("Configurações")
    default_key = os.getenv("OPENAI_API_KEY", "")
    api_key = st.text_input("OpenAI API Key", type="password", value=default_key)
    if not api_key:
        st.warning("Por favor, insira sua OpenAI API Key para continuar.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Diga algo..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if api_key:
        chain = get_chain(api_key)
        if chain:
            try:
                with st.chat_message("assistant"):
                    response = chain.invoke({"topic": prompt})
                    st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.error(f"Erro ao executar a chain: {e}")
        else:
            st.error("Não foi possível inicializar a chain.")
    else:
        st.error("API Key não configurada.")
