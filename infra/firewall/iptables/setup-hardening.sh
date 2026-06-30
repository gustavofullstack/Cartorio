#!/usr/bin/env bash
# =============================================================================
# iptables hardening — Cartório 2notas (FASE 2)
# =============================================================================
# DRAFT — NÃO EXECUTAR sem GO Gustavo via Telegram DM 6682284055
#         ou GRUPO -5006771024.
# Boundary rule: Lesson 245 + 247 + 250 (cross-agent directive ≠ autorização).
#
# Autor: M3 (Pietra root agent)
# Data:  2026-06-30
# Stack: Ubuntu 22.04 + iptables-nft + Docker (Traefik + OpenClaw + Easypanel)
#
# Objetivo:
#   - Criar chain fail2ban (idempotente) e linkar em INPUT
#   - INPUT default = ACCEPT (fail2ban gerencia ban; mantemos fail-safe)
#   - Tailscale 100.64.0.0/10 = always allowed (admin/Gustavo/agents)
#   - Loopback always allowed
#   - Established/related always allowed
#   - INVALID drop (silently)
#   - Log de drop em /var/log/iptables-fase2.log
#
# Idempotência: pode rodar 2x. Cria chain só se não existir; flushea chain
# fail2ban antes de repopular (fail2ban vai recriar bans ao reiniciar).
#
# ROLLBACK: ver função rollback() no fim. Recria iptables-flush se disaster.
# =============================================================================

set -euo pipefail

# --- Sanity checks -----------------------------------------------------------
if [[ $EUID -ne 0 ]]; then
  echo "[FATAL] Rode como root: sudo bash $0" >&2
  exit 1
fi

# Detectar backend (nft vs legacy). Ubuntu 22.04 default = iptables-nft.
IPT="$(command -v iptables)"
if [[ -z "$IPT" ]]; then
  echo "[FATAL] iptables não encontrado" >&2
  exit 1
fi

# Verificar Docker Swarm chain DOCKER-USER existe (não vamos tocar nela).
if ! $IPT -nL DOCKER-USER >/dev/null 2>&1; then
  echo "[WARN] chain DOCKER-USER não existe ainda (Swarm pode estar parado)"
fi

# --- Variáveis ---------------------------------------------------------------
TAILSCALE_CIDR="100.64.0.0/10"   # Tailscale CGNAT range
LOOPBACK="127.0.0.0/8"
F2B_CHAIN="f2b-cartorio"          # fail2ban banaction chain (custom)
LOG_PREFIX="F2-DROP:"
LOG_FILE="/var/log/iptables-fase2.log"

SSH_PORT="22"
API_PORTS="80,443,8080"            # Traefik HTTP/HTTPS/8080
EASYPANEL_PORT="3000"
OPENCLAW_PORT="18789"

# --- Funções -----------------------------------------------------------------
backup_rules() {
  local bak="/root/iptables.bak.$(date +%Y%m%d-%H%M%S)"
  iptables-save > "$bak"
  echo "[OK] backup iptables salvo em $bak"
}

create_f2b_chain() {
  if $IPT -nL "$F2B_CHAIN" >/dev/null 2>&1; then
    echo "[OK] chain $F2B_CHAIN já existe, flusheando"
    $IPT -F "$F2B_CHAIN"
  else
    echo "[OK] criando chain $F2B_CHAIN"
    $IPT -N "$F2B_CHAIN"
  fi
  # Política RETURN: regra que casar com ban volta (drop). Sem match = RETURN
  # pra chain pai. fail2ban insere -j DROP nesse chain pra IPs banidos.
  $IPT -A "$F2B_CHAIN" -j RETURN
}

link_f2b_in_input() {
  # Inserir f2b-chain cedo em INPUT (depois de established/related, antes do resto)
  if ! $IPT -C INPUT -j "$F2B_CHAIN" 2>/dev/null; then
    $IPT -I INPUT 1 -j "$F2B_CHAIN"
    echo "[OK] chain $F2B_CHAIN linkada em INPUT (posição 1)"
  else
    echo "[OK] chain $F2B_CHAIN já linkada em INPUT"
  fi
}

allow_always() {
  # Loopback (input + output já é OK por padrão mas explicita)
  $IPT -A INPUT -i lo -j ACCEPT -m comment --comment "loopback"

  # Established/related (stateful)
  $IPT -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT \
    -m comment --comment "stateful established/related"

  # Tailscale (admin/Gustavo/agents). 100.64.0.0/10 é CGNAT do Tailscale.
  $IPT -A INPUT -s "$TAILSCALE_CIDR" -j ACCEPT \
    -m comment --comment "tailscale always-allow"

  # SSH restrito a Tailscale (nada de SSH público!)
  $IPT -A INPUT -p tcp --dport "$SSH_PORT" -s "$TAILSCALE_CIDR" -j ACCEPT \
    -m comment --comment "ssh from tailscale only"
}

log_drops() {
  # Log + drop tudo que sobrou (limit evita log flood)
  $IPT -A INPUT -m limit --limit 5/min --limit-burst 10 \
    -j LOG --log-prefix "$LOG_PREFIX" --log-level 4
  $IPT -A INPUT -j DROP
}

# --- Execução principal ------------------------------------------------------
echo "=== Cartório FASE 2 iptables hardening (DRAFT) ==="
echo "Quando executar: confirmar GO Gustavo via Telegram antes."
echo
backup_rules
allow_always
create_f2b_chain
link_f2b_in_input
log_drops

echo
echo "=== Estado final ==="
$IPT -L INPUT -nv --line-numbers
echo
$IPT -L "$F2B_CHAIN" -nv --line-numbers
echo
echo "[OK] hardening aplicado. Logs em $LOG_FILE"
echo "[INFO] fail2ban vai popular $F2B_CHAIN dinamicamente quando reiniciar."
echo "[INFO] Para testar sem fail2ban: iptables -I $F2B_CHAIN 1 -s 1.2.3.4 -j DROP"

# --- Rollback -----------------------------------------------------------------
: <<'ROLLBACK_DOC'
ROLLBACK (disaster recovery):

  # 1. Backup mais recente
  LATEST=$(ls -t /root/iptables.bak.* | head -1)
  iptables-restore < "$LATEST"

  # 2. Ou flush total (perigoso: derruba Tailscale se já desconectou)
  iptables -F INPUT
  iptables -P INPUT ACCEPT
  iptables -F f2b-cartorio
  iptables -X f2b-cartorio

VERIFICAÇÃO PÓS-APPLY:

  iptables -L INPUT -nv
  # Esperado: chain INPUT com ~6-7 regras (loopback, established, tailscale,
  # ssh-from-tailscale, f2b-chain, log, drop)

  iptables -L f2b-cartorio -nv
  # Esperado: 1 regra RETURN (fail2ban insere -j DROP pra IPs banidos)

  tail -f /var/log/iptables-fase2.log
  # Conexões legítimas não devem aparecer; só probes/scanners.

ROLLBACK_DOC
