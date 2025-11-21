#!/bin/bash

trap 'kill 0' EXIT

python3 api.py &
(cd control-panel && bun dev) &

echo "Backend: http://localhost:5050"
echo "Frontend: http://localhost:5555"

wait