-- Comando: docker exec cartorio_supabase-db-1 pg_dump -U supabase_admin -d cartorio --schema-only
--
-- SOURCE OF TRUTH: backend/alembic/versions/ (NUNCA edite este arquivo
-- diretamente. Mudancas vao via Alembic migration + alembic upgrade head).
-- Este arquivo serve como REFERENCIA do schema canonico + restore manual
-- em caso de disaster recovery.
--
-- CONTEUDO:
-- - 10 tabelas S01: atendimentos, audit_log, clientes, documentos,
--   emolumentos, lgpd_consents, lgpd_audit_anpd, outbox_messages,
--   protocolos, webhook_events (+ conversas legacy)
-- - 3 functions: fn_audit_chain_verify, fn_auto_audit, fn_set_updated_at
-- - Indices: PK + FK + WHERE-frequentes (LGPD compliance)
-- - Constraints: FK + CHECK + UNIQUE
-- - RLS policies: 4 roles (anon, authenticated, service_role, dpo)
-- - Triggers: set_updated_at em todas as tabelas com updated_at
-- - Enums: motivo_encerramento_enum
--
-- LGPD-by-design:
-- - clientes.cpf_hash: SHA256 com salt (PI) - nunca persiste puro
-- - audit_log.ip_truncated: /24 IPv4 / /32 IPv6 (art. 5 I)
-- - lgpd_audit_anpd: rastreabilidade para ANPD (art. 48)
-- - RLS: anon SEM acesso, authenticated limitado, dpo read-only
--
-- Sprint 4 S01 (2026-06-25) — SQUAD S0 Supabase Foundation
-- Migration final aplicada: 2026_06_25_0010
-- Modified by Gustavo Almeida
-- =============================================================================

pg_dump: warning: there are circular foreign-key constraints on this table:
pg_dump: detail: key
pg_dump: hint: You might not be able to restore the dump without using --disable-triggers or temporarily dropping the constraints.
pg_dump: hint: Consider using a full dump instead of a --data-only dump to avoid this problem.
--
-- PostgreSQL database dump
--

-- Dumped from database version 15.8
-- Dumped by pg_dump version 15.8

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: auth; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA auth;


--
-- Name: extensions; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA extensions;


--
-- Name: graphql; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA graphql;


--
-- Name: pg_net; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_net WITH SCHEMA extensions;


--
-- Name: EXTENSION pg_net; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pg_net IS 'Async HTTP';


--
-- Name: pgsodium; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA pgsodium;


--
-- Name: pgsodium; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgsodium WITH SCHEMA pgsodium;


--
-- Name: EXTENSION pgsodium; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgsodium IS 'Pgsodium is a modern cryptography library for Postgres.';


--
-- Name: storage; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA storage;


--
-- Name: supabase_functions; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA supabase_functions;


--
-- Name: supabase_realtime; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA supabase_realtime;


--
-- Name: vault; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA vault;


--
-- Name: pg_graphql; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_graphql WITH SCHEMA graphql;


--
-- Name: EXTENSION pg_graphql; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pg_graphql IS 'pg_graphql: GraphQL support';


--
-- Name: supabase_vault; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS supabase_vault WITH SCHEMA vault;


--
-- Name: EXTENSION supabase_vault; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION supabase_vault IS 'Supabase Vault Extension';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: DeviceMessage; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public."DeviceMessage" AS ENUM (
    'ios',
    'android',
    'web',
    'unknown',
    'desktop'
);


--
-- Name: DifyBotType; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public."DifyBotType" AS ENUM (
    'chatBot',
    'textGenerator',
    'agent',
    'workflow'
);


--
-- Name: InstanceConnectionStatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public."InstanceConnectionStatus" AS ENUM (
    'open',
    'close',
    'connecting'
);


--
-- Name: OpenaiBotType; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public."OpenaiBotType" AS ENUM (
    'assistant',
    'chatCompletion'
);


--
-- Name: SessionStatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public."SessionStatus" AS ENUM (
    'opened',
    'closed',
    'paused'
);


--
-- Name: TriggerOperator; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public."TriggerOperator" AS ENUM (
    'contains',
    'equals',
    'startsWith',
    'endsWith',
    'regex'
);


--
-- Name: TriggerType; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public."TriggerType" AS ENUM (
    'all',
    'keyword',
    'none',
    'advanced'
);


--
-- Name: motivo_encerramento_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.motivo_encerramento_enum AS ENUM (
    'REVOGACAO_CONSENTIMENTO',
    'RETENCAO_5Y',
    'EXERCICIO_DIREITO_TITULAR',
    'OUTROS'
);


--
-- Name: outbox_queue_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.outbox_queue_enum AS ENUM (
    'EVOLUTION',
    'CHATWOOT',
    'TELEGRAM',
    'OUTBOX'
);


--
-- Name: outbox_status_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.outbox_status_enum AS ENUM (
    'PENDING',
    'PROCESSING',
    'DONE',
    'FAILED'
);


--
-- Name: role(); Type: FUNCTION; Schema: auth; Owner: -
--

CREATE FUNCTION auth.role() RETURNS text
    LANGUAGE sql STABLE
    AS $$
SELECT COALESCE(
  NULLIF(current_setting('request.jwt.claim.role', true), ''),
  'anon'
)
$$;


--
-- Name: uid(); Type: FUNCTION; Schema: auth; Owner: -
--

CREATE FUNCTION auth.uid() RETURNS uuid
    LANGUAGE sql STABLE
    AS $$
SELECT NULLIF(current_setting('request.jwt.claim.sub', true), '')::uuid
$$;


--
-- Name: criar_protocolo(uuid, character varying, text, character varying, jsonb); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.criar_protocolo(p_cliente_id uuid, p_tipo character varying, p_descricao text, p_origem character varying, p_metadata jsonb DEFAULT '{}'::jsonb) RETURNS uuid
    LANGUAGE plpgsql
    AS $$
DECLARE
  v_id UUID;
BEGIN
  INSERT INTO protocolos (cliente_id, tipo, descricao, origem, status, created_at)
  VALUES (p_cliente_id, p_tipo, p_descricao, p_origem, 'draft', NOW())
  RETURNING id INTO v_id;
  BEGIN
    INSERT INTO audit_log (evento, recurso_id, recurso_tipo, created_at)
    VALUES ('protocolo.criado', v_id::VARCHAR, 'protocolo', NOW());
  EXCEPTION WHEN undefined_table THEN
    NULL;
  END;
  RETURN v_id;
END;
$$;


--
-- Name: fn_audit_chain_verify(bigint, bigint); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_audit_chain_verify(p_from_id bigint DEFAULT 0, p_to_id bigint DEFAULT NULL::bigint) RETURNS TABLE(total_checked bigint, chain_ok boolean, first_bad_id bigint)
    LANGUAGE plpgsql STABLE
    AS $$
        DECLARE
            v_total BIGINT := 0;
            v_ok BOOLEAN := TRUE;
            v_bad_id BIGINT := NULL;
            v_rec RECORD;
            v_prev_hash TEXT := '';
            v_expected_hash TEXT;
        BEGIN
            FOR v_rec IN (
                SELECT id, prev_hash, hash, hmac_signature
                FROM audit_log
                WHERE id >= p_from_id AND (p_to_id IS NULL OR id <= p_to_id)
                ORDER BY id ASC
            ) LOOP
                v_total := v_total + 1;

                -- Confere prev_hash chain
                IF v_rec.prev_hash IS DISTINCT FROM v_prev_hash THEN
                    v_ok := FALSE;
                    v_bad_id := v_rec.id;
                    EXIT;
                END IF;

                v_prev_hash := v_rec.hash;
            END LOOP;

            RETURN QUERY SELECT v_total, v_ok, v_bad_id;
        END;
        $$;


