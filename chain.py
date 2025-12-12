"""
chain.py

Cria um agente LangChain que consegue usar tools do Supabase via MCP.

A função get_chain(api_key) retorna um agente com loop de ferramentas,
ou seja, ele pode decidir quando chamar uma tool e depois responder ao usuário.

Observação importante
Guarde SUPABASE_ACCESS_TOKEN no servidor. Não exponha em navegador.
"""

from __future__ import annotations

import asyncio
import os
import re
from functools import lru_cache
from typing import Dict, Iterable, Optional

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from pydantic import BaseModel, ConfigDict, Field

# --------------------------------------------------------------------------- #
# Configurações e constantes
# --------------------------------------------------------------------------- #
SYSTEM_SCHEMA_SUMMARY = """
- alunos (pessoa_id PK, nome, status, unidade, codigo_aluno, codigo_catraca, datas de cadastro/período, consultor, professor). Tabelas contato/dados_pessoais/endereco/emergencia usam pessoa_id para detalhar o aluno.
- contrato (id PK) guarda pessoa_id, valores e datas; frequencia_checkin e frequencia_matricula têm pessoa_id e contrato, mas não têm FK formal para alunos.
- frequencia_checkin (id PK, pessoa_id, unidade, turma, contrato, data, periodo, checkin, origem, seq) registra presença; relacione via pessoa_id.
- frequencia_matricula (id PK, pessoa_id, matricula_id, classe, contrato, professor, data, horario, ocupacao, tipo_checkin, status).
- assist_* são tabelas de auditoria/assistente (agents/sessions/messages/tool_runs/etc).
""".strip()

BASE_SYSTEM_PROMPT = f"""
Você é um assistente do NTT.
Quando a pergunta envolver dados, use as tools do Supabase MCP.
O acesso está em modo somente leitura, então não tente criar, atualizar ou deletar dados.
Responda em português, de forma clara, e cite o que consultou quando fizer sentido.
Siga o estilo ReAct: pense -> chame a tool -> observe -> responda.
Antes de escrever SQL, descubra o schema usando context_list_tables/context_describe_table/context_foreign_keys.
Quando gerar SQL, explique quais tabelas/colunas usou e por quê.
Resumo rápido do schema (schema.sql):
{SYSTEM_SCHEMA_SUMMARY}
""".strip()


def _supabase_mcp_url() -> str:
    """
    Monta a URL do servidor MCP do Supabase Cloud.

    read_only=true limita as ferramentas a operações seguras de leitura.
    features permite reduzir o conjunto de ferramentas expostas ao agente.
    """
    project_ref = os.getenv("SUPABASE_PROJECT_REF", "").strip()
    if not project_ref:
        raise RuntimeError("SUPABASE_PROJECT_REF não definido")

    features = os.getenv("SUPABASE_MCP_FEATURES", "database,docs").strip()

    return (
        "https://mcp.supabase.com/mcp"
        f"?project_ref={project_ref}"
        "&read_only=true"
        f"&features={features}"
    )


def _require_tool(tools: Iterable, name: str):
    for tool in tools:
        if tool.name == name:
            return tool
    msg = f"Tool '{name}' não encontrada na conexão MCP."
    raise RuntimeError(msg)


def _safe_ident(value: str) -> str:
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", value or ""):
        msg = "Use apenas letras, números e _ para nomes de schema/tabela."
        raise ValueError(msg)
    return value


class TableSchemaInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    table: str = Field(..., description="Nome da tabela (sem schema).")
    table_schema: str = Field(
        "public",
        alias="schema",
        description="Schema da tabela.",
    )


class SampleTableInput(TableSchemaInput):
    limit: int = Field(
        5,
        description="Quantidade de linhas para amostra (1-50).",
        ge=1,
        le=50,
    )


class ListTablesInput(BaseModel):
    schemas: list[str] | None = Field(
        default=None,
        description="Lista de schemas a inspecionar. Se vazio, usa 'public'.",
    )


