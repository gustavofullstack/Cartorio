#!/usr/bin/env python3
"""Coleta a tabela oficial de emolumentos do TJMG e valida contra o catálogo.

Fluxo (docs/DADOS_PRECOS_E_PAINEL_AGENT_AI.md): download da fonte primária →
SHA-256 → extração isolada → diff contra o catálogo publicado. Divergência ou
hash novo NÃO publica nada: sai com código 1 e relatório para revisão humana.

Uso:
    cd backend && uv run python ../scripts/coletar_tabela_tjmg.py
    cd backend && uv run python ../scripts/coletar_tabela_tjmg.py --salvar-evidencia
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.emolumento_fonte_tjmg import (  # noqa: E402
    baixar_fonte,
    diff_com_catalogo,
    extrair_tabela1,
    sha256_pdf,
)
from app.services.emolumento_real_djalma import FONTE_SHA256, FONTE_URL  # noqa: E402

EVIDENCIA_DIR = Path(__file__).resolve().parents[1] / "backend" / "data" / "fontes"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--salvar-evidencia",
        action="store_true",
        help="Grava o PDF capturado e o relatório de diff em backend/data/fontes/.",
    )
    args = parser.parse_args()

    capturado_em = datetime.now(timezone.utc).isoformat()
    print(f"[1/4] Baixando fonte primária: {FONTE_URL}")
    conteudo = baixar_fonte()

    sha256 = sha256_pdf(conteudo)
    hash_novo = sha256 != FONTE_SHA256
    print(
        f"[2/4] SHA-256: {sha256} ({'NOVO — revisão humana obrigatória' if hash_novo else 'confere com a proveniência registrada'})"
    )

    print("[3/4] Extraindo Tabela 1 (Atos do Tabelião de Notas)...")
    extracao = extrair_tabela1(conteudo)
    print(
        f"      itens extraídos: {len(extracao.itens)} | faixas 4.b: {len(extracao.faixas)}"
    )

    divergencias = diff_com_catalogo(extracao)
    print(f"[4/4] Diff contra o catálogo publicado: {len(divergencias)} divergência(s)")
    for d in divergencias:
        print(f"      - {d.slug} [{d.campo}]: catálogo={d.catalogo} fonte={d.fonte}")

    relatorio = {
        "fonte_url": FONTE_URL,
        "sha256": sha256,
        "sha256_registrado": FONTE_SHA256,
        "hash_novo": hash_novo,
        "capturado_em": capturado_em,
        "itens_extraidos": len(extracao.itens),
        "itens_nao_localizados": extracao.itens_nao_localizados,
        "faixas_extraidas": len(extracao.faixas),
        "divergencias": [d.__dict__ for d in divergencias],
        "estado": "EXTRACTED",
        "revisao_humana": "obrigatória antes de qualquer publicação",
    }

    if args.salvar_evidencia:
        EVIDENCIA_DIR.mkdir(parents=True, exist_ok=True)
        (EVIDENCIA_DIR / f"cpo86642025-{sha256[:8]}.pdf").write_bytes(conteudo)
        (EVIDENCIA_DIR / "ultimo_relatorio_coleta.json").write_text(
            json.dumps(relatorio, ensure_ascii=False, indent=2)
        )
        print(f"      evidência gravada em {EVIDENCIA_DIR}")

    if hash_novo or divergencias:
        print("RESULTADO: EXTRACTED — aguardando revisão humana (nada publicado).")
        return 1
    print("RESULTADO: zero divergências — catálogo íntegro.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
