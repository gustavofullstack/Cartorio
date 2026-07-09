// JavaScript client for coding-vps MCP orchestrator
// Usage: node coding_vps_client.js list
//        node coding_vps_client.js call chat_minimax prompt="hello"

const BASE_URL = process.env.CODING_VPS_URL || "http://100.99.172.84:8100";

async function listTools() {
  const r = await fetch(`${BASE_URL}/tools`);
  return await r.json();
}

async function callTool(toolName, kwargs = {}) {
  const r = await fetch(`${BASE_URL}/call/${toolName}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(kwargs),
  });
  return await r.json();
}

async function main() {
  const [cmd, ...args] = process.argv.slice(2);
  if (cmd === "list") {
    const tools = await listTools();
    console.log(`Available tools: ${Object.keys(tools).length}`);
    for (const [name, info] of Object.entries(tools)) {
      console.log(`  [${info.category.padEnd(12)}] ${name}(${info.args.join(", ")})`);
    }
  } else if (cmd === "call") {
    const toolName = args[0];
    const kwargs = {};
    for (const arg of args.slice(1)) {
      const [k, v] = arg.split("=", 2);
      if (k && v) kwargs[k] = v;
    }
    const result = await callTool(toolName, kwargs);
    console.log(JSON.stringify(result, null, 2));
  } else {
    console.error("Usage: node coding_vps_client.js [list|call <tool> ...]");
    process.exit(1);
  }
}

main().catch((e) => { console.error(e); process.exit(1); });
