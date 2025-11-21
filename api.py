#!/usr/bin/env python3
"""API Server Entry Point"""
from backend.app import create_app, create_socketio, running_benchmarks
from backend.routes import register_all_routes

app = create_app()
socketio = create_socketio(app)
register_all_routes(app, socketio, running_benchmarks)

if __name__ == '__main__':
    print("Starting API server on http://localhost:5050")
    socketio.run(app, debug=True, port=5050, host='0.0.0.0', allow_unsafe_werkzeug=True)
