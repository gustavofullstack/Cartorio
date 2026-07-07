// scripts/unify_services.sane.js
//
// Versão SANEADA de unify_services.js (2026-07-02).
// - NÃO contém senhas em texto puro.
// - Lê credenciais de process.env (ou de um arquivo .env carregado via dotenv).
// - Falha explicitamente se faltar alguma credencial obrigatória (em vez de gravar string vazia).
// - Permite dry-run via UNIFY_DRY_RUN=1 (não chama db.put).
//
// Uso:
//   UNIFY_DRY_RUN=1 node scripts/unify_services.sane.js   # mostra o que mudaria
//   cp scripts/secrets.example.env /tmp/easypanel-secrets.env
//   # editar /tmp/easypanel-secrets.env com as credenciais reais
//   set -a; source /tmp/easypanel-secrets.env; set +a
//   node scripts/unify_services.sane.js
//
// Requer: lmdb (já presente no Easypanel), dotenv (opcional).
//
// Modified by Gustavo Almeida

const path = require("path");
const fs = require("fs");

// Carrega .env opcional (sem dep hard de dotenv).
function loadDotenv(filePath) {
  if (!fs.existsSync(filePath)) return;
  for (const line of fs.readFileSync(filePath, "utf8").split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const idx = trimmed.indexOf("=");
    if (idx < 0) continue;
    const key = trimmed.slice(0, idx).trim();
    const val = trimmed.slice(idx + 1).trim().replace(/^['"]|['"]$/g, "");
    if (!(key in process.env)) process.env[key] = val;
  }
}
loadDotenv(path.join(__dirname, "..", "deploy", "secrets.env"));
loadDotenv("/etc/cartorio/easypanel-secrets.env");
loadDotenv("/tmp/easypanel-secrets.env");

const DRY_RUN = process.env.UNIFY_DRY_RUN === "1";
const LMDB_PATH = process.env.UNIFY_LMDB_PATH || "/etc/easypanel/data";

function requireEnv(name) {
  const v = process.env[name];
  if (!v) {
    console.error(`[FATAL] env var ${name} não definida. Abortando (sem mudanças aplicadas).`);
    process.exit(2);
  }
  return v;
}

// ---- Credenciais obrigatórias ----
const SECRETS = {
  POSTGRES_ADMIN_PASSWORD: requireEnv("POSTGRES_ADMIN_PASSWORD"),
  REDIS_PASSWORD: requireEnv("REDIS_PASSWORD"),
  ARGILLA_USER_PASSWORD: requireEnv("ARGILLA_USER_PASSWORD"),
  LOBECHAT_OPENAI_API_KEY: requireEnv("LOBECHAT_OPENAI_API_KEY"),
  CRAWL4AI_API_TOKEN: requireEnv("CRAWL4AI_API_TOKEN"),
};

const { open } = require("lmdb");
const db = open({ path: LMDB_PATH });

const services = [
  "crwal4ai",
  "chatwoot",
  "chatwoot-sidekiq",
  "litellm-app",
  "langfuse-web",
  "langfuse-worker",
  "argilla-web",
  "argilla-worker",
  "anything-llm",
  "lobechat",
];

function setEnvVar(envLines, varName, value) {
  const filtered = envLines.filter((line) => !line.startsWith(`${varName}=`));
  filtered.push(`${varName}=${value}`);
  return filtered;
}

function maskUrl(url) {
  return url.replace(/\/\/([^:]+):([^@]+)@/, "//$1:***@");
}

const changes = [];

for (const name of services) {
  const key = `services:cartorio:${name}`;
  const rawValue = db.get(key);
  if (!rawValue) {
    console.error(`[-] Key not found: ${key}`);
    continue;
  }
  console.log(`[+] Processando: ${name}`);
  const data = JSON.parse(rawValue);
  const jsonObj = data.json;
  let envLines = (jsonObj.env || "").split("\n");

  if (name === "crwal4ai") {
    jsonObj.source.image = "unclecode/crawl4ai:latest";
    envLines = setEnvVar(envLines, "CRAWL4AI_API_TOKEN", SECRETS.CRAWL4AI_API_TOKEN);
    changes.push(`${name}: image -> ${jsonObj.source.image} + CRAWL4AI_API_TOKEN`);
  }
  if (name === "chatwoot" || name === "chatwoot-sidekiq") {
    envLines = setEnvVar(envLines, "POSTGRES_HOST", "cartorio_supabase");
    envLines = setEnvVar(envLines, "POSTGRES_USERNAME", "admin");
    envLines = setEnvVar(envLines, "POSTGRES_PASSWORD", SECRETS.POSTGRES_ADMIN_PASSWORD);
    changes.push(`${name}: POSTGRES_HOST/PASSWORD atualizados`);
  }
  if (name === "litellm-app") {
    envLines = setEnvVar(
      envLines,
      "DATABASE_URL",
      `postgresql://admin:${SECRETS.POSTGRES_ADMIN_PASSWORD}@cartorio_supabase:5432/litellm`
    );
    changes.push(`${name}: DATABASE_URL atualizado`);
  }
  if (name === "langfuse-web" || name === "langfuse-worker") {
    envLines = setEnvVar(
      envLines,
      "DATABASE_URL",
      `postgresql://admin:${SECRETS.POSTGRES_ADMIN_PASSWORD}@cartorio_supabase:5432/langfuse`
    );
    envLines = setEnvVar(envLines, "REDIS_HOST", "cartorio_redis");
    envLines = setEnvVar(envLines, "REDIS_AUTH", SECRETS.REDIS_PASSWORD);
    changes.push(`${name}: DATABASE_URL/REDIS atualizados`);
  }
  if (name === "argilla-web" || name === "argilla-worker") {
    // argilla_user evita o erro de interpolação do configparser no Alembic
    envLines = setEnvVar(
      envLines,
      "ARGILLA_DATABASE_URL",
      `postgresql+asyncpg://argilla_user:${SECRETS.ARGILLA_USER_PASSWORD}@cartorio_supabase:5432/argilla`
    );
    envLines = setEnvVar(
      envLines,
      "ARGILLA_REDIS_URL",
      `redis://:${encodeURIComponent(SECRETS.REDIS_PASSWORD)}@cartorio_redis:6379/0`
    );
    changes.push(`${name}: ARGILLA_DATABASE_URL/REDIS_URL atualizados`);
  }
  if (name === "anything-llm") {
    jsonObj.source.image = "mintplexlabs/anythingllm:pg";
    envLines = setEnvVar(
      envLines,
      "DATABASE_URL",
      `postgresql://admin:${SECRETS.POSTGRES_ADMIN_PASSWORD}@cartorio_supabase:5432/anythingllm`
    );
    changes.push(`${name}: image + DATABASE_URL atualizados`);
  }
  if (name === "lobechat") {
    envLines = setEnvVar(envLines, "OPENAI_API_KEY", SECRETS.LOBECHAT_OPENAI_API_KEY);
    envLines = setEnvVar(envLines, "OPENAI_PROXY_URL", "http://cartorio_litellm-app:4000/v1");
    changes.push(`${name}: OPENAI_API_KEY/PROXY_URL atualizados`);
  }

  jsonObj.env = envLines.join("\n");
  data.json = jsonObj;

  if (DRY_RUN) {
    console.log(`    [dry-run] NÃO gravou ${key}`);
  } else {
    db.put(key, JSON.stringify(data));
    console.log(`    [gravado] ${key}`);
  }
}

console.log("\n=== Resumo das mudanças ===");
for (const c of changes) console.log("  -", c);
console.log(DRY_RUN ? "\n[DRY-RUN] Nenhuma alteração persistida." : "\n[OK] Migração aplicada.");