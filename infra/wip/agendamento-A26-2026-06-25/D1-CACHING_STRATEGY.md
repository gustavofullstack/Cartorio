# Estratégia de Cache para Agendamentos (A26)

## Visão Geral

Este documento descreve a implementação de caching Redis para otimizar o desempenho do módulo de agendamentos, reduzindo a carga no banco de dados e melhorando a latência das operações frequentemente acessadas.

## Objetivos

1. **Reduzir carga no banco de dados**: Diminuir o número de consultas ao PostgreSQL para operações frequentes
2. **Melhorar latência**: Reduzir o tempo de resposta de 20-50ms (PostgreSQL) para <5ms (Redis)
3. **Resiliência**: Implementar falha silenciosa - se Redis estiver indisponível, o sistema continua funcionando
4. **LGPD Compliance**: Garantir que as chaves de cache não exponham informações pessoais
5. **Monitoramento**: Rastrear métricas de cache hit/miss e performance

## Componentes Implementados

### 1. Módulo de Cache (`app/services/agendamento_cache.py`)

**Funcionalidades:**
- Cache de agendamentos pendentes (N8N workflow #01)
- Cache de agendamentos próximos (N8N workflow #02)
- Cache de dados de clientes para notificações
- Invalidação de cache automática
- Métricas de monitoramento

**Chaves de Cache:**
- `agendamento:v1:pendentes` - Lista de agendamentos pendentes
- `agendamento:v1:proximos` - Lista de agendamentos próximos (24h)
- `agendamento:v1:cliente:{hash}` - Dados de cliente (com ID hasheado)

**TTL (Time-to-Live):**
- 60 segundos para listas de agendamentos
- 300 segundos (5 minutos) para dados de clientes
- Versionamento (`CACHE_VERSION`) para invalidacao em massa

### 2. Integração com API

**Endpoints otimizados:**
- `GET /api/v1/agendamento/pendentes` - Cache de agendamentos pendentes
- `GET /api/v1/agendamento/proximos` - Cache de agendamentos próximos

**Fluxo de cache:**
```
1. Requisição chega ao endpoint
2. Sistema verifica cache Redis
3. Se cache hit: retorna dados cacheados
4. Se cache miss: consulta banco de dados
5. Armazena resultado no cache para próximas requisições
6. Retorna dados ao cliente
```

### 3. Invalidação de Cache

**Eventos que invalidam cache:**
- Criação de novo agendamento
- Cancelamento de agendamento
- Confirmação de agendamento
- Atualização de dados de cliente

**Métodos de invalidação:**
- `invalidate_agendamento_cache()` - Invalida todos os caches de agendamento
- `invalidate_cliente_cache(cliente_id)` - Invalida cache específico de cliente

### 4. Métricas e Monitoramento

**Métricas Prometheus:**
- `agendamento_cache_hits_total` - Contador de cache hits
- `agendamento_cache_misses_total` - Contador de cache misses
- `agendamento_cache_errors_total` - Contador de erros de cache
- `agendamento_cache_operations_total` - Total de operações de cache
- `agendamento_cache_operation_duration_ms` - Histograma de duração

**Labels:**
- `operation`: Tipo de operação (get_pendentes, get_proximos, get_cliente)
- `reason`: Razão do miss (redis_unavailable, cache_miss)
- `error`: Tipo de erro

## Implementação Técnica

### Configuração Redis

```python
# app/config.py
redis_url: str = "redis://localhost:6379/0"
```

### Exemplo de Uso

**Leitura com cache:**
```python
from app.services.agendamento_cache import get_agendamentos_pendentes_cached

# Tenta buscar do cache primeiro
cached = get_agendamentos_pendentes_cached()
if cached is not None:
    return cached

# Se cache miss, consulta banco de dados
db_data = db.query(Agendamento).all()

# Armazena no cache para próximas requisições
set_agendamentos_pendentes_cached(db_data)
```

**Escrita com invalidação:**
```python
from app.services.agendamento_cache import invalidate_agendamento_cache

# Cria novo agendamento
db.add(novo_agendamento)
db.commit()

# Invalida cache para garantir consistência
invalidate_agendamento_cache()
```

### Tratamento de Erros

**Falha silenciosa:**
```python
try:
    raw = r.get(cache_key)
    if raw is None:
        return None
    return json.loads(raw)
except Exception as e:
    logger.warning("Cache falhou: %s", e)
    # Métrica de erro
    increment_cache_metric("agendamento_cache_errors_total", {"error": type(e).__name__})
    return None  # Continua fluxo normal sem cache
```

## LGPD Compliance

**Proteção de dados:**
- Chaves de cache NÃO contêm PII (dados pessoais)
- IDs de clientes são hasheados usando `hash_pii()` com salt
- Dados cacheados são os mesmos retornados pela API (já LGPD-safe)

**Exemplo de chave segura:**
```python
# Inseguro: agendamento:cliente:123
# Seguro: agendamento:v1:cliente:hashed_abc123
```

## Benefícios Esperados

### Performance
- **Redução de carga no DB**: 4-12x menos consultas em horários de pico
- **Latência reduzida**: De 20-50ms para <5ms em cache hits
- **Throughput aumentado**: Mais requisições por segundo sem aumentar carga no banco

### Resiliência
- **Degradação elegante**: Sistema continua funcionando se Redis cair
- **Fallback automático**: Cache miss resulta em consulta ao banco de dados
- **Monitoramento proativo**: Métricas permitem detectar problemas rapidamente

### Custo
- **Eficiência**: Redis consome menos recursos que consultas PostgreSQL
- **Escalabilidade**: Cache permite escalar horizontalmente com mais facilidade

## Métricas de Sucesso

**Indicadores chave:**
1. **Cache Hit Rate**: >80% para endpoints de agendamento
2. **Latência média**: <10ms para endpoints cacheados
3. **Redução de carga DB**: 70-90% menos consultas para listas de agendamentos
4. **Disponibilidade**: 99.9% (com falha silenciosa)

**Dashboard sugerido:**
```
- Cache Hit Rate (agendamento_cache_hits_total / agendamento_cache_operations_total)
- Latência média de cache (agendamento_cache_operation_duration_ms)
- Taxa de erros de cache (agendamento_cache_errors_total)
- Comparação de latência: cache vs banco de dados
```

## Manutenção e Evolução

### Versionamento
- `CACHE_VERSION = "v1"` - Permite invalidar todos caches ao atualizar versão
- Bump da versão quando estrutura de dados cacheados mudar

### Atualizações Futuras
1. **Cache distribuído**: Implementar Redis Cluster para alta disponibilidade
2. **Cache por local**: Separar caches por local físico de atendimento
3. **Cache de prototipos**: Cachear dados de protocolos frequentemente acessados
4. **Cache warming**: Pré-carregar cache em horários de baixo tráfego

### Troubleshooting

**Problemas comuns:**
1. **Cache não está sendo usado**: Verificar se Redis está configurado corretamente
2. **Dados desatualizados**: Verificar se invalidação está sendo chamada nos eventos corretos
3. **Alta taxa de misses**: Verificar TTL e padrão de acesso
4. **Erros de conexão**: Verificar saúde do Redis e configuração de timeout

**Comandos úteis:**
```bash
# Verificar chaves de cache
redis-cli keys "agendamento:v1:*"

# Verificar TTL de uma chave
redis-cli ttl "agendamento:v1:pendentes"

# Limpar cache manualmente
redis-cli del "agendamento:v1:*"

# Monitorar operações Redis
redis-cli monitor
```

## Conclusão

A implementação de caching Redis para o módulo de agendamentos proporciona melhorias significativas de performance e escalabilidade, mantendo a conformidade com LGPD e garantindo resiliência através de mecanismos de falha silenciosa. As métricas integradas permitem monitoramento contínuo e otimização da estratégia de cache conforme o sistema evolui.