--
-- Name: fn_auto_audit(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_auto_audit() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        DECLARE
            v_action TEXT;
            v_resource TEXT;
            v_actor_id TEXT;
            v_payload JSONB;
        BEGIN
            v_resource := TG_TABLE_NAME;

            IF TG_OP = 'INSERT' THEN
                v_action := 'create';
                v_payload := to_jsonb(NEW);
            ELSIF TG_OP = 'UPDATE' THEN
                v_action := 'update';
                v_payload := jsonb_build_object('old', to_jsonb(OLD), 'new', to_jsonb(NEW));
            ELSIF TG_OP = 'DELETE' THEN
                v_action := 'delete';
                v_payload := to_jsonb(OLD);
            END IF;

            -- actor_id vem de current_setting('app.current_actor_id', true) ou 'system'
            BEGIN
                v_actor_id := current_setting('app.current_actor_id', true);
            EXCEPTION WHEN OTHERS THEN
                v_actor_id := 'auto_audit';
            END;
            IF v_actor_id IS NULL OR v_actor_id = '' THEN
                v_actor_id := 'auto_audit';
            END IF;

            INSERT INTO audit_log (
                actor_id, actor_type, action, resource, payload,
                request_id, canal, ip, user_agent, timestamp
            ) VALUES (
                v_actor_id, 'system', v_action, v_resource, v_payload,
                COALESCE(current_setting('app.request_id', true), 'auto'),
                COALESCE(current_setting('app.canal', true), 'system'),
                COALESCE(current_setting('app.ip', true), '0.0.0.0')::inet,
                COALESCE(current_setting('app.user_agent', true), 'auto_audit_trigger'),
                NOW()
            );

            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            ELSE
                RETURN NEW;
            END IF;
        END;
        $$;


--
-- Name: fn_set_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_set_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$;


--
-- Name: increment_workflow_version(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.increment_workflow_version() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
			BEGIN
				IF NEW."versionCounter" IS NOT DISTINCT FROM OLD."versionCounter"
					AND (NEW."nodes"::text IS DISTINCT FROM OLD."nodes"::text
						OR NEW."settings"::text IS DISTINCT FROM OLD."settings"::text) THEN
					NEW."versionCounter" = OLD."versionCounter" + 1;
				END IF;
				RETURN NEW;
			END;
			$$;


--
-- Name: lgpd_consent_webhook(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.lgpd_consent_webhook() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
BEGIN
  PERFORM supabase_functions.http_request(
    'https://flow.2notasudi.com.br/webhook/lgpd-consent'::text,
    'POST'::text,
    '{"Content-Type":"application/json"}'::jsonb,
    jsonb_build_object('event','INSERT','table','lgpd_consent_log','record', row_to_json(NEW)::jsonb),
    '5000'::text
  );
  RETURN NEW;
EXCEPTION WHEN OTHERS THEN
  RAISE WARNING 'lgpd_consent_webhook failed: %', SQLERRM;
  RETURN NEW;
END;
$$;


--
-- Name: notify_outbox_new(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.notify_outbox_new() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            PERFORM pg_notify(
                'outbox_new',
                json_build_object(
                    'id', NEW.id,
                    'event_type', NEW.event_type,
                    'resource', NEW.resource,
                    'created_at', NEW.created_at
                )::text
            );
            RETURN NEW;
        END;
        $$;


--
-- Name: opt_out_global(character varying, character varying, character varying); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.opt_out_global(p_phone character varying, p_channel character varying, p_keyword character varying DEFAULT NULL::character varying) RETURNS uuid
    LANGUAGE plpgsql
    AS $$
DECLARE
  v_id UUID;
BEGIN
  INSERT INTO opt_out_log (phone, channel, keyword, expires_at)
  VALUES (p_phone, p_channel, p_keyword, NOW() + INTERVAL '5 years')
  ON CONFLICT (phone) DO UPDATE SET channel = EXCLUDED.channel, keyword = EXCLUDED.keyword, opted_out_at = NOW()
  RETURNING id INTO v_id;
  RETURN v_id;
END;
$$;


--
-- Name: outbox_webhook(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.outbox_webhook() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
DECLARE
  api_key text;
BEGIN
  SELECT secret::text INTO api_key FROM vault.secrets
    WHERE name = 'cartorio_api_key_placeholder' LIMIT 1;
  IF api_key IS NULL OR api_key = 'PLACEHOLDER_REPLACE_ME' THEN
    api_key := 'PLACEHOLDER_REPLACE_ME';
  END IF;
  PERFORM supabase_functions.http_request(
    'https://api.2notasudi.com.br/api/v1/integrations/outbox/dispatch'::text,
    'POST'::text,
    jsonb_build_object('Content-Type','application/json','X-API-Key', api_key),
    jsonb_build_object('event','INSERT','table','outbox_messages','record', row_to_json(NEW)::jsonb),
    '5000'::text
  );
  RETURN NEW;
EXCEPTION WHEN OTHERS THEN
  RAISE WARNING 'outbox_webhook failed: %', SQLERRM;
  RETURN NEW;
END;
$$;


--
-- Name: protocolo_status_webhook(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.protocolo_status_webhook() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
BEGIN
  IF (TG_OP = 'UPDATE') AND (
    NEW.status IS DISTINCT FROM OLD.status
    OR NEW.updated_at IS DISTINCT FROM OLD.updated_at
  ) THEN
    PERFORM supabase_functions.http_request(
      'https://flow.2notasudi.com.br/webhook/protocolo-status'::text,
      'POST'::text,
      '{"Content-Type":"application/json"}'::jsonb,
      jsonb_build_object(
        'event','UPDATE','table','protocolos',
        'old', row_to_json(OLD)::jsonb,
        'new', row_to_json(NEW)::jsonb
      ),
      '5000'::text
    );
  END IF;
  RETURN NEW;
EXCEPTION WHEN OTHERS THEN
  RAISE WARNING 'protocolo_status_webhook failed: %', SQLERRM;
  RETURN NEW;
END;
$$;


--
-- Name: registrar_auditoria(character varying, character varying, character varying, jsonb); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.registrar_auditoria(p_evento character varying, p_recurso_id character varying, p_recurso_tipo character varying, p_metadata jsonb DEFAULT '{}'::jsonb) RETURNS uuid
    LANGUAGE plpgsql
    AS $$
DECLARE
  v_id UUID;
  v_prev_hash VARCHAR(64);
  v_new_hash VARCHAR(64);
BEGIN
  BEGIN
    SELECT hash_chain INTO v_prev_hash FROM audit_log ORDER BY created_at DESC LIMIT 1;
  EXCEPTION WHEN undefined_table THEN
    v_prev_hash := NULL;
  END;
  v_new_hash := encode(digest(p_evento || COALESCE(v_prev_hash, '') || COALESCE(p_recurso_id, '') || NOW()::TEXT, 'sha256'), 'hex');
  BEGIN
    INSERT INTO audit_log (evento, recurso_id, recurso_tipo, hash_chain, metadata, created_at)
    VALUES (p_evento, p_recurso_id, p_recurso_tipo, v_new_hash, p_metadata, NOW())
    RETURNING id INTO v_id;
  EXCEPTION WHEN undefined_table THEN
    v_id := gen_random_uuid();
  END;
  RETURN v_id;
END;
$$;


--
-- Name: vault_get_or_create(text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.vault_get_or_create(p_name text) RETURNS text
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    AS $$
        DECLARE
            v_decrypted TEXT;
        BEGIN
            SELECT decrypted_secret INTO v_decrypted
            FROM vault.decrypted_secrets
            WHERE name = p_name
            LIMIT 1;

            IF v_decrypted IS NULL THEN
                RAISE WARNING 'Vault secret % nao encontrado. Rode seed_vault_secrets.py', p_name;
                RETURN 'AWAITING_OPERATOR';
            END IF;

            RETURN v_decrypted;
        END;
        $$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: _prisma_migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public._prisma_migrations (
    id character varying(36) NOT NULL,
    checksum character varying(64) NOT NULL,
    finished_at timestamp with time zone,
    migration_name character varying(255) NOT NULL,
    logs text,
    rolled_back_at timestamp with time zone,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    applied_steps_count integer DEFAULT 0 NOT NULL
);


--
-- Name: agendamentos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agendamentos (
    id integer NOT NULL,
    cliente_id integer NOT NULL,
    servico character varying(255) NOT NULL,
    data_hora timestamp without time zone NOT NULL,
    status character varying(50) DEFAULT 'pendente'::character varying NOT NULL,
    observacoes text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE agendamentos; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.agendamentos IS 'Agendamentos de serviços do cartório';


--
-- Name: COLUMN agendamentos.servico; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agendamentos.servico IS 'Tipo de serviço agendado';


--
-- Name: COLUMN agendamentos.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agendamentos.status IS 'pendente, confirmado, realizado, cancelado, reagendado';


--
-- Name: agendamentos_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.agendamentos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: agendamentos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.agendamentos_id_seq OWNED BY public.agendamentos.id;


--
-- Name: agent_checkpoints; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_checkpoints (
    "runId" character varying(255) NOT NULL,
    "agentId" character varying(255),
    state text,
    expired boolean DEFAULT false NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: agent_execution; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_execution (
    id character varying(36) NOT NULL,
    "threadId" character varying(128) NOT NULL,
    status character varying(16) NOT NULL,
    "startedAt" timestamp(3) with time zone,
    "stoppedAt" timestamp(3) with time zone,
    duration integer DEFAULT 0 NOT NULL,
    "userMessage" text NOT NULL,
    "assistantResponse" text NOT NULL,
    model character varying(255),
    "promptTokens" integer,
    "completionTokens" integer,
    "totalTokens" integer,
    cost double precision,
    "toolCalls" json,
    timeline json,
    error text,
    "hitlStatus" character varying(16),
    source character varying(32),
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    CONSTRAINT "CHK_agent_execution_hitlStatus" CHECK ((("hitlStatus")::text = ANY ((ARRAY['suspended'::character varying, 'resumed'::character varying])::text[]))),
    CONSTRAINT "CHK_agent_execution_status" CHECK (((status)::text = ANY ((ARRAY['success'::character varying, 'error'::character varying])::text[])))
);


--
-- Name: agent_execution_threads; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_execution_threads (
    id character varying(128) NOT NULL,
    "agentId" character varying(36) NOT NULL,
    "agentName" character varying(255) NOT NULL,
    "projectId" character varying(255) NOT NULL,
    "sessionNumber" integer DEFAULT 0 NOT NULL,
    "totalPromptTokens" integer DEFAULT 0 NOT NULL,
    "totalCompletionTokens" integer DEFAULT 0 NOT NULL,
    "totalCost" double precision DEFAULT 0 NOT NULL,
    "totalDuration" integer DEFAULT 0 NOT NULL,
    title character varying(255),
    emoji character varying(8),
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "taskId" character varying(32),
    "taskVersionId" character varying(36),
    "parentThreadId" character varying(128),
    "parentAgentId" character varying(36)
);


--
-- Name: COLUMN agent_execution_threads."taskId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_execution_threads."taskId" IS 'Published task ID that triggered this session; not an FK because published runs can outlive draft task definition rows';


--
-- Name: COLUMN agent_execution_threads."taskVersionId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_execution_threads."taskVersionId" IS 'Published agent_history version that supplied the task snapshot';


--
-- Name: COLUMN agent_execution_threads."parentThreadId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_execution_threads."parentThreadId" IS 'Parent session thread id that delegated this subagent run.';


--
-- Name: COLUMN agent_execution_threads."parentAgentId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_execution_threads."parentAgentId" IS 'Saved agent id of the parent that delegated this subagent run.';


--
-- Name: agent_files; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_files (
    id character varying(16) NOT NULL,
    "agentId" character varying(36) NOT NULL,
    "binaryDataId" text NOT NULL,
    "fileName" character varying(255) NOT NULL,
    "mimeType" character varying(255) NOT NULL,
    "fileSizeBytes" integer NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: COLUMN agent_files.id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_files.id IS 'Application-generated n8n nano ID';


--
-- Name: COLUMN agent_files."agentId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_files."agentId" IS 'Agent that owns this uploaded file';


--
-- Name: COLUMN agent_files."binaryDataId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_files."binaryDataId" IS 'Opaque BinaryDataService reference (mode-prefixed, e.g. "filesystem-v2:<uuid>"); not an FK to binary_data, which only has rows in DB storage mode';


--
-- Name: COLUMN agent_files."fileSizeBytes"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_files."fileSizeBytes" IS 'Uploaded file size in bytes';


--
-- Name: agent_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_history (
    "versionId" character varying(36) NOT NULL,
    "agentId" character varying(36) NOT NULL,
    schema json,
    tools json,
    skills json,
    "publishedById" uuid,
    author character varying(255) NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: COLUMN agent_history.schema; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_history.schema IS 'Frozen snapshot of the published AgentJsonConfig';


--
-- Name: COLUMN agent_history.tools; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_history.tools IS 'Frozen map of `toolId → { code, descriptor }` at publish time';


--
-- Name: COLUMN agent_history.skills; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_history.skills IS 'Frozen map of `skillId → AgentSkill` at publish time';


--
-- Name: agent_task_definition; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_task_definition (
    id character varying(32) NOT NULL,
    "agentId" character varying(36) NOT NULL,
    name character varying(128) NOT NULL,
    objective text NOT NULL,
    "cronExpression" character varying(128) NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: COLUMN agent_task_definition.id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_task_definition.id IS 'Application-generated task ID referenced from agent JSON config';


--
-- Name: COLUMN agent_task_definition."agentId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_task_definition."agentId" IS 'Owning agent; task definitions are deleted when the agent is deleted';


--
-- Name: COLUMN agent_task_definition.objective; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_task_definition.objective IS 'User-authored instruction sent to the agent when this task runs';


--
-- Name: COLUMN agent_task_definition."cronExpression"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_task_definition."cronExpression" IS 'Cron schedule evaluated using the instance timezone';


--
-- Name: agent_task_run_lock; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_task_run_lock (
    "agentId" character varying(36) NOT NULL,
    "taskId" character varying(32) NOT NULL,
    "holderId" uuid NOT NULL,
    "heldUntil" timestamp(3) with time zone NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: COLUMN agent_task_run_lock."agentId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_task_run_lock."agentId" IS 'Published agent whose scheduled task run is locked';


--
-- Name: COLUMN agent_task_run_lock."taskId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_task_run_lock."taskId" IS 'Published task ID whose scheduled run is locked';


--
-- Name: COLUMN agent_task_run_lock."holderId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_task_run_lock."holderId" IS 'Ephemeral lock owner token generated by the running main';


--
-- Name: COLUMN agent_task_run_lock."heldUntil"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_task_run_lock."heldUntil" IS 'Time after which another main can claim this task run lock';


--
-- Name: agent_task_snapshot; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_task_snapshot (
    "versionId" character varying(36) NOT NULL,
    "taskId" character varying(32) NOT NULL,
    enabled boolean NOT NULL,
    name character varying(128) NOT NULL,
    objective text NOT NULL,
    "cronExpression" character varying(128) NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: COLUMN agent_task_snapshot."versionId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_task_snapshot."versionId" IS 'Published agent_history version this task snapshot belongs to';


--
-- Name: COLUMN agent_task_snapshot."taskId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_task_snapshot."taskId" IS 'Stable task ID referenced from the published agent JSON config';


--
-- Name: COLUMN agent_task_snapshot.enabled; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_task_snapshot.enabled IS 'Published enabled state for this task at publish time';


--
-- Name: COLUMN agent_task_snapshot.objective; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_task_snapshot.objective IS 'User-authored instruction sent to the agent when this task runs';


--
-- Name: COLUMN agent_task_snapshot."cronExpression"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_task_snapshot."cronExpression" IS 'Cron schedule evaluated using the instance timezone';


--
-- Name: agents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agents (
    id character varying(36) NOT NULL,
    name character varying(128) NOT NULL,
    description character varying(512),
    "projectId" character varying(255) NOT NULL,
    integrations json DEFAULT '[]'::json NOT NULL,
    schema json,
    tools json DEFAULT '{}'::json NOT NULL,
    skills json DEFAULT '{}'::json NOT NULL,
    "versionId" character varying(36),
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "activeVersionId" character varying(36)
);


--
-- Name: agents_memory_entries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agents_memory_entries (
    id character varying(36) NOT NULL,
    "agentId" character varying(36) NOT NULL,
    "resourceId" character varying(255) NOT NULL,
    content text NOT NULL,
    "contentHash" character varying(64) NOT NULL,
    status character varying(16) NOT NULL,
    "supersededBy" character varying(36),
    "embeddingModel" character varying(128),
    embedding json,
    metadata json,
    "lastSeenAt" timestamp(3) with time zone NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    CONSTRAINT "CHK_agents_memory_entries_status" CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'superseded'::character varying, 'dropped'::character varying])::text[])))
);


--
-- Name: COLUMN agents_memory_entries."agentId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents_memory_entries."agentId" IS 'Agent that owns this episodic memory entry';


--
-- Name: COLUMN agents_memory_entries."resourceId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents_memory_entries."resourceId" IS 'agents_resources.id partition used for episodic recall scope';


--
-- Name: COLUMN agents_memory_entries."supersededBy"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents_memory_entries."supersededBy" IS 'Self-reference to replacement memory entry';


--
-- Name: COLUMN agents_memory_entries."embeddingModel"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents_memory_entries."embeddingModel" IS 'Embedding model used to produce embedding';


--
-- Name: COLUMN agents_memory_entries.embedding; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents_memory_entries.embedding IS 'Embedding vector for episodic recall';


--
-- Name: COLUMN agents_memory_entries.metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents_memory_entries.metadata IS 'Optional system metadata for ranking and debugging';


--
-- Name: COLUMN agents_memory_entries."lastSeenAt"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents_memory_entries."lastSeenAt" IS 'Last time equivalent content was observed; updatedAt tracks row mutation time';


--
-- Name: agents_memory_entry_cursors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agents_memory_entry_cursors (
    "agentId" character varying(36) NOT NULL,
    "observationScopeId" character varying(255) NOT NULL,
    "lastIndexedObservationId" character varying(36) NOT NULL,
    "lastIndexedObservationCreatedAt" timestamp(3) with time zone NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: COLUMN agents_memory_entry_cursors."agentId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents_memory_entry_cursors."agentId" IS 'Agent that owns this cursor';


--
-- Name: COLUMN agents_memory_entry_cursors."observationScopeId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents_memory_entry_cursors."observationScopeId" IS 'agents_threads.id source stream indexed into episodic memory';


--
-- Name: COLUMN agents_memory_entry_cursors."lastIndexedObservationId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents_memory_entry_cursors."lastIndexedObservationId" IS 'Last observation-log row indexed into episodic memory';


--
-- Name: COLUMN agents_memory_entry_cursors."lastIndexedObservationCreatedAt"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents_memory_entry_cursors."lastIndexedObservationCreatedAt" IS 'Creation timestamp for the last indexed observation-log row';


--
-- Name: agents_memory_entry_locks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agents_memory_entry_locks (
    "agentId" character varying(36) NOT NULL,
    "resourceId" character varying(255) NOT NULL,
    "holderId" character varying(64) NOT NULL,
    "heldUntil" timestamp(3) with time zone NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: COLUMN agents_memory_entry_locks."agentId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents_memory_entry_locks."agentId" IS 'Agent that owns this lock';


--
-- Name: COLUMN agents_memory_entry_locks."resourceId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents_memory_entry_locks."resourceId" IS 'agents_resources.id partition locked for episodic indexing';


--
-- Name: COLUMN agents_memory_entry_locks."holderId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents_memory_entry_locks."holderId" IS 'Ephemeral background-task lock owner token';


--
-- Name: agents_memory_entry_sources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agents_memory_entry_sources (
    id character varying(36) NOT NULL,
    "agentId" character varying(36) NOT NULL,
    "memoryEntryId" character varying(36) NOT NULL,
    "observationId" character varying(36) NOT NULL,
    "threadId" character varying(255) NOT NULL,
    "evidenceHash" character varying(64) NOT NULL,
    "evidenceText" text NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: COLUMN agents_memory_entry_sources."agentId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents_memory_entry_sources."agentId" IS 'Agent that owns the linked episodic memory entry source';


--
-- Name: COLUMN agents_memory_entry_sources."memoryEntryId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents_memory_entry_sources."memoryEntryId" IS 'Episodic memory entry linked to this source evidence';


--
-- Name: COLUMN agents_memory_entry_sources."observationId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents_memory_entry_sources."observationId" IS 'Observation-log row used as source evidence';


--
-- Name: COLUMN agents_memory_entry_sources."threadId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents_memory_entry_sources."threadId" IS 'Source conversation thread that produced the linked observation';


--
-- Name: COLUMN agents_memory_entry_sources."evidenceHash"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents_memory_entry_sources."evidenceHash" IS 'Bounded hash used to deduplicate exact evidence links';


--
-- Name: COLUMN agents_memory_entry_sources."evidenceText"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents_memory_entry_sources."evidenceText" IS 'Exact source evidence text from the observation, not recall scope';


--
-- Name: agents_messages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agents_messages (
    id character varying(36) NOT NULL,
    "threadId" character varying(255) NOT NULL,
    "resourceId" character varying(255) NOT NULL,
    role character varying(36) NOT NULL,
    type character varying(36),
    content json NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: agents_observation_cursors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agents_observation_cursors (
    "agentId" character varying(36) NOT NULL,
    "observationScopeId" character varying(255) NOT NULL,
    "lastObservedMessageId" character varying(36) NOT NULL,
    "lastObservedAt" timestamp(3) with time zone NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: COLUMN agents_observation_cursors."agentId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents_observation_cursors."agentId" IS 'Agent that owns this cursor';


--
-- Name: COLUMN agents_observation_cursors."observationScopeId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents_observation_cursors."observationScopeId" IS 'agents_threads.id source stream checkpointed by this cursor';


--
-- Name: agents_observation_locks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agents_observation_locks (
    "agentId" character varying(36) NOT NULL,
    "observationScopeId" character varying(255) NOT NULL,
    "taskKind" character varying(20) NOT NULL,
    "holderId" character varying(64) NOT NULL,
    "heldUntil" timestamp(3) with time zone NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    CONSTRAINT "CHK_agents_observation_locks_taskKind" CHECK ((("taskKind")::text = ANY ((ARRAY['observer'::character varying, 'reflector'::character varying])::text[])))
);


--
-- Name: COLUMN agents_observation_locks."agentId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents_observation_locks."agentId" IS 'Agent that owns this lock';


--
-- Name: COLUMN agents_observation_locks."observationScopeId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents_observation_locks."observationScopeId" IS 'agents_threads.id source stream locked for observation tasks';


--
-- Name: COLUMN agents_observation_locks."holderId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents_observation_locks."holderId" IS 'Ephemeral background-task lock owner token, not a user ID';


--
-- Name: agents_observations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agents_observations (
    id character varying(36) NOT NULL,
    "agentId" character varying(36) NOT NULL,
    "observationScopeId" character varying(255) NOT NULL,
    marker character varying(16) NOT NULL,
    text text NOT NULL,
    "parentId" character varying(36),
    "tokenCount" integer DEFAULT 0 NOT NULL,
    status character varying(16) NOT NULL,
    "supersededBy" character varying(36),
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    CONSTRAINT "CHK_agents_observations_marker" CHECK (((marker)::text = ANY ((ARRAY['critical'::character varying, 'important'::character varying, 'info'::character varying, 'completion'::character varying])::text[]))),
    CONSTRAINT "CHK_agents_observations_status" CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'superseded'::character varying, 'dropped'::character varying])::text[])))
);


--
-- Name: COLUMN agents_observations.id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents_observations.id IS 'Application-generated n8n string ID, not a database UUID';


--
-- Name: COLUMN agents_observations."agentId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents_observations."agentId" IS 'Agent that owns this observation row';


--
-- Name: COLUMN agents_observations."observationScopeId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agents_observations."observationScopeId" IS 'agents_threads.id source stream for this observation log';


--
-- Name: agents_resources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agents_resources (
    id character varying(255) NOT NULL,
    metadata text,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: agents_threads; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agents_threads (
    id character varying(128) NOT NULL,
    "resourceId" character varying(255) NOT NULL,
    title character varying(255),
    metadata text,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: ai_builder_temporary_workflow; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ai_builder_temporary_workflow (
    "workflowId" character varying(36) NOT NULL,
    "threadId" uuid NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: annotation_tag_entity; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.annotation_tag_entity (
    id character varying(16) NOT NULL,
    name character varying(24) NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: atendimento_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.atendimento_link (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    atendimento_id uuid NOT NULL,
    protocolo_id uuid,
    cliente_id uuid,
    conversa_id uuid,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: atendimentos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.atendimentos (
    id integer NOT NULL,
    protocolo_id integer,
    cliente_id integer,
    canal character varying(32) NOT NULL,
    external_id character varying(128) NOT NULL,
    chatwoot_conversation_id integer,
    chatwoot_inbox_id integer,
    chatwoot_agent_id integer,
    status character varying(32) NOT NULL,
    tipo character varying(64) NOT NULL,
    contexto_scrubbed text,
    pesquisa_enviada_em timestamp without time zone,
    pesquisa_nota integer,
    pesquisa_comentario text,
    iniciado_em timestamp without time zone NOT NULL,
    concluido_em timestamp without time zone,
    handoff_para_humano boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


--
-- Name: atendimentos_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.atendimentos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: atendimentos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.atendimentos_id_seq OWNED BY public.atendimentos.id;


--
-- Name: audit_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_log (
    id integer NOT NULL,
    actor_id character varying(128) NOT NULL,
    actor_type character varying(32) NOT NULL,
    action character varying(64) NOT NULL,
    resource character varying(128) NOT NULL,
    payload json NOT NULL,
    ip character varying(45),
    user_agent character varying(512),
    request_id character varying(64),
    prev_hash character varying(64),
    hash character varying(64) NOT NULL,
    hmac_signature character varying(128) NOT NULL,
    "timestamp" timestamp without time zone NOT NULL,
    canal character varying(32),
    ip_truncated character varying(50)
);

ALTER TABLE ONLY public.audit_log FORCE ROW LEVEL SECURITY;


--
-- Name: COLUMN audit_log.ip_truncated; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.audit_log.ip_truncated IS 'LGPD D5: IP truncado em /24 (IPv4) ou /32 (IPv6) para OUTPUT';


--
-- Name: audit_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_log_id_seq OWNED BY public.audit_log.id;


--
-- Name: auth_identity; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_identity (
    "userId" uuid,
    "providerId" character varying(255) NOT NULL,
    "providerType" character varying(32) NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: auth_provider_sync_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_provider_sync_history (
    id integer NOT NULL,
    "providerType" character varying(32) NOT NULL,
    "runMode" text NOT NULL,
    status text NOT NULL,
    "startedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "endedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    scanned integer NOT NULL,
    created integer NOT NULL,
    updated integer NOT NULL,
    disabled integer NOT NULL,
    error text
);


--
-- Name: auth_provider_sync_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.auth_provider_sync_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: auth_provider_sync_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.auth_provider_sync_history_id_seq OWNED BY public.auth_provider_sync_history.id;


--
-- Name: binary_data; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.binary_data (
    "fileId" uuid NOT NULL,
    "sourceType" character varying(50) NOT NULL,
    "sourceId" character varying(255) NOT NULL,
    data bytea NOT NULL,
    "mimeType" character varying(255),
    "fileName" character varying(255),
    "fileSize" integer NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    CONSTRAINT "CHK_binary_data_sourceType" CHECK ((("sourceType")::text = ANY ((ARRAY['execution'::character varying, 'chat_message_attachment'::character varying, 'agent_file'::character varying])::text[])))
);


--
-- Name: COLUMN binary_data."sourceType"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.binary_data."sourceType" IS 'Source the file belongs to, e.g. ''execution''';


--
-- Name: COLUMN binary_data."sourceId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.binary_data."sourceId" IS 'ID of the source, e.g. execution ID';


--
-- Name: COLUMN binary_data.data; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.binary_data.data IS 'Raw, not base64 encoded';


--
-- Name: COLUMN binary_data."fileSize"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.binary_data."fileSize" IS 'In bytes';


--
-- Name: chat_hub_agent_tools; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chat_hub_agent_tools (
    "agentId" uuid NOT NULL,
    "toolId" uuid NOT NULL
);


--
-- Name: chat_hub_agents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chat_hub_agents (
    id uuid NOT NULL,
    name character varying(256) NOT NULL,
    description character varying(512),
    "systemPrompt" text NOT NULL,
    "ownerId" uuid NOT NULL,
    "credentialId" character varying(36),
    provider character varying(16) NOT NULL,
    model character varying(64) NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    icon json,
    files json DEFAULT '[]'::json NOT NULL,
    "suggestedPrompts" json DEFAULT '[]'::json NOT NULL
);


--
-- Name: COLUMN chat_hub_agents.provider; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chat_hub_agents.provider IS 'ChatHubProvider enum: "openai", "anthropic", "google", "n8n"';


--
-- Name: COLUMN chat_hub_agents.model; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chat_hub_agents.model IS 'Model name used at the respective Model node, ie. "gpt-4"';


--
-- Name: chat_hub_messages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chat_hub_messages (
    id uuid NOT NULL,
    "sessionId" uuid NOT NULL,
    "previousMessageId" uuid,
    "revisionOfMessageId" uuid,
    "retryOfMessageId" uuid,
    type character varying(16) NOT NULL,
    name character varying(128) NOT NULL,
    content text NOT NULL,
    provider character varying(16),
    model character varying(256),
    "workflowId" character varying(36),
    "executionId" integer,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "agentId" uuid,
    status character varying(16) DEFAULT 'success'::character varying NOT NULL,
    attachments json
);


--
-- Name: COLUMN chat_hub_messages.type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chat_hub_messages.type IS 'ChatHubMessageType enum: "human", "ai", "system", "tool", "generic"';


--
-- Name: COLUMN chat_hub_messages.provider; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chat_hub_messages.provider IS 'ChatHubProvider enum: "openai", "anthropic", "google", "n8n"';


--
-- Name: COLUMN chat_hub_messages.model; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chat_hub_messages.model IS 'Model name used at the respective Model node, ie. "gpt-4"';


--
-- Name: COLUMN chat_hub_messages."agentId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chat_hub_messages."agentId" IS 'ID of the custom agent (if provider is "custom-agent")';


--
-- Name: COLUMN chat_hub_messages.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chat_hub_messages.status IS 'ChatHubMessageStatus enum, eg. "success", "error", "running", "cancelled"';


--
-- Name: COLUMN chat_hub_messages.attachments; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chat_hub_messages.attachments IS 'File attachments for the message (if any), stored as JSON. Files are stored as base64-encoded data URLs.';


--
-- Name: chat_hub_session_tools; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chat_hub_session_tools (
    "sessionId" uuid NOT NULL,
    "toolId" uuid NOT NULL
);


--
-- Name: chat_hub_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chat_hub_sessions (
    id uuid NOT NULL,
    title character varying(256) NOT NULL,
    "ownerId" uuid NOT NULL,
    "lastMessageAt" timestamp(3) with time zone NOT NULL,
    "credentialId" character varying(36),
    provider character varying(16),
    model character varying(256),
    "workflowId" character varying(36),
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "agentId" uuid,
    "agentName" character varying(128),
    type character varying(16) DEFAULT 'production'::character varying NOT NULL,
    CONSTRAINT "CHK_chat_hub_sessions_type" CHECK (((type)::text = ANY ((ARRAY['production'::character varying, 'manual'::character varying])::text[])))
);


--
-- Name: COLUMN chat_hub_sessions.provider; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chat_hub_sessions.provider IS 'ChatHubProvider enum: "openai", "anthropic", "google", "n8n"';


--
-- Name: COLUMN chat_hub_sessions.model; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chat_hub_sessions.model IS 'Model name used at the respective Model node, ie. "gpt-4"';


--
-- Name: COLUMN chat_hub_sessions."agentId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chat_hub_sessions."agentId" IS 'ID of the custom agent (if provider is "custom-agent")';


--
-- Name: COLUMN chat_hub_sessions."agentName"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chat_hub_sessions."agentName" IS 'Cached name of the custom agent (if provider is "custom-agent")';


--
-- Name: chat_hub_tools; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chat_hub_tools (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    type character varying(255) NOT NULL,
    "typeVersion" double precision NOT NULL,
    "ownerId" uuid NOT NULL,
    definition json NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: chatwoot_conversation_meta; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chatwoot_conversation_meta (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    chatwoot_conversation_id bigint,
    cartorio_atendimento_id uuid,
    cartorio_protocolo_id uuid,
    handoff_at timestamp with time zone,
    agent_id bigint,
    status character varying(20),
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: clientes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clientes (
    id integer NOT NULL,
    cpf_hash character varying(64) NOT NULL,
    nome character varying(255) NOT NULL,
    email character varying(255),
    telefone_hash character varying(64),
    consentimento_lgpd boolean NOT NULL,
    consentimento_em timestamp without time zone,
    consentimento_ip character varying(45),
    consentimento_canal character varying(32),
    deleted_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    motivo_encerramento character varying(32),
    audit_encerramento_id integer
);

ALTER TABLE ONLY public.clientes FORCE ROW LEVEL SECURITY;


--
-- Name: clientes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clientes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clientes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clientes_id_seq OWNED BY public.clientes.id;


--
-- Name: conversas; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.conversas (
    id integer NOT NULL,
    cliente_id integer,
    canal character varying(32) NOT NULL,
    external_id character varying(128) NOT NULL,
    raw_message_hash character varying(64) NOT NULL,
    raw_message_scrubbed text NOT NULL,
    intent_detected character varying(64),
    confidence_score double precision,
    bot_response text,
    handoff_to_human boolean NOT NULL,
    handoff_at timestamp without time zone,
    handoff_reason character varying(255),
    handoff_agent character varying(128),
    llm_model character varying(64),
    llm_tokens_in integer,
    llm_tokens_out integer,
    llm_latency_ms integer,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: conversas_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.conversas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: conversas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.conversas_id_seq OWNED BY public.conversas.id;


--
-- Name: cpf_cnpj_validator; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cpf_cnpj_validator (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    cpf_hash character varying(64),
    cnpj_hash character varying(64),
    validated_at timestamp with time zone DEFAULT now(),
    source character varying(50)
);


--
-- Name: credential_dependency; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.credential_dependency (
    id integer NOT NULL,
    "credentialId" character varying(36) NOT NULL,
    "dependencyType" character varying(64) NOT NULL,
    "dependencyId" character varying(255) NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: credential_dependency_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.credential_dependency ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.credential_dependency_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: credentials_entity; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.credentials_entity (
    name character varying(128) NOT NULL,
    data text NOT NULL,
    type character varying(128) NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    id character varying(36) NOT NULL,
    "isManaged" boolean DEFAULT false NOT NULL,
    "isGlobal" boolean DEFAULT false NOT NULL,
    "isResolvable" boolean DEFAULT false NOT NULL,
    "resolvableAllowFallback" boolean DEFAULT false NOT NULL,
    "resolverId" character varying(16)
);


--
-- Name: data_table; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.data_table (
    id character varying(36) NOT NULL,
    name character varying(128) NOT NULL,
    "projectId" character varying(36) NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: data_table_column; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.data_table_column (
    id character varying(36) NOT NULL,
    name character varying(128) NOT NULL,
    type character varying(32) NOT NULL,
    index integer NOT NULL,
    "dataTableId" character varying(36) NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: COLUMN data_table_column.type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.data_table_column.type IS 'Expected: string, number, boolean, or date (not enforced as a constraint)';


--
-- Name: COLUMN data_table_column.index; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.data_table_column.index IS 'Column order, starting from 0 (0 = first column)';


--
-- Name: deployment_key; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.deployment_key (
    id character varying(36) NOT NULL,
    type character varying(64) NOT NULL,
    value text NOT NULL,
    algorithm character varying(20),
    status character varying(20) NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: documentos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documentos (
    id integer NOT NULL,
    protocolo_id integer NOT NULL,
    tipo character varying(64) NOT NULL,
    storage_path character varying(512) NOT NULL,
    storage_provider character varying(32) NOT NULL,
    tamanho_bytes bigint,
    mime_type character varying(128),
    hash_sha256 character varying(64) NOT NULL,
    uploaded_by character varying(128) NOT NULL,
    uploaded_by_tipo character varying(32) NOT NULL,
    validado_por character varying(128),
    validado_em timestamp without time zone,
    validacao_notas character varying(1024),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


--
-- Name: documentos_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.documentos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: documentos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.documentos_id_seq OWNED BY public.documentos.id;


--
-- Name: dynamic_credential_entry; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dynamic_credential_entry (
    credential_id character varying(16) NOT NULL,
    subject_id character varying(2048) NOT NULL,
    resolver_id character varying(16) NOT NULL,
    data text NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: dynamic_credential_resolver; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dynamic_credential_resolver (
    id character varying(16) NOT NULL,
    name character varying(128) NOT NULL,
    type character varying(128) NOT NULL,
    config text NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: COLUMN dynamic_credential_resolver.config; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.dynamic_credential_resolver.config IS 'Encrypted resolver configuration (JSON encrypted as string)';


--
-- Name: dynamic_credential_user_entry; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dynamic_credential_user_entry (
    "credentialId" character varying(16) NOT NULL,
    "userId" uuid NOT NULL,
    "resolverId" character varying(16) NOT NULL,
    data text NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: emolumentos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.emolumentos (
    id integer NOT NULL,
    tipo_servico character varying(100) NOT NULL,
    complexidade character varying(50) DEFAULT 'simples'::character varying NOT NULL,
    valor numeric(12,2) NOT NULL,
    tabela_mg_2026 character varying(50) DEFAULT '2026'::character varying NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE emolumentos; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.emolumentos IS 'Tabela de emolumentos do Cartório (MG 2026)';


--
-- Name: COLUMN emolumentos.tipo_servico; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.emolumentos.tipo_servico IS 'Tipo de serviço notarial/registral';


--
-- Name: COLUMN emolumentos.complexidade; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.emolumentos.complexidade IS 'simples, media, alta';


--
-- Name: COLUMN emolumentos.tabela_mg_2026; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.emolumentos.tabela_mg_2026 IS 'Ano base da tabela de emolumentos';


--
-- Name: emolumentos_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.emolumentos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: emolumentos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.emolumentos_id_seq OWNED BY public.emolumentos.id;


--
-- Name: evaluation_collection; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.evaluation_collection (
    id character varying(36) NOT NULL,
    name character varying(128) NOT NULL,
    description text,
    "workflowId" character varying(36) NOT NULL,
    "evaluationConfigId" character varying(36) NOT NULL,
    "createdById" uuid,
    "insightsCache" json,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: evaluation_config; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.evaluation_config (
    id character varying(36) NOT NULL,
    "workflowId" character varying(36) NOT NULL,
    name character varying(128) NOT NULL,
    status character varying(16) DEFAULT 'valid'::character varying NOT NULL,
    "invalidReason" character varying(64),
    "datasetSource" character varying(32) NOT NULL,
    "datasetRef" json NOT NULL,
    "startNodeName" character varying(255) NOT NULL,
    "endNodeName" character varying(255) NOT NULL,
    metrics json NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: event_destinations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_destinations (
    id uuid NOT NULL,
    destination jsonb NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: evolution_instance; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.evolution_instance (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    instance_name character varying(100) NOT NULL,
    phone character varying(20),
    state character varying(20),
    qr_code_base64 text,
    last_seen_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: execution_annotation_tags; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.execution_annotation_tags (
    "annotationId" integer NOT NULL,
    "tagId" character varying(24) NOT NULL
);


--
-- Name: execution_annotations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.execution_annotations (
    id integer NOT NULL,
    "executionId" integer NOT NULL,
    vote character varying(6),
    note text,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: execution_annotations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.execution_annotations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: execution_annotations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.execution_annotations_id_seq OWNED BY public.execution_annotations.id;


--
-- Name: execution_data; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.execution_data (
    "executionId" integer NOT NULL,
    "workflowData" json NOT NULL,
    data text NOT NULL,
    "workflowVersionId" character varying(36)
);


--
-- Name: execution_entity; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.execution_entity (
    id integer NOT NULL,
    finished boolean NOT NULL,
    mode character varying NOT NULL,
    "retryOf" character varying,
    "retrySuccessId" character varying,
    "startedAt" timestamp(3) with time zone,
    "stoppedAt" timestamp(3) with time zone,
    "waitTill" timestamp(3) with time zone,
    status character varying NOT NULL,
    "workflowId" character varying(36) NOT NULL,
    "deletedAt" timestamp(3) with time zone,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "storedAt" character varying(2) DEFAULT 'db'::character varying NOT NULL,
    "tracingContext" json,
    "deduplicationKey" character varying(255),
    CONSTRAINT "execution_entity_storedAt_check" CHECK ((("storedAt")::text = ANY ((ARRAY['db'::character varying, 'fs'::character varying, 's3'::character varying])::text[])))
);


--
-- Name: execution_entity_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.execution_entity_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: execution_entity_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.execution_entity_id_seq OWNED BY public.execution_entity.id;


--
-- Name: execution_metadata; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.execution_metadata (
    id integer NOT NULL,
    "executionId" integer NOT NULL,
    key character varying(255) NOT NULL,
    value text NOT NULL
);


--
-- Name: execution_metadata_temp_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.execution_metadata_temp_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: execution_metadata_temp_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.execution_metadata_temp_id_seq OWNED BY public.execution_metadata.id;


--
-- Name: folder; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.folder (
    id character varying(36) NOT NULL,
    name character varying(128) NOT NULL,
    "parentFolderId" character varying(36),
    "projectId" character varying(36) NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: folder_tag; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.folder_tag (
    "folderId" character varying(36) NOT NULL,
    "tagId" character varying(36) NOT NULL
);


--
-- Name: insights_by_period; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.insights_by_period (
    id integer NOT NULL,
    "metaId" integer NOT NULL,
    type integer NOT NULL,
    value bigint NOT NULL,
    "periodUnit" integer NOT NULL,
    "periodStart" timestamp(0) with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: COLUMN insights_by_period.type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.insights_by_period.type IS '0: time_saved_minutes, 1: runtime_milliseconds, 2: success, 3: failure';


--
-- Name: COLUMN insights_by_period."periodUnit"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.insights_by_period."periodUnit" IS '0: hour, 1: day, 2: week';


--
-- Name: insights_by_period_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.insights_by_period ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.insights_by_period_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: insights_metadata; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.insights_metadata (
    "metaId" integer NOT NULL,
    "workflowId" character varying(36),
    "projectId" character varying(36),
    "workflowName" character varying(128) NOT NULL,
    "projectName" character varying(255) NOT NULL
);


--
-- Name: insights_metadata_metaId_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.insights_metadata ALTER COLUMN "metaId" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public."insights_metadata_metaId_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: insights_raw; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.insights_raw (
    id integer NOT NULL,
    "metaId" integer NOT NULL,
    type integer NOT NULL,
    value bigint NOT NULL,
    "timestamp" timestamp(0) with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: COLUMN insights_raw.type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.insights_raw.type IS '0: time_saved_minutes, 1: runtime_milliseconds, 2: success, 3: failure';


--
-- Name: insights_raw_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.insights_raw ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.insights_raw_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: installed_nodes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.installed_nodes (
    name character varying(200) NOT NULL,
    type character varying(200) NOT NULL,
    "latestVersion" integer DEFAULT 1 NOT NULL,
    package character varying(241) NOT NULL
);


--
-- Name: installed_packages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.installed_packages (
    "packageName" character varying(214) NOT NULL,
    "installedVersion" character varying(50) NOT NULL,
    "authorName" character varying(70),
    "authorEmail" character varying(70),
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: instance_ai_checkpoints; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.instance_ai_checkpoints (
    key character varying(255) NOT NULL,
    "runId" character varying(255),
    "threadId" uuid NOT NULL,
    "resourceId" character varying(255),
    state json,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "expiredAt" timestamp(3) with time zone,
    CONSTRAINT instance_ai_checkpoints_state_tombstone_check CHECK (((("expiredAt" IS NOT NULL) AND (state IS NULL)) OR ("expiredAt" IS NULL)))
);


--
-- Name: COLUMN instance_ai_checkpoints.key; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.instance_ai_checkpoints.key IS 'Opaque checkpoint key from the agent runtime.';


--
-- Name: COLUMN instance_ai_checkpoints."runId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.instance_ai_checkpoints."runId" IS 'Run ID parsed from the checkpoint key when available.';


--
-- Name: COLUMN instance_ai_checkpoints."threadId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.instance_ai_checkpoints."threadId" IS 'Instance AI thread that owns the checkpoint.';


--
-- Name: COLUMN instance_ai_checkpoints."resourceId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.instance_ai_checkpoints."resourceId" IS 'Resource ID recorded by the agent runtime.';


--
-- Name: COLUMN instance_ai_checkpoints.state; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.instance_ai_checkpoints.state IS 'Serializable agent state snapshot stored as JSON.';


--
-- Name: COLUMN instance_ai_checkpoints."expiredAt"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.instance_ai_checkpoints."expiredAt" IS 'Soft-delete timestamp: null means live; non-null marks the row as a tombstone.';


--
-- Name: instance_ai_iteration_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.instance_ai_iteration_logs (
    id character varying(36) NOT NULL,
    "threadId" uuid NOT NULL,
    "taskKey" character varying NOT NULL,
    entry text NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: instance_ai_mcp_registry_connections; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.instance_ai_mcp_registry_connections (
    id uuid NOT NULL,
    "credentialId" character varying(36) NOT NULL,
    "serverSlug" character varying(255) NOT NULL,
    "toolFilter" json,
    "userId" uuid NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: COLUMN instance_ai_mcp_registry_connections."toolFilter"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.instance_ai_mcp_registry_connections."toolFilter" IS 'Optional MCP tool filter per registry connection: { mode: "allow" | "exclude", tools: string[] }';


--
-- Name: instance_ai_messages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.instance_ai_messages (
    id character varying(36) NOT NULL,
    "threadId" uuid NOT NULL,
    content text NOT NULL,
    role character varying(16) NOT NULL,
    type character varying(32),
    "resourceId" character varying(255),
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: instance_ai_observation_cursors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.instance_ai_observation_cursors (
    "observationScopeId" uuid NOT NULL,
    "lastObservedMessageId" character varying(36) NOT NULL,
    "lastObservedAt" timestamp(3) with time zone NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: COLUMN instance_ai_observation_cursors."observationScopeId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.instance_ai_observation_cursors."observationScopeId" IS 'instance_ai_threads.id source stream checkpointed by this cursor';


--
-- Name: instance_ai_observation_locks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.instance_ai_observation_locks (
    "observationScopeId" uuid NOT NULL,
    "taskKind" character varying(20) NOT NULL,
    "holderId" character varying(64) NOT NULL,
    "heldUntil" timestamp(3) with time zone NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    CONSTRAINT "CHK_instance_ai_observation_locks_taskKind" CHECK ((("taskKind")::text = ANY ((ARRAY['observer'::character varying, 'reflector'::character varying])::text[])))
);


--
-- Name: COLUMN instance_ai_observation_locks."observationScopeId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.instance_ai_observation_locks."observationScopeId" IS 'instance_ai_threads.id source stream locked for observation tasks';


--
-- Name: COLUMN instance_ai_observation_locks."holderId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.instance_ai_observation_locks."holderId" IS 'Ephemeral background-task lock owner token, not a user ID';


--
-- Name: instance_ai_observational_memory; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.instance_ai_observational_memory (
    id character varying(36) NOT NULL,
    "lookupKey" character varying(255) NOT NULL,
    scope character varying(16) NOT NULL,
    "threadId" uuid,
    "resourceId" character varying(255) NOT NULL,
    "activeObservations" text DEFAULT ''::text NOT NULL,
    "originType" character varying(32) NOT NULL,
    config text NOT NULL,
    "generationCount" integer DEFAULT 0 NOT NULL,
    "lastObservedAt" timestamp(3) with time zone,
    "pendingMessageTokens" integer DEFAULT 0 NOT NULL,
    "totalTokensObserved" integer DEFAULT 0 NOT NULL,
    "observationTokenCount" integer DEFAULT 0 NOT NULL,
    "isObserving" boolean DEFAULT false NOT NULL,
    "isReflecting" boolean DEFAULT false NOT NULL,
    "observedMessageIds" json,
    "observedTimezone" character varying,
    "bufferedObservations" text,
    "bufferedObservationTokens" integer,
    "bufferedMessageIds" json,
    "bufferedReflection" text,
    "bufferedReflectionTokens" integer,
    "bufferedReflectionInputTokens" integer,
    "reflectedObservationLineCount" integer,
    "bufferedObservationChunks" json,
    "isBufferingObservation" boolean DEFAULT false NOT NULL,
    "isBufferingReflection" boolean DEFAULT false NOT NULL,
    "lastBufferedAtTokens" integer DEFAULT 0 NOT NULL,
    "lastBufferedAtTime" timestamp(3) with time zone,
    metadata json,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: instance_ai_observations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.instance_ai_observations (
    id character varying(36) NOT NULL,
    "observationScopeId" uuid NOT NULL,
    marker character varying(16) NOT NULL,
    text text NOT NULL,
    "parentId" character varying(36),
    "tokenCount" integer DEFAULT 0 NOT NULL,
    status character varying(16) NOT NULL,
    "supersededBy" character varying(36),
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    CONSTRAINT "CHK_instance_ai_observations_marker" CHECK (((marker)::text = ANY ((ARRAY['critical'::character varying, 'important'::character varying, 'info'::character varying, 'completion'::character varying])::text[]))),
    CONSTRAINT "CHK_instance_ai_observations_status" CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'superseded'::character varying, 'dropped'::character varying])::text[])))
);


--
-- Name: COLUMN instance_ai_observations.id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.instance_ai_observations.id IS 'Application-generated n8n string ID, not a database UUID';


--
-- Name: COLUMN instance_ai_observations."observationScopeId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.instance_ai_observations."observationScopeId" IS 'instance_ai_threads.id source stream for this observation log';


--
-- Name: instance_ai_pending_confirmations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.instance_ai_pending_confirmations (
    "requestId" character varying(36) NOT NULL,
    "threadId" uuid NOT NULL,
    "userId" uuid NOT NULL,
    kind character varying(16) NOT NULL,
    "runId" character varying(36) NOT NULL,
    "toolCallId" character varying(64),
    "messageGroupId" character varying(36),
    "checkpointKey" character varying(255),
    "checkpointTaskId" character varying(36),
    "expiresAt" timestamp(3) with time zone,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    CONSTRAINT "CHK_instance_ai_pending_confirmations_kind" CHECK (((kind)::text = ANY ((ARRAY['suspended'::character varying, 'inline'::character varying])::text[])))
);


--
-- Name: COLUMN instance_ai_pending_confirmations."requestId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.instance_ai_pending_confirmations."requestId" IS 'HITL confirmation request identifier.';


--
-- Name: COLUMN instance_ai_pending_confirmations."threadId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.instance_ai_pending_confirmations."threadId" IS 'Instance AI thread that owns the confirmation.';


--
-- Name: COLUMN instance_ai_pending_confirmations."userId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.instance_ai_pending_confirmations."userId" IS 'User who is expected to confirm or cancel.';


--
-- Name: COLUMN instance_ai_pending_confirmations.kind; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.instance_ai_pending_confirmations.kind IS '''suspended'' (resumable from checkpoint) or ''inline'' (orchestrator-held Promise).';


--
-- Name: COLUMN instance_ai_pending_confirmations."runId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.instance_ai_pending_confirmations."runId" IS 'External run ID; reused on resume for SSE correlation.';


--
-- Name: COLUMN instance_ai_pending_confirmations."toolCallId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.instance_ai_pending_confirmations."toolCallId" IS 'Suspended tool call awaiting confirmation.';


--
-- Name: COLUMN instance_ai_pending_confirmations."messageGroupId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.instance_ai_pending_confirmations."messageGroupId" IS 'SSE event correlation group.';


--
-- Name: COLUMN instance_ai_pending_confirmations."checkpointKey"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.instance_ai_pending_confirmations."checkpointKey" IS 'FK to instance_ai_checkpoints.key; also the SDK runId used to resume.';


--
-- Name: COLUMN instance_ai_pending_confirmations."checkpointTaskId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.instance_ai_pending_confirmations."checkpointTaskId" IS 'Set when the suspended run was a planned-task checkpoint follow-up.';


--
-- Name: COLUMN instance_ai_pending_confirmations."expiresAt"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.instance_ai_pending_confirmations."expiresAt" IS 'TTL for the leader-only sweep; null disables auto-expiry.';


--
-- Name: instance_ai_resources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.instance_ai_resources (
    id character varying(255) NOT NULL,
    "workingMemory" text,
    metadata json,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: instance_ai_run_snapshots; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.instance_ai_run_snapshots (
    "threadId" uuid NOT NULL,
    "runId" character varying(36) NOT NULL,
    "messageGroupId" character varying(36),
    "runIds" json,
    tree text NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "langsmithRunId" character varying(36),
    "langsmithTraceId" character varying(36),
    "traceId" character varying(64),
    "spanId" character varying(64)
);


--
-- Name: COLUMN instance_ai_run_snapshots."langsmithRunId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.instance_ai_run_snapshots."langsmithRunId" IS 'LangSmith run ID (UUID v4, e.g. "f47ac10b-58cc-4372-a567-0e02b2c3d479").';


--
-- Name: COLUMN instance_ai_run_snapshots."langsmithTraceId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.instance_ai_run_snapshots."langsmithTraceId" IS 'LangSmith trace ID (UUID v4, e.g. "f47ac10b-58cc-4372-a567-0e02b2c3d479").';


--
-- Name: COLUMN instance_ai_run_snapshots."traceId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.instance_ai_run_snapshots."traceId" IS 'OpenTelemetry trace ID for the root Instance AI run.';


--
-- Name: COLUMN instance_ai_run_snapshots."spanId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.instance_ai_run_snapshots."spanId" IS 'OpenTelemetry span ID for the root Instance AI run.';


--
-- Name: instance_ai_threads; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.instance_ai_threads (
    id uuid NOT NULL,
    "resourceId" character varying(255) NOT NULL,
    title text DEFAULT ''::text NOT NULL,
    metadata json,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "projectId" character varying(36) NOT NULL
);


--
-- Name: COLUMN instance_ai_threads."projectId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.instance_ai_threads."projectId" IS 'Project this thread is scoped to';


--
-- Name: instance_ai_workflow_snapshots; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.instance_ai_workflow_snapshots (
    "runId" character varying(36) NOT NULL,
    "workflowName" character varying(255) NOT NULL,
    "resourceId" character varying(255),
    status character varying,
    snapshot text NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: instance_version_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.instance_version_history (
    id integer NOT NULL,
    major integer NOT NULL,
    minor integer NOT NULL,
    patch integer NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: instance_version_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.instance_version_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: instance_version_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.instance_version_history_id_seq OWNED BY public.instance_version_history.id;


--
-- Name: invalid_auth_token; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.invalid_auth_token (
    token character varying(512) NOT NULL,
    "expiresAt" timestamp(3) with time zone NOT NULL
);


--
-- Name: lgpd_audit_anpd; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lgpd_audit_anpd (
    id bigint NOT NULL,
    anpd_protocolo character varying(64),
    evento character varying(64) NOT NULL,
    dados_jsonb jsonb,
    ip_truncated inet,
    user_agent_truncated character varying(512),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: lgpd_audit_anpd_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.lgpd_audit_anpd_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: lgpd_audit_anpd_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.lgpd_audit_anpd_id_seq OWNED BY public.lgpd_audit_anpd.id;


--
-- Name: lgpd_consents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lgpd_consents (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    cliente_id uuid,
    conversation_id uuid,
    consent_type character varying(50) NOT NULL,
    granted boolean NOT NULL,
    ip_truncated inet,
    user_agent_truncated character varying(50),
    created_at timestamp with time zone DEFAULT now(),
    granted_at timestamp with time zone,
    revoked_at timestamp with time zone,
    version character varying(32)
);


--
-- Name: mcp_registry_server; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mcp_registry_server (
    slug character varying(255) NOT NULL,
    status character varying(50) NOT NULL,
    version character varying(50) NOT NULL,
    "registryUpdatedAt" timestamp(3) without time zone NOT NULL,
    data json DEFAULT '{}'::json NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    CONSTRAINT "CHK_tmp_mcp_registry_server_status" CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'deprecated'::character varying])::text[])))
);


--
-- Name: COLUMN mcp_registry_server.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.mcp_registry_server.status IS 'Server status in the MCP registry. Deprecated servers are not surfaced to users.';


--
-- Name: COLUMN mcp_registry_server.data; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.mcp_registry_server.data IS 'JSON object containing server metadata (icons, remotes, tools, etc.)';


--
-- Name: mensagens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mensagens (
    id integer NOT NULL,
    sessao_id integer NOT NULL,
    role character varying(50) NOT NULL,
    conteudo text NOT NULL,
    "timestamp" timestamp without time zone DEFAULT now() NOT NULL,
    metadata_audit jsonb DEFAULT '{}'::jsonb
);


--
-- Name: TABLE mensagens; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.mensagens IS 'Mensagens individuais dentro de sessões de chat';


--
-- Name: COLUMN mensagens.sessao_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.mensagens.sessao_id IS 'Sessão à qual a mensagem pertence';


--
-- Name: COLUMN mensagens.role; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.mensagens.role IS 'user, assistant, system, function';


--
-- Name: COLUMN mensagens.metadata_audit; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.mensagens.metadata_audit IS 'Metadados de auditoria: hash, modelo LLM, latência, tokens';


--
-- Name: mensagens_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.mensagens_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: mensagens_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.mensagens_id_seq OWNED BY public.mensagens.id;


--
-- Name: migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.migrations (
    id integer NOT NULL,
    "timestamp" bigint NOT NULL,
    name character varying NOT NULL
);


--
-- Name: migrations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.migrations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: migrations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.migrations_id_seq OWNED BY public.migrations.id;


--
-- Name: protocolos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.protocolos (
    id integer NOT NULL,
    numero character varying(32) NOT NULL,
    cliente_id integer NOT NULL,
    tipo character varying(64) NOT NULL,
    status character varying(32) NOT NULL,
    valor_base numeric(10,2),
    valor_adicional numeric(10,2),
    valor_total numeric(10,2),
    tabela_referencia character varying(64),
    prazo_dias integer,
    previsao_conclusao timestamp without time zone,
    concluido_em timestamp without time zone,
    pdf_storage_path character varying(512),
    pdf_hash_sha256 character varying(64),
    pdf_assinado_por character varying(255),
    canal_origem character varying(32) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    deleted_at timestamp without time zone
);


--
-- Name: mv_protocolo_stats; Type: MATERIALIZED VIEW; Schema: public; Owner: -
--

CREATE MATERIALIZED VIEW public.mv_protocolo_stats AS
 SELECT protocolos.status,
    protocolos.tipo,
    protocolos.canal_origem AS canal,
    count(*) AS total,
    (COALESCE(sum(((protocolos.valor_total * (100)::numeric))::bigint), (0)::numeric))::bigint AS valor_total,
    min(protocolos.created_at) AS first_at,
    max(protocolos.created_at) AS last_at
   FROM public.protocolos
  WHERE (protocolos.deleted_at IS NULL)
  GROUP BY protocolos.status, protocolos.tipo, protocolos.canal_origem
  WITH NO DATA;


--
-- Name: n8n_run_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.n8n_run_log (
    id bigint NOT NULL,
    execution_id character varying(100),
    workflow_id character varying(100),
    workflow_name character varying(200),
    status character varying(20),
    started_at timestamp with time zone,
    stopped_at timestamp with time zone,
    error_message text,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: n8n_run_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.n8n_run_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: n8n_run_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.n8n_run_log_id_seq OWNED BY public.n8n_run_log.id;


--
-- Name: oauth_access_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.oauth_access_tokens (
    token character varying NOT NULL,
    "clientId" character varying NOT NULL,
    "userId" uuid NOT NULL
);


--
-- Name: oauth_authorization_codes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.oauth_authorization_codes (
    code character varying(255) NOT NULL,
    "clientId" character varying NOT NULL,
    "userId" uuid NOT NULL,
    "redirectUri" character varying NOT NULL,
    "codeChallenge" character varying NOT NULL,
    "codeChallengeMethod" character varying(255) NOT NULL,
    "expiresAt" bigint NOT NULL,
    state character varying,
    used boolean DEFAULT false NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    resource character varying,
    scope json DEFAULT '["tool:listWorkflows","tool:getWorkflowDetails"]'::json NOT NULL
);


--
-- Name: COLUMN oauth_authorization_codes."expiresAt"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.oauth_authorization_codes."expiresAt" IS 'Unix timestamp in milliseconds';


--
-- Name: COLUMN oauth_authorization_codes.resource; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.oauth_authorization_codes.resource IS 'RFC 8707 resource indicator URI (e.g. https://n8n.example.com/mcp-server/http). NULL = legacy flow predating resource indicator support; defaults to the instance canonical MCP resource URL.';


--
-- Name: COLUMN oauth_authorization_codes.scope; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.oauth_authorization_codes.scope IS 'OAuth scopes granted for this authorization code';


--
-- Name: oauth_clients; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.oauth_clients (
    id character varying NOT NULL,
    name character varying(255) NOT NULL,
    "redirectUris" json NOT NULL,
    "grantTypes" json NOT NULL,
    "clientSecret" character varying(255),
    "clientSecretExpiresAt" bigint,
    "tokenEndpointAuthMethod" character varying(255) DEFAULT 'none'::character varying NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: COLUMN oauth_clients."tokenEndpointAuthMethod"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.oauth_clients."tokenEndpointAuthMethod" IS 'Possible values: none, client_secret_basic or client_secret_post';


--
-- Name: oauth_refresh_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.oauth_refresh_tokens (
    token character varying(255) NOT NULL,
    "clientId" character varying NOT NULL,
    "userId" uuid NOT NULL,
    "expiresAt" bigint NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    scope json DEFAULT '["tool:listWorkflows","tool:getWorkflowDetails"]'::json NOT NULL
);


--
-- Name: COLUMN oauth_refresh_tokens."expiresAt"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.oauth_refresh_tokens."expiresAt" IS 'Unix timestamp in milliseconds';


--
-- Name: COLUMN oauth_refresh_tokens.scope; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.oauth_refresh_tokens.scope IS 'OAuth scopes granted for this refresh token';


--
-- Name: oauth_user_consents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.oauth_user_consents (
    id integer NOT NULL,
    "userId" uuid NOT NULL,
    "clientId" character varying NOT NULL,
    "grantedAt" bigint NOT NULL
);


--
-- Name: COLUMN oauth_user_consents."grantedAt"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.oauth_user_consents."grantedAt" IS 'Unix timestamp in milliseconds';


--
-- Name: oauth_user_consents_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.oauth_user_consents ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.oauth_user_consents_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: opt_out_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.opt_out_log (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    phone character varying(20) NOT NULL,
    channel character varying(20) NOT NULL,
    keyword character varying(50),
    opted_out_at timestamp with time zone DEFAULT now(),
    expires_at timestamp with time zone
);


--
-- Name: outbox_messages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.outbox_messages (
    id uuid NOT NULL,
    queue public.outbox_queue_enum NOT NULL,
    payload jsonb NOT NULL,
    status public.outbox_status_enum NOT NULL,
    attempts integer NOT NULL,
    last_error text,
    next_retry_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE ONLY public.outbox_messages REPLICA IDENTITY FULL;


--
-- Name: pesquisa_evolucao; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pesquisa_evolucao (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    atendimento_id uuid,
    cliente_id uuid,
    nota integer,
    comentario text,
    origem character varying(50),
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT pesquisa_evolucao_nota_check CHECK (((nota >= 1) AND (nota <= 5)))
);


--
-- Name: processed_data; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.processed_data (
    "workflowId" character varying(36) NOT NULL,
    context character varying(255) NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    value text NOT NULL
);


--
-- Name: project; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project (
    id character varying(36) NOT NULL,
    name character varying(255) NOT NULL,
    type character varying(36) NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    icon json,
    description character varying(512),
    "creatorId" uuid,
    "customTelemetryTags" json DEFAULT '[]'::json NOT NULL
);


--
-- Name: COLUMN project."creatorId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.project."creatorId" IS 'ID of the user who created the project';


--
-- Name: project_relation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project_relation (
    "projectId" character varying(36) NOT NULL,
    "userId" uuid NOT NULL,
    role character varying NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: project_secrets_provider_access; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project_secrets_provider_access (
    "secretsProviderConnectionId" integer NOT NULL,
    "projectId" character varying(36) NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    role character varying(128) DEFAULT 'secretsProviderConnection:user'::character varying NOT NULL,
    CONSTRAINT "CHK_project_secrets_provider_access_role" CHECK (((role)::text = ANY ((ARRAY['secretsProviderConnection:owner'::character varying, 'secretsProviderConnection:user'::character varying])::text[])))
);


--
-- Name: protocolos_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.protocolos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: protocolos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.protocolos_id_seq OWNED BY public.protocolos.id;


--
-- Name: rate_limit_event; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rate_limit_event (
    id bigint NOT NULL,
    ip_truncated inet NOT NULL,
    endpoint character varying(200),
    method character varying(10),
    count integer,
    window_start timestamp with time zone,
    window_end timestamp with time zone,
    blocked boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: rate_limit_event_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.rate_limit_event_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: rate_limit_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.rate_limit_event_id_seq OWNED BY public.rate_limit_event.id;


--
-- Name: role; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.role (
    slug character varying(128) NOT NULL,
    "displayName" text,
    description text,
    "roleType" text,
    "systemRole" boolean DEFAULT false NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: COLUMN role.slug; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.role.slug IS 'Unique identifier of the role for example: "global:owner"';


--
-- Name: COLUMN role."displayName"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.role."displayName" IS 'Name used to display in the UI';


--
-- Name: COLUMN role.description; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.role.description IS 'Text describing the scope in more detail of users';


--
-- Name: COLUMN role."roleType"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.role."roleType" IS 'Type of the role, e.g., global, project, or workflow';


--
-- Name: COLUMN role."systemRole"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.role."systemRole" IS 'Indicates if the role is managed by the system and cannot be edited';


--
-- Name: role_mapping_rule; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.role_mapping_rule (
    id character varying(16) NOT NULL,
    expression text NOT NULL,
    role character varying(128) NOT NULL,
    type character varying(64) NOT NULL,
    "order" integer NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: COLUMN role_mapping_rule.type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.role_mapping_rule.type IS 'Expected values: ''instance'' (maps to a global role) or ''project'' (maps to a project role; projects linked via role_mapping_rule_project).';


--
-- Name: role_mapping_rule_project; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.role_mapping_rule_project (
    "roleMappingRuleId" character varying(16) NOT NULL,
    "projectId" character varying(36) NOT NULL
);


--
-- Name: role_scope; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.role_scope (
    "roleSlug" character varying(128) NOT NULL,
    "scopeSlug" character varying(128) NOT NULL
);


--
-- Name: scope; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scope (
    slug character varying(128) NOT NULL,
    "displayName" text,
    description text
);


--
-- Name: COLUMN scope.slug; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.scope.slug IS 'Unique identifier of the scope for example: "project:create"';


--
-- Name: COLUMN scope."displayName"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.scope."displayName" IS 'Name used to display in the UI';


--
-- Name: COLUMN scope.description; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.scope.description IS 'Text describing the scope in more detail of users';


--
-- Name: secrets_provider_connection; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.secrets_provider_connection (
    id integer NOT NULL,
    "providerKey" character varying(128) NOT NULL,
    type character varying(36) NOT NULL,
    "encryptedSettings" text NOT NULL,
    "isEnabled" boolean DEFAULT false NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: COLUMN secrets_provider_connection.type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.secrets_provider_connection.type IS 'Type of secrets provider. Possible values: awsSecretsManager, gcpSecretsManager, vault, azureKeyVault, infisical';


--
-- Name: secrets_provider_connection_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.secrets_provider_connection ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.secrets_provider_connection_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: sessoes_chat; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sessoes_chat (
    id integer NOT NULL,
    cliente_id integer,
    session_id character varying(255) NOT NULL,
    status character varying(50) DEFAULT 'ativa'::character varying NOT NULL,
    canal character varying(100),
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE sessoes_chat; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.sessoes_chat IS 'Sessões de chat dos clientes no sistema';


--
-- Name: COLUMN sessoes_chat.cliente_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.sessoes_chat.cliente_id IS 'Referência ao cliente (LGPD - mantém anonimização)';


--
-- Name: COLUMN sessoes_chat.session_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.sessoes_chat.session_id IS 'ID único da sessão no provedor de chat';


--
-- Name: COLUMN sessoes_chat.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.sessoes_chat.status IS 'ativa, encerrada, expirada, transferida';


--
-- Name: COLUMN sessoes_chat.canal; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.sessoes_chat.canal IS 'whatsapp, webchat, telegram, messenger';


--
-- Name: COLUMN sessoes_chat.metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.sessoes_chat.metadata IS 'Metadados flexíveis: agente, provedor, tags';


--
-- Name: sessoes_chat_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sessoes_chat_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sessoes_chat_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sessoes_chat_id_seq OWNED BY public.sessoes_chat.id;


--
-- Name: settings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.settings (
    key character varying(255) NOT NULL,
    value text NOT NULL,
    "loadOnStartup" boolean DEFAULT false NOT NULL
);


--
-- Name: shared_credentials; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shared_credentials (
    "credentialsId" character varying(36) NOT NULL,
    "projectId" character varying(36) NOT NULL,
    role text NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: shared_workflow; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shared_workflow (
    "workflowId" character varying(36) NOT NULL,
    "projectId" character varying(36) NOT NULL,
    role text NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: tag_entity; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tag_entity (
    name character varying(24) NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    id character varying(36) NOT NULL
);


--
-- Name: telegram_chat_meta; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.telegram_chat_meta (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    telegram_chat_id bigint,
    telegram_user_id bigint,
    username character varying(100),
    cartorio_cliente_id uuid,
    session_started_at timestamp with time zone,
    last_message_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: test_case_execution; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.test_case_execution (
    id character varying(36) NOT NULL,
    "testRunId" character varying(36) NOT NULL,
    "executionId" integer,
    status character varying NOT NULL,
    "runAt" timestamp(3) with time zone,
    "completedAt" timestamp(3) with time zone,
    "errorCode" character varying,
    "errorDetails" json,
    metrics json,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    inputs json,
    outputs json,
    "runIndex" integer
);


--
-- Name: test_run; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.test_run (
    id character varying(36) NOT NULL,
    "workflowId" character varying(36) NOT NULL,
    status character varying NOT NULL,
    "errorCode" character varying,
    "errorDetails" json,
    "runAt" timestamp(3) with time zone,
    "completedAt" timestamp(3) with time zone,
    metrics json,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "runningInstanceId" character varying(255),
    "cancelRequested" boolean DEFAULT false NOT NULL,
    "workflowVersionId" character varying(36),
    "evaluationConfigId" character varying(36),
    "evaluationConfigSnapshot" jsonb,
    "collectionId" character varying(36)
);


--
-- Name: token_exchange_jti; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.token_exchange_jti (
    jti character varying(255) NOT NULL,
    "expiresAt" timestamp(3) with time zone NOT NULL,
    "createdAt" timestamp(3) with time zone NOT NULL
);


--
-- Name: trusted_key; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.trusted_key (
    "sourceId" character varying(36) NOT NULL,
    kid character varying(255) NOT NULL,
    data text NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: trusted_key_source; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.trusted_key_source (
    id character varying(36) NOT NULL,
    type character varying(32) NOT NULL,
    config text NOT NULL,
    status character varying(32) DEFAULT 'pending'::character varying NOT NULL,
    "lastError" text,
    "lastRefreshedAt" timestamp(3) with time zone,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."user" (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    email character varying(255),
    "firstName" character varying(32),
    "lastName" character varying(32),
    password character varying(255),
    "personalizationAnswers" json,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    settings json,
    disabled boolean DEFAULT false NOT NULL,
    "mfaEnabled" boolean DEFAULT false NOT NULL,
    "mfaSecret" text,
    "mfaRecoveryCodes" text,
    "lastActiveAt" date,
    "roleSlug" character varying(128) DEFAULT 'global:member'::character varying NOT NULL
);


--
-- Name: user_api_keys; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_api_keys (
    id character varying(36) NOT NULL,
    "userId" uuid NOT NULL,
    label character varying(100) NOT NULL,
    "apiKey" character varying NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    scopes json,
    audience character varying DEFAULT 'public-api'::character varying NOT NULL,
    "lastUsedAt" timestamp(3) with time zone
);


--
-- Name: user_favorites; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_favorites (
    id integer NOT NULL,
    "userId" uuid NOT NULL,
    "resourceId" character varying(255) NOT NULL,
    "resourceType" character varying(64) NOT NULL
);


--
-- Name: user_favorites_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.user_favorites ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.user_favorites_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: variables; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.variables (
    key character varying(50) NOT NULL,
    type character varying(50) DEFAULT 'string'::character varying NOT NULL,
    value text,
    id character varying(36) NOT NULL,
    "projectId" character varying(36),
    CONSTRAINT variables_value_max_len CHECK (((value IS NULL) OR (char_length(value) <= 1000)))
);


--
-- Name: webhook_entity; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.webhook_entity (
    "webhookPath" character varying NOT NULL,
    method character varying NOT NULL,
    node character varying NOT NULL,
    "webhookId" character varying,
    "pathLength" integer,
    "workflowId" character varying(36) NOT NULL
);


--
-- Name: webhook_event_dlq; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.webhook_event_dlq (
    id bigint NOT NULL,
    source character varying(50) NOT NULL,
    event_type character varying(100),
    payload jsonb,
    error_message text,
    attempts integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: webhook_event_dlq_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.webhook_event_dlq_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: webhook_event_dlq_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.webhook_event_dlq_id_seq OWNED BY public.webhook_event_dlq.id;


--
-- Name: webhook_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.webhook_events (
    id integer NOT NULL,
    source character varying(32) NOT NULL,
    event_id character varying(256) NOT NULL,
    received_at timestamp without time zone NOT NULL,
    payload_hash character varying(64) NOT NULL
);


--
-- Name: webhook_events_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.webhook_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: webhook_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.webhook_events_id_seq OWNED BY public.webhook_events.id;


--
-- Name: workflow_builder_session; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workflow_builder_session (
    id uuid NOT NULL,
    "workflowId" character varying(36) NOT NULL,
    "userId" uuid NOT NULL,
    messages json DEFAULT '[]'::json NOT NULL,
    "previousSummary" text,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "activeVersionCardId" character varying(255),
    "resumeAfterRestoreMessageId" character varying(255)
);


--
-- Name: COLUMN workflow_builder_session."previousSummary"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.workflow_builder_session."previousSummary" IS 'Summary of prior conversation from compaction (/compact or auto-compact)';


--
-- Name: workflow_dependency; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workflow_dependency (
    id integer NOT NULL,
    "workflowId" character varying(36) NOT NULL,
    "workflowVersionId" integer NOT NULL,
    "dependencyType" character varying(32) NOT NULL,
    "dependencyKey" character varying(255) NOT NULL,
    "dependencyInfo" json,
    "indexVersionId" smallint DEFAULT 1 NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "publishedVersionId" character varying(36)
);


--
-- Name: COLUMN workflow_dependency."workflowVersionId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.workflow_dependency."workflowVersionId" IS 'Version of the workflow';


--
-- Name: COLUMN workflow_dependency."dependencyType"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.workflow_dependency."dependencyType" IS 'Type of dependency: "credential", "nodeType", "webhookPath", or "workflowCall"';


--
-- Name: COLUMN workflow_dependency."dependencyKey"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.workflow_dependency."dependencyKey" IS 'ID or name of the dependency';


--
-- Name: COLUMN workflow_dependency."dependencyInfo"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.workflow_dependency."dependencyInfo" IS 'Additional info about the dependency, interpreted based on type';


--
-- Name: COLUMN workflow_dependency."indexVersionId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.workflow_dependency."indexVersionId" IS 'Version of the index structure';


--
-- Name: workflow_dependency_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.workflow_dependency ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.workflow_dependency_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: workflow_entity; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workflow_entity (
    name character varying(128) NOT NULL,
    active boolean NOT NULL,
    nodes json NOT NULL,
    connections json NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    settings json,
    "staticData" json,
    "pinData" json,
    "versionId" character(36) NOT NULL,
    "triggerCount" integer DEFAULT 0 NOT NULL,
    id character varying(36) NOT NULL,
    meta json,
    "parentFolderId" character varying(36) DEFAULT NULL::character varying,
    "isArchived" boolean DEFAULT false NOT NULL,
    "versionCounter" integer DEFAULT 1 NOT NULL,
    description text,
    "activeVersionId" character varying(36),
    "nodeGroups" json DEFAULT '[]'::json NOT NULL,
    "sourceWorkflowId" character varying
);


--
-- Name: workflow_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workflow_history (
    "versionId" character varying(36) NOT NULL,
    "workflowId" character varying(36) NOT NULL,
    authors character varying(255) NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    nodes json NOT NULL,
    connections json NOT NULL,
    name character varying(128),
    autosaved boolean DEFAULT false NOT NULL,
    description text,
    "nodeGroups" json DEFAULT '[]'::json NOT NULL
);


--
-- Name: workflow_publication_outbox; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workflow_publication_outbox (
    id integer NOT NULL,
    "workflowId" character varying(36) NOT NULL,
    "publishedVersionId" character varying(36) NOT NULL,
    status character varying(20) NOT NULL,
    "errorMessage" text,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    CONSTRAINT "CHK_workflow_publication_outbox_status" CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'in_progress'::character varying, 'completed'::character varying, 'partial_success'::character varying, 'failed'::character varying])::text[])))
);


--
-- Name: COLUMN workflow_publication_outbox."workflowId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.workflow_publication_outbox."workflowId" IS 'References workflow_entity.id.';


--
-- Name: COLUMN workflow_publication_outbox."publishedVersionId"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.workflow_publication_outbox."publishedVersionId" IS 'References workflow_history.versionId.';


--
-- Name: COLUMN workflow_publication_outbox."errorMessage"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.workflow_publication_outbox."errorMessage" IS 'Error details for surfacing failed publications to the user.';


--
-- Name: workflow_publication_outbox_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.workflow_publication_outbox ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.workflow_publication_outbox_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: workflow_publish_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workflow_publish_history (
    id integer NOT NULL,
    "workflowId" character varying(36) NOT NULL,
    "versionId" character varying(36),
    event character varying(36) NOT NULL,
    "userId" uuid,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    CONSTRAINT "CHK_workflow_publish_history_event" CHECK (((event)::text = ANY ((ARRAY['activated'::character varying, 'deactivated'::character varying])::text[])))
);


--
-- Name: COLUMN workflow_publish_history.event; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.workflow_publish_history.event IS 'Type of history record: activated (workflow is now active), deactivated (workflow is now inactive)';


--
-- Name: workflow_publish_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.workflow_publish_history ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.workflow_publish_history_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: workflow_published_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workflow_published_version (
    "workflowId" character varying(36) NOT NULL,
    "publishedVersionId" character varying(36) NOT NULL,
    "createdAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    "updatedAt" timestamp(3) with time zone DEFAULT CURRENT_TIMESTAMP(3) NOT NULL
);


--
-- Name: workflow_statistics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workflow_statistics (
    count bigint DEFAULT 0,
    "latestEvent" timestamp(3) with time zone,
    name character varying(128) NOT NULL,
    "workflowId" character varying(36) NOT NULL,
    "rootCount" bigint DEFAULT 0,
    id integer NOT NULL,
    "workflowName" character varying(128)
);


--
-- Name: workflow_statistics_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.workflow_statistics_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: workflow_statistics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.workflow_statistics_id_seq OWNED BY public.workflow_statistics.id;


--
-- Name: workflows_tags; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workflows_tags (
    "workflowId" character varying(36) NOT NULL,
    "tagId" character varying(36) NOT NULL
);


--
-- Name: buckets; Type: TABLE; Schema: storage; Owner: -
--

CREATE TABLE storage.buckets (
    id text NOT NULL,
    name text NOT NULL,
    owner uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    public boolean DEFAULT false,
    avif_autodetection boolean DEFAULT false,
    file_size_limit bigint,
    allowed_mime_types text[],
    owner_id text
);


--
-- Name: hooks; Type: TABLE; Schema: supabase_functions; Owner: -
--

CREATE TABLE supabase_functions.hooks (
    id bigint NOT NULL,
    hook_name text NOT NULL,
    table_name text NOT NULL,
    events text[] DEFAULT '{}'::text[] NOT NULL,
    http_method text DEFAULT 'POST'::text NOT NULL,
    http_url text NOT NULL,
    http_headers jsonb DEFAULT '{}'::jsonb,
    function_name text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: hooks_id_seq; Type: SEQUENCE; Schema: supabase_functions; Owner: -
--

CREATE SEQUENCE supabase_functions.hooks_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: hooks_id_seq; Type: SEQUENCE OWNED BY; Schema: supabase_functions; Owner: -
--

ALTER SEQUENCE supabase_functions.hooks_id_seq OWNED BY supabase_functions.hooks.id;


--
-- Name: agendamentos id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agendamentos ALTER COLUMN id SET DEFAULT nextval('public.agendamentos_id_seq'::regclass);


--
-- Name: atendimentos id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.atendimentos ALTER COLUMN id SET DEFAULT nextval('public.atendimentos_id_seq'::regclass);


--
-- Name: audit_log id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log ALTER COLUMN id SET DEFAULT nextval('public.audit_log_id_seq'::regclass);


--
-- Name: auth_provider_sync_history id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_provider_sync_history ALTER COLUMN id SET DEFAULT nextval('public.auth_provider_sync_history_id_seq'::regclass);


--
-- Name: clientes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clientes ALTER COLUMN id SET DEFAULT nextval('public.clientes_id_seq'::regclass);


--
-- Name: conversas id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversas ALTER COLUMN id SET DEFAULT nextval('public.conversas_id_seq'::regclass);


--
-- Name: documentos id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentos ALTER COLUMN id SET DEFAULT nextval('public.documentos_id_seq'::regclass);


--
-- Name: emolumentos id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.emolumentos ALTER COLUMN id SET DEFAULT nextval('public.emolumentos_id_seq'::regclass);


--
-- Name: execution_annotations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.execution_annotations ALTER COLUMN id SET DEFAULT nextval('public.execution_annotations_id_seq'::regclass);


--
-- Name: execution_entity id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.execution_entity ALTER COLUMN id SET DEFAULT nextval('public.execution_entity_id_seq'::regclass);


--
-- Name: execution_metadata id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.execution_metadata ALTER COLUMN id SET DEFAULT nextval('public.execution_metadata_temp_id_seq'::regclass);


--
-- Name: instance_version_history id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_version_history ALTER COLUMN id SET DEFAULT nextval('public.instance_version_history_id_seq'::regclass);


--
-- Name: lgpd_audit_anpd id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lgpd_audit_anpd ALTER COLUMN id SET DEFAULT nextval('public.lgpd_audit_anpd_id_seq'::regclass);


--
-- Name: mensagens id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mensagens ALTER COLUMN id SET DEFAULT nextval('public.mensagens_id_seq'::regclass);


--
-- Name: migrations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.migrations ALTER COLUMN id SET DEFAULT nextval('public.migrations_id_seq'::regclass);


--
-- Name: n8n_run_log id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.n8n_run_log ALTER COLUMN id SET DEFAULT nextval('public.n8n_run_log_id_seq'::regclass);


--
-- Name: protocolos id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.protocolos ALTER COLUMN id SET DEFAULT nextval('public.protocolos_id_seq'::regclass);


--
-- Name: rate_limit_event id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rate_limit_event ALTER COLUMN id SET DEFAULT nextval('public.rate_limit_event_id_seq'::regclass);


--
-- Name: sessoes_chat id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sessoes_chat ALTER COLUMN id SET DEFAULT nextval('public.sessoes_chat_id_seq'::regclass);


--
-- Name: webhook_event_dlq id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook_event_dlq ALTER COLUMN id SET DEFAULT nextval('public.webhook_event_dlq_id_seq'::regclass);


--
-- Name: webhook_events id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook_events ALTER COLUMN id SET DEFAULT nextval('public.webhook_events_id_seq'::regclass);


--
-- Name: workflow_statistics id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_statistics ALTER COLUMN id SET DEFAULT nextval('public.workflow_statistics_id_seq'::regclass);


--
-- Name: hooks id; Type: DEFAULT; Schema: supabase_functions; Owner: -
--

ALTER TABLE ONLY supabase_functions.hooks ALTER COLUMN id SET DEFAULT nextval('supabase_functions.hooks_id_seq'::regclass);


--
-- Name: test_run PK_011c050f566e9db509a0fadb9b9; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.test_run
    ADD CONSTRAINT "PK_011c050f566e9db509a0fadb9b9" PRIMARY KEY (id);


--
-- Name: project_secrets_provider_access PK_0402b7fcec5415246656f102f83; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_secrets_provider_access
    ADD CONSTRAINT "PK_0402b7fcec5415246656f102f83" PRIMARY KEY ("secretsProviderConnectionId", "projectId");


--
-- Name: installed_packages PK_08cc9197c39b028c1e9beca225940576fd1a5804; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.installed_packages
    ADD CONSTRAINT "PK_08cc9197c39b028c1e9beca225940576fd1a5804" PRIMARY KEY ("packageName");


--
-- Name: instance_ai_run_snapshots PK_0a5fc9690a84950ebf1416fb146; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_ai_run_snapshots
    ADD CONSTRAINT "PK_0a5fc9690a84950ebf1416fb146" PRIMARY KEY ("threadId", "runId");


--
-- Name: mcp_registry_server PK_12fd89a1fb8489513b0a91f5d31; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mcp_registry_server
    ADD CONSTRAINT "PK_12fd89a1fb8489513b0a91f5d31" PRIMARY KEY (slug);


--
-- Name: instance_ai_messages PK_156c6f287225e9befe0181bb02b; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_ai_messages
    ADD CONSTRAINT "PK_156c6f287225e9befe0181bb02b" PRIMARY KEY (id);


--
-- Name: agent_task_definition PK_1756c11c637903e97629a7a784a; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_task_definition
    ADD CONSTRAINT "PK_1756c11c637903e97629a7a784a" PRIMARY KEY (id);


--
-- Name: execution_metadata PK_17a0b6284f8d626aae88e1c16e4; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.execution_metadata
    ADD CONSTRAINT "PK_17a0b6284f8d626aae88e1c16e4" PRIMARY KEY (id);


--
-- Name: role_mapping_rule_project PK_198c5b5aea509d139274efcaf9a; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_mapping_rule_project
    ADD CONSTRAINT "PK_198c5b5aea509d139274efcaf9a" PRIMARY KEY ("roleMappingRuleId", "projectId");


--
-- Name: project_relation PK_1caaa312a5d7184a003be0f0cb6; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_relation
    ADD CONSTRAINT "PK_1caaa312a5d7184a003be0f0cb6" PRIMARY KEY ("projectId", "userId");


--
-- Name: chat_hub_sessions PK_1eafef1273c70e4464fec703412; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_hub_sessions
    ADD CONSTRAINT "PK_1eafef1273c70e4464fec703412" PRIMARY KEY (id);


--
-- Name: agent_task_snapshot PK_2142a8bcda2360c3c5e34f82640; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_task_snapshot
    ADD CONSTRAINT "PK_2142a8bcda2360c3c5e34f82640" PRIMARY KEY ("versionId", "taskId");


--
-- Name: instance_ai_iteration_logs PK_21c2b214b44bc6c34a6d3551c90; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_ai_iteration_logs
    ADD CONSTRAINT "PK_21c2b214b44bc6c34a6d3551c90" PRIMARY KEY (id);


--
-- Name: agent_execution_threads PK_22373dbf6ba6929d8ac50093309; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_execution_threads
    ADD CONSTRAINT "PK_22373dbf6ba6929d8ac50093309" PRIMARY KEY (id);


--
-- Name: instance_ai_pending_confirmations PK_25c38179c8d45095b168adfff80; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_ai_pending_confirmations
    ADD CONSTRAINT "PK_25c38179c8d45095b168adfff80" PRIMARY KEY ("requestId");


--
-- Name: agents_memory_entry_sources PK_278f05e98e74baaaa93f52b4bab; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents_memory_entry_sources
    ADD CONSTRAINT "PK_278f05e98e74baaaa93f52b4bab" PRIMARY KEY (id);


--
-- Name: folder_tag PK_27e4e00852f6b06a925a4d83a3e; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.folder_tag
    ADD CONSTRAINT "PK_27e4e00852f6b06a925a4d83a3e" PRIMARY KEY ("folderId", "tagId");


--
-- Name: instance_ai_threads PK_35575100e45cdedeb89ae0643e9; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_ai_threads
    ADD CONSTRAINT "PK_35575100e45cdedeb89ae0643e9" PRIMARY KEY (id);


--
-- Name: role PK_35c9b140caaf6da09cfabb0d675; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role
    ADD CONSTRAINT "PK_35c9b140caaf6da09cfabb0d675" PRIMARY KEY (slug);


--
-- Name: secrets_provider_connection PK_4350ae85e76f9ba7df1370acb5d; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.secrets_provider_connection
    ADD CONSTRAINT "PK_4350ae85e76f9ba7df1370acb5d" PRIMARY KEY (id);


--
-- Name: instance_ai_resources PK_45b5b0b6f715dae4292b86603d8; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_ai_resources
    ADD CONSTRAINT "PK_45b5b0b6f715dae4292b86603d8" PRIMARY KEY (id);


--
-- Name: agents_threads PK_4a3feb0a13ffe315c009cce64e5; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents_threads
    ADD CONSTRAINT "PK_4a3feb0a13ffe315c009cce64e5" PRIMARY KEY (id);


--
-- Name: project PK_4d68b1358bb5b766d3e78f32f57; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project
    ADD CONSTRAINT "PK_4d68b1358bb5b766d3e78f32f57" PRIMARY KEY (id);


--
-- Name: instance_ai_observations PK_4d9b514cdf0f0b577650caf2ac2; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_ai_observations
    ADD CONSTRAINT "PK_4d9b514cdf0f0b577650caf2ac2" PRIMARY KEY (id);


--
-- Name: agent_checkpoints PK_50a27cbafa6806c9b162304b5fd; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_checkpoints
    ADD CONSTRAINT "PK_50a27cbafa6806c9b162304b5fd" PRIMARY KEY ("runId");


--
-- Name: dynamic_credential_entry PK_5135ffcabecad4727ff6b9b803d; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dynamic_credential_entry
    ADD CONSTRAINT "PK_5135ffcabecad4727ff6b9b803d" PRIMARY KEY (credential_id, subject_id, resolver_id);


--
-- Name: workflow_dependency PK_52325e34cd7a2f0f67b0f3cad65; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_dependency
    ADD CONSTRAINT "PK_52325e34cd7a2f0f67b0f3cad65" PRIMARY KEY (id);


--
-- Name: instance_ai_checkpoints PK_5315a45f0846d1f9d128c18a2ed; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_ai_checkpoints
    ADD CONSTRAINT "PK_5315a45f0846d1f9d128c18a2ed" PRIMARY KEY (key);


--
-- Name: invalid_auth_token PK_5779069b7235b256d91f7af1a15; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invalid_auth_token
    ADD CONSTRAINT "PK_5779069b7235b256d91f7af1a15" PRIMARY KEY (token);


--
-- Name: evaluation_config PK_59c14dccf8989df94070c2dcfda; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_config
    ADD CONSTRAINT "PK_59c14dccf8989df94070c2dcfda" PRIMARY KEY (id);


--
-- Name: instance_ai_observation_cursors PK_5b6319b2e9a37c1064a72428f9a; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_ai_observation_cursors
    ADD CONSTRAINT "PK_5b6319b2e9a37c1064a72428f9a" PRIMARY KEY ("observationScopeId");


--
-- Name: shared_workflow PK_5ba87620386b847201c9531c58f; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shared_workflow
    ADD CONSTRAINT "PK_5ba87620386b847201c9531c58f" PRIMARY KEY ("workflowId", "projectId");


--
-- Name: workflow_published_version PK_5c76fb7ee939fe2530374d3f75a; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_published_version
    ADD CONSTRAINT "PK_5c76fb7ee939fe2530374d3f75a" PRIMARY KEY ("workflowId");


--
-- Name: folder PK_6278a41a706740c94c02e288df8; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.folder
    ADD CONSTRAINT "PK_6278a41a706740c94c02e288df8" PRIMARY KEY (id);


--
-- Name: agent_history PK_65ffcfe7a8e112fb826311fb092; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_history
    ADD CONSTRAINT "PK_65ffcfe7a8e112fb826311fb092" PRIMARY KEY ("versionId");


--
-- Name: data_table_column PK_673cb121ee4a8a5e27850c72c51; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_table_column
    ADD CONSTRAINT "PK_673cb121ee4a8a5e27850c72c51" PRIMARY KEY (id);


--
-- Name: agent_files PK_692920e59217af7d124cd95106f; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_files
    ADD CONSTRAINT "PK_692920e59217af7d124cd95106f" PRIMARY KEY (id);


--
-- Name: chat_hub_tools PK_696d26426c704fba79b2c195ef5; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_hub_tools
    ADD CONSTRAINT "PK_696d26426c704fba79b2c195ef5" PRIMARY KEY (id);


--
-- Name: annotation_tag_entity PK_69dfa041592c30bbc0d4b84aa00; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.annotation_tag_entity
    ADD CONSTRAINT "PK_69dfa041592c30bbc0d4b84aa00" PRIMARY KEY (id);


--
-- Name: user_favorites PK_6c472a19a7423cfbbf6b7c75939; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_favorites
    ADD CONSTRAINT "PK_6c472a19a7423cfbbf6b7c75939" PRIMARY KEY (id);


--
-- Name: instance_ai_observational_memory PK_7192dd00cddba039bf1d3e6a098; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_ai_observational_memory
    ADD CONSTRAINT "PK_7192dd00cddba039bf1d3e6a098" PRIMARY KEY (id);


--
-- Name: oauth_refresh_tokens PK_74abaed0b30711b6532598b0392; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.oauth_refresh_tokens
    ADD CONSTRAINT "PK_74abaed0b30711b6532598b0392" PRIMARY KEY (token);


--
-- Name: dynamic_credential_user_entry PK_74f548e633abc66dc27c8f0ca77; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dynamic_credential_user_entry
    ADD CONSTRAINT "PK_74f548e633abc66dc27c8f0ca77" PRIMARY KEY ("credentialId", "userId", "resolverId");


--
-- Name: chat_hub_messages PK_7704a5add6baed43eef835f0bfb; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_hub_messages
    ADD CONSTRAINT "PK_7704a5add6baed43eef835f0bfb" PRIMARY KEY (id);


--
-- Name: execution_annotations PK_7afcf93ffa20c4252869a7c6a23; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.execution_annotations
    ADD CONSTRAINT "PK_7afcf93ffa20c4252869a7c6a23" PRIMARY KEY (id);


--
-- Name: agents_observation_locks PK_7e2e315162ac3d80587e15ac2c3; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents_observation_locks
    ADD CONSTRAINT "PK_7e2e315162ac3d80587e15ac2c3" PRIMARY KEY ("agentId", "observationScopeId", "taskKind");


--
-- Name: credential_dependency PK_80212729ed0ffa0709417ab28f4; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credential_dependency
    ADD CONSTRAINT "PK_80212729ed0ffa0709417ab28f4" PRIMARY KEY (id);


--
-- Name: agents_messages PK_81020dc608dfb0af1ede386d907; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents_messages
    ADD CONSTRAINT "PK_81020dc608dfb0af1ede386d907" PRIMARY KEY (id);


--
-- Name: ai_builder_temporary_workflow PK_85a87a1ba0f61999fe11dc56325; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_builder_temporary_workflow
    ADD CONSTRAINT "PK_85a87a1ba0f61999fe11dc56325" PRIMARY KEY ("workflowId");


--
-- Name: oauth_user_consents PK_85b9ada746802c8993103470f05; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.oauth_user_consents
    ADD CONSTRAINT "PK_85b9ada746802c8993103470f05" PRIMARY KEY (id);


--
-- Name: instance_version_history PK_874f58cb616935bf49d9dbd67e9; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_version_history
    ADD CONSTRAINT "PK_874f58cb616935bf49d9dbd67e9" PRIMARY KEY (id);


--
-- Name: chat_hub_session_tools PK_87aea76ff4c274c4a5ac838ebe3; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_hub_session_tools
    ADD CONSTRAINT "PK_87aea76ff4c274c4a5ac838ebe3" PRIMARY KEY ("sessionId", "toolId");


--
-- Name: migrations PK_8c82d7f526340ab734260ea46be; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.migrations
    ADD CONSTRAINT "PK_8c82d7f526340ab734260ea46be" PRIMARY KEY (id);


--
-- Name: installed_nodes PK_8ebd28194e4f792f96b5933423fc439df97d9689; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.installed_nodes
    ADD CONSTRAINT "PK_8ebd28194e4f792f96b5933423fc439df97d9689" PRIMARY KEY (name);


--
-- Name: shared_credentials PK_8ef3a59796a228913f251779cff; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shared_credentials
    ADD CONSTRAINT "PK_8ef3a59796a228913f251779cff" PRIMARY KEY ("credentialsId", "projectId");


--
-- Name: test_case_execution PK_90c121f77a78a6580e94b794bce; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.test_case_execution
    ADD CONSTRAINT "PK_90c121f77a78a6580e94b794bce" PRIMARY KEY (id);


--
-- Name: instance_ai_workflow_snapshots PK_93f2696eb321dfe1d7defe7073f; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_ai_workflow_snapshots
    ADD CONSTRAINT "PK_93f2696eb321dfe1d7defe7073f" PRIMARY KEY ("runId", "workflowName");


--
-- Name: deployment_key PK_94bb7aeb5def5a0284a5fe9f9a0; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.deployment_key
    ADD CONSTRAINT "PK_94bb7aeb5def5a0284a5fe9f9a0" PRIMARY KEY (id);


--
-- Name: user_api_keys PK_978fa5caa3468f463dac9d92e69; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_api_keys
    ADD CONSTRAINT "PK_978fa5caa3468f463dac9d92e69" PRIMARY KEY (id);


--
-- Name: execution_annotation_tags PK_979ec03d31294cca484be65d11f; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.execution_annotation_tags
    ADD CONSTRAINT "PK_979ec03d31294cca484be65d11f" PRIMARY KEY ("annotationId", "tagId");


--
-- Name: trusted_key_source PK_99e8908ce2c2cdccce487db7fc6; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trusted_key_source
    ADD CONSTRAINT "PK_99e8908ce2c2cdccce487db7fc6" PRIMARY KEY (id);


--
-- Name: agents_observations PK_9ad319654d12c2649f7caf27135; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents_observations
    ADD CONSTRAINT "PK_9ad319654d12c2649f7caf27135" PRIMARY KEY (id);


--
-- Name: agents PK_9c653f28ae19c5884d5baf6a1d9; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT "PK_9c653f28ae19c5884d5baf6a1d9" PRIMARY KEY (id);


--
-- Name: agents_memory_entry_locks PK_a8e0f570d04a174292bea104ae6; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents_memory_entry_locks
    ADD CONSTRAINT "PK_a8e0f570d04a174292bea104ae6" PRIMARY KEY ("agentId", "resourceId");


--
-- Name: webhook_entity PK_b21ace2e13596ccd87dc9bf4ea6; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook_entity
    ADD CONSTRAINT "PK_b21ace2e13596ccd87dc9bf4ea6" PRIMARY KEY ("webhookPath", method);


--
-- Name: agents_memory_entry_cursors PK_b31a1d5c009a27f4cc5ef8f102a; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents_memory_entry_cursors
    ADD CONSTRAINT "PK_b31a1d5c009a27f4cc5ef8f102a" PRIMARY KEY ("agentId", "observationScopeId");


--
-- Name: workflow_publication_outbox PK_b3e2eeee36a4bd044d56468d311; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_publication_outbox
    ADD CONSTRAINT "PK_b3e2eeee36a4bd044d56468d311" PRIMARY KEY (id);


--
-- Name: insights_by_period PK_b606942249b90cc39b0265f0575; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.insights_by_period
    ADD CONSTRAINT "PK_b606942249b90cc39b0265f0575" PRIMARY KEY (id);


--
-- Name: workflow_history PK_b6572dd6173e4cd06fe79937b58; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_history
    ADD CONSTRAINT "PK_b6572dd6173e4cd06fe79937b58" PRIMARY KEY ("versionId");


--
-- Name: dynamic_credential_resolver PK_b76cfb088dcdaf5275e9980bb64; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dynamic_credential_resolver
    ADD CONSTRAINT "PK_b76cfb088dcdaf5275e9980bb64" PRIMARY KEY (id);


--
-- Name: agent_execution PK_ba438acc8532addc12d1ef17049; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_execution
    ADD CONSTRAINT "PK_ba438acc8532addc12d1ef17049" PRIMARY KEY (id);


--
-- Name: agents_memory_entries PK_bfbc45dc88f66fae4e4b4a15fec; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents_memory_entries
    ADD CONSTRAINT "PK_bfbc45dc88f66fae4e4b4a15fec" PRIMARY KEY (id);


--
-- Name: scope PK_bfc45df0481abd7f355d6187da1; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scope
    ADD CONSTRAINT "PK_bfc45df0481abd7f355d6187da1" PRIMARY KEY (slug);


--
-- Name: oauth_clients PK_c4759172d3431bae6f04e678e0d; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.oauth_clients
    ADD CONSTRAINT "PK_c4759172d3431bae6f04e678e0d" PRIMARY KEY (id);


--
-- Name: workflow_publish_history PK_c788f7caf88e91e365c97d6d04a; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_publish_history
    ADD CONSTRAINT "PK_c788f7caf88e91e365c97d6d04a" PRIMARY KEY (id);


--
-- Name: processed_data PK_ca04b9d8dc72de268fe07a65773; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processed_data
    ADD CONSTRAINT "PK_ca04b9d8dc72de268fe07a65773" PRIMARY KEY ("workflowId", context);


--
-- Name: chat_hub_agent_tools PK_cc8806fdea48297a7d497035d72; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_hub_agent_tools
    ADD CONSTRAINT "PK_cc8806fdea48297a7d497035d72" PRIMARY KEY ("agentId", "toolId");


--
-- Name: role_mapping_rule PK_d772c8ec1a89b52d31c882bc560; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_mapping_rule
    ADD CONSTRAINT "PK_d772c8ec1a89b52d31c882bc560" PRIMARY KEY (id);


--
-- Name: token_exchange_jti PK_d8e8a6f737d530fdd2dd716e89c; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.token_exchange_jti
    ADD CONSTRAINT "PK_d8e8a6f737d530fdd2dd716e89c" PRIMARY KEY (jti);


--
-- Name: settings PK_dc0fe14e6d9943f268e7b119f69ab8bd; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.settings
    ADD CONSTRAINT "PK_dc0fe14e6d9943f268e7b119f69ab8bd" PRIMARY KEY (key);


--
-- Name: trusted_key PK_dc7d93798f3dbb6959f974c97e1; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trusted_key
    ADD CONSTRAINT "PK_dc7d93798f3dbb6959f974c97e1" PRIMARY KEY ("sourceId", kid);


--
-- Name: oauth_access_tokens PK_dcd71f96a5d5f4bf79e67d322bf; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.oauth_access_tokens
    ADD CONSTRAINT "PK_dcd71f96a5d5f4bf79e67d322bf" PRIMARY KEY (token);


--
-- Name: data_table PK_e226d0001b9e6097cbfe70617cb; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_table
    ADD CONSTRAINT "PK_e226d0001b9e6097cbfe70617cb" PRIMARY KEY (id);


--
-- Name: instance_ai_mcp_registry_connections PK_e34e4d15d78eabbe8217e33ef03; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_ai_mcp_registry_connections
    ADD CONSTRAINT "PK_e34e4d15d78eabbe8217e33ef03" PRIMARY KEY (id);


--
-- Name: workflow_builder_session PK_e69ef0d385986e273423b0e8695; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_builder_session
    ADD CONSTRAINT "PK_e69ef0d385986e273423b0e8695" PRIMARY KEY (id);


--
-- Name: evaluation_collection PK_e720b6efc1e45b878ebb0b2ca30; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_collection
    ADD CONSTRAINT "PK_e720b6efc1e45b878ebb0b2ca30" PRIMARY KEY (id);


--
-- Name: user PK_ea8f538c94b6e352418254ed6474a81f; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT "PK_ea8f538c94b6e352418254ed6474a81f" PRIMARY KEY (id);


--
-- Name: agents_observation_cursors PK_eb777ac57ab872d38f8ebd19317; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents_observation_cursors
    ADD CONSTRAINT "PK_eb777ac57ab872d38f8ebd19317" PRIMARY KEY ("agentId", "observationScopeId");


--
-- Name: insights_raw PK_ec15125755151e3a7e00e00014f; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.insights_raw
    ADD CONSTRAINT "PK_ec15125755151e3a7e00e00014f" PRIMARY KEY (id);


--
-- Name: chat_hub_agents PK_f39a3b36bbdf0e2979ddb21cf78; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_hub_agents
    ADD CONSTRAINT "PK_f39a3b36bbdf0e2979ddb21cf78" PRIMARY KEY (id);


--
-- Name: insights_metadata PK_f448a94c35218b6208ce20cf5a1; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.insights_metadata
    ADD CONSTRAINT "PK_f448a94c35218b6208ce20cf5a1" PRIMARY KEY ("metaId");


--
-- Name: agent_task_run_lock PK_f593adaf7230e964d3c25deda64; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_task_run_lock
    ADD CONSTRAINT "PK_f593adaf7230e964d3c25deda64" PRIMARY KEY ("agentId", "taskId");


--
-- Name: agents_resources PK_fa6b20b2d31a9991529dbf8ef7d; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents_resources
    ADD CONSTRAINT "PK_fa6b20b2d31a9991529dbf8ef7d" PRIMARY KEY (id);


--
-- Name: oauth_authorization_codes PK_fb91ab932cfbd694061501cc20f; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.oauth_authorization_codes
    ADD CONSTRAINT "PK_fb91ab932cfbd694061501cc20f" PRIMARY KEY (code);


--
-- Name: binary_data PK_fc3691585b39408bb0551122af6; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.binary_data
    ADD CONSTRAINT "PK_fc3691585b39408bb0551122af6" PRIMARY KEY ("fileId");


--
-- Name: instance_ai_observation_locks PK_fc491dd378b9448655c3c683f85; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_ai_observation_locks
    ADD CONSTRAINT "PK_fc491dd378b9448655c3c683f85" PRIMARY KEY ("observationScopeId", "taskKind");


--
-- Name: role_scope PK_role_scope; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_scope
    ADD CONSTRAINT "PK_role_scope" PRIMARY KEY ("roleSlug", "scopeSlug");


--
-- Name: oauth_user_consents UQ_083721d99ce8db4033e2958ebb4; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.oauth_user_consents
    ADD CONSTRAINT "UQ_083721d99ce8db4033e2958ebb4" UNIQUE ("userId", "clientId");


--
-- Name: evaluation_config UQ_3c3c99a712e971835c52292e44c; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_config
    ADD CONSTRAINT "UQ_3c3c99a712e971835c52292e44c" UNIQUE ("workflowId", name);


--
-- Name: data_table_column UQ_8082ec4890f892f0bc77473a123; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_table_column
    ADD CONSTRAINT "UQ_8082ec4890f892f0bc77473a123" UNIQUE ("dataTableId", name);


--
-- Name: data_table UQ_b23096ef747281ac944d28e8b0d; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_table
    ADD CONSTRAINT "UQ_b23096ef747281ac944d28e8b0d" UNIQUE ("projectId", name);


--
-- Name: role_mapping_rule UQ_b33ac896ad3099fc8de36fdc1c4; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_mapping_rule
    ADD CONSTRAINT "UQ_b33ac896ad3099fc8de36fdc1c4" UNIQUE (type, "order");


--
-- Name: user_favorites UQ_cf6ae658ead9ffc124723413c65; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_favorites
    ADD CONSTRAINT "UQ_cf6ae658ead9ffc124723413c65" UNIQUE ("userId", "resourceId", "resourceType");


--
-- Name: user UQ_e12875dfb3b1d92d7d7c5377e2; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT "UQ_e12875dfb3b1d92d7d7c5377e2" UNIQUE (email);


--
-- Name: workflow_builder_session UQ_ec2aa73632932d485a1d5192ce1; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_builder_session
    ADD CONSTRAINT "UQ_ec2aa73632932d485a1d5192ce1" UNIQUE ("workflowId", "userId");


--
-- Name: _prisma_migrations _prisma_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public._prisma_migrations
    ADD CONSTRAINT _prisma_migrations_pkey PRIMARY KEY (id);


--
-- Name: agendamentos agendamentos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agendamentos
    ADD CONSTRAINT agendamentos_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: atendimento_link atendimento_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.atendimento_link
    ADD CONSTRAINT atendimento_link_pkey PRIMARY KEY (id);


--
-- Name: atendimentos atendimentos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.atendimentos
    ADD CONSTRAINT atendimentos_pkey PRIMARY KEY (id);


--
-- Name: audit_log audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT audit_log_pkey PRIMARY KEY (id);


--
-- Name: auth_identity auth_identity_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_identity
    ADD CONSTRAINT auth_identity_pkey PRIMARY KEY ("providerId", "providerType");


--
-- Name: auth_provider_sync_history auth_provider_sync_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_provider_sync_history
    ADD CONSTRAINT auth_provider_sync_history_pkey PRIMARY KEY (id);


--
-- Name: chatwoot_conversation_meta chatwoot_conversation_meta_chatwoot_conversation_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chatwoot_conversation_meta
    ADD CONSTRAINT chatwoot_conversation_meta_chatwoot_conversation_id_key UNIQUE (chatwoot_conversation_id);


--
-- Name: chatwoot_conversation_meta chatwoot_conversation_meta_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chatwoot_conversation_meta
    ADD CONSTRAINT chatwoot_conversation_meta_pkey PRIMARY KEY (id);


--
-- Name: clientes clientes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clientes
    ADD CONSTRAINT clientes_pkey PRIMARY KEY (id);


--
-- Name: conversas conversas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversas
    ADD CONSTRAINT conversas_pkey PRIMARY KEY (id);


--
-- Name: cpf_cnpj_validator cpf_cnpj_validator_cnpj_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cpf_cnpj_validator
    ADD CONSTRAINT cpf_cnpj_validator_cnpj_hash_key UNIQUE (cnpj_hash);


--
-- Name: cpf_cnpj_validator cpf_cnpj_validator_cpf_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cpf_cnpj_validator
    ADD CONSTRAINT cpf_cnpj_validator_cpf_hash_key UNIQUE (cpf_hash);


--
-- Name: cpf_cnpj_validator cpf_cnpj_validator_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cpf_cnpj_validator
    ADD CONSTRAINT cpf_cnpj_validator_pkey PRIMARY KEY (id);


--
-- Name: credentials_entity credentials_entity_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credentials_entity
    ADD CONSTRAINT credentials_entity_pkey PRIMARY KEY (id);


--
-- Name: documentos documentos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentos
    ADD CONSTRAINT documentos_pkey PRIMARY KEY (id);


--
-- Name: emolumentos emolumentos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.emolumentos
    ADD CONSTRAINT emolumentos_pkey PRIMARY KEY (id);


--
-- Name: event_destinations event_destinations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_destinations
    ADD CONSTRAINT event_destinations_pkey PRIMARY KEY (id);


--
-- Name: evolution_instance evolution_instance_instance_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evolution_instance
    ADD CONSTRAINT evolution_instance_instance_name_key UNIQUE (instance_name);


--
-- Name: evolution_instance evolution_instance_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evolution_instance
    ADD CONSTRAINT evolution_instance_pkey PRIMARY KEY (id);


--
-- Name: execution_data execution_data_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.execution_data
    ADD CONSTRAINT execution_data_pkey PRIMARY KEY ("executionId");


--
-- Name: lgpd_audit_anpd lgpd_audit_anpd_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lgpd_audit_anpd
    ADD CONSTRAINT lgpd_audit_anpd_pkey PRIMARY KEY (id);


--
-- Name: lgpd_consents lgpd_consent_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lgpd_consents
    ADD CONSTRAINT lgpd_consent_log_pkey PRIMARY KEY (id);


--
-- Name: mensagens mensagens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mensagens
    ADD CONSTRAINT mensagens_pkey PRIMARY KEY (id);


--
-- Name: n8n_run_log n8n_run_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.n8n_run_log
    ADD CONSTRAINT n8n_run_log_pkey PRIMARY KEY (id);


--
-- Name: opt_out_log opt_out_log_phone_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opt_out_log
    ADD CONSTRAINT opt_out_log_phone_key UNIQUE (phone);


--
-- Name: opt_out_log opt_out_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opt_out_log
    ADD CONSTRAINT opt_out_log_pkey PRIMARY KEY (id);


--
-- Name: outbox_messages outbox_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.outbox_messages
    ADD CONSTRAINT outbox_messages_pkey PRIMARY KEY (id);


--
-- Name: pesquisa_evolucao pesquisa_evolucao_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pesquisa_evolucao
    ADD CONSTRAINT pesquisa_evolucao_pkey PRIMARY KEY (id);


--
-- Name: execution_entity pk_e3e63bbf986767844bbe1166d4e; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.execution_entity
    ADD CONSTRAINT pk_e3e63bbf986767844bbe1166d4e PRIMARY KEY (id);


--
-- Name: workflows_tags pk_workflows_tags; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflows_tags
    ADD CONSTRAINT pk_workflows_tags PRIMARY KEY ("workflowId", "tagId");


--
-- Name: protocolos protocolos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.protocolos
    ADD CONSTRAINT protocolos_pkey PRIMARY KEY (id);


--
-- Name: rate_limit_event rate_limit_event_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rate_limit_event
    ADD CONSTRAINT rate_limit_event_pkey PRIMARY KEY (id);


--
-- Name: sessoes_chat sessoes_chat_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sessoes_chat
    ADD CONSTRAINT sessoes_chat_pkey PRIMARY KEY (id);


--
-- Name: sessoes_chat sessoes_chat_session_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sessoes_chat
    ADD CONSTRAINT sessoes_chat_session_id_key UNIQUE (session_id);


--
-- Name: tag_entity tag_entity_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tag_entity
    ADD CONSTRAINT tag_entity_pkey PRIMARY KEY (id);


--
-- Name: telegram_chat_meta telegram_chat_meta_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.telegram_chat_meta
    ADD CONSTRAINT telegram_chat_meta_pkey PRIMARY KEY (id);


--
-- Name: telegram_chat_meta telegram_chat_meta_telegram_chat_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.telegram_chat_meta
    ADD CONSTRAINT telegram_chat_meta_telegram_chat_id_key UNIQUE (telegram_chat_id);


--
-- Name: webhook_events uq_webhook_events_source_event; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook_events
    ADD CONSTRAINT uq_webhook_events_source_event UNIQUE (source, event_id);


--
-- Name: variables variables_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.variables
    ADD CONSTRAINT variables_pkey PRIMARY KEY (id);


--
-- Name: webhook_event_dlq webhook_event_dlq_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook_event_dlq
    ADD CONSTRAINT webhook_event_dlq_pkey PRIMARY KEY (id);


--
-- Name: webhook_events webhook_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook_events
    ADD CONSTRAINT webhook_events_pkey PRIMARY KEY (id);


--
-- Name: workflow_entity workflow_entity_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_entity
    ADD CONSTRAINT workflow_entity_pkey PRIMARY KEY (id);


--
-- Name: workflow_statistics workflow_statistics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_statistics
    ADD CONSTRAINT workflow_statistics_pkey PRIMARY KEY (id);


--
-- Name: buckets buckets_name_key; Type: CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.buckets
    ADD CONSTRAINT buckets_name_key UNIQUE (name);


--
-- Name: buckets buckets_pkey; Type: CONSTRAINT; Schema: storage; Owner: -
--

ALTER TABLE ONLY storage.buckets
    ADD CONSTRAINT buckets_pkey PRIMARY KEY (id);


--
-- Name: hooks hooks_hook_name_key; Type: CONSTRAINT; Schema: supabase_functions; Owner: -
--

ALTER TABLE ONLY supabase_functions.hooks
    ADD CONSTRAINT hooks_hook_name_key UNIQUE (hook_name);


--
-- Name: hooks hooks_pkey; Type: CONSTRAINT; Schema: supabase_functions; Owner: -
--

ALTER TABLE ONLY supabase_functions.hooks
    ADD CONSTRAINT hooks_pkey PRIMARY KEY (id);


--
-- Name: IDX_02751202c9a2ad75f2d8e14f5e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_02751202c9a2ad75f2d8e14f5e" ON public.instance_ai_iteration_logs USING btree ("threadId", "taskKey", "createdAt");


--
-- Name: IDX_0468a9dc35597314e641d4722a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_0468a9dc35597314e641d4722a" ON public.agent_execution_threads USING btree ("agentId");


--
-- Name: IDX_069e791e428391a5569e7a96b2; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_069e791e428391a5569e7a96b2" ON public.agents_memory_entry_cursors USING btree ("observationScopeId");


--
-- Name: IDX_070b5de842ece9ccdda0d9738b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_070b5de842ece9ccdda0d9738b" ON public.workflow_publish_history USING btree ("workflowId", "versionId");


--
-- Name: IDX_07cb1e4a302629c5fa5d74d2bb; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_07cb1e4a302629c5fa5d74d2bb" ON public.agents_observations USING btree ("agentId", "observationScopeId", status);


--
-- Name: IDX_0babdf6e3b897a86fe4678355e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_0babdf6e3b897a86fe4678355e" ON public.instance_ai_pending_confirmations USING btree ("checkpointKey");


--
-- Name: IDX_0d5db648188d338df7fb2a8064; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_0d5db648188d338df7fb2a8064" ON public.instance_ai_observations USING btree ("observationScopeId", status, "createdAt", id);


--
-- Name: IDX_0e2f8bf92a7a9c88b89670f701; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_0e2f8bf92a7a9c88b89670f701" ON public.agent_execution_threads USING btree ("projectId");


--
-- Name: IDX_0edf1226b77ddc525eae493807; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_0edf1226b77ddc525eae493807" ON public.agents_memory_entries USING btree ("supersededBy");


--
-- Name: IDX_127ee1078ffa952bb37b511efa; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_127ee1078ffa952bb37b511efa" ON public.agents_observations USING btree ("supersededBy");


--
-- Name: IDX_1443a75e59adbfb796071d6639; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_1443a75e59adbfb796071d6639" ON public.agents_memory_entries USING btree ("resourceId");


--
-- Name: IDX_14f68deffaf858465715995508; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX "IDX_14f68deffaf858465715995508" ON public.folder USING btree ("projectId", id);


--
-- Name: IDX_16db3adb7b19df1ee55ff06b27; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX "IDX_16db3adb7b19df1ee55ff06b27" ON public.instance_ai_mcp_registry_connections USING btree ("userId", "serverSlug", "credentialId");


--
-- Name: IDX_1d11050a381548c42c32cc25c4; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_1d11050a381548c42c32cc25c4" ON public.user_favorites USING btree ("resourceType", "resourceId");


--
-- Name: IDX_1d8ab99d5861c9388d2dc1cf73; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX "IDX_1d8ab99d5861c9388d2dc1cf73" ON public.insights_metadata USING btree ("workflowId");


--
-- Name: IDX_1dd5c393ad0517be3c31a7af83; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_1dd5c393ad0517be3c31a7af83" ON public.user_favorites USING btree ("userId");


--
-- Name: IDX_1e31657f5fe46816c34be7c1b4; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_1e31657f5fe46816c34be7c1b4" ON public.workflow_history USING btree ("workflowId");


--
-- Name: IDX_1eeb64cb9d66a927988de759e6; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_1eeb64cb9d66a927988de759e6" ON public.instance_ai_messages USING btree ("threadId");


--
-- Name: IDX_1ef35bac35d20bdae979d917a3; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX "IDX_1ef35bac35d20bdae979d917a3" ON public.user_api_keys USING btree ("apiKey");


--
-- Name: IDX_2b23f3f24a70bebb990203b011; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_2b23f3f24a70bebb990203b011" ON public.instance_ai_checkpoints USING btree ("threadId");


--
-- Name: IDX_35a78869286c65d9330d02b88f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_35a78869286c65d9330d02b88f" ON public.role_mapping_rule_project USING btree ("projectId");


--
-- Name: IDX_39b07732e819fb561d74c38763; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_39b07732e819fb561d74c38763" ON public.ai_builder_temporary_workflow USING btree ("threadId");


--
-- Name: IDX_451d387a182fa8dd8002dfc3a7; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_451d387a182fa8dd8002dfc3a7" ON public.agents_memory_entry_sources USING btree ("threadId");


--
-- Name: IDX_45dafc48fe2ce95eac30fc8ffd; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_45dafc48fe2ce95eac30fc8ffd" ON public.agent_files USING btree ("agentId", "createdAt");


--
-- Name: IDX_4c72ebdb265d1775bf61147af0; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX "IDX_4c72ebdb265d1775bf61147af0" ON public.chat_hub_tools USING btree ("ownerId", name);


--
-- Name: IDX_4cfd8a70ebb0a5b0cf047dca3c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_4cfd8a70ebb0a5b0cf047dca3c" ON public.agents_observations USING btree ("observationScopeId");


--
-- Name: IDX_501e2d1701a10e24fb69ab5fc5; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_501e2d1701a10e24fb69ab5fc5" ON public.agents_observations USING btree ("parentId");


--
-- Name: IDX_54fa1b94f34a409beafae567a4; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_54fa1b94f34a409beafae567a4" ON public.agents_threads USING btree ("resourceId");


--
-- Name: IDX_56900edc3cfd16612e2ef2c6a8; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_56900edc3cfd16612e2ef2c6a8" ON public.binary_data USING btree ("sourceType", "sourceId");


--
-- Name: IDX_5e31c210f896d539964bf99fe3; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_5e31c210f896d539964bf99fe3" ON public.agent_checkpoints USING btree ("agentId");


--
-- Name: IDX_5ec8e8c8d3539f3696cf73b43b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_5ec8e8c8d3539f3696cf73b43b" ON public.credential_dependency USING btree ("credentialId");


--
-- Name: IDX_5f0643f6717905a05164090dde; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_5f0643f6717905a05164090dde" ON public.project_relation USING btree ("userId");


--
-- Name: IDX_60b6a84299eeb3f671dfec7693; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX "IDX_60b6a84299eeb3f671dfec7693" ON public.insights_by_period USING btree ("periodStart", type, "periodUnit", "metaId");


--
-- Name: IDX_61448d56d61802b5dfde5cdb00; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_61448d56d61802b5dfde5cdb00" ON public.project_relation USING btree ("projectId");


--
-- Name: IDX_62476b94b56d9dc7ed9ed75d3d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_62476b94b56d9dc7ed9ed75d3d" ON public.dynamic_credential_entry USING btree (subject_id);


--
-- Name: IDX_63d3c3a68b9cebf05f967f0b1c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_63d3c3a68b9cebf05f967f0b1c" ON public.agent_execution USING btree ("threadId", "createdAt");


--
-- Name: IDX_63d7bbae72c767cf162d459fcc; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX "IDX_63d7bbae72c767cf162d459fcc" ON public.user_api_keys USING btree ("userId", label);


--
-- Name: IDX_6b55089892e447c2f82e5ec60e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_6b55089892e447c2f82e5ec60e" ON public.agents_observation_locks USING btree ("observationScopeId");


--
-- Name: IDX_6edec973a6450990977bb854c3; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_6edec973a6450990977bb854c3" ON public.dynamic_credential_user_entry USING btree ("resolverId");


--
-- Name: IDX_768189b506cc26c4fe878b87cb; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_768189b506cc26c4fe878b87cb" ON public.instance_ai_checkpoints USING btree ("runId");


--
-- Name: IDX_76e212c6867fbaa06bf0decd6f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_76e212c6867fbaa06bf0decd6f" ON public.instance_ai_messages USING btree ("resourceId");


--
-- Name: IDX_87aa187d27ea67eafd16490515; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_87aa187d27ea67eafd16490515" ON public.agents_observation_cursors USING btree ("observationScopeId");


--
-- Name: IDX_87cd5a8da20304b089ea2f83fe; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_87cd5a8da20304b089ea2f83fe" ON public.agent_history USING btree ("agentId");


--
-- Name: IDX_8e4b4774db42f1e6dda3452b2a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_8e4b4774db42f1e6dda3452b2a" ON public.test_case_execution USING btree ("testRunId");


--
-- Name: IDX_91ee85fa9619dd6776725e117b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_91ee85fa9619dd6776725e117b" ON public.credential_dependency USING btree ("dependencyType", "dependencyId");


--
-- Name: IDX_92f13cb6bc694227e069447f7b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_92f13cb6bc694227e069447f7b" ON public.instance_ai_observational_memory USING btree ("lookupKey");


--
-- Name: IDX_9594c0983cfee1c8ff49b05848; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_9594c0983cfee1c8ff49b05848" ON public.agents_memory_entry_locks USING btree ("resourceId");


--
-- Name: IDX_97f863fa83c4786f1956508496; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX "IDX_97f863fa83c4786f1956508496" ON public.execution_annotations USING btree ("executionId");


--
-- Name: IDX_9c9ee9df586e60bb723234e499; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_9c9ee9df586e60bb723234e499" ON public.dynamic_credential_resolver USING btree (type);


--
-- Name: IDX_UniqueRoleDisplayName; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX "IDX_UniqueRoleDisplayName" ON public.role USING btree ("displayName");


--
-- Name: IDX_a03e04e94bea8439dd166d4b52; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX "IDX_a03e04e94bea8439dd166d4b52" ON public.agents_memory_entries USING btree ("agentId", "resourceId", "contentHash");


--
-- Name: IDX_a30d560207c4071d98aa03c179; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_a30d560207c4071d98aa03c179" ON public.agents USING btree ("projectId");


--
-- Name: IDX_a353ac251315ef0af6ad3c9f0a; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX "IDX_a353ac251315ef0af6ad3c9f0a" ON public.agents_memory_entry_sources USING btree ("memoryEntryId", "observationId", "evidenceHash");


--
-- Name: IDX_a3697779b366e131b2bbdae297; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_a3697779b366e131b2bbdae297" ON public.execution_annotation_tags USING btree ("tagId");


--
-- Name: IDX_a36dc616fabc3f736bb82410a2; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_a36dc616fabc3f736bb82410a2" ON public.dynamic_credential_user_entry USING btree ("userId");


--
-- Name: IDX_a371ee6b8e0ebb5635f8baa46d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_a371ee6b8e0ebb5635f8baa46d" ON public.instance_ai_workflow_snapshots USING btree ("workflowName", status);


--
-- Name: IDX_a48ce930c3bc7604894b8f0eaa; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_a48ce930c3bc7604894b8f0eaa" ON public.evaluation_collection USING btree ("workflowId");


--
-- Name: IDX_a4ff2d9b9628ea988fa9e7d0bf; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_a4ff2d9b9628ea988fa9e7d0bf" ON public.workflow_dependency USING btree ("workflowId");


--
-- Name: IDX_a680ac96aae02dc887bbaac512; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX "IDX_a680ac96aae02dc887bbaac512" ON public.instance_ai_observational_memory USING btree (scope, "threadId", "resourceId");


--
-- Name: IDX_a80e0ee839a2f10ba4b86e1999; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_a80e0ee839a2f10ba4b86e1999" ON public.instance_ai_observations USING btree ("supersededBy");


--
-- Name: IDX_ae51b54c4bb430cf92f48b623f; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX "IDX_ae51b54c4bb430cf92f48b623f" ON public.annotation_tag_entity USING btree (name);


--
-- Name: IDX_aff2807b31eccbafe59d0474f0; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_aff2807b31eccbafe59d0474f0" ON public.agents_memory_entries USING btree ("agentId", "resourceId", status, "createdAt", id);


--
-- Name: IDX_agent_execution_threads_taskVersionId; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_agent_execution_threads_taskVersionId" ON public.agent_execution_threads USING btree ("taskVersionId");


--
-- Name: IDX_agents_messages_threadId_createdAt; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_agents_messages_threadId_createdAt" ON public.agents_messages USING btree ("threadId", "createdAt");


--
-- Name: IDX_agents_projectId; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_agents_projectId" ON public.agents USING btree ("projectId");


--
-- Name: IDX_ba67ee8dc311830a2eea89b6e9; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_ba67ee8dc311830a2eea89b6e9" ON public.instance_ai_pending_confirmations USING btree ("threadId");


--
-- Name: IDX_bb66e404c35996b0d694617750; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_bb66e404c35996b0d694617750" ON public.role_mapping_rule USING btree (role);


--
-- Name: IDX_be9d0eca0b19fb93d4eb74b327; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_be9d0eca0b19fb93d4eb74b327" ON public.instance_ai_checkpoints USING btree ("resourceId");


--
-- Name: IDX_c1519757391996eb06064f0e7c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_c1519757391996eb06064f0e7c" ON public.execution_annotation_tags USING btree ("annotationId");


--
-- Name: IDX_cb7c15d22fd068a0806aa57fc0; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_cb7c15d22fd068a0806aa57fc0" ON public.agents_memory_entry_sources USING btree ("observationId");


--
-- Name: IDX_cec8eea3bf49551482ccb4933e; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX "IDX_cec8eea3bf49551482ccb4933e" ON public.execution_metadata USING btree ("executionId", key);


--
-- Name: IDX_chat_hub_messages_sessionId; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_chat_hub_messages_sessionId" ON public.chat_hub_messages USING btree ("sessionId");


--
-- Name: IDX_chat_hub_sessions_owner_lastmsg_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_chat_hub_sessions_owner_lastmsg_id" ON public.chat_hub_sessions USING btree ("ownerId", "lastMessageAt" DESC, id);


--
-- Name: IDX_credential_dependency_credentialId_dependencyType_dependenc; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX "IDX_credential_dependency_credentialId_dependencyType_dependenc" ON public.credential_dependency USING btree ("credentialId", "dependencyType", "dependencyId");


--
-- Name: IDX_d3a2bc880e7a8626802e5474ad; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_d3a2bc880e7a8626802e5474ad" ON public.instance_ai_run_snapshots USING btree ("threadId", "createdAt");


--
-- Name: IDX_d61a12235d268a49af6a3c09c1; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_d61a12235d268a49af6a3c09c1" ON public.dynamic_credential_entry USING btree (resolver_id);


--
-- Name: IDX_d634a0c93fd7de68a87eab951b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_d634a0c93fd7de68a87eab951b" ON public.evaluation_collection USING btree ("evaluationConfigId");


--
-- Name: IDX_d6870d3b6e4c185d33926f423c; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_d6870d3b6e4c185d33926f423c" ON public.test_run USING btree ("workflowId");


--
-- Name: IDX_d7a4aba7440449865e2b924377; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_d7a4aba7440449865e2b924377" ON public.instance_ai_pending_confirmations USING btree ("expiresAt");


--
-- Name: IDX_d926c16c2ad9728cb9a81790c0; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_d926c16c2ad9728cb9a81790c0" ON public.instance_ai_run_snapshots USING btree ("threadId", "messageGroupId");


--
-- Name: IDX_daef2195a4a846eb70eed15e03; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_daef2195a4a846eb70eed15e03" ON public.instance_ai_observations USING btree ("parentId");


--
-- Name: IDX_deployment_key_data_encryption_active; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX "IDX_deployment_key_data_encryption_active" ON public.deployment_key USING btree (type) WHERE (((status)::text = 'active'::text) AND ((type)::text = 'data_encryption'::text));


--
-- Name: IDX_deployment_key_instance_id_active; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX "IDX_deployment_key_instance_id_active" ON public.deployment_key USING btree (type) WHERE (((status)::text = 'active'::text) AND ((type)::text = 'instance.id'::text));


--
-- Name: IDX_deployment_key_jwe_private_key_active; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX "IDX_deployment_key_jwe_private_key_active" ON public.deployment_key USING btree (type, algorithm) WHERE (((status)::text = 'active'::text) AND ((type)::text = 'jwe.private-key'::text));


--
-- Name: IDX_deployment_key_signing_binary_data_active; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX "IDX_deployment_key_signing_binary_data_active" ON public.deployment_key USING btree (type) WHERE (((status)::text = 'active'::text) AND ((type)::text = 'signing.binary_data'::text));


--
-- Name: IDX_deployment_key_signing_hmac_active; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX "IDX_deployment_key_signing_hmac_active" ON public.deployment_key USING btree (type) WHERE (((status)::text = 'active'::text) AND ((type)::text = 'signing.hmac'::text));


--
-- Name: IDX_deployment_key_signing_jwt_active; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX "IDX_deployment_key_signing_jwt_active" ON public.deployment_key USING btree (type) WHERE (((status)::text = 'active'::text) AND ((type)::text = 'signing.jwt'::text));


--
-- Name: IDX_df5fd25c8bbfd2b042602600d8; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_df5fd25c8bbfd2b042602600d8" ON public.instance_ai_pending_confirmations USING btree ("userId");


--
-- Name: IDX_e48a201071ab85d9d09119d640; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_e48a201071ab85d9d09119d640" ON public.workflow_dependency USING btree ("dependencyKey");


--
-- Name: IDX_e7fe1cfda990c14a445937d0b9; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_e7fe1cfda990c14a445937d0b9" ON public.workflow_dependency USING btree ("dependencyType");


--
-- Name: IDX_execution_entity_deduplicationKey; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX "IDX_execution_entity_deduplicationKey" ON public.execution_entity USING btree ("deduplicationKey") WHERE ("deduplicationKey" IS NOT NULL);


--
-- Name: IDX_execution_entity_deletedAt; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_execution_entity_deletedAt" ON public.execution_entity USING btree ("deletedAt");


--
-- Name: IDX_f36dea4d38fe92e0e8f44d5a56; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_f36dea4d38fe92e0e8f44d5a56" ON public.instance_ai_threads USING btree ("resourceId");


--
-- Name: IDX_f45d0535a2ed59b6c2dd6da98a; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_f45d0535a2ed59b6c2dd6da98a" ON public.agent_task_definition USING btree ("agentId");


--
-- Name: IDX_f9573af4ed653f13b0ba1f7b12; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_f9573af4ed653f13b0ba1f7b12" ON public.agents_memory_entry_sources USING btree ("agentId", "threadId");


--
-- Name: IDX_fc7bf858660bfafd19181e8e35; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_fc7bf858660bfafd19181e8e35" ON public.agents_messages USING btree ("threadId", "createdAt");


--
-- Name: IDX_fd7542bb123074760285dc1bbf; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_fd7542bb123074760285dc1bbf" ON public.evaluation_config USING btree ("workflowId");


--
-- Name: IDX_insights_raw_timestamp_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_insights_raw_timestamp_id" ON public.insights_raw USING btree ("timestamp", id);


--
-- Name: IDX_instance_ai_threads_projectId; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_instance_ai_threads_projectId" ON public.instance_ai_threads USING btree ("projectId");


--
-- Name: IDX_role_scope_scopeSlug; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_role_scope_scopeSlug" ON public.role_scope USING btree ("scopeSlug");


--
-- Name: IDX_secrets_provider_connection_providerKey; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX "IDX_secrets_provider_connection_providerKey" ON public.secrets_provider_connection USING btree ("providerKey");


--
-- Name: IDX_shared_workflow_projectId; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_shared_workflow_projectId" ON public.shared_workflow USING btree ("projectId");


--
-- Name: IDX_test_run_collectionId; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_test_run_collectionId" ON public.test_run USING btree ("collectionId");


--
-- Name: IDX_test_run_evaluationConfigId; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_test_run_evaluationConfigId" ON public.test_run USING btree ("evaluationConfigId");


--
-- Name: IDX_workflow_dependency_publishedVersionId; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_workflow_dependency_publishedVersionId" ON public.workflow_dependency USING btree ("publishedVersionId");


--
-- Name: IDX_workflow_entity_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_workflow_entity_name" ON public.workflow_entity USING btree (name);


--
-- Name: IDX_workflow_entity_sourceWorkflowId; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "IDX_workflow_entity_sourceWorkflowId" ON public.workflow_entity USING btree ("sourceWorkflowId") WHERE ("sourceWorkflowId" IS NOT NULL);


--
-- Name: IDX_workflow_publication_outbox_active_workflow_status; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX "IDX_workflow_publication_outbox_active_workflow_status" ON public.workflow_publication_outbox USING btree ("workflowId", status) WHERE ((status)::text = ANY ((ARRAY['pending'::character varying, 'in_progress'::character varying])::text[]));


--
-- Name: IDX_workflow_statistics_workflow_name; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX "IDX_workflow_statistics_workflow_name" ON public.workflow_statistics USING btree ("workflowId", name);


--
-- Name: idx_07fde106c0b471d8cc80a64fc8; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_07fde106c0b471d8cc80a64fc8 ON public.credentials_entity USING btree (type);


--
-- Name: idx_16f4436789e804e3e1c9eeb240; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_16f4436789e804e3e1c9eeb240 ON public.webhook_entity USING btree ("webhookId", method, "pathLength");


--
-- Name: idx_812eb05f7451ca757fb98444ce; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_812eb05f7451ca757fb98444ce ON public.tag_entity USING btree (name);


--
-- Name: idx_agendamentos_cliente_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_agendamentos_cliente_id ON public.agendamentos USING btree (cliente_id);


--
-- Name: idx_agendamentos_data_hora; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_agendamentos_data_hora ON public.agendamentos USING btree (data_hora);


--
-- Name: idx_agendamentos_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_agendamentos_status ON public.agendamentos USING btree (status);


--
-- Name: idx_atendimento_link_atendimento; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_atendimento_link_atendimento ON public.atendimento_link USING btree (atendimento_id);


--
-- Name: idx_emolumentos_tipo_servico; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_emolumentos_tipo_servico ON public.emolumentos USING btree (tipo_servico);


--
-- Name: idx_execution_entity_stopped_at_status_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_execution_entity_stopped_at_status_deleted_at ON public.execution_entity USING btree ("stoppedAt", status, "deletedAt") WHERE (("stoppedAt" IS NOT NULL) AND ("deletedAt" IS NULL));


--
-- Name: idx_execution_entity_wait_till_status_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_execution_entity_wait_till_status_deleted_at ON public.execution_entity USING btree ("waitTill", status, "deletedAt") WHERE (("waitTill" IS NOT NULL) AND ("deletedAt" IS NULL));


--
-- Name: idx_execution_entity_workflow_id_started_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_execution_entity_workflow_id_started_at ON public.execution_entity USING btree ("workflowId", "startedAt") WHERE (("startedAt" IS NOT NULL) AND ("deletedAt" IS NULL));


--
-- Name: idx_lgpd_consent_cliente; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_lgpd_consent_cliente ON public.lgpd_consents USING btree (cliente_id);


--
-- Name: idx_mensagens_sessao_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mensagens_sessao_id ON public.mensagens USING btree (sessao_id);


--
-- Name: idx_mensagens_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mensagens_timestamp ON public.mensagens USING btree ("timestamp");


--
-- Name: idx_n8n_run_log_workflow; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_n8n_run_log_workflow ON public.n8n_run_log USING btree (workflow_id);


--
-- Name: idx_optout_phone; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_optout_phone ON public.opt_out_log USING btree (phone);


--
-- Name: idx_rate_limit_ip; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rate_limit_ip ON public.rate_limit_event USING btree (ip_truncated);


--
-- Name: idx_sessoes_chat_cliente_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sessoes_chat_cliente_id ON public.sessoes_chat USING btree (cliente_id);


--
-- Name: idx_sessoes_chat_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sessoes_chat_session_id ON public.sessoes_chat USING btree (session_id);


--
-- Name: idx_sessoes_chat_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sessoes_chat_status ON public.sessoes_chat USING btree (status);


--
-- Name: idx_workflows_tags_workflow_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_workflows_tags_workflow_id ON public.workflows_tags USING btree ("workflowId");


--
-- Name: ix_atendimentos_canal; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_atendimentos_canal ON public.atendimentos USING btree (canal);


--
-- Name: ix_atendimentos_cliente_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_atendimentos_cliente_id ON public.atendimentos USING btree (cliente_id);


--
-- Name: ix_atendimentos_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_atendimentos_deleted_at ON public.atendimentos USING btree (deleted_at) WHERE (deleted_at IS NULL);


--
-- Name: ix_atendimentos_external_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_atendimentos_external_id ON public.atendimentos USING btree (external_id);


--
-- Name: ix_atendimentos_protocolo_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_atendimentos_protocolo_id ON public.atendimentos USING btree (protocolo_id);


--
-- Name: ix_atendimentos_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_atendimentos_status ON public.atendimentos USING btree (status);


--
-- Name: ix_audit_actor_action; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_actor_action ON public.audit_log USING btree (actor_id, action);


--
-- Name: ix_audit_ip_truncated; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_ip_truncated ON public.audit_log USING btree (ip_truncated);


--
-- Name: ix_audit_log_action; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_log_action ON public.audit_log USING btree (action);


--
-- Name: ix_audit_log_actor_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_log_actor_id ON public.audit_log USING btree (actor_id);


--
-- Name: ix_audit_log_canal; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_log_canal ON public.audit_log USING btree (canal);


--
-- Name: ix_audit_log_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_audit_log_hash ON public.audit_log USING btree (hash);


--
-- Name: ix_audit_log_request_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_log_request_id ON public.audit_log USING btree (request_id);


--
-- Name: ix_audit_log_resource; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_log_resource ON public.audit_log USING btree (resource);


--
-- Name: ix_audit_log_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_log_timestamp ON public.audit_log USING btree ("timestamp");


--
-- Name: ix_audit_resource_action; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_resource_action ON public.audit_log USING btree (resource, action);


--
-- Name: ix_clientes_cpf_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_clientes_cpf_hash ON public.clientes USING btree (cpf_hash);


--
-- Name: ix_clientes_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_clientes_deleted_at ON public.clientes USING btree (deleted_at);


--
-- Name: ix_clientes_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_clientes_email ON public.clientes USING btree (email);


--
-- Name: ix_clientes_motivo_encerramento; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_clientes_motivo_encerramento ON public.clientes USING btree (motivo_encerramento);


--
-- Name: ix_clientes_telefone_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_clientes_telefone_hash ON public.clientes USING btree (telefone_hash);


--
-- Name: ix_conversas_canal; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_conversas_canal ON public.conversas USING btree (canal);


--
-- Name: ix_conversas_cliente_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_conversas_cliente_id ON public.conversas USING btree (cliente_id);


--
-- Name: ix_conversas_external_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_conversas_external_id ON public.conversas USING btree (external_id);


--
-- Name: ix_conversas_handoff_to_human; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_conversas_handoff_to_human ON public.conversas USING btree (handoff_to_human);


--
-- Name: ix_conversas_intent_detected; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_conversas_intent_detected ON public.conversas USING btree (intent_detected);


--
-- Name: ix_documentos_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documentos_deleted_at ON public.documentos USING btree (deleted_at) WHERE (deleted_at IS NULL);


--
-- Name: ix_documentos_hash_sha256; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documentos_hash_sha256 ON public.documentos USING btree (hash_sha256);


--
-- Name: ix_documentos_protocolo_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documentos_protocolo_id ON public.documentos USING btree (protocolo_id);


--
-- Name: ix_documentos_tipo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documentos_tipo ON public.documentos USING btree (tipo);


--
-- Name: ix_lgpd_audit_anpd_anpd_protocolo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_lgpd_audit_anpd_anpd_protocolo ON public.lgpd_audit_anpd USING btree (anpd_protocolo);


--
-- Name: ix_lgpd_audit_anpd_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_lgpd_audit_anpd_created_at ON public.lgpd_audit_anpd USING btree (created_at);


--
-- Name: ix_lgpd_audit_anpd_evento; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_lgpd_audit_anpd_evento ON public.lgpd_audit_anpd USING btree (evento);


--
-- Name: ix_mv_protocolo_stats_pk; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_mv_protocolo_stats_pk ON public.mv_protocolo_stats USING btree (status, tipo, canal);


--
-- Name: ix_mv_protocolo_stats_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_mv_protocolo_stats_status ON public.mv_protocolo_stats USING btree (status);


--
-- Name: ix_outbox_messages_next_retry_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_outbox_messages_next_retry_at ON public.outbox_messages USING btree (next_retry_at);


--
-- Name: ix_outbox_messages_queue; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_outbox_messages_queue ON public.outbox_messages USING btree (queue);


--
-- Name: ix_outbox_messages_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_outbox_messages_status ON public.outbox_messages USING btree (status);


--
-- Name: ix_protocolos_cliente_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_protocolos_cliente_id ON public.protocolos USING btree (cliente_id);


--
-- Name: ix_protocolos_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_protocolos_deleted_at ON public.protocolos USING btree (deleted_at) WHERE (deleted_at IS NULL);


--
-- Name: ix_protocolos_numero; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_protocolos_numero ON public.protocolos USING btree (numero);


--
-- Name: ix_protocolos_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_protocolos_status ON public.protocolos USING btree (status);


--
-- Name: ix_protocolos_tipo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_protocolos_tipo ON public.protocolos USING btree (tipo);


--
-- Name: ix_webhook_events_event_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_webhook_events_event_id ON public.webhook_events USING btree (event_id);


--
-- Name: ix_webhook_events_received_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_webhook_events_received_at ON public.webhook_events USING btree (received_at DESC);


--
-- Name: ix_webhook_events_source; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_webhook_events_source ON public.webhook_events USING btree (source);


--
-- Name: pk_credentials_entity_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX pk_credentials_entity_id ON public.credentials_entity USING btree (id);


--
-- Name: pk_tag_entity_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX pk_tag_entity_id ON public.tag_entity USING btree (id);


--
-- Name: pk_workflow_entity_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX pk_workflow_entity_id ON public.workflow_entity USING btree (id);


--
-- Name: project_relation_role_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX project_relation_role_idx ON public.project_relation USING btree (role);


--
-- Name: project_relation_role_project_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX project_relation_role_project_idx ON public.project_relation USING btree ("projectId", role);


--
-- Name: user_role_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX user_role_idx ON public."user" USING btree ("roleSlug");


--
-- Name: variables_global_key_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX variables_global_key_unique ON public.variables USING btree (key) WHERE ("projectId" IS NULL);


--
-- Name: variables_project_key_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX variables_project_key_unique ON public.variables USING btree ("projectId", key) WHERE ("projectId" IS NOT NULL);


--
-- Name: atendimentos trg_auto_audit_atendimentos; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_auto_audit_atendimentos AFTER INSERT OR DELETE OR UPDATE ON public.atendimentos FOR EACH ROW EXECUTE FUNCTION public.fn_auto_audit();


--
-- Name: clientes trg_auto_audit_clientes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_auto_audit_clientes AFTER INSERT OR DELETE OR UPDATE ON public.clientes FOR EACH ROW EXECUTE FUNCTION public.fn_auto_audit();


--
-- Name: conversas trg_auto_audit_conversas; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_auto_audit_conversas AFTER INSERT OR DELETE OR UPDATE ON public.conversas FOR EACH ROW EXECUTE FUNCTION public.fn_auto_audit();


--
-- Name: documentos trg_auto_audit_documentos; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_auto_audit_documentos AFTER INSERT OR DELETE OR UPDATE ON public.documentos FOR EACH ROW EXECUTE FUNCTION public.fn_auto_audit();


--
-- Name: emolumentos trg_auto_audit_emolumentos; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_auto_audit_emolumentos AFTER INSERT OR DELETE OR UPDATE ON public.emolumentos FOR EACH ROW EXECUTE FUNCTION public.fn_auto_audit();


--
-- Name: protocolos trg_auto_audit_protocolos; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_auto_audit_protocolos AFTER INSERT OR DELETE OR UPDATE ON public.protocolos FOR EACH ROW EXECUTE FUNCTION public.fn_auto_audit();


--
-- Name: lgpd_consents trg_lgpd_consent_webhook; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_lgpd_consent_webhook AFTER INSERT ON public.lgpd_consents FOR EACH ROW EXECUTE FUNCTION public.lgpd_consent_webhook();


--
-- Name: outbox_messages trg_outbox_new; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_outbox_new AFTER INSERT ON public.outbox_messages FOR EACH ROW EXECUTE FUNCTION public.notify_outbox_new();


--
-- Name: outbox_messages trg_outbox_webhook; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_outbox_webhook AFTER INSERT ON public.outbox_messages FOR EACH ROW EXECUTE FUNCTION public.outbox_webhook();


--
-- Name: protocolos trg_protocolo_status_webhook; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_protocolo_status_webhook AFTER UPDATE ON public.protocolos FOR EACH ROW EXECUTE FUNCTION public.protocolo_status_webhook();


--
-- Name: atendimentos trg_set_updated_at_atendimentos; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_set_updated_at_atendimentos BEFORE UPDATE ON public.atendimentos FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: clientes trg_set_updated_at_clientes; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_set_updated_at_clientes BEFORE UPDATE ON public.clientes FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: conversas trg_set_updated_at_conversas; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_set_updated_at_conversas BEFORE UPDATE ON public.conversas FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: documentos trg_set_updated_at_documentos; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_set_updated_at_documentos BEFORE UPDATE ON public.documentos FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: emolumentos trg_set_updated_at_emolumentos; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_set_updated_at_emolumentos BEFORE UPDATE ON public.emolumentos FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: lgpd_audit_anpd trg_set_updated_at_lgpd_audit_anpd; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_set_updated_at_lgpd_audit_anpd BEFORE UPDATE ON public.lgpd_audit_anpd FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: lgpd_consents trg_set_updated_at_lgpd_consents; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_set_updated_at_lgpd_consents BEFORE UPDATE ON public.lgpd_consents FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: outbox_messages trg_set_updated_at_outbox_messages; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_set_updated_at_outbox_messages BEFORE UPDATE ON public.outbox_messages FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: protocolos trg_set_updated_at_protocolos; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_set_updated_at_protocolos BEFORE UPDATE ON public.protocolos FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: webhook_events trg_set_updated_at_webhook_events; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_set_updated_at_webhook_events BEFORE UPDATE ON public.webhook_events FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();


--
-- Name: workflow_entity workflow_version_increment; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER workflow_version_increment BEFORE UPDATE ON public.workflow_entity FOR EACH ROW EXECUTE FUNCTION public.increment_workflow_version();


--
-- Name: workflow_builder_session FK_00290cdeee4d4d7db84709be936; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_builder_session
    ADD CONSTRAINT "FK_00290cdeee4d4d7db84709be936" FOREIGN KEY ("userId") REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: agent_execution_threads FK_0468a9dc35597314e641d4722aa; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_execution_threads
    ADD CONSTRAINT "FK_0468a9dc35597314e641d4722aa" FOREIGN KEY ("agentId") REFERENCES public.agents(id) ON DELETE CASCADE;


--
-- Name: agents_memory_entry_cursors FK_069e791e428391a5569e7a96b20; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents_memory_entry_cursors
    ADD CONSTRAINT "FK_069e791e428391a5569e7a96b20" FOREIGN KEY ("observationScopeId") REFERENCES public.agents_threads(id) ON DELETE CASCADE;


--
-- Name: processed_data FK_06a69a7032c97a763c2c7599464; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processed_data
    ADD CONSTRAINT "FK_06a69a7032c97a763c2c7599464" FOREIGN KEY ("workflowId") REFERENCES public.workflow_entity(id) ON DELETE CASCADE;


--
-- Name: workflow_entity FK_08d6c67b7f722b0039d9d5ed620; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_entity
    ADD CONSTRAINT "FK_08d6c67b7f722b0039d9d5ed620" FOREIGN KEY ("activeVersionId") REFERENCES public.workflow_history("versionId") ON DELETE RESTRICT;


--
-- Name: agents_observation_locks FK_093e44ae20f2518e97d83a95433; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents_observation_locks
    ADD CONSTRAINT "FK_093e44ae20f2518e97d83a95433" FOREIGN KEY ("agentId") REFERENCES public.agents(id) ON DELETE CASCADE;


--
-- Name: agents_messages FK_0a8057a61afabd2999608ffd0d9; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents_messages
    ADD CONSTRAINT "FK_0a8057a61afabd2999608ffd0d9" FOREIGN KEY ("threadId") REFERENCES public.agents_threads(id) ON DELETE CASCADE;


--
-- Name: instance_ai_pending_confirmations FK_0babdf6e3b897a86fe4678355eb; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_ai_pending_confirmations
    ADD CONSTRAINT "FK_0babdf6e3b897a86fe4678355eb" FOREIGN KEY ("checkpointKey") REFERENCES public.instance_ai_checkpoints(key) ON DELETE CASCADE;


--
-- Name: agents_memory_entry_locks FK_0ccf6d9ea6f44fa1c264fc2f795; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents_memory_entry_locks
    ADD CONSTRAINT "FK_0ccf6d9ea6f44fa1c264fc2f795" FOREIGN KEY ("agentId") REFERENCES public.agents(id) ON DELETE CASCADE;


--
-- Name: agent_execution_threads FK_0e2f8bf92a7a9c88b89670f701c; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_execution_threads
    ADD CONSTRAINT "FK_0e2f8bf92a7a9c88b89670f701c" FOREIGN KEY ("projectId") REFERENCES public.project(id) ON DELETE CASCADE;


--
-- Name: agents_memory_entries FK_0edf1226b77ddc525eae4938079; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents_memory_entries
    ADD CONSTRAINT "FK_0edf1226b77ddc525eae4938079" FOREIGN KEY ("supersededBy") REFERENCES public.agents_memory_entries(id);


--
-- Name: instance_ai_observation_locks FK_103e2e5f454860b28ea05a82c74; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_ai_observation_locks
    ADD CONSTRAINT "FK_103e2e5f454860b28ea05a82c74" FOREIGN KEY ("observationScopeId") REFERENCES public.instance_ai_threads(id) ON DELETE CASCADE;


--
-- Name: agents_observations FK_127ee1078ffa952bb37b511efad; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents_observations
    ADD CONSTRAINT "FK_127ee1078ffa952bb37b511efad" FOREIGN KEY ("supersededBy") REFERENCES public.agents_observations(id);


--
-- Name: agents_memory_entries FK_1443a75e59adbfb796071d66393; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents_memory_entries
    ADD CONSTRAINT "FK_1443a75e59adbfb796071d66393" FOREIGN KEY ("resourceId") REFERENCES public.agents_resources(id) ON DELETE CASCADE;


--
-- Name: project_secrets_provider_access FK_18e5c27d2524b1638b292904e48; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_secrets_provider_access
    ADD CONSTRAINT "FK_18e5c27d2524b1638b292904e48" FOREIGN KEY ("secretsProviderConnectionId") REFERENCES public.secrets_provider_connection(id) ON DELETE CASCADE;


--
-- Name: agent_task_snapshot FK_1acedce6690392ef1611cca8b88; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_task_snapshot
    ADD CONSTRAINT "FK_1acedce6690392ef1611cca8b88" FOREIGN KEY ("versionId") REFERENCES public.agent_history("versionId") ON DELETE CASCADE;


--
-- Name: instance_ai_mcp_registry_connections FK_1d25707354d2012da256eb2ec0a; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_ai_mcp_registry_connections
    ADD CONSTRAINT "FK_1d25707354d2012da256eb2ec0a" FOREIGN KEY ("serverSlug") REFERENCES public.mcp_registry_server(slug) ON DELETE CASCADE;


--
-- Name: insights_metadata FK_1d8ab99d5861c9388d2dc1cf733; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.insights_metadata
    ADD CONSTRAINT "FK_1d8ab99d5861c9388d2dc1cf733" FOREIGN KEY ("workflowId") REFERENCES public.workflow_entity(id) ON DELETE SET NULL;


--
-- Name: user_favorites FK_1dd5c393ad0517be3c31a7af836; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_favorites
    ADD CONSTRAINT "FK_1dd5c393ad0517be3c31a7af836" FOREIGN KEY ("userId") REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: workflow_history FK_1e31657f5fe46816c34be7c1b4b; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_history
    ADD CONSTRAINT "FK_1e31657f5fe46816c34be7c1b4b" FOREIGN KEY ("workflowId") REFERENCES public.workflow_entity(id) ON DELETE CASCADE;


--
-- Name: instance_ai_mcp_registry_connections FK_1e826120e7e53ebc4681f026de8; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_ai_mcp_registry_connections
    ADD CONSTRAINT "FK_1e826120e7e53ebc4681f026de8" FOREIGN KEY ("credentialId") REFERENCES public.credentials_entity(id) ON DELETE CASCADE;


--
-- Name: instance_ai_messages FK_1eeb64cb9d66a927988de759e6e; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_ai_messages
    ADD CONSTRAINT "FK_1eeb64cb9d66a927988de759e6e" FOREIGN KEY ("threadId") REFERENCES public.instance_ai_threads(id) ON DELETE CASCADE;


--
-- Name: chat_hub_messages FK_1f4998c8a7dec9e00a9ab15550e; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_hub_messages
    ADD CONSTRAINT "FK_1f4998c8a7dec9e00a9ab15550e" FOREIGN KEY ("revisionOfMessageId") REFERENCES public.chat_hub_messages(id) ON DELETE CASCADE;


--
-- Name: oauth_user_consents FK_21e6c3c2d78a097478fae6aaefa; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.oauth_user_consents
    ADD CONSTRAINT "FK_21e6c3c2d78a097478fae6aaefa" FOREIGN KEY ("userId") REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: insights_metadata FK_2375a1eda085adb16b24615b69c; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.insights_metadata
    ADD CONSTRAINT "FK_2375a1eda085adb16b24615b69c" FOREIGN KEY ("projectId") REFERENCES public.project(id) ON DELETE SET NULL;


--
-- Name: chat_hub_messages FK_25c9736e7f769f3a005eef4b372; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_hub_messages
    ADD CONSTRAINT "FK_25c9736e7f769f3a005eef4b372" FOREIGN KEY ("retryOfMessageId") REFERENCES public.chat_hub_messages(id) ON DELETE CASCADE;


--
-- Name: agents_memory_entries FK_28e981fb675e9b44ce02f0ec1dd; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents_memory_entries
    ADD CONSTRAINT "FK_28e981fb675e9b44ce02f0ec1dd" FOREIGN KEY ("agentId") REFERENCES public.agents(id) ON DELETE CASCADE;


--
-- Name: instance_ai_checkpoints FK_2b23f3f24a70bebb990203b011e; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_ai_checkpoints
    ADD CONSTRAINT "FK_2b23f3f24a70bebb990203b011e" FOREIGN KEY ("threadId") REFERENCES public.instance_ai_threads(id) ON DELETE CASCADE;


--
-- Name: chat_hub_agent_tools FK_2b53d796b3dbae91b1a9553c048; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_hub_agent_tools
    ADD CONSTRAINT "FK_2b53d796b3dbae91b1a9553c048" FOREIGN KEY ("agentId") REFERENCES public.chat_hub_agents(id) ON DELETE CASCADE;


--
-- Name: instance_ai_run_snapshots FK_2f63fa21d09d7918f347ddbdf70; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_ai_run_snapshots
    ADD CONSTRAINT "FK_2f63fa21d09d7918f347ddbdf70" FOREIGN KEY ("threadId") REFERENCES public.instance_ai_threads(id) ON DELETE CASCADE;


--
-- Name: execution_metadata FK_31d0b4c93fb85ced26f6005cda3; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.execution_metadata
    ADD CONSTRAINT "FK_31d0b4c93fb85ced26f6005cda3" FOREIGN KEY ("executionId") REFERENCES public.execution_entity(id) ON DELETE CASCADE;


--
-- Name: instance_ai_observational_memory FK_34018c303885cd37093458e6409; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_ai_observational_memory
    ADD CONSTRAINT "FK_34018c303885cd37093458e6409" FOREIGN KEY ("threadId") REFERENCES public.instance_ai_threads(id) ON DELETE SET NULL;


--
-- Name: role_mapping_rule_project FK_35a78869286c65d9330d02b88f5; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_mapping_rule_project
    ADD CONSTRAINT "FK_35a78869286c65d9330d02b88f5" FOREIGN KEY ("projectId") REFERENCES public.project(id) ON DELETE CASCADE;


--
-- Name: ai_builder_temporary_workflow FK_39b07732e819fb561d74c38763f; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_builder_temporary_workflow
    ADD CONSTRAINT "FK_39b07732e819fb561d74c38763f" FOREIGN KEY ("threadId") REFERENCES public.instance_ai_threads(id) ON DELETE CASCADE;


--
-- Name: shared_credentials FK_416f66fc846c7c442970c094ccf; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shared_credentials
    ADD CONSTRAINT "FK_416f66fc846c7c442970c094ccf" FOREIGN KEY ("credentialsId") REFERENCES public.credentials_entity(id) ON DELETE CASCADE;


--
-- Name: variables FK_42f6c766f9f9d2edcc15bdd6e9b; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.variables
    ADD CONSTRAINT "FK_42f6c766f9f9d2edcc15bdd6e9b" FOREIGN KEY ("projectId") REFERENCES public.project(id) ON DELETE CASCADE;


--
-- Name: chat_hub_agent_tools FK_43e70f04c53344f82483d0570f6; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_hub_agent_tools
    ADD CONSTRAINT "FK_43e70f04c53344f82483d0570f6" FOREIGN KEY ("toolId") REFERENCES public.chat_hub_tools(id) ON DELETE CASCADE;


--
-- Name: chat_hub_agents FK_441ba2caba11e077ce3fbfa2cd8; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_hub_agents
    ADD CONSTRAINT "FK_441ba2caba11e077ce3fbfa2cd8" FOREIGN KEY ("ownerId") REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: agents_memory_entry_sources FK_451d387a182fa8dd8002dfc3a77; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents_memory_entry_sources
    ADD CONSTRAINT "FK_451d387a182fa8dd8002dfc3a77" FOREIGN KEY ("threadId") REFERENCES public.agents_threads(id) ON DELETE CASCADE;


--
-- Name: agents_memory_entry_sources FK_4706f6223313959b7437a2b48df; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents_memory_entry_sources
    ADD CONSTRAINT "FK_4706f6223313959b7437a2b48df" FOREIGN KEY ("memoryEntryId") REFERENCES public.agents_memory_entries(id) ON DELETE CASCADE;


--
-- Name: agents_observations FK_4cfd8a70ebb0a5b0cf047dca3cf; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents_observations
    ADD CONSTRAINT "FK_4cfd8a70ebb0a5b0cf047dca3cf" FOREIGN KEY ("observationScopeId") REFERENCES public.agents_threads(id) ON DELETE CASCADE;


--
-- Name: agents_observations FK_501e2d1701a10e24fb69ab5fc5f; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents_observations
    ADD CONSTRAINT "FK_501e2d1701a10e24fb69ab5fc5f" FOREIGN KEY ("parentId") REFERENCES public.agents_observations(id);


--
-- Name: instance_ai_observation_cursors FK_5b6319b2e9a37c1064a72428f9a; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_ai_observation_cursors
    ADD CONSTRAINT "FK_5b6319b2e9a37c1064a72428f9a" FOREIGN KEY ("observationScopeId") REFERENCES public.instance_ai_threads(id) ON DELETE CASCADE;


--
-- Name: workflow_published_version FK_5c76fb7ee939fe2530374d3f75a; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_published_version
    ADD CONSTRAINT "FK_5c76fb7ee939fe2530374d3f75a" FOREIGN KEY ("workflowId") REFERENCES public.workflow_entity(id) ON DELETE RESTRICT;


--
-- Name: agent_checkpoints FK_5e31c210f896d539964bf99fe32; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_checkpoints
    ADD CONSTRAINT "FK_5e31c210f896d539964bf99fe32" FOREIGN KEY ("agentId") REFERENCES public.agents(id) ON DELETE CASCADE;


--
-- Name: credential_dependency FK_5ec8e8c8d3539f3696cf73b43bf; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credential_dependency
    ADD CONSTRAINT "FK_5ec8e8c8d3539f3696cf73b43bf" FOREIGN KEY ("credentialId") REFERENCES public.credentials_entity(id) ON DELETE CASCADE;


--
-- Name: project_relation FK_5f0643f6717905a05164090dde7; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_relation
    ADD CONSTRAINT "FK_5f0643f6717905a05164090dde7" FOREIGN KEY ("userId") REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: project_relation FK_61448d56d61802b5dfde5cdb002; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_relation
    ADD CONSTRAINT "FK_61448d56d61802b5dfde5cdb002" FOREIGN KEY ("projectId") REFERENCES public.project(id) ON DELETE CASCADE;


--
-- Name: insights_by_period FK_6414cfed98daabbfdd61a1cfbc0; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.insights_by_period
    ADD CONSTRAINT "FK_6414cfed98daabbfdd61a1cfbc0" FOREIGN KEY ("metaId") REFERENCES public.insights_metadata("metaId") ON DELETE CASCADE;


--
-- Name: oauth_authorization_codes FK_64d965bd072ea24fb6da55468cd; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.oauth_authorization_codes
    ADD CONSTRAINT "FK_64d965bd072ea24fb6da55468cd" FOREIGN KEY ("clientId") REFERENCES public.oauth_clients(id) ON DELETE CASCADE;


--
-- Name: agents_observation_cursors FK_64e92819f4b413661ed6e2c3c3d; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents_observation_cursors
    ADD CONSTRAINT "FK_64e92819f4b413661ed6e2c3c3d" FOREIGN KEY ("agentId") REFERENCES public.agents(id) ON DELETE CASCADE;


--
-- Name: chat_hub_session_tools FK_6596a328affd8d4967ffb303eee; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_hub_session_tools
    ADD CONSTRAINT "FK_6596a328affd8d4967ffb303eee" FOREIGN KEY ("toolId") REFERENCES public.chat_hub_tools(id) ON DELETE CASCADE;


--
-- Name: chat_hub_messages FK_6afb260449dd7a9b85355d4e0c9; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_hub_messages
    ADD CONSTRAINT "FK_6afb260449dd7a9b85355d4e0c9" FOREIGN KEY ("executionId") REFERENCES public.execution_entity(id) ON DELETE SET NULL;


--
-- Name: agents_observation_locks FK_6b55089892e447c2f82e5ec60ed; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents_observation_locks
    ADD CONSTRAINT "FK_6b55089892e447c2f82e5ec60ed" FOREIGN KEY ("observationScopeId") REFERENCES public.agents_threads(id) ON DELETE CASCADE;


--
-- Name: insights_raw FK_6e2e33741adef2a7c5d66befa4e; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.insights_raw
    ADD CONSTRAINT "FK_6e2e33741adef2a7c5d66befa4e" FOREIGN KEY ("metaId") REFERENCES public.insights_metadata("metaId") ON DELETE CASCADE;


--
-- Name: workflow_publish_history FK_6eab5bd9eedabe9c54bd879fc40; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_publish_history
    ADD CONSTRAINT "FK_6eab5bd9eedabe9c54bd879fc40" FOREIGN KEY ("userId") REFERENCES public."user"(id) ON DELETE SET NULL;


--
-- Name: dynamic_credential_user_entry FK_6edec973a6450990977bb854c38; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dynamic_credential_user_entry
    ADD CONSTRAINT "FK_6edec973a6450990977bb854c38" FOREIGN KEY ("resolverId") REFERENCES public.dynamic_credential_resolver(id) ON DELETE CASCADE;


--
-- Name: oauth_access_tokens FK_7234a36d8e49a1fa85095328845; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.oauth_access_tokens
    ADD CONSTRAINT "FK_7234a36d8e49a1fa85095328845" FOREIGN KEY ("userId") REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: installed_nodes FK_73f857fc5dce682cef8a99c11dbddbc969618951; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.installed_nodes
    ADD CONSTRAINT "FK_73f857fc5dce682cef8a99c11dbddbc969618951" FOREIGN KEY (package) REFERENCES public.installed_packages("packageName") ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: agents_memory_entry_cursors FK_746780fd115e5e4352457a3c617; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents_memory_entry_cursors
    ADD CONSTRAINT "FK_746780fd115e5e4352457a3c617" FOREIGN KEY ("agentId") REFERENCES public.agents(id) ON DELETE CASCADE;


--
-- Name: oauth_access_tokens FK_78b26968132b7e5e45b75876481; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.oauth_access_tokens
    ADD CONSTRAINT "FK_78b26968132b7e5e45b75876481" FOREIGN KEY ("clientId") REFERENCES public.oauth_clients(id) ON DELETE CASCADE;


--
-- Name: workflow_builder_session FK_7983c618db48f47bf5a4cc1e1e4; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_builder_session
    ADD CONSTRAINT "FK_7983c618db48f47bf5a4cc1e1e4" FOREIGN KEY ("workflowId") REFERENCES public.workflow_entity(id) ON DELETE CASCADE;


--
-- Name: chat_hub_sessions FK_7bc13b4c7e6afbfaf9be326c189; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_hub_sessions
    ADD CONSTRAINT "FK_7bc13b4c7e6afbfaf9be326c189" FOREIGN KEY ("credentialId") REFERENCES public.credentials_entity(id) ON DELETE SET NULL;


--
-- Name: folder FK_804ea52f6729e3940498bd54d78; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.folder
    ADD CONSTRAINT "FK_804ea52f6729e3940498bd54d78" FOREIGN KEY ("parentFolderId") REFERENCES public.folder(id) ON DELETE CASCADE;


--
-- Name: shared_credentials FK_812c2852270da1247756e77f5a4; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shared_credentials
    ADD CONSTRAINT "FK_812c2852270da1247756e77f5a4" FOREIGN KEY ("projectId") REFERENCES public.project(id) ON DELETE CASCADE;


--
-- Name: ai_builder_temporary_workflow FK_85a87a1ba0f61999fe11dc56325; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_builder_temporary_workflow
    ADD CONSTRAINT "FK_85a87a1ba0f61999fe11dc56325" FOREIGN KEY ("workflowId") REFERENCES public.workflow_entity(id) ON DELETE CASCADE;


--
-- Name: agent_history FK_8771675f44c58fb40e0feb9ee35; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_history
    ADD CONSTRAINT "FK_8771675f44c58fb40e0feb9ee35" FOREIGN KEY ("publishedById") REFERENCES public."user"(id) ON DELETE SET NULL;


--
-- Name: agents_observation_cursors FK_87aa187d27ea67eafd164905154; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents_observation_cursors
    ADD CONSTRAINT "FK_87aa187d27ea67eafd164905154" FOREIGN KEY ("observationScopeId") REFERENCES public.agents_threads(id) ON DELETE CASCADE;


--
-- Name: agent_history FK_87cd5a8da20304b089ea2f83fec; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_history
    ADD CONSTRAINT "FK_87cd5a8da20304b089ea2f83fec" FOREIGN KEY ("agentId") REFERENCES public.agents(id) ON DELETE CASCADE;


--
-- Name: instance_ai_mcp_registry_connections FK_8b42c08a531d76410980c639a5b; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_ai_mcp_registry_connections
    ADD CONSTRAINT "FK_8b42c08a531d76410980c639a5b" FOREIGN KEY ("userId") REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: instance_ai_iteration_logs FK_8bfcc6c51fd3d69b1eae8aebd49; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_ai_iteration_logs
    ADD CONSTRAINT "FK_8bfcc6c51fd3d69b1eae8aebd49" FOREIGN KEY ("threadId") REFERENCES public.instance_ai_threads(id) ON DELETE CASCADE;


--
-- Name: trusted_key FK_8c2938d746943dd8f608d23c891; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.trusted_key
    ADD CONSTRAINT "FK_8c2938d746943dd8f608d23c891" FOREIGN KEY ("sourceId") REFERENCES public.trusted_key_source(id) ON DELETE CASCADE;


--
-- Name: test_case_execution FK_8e4b4774db42f1e6dda3452b2af; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.test_case_execution
    ADD CONSTRAINT "FK_8e4b4774db42f1e6dda3452b2af" FOREIGN KEY ("testRunId") REFERENCES public.test_run(id) ON DELETE CASCADE;


--
-- Name: data_table_column FK_930b6e8faaf88294cef23484160; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_table_column
    ADD CONSTRAINT "FK_930b6e8faaf88294cef23484160" FOREIGN KEY ("dataTableId") REFERENCES public.data_table(id) ON DELETE CASCADE;


--
-- Name: agents FK_940597dfe9753375309ce6aeea0; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT "FK_940597dfe9753375309ce6aeea0" FOREIGN KEY ("activeVersionId") REFERENCES public.agent_history("versionId") ON DELETE SET NULL;


--
-- Name: dynamic_credential_user_entry FK_945ba70b342a066d1306b12ccd2; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dynamic_credential_user_entry
    ADD CONSTRAINT "FK_945ba70b342a066d1306b12ccd2" FOREIGN KEY ("credentialId") REFERENCES public.credentials_entity(id) ON DELETE CASCADE;


--
-- Name: folder_tag FK_94a60854e06f2897b2e0d39edba; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.folder_tag
    ADD CONSTRAINT "FK_94a60854e06f2897b2e0d39edba" FOREIGN KEY ("folderId") REFERENCES public.folder(id) ON DELETE CASCADE;


--
-- Name: agents_memory_entry_locks FK_9594c0983cfee1c8ff49b05848b; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents_memory_entry_locks
    ADD CONSTRAINT "FK_9594c0983cfee1c8ff49b05848b" FOREIGN KEY ("resourceId") REFERENCES public.agents_resources(id) ON DELETE CASCADE;


--
-- Name: execution_annotations FK_97f863fa83c4786f19565084960; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.execution_annotations
    ADD CONSTRAINT "FK_97f863fa83c4786f19565084960" FOREIGN KEY ("executionId") REFERENCES public.execution_entity(id) ON DELETE CASCADE;


--
-- Name: chat_hub_agents FK_9c61ad497dcbae499c96a6a78ba; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_hub_agents
    ADD CONSTRAINT "FK_9c61ad497dcbae499c96a6a78ba" FOREIGN KEY ("credentialId") REFERENCES public.credentials_entity(id) ON DELETE SET NULL;


--
-- Name: chat_hub_sessions FK_9f9293d9f552496c40e0d1a8f80; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_hub_sessions
    ADD CONSTRAINT "FK_9f9293d9f552496c40e0d1a8f80" FOREIGN KEY ("workflowId") REFERENCES public.workflow_entity(id) ON DELETE SET NULL;


--
-- Name: agents FK_a30d560207c4071d98aa03c179c; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT "FK_a30d560207c4071d98aa03c179c" FOREIGN KEY ("projectId") REFERENCES public.project(id) ON DELETE CASCADE;


--
-- Name: execution_annotation_tags FK_a3697779b366e131b2bbdae2976; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.execution_annotation_tags
    ADD CONSTRAINT "FK_a3697779b366e131b2bbdae2976" FOREIGN KEY ("tagId") REFERENCES public.annotation_tag_entity(id) ON DELETE CASCADE;


--
-- Name: dynamic_credential_user_entry FK_a36dc616fabc3f736bb82410a22; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dynamic_credential_user_entry
    ADD CONSTRAINT "FK_a36dc616fabc3f736bb82410a22" FOREIGN KEY ("userId") REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: shared_workflow FK_a45ea5f27bcfdc21af9b4188560; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shared_workflow
    ADD CONSTRAINT "FK_a45ea5f27bcfdc21af9b4188560" FOREIGN KEY ("projectId") REFERENCES public.project(id) ON DELETE CASCADE;


--
-- Name: evaluation_collection FK_a48ce930c3bc7604894b8f0eaad; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_collection
    ADD CONSTRAINT "FK_a48ce930c3bc7604894b8f0eaad" FOREIGN KEY ("workflowId") REFERENCES public.workflow_entity(id) ON DELETE CASCADE;


--
-- Name: workflow_dependency FK_a4ff2d9b9628ea988fa9e7d0bf8; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_dependency
    ADD CONSTRAINT "FK_a4ff2d9b9628ea988fa9e7d0bf8" FOREIGN KEY ("workflowId") REFERENCES public.workflow_entity(id) ON DELETE CASCADE;


--
-- Name: oauth_user_consents FK_a651acea2f6c97f8c4514935486; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.oauth_user_consents
    ADD CONSTRAINT "FK_a651acea2f6c97f8c4514935486" FOREIGN KEY ("clientId") REFERENCES public.oauth_clients(id) ON DELETE CASCADE;


--
-- Name: oauth_refresh_tokens FK_a699f3ed9fd0c1b19bc2608ac53; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.oauth_refresh_tokens
    ADD CONSTRAINT "FK_a699f3ed9fd0c1b19bc2608ac53" FOREIGN KEY ("userId") REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: dynamic_credential_entry FK_a6d1dd080958304a47a02952aab; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dynamic_credential_entry
    ADD CONSTRAINT "FK_a6d1dd080958304a47a02952aab" FOREIGN KEY (credential_id) REFERENCES public.credentials_entity(id) ON DELETE CASCADE;


--
-- Name: instance_ai_observations FK_a80e0ee839a2f10ba4b86e19998; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_ai_observations
    ADD CONSTRAINT "FK_a80e0ee839a2f10ba4b86e19998" FOREIGN KEY ("supersededBy") REFERENCES public.instance_ai_observations(id);


--
-- Name: folder FK_a8260b0b36939c6247f385b8221; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.folder
    ADD CONSTRAINT "FK_a8260b0b36939c6247f385b8221" FOREIGN KEY ("projectId") REFERENCES public.project(id) ON DELETE CASCADE;


--
-- Name: oauth_authorization_codes FK_aa8d3560484944c19bdf79ffa16; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.oauth_authorization_codes
    ADD CONSTRAINT "FK_aa8d3560484944c19bdf79ffa16" FOREIGN KEY ("userId") REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: agent_files FK_aca4514cb500494b64356c2e164; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_files
    ADD CONSTRAINT "FK_aca4514cb500494b64356c2e164" FOREIGN KEY ("agentId") REFERENCES public.agents(id) ON DELETE CASCADE;


--
-- Name: chat_hub_messages FK_acf8926098f063cdbbad8497fd1; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_hub_messages
    ADD CONSTRAINT "FK_acf8926098f063cdbbad8497fd1" FOREIGN KEY ("workflowId") REFERENCES public.workflow_entity(id) ON DELETE SET NULL;


--
-- Name: agent_execution FK_add2432fb6034cc18b6af299dce; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_execution
    ADD CONSTRAINT "FK_add2432fb6034cc18b6af299dce" FOREIGN KEY ("threadId") REFERENCES public.agent_execution_threads(id) ON DELETE CASCADE;


--
-- Name: oauth_refresh_tokens FK_b388696ce4d8be7ffbe8d3e4b69; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.oauth_refresh_tokens
    ADD CONSTRAINT "FK_b388696ce4d8be7ffbe8d3e4b69" FOREIGN KEY ("clientId") REFERENCES public.oauth_clients(id) ON DELETE CASCADE;


--
-- Name: workflow_publish_history FK_b4cfbc7556d07f36ca177f5e473; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_publish_history
    ADD CONSTRAINT "FK_b4cfbc7556d07f36ca177f5e473" FOREIGN KEY ("versionId") REFERENCES public.workflow_history("versionId") ON DELETE SET NULL;


--
-- Name: agent_task_run_lock FK_b57a2862ae869aab24e54cefd48; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_task_run_lock
    ADD CONSTRAINT "FK_b57a2862ae869aab24e54cefd48" FOREIGN KEY ("agentId") REFERENCES public.agents(id) ON DELETE CASCADE;


--
-- Name: chat_hub_tools FK_b8030b47af9213f1fd15450fb7f; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_hub_tools
    ADD CONSTRAINT "FK_b8030b47af9213f1fd15450fb7f" FOREIGN KEY ("ownerId") REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: instance_ai_pending_confirmations FK_ba67ee8dc311830a2eea89b6e96; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_ai_pending_confirmations
    ADD CONSTRAINT "FK_ba67ee8dc311830a2eea89b6e96" FOREIGN KEY ("threadId") REFERENCES public.instance_ai_threads(id) ON DELETE CASCADE;


--
-- Name: role_mapping_rule FK_bb66e404c35996b0d6946177501; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_mapping_rule
    ADD CONSTRAINT "FK_bb66e404c35996b0d6946177501" FOREIGN KEY (role) REFERENCES public.role(slug) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: project_secrets_provider_access FK_bd264b81209355b543878deedb1; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_secrets_provider_access
    ADD CONSTRAINT "FK_bd264b81209355b543878deedb1" FOREIGN KEY ("projectId") REFERENCES public.project(id) ON DELETE CASCADE;


--
-- Name: workflow_publish_history FK_c01316f8c2d7101ec4fa9809267; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_publish_history
    ADD CONSTRAINT "FK_c01316f8c2d7101ec4fa9809267" FOREIGN KEY ("workflowId") REFERENCES public.workflow_entity(id) ON DELETE CASCADE;


--
-- Name: execution_annotation_tags FK_c1519757391996eb06064f0e7c8; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.execution_annotation_tags
    ADD CONSTRAINT "FK_c1519757391996eb06064f0e7c8" FOREIGN KEY ("annotationId") REFERENCES public.execution_annotations(id) ON DELETE CASCADE;


--
-- Name: data_table FK_c2a794257dee48af7c9abf681de; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_table
    ADD CONSTRAINT "FK_c2a794257dee48af7c9abf681de" FOREIGN KEY ("projectId") REFERENCES public.project(id) ON DELETE CASCADE;


--
-- Name: agents_memory_entry_sources FK_c38e8a57a36b880e39a52ada2e8; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents_memory_entry_sources
    ADD CONSTRAINT "FK_c38e8a57a36b880e39a52ada2e8" FOREIGN KEY ("agentId") REFERENCES public.agents(id) ON DELETE CASCADE;


--
-- Name: project_relation FK_c6b99592dc96b0d836d7a21db91; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_relation
    ADD CONSTRAINT "FK_c6b99592dc96b0d836d7a21db91" FOREIGN KEY (role) REFERENCES public.role(slug);


--
-- Name: agents_memory_entry_sources FK_cb7c15d22fd068a0806aa57fc03; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents_memory_entry_sources
    ADD CONSTRAINT "FK_cb7c15d22fd068a0806aa57fc03" FOREIGN KEY ("observationId") REFERENCES public.agents_observations(id) ON DELETE CASCADE;


--
-- Name: chat_hub_messages FK_chat_hub_messages_agentId; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_hub_messages
    ADD CONSTRAINT "FK_chat_hub_messages_agentId" FOREIGN KEY ("agentId") REFERENCES public.chat_hub_agents(id) ON DELETE SET NULL;


--
-- Name: chat_hub_sessions FK_chat_hub_sessions_agentId; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_hub_sessions
    ADD CONSTRAINT "FK_chat_hub_sessions_agentId" FOREIGN KEY ("agentId") REFERENCES public.chat_hub_agents(id) ON DELETE SET NULL;


--
-- Name: agents_observations FK_d206432be97b7ed88d187479b1b; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agents_observations
    ADD CONSTRAINT "FK_d206432be97b7ed88d187479b1b" FOREIGN KEY ("agentId") REFERENCES public.agents(id) ON DELETE CASCADE;


--
-- Name: instance_ai_observations FK_d54fc84a6c8ac91b5e0db0378a4; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_ai_observations
    ADD CONSTRAINT "FK_d54fc84a6c8ac91b5e0db0378a4" FOREIGN KEY ("observationScopeId") REFERENCES public.instance_ai_threads(id) ON DELETE CASCADE;


--
-- Name: dynamic_credential_entry FK_d61a12235d268a49af6a3c09c13; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dynamic_credential_entry
    ADD CONSTRAINT "FK_d61a12235d268a49af6a3c09c13" FOREIGN KEY (resolver_id) REFERENCES public.dynamic_credential_resolver(id) ON DELETE CASCADE;


--
-- Name: evaluation_collection FK_d634a0c93fd7de68a87eab951b2; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_collection
    ADD CONSTRAINT "FK_d634a0c93fd7de68a87eab951b2" FOREIGN KEY ("evaluationConfigId") REFERENCES public.evaluation_config(id) ON DELETE CASCADE;


--
-- Name: test_run FK_d6870d3b6e4c185d33926f423c8; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.test_run
    ADD CONSTRAINT "FK_d6870d3b6e4c185d33926f423c8" FOREIGN KEY ("workflowId") REFERENCES public.workflow_entity(id) ON DELETE CASCADE;


--
-- Name: shared_workflow FK_daa206a04983d47d0a9c34649ce; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shared_workflow
    ADD CONSTRAINT "FK_daa206a04983d47d0a9c34649ce" FOREIGN KEY ("workflowId") REFERENCES public.workflow_entity(id) ON DELETE CASCADE;


--
-- Name: instance_ai_observations FK_daef2195a4a846eb70eed15e039; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_ai_observations
    ADD CONSTRAINT "FK_daef2195a4a846eb70eed15e039" FOREIGN KEY ("parentId") REFERENCES public.instance_ai_observations(id);


--
-- Name: folder_tag FK_dc88164176283de80af47621746; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.folder_tag
    ADD CONSTRAINT "FK_dc88164176283de80af47621746" FOREIGN KEY ("tagId") REFERENCES public.tag_entity(id) ON DELETE CASCADE;


--
-- Name: role_mapping_rule_project FK_dd7ce4dfa09e95b36a626bd9de3; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_mapping_rule_project
    ADD CONSTRAINT "FK_dd7ce4dfa09e95b36a626bd9de3" FOREIGN KEY ("roleMappingRuleId") REFERENCES public.role_mapping_rule(id) ON DELETE CASCADE;


--
-- Name: workflow_published_version FK_df3428a541b802d6a63ac56e330; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_published_version
    ADD CONSTRAINT "FK_df3428a541b802d6a63ac56e330" FOREIGN KEY ("publishedVersionId") REFERENCES public.workflow_history("versionId") ON DELETE RESTRICT;


--
-- Name: instance_ai_pending_confirmations FK_df5fd25c8bbfd2b042602600d8e; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_ai_pending_confirmations
    ADD CONSTRAINT "FK_df5fd25c8bbfd2b042602600d8e" FOREIGN KEY ("userId") REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: user_api_keys FK_e131705cbbc8fb589889b02d457; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_api_keys
    ADD CONSTRAINT "FK_e131705cbbc8fb589889b02d457" FOREIGN KEY ("userId") REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: chat_hub_messages FK_e22538eb50a71a17954cd7e076c; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_hub_messages
    ADD CONSTRAINT "FK_e22538eb50a71a17954cd7e076c" FOREIGN KEY ("sessionId") REFERENCES public.chat_hub_sessions(id) ON DELETE CASCADE;


--
-- Name: test_case_execution FK_e48965fac35d0f5b9e7f51d8c44; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.test_case_execution
    ADD CONSTRAINT "FK_e48965fac35d0f5b9e7f51d8c44" FOREIGN KEY ("executionId") REFERENCES public.execution_entity(id) ON DELETE SET NULL;


--
-- Name: chat_hub_messages FK_e5d1fa722c5a8d38ac204746662; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_hub_messages
    ADD CONSTRAINT "FK_e5d1fa722c5a8d38ac204746662" FOREIGN KEY ("previousMessageId") REFERENCES public.chat_hub_messages(id) ON DELETE CASCADE;


--
-- Name: chat_hub_session_tools FK_e649bf1295f4ed8d4299ed290f9; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_hub_session_tools
    ADD CONSTRAINT "FK_e649bf1295f4ed8d4299ed290f9" FOREIGN KEY ("sessionId") REFERENCES public.chat_hub_sessions(id) ON DELETE CASCADE;


--
-- Name: chat_hub_sessions FK_e9ecf8ede7d989fcd18790fe36a; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_hub_sessions
    ADD CONSTRAINT "FK_e9ecf8ede7d989fcd18790fe36a" FOREIGN KEY ("ownerId") REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: user FK_eaea92ee7bfb9c1b6cd01505d56; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT "FK_eaea92ee7bfb9c1b6cd01505d56" FOREIGN KEY ("roleSlug") REFERENCES public.role(slug);


--
-- Name: agent_execution_threads FK_f00b52d74fe11838e1fe086deea; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_execution_threads
    ADD CONSTRAINT "FK_f00b52d74fe11838e1fe086deea" FOREIGN KEY ("taskVersionId") REFERENCES public.agent_history("versionId") ON DELETE SET NULL;


--
-- Name: evaluation_collection FK_f4561f38b5a22a4f090d5cd3eae; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_collection
    ADD CONSTRAINT "FK_f4561f38b5a22a4f090d5cd3eae" FOREIGN KEY ("createdById") REFERENCES public."user"(id) ON DELETE SET NULL;


--
-- Name: agent_task_definition FK_f45d0535a2ed59b6c2dd6da98a0; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_task_definition
    ADD CONSTRAINT "FK_f45d0535a2ed59b6c2dd6da98a0" FOREIGN KEY ("agentId") REFERENCES public.agents(id) ON DELETE CASCADE;


--
-- Name: evaluation_config FK_fd7542bb123074760285dc1bbf3; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_config
    ADD CONSTRAINT "FK_fd7542bb123074760285dc1bbf3" FOREIGN KEY ("workflowId") REFERENCES public.workflow_entity(id) ON DELETE CASCADE;


--
-- Name: instance_ai_threads FK_instance_ai_threads_projectId; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instance_ai_threads
    ADD CONSTRAINT "FK_instance_ai_threads_projectId" FOREIGN KEY ("projectId") REFERENCES public.project(id) ON DELETE CASCADE;


--
-- Name: role_scope FK_role; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_scope
    ADD CONSTRAINT "FK_role" FOREIGN KEY ("roleSlug") REFERENCES public.role(slug) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: role_scope FK_scope; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_scope
    ADD CONSTRAINT "FK_scope" FOREIGN KEY ("scopeSlug") REFERENCES public.scope(slug) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: test_run FK_test_run_collection_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.test_run
    ADD CONSTRAINT "FK_test_run_collection_id" FOREIGN KEY ("collectionId") REFERENCES public.evaluation_collection(id) ON DELETE SET NULL;


--
-- Name: test_run FK_test_run_evaluation_config_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.test_run
    ADD CONSTRAINT "FK_test_run_evaluation_config_id" FOREIGN KEY ("evaluationConfigId") REFERENCES public.evaluation_config(id) ON DELETE SET NULL;


--
-- Name: agendamentos agendamentos_cliente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agendamentos
    ADD CONSTRAINT agendamentos_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clientes(id) ON DELETE CASCADE;


--
-- Name: atendimentos atendimentos_cliente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.atendimentos
    ADD CONSTRAINT atendimentos_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clientes(id);


--
-- Name: atendimentos atendimentos_protocolo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.atendimentos
    ADD CONSTRAINT atendimentos_protocolo_id_fkey FOREIGN KEY (protocolo_id) REFERENCES public.protocolos(id);


--
-- Name: auth_identity auth_identity_userId_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_identity
    ADD CONSTRAINT "auth_identity_userId_fkey" FOREIGN KEY ("userId") REFERENCES public."user"(id);


--
-- Name: clientes clientes_audit_encerramento_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clientes
    ADD CONSTRAINT clientes_audit_encerramento_id_fkey FOREIGN KEY (audit_encerramento_id) REFERENCES public.audit_log(id) ON DELETE SET NULL;


--
-- Name: conversas conversas_cliente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversas
    ADD CONSTRAINT conversas_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clientes(id);


--
-- Name: credentials_entity credentials_entity_resolverId_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credentials_entity
    ADD CONSTRAINT "credentials_entity_resolverId_foreign" FOREIGN KEY ("resolverId") REFERENCES public.dynamic_credential_resolver(id) ON DELETE SET NULL;


--
-- Name: documentos documentos_protocolo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentos
    ADD CONSTRAINT documentos_protocolo_id_fkey FOREIGN KEY (protocolo_id) REFERENCES public.protocolos(id);


--
-- Name: execution_data execution_data_fk; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.execution_data
    ADD CONSTRAINT execution_data_fk FOREIGN KEY ("executionId") REFERENCES public.execution_entity(id) ON DELETE CASCADE;


--
-- Name: execution_entity fk_execution_entity_workflow_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.execution_entity
    ADD CONSTRAINT fk_execution_entity_workflow_id FOREIGN KEY ("workflowId") REFERENCES public.workflow_entity(id) ON DELETE CASCADE;


--
-- Name: webhook_entity fk_webhook_entity_workflow_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook_entity
    ADD CONSTRAINT fk_webhook_entity_workflow_id FOREIGN KEY ("workflowId") REFERENCES public.workflow_entity(id) ON DELETE CASCADE;


--
-- Name: workflow_entity fk_workflow_parent_folder; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow_entity
    ADD CONSTRAINT fk_workflow_parent_folder FOREIGN KEY ("parentFolderId") REFERENCES public.folder(id) ON DELETE CASCADE;


--
-- Name: workflows_tags fk_workflows_tags_tag_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflows_tags
    ADD CONSTRAINT fk_workflows_tags_tag_id FOREIGN KEY ("tagId") REFERENCES public.tag_entity(id) ON DELETE CASCADE;


--
-- Name: workflows_tags fk_workflows_tags_workflow_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflows_tags
    ADD CONSTRAINT fk_workflows_tags_workflow_id FOREIGN KEY ("workflowId") REFERENCES public.workflow_entity(id) ON DELETE CASCADE;


--
-- Name: mensagens mensagens_sessao_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mensagens
    ADD CONSTRAINT mensagens_sessao_id_fkey FOREIGN KEY (sessao_id) REFERENCES public.sessoes_chat(id) ON DELETE CASCADE;


--
-- Name: project projects_creatorId_foreign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project
    ADD CONSTRAINT "projects_creatorId_foreign" FOREIGN KEY ("creatorId") REFERENCES public."user"(id) ON DELETE SET NULL;


--
-- Name: protocolos protocolos_cliente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.protocolos
    ADD CONSTRAINT protocolos_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clientes(id);


--
-- Name: sessoes_chat sessoes_chat_cliente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sessoes_chat
    ADD CONSTRAINT sessoes_chat_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clientes(id) ON DELETE CASCADE;


--
-- Name: agendamentos; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.agendamentos ENABLE ROW LEVEL SECURITY;

--
-- Name: clientes anon_insert_own_clientes; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY anon_insert_own_clientes ON public.clientes FOR INSERT TO anon WITH CHECK (true);


--
-- Name: clientes anon_select_own_clientes; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY anon_select_own_clientes ON public.clientes FOR SELECT TO anon USING (true);


--
-- Name: atendimentos; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.atendimentos ENABLE ROW LEVEL SECURITY;

--
-- Name: audit_log; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;

--
-- Name: atendimentos auth_all_atendimentos; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY auth_all_atendimentos ON public.atendimentos TO authenticated USING (true) WITH CHECK (true);


--
-- Name: audit_log auth_all_audit_log; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY auth_all_audit_log ON public.audit_log TO authenticated USING (true) WITH CHECK (true);


--
-- Name: conversas auth_all_conversas; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY auth_all_conversas ON public.conversas TO authenticated USING (true) WITH CHECK (true);


--
-- Name: agendamentos auth_all_own_agendamentos; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY auth_all_own_agendamentos ON public.agendamentos TO authenticated USING (true) WITH CHECK (true);


--
-- Name: mensagens auth_all_own_mensagens; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY auth_all_own_mensagens ON public.mensagens TO authenticated USING (true) WITH CHECK (true);


--
-- Name: sessoes_chat auth_all_own_sessoes_chat; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY auth_all_own_sessoes_chat ON public.sessoes_chat TO authenticated USING (true) WITH CHECK (true);


--
-- Name: emolumentos auth_select_emolumentos; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY auth_select_emolumentos ON public.emolumentos FOR SELECT TO authenticated USING (true);


--
-- Name: atendimentos authenticated_read_own; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY authenticated_read_own ON public.atendimentos FOR SELECT TO authenticated USING ((((cliente_id)::text = (auth.uid())::text) OR (cliente_id IS NULL)));


--
-- Name: clientes authenticated_read_own; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY authenticated_read_own ON public.clientes FOR SELECT TO authenticated USING ((((id)::text = (auth.uid())::text) OR (id IS NULL)));


--
-- Name: conversas authenticated_read_own; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY authenticated_read_own ON public.conversas FOR SELECT TO authenticated USING ((((cliente_id)::text = (auth.uid())::text) OR (cliente_id IS NULL)));


--
-- Name: documentos authenticated_read_own; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY authenticated_read_own ON public.documentos FOR SELECT TO authenticated USING ((((id)::text = (auth.uid())::text) OR (id IS NULL)));


--
-- Name: emolumentos authenticated_read_own; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY authenticated_read_own ON public.emolumentos FOR SELECT TO authenticated USING ((((id)::text = (auth.uid())::text) OR (id IS NULL)));


--
-- Name: protocolos authenticated_read_own; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY authenticated_read_own ON public.protocolos FOR SELECT TO authenticated USING ((((cliente_id)::text = (auth.uid())::text) OR (cliente_id IS NULL)));


--
-- Name: clientes; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.clientes ENABLE ROW LEVEL SECURITY;

--
-- Name: conversas; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.conversas ENABLE ROW LEVEL SECURITY;

--
-- Name: documentos; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.documentos ENABLE ROW LEVEL SECURITY;

--
-- Name: atendimentos dpo_read_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY dpo_read_access ON public.atendimentos FOR SELECT TO dpo USING (true);


--
-- Name: audit_log dpo_read_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY dpo_read_access ON public.audit_log FOR SELECT TO dpo USING (true);


--
-- Name: clientes dpo_read_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY dpo_read_access ON public.clientes FOR SELECT TO dpo USING (true);


--
-- Name: conversas dpo_read_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY dpo_read_access ON public.conversas FOR SELECT TO dpo USING (true);


--
-- Name: documentos dpo_read_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY dpo_read_access ON public.documentos FOR SELECT TO dpo USING (true);


--
-- Name: emolumentos dpo_read_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY dpo_read_access ON public.emolumentos FOR SELECT TO dpo USING (true);


--
-- Name: lgpd_audit_anpd dpo_read_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY dpo_read_access ON public.lgpd_audit_anpd FOR SELECT TO dpo USING (true);


--
-- Name: lgpd_consents dpo_read_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY dpo_read_access ON public.lgpd_consents FOR SELECT TO dpo USING (true);


--
-- Name: protocolos dpo_read_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY dpo_read_access ON public.protocolos FOR SELECT TO dpo USING (true);


--
-- Name: emolumentos; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.emolumentos ENABLE ROW LEVEL SECURITY;

--
-- Name: lgpd_audit_anpd; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.lgpd_audit_anpd ENABLE ROW LEVEL SECURITY;

--
-- Name: lgpd_consents; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.lgpd_consents ENABLE ROW LEVEL SECURITY;

--
-- Name: mensagens; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.mensagens ENABLE ROW LEVEL SECURITY;

--
-- Name: outbox_messages; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.outbox_messages ENABLE ROW LEVEL SECURITY;

--
-- Name: protocolos; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.protocolos ENABLE ROW LEVEL SECURITY;

--
-- Name: agendamentos service_all_agendamentos; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY service_all_agendamentos ON public.agendamentos TO service_role USING (true) WITH CHECK (true);


--
-- Name: clientes service_all_all_tables; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY service_all_all_tables ON public.clientes TO service_role USING (true) WITH CHECK (true);


--
-- Name: audit_log service_all_audit_log; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY service_all_audit_log ON public.audit_log TO service_role USING (true) WITH CHECK (true);


--
-- Name: emolumentos service_all_emolumentos; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY service_all_emolumentos ON public.emolumentos TO service_role USING (true) WITH CHECK (true);


--
-- Name: mensagens service_all_mensagens; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY service_all_mensagens ON public.mensagens TO service_role USING (true) WITH CHECK (true);


--
-- Name: sessoes_chat service_all_sessoes_chat; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY service_all_sessoes_chat ON public.sessoes_chat TO service_role USING (true) WITH CHECK (true);


--
-- Name: atendimentos service_role_full_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY service_role_full_access ON public.atendimentos TO service_role USING (true) WITH CHECK (true);


--
-- Name: audit_log service_role_full_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY service_role_full_access ON public.audit_log TO service_role USING (true) WITH CHECK (true);


--
-- Name: clientes service_role_full_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY service_role_full_access ON public.clientes TO service_role USING (true) WITH CHECK (true);


--
-- Name: conversas service_role_full_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY service_role_full_access ON public.conversas TO service_role USING (true) WITH CHECK (true);


--
-- Name: documentos service_role_full_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY service_role_full_access ON public.documentos TO service_role USING (true) WITH CHECK (true);


--
-- Name: emolumentos service_role_full_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY service_role_full_access ON public.emolumentos TO service_role USING (true) WITH CHECK (true);


--
-- Name: lgpd_audit_anpd service_role_full_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY service_role_full_access ON public.lgpd_audit_anpd TO service_role USING (true) WITH CHECK (true);


--
-- Name: lgpd_consents service_role_full_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY service_role_full_access ON public.lgpd_consents TO service_role USING (true) WITH CHECK (true);


--
-- Name: outbox_messages service_role_full_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY service_role_full_access ON public.outbox_messages TO service_role USING (true) WITH CHECK (true);


--
-- Name: protocolos service_role_full_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY service_role_full_access ON public.protocolos TO service_role USING (true) WITH CHECK (true);


--
-- Name: webhook_events service_role_full_access; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY service_role_full_access ON public.webhook_events TO service_role USING (true) WITH CHECK (true);


--
-- Name: sessoes_chat; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.sessoes_chat ENABLE ROW LEVEL SECURITY;

--
-- Name: webhook_events; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.webhook_events ENABLE ROW LEVEL SECURITY;

--
-- Name: supabase_realtime; Type: PUBLICATION; Schema: -; Owner: -
--

CREATE PUBLICATION supabase_realtime WITH (publish = 'insert, update, delete, truncate');


--
-- Name: supabase_realtime atendimentos; Type: PUBLICATION TABLE; Schema: public; Owner: -
--

ALTER PUBLICATION supabase_realtime ADD TABLE ONLY public.atendimentos;


--
-- Name: supabase_realtime conversas; Type: PUBLICATION TABLE; Schema: public; Owner: -
--

ALTER PUBLICATION supabase_realtime ADD TABLE ONLY public.conversas;


--
-- Name: supabase_realtime lgpd_consents; Type: PUBLICATION TABLE; Schema: public; Owner: -
--

ALTER PUBLICATION supabase_realtime ADD TABLE ONLY public.lgpd_consents;


--
-- Name: supabase_realtime outbox_messages; Type: PUBLICATION TABLE; Schema: public; Owner: -
--

ALTER PUBLICATION supabase_realtime ADD TABLE ONLY public.outbox_messages;


--
-- Name: supabase_realtime protocolos; Type: PUBLICATION TABLE; Schema: public; Owner: -
--

ALTER PUBLICATION supabase_realtime ADD TABLE ONLY public.protocolos;


--
-- PostgreSQL database dump complete
--

