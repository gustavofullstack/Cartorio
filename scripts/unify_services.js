const { open } = require("lmdb");

const db = open({
  path: "/etc/easypanel/data",
});

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
  "lobechat"
];

services.forEach((name) => {
  const key = `services:cartorio:${name}`;
  const rawValue = db.get(key);
  
  if (!rawValue) {
    console.error(`[-] Key not found: ${key}`);
    return;
  }
  
  console.log(`[+] Modificando serviço: ${name}`);
  let data = JSON.parse(rawValue);
  let jsonObj = data.json;
  
  let envLines = jsonObj.env.split("\n");
  
  // Função auxiliar para definir ou substituir uma variável de ambiente
  function setEnvVar(varName, value) {
    envLines = envLines.filter(line => !line.startsWith(`${varName}=`));
    envLines.push(`${varName}=${value}`);
  }
  
  if (name === "crwal4ai") {
    jsonObj.source.image = "unclecode/crawl4ai:latest";
  }
  
  if (name === "chatwoot" || name === "chatwoot-sidekiq") {
    setEnvVar("POSTGRES_HOST", "cartorio_supabase");
    setEnvVar("POSTGRES_USERNAME", "admin");
    setEnvVar("POSTGRES_PASSWORD", "@Techno832466");
  }
  
  if (name === "litellm-app") {
    setEnvVar("DATABASE_URL", "postgresql://admin:%40Techno832466@cartorio_supabase:5432/litellm");
  }
  
  if (name === "langfuse-web" || name === "langfuse-worker") {
    setEnvVar("DATABASE_URL", "postgresql://admin:%40Techno832466@cartorio_supabase:5432/langfuse");
    setEnvVar("REDIS_HOST", "cartorio_redis");
    setEnvVar("REDIS_AUTH", "@Techno832466");
  }
  
  if (name === "argilla-web" || name === "argilla-worker") {
    // Usa argilla_user para evitar o erro de interpolação do configparser no Alembic
    setEnvVar("ARGILLA_DATABASE_URL", "postgresql+asyncpg://argilla_user:argillaPassword123@cartorio_supabase:5432/argilla");
    setEnvVar("ARGILLA_REDIS_URL", "redis://:%40Techno832466@cartorio_redis:6379/0");
  }
  
  if (name === "anything-llm") {
    jsonObj.source.image = "mintplexlabs/anythingllm:pg";
    setEnvVar("DATABASE_URL", "postgresql://admin:%40Techno832466@cartorio_supabase:5432/anythingllm");
  }
  
  if (name === "lobechat") {
    setEnvVar("OPENAI_API_KEY", "0vrszdxd19zweryz7cfl");
    setEnvVar("OPENAI_PROXY_URL", "http://cartorio_litellm-app:4000/v1");
  }
  
  jsonObj.env = envLines.join("\n");
  data.json = jsonObj;
  db.put(key, JSON.stringify(data));
  console.log(`[+] Salvo com sucesso no banco: ${key}`);
});

console.log("[+] Migração de serviços finalizada com sucesso.");
