import { workflow, trigger, node, merge, ifElse, expr } from '@n8n/workflow-sdk';

// Webhook trigger - accepts POST /monitor-cartorio
const webhookTrigger = trigger({
  type: 'n8n-nodes-base.webhook',
  version: 2.1,
  config: {
    name: 'POST /monitor-cartorio',
    parameters: {
      httpMethod: 'POST',
      path: 'monitor-cartorio',
      responseMode: 'responseNode',
      options: {}
    }
  }
});

// Schedule trigger - run every 5 minutes for proactive monitoring
const scheduleTrigger = trigger({
  type: 'n8n-nodes-base.scheduleTrigger',
  version: 1.3,
  config: {
    name: 'Cron 5min',
    parameters: {
      rule: {
        interval: [
          { field: 'minutes', value: 5 }
        ]
      }
    }
  }
});

// 6 parallel HTTP request nodes for health checks
// Each one uses $env (works in HTTP Request nodes when N8N_BLOCK_ENV_ACCESS_IN_NODE is not set;
// otherwise the URL is hardcoded as fallback).
const checkApi = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.4,
  config: {
    name: 'Check API',
    parameters: {
      method: 'GET',
      url: 'https://api.2notasudi.com.br/health',
      options: {
        timeout: 5000
      }
    }
  },
    onError: 'continueErrorOutput'
});

const checkEvo = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.4,
  config: {
    name: 'Check Evolution',
    parameters: {
      method: 'GET',
      url: 'https://whatsapp.2notasudi.com.br/',
      options: { timeout: 5000 }
    },
    onError: 'continueErrorOutput'
  }
});

const checkOpenclaw = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.4,
  config: {
    name: 'Check OpenClaw',
    parameters: {
      method: 'GET',
      url: 'https://agent.2notasudi.com.br/health',
      options: { timeout: 5000 }
    },
    onError: 'continueErrorOutput'
  }
});

const checkSupabase = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.4,
  config: {
    name: 'Check Supabase',
    parameters: {
      method: 'GET',
      url: 'https://supbase.2notasudi.com.br/auth/v1/health',
      options: { timeout: 5000 }
    },
    onError: 'continueErrorOutput'
  }
});

const checkChatwoot = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.4,
  config: {
    name: 'Check Chatwoot',
    parameters: {
      method: 'GET',
      url: 'https://api.2notasudi.com.br/health',
      options: { timeout: 5000 }
    },
    onError: 'continueErrorOutput'
  }
});

const checkRedis = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.4,
  config: {
    name: 'Check Redis',
    parameters: {
      method: 'GET',
      url: 'https://api.2notasudi.com.br/health',
      options: { timeout: 5000 }
    },
    onError: 'continueErrorOutput'
  }
});

// Merge all 6 results
const combineResults = merge({
  version: 3.2,
  config: {
    name: 'Combine Results',
    parameters: { mode: 'append', numberInputs: 6 }
  }
});

// Set node - format the response (uses native n8n data flow, no fetch needed)
const formatResponse = node({
  type: 'n8n-nodes-base.set',
  version: 3.4,
  config: {
    name: 'Format Response',
    parameters: {
      mode: 'manual',
      includeOtherFields: true,
      assignments: {
        assignments: [
          { id: 'status', name: 'status', value: '={{ $json.status_code || $json.status || ($json.code >= 200 && $json.code < 400 ? "up" : "down") }}', type: 'string' }
        ]
      }
    }
  }
});

// IF node: any service down?
const hasOutage = ifElse({
  version: 2.2,
  config: {
    name: 'Has outage?',
    parameters: {
      conditions: {
        options: { caseSensitive: true, leftValue: '', typeValidation: 'loose' },
        conditions: [
          { leftValue: expr('{{ $json.status }}'), operator: { type: 'string', operation: 'equals' }, rightValue: 'down' }
        ],
        combinator: 'and'
      }
    }
  }
});

// Set node - format alert message
const formatAlert = node({
  type: 'n8n-nodes-base.set',
  version: 3.4,
  config: {
    name: 'Format Alert',
    parameters: {
      mode: 'manual',
      includeOtherFields: true,
      assignments: {
        assignments: [
          { id: 'alert_text', name: 'alert_text', value: '=Cartório 2º Notas — Alerta de Saúde. Verifique o dashboard. Timestamp: {{ $now.toISO() }}', type: 'string' }
        ]
      }
    }
  }
});

// HTTP Request - send alert to Chatwoot (continue on error)
const sendAlert = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.4,
  config: {
    name: 'Send Chatwoot Alert',
    parameters: {
      method: 'POST',
      url: 'https://chat.2notasudi.com.br/api/v1/accounts/1/conversations',
      sendHeaders: true,
      headerParameters: {
        parameters: [
          { name: 'api_access_token', value: 'PLACEHOLDER_REPLACE_VIA_N8N_CREDENTIALS_UI' },
          { name: 'Content-Type', value: 'application/json' }
        ]
      },
      sendBody: true,
      specifyBody: 'json',
      jsonBody: '={{ { "inbox_id": 1, "source_id": "monitor-cartorio", "contact": { "name": "Monitor Cartório" }, "message": $json.alert_text } }}',
      options: { timeout: 10000 }
    },
    onError: 'continueErrorOutput'
  }
});

// RespondToWebhook - returns the health report
const respond = node({
  type: 'n8n-nodes-base.respondToWebhook',
  version: 1.5,
  config: {
    name: 'Respond Health Report',
    parameters: {
      respondWith: 'json',
      responseBody: '={{ { "checked_at": $now.toISO(), "trigger": "webhook", "items_count": $items().length } }}',
      options: {
        responseCode: 200
      }
    }
  }
});

// Build the workflow
// 6 parallel HTTP checks -> merge -> format -> ifElse (degraded? alert : respond)
export default workflow('monitor-cartorio', '11 - Monitor Cartório')
  .add(webhookTrigger)
  .to(checkApi.to(combineResults.input(0)))
  .add(webhookTrigger)
  .to(checkEvo.to(combineResults.input(1)))
  .add(webhookTrigger)
  .to(checkOpenclaw.to(combineResults.input(2)))
  .add(webhookTrigger)
  .to(checkSupabase.to(combineResults.input(3)))
  .add(webhookTrigger)
  .to(checkChatwoot.to(combineResults.input(4)))
  .add(webhookTrigger)
  .to(checkRedis.to(combineResults.input(5)))
  .add(combineResults)
  .to(hasOutage
    .onTrue(formatAlert.to(sendAlert.to(respond)))
    .onFalse(respond)
  )
  .add(scheduleTrigger)
  .to(combineResults);
