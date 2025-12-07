#!/bin/bash

trap 'kill 0' EXIT

if command -v bun &> /dev/null; then
  PKG_MGR="bun"
  DEV_CMD="bun dev"
else
  PKG_MGR="npm"
  DEV_CMD="npm run dev"
fi

python3 api.py "$@" &
(cd control-panel && $DEV_CMD) &

echo "Backend: http://localhost:5050"
echo "Frontend: http://localhost:5555 ($PKG_MGR)"

wait