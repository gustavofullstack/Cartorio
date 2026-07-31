import os
import pytest
from brain.lark_zip_handler import LarkZipHandler
from brain.conversation_memory import ConversationMemoryManager
from brain.execution_promise_engine import ExecutionPromiseEngine
from brain.lark_agent_protocol import LarkAgentProtocolBridge

def test_lark_zip_handler_missing_file(tmp_path):
    db_file = str(tmp_path / "test_lark.db")
    handler = LarkZipHandler(db_path=db_file)
    res = handler.process_incoming_zip("/invalid/path/file.zip")
    assert res["success"] is False
    assert "não encontrado" in res["error"]

def test_lark_zip_handler_real_zip(tmp_path):
    db_file = str(tmp_path / "test_lark_real.db")
    handler = LarkZipHandler(db_path=db_file)
    res = handler.process_incoming_zip("/Users/gustavoalmeida/Downloads/Cartorio-20260731T144042Z-1-001.zip")
    assert res["success"] is True
    assert res["total_files_extracted"] == 90

def test_conversation_memory(tmp_path):
    db_file = str(tmp_path / "test_mem.db")
    mem = ConversationMemoryManager(db_path=db_file)
    
    mem.add_turn("session_123", "User", "Te mandei o zip da usucapião")
    mem.add_turn("session_123", "Agent", "Recebi o zip com 90 documentos.")
    
    turns = mem.get_conversation_context("session_123")
    assert len(turns) == 2
    assert turns[0]["sender"] == "User"
    assert turns[1]["sender"] == "Agent"

    mem.update_session_state("session_123", act="Usucapião", client="Gustavo")
    state = mem.get_session_state("session_123")
    assert state["current_act"] == "Usucapião"
    assert state["client_name"] == "Gustavo"

def test_execution_promise_engine(tmp_path):
    db_file = str(tmp_path / "test_promise.db")
    engine = ExecutionPromiseEngine(db_path=db_file)
    
    res = engine.execute_promise("Calculate_Test", lambda: 10 + 20, session_id="s1")
    assert res["status"] == "COMPLETED"
    assert res["result"] == 30

def test_lark_agent_protocol_bridge(tmp_path):
    db_file = str(tmp_path / "test_bridge.db")
    bridge = LarkAgentProtocolBridge(db_path=db_file)
    
    res = bridge.handle_lark_message("lark_session_1", "Gustavo", "Tudo isso registrado de cabo a rabo?")
    assert "session_id" in res
    assert "response" in res
    assert res["context_history_turns"] == 2
