#!/bin/bash
set -e

# EHS Dashboard — Unified Start Script
# Usage: ./start.sh [port]

PORT="${1:-8000}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "=== EHS Dashboard Startup ==="
echo "Port: $PORT"
echo "Dir:  $SCRIPT_DIR"

# ── Check Node.js (required for Shield backend) ──
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is required but not installed."
    echo "Install with: sudo apt-get install -y nodejs npm"
    exit 1
fi
NODE_VERSION=$(node --version)
echo "Node.js: $NODE_VERSION"

# ── Python venv ──
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating Python venv..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# ── Install dependencies ──
echo "Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r "$BACKEND_DIR/requirements.txt"

# ── Start ──
echo "Starting EHS Dashboard on port $PORT..."
# Run from project root so ./data/ resolves to <project>/data/
cd "$SCRIPT_DIR"
exec uvicorn backend.main:app --host 0.0.0.0 --port "$PORT"
