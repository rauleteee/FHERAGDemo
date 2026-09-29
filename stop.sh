#!/usr/bin/env bash
#
# Stops anything this project may have started on its default ports —
# useful after a server or UI process got left running in a closed
# terminal, or crashed without cleaning up after itself.
#
# Usage: ./stop.sh [extra_port ...]
#   ./stop.sh              # stops the default server (8001) and UI (8501) ports
#   ./stop.sh 9000         # also stops a custom port, e.g. if you ran
#                          # `./run.sh server 9000`
#
set -uo pipefail  # no -e: we want to keep going even if one kill fails

DEFAULT_PORTS=(8001 8501)
EXTRA_PORTS=("$@")
ALL_PORTS=("${DEFAULT_PORTS[@]}" "${EXTRA_PORTS[@]}")

# Last-resort fallback needing zero external tools (no lsof/fuser/ss/
# netstat) — reads /proc directly. Works on any Linux system.
proc_net_port_pid() {
  local port="$1"
  local hex_port
  hex_port="$(printf '%04X' "$port")"
  local inode
  inode="$(awk -v p=":${hex_port}" '$2 ~ p {print $10; exit}' /proc/net/tcp 2>/dev/null)"
  [ -z "$inode" ] && return
  for fd_path in /proc/[0-9]*/fd/*; do
    [ -L "$fd_path" ] || continue
    if [ "$(readlink "$fd_path" 2>/dev/null)" = "socket:[${inode}]" ]; then
      echo "$fd_path" | sed -E 's#/proc/([0-9]+)/fd/.*#\1#'
      return
    fi
  done
}

kill_port() {
  local port="$1"
  local pids=""

  if command -v lsof >/dev/null 2>&1; then
    pids="$(lsof -ti "tcp:${port}" 2>/dev/null || true)"
  elif command -v fuser >/dev/null 2>&1; then
    pids="$(fuser -n tcp "${port}" 2>/dev/null | awk '{print $1}' || true)"
  elif command -v ss >/dev/null 2>&1; then
    pids="$(ss -ltnp 2>/dev/null | awk -v p=":${port}\$" '$4 ~ p' | grep -oP 'pid=\K[0-9]+' || true)"
  fi

  # None of the above tools available, or none found a match — try the
  # zero-dependency /proc fallback before giving up on this port.
  if [ -z "$pids" ]; then
    pids="$(proc_net_port_pid "$port")"
  fi

  if [ -n "$pids" ]; then
    echo "Stopping process on port ${port} (PID: ${pids})"
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null
    sleep 1
    for pid in $pids; do
      if kill -0 "$pid" 2>/dev/null; then
        echo "  still alive, force-killing PID ${pid}"
        kill -9 "$pid" 2>/dev/null
      fi
    done
  else
    echo "Port ${port}: nothing listening, nothing to stop."
  fi
}

echo "Stopping FHE-RAG processes..."
echo

for port in "${ALL_PORTS[@]}"; do
  kill_port "$port"
done

echo

# Belt-and-suspenders fallback: catch anything matching our own scripts
# by name, in case it's running on a non-default port we didn't check.
found_extra=false
if pkill -f "uvicorn server.app" 2>/dev/null; then
  echo "Stopped a uvicorn server.app process not on a checked port."
  found_extra=true
fi
if pkill -f "http.server .* --directory.*/web" 2>/dev/null; then
  echo "Stopped a web-explainer static server not on a checked port."
  found_extra=true
fi

if [ "$found_extra" = false ]; then
  echo "Done."
else
  echo
  echo "Done."
fi
