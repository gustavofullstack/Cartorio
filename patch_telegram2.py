import re
with open("backend/app/api/v1/telegram.py", "r") as f:
    content = f.read()

# Replace the type hint for _tool_criar_atendimento argument
content = content.replace("cliente_id: int,", "cliente_id: int | str,")

with open("backend/app/api/v1/telegram.py", "w") as f:
    f.write(content)
