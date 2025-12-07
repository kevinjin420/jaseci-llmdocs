#!/usr/bin/env python3
"""API Server Entry Point"""
import argparse
from backend.app import create_app, create_socketio, running_benchmarks
from backend.routes import register_all_routes

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='DocBench API Server')
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='Verbosity level: -v (basic), -vv (detailed), -vvv (debug), -vvvv (full debug)')
    args = parser.parse_args()

    verbosity = args.verbose if args.verbose > 0 else 1

    app = create_app(verbosity=verbosity)
    socketio = create_socketio(app, verbosity=verbosity)
    register_all_routes(app, socketio, running_benchmarks)

    verbosity_names = {1: 'BASIC', 2: 'DETAILED', 3: 'DEBUG', 4: 'FULL DEBUG'}
    print(f"Starting API server on http://localhost:5050 (verbosity: {verbosity_names.get(verbosity, 'BASIC')})")
    socketio.run(app, debug=True, port=5050, host='0.0.0.0', allow_unsafe_werkzeug=True)
else:
    app = create_app(verbosity=1)
    socketio = create_socketio(app, verbosity=1)
    register_all_routes(app, socketio, running_benchmarks)
