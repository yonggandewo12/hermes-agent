#!/bin/bash
# ============================================================================
# Hermes Agent Source Installer
# ============================================================================
# Install Hermes Agent from an existing local source tree.
# Intended for internal-network deployments where the source code is already
# present and should NOT be cloned from GitHub.
#
# Usage:
#   ./scripts/install-from-source.sh
#   ./scripts/install-from-source.sh --source-dir /path/to/hermes-agent
#   ./scripts/install-from-source.sh --skip-setup
#
# Rules:
# - uv/Python/Git may be auto-installed if missing
# - pip and npm are REQUIRED to already exist; if missing, exit with guidance
# - package installs still use network access for Python/npm dependencies
# ============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'
BOLD='\033[1m'

HERMES_HOME="$HOME/.hermes"
PYTHON_VERSION="3.11"
NODE_VERSION="22"
RUN_SETUP=true
SOURCE_DIR="$(pwd)"
USE_VENV=true

log_info() { echo -e "${CYAN}→${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warn() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }

print_banner() {
  echo ""
  echo -e "${MAGENTA}${BOLD}"
  echo "┌─────────────────────────────────────────────────────────┐"
  echo "│         ⚕ Hermes Agent Source Installer                │"
  echo "└─────────────────────────────────────────────────────────┘"
  echo -e "${NC}"
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --source-dir)
      SOURCE_DIR="$2"
      shift 2
      ;;
    --skip-setup)
      RUN_SETUP=false
      shift
      ;;
    --no-venv)
      USE_VENV=false
      shift
      ;;
    -h|--help)
      echo "Usage: install-from-source.sh [--source-dir PATH] [--skip-setup] [--no-venv]"
      exit 0
      ;;
    *)
      log_error "Unknown option: $1"
      exit 1
      ;;
  esac
done

validate_source_dir() {
  if [ ! -d "$SOURCE_DIR" ]; then
    log_error "Source directory does not exist: $SOURCE_DIR"
    exit 1
  fi

  if [ ! -f "$SOURCE_DIR/pyproject.toml" ] || [ ! -f "$SOURCE_DIR/package.json" ] || [ ! -d "$SOURCE_DIR/hermes_cli" ]; then
    log_error "Not a Hermes source root: $SOURCE_DIR"
    log_info "Expected files: pyproject.toml, package.json, hermes_cli/"
    exit 1
  fi

  INSTALL_DIR="$SOURCE_DIR"
  log_success "Using local source tree: $INSTALL_DIR"
}

install_uv() {
  log_info "Checking uv package manager..."
  if command -v uv >/dev/null 2>&1; then
    UV_CMD="uv"
    log_success "uv found ($(uv --version 2>/dev/null))"
    return 0
  fi
  if [ -x "$HOME/.local/bin/uv" ]; then
    UV_CMD="$HOME/.local/bin/uv"
    log_success "uv found at ~/.local/bin ($("$UV_CMD" --version 2>/dev/null))"
    return 0
  fi
  if [ -x "$HOME/.cargo/bin/uv" ]; then
    UV_CMD="$HOME/.cargo/bin/uv"
    log_success "uv found at ~/.cargo/bin ($("$UV_CMD" --version 2>/dev/null))"
    return 0
  fi

  log_info "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  if [ -x "$HOME/.local/bin/uv" ]; then
    UV_CMD="$HOME/.local/bin/uv"
  elif [ -x "$HOME/.cargo/bin/uv" ]; then
    UV_CMD="$HOME/.cargo/bin/uv"
  elif command -v uv >/dev/null 2>&1; then
    UV_CMD="uv"
  else
    log_error "uv installation succeeded but uv was not found afterwards"
    exit 1
  fi
  log_success "uv installed ($("$UV_CMD" --version 2>/dev/null))"
}

check_python() {
  log_info "Checking Python $PYTHON_VERSION..."
  if "$UV_CMD" python find "$PYTHON_VERSION" >/dev/null 2>&1; then
    PYTHON_PATH=$("$UV_CMD" python find "$PYTHON_VERSION")
    log_success "Python found: $("$PYTHON_PATH" --version 2>/dev/null)"
    return 0
  fi
  log_info "Installing Python $PYTHON_VERSION via uv..."
  "$UV_CMD" python install "$PYTHON_VERSION"
  PYTHON_PATH=$("$UV_CMD" python find "$PYTHON_VERSION")
  log_success "Python installed: $("$PYTHON_PATH" --version 2>/dev/null)"
}

check_git() {
  log_info "Checking Git..."
  if command -v git >/dev/null 2>&1; then
    log_success "Git found ($(git --version))"
    return 0
  fi
  log_error "Git is required but not installed"
  case "$(uname -s)" in
    Linux*) log_info "Install manually via your package manager, e.g. apt/dnf/pacman" ;;
    Darwin*) log_info "Install manually: xcode-select --install or brew install git" ;;
    *) log_info "Install Git manually and rerun the script" ;;
  esac
  exit 1
}

