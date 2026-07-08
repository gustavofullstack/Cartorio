## 2026-07-08 - Make Typing Action Non-Blocking
 **Learning:** When creating fire-and-forget tasks in Python 3.7+ (and especially Python 3.11+), it's important to keep a strong reference to the task created by `asyncio.create_task` to prevent the garbage collector from destroying it mid-execution.
 **Action:** Removed redundant nested tasks inside `_send_typing_fast` and instead maintained a strong reference `_typing_tasks` at the call site `telegram_webhook`.
