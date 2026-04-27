#!/bin/bash
# ============================================================
# Development Environment Setup and Run Script
# ============================================================
# Usage: ./scripts/run_dev.sh [command]

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo_info() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

echo_step() {
  echo -e "${GREEN}[STEP]${NC} $1"
}

# Ensure virtual environment exists
setup_venv() {
  if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    echo_step "Creating virtual environment..."
    python -m venv "$PROJECT_ROOT/.venv"
  fi

  echo_step "Activating virtual environment..."
  source "$PROJECT_ROOT/.venv/bin/activate" 2>/dev/null || source "$PROJECT_ROOT/.venv/Scripts/activate"

  echo_step "Installing dependencies..."
  pip install --upgrade pip
  pip install -e ".[dev]"
}

# Ensure output directories exist
setup_outputs() {
  echo_step "Creating output directories..."
  mkdir -p "$PROJECT_ROOT/outputs/logs"
  mkdir -p "$PROJECT_ROOT/outputs/exports"
  mkdir -p "$PROJECT_ROOT/outputs/reports"
  mkdir -p "$PROJECT_ROOT/outputs/temp"
}

# Run a specific module
run_module() {
  local module="$1"
  shift
  local args="$@"

  echo_step "Running module: $module"
  python -m src.jobs.run_$module $args
}

# Run full pipeline
run_pipeline() {
  local args="$@"
  echo_step "Running full pipeline"
  python -m src.jobs.run_pipeline $args
}

# Start API server
start_api() {
  echo_step "Starting Query API server..."
  echo_info "API will be available at http://localhost:8010"
  echo_info "API docs at http://localhost:8010/docs"
  uvicorn src.services.query_api.main:app --reload --host 0.0.0.0 --port 8010
}

# Main menu
show_help() {
  echo "Usage: ./scripts/run_dev.sh [command]"
  echo ""
  echo "Commands:"
  echo "  setup              Setup development environment"
  echo "  m0 [args]          Run M0 module"
  echo "  m1 [args]          Run M1 module"
  echo "  m2 [args]          Run M2 module"
  echo "  m3 [args]          Run M3 module"
  echo "  m4 [args]          Run M4 module"
  echo "  m5 [args]          Run M5 module"
  echo "  pipeline [args]    Run full pipeline"
  echo "  api                Start Query API server"
  echo "  help               Show this help message"
  echo ""
  echo "Examples:"
  echo "  ./scripts/run_dev.sh setup"
  echo "  ./scripts/run_dev.sh m0 --scheme-id SCH_001 --start-date 2026-04-01 --end-date 2026-04-30"
  echo "  ./scripts/run_dev.sh pipeline --scheme-id SCH_001 --start-date 2026-04-01 --end-date 2026-04-30"
}

# Main
COMMAND="${1:-help}"
shift || true

case "$COMMAND" in
  setup)
    setup_venv
    setup_outputs
    ;;
  m0|m1|m2|m3|m4|m5)
    setup_venv
    run_module "$COMMAND" "$@"
    ;;
  pipeline)
    setup_venv
    run_pipeline "$@"
    ;;
  api)
    setup_venv
    start_api
    ;;
  help|--help|-h)
    show_help
    ;;
  *)
    echo "Unknown command: $COMMAND"
    show_help
    exit 1
    ;;
esac
