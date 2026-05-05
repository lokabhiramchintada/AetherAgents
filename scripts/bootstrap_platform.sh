#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/.run/logs"
PID_DIR="$ROOT_DIR/.run/pids"

mkdir -p "$LOG_DIR" "$PID_DIR"

echo "[1/6] Starting infra containers (Kafka, master node, VMs, nginx)..."
docker compose -f "$ROOT_DIR/infra/docker-compose.platform.yml" up -d

echo "[2/6] Preparing Python env (local)..."
python -m venv "$ROOT_DIR/.venv"
source "$ROOT_DIR/.venv/bin/activate"
pip install --upgrade pip >/dev/null
pip install \
  fastapi==0.104.0 uvicorn==0.24.0 pydantic==2.5.0 \
  python-dotenv==1.0.0 email-validator==2.2.0 \
  kafka-python==2.0.2 pyyaml==6.0 requests==2.31.0 \
  jinja2==3.1.2 paramiko==3.4.0 sqlalchemy==2.0.31 \
  bcrypt==4.1.3 python-jose==3.3.0 >/dev/null

export KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"
export AETHER_APP_HEALTH_CHECKER_URL="${AETHER_APP_HEALTH_CHECKER_URL:-http://localhost:8015}"
export AETHER_LIFECYCLE_MANAGER_URL="${AETHER_LIFECYCLE_MANAGER_URL:-http://localhost:8016}"
export AETHER_NOTIFICATION_SERVICE_URL="${AETHER_NOTIFICATION_SERVICE_URL:-http://localhost:8019}"
export PYTHONPATH="$ROOT_DIR"

if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
  set +a
fi

run_service() {
  local name="$1"
  local module="$2"
  local port="$3"
  local log_file="$LOG_DIR/$name.log"
  local pid_file="$PID_DIR/$name.pid"
  echo "  - starting $name on :$port"
  nohup "$ROOT_DIR/.venv/bin/python" -m uvicorn "$module:app" --host 0.0.0.0 --port "$port" >"$log_file" 2>&1 &
  echo $! > "$pid_file"
}

echo "[3/6] Starting backend subsystems..."
run_service "user_management" "aether.subsystems.user_management.service" 8001
run_service "app_validator" "aether.subsystems.app_validator.service" 8011
run_service "app_registry" "aether.subsystems.app_registry.app_registry" 8012
run_service "vm_health_checker" "aether.subsystems.vm_health_checker.service" 8013
run_service "app_health_checker" "aether.subsystems.app_health_checker.service" 8015
run_service "lifecycle_manager" "aether.subsystems.lifecycle_manager.service" 8016
run_service "notification_service" "aether.subsystems.notification_service.service" 8019
run_service "gateway" "aether.gateway.app" 8000

echo "[4/6] Starting platform UI..."
pushd "$ROOT_DIR/aether/dashboard" >/dev/null
npm install >/dev/null
nohup npm run dev -- --host 0.0.0.0 --port 3000 >"$LOG_DIR/dashboard.log" 2>&1 &
echo $! > "$PID_DIR/dashboard.pid"
popd >/dev/null

echo "[5/6] Waiting for gateway health..."
for i in {1..30}; do
  if curl -sf "http://localhost:8000/health" >/dev/null; then
    break
  fi
  sleep 1
done

echo "[6/6] Platform bootstrapped."
echo "Gateway: http://localhost:8000"
echo "Dashboard UI: http://localhost:3000"
echo "Nginx LB: http://localhost"
echo "Kafka: localhost:9092"
echo "Master node shared repo mount: /shared-repo (inside aether-master-node)"
