"""
app.py

Interface Streamlit para conversar com um agente LangChain que possui acesso ao Supabase via MCP.

O histórico do chat fica em st.session_state.messages no formato:
{ "role": "user" | "assistant", "content": "texto" }

Na hora de chamar o agente, convertemos para objetos de mensagem do LangChain.
"""

import asyncio
import logging
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from chain import get_chain


def to_langchain_messages(history):
    """
    Converte o histórico do Streamlit para mensagens do LangChain.

    Isso melhora compatibilidade com agentes e evita ambiguidades de formato.
    """
    out = []
    for item in history:
        role = item.get("role")
        content = item.get("content", "")
        if role == "user":
            out.append(HumanMessage(content=content))
        elif role == "assistant":
            out.append(AIMessage(content=content))
        elif role == "system":
            out.append(SystemMessage(content=content))
    return out


async def ainvoke_agent(agent, messages):
    """
    Invoca o agente de forma assíncrona para permitir o uso de tools assíncronas (ex.: MCP).
    """
    return await agent.ainvoke({"messages": messages})


def _setup_logger() -> logging.Logger:
    logger = logging.getLogger("ntt_agent")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    log_path = Path(os.getenv("AGENT_LOG_FILE", "agent.log"))
    if not log_path.is_absolute():
        log_path = Path.cwd() / log_path

    handler = logging.FileHandler(log_path, encoding="utf-8")
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


load_dotenv()
logger = _setup_logger()

st.set_page_config(page_title="NTT Agents", page_icon="💬")
st.title("NTT Agents")

with st.sidebar:
    st.header("Configurações")

    default_key = os.getenv("OPENAI_API_KEY", "")
    api_key = st.text_input("OpenAI API Key", type="password", value=default_key)

    default_project_ref = os.getenv("SUPABASE_PROJECT_REF", "")
    default_supabase_token = os.getenv("SUPABASE_ACCESS_TOKEN", "")
    default_features = os.getenv("SUPABASE_MCP_FEATURES", "database,docs")

    project_ref = st.text_input(
        "SUPABASE Project Ref",
        value=default_project_ref,
        help="Ref do projeto Supabase usado pelo MCP.",
    )
    supabase_token = st.text_input(
        "SUPABASE Access Token",
        type="password",
        value=default_supabase_token,
        help="Token Bearer para acessar o MCP (somente leitura).",
    )
    supabase_features = st.text_input(
        "Supabase MCP features",
        value=default_features,
        help="Lista de features na URL do MCP (ex.: database,docs).",
    )

    if not api_key:
        st.warning("Por favor, insira sua OpenAI API Key para continuar.")
    if not project_ref:
        st.warning("Informe o SUPABASE Project Ref para inicializar o MCP.")


if "messages" not in st.session_state:
    st.session_state.messages = []


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


if prompt := st.chat_input("Diga algo..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    if not api_key:
        st.error("API Key não configurada.")
        st.stop()
    if not project_ref:
        st.error("SUPABASE_PROJECT_REF não configurado.")
        st.stop()
    else:
        logger.info("chat.prompt text_len=%s", len(prompt))

    try:
        agent = get_chain(
            api_key,
            project_ref=project_ref,
            supabase_token=supabase_token,
            features=supabase_features,
        )
        logger.info(
            "agent.initialized project_ref=%s features=%s headers=%s",
            project_ref or "missing",
            supabase_features or "missing",
            "present" if supabase_token else "absent",
        )
    except Exception as e:
        logger.exception("agent.init.error")
        st.error(f"Falha ao inicializar o agente: {e}")
        st.stop()

    try:
        lc_messages = to_langchain_messages(st.session_state.messages)

        with st.chat_message("assistant"):
            result = asyncio.run(ainvoke_agent(agent, lc_messages))

            messages = result.get("messages", [])
            if messages:
                response = getattr(messages[-1], "content", str(messages[-1]))
            else:
                response = str(result)

            st.markdown(response)
            logger.info("chat.response text_len=%s", len(response))

        st.session_state.messages.append({"role": "assistant", "content": response})

    except Exception as e:
        logger.exception("agent.invoke.error")
        st.error(f"Erro ao executar o agente: {e}")
