import re

with open('backend/app/config.py', 'r') as f:
    content = f.read()

content = content.replace(
    'app_env: Literal["development", "staging", "production"] = "development"',
    'app_env: Literal["development", "staging", "production", "testing"] = "development"'
)

with open('backend/app/config.py', 'w') as f:
    f.write(content)
