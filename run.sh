#!/usr/bin/env bash
#
# Single entry point for this project. Handles venv creation so you
# never hit the "externally-managed-environment" pip error.
#
# Run with no arguments for a zero-friction demo: it sets up the
# virtual environment, downloads the embedding model, and runs the
# educational walkthrough — all automatically, on first run.
#
# Usage: ./run.sh [command] [args]
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"
MODEL_FILE="$SCRIPT_DIR/models/Xenova/all-MiniLM-L6-v2/model.onnx"

usage() {
  cat <<'USAGE'
Usage: ./run.sh [command] [args]

  (no command)       Zero-friction demo: sets up the environment if needed,
                     downloads the embedding model if needed, then runs the
                     educational walkthrough. This is the easiest way to
                     just see it work.

  setup              Create .venv and install dependencies
  download           Download the local ONNX embedding model (one-time, ~90MB)
  test               Run the test suite (pytest)
  learn              Run the educational, step-by-step demo — shows the
                     real plaintext vector, the real ciphertext bytes,
                     and the real decrypted result at every stage
  demo               Run the one-command end-to-end demo
                     (starts its own server, no second terminal needed)
  ui [port]          Serve the animated web explainer (default port: 8080).
                     Self-contained HTML/CSS/JS: an in-motion walkthrough that
                     compares semantic search WITHOUT FHE vs WITH FHE, with
                     theory on client/server and what each one stores.
  server [port]      Start the FastAPI server      (default port: 8001)
  client [url]       Run an interactive client      (default url:  http://127.0.0.1:8001)
                     against an already-running server — use this in a
                     second terminal after `./run.sh server`
  stop [port ...]    Stop any server processes left running on the default
                     port (8001), plus any extra ports given
  help               Show this message

Examples:
  ./run.sh                     # just run it — sets everything up automatically
  ./run.sh test
  ./run.sh learn

  # or, as two separate processes:
  ./run.sh server               # terminal 1
  ./run.sh client                # terminal 2
USAGE
}

ensure_venv() {
  if [ ! -x "$PYTHON_BIN" ]; then
    echo "No virtual environment found. Run './run.sh setup' first." >&2
    exit 1
  fi
}

cmd_setup() {
  if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in .venv ..."
    python3 -m venv "$VENV_DIR"
  else
    echo "Virtual environment already exists at .venv"
  fi

  echo "Installing dependencies..."
  "$PIP_BIN" install --upgrade pip --quiet
  "$PIP_BIN" install -r requirements.txt

  echo
  echo "Setup complete. You don't need to 'source .venv/bin/activate' —"
  echo "every ./run.sh command below already uses this environment."
}

cmd_download() {
  ensure_venv
  "$PYTHON_BIN" download_model.py
}

cmd_test() {
  ensure_venv
  "$PYTHON_BIN" -m pytest tests/ -v
}

cmd_server() {
  ensure_venv
  local port="${1:-8001}"
  echo "Starting server on http://127.0.0.1:${port} (no secret key ever held here)"
  "$PYTHON_BIN" -m uvicorn server.app:app --host 127.0.0.1 --port "$port"
}

cmd_client() {
  ensure_venv
  local url="${1:-http://127.0.0.1:8001}"
  "$PYTHON_BIN" client_cli.py "$url"
}

cmd_demo() {
  ensure_venv
  "$PYTHON_BIN" demo.py
}

cmd_learn() {
  ensure_venv
  "$PYTHON_BIN" educational_demo.py
}

cmd_ui() {
  # Animated web explainer, backed by the REAL FHE pipeline (web/app.py runs
  # the real server + client and serves the page). Needs the venv + model.
  ensure_venv
  if [ ! -f "$MODEL_FILE" ]; then
    echo "Embedding model not found — downloading first (one-time, ~90MB)..."
    cmd_download
    echo
  fi
  local want="${1:-8080}"
  # Pick the first free port at/above the requested one, so a busy port
  # (e.g. another app already on 8080) doesn't stop the demo.
  local port
  port="$("$PYTHON_BIN" - "$want" <<'PY'
import socket, sys
start = int(sys.argv[1])
for p in range(start, start + 50):
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", p)); s.close(); print(p); break
    except OSError:
        continue
else:
    print(start)
PY
)"
  if [ "$port" != "$want" ]; then
    echo "Port ${want} is busy — using ${port} instead."
  fi
  echo "Serving the web explainer (real pipeline) at http://127.0.0.1:${port}"
  echo "First load takes a few seconds while it encrypts + indexes the documents."
  echo "(Ctrl-C to stop)"
  "$PYTHON_BIN" -m uvicorn web.app:app --host 127.0.0.1 --port "$port"
}

cmd_stop() {
  # Doesn't need the venv — it just kills processes, no Python needed.
  bash "$SCRIPT_DIR/stop.sh" "$@"
}

cmd_auto() {
  if [ ! -x "$PYTHON_BIN" ]; then
    echo "First run — setting up automatically..."
    echo
    cmd_setup
    echo
  fi
  if [ ! -f "$MODEL_FILE" ]; then
    echo "Downloading the embedding model (one-time, ~90MB)..."
    echo
    cmd_download
    echo
  fi
  cmd_learn
}

main() {
  local command="${1:-}"

  if [ -z "$command" ]; then
    cmd_auto
    return
  fi

  shift || true
  case "$command" in
    setup)          cmd_setup "$@" ;;
    download)       cmd_download "$@" ;;
    test)           cmd_test "$@" ;;
    server)         cmd_server "$@" ;;
    client)         cmd_client "$@" ;;
    demo)           cmd_demo "$@" ;;
    ui)             cmd_ui "$@" ;;
    learn)          cmd_learn "$@" ;;
    stop)           cmd_stop "$@" ;;
    help|-h|--help) usage ;;
    *)
      echo "Unknown command: ${command}" >&2
      echo >&2
      usage >&2
      exit 1
      ;;
  esac
}

main "$@"
