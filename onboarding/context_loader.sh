#!/usr/bin/env bash
# context_loader.sh v4.0
#
# MINIMAL VERSION - Most functionality moved to /tasks and /adversarial-spec
#
# This script now only provides:
#   --check-sync: Verify core-practices.md is in sync with Brainquarters
#   --version: Print version
#
# DEPRECATED in v4.0:
#   - Domain loading (use /tasks to see current work)
#   - .active_context.md generation (CLAUDE.md is static now)
#   - Context chunks (use checkpoints instead)
#
# New workflow:
#   1. CLAUDE.md is static (60-100 lines, hand-written)
#   2. Run /tasks to see current work streams
#   3. Run /adversarial-spec to resume spec sessions
#   4. Checkpoints in .adversarial-spec/checkpoints/ for session state

set -euo pipefail

VERSION="4.0"
BRAINQUARTERS="/home/jason/PycharmProjects/Brainquarters"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ------------------------------------------------------------
# Help / Version
# ------------------------------------------------------------
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  echo "context_loader.sh v$VERSION"
  echo ""
  echo "Usage: $0 --check-sync"
  echo ""
  echo "Options:"
  echo "  --check-sync  Verify core-practices.md is in sync with Brainquarters"
  echo "  --version     Print version"
  echo ""
  echo "DEPRECATED: Domain loading and .active_context.md generation"
  echo "Use /tasks and /adversarial-spec for the new workflow."
  exit 0
fi

if [[ "${1:-}" == "--version" ]]; then
  echo "context_loader.sh v$VERSION"
  exit 0
fi

# ------------------------------------------------------------
# --check-sync: Verify core-practices.md is in sync
# ------------------------------------------------------------
if [[ "${1:-}" == "--check-sync" ]]; then
  local_file="$SCRIPT_DIR/core-practices.md"
  bq_file="$BRAINQUARTERS/onboarding/core-practices.md"

  if [[ ! -f "$local_file" ]]; then
    echo -e "${YELLOW}WARNING: core-practices.md not found${NC}" >&2
    exit 1
  fi

  if [[ ! -f "$bq_file" ]]; then
    echo -e "${YELLOW}WARNING: Cannot check sync - Brainquarters not found at $BRAINQUARTERS${NC}" >&2
    exit 1
  fi

  # Extract version from local (synced copy)
  local_version=$(grep -oP 'Base: Brainquarters v\d+\.\d+' "$local_file" 2>/dev/null | grep -oP 'v\d+\.\d+' || echo "none")

  # Extract version from Brainquarters canonical
  bq_version=$(grep -oP 'v\d+\.\d+' "$bq_file" 2>/dev/null | head -1 || echo "unknown")

  if [[ "$local_version" == "none" ]]; then
    echo -e "${YELLOW}WARNING: core-practices.md has no Base header - may not be from Brainquarters${NC}" >&2
    exit 1
  fi

  if [[ "$local_version" != "$bq_version" ]]; then
    echo "" >&2
    echo -e "${YELLOW}SYNC WARNING: core-practices.md is out of date${NC}" >&2
    echo "  Local version:        $local_version" >&2
    echo "  Brainquarters version: $bq_version" >&2
    echo "  Run: $BRAINQUARTERS/onboarding/sync-project.sh <project-name>" >&2
    echo "" >&2
    exit 1
  fi

  echo -e "${GREEN}Sync check: core-practices.md is up to date ($local_version)${NC}"
  exit 0
fi

# ------------------------------------------------------------
# Deprecated: Any other arguments
# ------------------------------------------------------------
echo "context_loader.sh v$VERSION" >&2
echo "" >&2
echo -e "${YELLOW}DEPRECATED: Domain loading has been removed in v4.0${NC}" >&2
echo "" >&2
echo "New workflow:" >&2
echo "  1. CLAUDE.md is now static (60-100 lines)" >&2
echo "  2. Run /tasks to see current work streams" >&2
echo "  3. Run /adversarial-spec to resume spec sessions" >&2
echo "  4. Checkpoints are in .adversarial-spec/checkpoints/" >&2
echo "" >&2
echo "Available commands:" >&2
echo "  $0 --check-sync   Verify core-practices.md sync" >&2
echo "  $0 --version      Print version" >&2
exit 1
