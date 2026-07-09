#!/bin/bash
# Deploy a new coding agent on coding-vps_apenas_para_auxilio
# Usage: ./deploy_coding_agent.sh <agent_name> <port> [stack=main|side]
set -e
AGENT_NAME="${1:?Usage: $0 <agent_name> <port> [stack]}"
PORT="${2:?Usage: $0 <agent_name> <port> [stack]}"
STACK="${3:-main}"
VPS="100.99.172.84"
SSH_KEY="${HOME}/.ssh/id_ed25519_cartorio"

if [ "$STACK" = "main" ]; then
  SERVICE_NAME="coding-vps_apenas_para_auxilio_${AGENT_NAME}"
  REPLICAS=1
else
  SERVICE_NAME="coding-vps-agents_${AGENT_NAME}"
  REPLICAS=1
fi

echo "=== Deploying $AGENT_NAME on port $PORT (stack=$STACK) ==="
echo "Service: $SERVICE_NAME"

# Build image on VPS
ssh -i "$SSH_KEY" root@$VPS bash <<BUILDEOF
cd /opt/coding-vps-infra/agent-template
docker build -t "coding-vps/${AGENT_NAME}:latest" .
BUILDEOF

# Create or update service
ssh -i "$SSH_KEY" root@$VPS bash <<SERVICEEOF
set +e
if docker service ls --format '{{.Name}}' | grep -q "^${SERVICE_NAME}\$"; then
  echo "Service exists, updating image"
  docker service update --image "coding-vps/${AGENT_NAME}:latest" $SERVICE_NAME
else
  echo "Creating new service"
  docker service create \
    --name $SERVICE_NAME \
    --network coding-vps_apenas_para_auxilio_default \
    --env-file /opt/coding-vps-infra/agent-template/.env \
    --env "AGENT_NAME=$AGENT_NAME" \
    --replicas $REPLICAS \
    "coding-vps/${AGENT_NAME}:latest"
fi
SERVICEEOF

sleep 5
echo "=== Testing ==="
ssh -i "$SSH_KEY" root@$VPS docker exec \$(docker ps --filter "name=$SERVICE_NAME" -q | head -1) curl -s "http://localhost:8000/health"
echo
echo "=== Deploy $AGENT_NAME OK ==="
