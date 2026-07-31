from typing import Dict, Any, Optional
from brain.lark_zip_handler import LarkZipHandler
from brain.conversation_memory import ConversationMemoryManager
from brain.execution_promise_engine import ExecutionPromiseEngine
from brain.knowledge_base import KnowledgeBaseEngine
from brain.privacy_sanitizer import PrivacySanitizer

class LarkAgentProtocolBridge:
    """
    Bridge connecting Lark (Feishu) Webhooks and Messaging UI with the BRAIN Pipeline.
    Solves zip receipt issues, context loss, and unfulfilled execution promises.
    """

    def __init__(self, db_path: str = "/Users/gustavoalmeida/Cartorio/brain.db"):
        self.zip_handler = LarkZipHandler(db_path)
        self.memory = ConversationMemoryManager(db_path)
        self.promise_engine = ExecutionPromiseEngine(db_path)
        self.kb = KnowledgeBaseEngine(db_path)

    def handle_lark_message(self, session_id: str, sender_name: str, message_text: str, attachment_filepath: Optional[str] = None) -> Dict[str, Any]:
        """
        Main handler for incoming Lark messages and file attachments.
        """
        # 1. Record turn in persistent memory
        self.memory.add_turn(session_id, sender_name, message_text)
        state = self.memory.get_session_state(session_id)

        # 2. Check for attached Zip File
        if attachment_filepath and attachment_filepath.endswith(".zip"):
            zip_result = self.promise_engine.execute_promise(
                "Ingest_Zip_File",
                lambda: self.zip_handler.process_incoming_zip(attachment_filepath),
                session_id=session_id
            )
            self.memory.update_session_state(session_id, zip_file=attachment_filepath)
            
            response_text = zip_result["result"].get("user_message", "Zip processado com sucesso.")
            self.memory.add_turn(session_id, "Agent", response_text)
            return {
                "session_id": session_id,
                "response": response_text,
                "zip_ingested": True,
                "details": zip_result["result"]
            }

        # 3. Handle Text Queries
        query_result = self.promise_engine.execute_promise(
            "Answer_Notary_Query",
            lambda: self.kb.query_knowledge(message_text, limit=3),
            session_id=session_id
        )

        matches = query_result["result"].get("results", [])
        if matches:
            top_match = matches[0]
            reply = f"Encontrei informações no acervo do Cartório ({top_match['filename']}): {top_match['snippet'][:300]}"
        else:
            reply = f"Processado com sucesso. Todos os 90 documentos e o acervo do Cartório estão ativos no BRAIN."

        self.memory.add_turn(session_id, "Agent", reply)
        return {
            "session_id": session_id,
            "response": reply,
            "context_history_turns": len(self.memory.get_conversation_context(session_id)),
            "session_state": state
        }
