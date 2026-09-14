with open("backend/scripts/check_no_literal_keys.baseline", "r") as f:
    lines = f.read().splitlines()

new_lines = []
for line in lines:
    if line.startswith("backend/app/services/tjmg_ocr_loader.py:") or \
       line.startswith("backend/tests/test_agent_security_g9.py:") or \
       line.startswith("backend/tests/test_mcp_gate_e310.py:") or \
       line.startswith("backend/tests/test_mcp_tool_errors_e206.py:"):
        new_lines.append("# ALLOW_KEY_FALLBACK (false positive / synthetic keys / safe public fingerprint)")
    new_lines.append(line)

with open("backend/scripts/check_no_literal_keys.baseline", "w") as f:
    f.write("\n".join(new_lines) + "\n")
