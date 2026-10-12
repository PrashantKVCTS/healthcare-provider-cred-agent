#!/usr/bin/env bash
# ==============================================================================
# Automated WSL2 Linux VM Provisioning Script for Healthcare Credentialing Agent
# ==============================================================================

set -e

echo "=========================================================="
echo "  WSL2 Linux VM Setup: Healthcare Credentialing Agent    "
echo "=========================================================="

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "[*] Project directory: ${PROJECT_DIR}"

echo "[1/4] Checking Linux Python3 packages..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv curl

echo "[2/4] Setting up Python virtual environment..."
VENV_DIR="${PROJECT_DIR}/.venv_linux"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip install --upgrade pip setuptools wheel
pip install -r "${PROJECT_DIR}/requirements.txt"

echo "[3/4] Running automated test verification..."
cd "${PROJECT_DIR}"
pytest tests/test_cred_agent.py -v

echo "[4/4] Starting Credentialing Agent Services (0.0.0.0 for host access)..."
export HOST="0.0.0.0"
export PORT="8000"
export UI_PORT="8501"

echo "=========================================================="
echo " WSL2 VM Services are now active!"
echo " Access from your Windows Host browser:"
echo "   - FastAPI Web Workbench: http://localhost:8000/ui"
echo "   - Streamlit Committee:   http://localhost:8501"
echo "   - Swagger API Docs:      http://localhost:8000/docs"
echo "=========================================================="

# Launch FastAPI in background, Streamlit in foreground
python3 api/appian_api.py &
API_PID=$!

streamlit run ui/app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true

# Clean up on exit
kill $API_PID 2>/dev/null || true
