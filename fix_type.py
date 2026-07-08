import re

with open('backend/app/api/v1/telegram.py', 'r') as f:
    content = f.read()

content = content.replace(
    'if not hasattr(_get_tg_pool, "_loop_id"):',
    'if not hasattr(_get_tg_pool, "_loop_id"):  # type: ignore[attr-defined]'
).replace(
    '_get_tg_pool._loop_id = 0',
    '_get_tg_pool._loop_id = 0  # type: ignore[attr-defined]'
).replace(
    'if _TG_HTTP_POOL is None or _get_tg_pool._loop_id != current_loop_id:',
    'if _TG_HTTP_POOL is None or _get_tg_pool._loop_id != current_loop_id:  # type: ignore[attr-defined]'
).replace(
    '_get_tg_pool._loop_id = current_loop_id',
    '_get_tg_pool._loop_id = current_loop_id  # type: ignore[attr-defined]'
)

with open('backend/app/api/v1/telegram.py', 'w') as f:
    f.write(content)
