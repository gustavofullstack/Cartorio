import datetime
from typing import Dict, Any, Callable, Optional
from brain.privacy_sanitizer import PrivacySanitizer
from brain.traceability import TraceabilityLogger

class ExecutionPromiseEngine:
    """
    Execution Promise & Progress Tracker.
    Eliminates 'talking about doing without executing' by capturing promises,
    executing promised actions immediately, and logging completion status.
    """

    def __init__(self, db_path: str = "/Users/gustavoalmeida/Cartorio/brain.db"):
        self.logger = TraceabilityLogger(db_path)

    def execute_promise(self, promise_name: str, action_func: Callable[[], Any], session_id: str = "default_session") -> Dict[str, Any]:
        """
        Executes a promised agent action synchronously, guaranteeing an immediate result payload.
        """
        start_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            result = action_func()
            end_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
            
            payload = {
                "promise_name": promise_name,
                "status": "COMPLETED",
                "session_id": session_id,
                "result": result,
                "started_at": start_time,
                "completed_at": end_time
            }
            self.logger.log_action("ExecutionPromiseEngine", promise_name, {"session_id": session_id}, payload, 1.0)
            return payload

        except Exception as e:
            end_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
            payload = {
                "promise_name": promise_name,
                "status": "FAILED",
                "session_id": session_id,
                "error": str(e),
                "started_at": start_time,
                "completed_at": end_time
            }
            self.logger.log_action("ExecutionPromiseEngine", promise_name, {"session_id": session_id}, payload, 0.0)
            return payload
