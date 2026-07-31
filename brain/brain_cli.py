import sys
import json
import argparse
from typing import List

from brain.db import BrainDatabase
from brain.document_identifier import DocumentIdentifier
from brain.calculations import EmolumentCalculations
from brain.validations import ActValidations
from brain.knowledge_base import KnowledgeBaseEngine
from brain.privacy_sanitizer import PrivacySanitizer
from brain.traceability import TraceabilityLogger
from brain.drafting_engine import DraftingEngine
from brain.jurisprudence_matrix import JurisprudenceMatrix
from brain.enotariado_engine import ENotariadoEngine
from brain.usucapiao_adjudicacao_workflow import ExtrajudicialWorkflowEngine
from brain.estremacao_engine import EstremacaoEngine
from brain.succession_engine import SuccessionEngine
from brain.lark_zip_handler import LarkZipHandler
from brain.conversation_memory import ConversationMemoryManager
from brain.execution_promise_engine import ExecutionPromiseEngine
from brain.lark_agent_protocol import LarkAgentProtocolBridge

def main():
    parser = argparse.ArgumentParser(description="BRAIN - Cartório Notary Pipeline CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Subcommand: init-db
    init_parser = subparsers.add_parser("init-db", help="Initialize and populate database from inventory.json")
    init_parser.add_argument("--inventory", default="/Users/gustavoalmeida/Cartorio/inventory.json", help="Path to inventory.json")

    # Subcommand: identify
    id_parser = subparsers.add_parser("identify", help="Classify document category and return confidence score")
    id_parser.add_argument("text_or_file", help="Text content or filepath to identify")
    id_parser.add_argument("--filename", default="", help="Optional original filename")

    # Subcommand: calculate
    calc_parser = subparsers.add_parser("calculate", help="Calculate emoluments and tax comparison (ITCMD vs ITBI)")
    calc_parser.add_argument("--value", type=float, required=True, help="Asset/Property monetary value")
    calc_parser.add_argument("--act", default="Escritura", help="Act type")

    # Subcommand: validate
    val_parser = subparsers.add_parser("validate", help="Validate document checklist for a notary act")
    val_parser.add_argument("--act", required=True, help="Act type (e.g. 'Inventário e Partilha', 'Usucapião')")
    val_parser.add_argument("--docs", required=True, help="Comma-separated list of provided documents")

    # Subcommand: query
    query_parser = subparsers.add_parser("query", help="Query legal knowledge base and provimentos")
    query_parser.add_argument("--q", required=True, help="Search query string")
    query_parser.add_argument("--category", default=None, help="Filter category")

    # Subcommand: logs
    logs_parser = subparsers.add_parser("logs", help="View agent execution traceability audit log")
    logs_parser.add_argument("--agent", default=None, help="Filter by agent name")
    logs_parser.add_argument("--limit", type=int, default=20, help="Max entries to return")

    # Subcommand: draft
    draft_parser = subparsers.add_parser("draft", help="Generate public testament minute with diligence and medical certificate")
    draft_parser.add_argument("--testador", default="Maria Silva", help="Name of testador")
    draft_parser.add_argument("--medico", default="Dr. João Santos", help="Name of doctor")

    # Subcommand: email-response
    email_parser = subparsers.add_parser("email-response", help="Generate official email response for property deed requirement")

    # Subcommand: precedent
    prec_parser = subparsers.add_parser("precedent", help="Search STJ jurisprudence and CNJ provimentos matrix")
    prec_parser.add_argument("--q", required=True, help="Search query (e.g. 'Nancy Andrighi', 'procuração', 'usucapião')")

    # Subcommand: enotariado
    enot_parser = subparsers.add_parser("enotariado", help="Verify e-Notariado territorial jurisdiction compliance")
    enot_parser.add_argument("--property", default="", help="Property location city")
    enot_parser.add_argument("--domicile", default="", help="Party domicile city")
    enot_parser.add_argument("--serventia", default="Uberlândia", help="Notary serventia city")

    # Subcommand: usucapiao-workflow
    wf_parser = subparsers.add_parser("usucapiao-workflow", help="Get Usucapião Extrajudicial workflow stage info")
    wf_parser.add_argument("--stage", type=int, default=1, help="Stage number (1 to 7)")

    # Subcommand: estremacao-check
    est_parser = subparsers.add_parser("estremacao-check", help="Validate Estremação requirements")
    est_parser.add_argument("--posse-anos", type=float, required=True, help="Years of localized possession")

    # Subcommand: succession
    succ_parser = subparsers.add_parser("succession", help="Calculate legal succession quotas and shares")
    succ_parser.add_argument("--value", type=float, required=True, help="Total estate value")
    succ_parser.add_argument("--regime", default="Comunhão Parcial de Bens", help="Marital regime")
    succ_parser.add_argument("--children", type=int, default=2, help="Number of children")

    # Subcommand: receive-zip
    zip_parser = subparsers.add_parser("receive-zip", help="Ingest incoming zip file into BRAIN pipeline")
    zip_parser.add_argument("--file", required=True, help="Zip file path")

    # Subcommand: memory
    mem_parser = subparsers.add_parser("memory", help="Add or retrieve multi-turn conversation memory")
    mem_parser.add_argument("--session", default="lark_default", help="Session ID")
    mem_parser.add_argument("--msg", default="", help="Message text to store")

    # Subcommand: lark-msg
    lark_parser = subparsers.add_parser("lark-msg", help="Simulate incoming Lark message and process automatically")
    lark_parser.add_argument("--session", default="lark_session_1", help="Session ID")
    lark_parser.add_argument("--sender", default="Gustavo", help="Sender name")
    lark_parser.add_argument("--text", required=True, help="Message text")
    lark_parser.add_argument("--zip", default=None, help="Optional attached zip file path")

    args = parser.parse_args()

    trace_logger = TraceabilityLogger()

    if args.command == "init-db":
        db = BrainDatabase()
        db.populate_from_inventory(args.inventory)
        trace_logger.log_action("CLI_Agent", "init-db", {"inventory_path": args.inventory}, "DB Populated successfully", 1.0)

    elif args.command == "identify":
        text_input = args.text_or_file
        filename = args.filename
        if not filename and text_input.endswith((".docx", ".pdf", ".txt", ".odt")):
            filename = text_input
            text_input = f"Filename: {filename}"
        
        result = DocumentIdentifier.identify(text_input, filename=filename)
        trace_logger.log_action("CLI_Agent", "identify", {"input": text_input[:100], "filename": filename}, result, result["confidence"])
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "calculate":
        emoluments = EmolumentCalculations.calculate_emoluments(args.value, args.act)
        comparison = EmolumentCalculations.compare_doacao_vs_compra_venda(args.value)
        out = {
            "emoluments": emoluments,
            "tax_comparison": comparison
        }
        trace_logger.log_action("CLI_Agent", "calculate", {"value": args.value, "act": args.act}, out, 1.0)
        print(json.dumps(out, ensure_ascii=False, indent=2))

    elif args.command == "validate":
        docs_list = [d.strip() for d in args.docs.split(",") if d.strip()]
        result = ActValidations.validate_document_checklist(args.act, docs_list)
        trace_logger.log_action("CLI_Agent", "validate", {"act": args.act, "provided_docs": docs_list}, result, 1.0)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "query":
        kb = KnowledgeBaseEngine()
        result = kb.query_knowledge(args.q, category=args.category)
        trace_logger.log_action("CLI_Agent", "query", {"query": args.q, "category": args.category}, f"Matches: {result['total_matches']}", 1.0)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "logs":
        logs = trace_logger.get_logs(agent_name=args.agent, limit=args.limit)
        print(json.dumps(logs, ensure_ascii=False, indent=2))

    elif args.command == "draft":
        engine = DraftingEngine()
        draft = engine.draft_testamento_diligencia({"nome_testador": args.testador, "nome_medico": args.medico})
        print(draft)

    elif args.command == "email-response":
        engine = DraftingEngine()
        email = engine.generate_email_exigencia_matriculas()
        print(email)

    elif args.command == "precedent":
        results = JurisprudenceMatrix.search_precedents(args.q)
        print(json.dumps(results, ensure_ascii=False, indent=2))

    elif args.command == "enotariado":
        res = ENotariadoEngine.verify_territorial_jurisdiction(args.property, args.domicile, args.serventia)
        print(json.dumps(res, ensure_ascii=False, indent=2))

    elif args.command == "usucapiao-workflow":
        res = ExtrajudicialWorkflowEngine.get_usucapiao_stage_info(args.stage)
        print(json.dumps(res, ensure_ascii=False, indent=2))

    elif args.command == "estremacao-check":
        res = EstremacaoEngine.validate_estremacao_requirements(args.posse_anos, True, True, True)
        print(json.dumps(res, ensure_ascii=False, indent=2))

    elif args.command == "succession":
        res = SuccessionEngine.calculate_succession_shares(args.value, args.regime, args.children)
        print(json.dumps(res, ensure_ascii=False, indent=2))

    elif args.command == "receive-zip":
        handler = LarkZipHandler()
        res = handler.process_incoming_zip(args.file)
        print(json.dumps(res, ensure_ascii=False, indent=2))

    elif args.command == "memory":
        mem = ConversationMemoryManager()
        if args.msg:
            mem.add_turn(args.session, "User", args.msg)
        context = mem.get_conversation_context(args.session)
        print(json.dumps(context, ensure_ascii=False, indent=2))

    elif args.command == "lark-msg":
        bridge = LarkAgentProtocolBridge()
        res = bridge.handle_lark_message(args.session, args.sender, args.text, attachment_filepath=args.zip)
        print(json.dumps(res, ensure_ascii=False, indent=2))

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
