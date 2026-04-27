#!/bin/bash
# ============================================================
# Database Initialization Script
# ============================================================
# Creates all tables defined in sql/ddl/
# Usage: ./scripts/init_db.sh [--env dev|prod]

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SQL_DIR="$PROJECT_ROOT/sql/ddl"
ENV="${1:-dev}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_step() {
  echo -e "${GREEN}[STEP]${NC} $1"
}

echo_warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
  echo_step "Loading environment from .env"
  export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
else
  echo_warn ".env file not found, using defaults"
fi

# Database connection parameters
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-postgres}"
DB_NAME="${DB_NAME:-shaanxi_resilience}"

echo_step "Database: $DB_NAME@$DB_HOST:$DB_PORT"

# Check if database exists
check_db() {
  psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1
}

# Create database if not exists
create_db() {
  echo_step "Creating database: $DB_NAME"
  psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || true
}

# Execute SQL files
execute_sql() {
  local file="$1"
  local filename=$(basename "$file")
  echo "  - $filename"
  PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$file" || {
    echo_error "Failed to execute $filename"
    return 1
  }
}

# Create all tables
create_tables() {
  echo_step "Creating tables..."

  # Create tables in order (dependencies first)
  local order=(
    "dim/create_dim_section_info.sql"
    "dim/create_dim_station_info.sql"
    "dim/create_dim_road_topology.sql"
    "dim/create_dim_scheme_info.sql"
    "dim/create_dim_capacity_rule.sql"
    "dim/create_dim_toll_diversion_rule.sql"
    "dwd/create_dwd_single_trip_info.sql"
    "dwd/create_dwd_scheme_section_map.sql"
    "dwd/create_dwd_od_path_map.sql"
    "dws/create_dws_section_capacity_day.sql"
    "dws/create_dws_section_od_flow_day.sql"
    "dws/create_dws_section_flow_day.sql"
    "dws/create_dws_impacted_od_flow_day.sql"
    "dws/create_dws_od_candidate_path.sql"
    "ads/create_ads_od_diversion_plan.sql"
    "ads/create_ads_toll_impact_result.sql"
    "ads/create_ads_scheme_summary.sql"
  )

  for rel_path in "${order[@]}"; do
    local file="$SQL_DIR/$rel_path"
    if [ -f "$file" ]; then
      execute_sql "$file"
    else
      echo_warn "File not found: $file"
    fi
  done
}

# Main
main() {
  echo_step "=========================================="
  echo_step "Database Initialization"
  echo_step "=========================================="

  if ! check_db; then
    create_db
  else
    echo_step "Database $DB_NAME already exists"
  fi

  create_tables

  echo_step "=========================================="
  echo_step "Database initialization completed!"
  echo_step "=========================================="
}

main "$@"
