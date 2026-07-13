import re
with open("backend/app/api/v1/telegram.py", "r") as f:
    content = f.read()

# Replace the type hint for user_id to accept None
content = content.replace("user_id: int | None = None", "user_id: int | str | None = None")

with open("backend/app/api/v1/telegram.py", "w") as f:
    f.write(content)
