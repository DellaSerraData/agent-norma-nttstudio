-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.alunos (
  pessoa_id text NOT NULL,
  nome text,
  status text,
  unidade text,
  codigo_aluno text,
  codigo_catraca text,
  data_cadastro date,
  consultor text,
  professor text,
  periodo_ini date,
  periodo_fim date,
  CONSTRAINT alunos_pkey PRIMARY KEY (pessoa_id)
);
CREATE TABLE public.assist_agents (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  name text NOT NULL,
  description text,
  purpose text,
  status text NOT NULL DEFAULT 'active'::text CHECK (status = ANY (ARRAY['active'::text, 'inactive'::text, 'draft'::text])),
  default_model text,
  temperature numeric,
  max_tokens integer,
  owner text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT assist_agents_pkey PRIMARY KEY (id)
);
CREATE TABLE public.assist_data_mentions (
  id bigint NOT NULL DEFAULT nextval('assist_data_mentions_id_seq'::regclass),
  message_id bigint NOT NULL,
  table_name text NOT NULL,
  record_id text,
  summary text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT assist_data_mentions_pkey PRIMARY KEY (id),
  CONSTRAINT assist_data_mentions_message_id_fkey FOREIGN KEY (message_id) REFERENCES public.assist_messages(id)
);
CREATE TABLE public.assist_embeddings (
  chunk_id bigint NOT NULL,
  embedding USER-DEFINED NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT assist_embeddings_pkey PRIMARY KEY (chunk_id),
  CONSTRAINT assist_embeddings_chunk_id_fkey FOREIGN KEY (chunk_id) REFERENCES public.assist_knowledge_chunks(id)
);
CREATE TABLE public.assist_knowledge_chunks (
  id bigint NOT NULL DEFAULT nextval('assist_knowledge_chunks_id_seq'::regclass),
  doc_id uuid NOT NULL,
  chunk text NOT NULL,
  chunk_index integer NOT NULL,
  token_count integer,
  metadata jsonb,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT assist_knowledge_chunks_pkey PRIMARY KEY (id),
  CONSTRAINT assist_knowledge_chunks_doc_id_fkey FOREIGN KEY (doc_id) REFERENCES public.assist_knowledge_docs(id)
);
CREATE TABLE public.assist_knowledge_docs (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  source_type text NOT NULL,
  source_uri text,
  hash text,
  mime_type text,
  token_count integer,
  metadata jsonb,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT assist_knowledge_docs_pkey PRIMARY KEY (id)
);
CREATE TABLE public.assist_messages (
  id bigint NOT NULL DEFAULT nextval('assist_messages_id_seq'::regclass),
  session_id uuid NOT NULL,
  role text NOT NULL CHECK (role = ANY (ARRAY['user'::text, 'agent'::text, 'system'::text, 'tool'::text])),
  content text,
  tool_name text,
  tool_input jsonb,
  tool_output jsonb,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT assist_messages_pkey PRIMARY KEY (id),
  CONSTRAINT assist_messages_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.assist_sessions(id)
);
CREATE TABLE public.assist_moderation (
  id bigint NOT NULL DEFAULT nextval('assist_moderation_id_seq'::regclass),
  message_id bigint NOT NULL,
  flagged boolean NOT NULL DEFAULT false,
  category text,
  score numeric,
  reason text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT assist_moderation_pkey PRIMARY KEY (id),
  CONSTRAINT assist_moderation_message_id_fkey FOREIGN KEY (message_id) REFERENCES public.assist_messages(id)
);
CREATE TABLE public.assist_sessions (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  agent_id uuid NOT NULL,
  created_by text,
  subject text,
  metadata jsonb,
  status text NOT NULL DEFAULT 'open'::text CHECK (status = ANY (ARRAY['open'::text, 'closed'::text])),
  opened_at timestamp with time zone NOT NULL DEFAULT now(),
  closed_at timestamp with time zone,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT assist_sessions_pkey PRIMARY KEY (id),
  CONSTRAINT assist_sessions_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.assist_agents(id)
);
CREATE TABLE public.assist_tool_catalog (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  name text NOT NULL UNIQUE,
  description text,
  schema jsonb,
  enabled boolean NOT NULL DEFAULT true,
  version text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT assist_tool_catalog_pkey PRIMARY KEY (id)
);
CREATE TABLE public.assist_tool_runs (
  id bigint NOT NULL DEFAULT nextval('assist_tool_runs_id_seq'::regclass),
  session_id uuid NOT NULL,
  message_id bigint,
  tool_id uuid,
  tool_name text NOT NULL,
  input jsonb,
  output jsonb,
  error text,
  status text NOT NULL DEFAULT 'queued'::text CHECK (status = ANY (ARRAY['queued'::text, 'running'::text, 'success'::text, 'error'::text])),
  started_at timestamp with time zone DEFAULT now(),
  finished_at timestamp with time zone,
  latency_ms integer DEFAULT
CASE
    WHEN ((finished_at IS NOT NULL) AND (started_at IS NOT NULL)) THEN ((EXTRACT(epoch FROM (finished_at - started_at)) * (1000)::numeric))::integer
    ELSE NULL::integer
END,
  CONSTRAINT assist_tool_runs_pkey PRIMARY KEY (id),
  CONSTRAINT assist_tool_runs_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.assist_sessions(id),
  CONSTRAINT assist_tool_runs_message_id_fkey FOREIGN KEY (message_id) REFERENCES public.assist_messages(id),
  CONSTRAINT assist_tool_runs_tool_id_fkey FOREIGN KEY (tool_id) REFERENCES public.assist_tool_catalog(id)
);
CREATE TABLE public.assist_user_map (
  session_id uuid NOT NULL,
  user_id uuid NOT NULL,
  user_role text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT assist_user_map_pkey PRIMARY KEY (session_id),
  CONSTRAINT assist_user_map_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.assist_sessions(id)
);
CREATE TABLE public.contato (
  pessoa_id text NOT NULL,
  email text,
  celular text,
  CONSTRAINT contato_pkey PRIMARY KEY (pessoa_id)
);
CREATE TABLE public.contrato (
  id text NOT NULL,
  pessoa_id text,
  descricao text,
  valor numeric,
  inicio date,
  vencimento date,
  status text,
  aceite_datahora timestamp without time zone,
  aceite_id text,
  unidade text,
  is_compartilhado boolean,
  CONSTRAINT contrato_pkey PRIMARY KEY (id)
);
CREATE TABLE public.dados_pessoais (
  pessoa_id text NOT NULL,
  data_nascimento date,
  sexo text,
  cpf text,
  estado_civil text,
  profissao text,
  CONSTRAINT dados_pessoais_pkey PRIMARY KEY (pessoa_id)
);
CREATE TABLE public.emergencia (
  pessoa_id text NOT NULL,
  contato text,
  telefone text,
  celular text,
  CONSTRAINT emergencia_pkey PRIMARY KEY (pessoa_id)
);
CREATE TABLE public.endereco (
  pessoa_id text NOT NULL,
  logradouro text,
  numero text,
  complemento text,
  bairro text,
  cidade text,
  uf text,
  cep text,
  CONSTRAINT endereco_pkey PRIMARY KEY (pessoa_id)
);
CREATE TABLE public.frequencia_checkin (
  id integer NOT NULL DEFAULT nextval('frequencia_checkin_id_seq'::regclass),
  pessoa_id text,
  unidade text,
  turma text,
  contrato text,
  data date,
  periodo text,
  checkin timestamp without time zone,
  origem text,
  seq integer,
  CONSTRAINT frequencia_checkin_pkey PRIMARY KEY (id)
);
CREATE TABLE public.frequencia_matricula (
  id integer NOT NULL DEFAULT nextval('frequencia_matricula_id_seq'::regclass),
  pessoa_id text,
  matricula_id text,
  classe text,
  contrato text,
  professor text,
  data text,
  horario text,
  ocupacao text,
  tipo_checkin text,
  status text,
  CONSTRAINT frequencia_matricula_pkey PRIMARY KEY (id)
);
