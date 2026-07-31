import os
import pytest
from brain.traceability import TraceabilityLogger

def test_traceability_logging(tmp_path):
    db_file = str(tmp_path / "test_trace.db")
    logger = TraceabilityLogger(db_path=db_file)
    
    log_entry = logger.log_action("TestAgent", "test_action", {"key": "val"}, {"out": "ok"}, confidence_score=0.95)
    assert log_entry["agent_name"] == "TestAgent"
    assert log_entry["action_type"] == "test_action"
    assert log_entry["confidence_score"] == 0.95
    assert len(log_entry["data_hash"]) == 16

    logs = logger.get_logs(agent_name="TestAgent")
    assert len(logs) == 1
    assert logs[0]["agent_name"] == "TestAgent"
