#!/bin/sh
# Mac: forward refresh/notify signals to daemon hook server when running.
case "$1" in
  refresh) curl -sS -X POST http://127.0.0.1:27182/refresh 2>/dev/null || true ;;
  notify)  curl -sS -X POST http://127.0.0.1:27182/notify 2>/dev/null || true ;;
esac
