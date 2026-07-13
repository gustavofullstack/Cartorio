import re
with open("backend/app/api/v1/telegram.py", "r") as f:
    content = f.read()

# Make key argument accept None as well since that's what's failing now
content = content.replace("bus: Any, key: int | str, *, user_id: int | str | None = None", "bus: Any, key: int | str | None, *, user_id: int | str | None = None")

with open("backend/app/api/v1/telegram.py", "w") as f:
    f.write(content)
