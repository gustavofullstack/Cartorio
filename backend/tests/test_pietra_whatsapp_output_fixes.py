from __future__ import annotations

from app.api.v1.whatsapp import parse_evolution_payload, split_whatsapp_text
from app.services.ptbr_output import normalize_ptbr_output
from app.services import pietra_memoria


def test_split_whatsapp_text_preserves_all_words_and_unicode() -> None:
    source = "A Ata Notarial é muito utilizada para provas em geral.\n\n" + "animais " * 180
    chunks = split_whatsapp_text(source, max_len=80)

    assert len(chunks) > 1
    assert all(len(chunk) <= 80 for chunk in chunks)
    assert "".join(chunks).replace("\n\n", "") != ""
    assert "animais" in " ".join(chunks)
    assert all(not chunk.endswith("animai") for chunk in chunks)


def test_split_whatsapp_text_does_not_drop_short_response() -> None:
    assert split_whatsapp_text("Olá, você está bem?", max_len=80) == ["Olá, você está bem?"]


def test_normalize_ptbr_output_repairs_common_model_spelling() -> None:
    result = normalize_ptbr_output("Ola. A Ata Notarial e um servico do cartorio. Nao corte animais.")
    assert result == "Olá. A Ata Notarial é um serviço do cartório. Não corte animais."


def test_parse_evolution_payload_accepts_root_level_legacy_shape() -> None:
    inbound = parse_evolution_payload(
        {
            "event": "MESSAGES_UPSERT",
            "key": {"remoteJid": "5534999999999@s.whatsapp.net", "id": "root-1"},
            "message": {"conversation": "Olá"},
        }
    )

    assert inbound is not None
    assert inbound.sender_id == "5534999999999@s.whatsapp.net"
    assert inbound.text == "Olá"


def test_pietra_memory_scrubs_content_before_persistence(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeDB:
        def execute(self, _statement, params):
            captured.update(params)

        def rollback(self):
            raise AssertionError("não deveria fazer rollback")

    class FakeRedis:
        def lpush(self, _key, entry):
            captured["redis_entry"] = entry

        def ltrim(self, *_args):
            return None

        def expire(self, *_args):
            return None

    monkeypatch.setattr(pietra_memoria, "get_redis", lambda: FakeRedis())
    assert pietra_memoria.salvar_mensagem(
        FakeDB(),
        telefone_hash="hash",
        session_id="s",
        role="user",
        content="CPF 123.456.789-09 e e-mail pessoa@example.com",
    )

    assert "123.456.789-09" not in str(captured["content"])
    assert "pessoa@example.com" not in str(captured["content"])
