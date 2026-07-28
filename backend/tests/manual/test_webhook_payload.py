from app.api.v1.whatsapp import parse_evolution_payload

payload_modern = {
    "event": "messages.upsert",
    "instance": "cartorio-2notas",
    "data": {
        "key": {"remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False, "id": "test-1"},
        "message": {"conversation": "Hello Fenix (modern)"},
        "messageType": "conversation",
        "pushName": "Gustavo Fenix",
    },
}

payload_legacy = {
    "event": "messages.upsert",
    "instance": "cartorio-2notas",
    "key": {"remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False, "id": "test-2"},
    "message": {"conversation": "Hello Fenix (legacy)"},
    "messageType": "conversation",
    "pushName": "Gustavo Fenix Legacy",
}

msg_modern = parse_evolution_payload(payload_modern)
print(f"Modern parse: {msg_modern}")

msg_legacy = parse_evolution_payload(payload_legacy)
print(f"Legacy parse: {msg_legacy}")