def _build_context_tools(tools: Iterable):
    """Cria as tools de contexto (schema, amostras, FKs) a partir das MCP tools base."""
    list_tables_tool = _require_tool(tools, "list_tables")
    execute_sql_tool = _require_tool(tools, "execute_sql")

    async def list_tables_context(schemas: list[str] | None = None):
        payload = {}
        if schemas:
            payload["schemas"] = schemas
        return await list_tables_tool.ainvoke(payload)

    async def describe_table(table: str, table_schema: str = "public"):
        _safe_ident(table)
        _safe_ident(table_schema)
        sql = f"""
        select
            column_name,
            data_type,
            is_nullable,
            column_default
        from information_schema.columns
        where table_schema = '{table_schema}'
          and table_name = '{table}'
        order by ordinal_position;
        """
        return await execute_sql_tool.ainvoke({"query": sql})

    async def sample_rows(table: str, table_schema: str = "public", limit: int = 5):
        _safe_ident(table)
        _safe_ident(table_schema)
        limit = max(1, min(limit, 50))
        sql = f"select * from {table_schema}.{table} limit {limit};"
        return await execute_sql_tool.ainvoke({"query": sql})

    async def foreign_keys(table: str, table_schema: str = "public"):
        _safe_ident(table)
        _safe_ident(table_schema)
        sql = f"""
        select
            tc.constraint_name,
            kcu.column_name as local_column,
            ccu.table_schema as foreign_table_schema,
            ccu.table_name as foreign_table,
            ccu.column_name as foreign_column
        from information_schema.table_constraints tc
        join information_schema.key_column_usage kcu
          on tc.constraint_name = kcu.constraint_name
         and tc.table_schema = kcu.table_schema
        join information_schema.constraint_column_usage ccu
          on ccu.constraint_name = tc.constraint_name
        where tc.constraint_type = 'FOREIGN KEY'
          and tc.table_schema = '{table_schema}'
          and tc.table_name = '{table}'
        order by tc.constraint_name, kcu.ordinal_position;
        """
        return await execute_sql_tool.ainvoke({"query": sql})

    async def table_row_counts():
        sql = """
        select
            schemaname as schema,
            relname   as table,
            n_live_tup as estimated_rows
        from pg_stat_user_tables
        order by n_live_tup desc;
        """
        return await execute_sql_tool.ainvoke({"query": sql})

    return [
        StructuredTool.from_function(
            coroutine=list_tables_context,
            name="context_list_tables",
            description="Lista tabelas por schema para descobrir nomes corretos antes de montar consultas.",
            args_schema=ListTablesInput,
        ),
        StructuredTool.from_function(
            coroutine=describe_table,
            name="context_describe_table",
            description="Mostra colunas de uma tabela (nome, tipo, nullable, default) usando information_schema.",
            args_schema=TableSchemaInput,
        ),
        StructuredTool.from_function(
            coroutine=foreign_keys,
            name="context_foreign_keys",
            description="Lista chaves estrangeiras de uma tabela (coluna local -> tabela/coluna remota).",
            args_schema=TableSchemaInput,
        ),
        StructuredTool.from_function(
            coroutine=sample_rows,
            name="context_sample_rows",
            description="Busca uma amostra de linhas de uma tabela (limite 1-50) para entender os dados.",
            args_schema=SampleTableInput,
        ),
        StructuredTool.from_function(
            coroutine=table_row_counts,
            name="context_table_row_counts",
            description="Traz contagem aproximada de linhas por tabela para priorizar onde consultar.",
        ),
    ]


def _build_headers() -> Dict[str, str]:
    headers: Dict[str, str] = {}
    token = os.getenv("SUPABASE_ACCESS_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


async def _build_agent(api_key: str):
    """
    Cria o agente e carrega as tools do Supabase MCP.
    """
    if not api_key:
        raise ValueError("api_key vazia")

    headers = _build_headers()
    client = MultiServerMCPClient(
        {
            "supabase": {
                "transport": "http",
                "url": _supabase_mcp_url(),
                **({"headers": headers} if headers else {}),
            }
        }
    )

    base_tools = await client.get_tools()
    context_tools = _build_context_tools(base_tools)

    model = ChatOpenAI(
        openai_api_key=api_key,
        model=os.getenv("OPENAI_MODEL", "gpt-4.1"),
        temperature=0.1,
    )

    all_tools = list(base_tools) + context_tools
    return create_agent(model, tools=all_tools, system_prompt=BASE_SYSTEM_PROMPT)


@lru_cache(maxsize=4)
def get_chain(api_key: str):
    """
    Retorna o agente pronto para uso no Streamlit.

    Faz cache por api_key para evitar recarregar tools em toda mensagem.
    """
    return asyncio.run(_build_agent(api_key))
