const { open } = require("lmdb");
const http = require("http");

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

function post(url) {
  return new Promise((resolve, reject) => {
    const req = http.request(url, { method: "POST" }, (res) => {
      let data = "";
      res.on("data", (chunk) => { data += chunk; });
      res.on("end", () => { resolve({ statusCode: res.statusCode, body: data }); });
    });
    req.on("error", (err) => { reject(err); });
    req.end();
  });
}

async function run() {
  for (let name of services) {
    const key = `services:cartorio:${name}`;
    const rawValue = db.get(key);
    if (!rawValue) {
      console.error(`[-] Service not found: ${name}`);
      continue;
    }
    const data = JSON.parse(rawValue);
    const token = data.json.token;
    if (!token) {
      console.error(`[-] No token for service: ${name}`);
      continue;
    }
    console.log(`[+] Deploying ${name} with token: ${token}...`);
    try {
      const res = await post(`http://localhost:3000/api/deploy/${token}`);
      console.log(`[+] Result for ${name}: status=${res.statusCode}, body=${res.body}`);
    } catch (err) {
      console.error(`[-] Error deploying ${name}:`, err.message);
    }
    // Espera 1 segundo entre deploys para evitar sobrecarregar o Swarm de uma vez
    await new Promise((r) => setTimeout(r, 1000));
  }
}

run();