check_pip() {
  log_info "Checking pip..."
  if python3 -m pip --version >/dev/null 2>&1; then
    log_success "pip found"
    return 0
  fi
  log_error "pip is required for internal source installation but was not found"
  log_info "Please install pip manually in your environment, then rerun this script"
  exit 1
}

check_node() {
  log_info "Checking Node.js..."
  if command -v node >/dev/null 2>&1; then
    HAS_NODE=true
    log_success "Node.js found ($(node --version 2>/dev/null))"
    return 0
  fi

  HAS_NODE=false
  log_info "Node.js not found — attempting install..."
  case "$(uname -s)" in
    Darwin*)
      if command -v brew >/dev/null 2>&1; then
        brew install node
        HAS_NODE=true
      fi
      ;;
    Linux*)
      if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update && sudo apt-get install -y nodejs npm || true
      elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y nodejs npm || true
      elif command -v pacman >/dev/null 2>&1; then
        sudo pacman -S --noconfirm nodejs npm || true
      fi
      if command -v node >/dev/null 2>&1; then HAS_NODE=true; fi
      ;;
  esac

  if [ "$HAS_NODE" = true ]; then
    log_success "Node.js available ($(node --version 2>/dev/null))"
  else
    log_warn "Node.js unavailable; browser-related tooling will be skipped"
  fi
}

check_npm() {
  log_info "Checking npm..."
  if command -v npm >/dev/null 2>&1; then
    log_success "npm found ($(npm --version 2>/dev/null))"
    return 0
  fi
  log_error "npm is required for internal source installation but was not found"
  log_info "Please install npm manually, then rerun this script"
  exit 1
}

install_optional_system_packages() {
  if ! command -v rg >/dev/null 2>&1; then
    log_warn "ripgrep not found; attempting install"
    case "$(uname -s)" in
      Darwin*)
        # macOS: skip ripgrep (no bottle → builds llvm@21 from source → hours)
        # ripgrep is optional; grep fallback is always available
        log_warn "Skipping ripgrep on macOS (brew would build llvm@21 from source — too slow)"
        log_info "Install manually if needed: brew install ripgrep"
        ;;
      Linux*)
        if command -v apt-get >/dev/null 2>&1; then sudo apt-get install -y ripgrep || true
        elif command -v dnf >/dev/null 2>&1; then sudo dnf install -y ripgrep || true
        elif command -v pacman >/dev/null 2>&1; then sudo pacman -S --noconfirm ripgrep || true
        fi
        ;;
    esac
  fi

  if ! command -v ffmpeg >/dev/null 2>&1; then
    log_warn "ffmpeg not found; attempting install"
    case "$(uname -s)" in
      Darwin*)
        # macOS: ffmpeg builds many deps from source on this OS version — too slow
        # TTS voice messages will be limited; skip for faster install
        log_warn "Skipping ffmpeg on macOS (slow build from source)"
        log_info "Install manually if needed: brew install ffmpeg"
        ;;
      Linux*)
        if command -v apt-get >/dev/null 2>&1; then sudo apt-get install -y ffmpeg || true
        elif command -v dnf >/dev/null 2>&1; then sudo dnf install -y ffmpeg || true
        elif command -v pacman >/dev/null 2>&1; then sudo pacman -S --noconfirm ffmpeg || true
        fi
        ;;
    esac
  fi
}

setup_venv() {
  if [ "$USE_VENV" = false ]; then
    log_warn "Skipping venv creation (--no-venv)"
    return 0
  fi
  cd "$INSTALL_DIR"
  if [ -d venv ]; then
    rm -rf venv
  fi
  "$UV_CMD" venv venv --python "$PYTHON_VERSION"
  export VIRTUAL_ENV="$INSTALL_DIR/venv"
  log_success "Virtual environment ready"
}

install_python_deps() {
  cd "$INSTALL_DIR"
  local python_bin="$INSTALL_DIR/venv/bin/python"
  if [ "$USE_VENV" = false ]; then
    python_bin="python3"
  fi
  # --no-compile: skip .pyc generation (faster install, compiled on first import)
  if ! "$UV_CMD" pip install --python "$python_bin" --no-compile ".[all]"; then
    log_warn "Full extras install failed, falling back to base install"
    "$UV_CMD" pip install --python "$python_bin" --no-compile .
  fi
  log_success "Python package installation complete"
}

