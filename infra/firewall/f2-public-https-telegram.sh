#!/usr/bin/env bash
# F2 fix 2026-07-09: allow public TCP 80/443 for Traefik (API + Telegram webhooks + LE)
# while keeping admin ports Tailscale-only. DO NOT re-add F2-DU-HTTPS-DROP.
set -euo pipefail
iptables -C DOCKER-USER -p tcp --dport 443 -j ACCEPT -m comment --comment "F2-DU-HTTPS-PUBLIC-API" 2>/dev/null \
  || iptables -I DOCKER-USER 1 -p tcp --dport 443 -j ACCEPT -m comment --comment "F2-DU-HTTPS-PUBLIC-API"
iptables -C DOCKER-USER -p tcp --dport 80 -j ACCEPT -m comment --comment "F2-DU-HTTP-PUBLIC-LE" 2>/dev/null \
  || iptables -I DOCKER-USER 1 -p tcp --dport 80 -j ACCEPT -m comment --comment "F2-DU-HTTP-PUBLIC-LE"
# Remove accidental public DROP on 80/443 if reintroduced
for comment in "F2-DU-HTTP-DROP" "F2-DU-HTTPS-DROP" "F2-DU-HTTP-TS" "F2-DU-HTTPS-TS"; do
  while iptables -L DOCKER-USER -n --line-numbers 2>/dev/null | grep -q "$comment"; do
    NUM=$(iptables -L DOCKER-USER -n --line-numbers | grep "$comment" | head -1 | awk '{print $1}')
    iptables -D DOCKER-USER "$NUM"
  done
done
iptables-save > /etc/iptables/rules.v4
echo "OK: public 80/443 allowed for Telegram webhooks"
