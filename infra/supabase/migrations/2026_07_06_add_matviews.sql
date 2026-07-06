-- Materialized views para performance (SQUAD A22)
-- Sprint 47 - 2026-07-06

CREATE MATERIALIZED VIEW IF NOT EXISTS public.mv_emolumento_stats AS
SELECT
    tipo_ato,
    COUNT(*) AS total_atos,
    AVG(valor) AS valor_medio,
    SUM(valor) AS valor_total,
    DATE_TRUNC('month', created_at) AS mes
FROM public.emolumento
WHERE deleted_at IS NULL
GROUP BY tipo_ato, DATE_TRUNC('month', created_at);

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_emol_stats
    ON public.mv_emolumento_stats (tipo_ato, mes);

CREATE MATERIALIZED VIEW IF NOT EXISTS public.mv_protocolo_aging AS
SELECT
    status,
    COUNT(*) AS total,
    AVG(EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400) AS dias_medio,
    MAX(EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400) AS dias_maximo
FROM public.protocolo
WHERE deleted_at IS NULL
GROUP BY status;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_proto_aging
    ON public.mv_protocolo_aging (status);

COMMENT ON MATERIALIZED VIEW public.mv_emolumento_stats IS
    'Stats mensais emolumentos por tipo de ato (SQUAD A22)';
COMMENT ON MATERIALIZED VIEW public.mv_protocolo_aging IS
    'Aging de protocolos por status (SQUAD A22)';
