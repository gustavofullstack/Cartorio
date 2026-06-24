-- ============================================
-- 2026-06-24 Supabase Real Rollout
-- 11 tables + 3 RPCs
-- (cron/vault/pg_net não disponíveis nesta instância)
-- ============================================

-- BLOCO 1: TABELAS
CREATE TABLE IF NOT EXISTS lgpd_consent_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cliente_id UUID,
  conversation_id UUID,
  consent_type VARCHAR(50) NOT NULL,
  granted BOOLEAN NOT NULL,
  ip_truncated INET,
  user_agent_truncated VARCHAR(50),
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_lgpd_consent_cliente ON lgpd_consent_log(cliente_id);

CREATE TABLE IF NOT EXISTS opt_out_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phone VARCHAR(20) NOT NULL UNIQUE,
  channel VARCHAR(20) NOT NULL,
  keyword VARCHAR(50),
  opted_out_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_optout_phone ON opt_out_log(phone);

CREATE TABLE IF NOT EXISTS cpf_cnpj_validator (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cpf_hash VARCHAR(64) UNIQUE,
  cnpj_hash VARCHAR(64) UNIQUE,
  validated_at TIMESTAMPTZ DEFAULT NOW(),
  source VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS atendimento_link (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  atendimento_id UUID NOT NULL,
  protocolo_id UUID,
  cliente_id UUID,
  conversa_id UUID,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_atendimento_link_atendimento ON atendimento_link(atendimento_id);

CREATE TABLE IF NOT EXISTS evolution_instance (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  instance_name VARCHAR(100) UNIQUE NOT NULL,
  phone VARCHAR(20),
  state VARCHAR(20),
  qr_code_base64 TEXT,
  last_seen_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS n8n_run_log (
  id BIGSERIAL PRIMARY KEY,
  execution_id VARCHAR(100),
  workflow_id VARCHAR(100),
  workflow_name VARCHAR(200),
  status VARCHAR(20),
  started_at TIMESTAMPTZ,
  stopped_at TIMESTAMPTZ,
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_n8n_run_log_workflow ON n8n_run_log(workflow_id);

CREATE TABLE IF NOT EXISTS chatwoot_conversation_meta (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chatwoot_conversation_id BIGINT UNIQUE,
  cartorio_atendimento_id UUID,
  cartorio_protocolo_id UUID,
  handoff_at TIMESTAMPTZ,
  agent_id BIGINT,
  status VARCHAR(20),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS telegram_chat_meta (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  telegram_chat_id BIGINT UNIQUE,
  telegram_user_id BIGINT,
  username VARCHAR(100),
  cartorio_cliente_id UUID,
  session_started_at TIMESTAMPTZ,
  last_message_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rate_limit_event (
  id BIGSERIAL PRIMARY KEY,
  ip_truncated INET NOT NULL,
  endpoint VARCHAR(200),
  method VARCHAR(10),
  count INT,
  window_start TIMESTAMPTZ,
  window_end TIMESTAMPTZ,
  blocked BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_rate_limit_ip ON rate_limit_event(ip_truncated);

CREATE TABLE IF NOT EXISTS pesquisa_evolucao (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  atendimento_id UUID,
  cliente_id UUID,
  nota INT CHECK (nota BETWEEN 1 AND 5),
  comentario TEXT,
  origem VARCHAR(50),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS webhook_event_dlq (
  id BIGSERIAL PRIMARY KEY,
  source VARCHAR(50) NOT NULL,
  event_type VARCHAR(100),
  payload JSONB,
  error_message TEXT,
  attempts INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- BLOCO 2: RPCs
CREATE OR REPLACE FUNCTION criar_protocolo(
  p_cliente_id UUID,
  p_tipo VARCHAR(50),
  p_descricao TEXT,
  p_origem VARCHAR(20),
  p_metadata JSONB DEFAULT '{}'::JSONB
) RETURNS UUID
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

CREATE OR REPLACE FUNCTION opt_out_global(
  p_phone VARCHAR(20),
  p_channel VARCHAR(20),
  p_keyword VARCHAR(50) DEFAULT NULL
) RETURNS UUID
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

CREATE OR REPLACE FUNCTION registrar_auditoria(
  p_evento VARCHAR(100),
  p_recurso_id VARCHAR(100),
  p_recurso_tipo VARCHAR(50),
  p_metadata JSONB DEFAULT '{}'::JSONB
) RETURNS UUID
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