install_node_deps() {
  if [ "$HAS_NODE" != true ]; then
    log_info "Skipping Node.js dependencies because Node.js is unavailable"
    return 0
  fi
  cd "$INSTALL_DIR"

  # Use faster npm flags: skip audit/fund checks, prefer cached packages
  local npm_flags="--silent --no-audit --no-fund --prefer-offline"

  install_repo_npm() {
    npm install $npm_flags || log_warn "npm install failed in repo root"
  }

  install_playwright_browser() {
    if [ ! -f "$INSTALL_DIR/package.json" ]; then
      return 0
    fi
    case "$(uname -s)" in
      Darwin*)
        npx playwright install chromium || log_warn "Playwright Chromium install failed"
        ;;
      Linux*)
        if command -v sudo >/dev/null 2>&1; then
          sudo npx playwright install --with-deps chromium || log_warn "Playwright Chromium install failed"
        else
          npx playwright install chromium || log_warn "Playwright Chromium install failed"
        fi
        ;;
      *)
        npx playwright install chromium || log_warn "Playwright Chromium install failed"
        ;;
    esac
  }

  if [ -f "$INSTALL_DIR/scripts/whatsapp-bridge/package.json" ]; then
    install_whatsapp_npm() {
      cd "$INSTALL_DIR/scripts/whatsapp-bridge"
      npm install $npm_flags || log_warn "npm install failed in whatsapp bridge"
    }
    install_repo_npm &
    install_whatsapp_npm &
    wait
  else
    install_repo_npm
  fi

  log_info "Installing Playwright Chromium browser..."
  install_playwright_browser
}

setup_path() {
  local link_dir="$HOME/.local/bin"
  mkdir -p "$link_dir"
  if [ "$USE_VENV" = true ]; then
    ln -sf "$INSTALL_DIR/venv/bin/hermes" "$link_dir/hermes"
  fi
  export PATH="$link_dir:$PATH"
  log_success "hermes command linked into ~/.local/bin"
}

copy_config_templates() {
  mkdir -p "$HERMES_HOME"/{cron,sessions,logs,pairing,hooks,image_cache,audio_cache,memories,skills,whatsapp/session}
  if [ ! -f "$HERMES_HOME/.env" ]; then
    if [ -f "$INSTALL_DIR/.env.example" ]; then
      cp "$INSTALL_DIR/.env.example" "$HERMES_HOME/.env"
    else
      touch "$HERMES_HOME/.env"
    fi
    log_success "Prepared ~/.hermes/.env"
  fi
  if [ ! -f "$HERMES_HOME/config.yaml" ] && [ -f "$INSTALL_DIR/cli-config.yaml.example" ]; then
    cp "$INSTALL_DIR/cli-config.yaml.example" "$HERMES_HOME/config.yaml"
    log_success "Prepared ~/.hermes/config.yaml"
  fi
  if [ ! -f "$HERMES_HOME/SOUL.md" ]; then
    cat > "$HERMES_HOME/SOUL.md" <<'EOF'
# Hermes Agent Persona
EOF
  fi
  if [ -x "$INSTALL_DIR/venv/bin/python" ]; then
    "$INSTALL_DIR/venv/bin/python" "$INSTALL_DIR/tools/skills_sync.py" 2>/dev/null || true
  fi
}

run_setup_wizard() {
  if [ "$RUN_SETUP" = false ]; then
    log_info "Skipping setup wizard (--skip-setup)"
    return 0
  fi
  if [ ! -e /dev/tty ]; then
    log_info "No terminal available, skipping interactive setup"
    return 0
  fi
  cd "$INSTALL_DIR"
  if [ "$USE_VENV" = true ] && [ -x "$INSTALL_DIR/venv/bin/python" ]; then
    "$INSTALL_DIR/venv/bin/python" -m hermes_cli.main setup < /dev/tty
  elif command -v python3 >/dev/null 2>&1; then
    python3 -m hermes_cli.main setup < /dev/tty
  else
    log_warn "Skipping setup wizard because no Python executable is available"
  fi
}

verify_install() {
  cd "$INSTALL_DIR"
  export PATH="$HOME/.local/bin:$PATH"
  log_info "Running installation verification..."
  local hermes_bin
  if [ "$USE_VENV" = true ]; then
    hermes_bin="$INSTALL_DIR/venv/bin/hermes"
  else
    hermes_bin="$(command -v hermes || true)"
  fi
  if [ -z "$hermes_bin" ] || [ ! -x "$hermes_bin" ]; then
    log_error "hermes executable not found for verification"
    exit 1
  fi
  "$hermes_bin" --version
  "$hermes_bin" doctor
  log_success "End-to-end source installation verification passed"
}

main() {
  print_banner
  validate_source_dir
  install_uv
  check_python
  check_git
  check_pip
  check_node
  check_npm
  install_optional_system_packages
  setup_venv
  install_python_deps
  install_node_deps
  setup_path
  copy_config_templates
  run_setup_wizard
  verify_install
}

main
