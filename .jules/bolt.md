## 2024-06-26 - [Async file I/O]
 **Learning:** When optimizing blocking file I/O operations (like `json.load` and `os.listdir`) in FastAPI async endpoints, use `starlette.concurrency.run_in_threadpool` to offload synchronous calls and prevent blocking the main ASGI event loop.
 **Action:** Extract blocking `open()` and `os.listdir()` operations into local helper functions and await them with `run_in_threadpool`.
