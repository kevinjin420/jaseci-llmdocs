"""Health route handlers"""
from flask import jsonify
import os
from database import get_db
from database.models import BenchmarkResult, BenchmarkRun


def register_routes(app, socketio=None, running_benchmarks=None):

    @app.route('/api/env-status', methods=['GET'])
    def env_status():
        return jsonify({'keys': {'OPENROUTER_API_KEY': bool(os.getenv('OPENROUTER_API_KEY'))}})

    @app.route('/api/clear-db', methods=['POST'])
    def clear_database():
        with get_db() as session:
            deleted_results = session.query(BenchmarkResult).delete()
            deleted_runs = session.query(BenchmarkRun).delete()
        return jsonify({
            'status': 'success',
            'message': f'Cleared {deleted_results} results and {deleted_runs} runs'
        })
